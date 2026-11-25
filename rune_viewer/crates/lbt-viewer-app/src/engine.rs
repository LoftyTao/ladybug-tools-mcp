//! Renderer and scene backend abstraction allowing zero-GPU headless Rune UI tests
//! alongside full `wgpu` rendering in the live application and `--snap` paths.

use std::f32::consts::{FRAC_PI_2, PI, TAU};

use glam::{Mat4, Vec3, Vec4};
use lbt_renderer_wgpu::{BuildingRenderer, RenderState};
use lbt_scene::{
    Bounds3, CameraPose, CameraPreset, ColorBy, IsolationMode, SceneData, SectionSpec,
};

/// Render state synchronized from `ViewerState` into the 3D renderer.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ViewerRenderState {
    pub color_by: ColorBy,
    pub selected_ids: Vec<u32>,
    pub highlighted_ids: Vec<u32>,
    pub isolation_mode: IsolationMode,
    pub validation_error_ids: Vec<u32>,
    pub validation_warning_ids: Vec<u32>,
    pub section: Option<SectionSpec>,
    pub dark_mode: bool,
    pub show_edges: bool,
}

/// Result of picking at a viewport coordinate.
#[derive(Copy, Clone, Debug, PartialEq)]
pub struct ViewerPickHit {
    pub object_id: u32,
    pub world_point: [f32; 3],
}

/// Abstraction over the 3D camera + offscreen renderer.
pub trait ViewerRenderer {
    fn set_scene(&mut self, scene: &SceneData);
    fn set_render_state(&mut self, state: &ViewerRenderState);
    fn apply_camera_preset(
        &mut self,
        preset: CameraPreset,
        bounds: Bounds3,
        highlight_bounds: Option<Bounds3>,
    );
    fn apply_camera_pose(&mut self, pose: &CameraPose);
    fn camera_pose(&self) -> CameraPose;
    fn orbit_pixels(&mut self, dx_pts: f32, dy_pts: f32, sensitivity: f32);
    fn pan_pixels(&mut self, dx_pts: f32, dy_pts: f32, viewport_h_pts: u32);
    fn zoom_wheel(&mut self, delta_lines: f32);
    fn zoom_factor(&mut self, factor: f32);
    fn set_orthographic(&mut self, ortho: bool);
    fn is_orthographic(&self) -> bool;
    fn project_world(&self, point: [f32; 3], width: u32, height: u32) -> Option<[f32; 2]>;
    /// Return camera basis `(right, up, forward)` in world Z-up coordinates for HUD compass.
    fn camera_basis(&self) -> ([f32; 3], [f32; 3], [f32; 3]);
    fn render_rgba(
        &mut self,
        width: u32,
        height: u32,
        out_rgba: &mut Vec<u8>,
    ) -> Result<(), String>;
    fn render_png(&mut self, width: u32, height: u32) -> Result<Vec<u8>, String>;
    fn pick_at(
        &mut self,
        px: f32,
        py: f32,
        width: u32,
        height: u32,
    ) -> Result<Option<ViewerPickHit>, String>;
}

/// Pure-CPU Z-up turntable camera backend used by headless Rune UI tests when no GPU is attached.
#[derive(Clone, Debug)]
pub struct CpuCameraBackend {
    pub target: [f32; 3],
    pub distance: f32,
    pub yaw: f32,
    pub pitch: f32,
    pub fov_y_deg: f32,
    pub orthographic: bool,
    pub ortho_height: f32,
    pub auto_ortho: bool,
    pub mock_pick: Option<ViewerPickHit>,
}

impl Default for CpuCameraBackend {
    fn default() -> Self {
        let fov_y_deg = 40.0_f32;
        let distance = 24.0_f32;
        Self {
            target: [0.0, 0.0, 1.5],
            distance,
            yaw: -52.0_f32.to_radians(),
            pitch: 28.0_f32.to_radians(),
            fov_y_deg,
            orthographic: false,
            ortho_height: 2.0 * distance * (0.5 * fov_y_deg.to_radians()).tan(),
            auto_ortho: false,
            mock_pick: None,
        }
    }
}

