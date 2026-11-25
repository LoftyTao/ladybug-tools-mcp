//! Z-up CAD turntable orbit camera with perspective and orthographic support.

use std::collections::HashSet;
use std::f32::consts::{FRAC_PI_2, PI, TAU};

use glam::{Mat4, Vec3, Vec4};
use lbt_scene::{Bounds3, CameraPose, CameraPreset, ObjectKind, SceneData};

const MIN_PITCH_RAD: f32 = -89.0_f32.to_radians();
const MAX_PITCH_RAD: f32 = 89.0_f32.to_radians();
const MIN_DISTANCE: f32 = 0.25;
const MAX_DISTANCE: f32 = 100_000.0;

/// Z-up CAD turntable orbit camera for architectural building inspection.
///
/// World coordinates follow Honeybee's right-handed Z-up convention:
/// `+X` = East, `+Y` = North, `+Z` = Up.
#[derive(Clone, Debug, PartialEq)]
pub struct OrbitCamera {
    /// World-space orbit target point in meters.
    pub target: [f32; 3],
    /// Distance from `target` to the camera eye in meters.
    pub distance: f32,
    /// Horizontal turntable azimuth in radians around world `+Z`.
    /// `0` places the eye at `+X` (East), `-PI/2` places the eye at `-Y` (South).
    pub yaw: f32,
    /// Vertical elevation angle in radians, clamped to `[-89°, +89°]`.
    pub pitch: f32,
    /// Vertical field-of-view in degrees for perspective projection.
    pub fov_y_deg: f32,
    /// When `true`, renders with orthographic projection instead of perspective.
    pub orthographic: bool,
    /// World-space visible vertical span when `orthographic == true`.
    pub ortho_height: f32,
    /// Tracks whether `orthographic` was turned on automatically by `CameraPreset::Top`.
    auto_ortho: bool,
}

impl Default for OrbitCamera {
    fn default() -> Self {
        Self::new()
    }
}

impl OrbitCamera {
    /// Construct a default South-East axonometric camera centered at `[0, 0, 1.5]`.
    pub fn new() -> Self {
        let fov_y_deg = 40.0_f32;
        let distance = 24.0_f32;
        let ortho_height = 2.0 * distance * (0.5 * fov_y_deg.to_radians()).tan();
        Self {
            target: [0.0, 0.0, 1.5],
            distance,
            yaw: -52.0_f32.to_radians(),
            pitch: 28.0_f32.to_radians(),
            fov_y_deg,
            orthographic: false,
            ortho_height,
            auto_ortho: false,
        }
    }

    /// World-space camera eye position.
    pub fn eye_position(&self) -> [f32; 3] {
        let cp = self.pitch.cos();
        let sp = self.pitch.sin();
        let cy = self.yaw.cos();
        let sy = self.yaw.sin();
        [
            self.target[0] + self.distance * cp * cy,
            self.target[1] + self.distance * cp * sy,
            self.target[2] + self.distance * sp,
        ]
    }

    /// Unit forward vector pointing from the eye toward `target`.
    pub fn forward(&self) -> [f32; 3] {
        let eye = Vec3::from_array(self.eye_position());
        let target = Vec3::from_array(self.target);
        (target - eye).normalize_or(Vec3::Y).to_array()
    }

    /// Unit camera right vector in world space (horizontal in Z-up turntable).
    pub fn right(&self) -> [f32; 3] {
        let fwd = Vec3::from_array(self.forward());
        fwd.cross(Vec3::Z).normalize_or(Vec3::X).to_array()
    }

    /// Unit camera up vector in world space.
    pub fn up(&self) -> [f32; 3] {
        let fwd = Vec3::from_array(self.forward());
        let right = Vec3::from_array(self.right());
        right.cross(fwd).normalize_or(Vec3::Z).to_array()
    }

    /// Switch perspective vs orthographic projection explicitly, keeping apparent target scale.
    pub fn set_orthographic(&mut self, orthographic: bool) {
        self.orthographic = orthographic;
        self.auto_ortho = false;
        self.sync_ortho_height();
    }

    /// Return whether orthographic projection is currently active.
    pub const fn is_orthographic(&self) -> bool {
        self.orthographic
    }

    /// Orbit around `target` by `delta_yaw_rad` and `delta_pitch_rad`, clamping pitch to `[-89°, +89°]`.
    pub fn orbit(&mut self, delta_yaw_rad: f32, delta_pitch_rad: f32) {
        self.yaw = wrap_angle(self.yaw + delta_yaw_rad);
        self.pitch = (self.pitch + delta_pitch_rad).clamp(MIN_PITCH_RAD, MAX_PITCH_RAD);
    }

