//! Application state, CAD camera/selection/pin actions, and bidirectional Garden sync state.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use lbt_mcp_bridge::{GardenBridge, GardenWatcher, utc_now_iso, write_bytes_atomic};
use lbt_scene::{
    Bounds3, Callout, CameraPose, CameraPreset, CameraSpec, CaptureRequest, ColorBy,
    IsolationMode, ObjectKind, ObjectRecord, ObjectTargetRef, PinStatus, PresentCommand,
    SceneData, SectionAxis, SectionSpec, SpatialPin, ValidationIssue, ViewportSnapshot,
};
use rune::{Pixels, TextEdit};

use crate::engine::{CpuCameraBackend, ViewerPickHit, ViewerRenderState, ViewerRenderer};
use crate::outliner::{
    OutlinerTree, build_outliner, escalate_to_room_id, expand_render_ids, find_parent_room,
    format_ai_context_prompt, issue_object_ids, select_similar_ids,
};

/// Active popup menu in the top bar.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum TopMenu {
    ColorBy,
    Camera,
}

/// Draft pin composer state before saving a spatial annotation.
#[derive(Clone, Debug)]
pub struct PendingPinDraft {
    pub target: Option<ObjectTargetRef>,
    pub target_label: String,
    pub world_point: [f32; 3],
    pub camera_bookmark: Option<CameraSpec>,
    pub comment_edit: TextEdit,
}

/// Complete viewer UI + 3D state driven by Rune.
pub struct ViewerState {
    pub dark_mode: bool,
    pub drawer_open: bool,
    pub drawer_user_toggled: bool,
    pub outliner_expanded_stories: BTreeSet<String>,
    pub outliner_expanded_rooms: BTreeSet<u32>,
    pub pins_section_open: bool,
    pub issues_section_open: bool,
    pub outliner_section_open: bool,

    pub model_label: String,
    pub model_path: Option<String>,
    pub garden_root: Option<PathBuf>,
    pub garden_id: Option<String>,
    pub present_revision: u64,
    pub present_title: Option<String>,
    pub present_note: Option<String>,

    pub scene: SceneData,
    pub outliner: OutlinerTree,
    pub color_by: ColorBy,
    pub isolation_mode: IsolationMode,
    pub local_isolate: bool,
    pub show_edges: bool,

    pub selected_ids: Vec<u32>,
    pub highlight_ids: Vec<u32>,
    pub validation_issues: Vec<ValidationIssue>,
    pub callouts: Vec<Callout>,
    pub annotations: Vec<SpatialPin>,
    pub pin_mode: bool,
    pub pin_draft: Option<PendingPinDraft>,
    pub active_pin_id: Option<String>,

    pub section: SectionSpec,
    pub open_menu: Option<TopMenu>,
    pub status_banner: Option<String>,
    pub last_copied_context: Option<String>,

    pub viewport_pixels: Pixels,
    pub viewport_pts: [f32; 2],
    pub viewport_scale: f32,
    pub backing_px: [u32; 2],
    pub render_buf: Vec<u8>,
    pub render_dirty: bool,
    pub renderer: Box<dyn ViewerRenderer>,

    pub drag_pan: bool,
    pub drag_prev_xy: [f32; 2],
    pub drag_start_pose: Option<CameraPose>,
    pub drag_moved: bool,

    pub watcher: Option<GardenWatcher>,
    pub bridge: Option<GardenBridge>,
    pub garden_stop: Option<Arc<AtomicBool>>,
    pub camera_flush_due: Option<f64>,
    pub next_pin_seq: u64,
}