impl CpuCameraBackend {
    fn eye(&self) -> Vec3 {
        let (sp, cp) = (self.pitch.sin(), self.pitch.cos());
        let (sy, cy) = (self.yaw.sin(), self.yaw.cos());
        Vec3::new(
            self.target[0] + self.distance * cp * cy,
            self.target[1] + self.distance * cp * sy,
            self.target[2] + self.distance * sp,
        )
    }

    fn basis_vecs(&self) -> (Vec3, Vec3, Vec3) {
        let eye = self.eye();
        let target = Vec3::from_array(self.target);
        let fwd = (target - eye).normalize_or(Vec3::Y);
        let right = fwd.cross(Vec3::Z).normalize_or(Vec3::X);
        let up = right.cross(fwd).normalize_or(Vec3::Z);
        (right, up, fwd)
    }

    fn fit_bounds(&mut self, bounds: Bounds3) {
        if !bounds.is_valid() {
            return;
        }
        self.target = bounds.center();
        let diag = bounds.diagonal().max(2.0);
        let half_fov = (0.5 * self.fov_y_deg.to_radians()).clamp(0.1, 1.4);
        self.distance = (diag * 0.72 / half_fov.sin()).clamp(0.25, 100_000.0);
        self.ortho_height = (2.0 * self.distance * half_fov.tan()).max(0.2);
    }

    fn vp_matrix(&self, aspect: f32) -> Mat4 {
        let view = Mat4::look_at_rh(self.eye(), Vec3::from_array(self.target), Vec3::Z);
        let aspect = if aspect.is_finite() && aspect > 1e-4 {
            aspect
        } else {
            1.0
        };
        let proj = if self.orthographic {
            let half_h = 0.5 * self.ortho_height.max(0.1);
            let half_w = half_h * aspect;
            let bound = (self.distance + self.ortho_height * 10.0).max(200.0);
            Mat4::orthographic_rh(-half_w, half_w, -half_h, half_h, -bound, bound)
        } else {
            let near = (self.distance * 0.005).clamp(0.05, 1.0);
            let far = (self.distance + 500.0).max(near + 100.0);
            Mat4::perspective_rh(self.fov_y_deg.to_radians(), aspect, near, far)
        };
        proj * view
    }
}

impl ViewerRenderer for CpuCameraBackend {
    fn set_scene(&mut self, _scene: &SceneData) {}

    fn set_render_state(&mut self, _state: &ViewerRenderState) {}