    /// Orbit from screen-space pointer drag deltas (`dx` right, `dy` down in pixels).
    pub fn orbit_pixels(&mut self, dx_px: f32, dy_px: f32, sensitivity_rad_per_px: f32) {
        self.orbit(-dx_px * sensitivity_rad_per_px, dy_px * sensitivity_rad_per_px);
    }

    /// Pan `target` in the camera image plane by world-space displacements along `right` and `up`.
    pub fn pan_world(&mut self, delta_right: f32, delta_up: f32) {
        let right = Vec3::from_array(self.right());
        let up = Vec3::from_array(self.up());
        let target = Vec3::from_array(self.target) + right * delta_right + up * delta_up;
        self.target = target.to_array();
    }

    /// Pan `target` from screen-space pointer drag deltas (`dx` right, `dy` down in pixels).
    pub fn pan_pixels(&mut self, dx_px: f32, dy_px: f32, viewport_height: u32) {
        let h = viewport_height.max(1) as f32;
        let visible_height = self.visible_height_at_target();
        let units_per_px = visible_height / h;
        // Dragging content right/down moves the camera target left/up.
        self.pan_world(-dx_px * units_per_px, dy_px * units_per_px);
    }

    /// Zoom by scaling `distance` (and `ortho_height`) by `factor` (`< 1.0` zooms in, `> 1.0` zooms out).
    pub fn zoom(&mut self, factor: f32) {
        if !factor.is_finite() || factor <= 0.0 {
            return;
        }
        self.distance = (self.distance * factor).clamp(MIN_DISTANCE, MAX_DISTANCE);
        self.sync_ortho_height();
    }

    /// Smooth wheel zoom (`delta_lines > 0` zooms in, `< 0` zooms out).
    pub fn zoom_wheel(&mut self, delta_lines: f32) {
        if !delta_lines.is_finite() {
            return;
        }
        let factor = 0.88_f32.powf(delta_lines.clamp(-12.0, 12.0));
        self.zoom(factor);
    }

    /// Frame `bounds` comfortably inside the view while preserving current `yaw`, `pitch`, and projection.
    pub fn fit_bounds(&mut self, bounds: Bounds3) {
        if !bounds.is_valid() {
            return;
        }
        self.target = bounds.center();
        let size = bounds.size();
        let max_dim = size[0].max(size[1]).max(size[2]).max(1.0);
        let right = Vec3::from_array(self.right());
        let up = Vec3::from_array(self.up());
        let fwd = Vec3::from_array(self.forward());

        // Project the AABB extents onto the camera basis for snug framing of wide/tall buildings.
        let half = Vec3::new(size[0] * 0.5, size[1] * 0.5, size[2] * 0.5);
        let proj_half_w =
            half.x * right.x.abs() + half.y * right.y.abs() + half.z * right.z.abs();
        let proj_half_h = half.x * up.x.abs() + half.y * up.y.abs() + half.z * up.z.abs();
        let proj_half_d = half.x * fwd.x.abs() + half.y * fwd.y.abs() + half.z * fwd.z.abs();

        let assumed_aspect = 16.0_f32 / 9.0;
        let half_fov = 0.5 * self.fov_y_deg.to_radians().clamp(0.1, PI - 0.1);
        let tan_half_y = half_fov.tan();
        let tan_half_x = tan_half_y * assumed_aspect;

        let margin = 1.12_f32;
        let dist_y = (proj_half_h * margin) / tan_half_y + proj_half_d;
        let dist_x = (proj_half_w * margin) / tan_half_x + proj_half_d;
        let sphere_radius = 0.5 * bounds.diagonal().max(max_dim);
        let dist_sphere = (sphere_radius * 1.05) / half_fov.sin();

        self.distance = dist_y
            .max(dist_x)
            .max(dist_sphere * 0.78)
            .clamp(MIN_DISTANCE.max(max_dim * 0.25), MAX_DISTANCE);
        self.sync_ortho_height();
    }