impl ViewerState {
    /// Construct initial viewer state with an optional GPU renderer or CPU camera fallback.
    pub fn new(
        scene: SceneData,
        model_label: impl Into<String>,
        renderer: Option<Box<dyn ViewerRenderer>>,
    ) -> Self {
        let renderer = renderer.unwrap_or_else(|| Box::new(CpuCameraBackend::default()));
        let mut state = Self {
            dark_mode: true,
            drawer_open: true,
            drawer_user_toggled: false,
            outliner_expanded_stories: BTreeSet::new(),
            outliner_expanded_rooms: BTreeSet::new(),
            pins_section_open: true,
            issues_section_open: true,
            outliner_section_open: true,
            model_label: model_label.into(),
            model_path: scene.source_path.clone(),
            garden_root: None,
            garden_id: None,
            present_revision: 0,
            present_title: None,
            present_note: None,
            scene,
            outliner: OutlinerTree::default(),
            color_by: ColorBy::Type,
            isolation_mode: IsolationMode::Highlight,
            local_isolate: false,
            show_edges: true,
            selected_ids: Vec::new(),
            highlight_ids: Vec::new(),
            validation_issues: Vec::new(),
            callouts: Vec::new(),
            annotations: Vec::new(),
            pin_mode: false,
            pin_draft: None,
            active_pin_id: None,
            section: SectionSpec {
                enabled: false,
                axis: SectionAxis::Z,
                value: None,
                story: None,
                invert: false,
            },
            open_menu: None,
            status_banner: None,
            last_copied_context: None,
            viewport_pixels: Pixels::new(),
            viewport_pts: [960.0, 680.0],
            viewport_scale: 1.0,
            backing_px: [960, 680],
            render_buf: Vec::new(),
            render_dirty: true,
            renderer,
            drag_pan: false,
            drag_prev_xy: [0.0, 0.0],
            drag_start_pose: None,
            drag_moved: false,
            watcher: None,
            bridge: None,
            garden_stop: None,
            camera_flush_due: None,
            next_pin_seq: 1,
        };
        state.rebuild_scene_derived(true);
        state.render_viewport_now();
        state
    }

    /// Recompute outliner, default story/room expansion, and section elevation after loading a scene.
    pub fn rebuild_scene_derived(&mut self, fit_camera: bool) {
        self.outliner = build_outliner(&self.scene);
        self.outliner_expanded_stories.clear();
        for story in &self.outliner.stories {
            self.outliner_expanded_stories.insert(story.name.clone());
        }
        self.outliner_expanded_rooms.clear();
        if let Some(first_room) = self.outliner.stories.first().and_then(|s| s.rooms.first()) {
            self.outliner_expanded_rooms.insert(first_room.object_id);
        }
        if self.section.value.is_none() && self.scene.bounds.is_valid() {
            self.section.value = Some(self.scene.bounds.center()[2]);
        }
        self.renderer.set_scene(&self.scene);
        if fit_camera && self.scene.bounds.is_valid() {
            self.renderer
                .apply_camera_preset(CameraPreset::Axon, self.scene.bounds, None);
        }
        self.sync_render_state();
    }

    /// Synchronize current selection, highlights, validation issues, and section into the renderer.
    pub fn sync_render_state(&mut self) {
        let mut highlighted = expand_render_ids(&self.scene, &self.highlight_ids);
        let selected_render = expand_render_ids(&self.scene, &self.selected_ids);
        let mut isolation_mode = self.isolation_mode;

        if self.local_isolate && !selected_render.is_empty() {
            highlighted = selected_render.clone();
            isolation_mode = IsolationMode::Isolate;
        }

        let mut error_ids = Vec::new();
        let mut warning_ids = Vec::new();
        for issue in &self.validation_issues {
            let sev = issue
                .severity
                .as_deref()
                .unwrap_or("error")
                .to_ascii_lowercase();
            let ids = expand_render_ids(&self.scene, &issue_object_ids(&self.scene, issue));
            if sev.contains("warn") {
                for id in ids {
                    if !warning_ids.contains(&id) {
                        warning_ids.push(id);
                    }
                }
            } else {
                for id in ids {
                    if !error_ids.contains(&id) {
                        error_ids.push(id);
                    }
                }
            }
        }

        let section = if self.section.enabled {
            Some(self.section.clone())
        } else {
            None
        };

        self.renderer.set_render_state(&ViewerRenderState {
            color_by: self.color_by,
            selected_ids: selected_render,
            highlighted_ids: highlighted,
            isolation_mode,
            validation_error_ids: error_ids,
            validation_warning_ids: warning_ids,
            section,
            dark_mode: self.dark_mode,
            show_edges: self.show_edges,
        });
        self.render_dirty = true;
    }

    /// Render the 3D scene immediately into `self.viewport_pixels` using the ping-pong `render_buf`.
    pub fn render_viewport_now(&mut self) {
        let w = self.backing_px[0].max(1).min(4096);
        let h = self.backing_px[1].max(1).min(4096);
        let mut buf = std::mem::take(&mut self.render_buf);
        match self.renderer.render_rgba(w, h, &mut buf) {
            Ok(()) => {
                self.render_buf = self.viewport_pixels.replace(w, h, buf);
                self.render_dirty = false;
            }
            Err(err) => {
                self.render_buf = buf;
                self.status_banner = Some(format!("Render error: {err}"));
            }
        }
    }