    fn apply_camera_preset(
        &mut self,
        preset: CameraPreset,
        bounds: Bounds3,
        highlight_bounds: Option<Bounds3>,
    ) {
        let min_p = -89.0_f32.to_radians();
        let max_p = 89.0_f32.to_radians();
        match preset {
            CameraPreset::Keep => {}
            CameraPreset::Fit => self.fit_bounds(bounds),
            CameraPreset::FitHighlights => {
                self.fit_bounds(highlight_bounds.filter(Bounds3::is_valid).unwrap_or(bounds));
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
                self.pitch = max_p;
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
        self.pitch = self.pitch.clamp(min_p, max_p);
    }

    fn apply_camera_pose(&mut self, pose: &CameraPose) {
        self.target = pose.target;
        let offset = Vec3::from_array(pose.position) - Vec3::from_array(pose.target);
        let len = offset.length();
        if len > 1e-4 {
            self.distance = len.clamp(0.25, 100_000.0);
            let dir = offset / len;
            self.pitch = dir
                .z
                .clamp(-1.0, 1.0)
                .asin()
                .clamp(-89.0_f32.to_radians(), 89.0_f32.to_radians());
            if dir.x * dir.x + dir.y * dir.y > 1e-6 {
                self.yaw = dir.y.atan2(dir.x);
            }
        }
        if let Some(ortho) = pose.orthographic {
            self.orthographic = ortho;
            self.auto_ortho = false;
        }
        self.ortho_height =
            (2.0 * self.distance * (0.5 * self.fov_y_deg.to_radians()).tan()).max(0.2);
    }

    fn camera_pose(&self) -> CameraPose {
        CameraPose {
            position: self.eye().to_array(),
            target: self.target,
            up: Some([0.0, 0.0, 1.0]),
            orthographic: Some(self.orthographic),
        }
    }

    fn orbit_pixels(&mut self, dx_pts: f32, dy_pts: f32, sensitivity: f32) {
        self.yaw = (self.yaw - dx_pts * sensitivity).rem_euclid(TAU);
        self.pitch = (self.pitch + dy_pts * sensitivity)
            .clamp(-89.0_f32.to_radians(), 89.0_f32.to_radians());
    }

    fn pan_pixels(&mut self, dx_pts: f32, dy_pts: f32, viewport_h_pts: u32) {
        let (right, up, _) = self.basis_vecs();
        let vis_h = if self.orthographic {
            self.ortho_height
        } else {
            2.0 * self.distance * (0.5 * self.fov_y_deg.to_radians()).tan()
        };
        let scale = vis_h / viewport_h_pts.max(1) as f32;
        let next = Vec3::from_array(self.target) - right * (dx_pts * scale) + up * (dy_pts * scale);
        self.target = next.to_array();
    }

    fn zoom_wheel(&mut self, delta_lines: f32) {
        let factor = 0.88_f32.powf(delta_lines.clamp(-12.0, 12.0));
        self.zoom_factor(factor);
    }

    fn zoom_factor(&mut self, factor: f32) {
        if factor.is_finite() && factor > 0.0 {
            self.distance = (self.distance * factor).clamp(0.25, 100_000.0);
            self.ortho_height =
                (2.0 * self.distance * (0.5 * self.fov_y_deg.to_radians()).tan()).max(0.2);
        }
    }

    fn set_orthographic(&mut self, ortho: bool) {
        self.orthographic = ortho;
        self.auto_ortho = false;
    }

    fn is_orthographic(&self) -> bool {
        self.orthographic
    }

    fn project_world(&self, point: [f32; 3], width: u32, height: u32) -> Option<[f32; 2]> {
        if width == 0 || height == 0 {
            return None;
        }
        let clip = self.vp_matrix(width as f32 / height as f32)
            * Vec4::new(point[0], point[1], point[2], 1.0);
        if !clip.w.is_finite() || clip.w <= 1e-6 {
            return None;
        }
        let ndc = clip.truncate() / clip.w;
        if ndc.z < 0.0 || ndc.z > 1.0 {
            return None;
        }
        Some([
            (ndc.x * 0.5 + 0.5) * width as f32,
            (0.5 - ndc.y * 0.5) * height as f32,
        ])
    }

    fn camera_basis(&self) -> ([f32; 3], [f32; 3], [f32; 3]) {
        let (r, u, f) = self.basis_vecs();
        (r.to_array(), u.to_array(), f.to_array())
    }

    fn render_rgba(
        &mut self,
        width: u32,
        height: u32,
        out_rgba: &mut Vec<u8>,
    ) -> Result<(), String> {
        let len = (width as usize).saturating_mul(height as usize).saturating_mul(4);
        out_rgba.resize(len, 0);
        for chunk in out_rgba.chunks_exact_mut(4) {
            chunk[0] = 28;
            chunk[1] = 32;
            chunk[2] = 38;
            chunk[3] = 255;
        }
        Ok(())
    }

    fn render_png(&mut self, _width: u32, _height: u32) -> Result<Vec<u8>, String> {
        Ok(vec![137, 80, 78, 71, 13, 10, 26, 10])
    }

    fn pick_at(
        &mut self,
        _px: f32,
        _py: f32,
        _width: u32,
        _height: u32,
    ) -> Result<Option<ViewerPickHit>, String> {
        Ok(self.mock_pick)
    }
}

/// Convert viewer render state to `lbt_renderer_wgpu::RenderState`.
pub fn to_wgpu_render_state(state: &ViewerRenderState) -> RenderState {
    RenderState {
        color_by: state.color_by,
        selected_ids: state.selected_ids.clone(),
        highlighted_ids: state.highlighted_ids.clone(),
        isolation_mode: state.isolation_mode,
        validation_error_ids: state.validation_error_ids.clone(),
        validation_warning_ids: state.validation_warning_ids.clone(),
        section: state.section.clone(),
        dark_mode: state.dark_mode,
        show_edges: state.show_edges,
    }
}

/// Live `wgpu` GPU renderer implementation of [`ViewerRenderer`].
pub struct WgpuViewerRenderer {
    inner: BuildingRenderer,
}

impl WgpuViewerRenderer {
    /// Initialize offscreen `wgpu` device & pipelines.
    pub fn new() -> Result<Self, String> {
        BuildingRenderer::new()
            .map(|inner| Self { inner })
            .map_err(|e| e.to_string())
    }
}

impl ViewerRenderer for WgpuViewerRenderer {
    fn set_scene(&mut self, scene: &SceneData) {
        self.inner.set_scene(scene);
    }

    fn set_render_state(&mut self, state: &ViewerRenderState) {
        self.inner.set_render_state(&to_wgpu_render_state(state));
    }

    fn apply_camera_preset(
        &mut self,
        preset: CameraPreset,
        bounds: Bounds3,
        highlight_bounds: Option<Bounds3>,
    ) {
        self.inner
            .camera_mut()
            .apply_preset(preset, bounds, highlight_bounds);
    }

    fn apply_camera_pose(&mut self, pose: &CameraPose) {
        self.inner.camera_mut().apply_pose(pose);
    }

    fn camera_pose(&self) -> CameraPose {
        self.inner.camera().to_pose()
    }

    fn orbit_pixels(&mut self, dx_pts: f32, dy_pts: f32, sensitivity: f32) {
        self.inner
            .camera_mut()
            .orbit_pixels(dx_pts, dy_pts, sensitivity);
    }

    fn pan_pixels(&mut self, dx_pts: f32, dy_pts: f32, viewport_h_pts: u32) {
        self.inner
            .camera_mut()
            .pan_pixels(dx_pts, dy_pts, viewport_h_pts);
    }

    fn zoom_wheel(&mut self, delta_lines: f32) {
        self.inner.camera_mut().zoom_wheel(delta_lines);
    }

    fn zoom_factor(&mut self, factor: f32) {
        self.inner.camera_mut().zoom(factor);
    }

    fn set_orthographic(&mut self, ortho: bool) {
        self.inner.camera_mut().set_orthographic(ortho);
    }

    fn is_orthographic(&self) -> bool {
        self.inner.camera().orthographic
    }

    fn project_world(&self, point: [f32; 3], width: u32, height: u32) -> Option<[f32; 2]> {
        self.inner.camera().project_world(point, width, height)
    }

    fn camera_basis(&self) -> ([f32; 3], [f32; 3], [f32; 3]) {
        let cam = self.inner.camera();
        (cam.right(), cam.up(), cam.forward())
    }

    fn render_rgba(
        &mut self,
        width: u32,
        height: u32,
        out_rgba: &mut Vec<u8>,
    ) -> Result<(), String> {
        self.inner
            .render_rgba(width, height, out_rgba)
            .map_err(|e| e.to_string())
    }

    fn render_png(&mut self, width: u32, height: u32) -> Result<Vec<u8>, String> {
        self.inner.render_png(width, height).map_err(|e| e.to_string())
    }

    fn pick_at(
        &mut self,
        px: f32,
        py: f32,
        width: u32,
        height: u32,
    ) -> Result<Option<ViewerPickHit>, String> {
        self.inner
            .pick_at(px, py, width, height)
            .map(|hit| {
                hit.map(|h| ViewerPickHit {
                    object_id: h.object_id,
                    world_point: h.world_point,
                })
            })
            .map_err(|e| e.to_string())
    }
}