    /// Frame the union bounds of `ids` within `scene`, falling back to `scene.bounds` if none match.
    pub fn fit_objects(&mut self, scene: &SceneData, ids: &[u32]) {
        if ids.is_empty() {
            self.fit_bounds(scene.bounds);
            return;
        }
        let wanted: HashSet<u32> = ids.iter().copied().collect();
        let mut combined = Bounds3::empty();
        for record in &scene.objects {
            if wanted.contains(&record.object_id) {
                combined.merge(&record.bounds);
            }
        }
        // If only Room containers were passed and a Room lacked bounds, check descendants.
        if !combined.is_valid() {
            let mut room_ids = HashSet::new();
            for record in &scene.objects {
                if record.kind == ObjectKind::Room && wanted.contains(&record.object_id) {
                    room_ids.insert(record.object_id);
                }
            }
            if !room_ids.is_empty() {
                for record in &scene.objects {
                    if record
                        .parent_object_id
                        .is_some_and(|pid| room_ids.contains(&pid))
                    {
                        combined.merge(&record.bounds);
                    }
                }
            }
        }
        if combined.is_valid() {
            self.fit_bounds(combined);
        } else {
            self.fit_bounds(scene.bounds);
        }
    }

    /// Apply a named [`CameraPreset`] using scene bounds and optional highlight bounds.
    pub fn apply_preset(
        &mut self,
        preset: CameraPreset,
        bounds: Bounds3,
        highlight_bounds: Option<Bounds3>,
    ) {
        match preset {
            CameraPreset::Keep => {}
            CameraPreset::Fit => {
                self.fit_bounds(bounds);
            }
            CameraPreset::FitHighlights => {
                let target_bounds = highlight_bounds
                    .filter(Bounds3::is_valid)
                    .unwrap_or(bounds);
                self.fit_bounds(target_bounds);
            }
            CameraPreset::Axon => {
                self.orthographic = false;
                self.auto_ortho = false;
                self.yaw = -52.0_f32.to_radians();
                self.pitch = 28.0_f32.to_radians();
                self.fit_bounds(bounds);
            }
            CameraPreset::Top => {
                self.orthographic = true;
                self.auto_ortho = true;
                self.yaw = -FRAC_PI_2;
                self.pitch = MAX_PITCH_RAD;
                self.fit_bounds(bounds);
            }
            CameraPreset::North => {
                if self.auto_ortho {
                    self.orthographic = false;
                    self.auto_ortho = false;
                }
                self.yaw = FRAC_PI_2;
                self.pitch = 0.0;
                self.fit_bounds(bounds);
            }
            CameraPreset::South => {
                if self.auto_ortho {
                    self.orthographic = false;
                    self.auto_ortho = false;
                }
                self.yaw = -FRAC_PI_2;
                self.pitch = 0.0;
                self.fit_bounds(bounds);
            }
            CameraPreset::East => {
                if self.auto_ortho {
                    self.orthographic = false;
                    self.auto_ortho = false;
                }
                self.yaw = 0.0;
                self.pitch = 0.0;
                self.fit_bounds(bounds);
            }
            CameraPreset::West => {
                if self.auto_ortho {
                    self.orthographic = false;
                    self.auto_ortho = false;
                }
                self.yaw = PI;
                self.pitch = 0.0;
                self.fit_bounds(bounds);
            }
        }
    }

    /// Apply an explicit [`CameraPose`] from `present.json` or `capture_request.json`.
    pub fn apply_pose(&mut self, pose: &CameraPose) {
        self.target = pose.target;
        let offset = Vec3::from_array(pose.position) - Vec3::from_array(pose.target);
        let len = offset.length();
        if len > 1e-4 {
            self.distance = len.clamp(MIN_DISTANCE, MAX_DISTANCE);
            let dir = offset / len;
            let raw_pitch = dir.z.clamp(-1.0, 1.0).asin();
            self.pitch = raw_pitch.clamp(MIN_PITCH_RAD, MAX_PITCH_RAD);
            if dir.x * dir.x + dir.y * dir.y > 1e-6 {
                self.yaw = dir.y.atan2(dir.x);
            } else if let Some(up) = pose.up {
                // If position is directly above/below target, orient yaw opposite the provided up vector.
                let up_v = Vec3::from_array(up);
                if up_v.x * up_v.x + up_v.y * up_v.y > 1e-6 {
                    self.yaw = (-up_v.y).atan2(-up_v.x);
                }
            }
        }
        if let Some(ortho) = pose.orthographic {
            self.orthographic = ortho;
            self.auto_ortho = false;
        }
        self.sync_ortho_height();
    }

    /// Export the current camera state as a [`CameraPose`] for `interaction_state.json`.
    pub fn to_pose(&self) -> CameraPose {
        CameraPose {
            position: self.eye_position(),
            target: self.target,
            up: Some([0.0, 0.0, 1.0]),
            orthographic: Some(self.orthographic),
        }
    }