    /// Update viewport layout size (in logical points) and HiDPI scale, re-rendering if backing pixels changed.
    pub fn on_viewport_layout(&mut self, w_pts: f32, h_pts: f32, scale: f32) {
        let scale = if scale.is_finite() && scale > 0.0 {
            scale
        } else {
            1.0
        };
        let pw = (w_pts * scale).round().max(1.0).min(4096.0) as u32;
        let ph = (h_pts * scale).round().max(1.0).min(4096.0) as u32;
        let size_changed =
            (self.viewport_pts[0] - w_pts).abs() > 0.5 || (self.viewport_pts[1] - h_pts).abs() > 0.5;
        let backing_changed = self.backing_px != [pw, ph] || (self.viewport_scale - scale).abs() > 1e-3;
        self.viewport_pts = [w_pts.max(1.0), h_pts.max(1.0)];
        self.viewport_scale = scale;
        if backing_changed || size_changed || self.render_dirty {
            self.backing_px = [pw, ph];
            self.render_viewport_now();
        }
    }

    /// Project a 3D world point into element-local viewport logical points.
    pub fn project_world_pts(&self, pt: [f32; 3]) -> Option<[f32; 2]> {
        let [pw, ph] = self.backing_px;
        let px = self.renderer.project_world(pt, pw, ph)?;
        let s = self.viewport_scale.max(1.0);
        Some([px[0] / s, px[1] / s])
    }

    /// Bounds of currently highlighted or selected objects, if any.
    pub fn active_highlight_bounds(&self) -> Option<Bounds3> {
        let ids = if !self.highlight_ids.is_empty() {
            &self.highlight_ids
        } else {
            &self.selected_ids
        };
        let mut combined = Bounds3::empty();
        for &id in ids {
            if let Some(rec) = self.scene.object_by_id(id) {
                combined.merge(&rec.bounds);
            }
        }
        combined.is_valid().then_some(combined)
    }

    /// Primary selected object record, if any.
    pub fn primary_selected(&self) -> Option<&ObjectRecord> {
        let id = *self.selected_ids.first()?;
        self.scene.object_by_id(id)
    }

    /// All currently selected object records.
    pub fn selected_records(&self) -> Vec<&ObjectRecord> {
        self.selected_ids
            .iter()
            .filter_map(|&id| self.scene.object_by_id(id))
            .collect()
    }