    /// Right-handed view matrix mapping world coordinates into view space.
    pub fn view_matrix(&self) -> Mat4 {
        let eye = Vec3::from_array(self.eye_position());
        let target = Vec3::from_array(self.target);
        Mat4::look_at_rh(eye, target, Vec3::Z)
    }

    /// Right-handed projection matrix targeting wgpu's `[0, 1]` NDC depth range.
    pub fn projection_matrix(&self, aspect: f32) -> Mat4 {
        let aspect = if aspect.is_finite() && aspect > 1e-4 {
            aspect
        } else {
            1.0
        };
        let half_diag = self.visible_height_at_target().max(1.0);
        let z_near = (self.distance * 0.005).clamp(0.05, 1.0);
        let z_far = (self.distance + half_diag * 20.0).max(z_near + 500.0);
        if self.orthographic {
            let half_h = 0.5 * self.ortho_height.max(0.1);
            let half_w = half_h * aspect;
            // Use symmetric negative-to-positive depth bounds in view space so tall roofs behind
            // `target` are never clipped in top/elevation views.
            let ortho_near = -(self.distance + half_diag * 10.0).max(200.0);
            let ortho_far = (self.distance + half_diag * 10.0).max(200.0);
            Mat4::orthographic_rh(-half_w, half_w, -half_h, half_h, ortho_near, ortho_far)
        } else {
            Mat4::perspective_rh(self.fov_y_deg.to_radians(), aspect, z_near, z_far)
        }
    }

    /// Combined `projection * view` matrix.
    pub fn view_projection_matrix(&self, aspect: f32) -> Mat4 {
        self.projection_matrix(aspect) * self.view_matrix()
    }

    /// Project a 3D world point to 2D pixel coordinates `[px, py]` (top-left origin), or `None` if clipped.
    pub fn project_world(&self, point: [f32; 3], width: u32, height: u32) -> Option<[f32; 2]> {
        if width == 0 || height == 0 {
            return None;
        }
        let aspect = width as f32 / height as f32;
        let clip = self.view_projection_matrix(aspect)
            * Vec4::new(point[0], point[1], point[2], 1.0);
        if !clip.w.is_finite() || clip.w <= 1e-6 {
            return None;
        }
        let ndc = clip.truncate() / clip.w;
        if ndc.z < 0.0 || ndc.z > 1.0 {
            return None;
        }
        let px = (ndc.x * 0.5 + 0.5) * width as f32;
        let py = (0.5 - ndc.y * 0.5) * height as f32;
        if px.is_finite() && py.is_finite() {
            Some([px, py])
        } else {
            None
        }
    }

    /// Compute a world-space ray `(origin, unit_direction)` from screen pixel coordinates `(px, py)`.
    pub fn screen_ray(&self, px: f32, py: f32, width: u32, height: u32) -> ([f32; 3], [f32; 3]) {
        let w = width.max(1) as f32;
        let h = height.max(1) as f32;
        let ndc_x = (px / w) * 2.0 - 1.0;
        let ndc_y = 1.0 - (py / h) * 2.0;
        let inv = self.view_projection_matrix(w / h).inverse();
        let near_h = inv * Vec4::new(ndc_x, ndc_y, 0.0, 1.0);
        let far_h = inv * Vec4::new(ndc_x, ndc_y, 1.0, 1.0);
        let near = if near_h.w.abs() > 1e-7 {
            near_h.truncate() / near_h.w
        } else {
            Vec3::from_array(self.eye_position())
        };
        let far = if far_h.w.abs() > 1e-7 {
            far_h.truncate() / far_h.w
        } else {
            near + Vec3::from_array(self.forward())
        };
        let dir = (far - near).normalize_or(Vec3::from_array(self.forward()));
        (near.to_array(), dir.to_array())
    }

    /// Unproject a pixel `(px, py)` and normalized hardware depth `[0, 1]` into world XYZ coordinates.
    pub fn unproject_depth(
        &self,
        px: f32,
        py: f32,
        depth: f32,
        width: u32,
        height: u32,
    ) -> Option<[f32; 3]> {
        if width == 0 || height == 0 || !depth.is_finite() {
            return None;
        }
        let w = width as f32;
        let h = height as f32;
        let ndc_x = (px / w) * 2.0 - 1.0;
        let ndc_y = 1.0 - (py / h) * 2.0;
        let inv = self.view_projection_matrix(w / h).inverse();
        let world_h = inv * Vec4::new(ndc_x, ndc_y, depth, 1.0);
        if world_h.w.abs() <= 1e-7 {
            return None;
        }
        let world = world_h.truncate() / world_h.w;
        if world.is_finite() {
            Some(world.to_array())
        } else {
            None
        }
    }

    fn visible_height_at_target(&self) -> f32 {
        if self.orthographic {
            self.ortho_height
        } else {
            2.0 * self.distance * (0.5 * self.fov_y_deg.to_radians()).tan()
        }
    }

    fn sync_ortho_height(&mut self) {
        self.ortho_height = (2.0 * self.distance * (0.5 * self.fov_y_deg.to_radians()).tan()).max(0.2);
    }
}

fn wrap_angle(mut angle: f32) -> f32 {
    while angle > PI {
        angle -= TAU;
    }
    while angle < -PI {
        angle += TAU;
    }
    angle
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pitch_is_clamped_to_89_degrees_in_both_directions() {
        let mut cam = OrbitCamera::new();
        cam.orbit(0.0, 5.0);
        assert!((cam.pitch - MAX_PITCH_RAD).abs() < 1e-5);
        cam.orbit(0.0, -10.0);
        assert!((cam.pitch - MIN_PITCH_RAD).abs() < 1e-5);
    }

    #[test]
    fn project_world_and_screen_ray_roundtrip_persp_and_ortho() {
        for ortho in [false, true] {
            let mut cam = OrbitCamera::new();
            cam.set_orthographic(ortho);
            let bounds = Bounds3::new([0.0, 0.0, 0.0], [10.0, 8.0, 4.0]);
            cam.fit_bounds(bounds);

            let pt = [5.0, 4.0, 2.0];
            let px = cam.project_world(pt, 1280, 720).expect("target visible");
            assert!((px[0] - 640.0).abs() < 1.0, "center x: {px:?}");
            assert!((px[1] - 360.0).abs() < 1.0, "center y: {px:?}");

            let (origin, dir) = cam.screen_ray(px[0], px[1], 1280, 720);
            let to_pt = Vec3::from_array(pt) - Vec3::from_array(origin);
            let proj = to_pt.dot(Vec3::from_array(dir));
            let closest = Vec3::from_array(origin) + Vec3::from_array(dir) * proj;
            assert!(
                (closest - Vec3::from_array(pt)).length() < 1e-3,
                "ray missed point in ortho={ortho}: closest={closest:?}"
            );
        }
    }

    #[test]
    fn presets_and_pose_roundtrip_cleanly() {
        let mut cam = OrbitCamera::new();
        let bounds = Bounds3::new([0.0, 0.0, 0.0], [12.0, 10.0, 6.0]);
        let hi_bounds = Bounds3::new([0.0, 0.0, 0.0], [4.0, 4.0, 3.0]);

        cam.apply_preset(CameraPreset::Top, bounds, None);
        assert!(cam.is_orthographic());
        assert!((cam.pitch - MAX_PITCH_RAD).abs() < 1e-5);

        cam.apply_preset(CameraPreset::Axon, bounds, None);
        assert!(!cam.is_orthographic());

        cam.apply_preset(CameraPreset::FitHighlights, bounds, Some(hi_bounds));
        assert_eq!(cam.target, hi_bounds.center());

        let pose = cam.to_pose();
        let mut cam2 = OrbitCamera::new();
        cam2.apply_pose(&pose);
        assert!((Vec3::from_array(cam2.eye_position()) - Vec3::from_array(cam.eye_position())).length() < 1e-3);
        assert_eq!(cam2.is_orthographic(), cam.is_orthographic());
    }

    #[test]
    fn z_up_axes_match_cardinal_views() {
        let mut cam = OrbitCamera::new();
        let bounds = Bounds3::new([-5.0, -5.0, 0.0], [5.0, 5.0, 4.0]);

        cam.apply_preset(CameraPreset::South, bounds, None);
        assert!(cam.eye_position()[1] < 0.0);
        assert!(cam.forward()[1] > 0.99);
        assert!(cam.right()[0] > 0.99);

        cam.apply_preset(CameraPreset::North, bounds, None);
        assert!(cam.eye_position()[1] > 0.0);
        assert!(cam.forward()[1] < -0.99);

        cam.apply_preset(CameraPreset::East, bounds, None);
        assert!(cam.eye_position()[0] > 0.0);
        assert!(cam.forward()[0] < -0.99);

        cam.apply_preset(CameraPreset::West, bounds, None);
        assert!(cam.eye_position()[0] < 0.0);
        assert!(cam.forward()[0] > 0.99);
    }
}