    /// Select a single object (or toggle when `additive == true`), optionally focusing camera on it.
    pub fn select_object(&mut self, object_id: u32, additive: bool, focus_camera: bool) {
        if object_id == 0 || self.scene.object_by_id(object_id).is_none() {
            if !additive {
                self.selected_ids.clear();
                self.local_isolate = false;
                self.sync_render_state();
                self.render_viewport_now();
                self.flush_interaction_state();
            }
            return;
        }
        if additive {
            if let Some(pos) = self.selected_ids.iter().position(|&id| id == object_id) {
                self.selected_ids.remove(pos);
            } else {
                self.selected_ids.push(object_id);
            }
        } else {
            self.selected_ids = vec![object_id];
        }
        if focus_camera {
            self.focus_on_object(object_id);
        }
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Focus camera target on `object_id` (and frame its bounds comfortably).
    pub fn focus_on_object(&mut self, object_id: u32) {
        if let Some(rec) = self.scene.object_by_id(object_id) {
            let b = rec.bounds;
            if b.is_valid() {
                self.renderer
                    .apply_camera_preset(CameraPreset::Keep, self.scene.bounds, Some(b));
                let mut pose = self.renderer.camera_pose();
                let center = b.center();
                let delta = [
                    center[0] - pose.target[0],
                    center[1] - pose.target[1],
                    center[2] - pose.target[2],
                ];
                pose.target = center;
                pose.position = [
                    pose.position[0] + delta[0],
                    pose.position[1] + delta[1],
                    pose.position[2] + delta[2],
                ];
                self.renderer.apply_camera_pose(&pose);
                self.render_dirty = true;
            }
        }
    }

    /// Focus camera on a 3D world point (or fallback to its target object).
    pub fn focus_on_pin(&mut self, pin: &SpatialPin) {
        self.active_pin_id = Some(pin.id.clone());
        if let Some(target) = &pin.target
            && let Some(rec) = self.scene.find_by_target(target)
        {
            self.selected_ids = vec![rec.object_id];
            self.sync_render_state();
        }
        if let Some(CameraSpec::Pose(pose)) = &pin.camera_bookmark {
            self.renderer.apply_camera_pose(pose);
        } else if let Some(pt) = pin.world_point {
            let mut pose = self.renderer.camera_pose();
            let delta = [
                pt[0] - pose.target[0],
                pt[1] - pose.target[1],
                pt[2] - pose.target[2],
            ];
            pose.target = pt;
            pose.position = [
                pose.position[0] + delta[0],
                pose.position[1] + delta[1],
                pose.position[2] + delta[2],
            ];
            self.renderer.apply_camera_pose(&pose);
        }
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Handle a single click on the 3D viewport at local logical coordinates `(lx, ly)`.
    pub fn handle_viewport_click(&mut self, lx: f32, ly: f32, shift: bool) {
        self.open_menu = None;
        let scale = self.viewport_scale.max(1.0);
        let [pw, ph] = self.backing_px;
        let hit = self
            .renderer
            .pick_at(lx * scale, ly * scale, pw, ph)
            .ok()
            .flatten()
            .filter(|h| h.object_id != 0);

        if self.pin_mode {
            if let Some(ViewerPickHit {
                object_id,
                world_point,
            }) = hit
            {
                let (target, label) = if let Some(rec) = self.scene.object_by_id(object_id) {
                    (Some(rec.target.clone()), rec.identifier.clone())
                } else {
                    (None, format!("Point ({:.1}, {:.1}, {:.1})", world_point[0], world_point[1], world_point[2]))
                };
                self.begin_pin_draft(target, label, world_point);
            } else if self.scene.bounds.is_valid() {
                let pt = self.scene.bounds.center();
                self.begin_pin_draft(None, "Scene Center".to_owned(), pt);
            }
            return;
        }

        match hit {
            Some(ViewerPickHit { object_id, .. }) => {
                self.select_object(object_id, shift, false);
            }
            None if !shift => {
                self.selected_ids.clear();
                self.local_isolate = false;
                self.sync_render_state();
                self.render_viewport_now();
                self.flush_interaction_state();
            }
            None => {}
        }
    }

    /// Handle double-click on the 3D viewport: escalate picked sub-face/face to its parent Room.
    pub fn handle_viewport_double_click(&mut self, lx: f32, ly: f32) {
        if self.pin_mode {
            return;
        }
        let scale = self.viewport_scale.max(1.0);
        let [pw, ph] = self.backing_px;
        let hit = self
            .renderer
            .pick_at(lx * scale, ly * scale, pw, ph)
            .ok()
            .flatten()
            .filter(|h| h.object_id != 0);
        if let Some(hit) = hit {
            let escalated = escalate_to_room_id(&self.scene, hit.object_id);
            self.select_object(escalated, false, false);
        } else if let Some(&first) = self.selected_ids.first() {
            let escalated = escalate_to_room_id(&self.scene, first);
            if escalated != first {
                self.select_object(escalated, false, false);
            }
        }
    }

    /// Start drafting a new 3D spatial pin.
    pub fn begin_pin_draft(
        &mut self,
        target: Option<ObjectTargetRef>,
        target_label: String,
        world_point: [f32; 3],
    ) {
        let mut edit = TextEdit::new("");
        edit.focused = true;
        self.pin_draft = Some(PendingPinDraft {
            target,
            target_label,
            world_point,
            camera_bookmark: Some(CameraSpec::Pose(self.renderer.camera_pose())),
            comment_edit: edit,
        });
    }

    /// Start drafting a pin on the currently selected object's centroid.
    pub fn pin_selected_object(&mut self) {
        let Some(rec) = self.primary_selected().cloned() else {
            return;
        };
        self.begin_pin_draft(Some(rec.target), rec.identifier, rec.centroid);
    }

    /// Commit the active `pin_draft` into `self.annotations` and flush to `interaction_state.json`.
    pub fn commit_pin_draft(&mut self) {
        let Some(draft) = self.pin_draft.take() else {
            return;
        };
        let seq = self.next_pin_seq;
        self.next_pin_seq += 1;
        let now = utc_now_iso();
        let comment = draft.comment_edit.text.trim().to_owned();
        let pin = SpatialPin {
            id: format!("pin_{}_{seq}", std::process::id()),
            status: PinStatus::Open,
            target: draft.target,
            world_point: Some(draft.world_point),
            comment,
            resolution_note: None,
            camera_bookmark: draft.camera_bookmark,
            created_at: Some(now.clone()),
            updated_at: Some(now),
        };
        self.active_pin_id = Some(pin.id.clone());
        self.pin_mode = false;
        self.annotations.push(pin);
        self.pins_section_open = true;
        self.status_banner = Some("Saved 3D spatial pin".to_owned());
        self.flush_interaction_state();
    }

    /// Mark an open pin as resolved locally and flush `interaction_state.json`.
    pub fn resolve_pin_local(&mut self, pin_id: &str) {
        let now = utc_now_iso();
        if let Some(pin) = self.annotations.iter_mut().find(|p| p.id == pin_id) {
            pin.status = PinStatus::Resolved;
            pin.resolution_note = Some("Resolved in viewer".to_owned());
            pin.updated_at = Some(now);
            self.flush_interaction_state();
        }
    }

    /// Switch ColorBy mode and re-render.
    pub fn set_color_by(&mut self, mode: ColorBy) {
        self.color_by = mode;
        self.open_menu = None;
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Apply a named camera preset and re-render.
    pub fn apply_camera_preset(&mut self, preset: CameraPreset) {
        let hi_bounds = self.active_highlight_bounds();
        self.renderer
            .apply_camera_preset(preset, self.scene.bounds, hi_bounds);
        self.open_menu = None;
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Toggle perspective vs orthographic projection and re-render.
    pub fn toggle_orthographic(&mut self) {
        let next = !self.renderer.is_orthographic();
        self.renderer.set_orthographic(next);
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Toggle horizontal section cut and re-render.
    pub fn toggle_section(&mut self) {
        self.section.enabled = !self.section.enabled;
        if self.section.enabled && self.section.value.is_none() {
            self.section.value = Some(if self.scene.bounds.is_valid() {
                self.scene.bounds.center()[2]
            } else {
                3.0
            });
        }
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Step section plane Z height by `delta` meters and enable section if currently off.
    pub fn step_section_z(&mut self, delta: f32) {
        let cur = self.section.value.unwrap_or_else(|| {
            if self.scene.bounds.is_valid() {
                self.scene.bounds.center()[2]
            } else {
                3.0
            }
        });
        let next = cur + delta;
        self.section.value = Some((next * 10.0).round() / 10.0);
        self.section.enabled = true;
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Toggle isolation of currently selected objects.
    pub fn toggle_isolate_selection(&mut self) {
        if self.selected_ids.is_empty() {
            self.local_isolate = false;
        } else {
            self.local_isolate = !self.local_isolate;
        }
        self.sync_render_state();
        self.render_viewport_now();
    }

    /// Select all objects similar to the primary selection.
    pub fn select_similar(&mut self) {
        let Some(anchor) = self.primary_selected().cloned() else {
            return;
        };
        let ids = select_similar_ids(&self.scene, &anchor);
        if !ids.is_empty() {
            self.selected_ids = ids;
            self.sync_render_state();
            self.render_viewport_now();
            self.flush_interaction_state();
        }
    }

    /// Clear current selection and local isolation.
    pub fn clear_selection(&mut self) {
        self.selected_ids.clear();
        self.local_isolate = false;
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Build the compact AI context prompt and copy it via `tx.copy`.
    pub fn copy_ai_context(&mut self) -> String {
        let selected = self.selected_records();
        let garden_str = self
            .garden_root
            .as_ref()
            .map(|p| p.to_string_lossy().into_owned());
        let prompt = format_ai_context_prompt(
            &self.model_label,
            garden_str.as_deref(),
            &selected,
            &self.annotations,
            &self.validation_issues,
        );
        self.last_copied_context = Some(prompt.clone());
        self.status_banner = Some("Copied AI context to clipboard".to_owned());
        prompt
    }

    /// Save a PNG capture of the current viewport to disk and update `status_banner`.
    pub fn capture_current_png(&mut self) {
        let [w, h] = self.backing_px;
        let w = w.max(640);
        let h = h.max(360);
        match self.renderer.render_png(w, h) {
            Ok(bytes) => {
                let target_path = if let Some(root) = &self.garden_root {
                    let ts = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs();
                    root.join("tmp")
                        .join("web_view")
                        .join("captures")
                        .join(format!("manual_{ts}.png"))
                } else if let Some(src) = &self.model_path {
                    let src_path = PathBuf::from(src);
                    let stem = src_path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("model");
                    src_path.with_file_name(format!("{stem}_capture.png"))
                } else {
                    std::env::temp_dir().join("lbt_rune_capture.png")
                };
                match write_bytes_atomic(&target_path, &bytes) {
                    Ok(()) => {
                        self.status_banner =
                            Some(format!("Saved capture: {}", target_path.display()));
                    }
                    Err(err) => {
                        self.status_banner = Some(format!("Capture write failed: {err}"));
                    }
                }
            }
            Err(err) => {
                self.status_banner = Some(format!("Capture failed: {err}"));
            }
        }
    }

    /// Parent room label for a given object record.
    pub fn parent_room_label(&self, rec: &ObjectRecord) -> Option<String> {
        find_parent_room(&self.scene, rec).map(|r| r.identifier.clone())
    }

    /// Apply a `PresentCommand` received from `<garden>/tmp/web_view/present.json`.
    pub fn apply_present_command(
        &mut self,
        cmd: &PresentCommand,
        load_model: impl FnOnce(&std::path::Path) -> Result<SceneData, String>,
    ) {
        self.present_revision = cmd.revision;
        if cmd.garden_id.is_some() {
            self.garden_id = cmd.garden_id.clone();
        }
        self.present_title = cmd.title.clone();
        self.present_note = cmd.note.clone();
        self.color_by = cmd.color_by;
        self.isolation_mode = cmd.isolation_mode;
        self.local_isolate = false;
        self.validation_issues = cmd.validation_issues.clone();
        self.callouts = cmd.callouts.clone();
        if let Some(sec) = &cmd.section {
            self.section = sec.clone();
        } else {
            self.section.enabled = false;
        }

        let mut model_reloaded = false;
        if let Some(watcher) = &self.watcher
            && let Ok(Some(resolved_path)) = watcher.resolve_model_path(cmd)
        {
            let should_reload = self.model_path.as_deref() != cmd.model_path.as_deref()
                || self.scene.is_empty();
            if should_reload {
                match load_model(&resolved_path) {
                    Ok(scene) => {
                        self.model_label = scene
                            .display_name
                            .clone()
                            .unwrap_or_else(|| scene.model_identifier.clone());
                        self.model_path = cmd.model_path.clone();
                        self.scene = scene;
                        model_reloaded = true;
                    }
                    Err(err) => {
                        self.status_banner = Some(format!("Model load error: {err}"));
                    }
                }
            }
        }

        if model_reloaded {
            self.rebuild_scene_derived(false);
        }

        self.highlight_ids = cmd
            .highlight_targets
            .iter()
            .filter_map(|t| self.scene.find_by_target(t).map(|r| r.object_id))
            .collect();

        self.sync_render_state();

        let hi_bounds = self.active_highlight_bounds();
        match &cmd.camera {
            CameraSpec::Preset(CameraPreset::Keep) => {
                if model_reloaded && self.scene.bounds.is_valid() {
                    self.renderer
                        .apply_camera_preset(CameraPreset::Axon, self.scene.bounds, hi_bounds);
                }
            }
            CameraSpec::Preset(preset) => {
                self.renderer
                    .apply_camera_preset(*preset, self.scene.bounds, hi_bounds);
            }
            CameraSpec::Pose(pose) => {
                self.renderer.apply_camera_pose(pose);
            }
        }

        self.render_viewport_now();
    }

    /// Answer a pending `capture_request.json` using the live renderer without corrupting the user's pose.
    pub fn answer_capture_request(&mut self, req: &CaptureRequest) {
        let saved_pose = self.renderer.camera_pose();
        let hi_bounds = self.active_highlight_bounds();
        if let Some(view) = &req.view {
            match view {
                CameraSpec::Preset(preset) => {
                    self.renderer
                        .apply_camera_preset(*preset, self.scene.bounds, hi_bounds);
                }
                CameraSpec::Pose(pose) => {
                    self.renderer.apply_camera_pose(pose);
                }
            }
        }

        let w = req.width.clamp(64, 4096);
        let h = req.height.clamp(64, 4096);
        let png_res = self.renderer.render_png(w, h);
        self.renderer.apply_camera_pose(&saved_pose);

        if let Some(watcher) = &mut self.watcher {
            match png_res {
                Ok(png_bytes) => {
                    let rev = (self.present_revision > 0).then_some(self.present_revision);
                    let _ = watcher.write_capture_result(
                        req,
                        &png_bytes,
                        w,
                        h,
                        self.model_path.clone(),
                        rev,
                    );
                }
                Err(err) => {
                    let _ = watcher.write_capture_error(req, err);
                }
            }
        }
    }

    /// Load existing `interaction_state.json` pins/selection/viewport when attaching a Garden.
    pub fn load_initial_interaction_state(&mut self) {
        let Some(bridge) = &self.bridge else {
            return;
        };
        if let Ok(Some(state)) = bridge.read_interaction_state() {
            if state.garden_id.is_some() {
                self.garden_id = state.garden_id;
            }
            self.annotations = state.annotations;
            self.selected_ids = state
                .selected_targets
                .iter()
                .filter_map(|t| self.scene.find_by_target(t).map(|r| r.object_id))
                .collect();
            self.sync_render_state();
        }
    }

    /// Atomically flush selection, annotations, and viewport snapshot to `interaction_state.json`.
    pub fn flush_interaction_state(&mut self) {
        self.camera_flush_due = None;
        let Some(bridge) = &self.bridge else {
            return;
        };
        let selected_targets: Vec<ObjectTargetRef> = self
            .selected_ids
            .iter()
            .filter_map(|&id| self.scene.object_by_id(id).map(|r| r.target.clone()))
            .collect();
        let viewport = ViewportSnapshot {
            model_path: self.model_path.clone(),
            color_by: Some(self.color_by),
            camera: Some(CameraSpec::Pose(self.renderer.camera_pose())),
            section: self.section.enabled.then(|| self.section.clone()),
        };
        let annotations = self.annotations.clone();
        let garden_id = self.garden_id.clone();

        let _ = bridge.update_interaction_state(|state| {
            if state.garden_id.is_none() {
                state.garden_id = garden_id;
            }
            state.selected_targets = selected_targets;
            state.annotations = annotations;
            state.viewport = Some(viewport);
        });
    }

    /// Resolve a `Callout`'s 3D world position from `world_point` or its target object's centroid.
    pub fn callout_world_point(&self, callout: &Callout) -> Option<[f32; 3]> {
        if let Some(pt) = callout.world_point {
            return Some(pt);
        }
        if let Some(target) = &callout.target
            && let Some(rec) = self.scene.find_by_target(target)
        {
            return Some(rec.centroid);
        }
        None
    }

    /// Resolve a `SpatialPin`'s 3D world position from `world_point` or its target object's centroid.
    pub fn pin_world_point(&self, pin: &SpatialPin) -> Option<[f32; 3]> {
        if let Some(pt) = pin.world_point {
            return Some(pt);
        }
        if let Some(target) = &pin.target
            && let Some(rec) = self.scene.find_by_target(target)
        {
            return Some(rec.centroid);
        }
        None
    }

    /// Return open spatial pins in stable order.
    pub fn open_pins(&self) -> Vec<&SpatialPin> {
        self.annotations
            .iter()
            .filter(|p| p.status == PinStatus::Open)
            .collect()
    }

    /// Stop background watcher (if any) and clear viewer PID in `interaction_state.json`.
    pub fn shutdown_garden(&mut self) {
        if let Some(flag) = self.garden_stop.take() {
            flag.store(true, Ordering::Relaxed);
        }
        if let Some(bridge) = &self.bridge {
            let _ = bridge.set_viewer_pid(None);
        }
    }
}

/// Ensure all `ObjectKind::Room` vs sub-object badges resolve nicely.
pub fn object_kind_label(kind: ObjectKind) -> &'static str {
    match kind {
        ObjectKind::Room => "Room",
        ObjectKind::Face => "Face",
        ObjectKind::Aperture => "Aperture",
        ObjectKind::Door => "Door",
        ObjectKind::Shade => "Shade",
    }
}
