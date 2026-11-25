//! Application state, `rune-kit` shell pane states, Room-first picking, SketchUp/OpenStudio
//! Room Edit Mode, bilingual i18n locale, Ladybug Legend toggle, and Garden protocol sync.

use std::collections::BTreeSet;
use std::path::PathBuf;
#[cfg(not(target_arch = "wasm32"))]
use std::sync::Arc;
#[cfg(not(target_arch = "wasm32"))]
use std::sync::atomic::{AtomicBool, Ordering};

#[cfg(not(target_arch = "wasm32"))]
use lbt_mcp_bridge::{GardenBridge, GardenWatcher};
#[cfg(not(target_arch = "wasm32"))]
use lbt_scene::CaptureRequest;
use lbt_scene::{
    Bounds3, Callout, CameraPose, CameraPreset, CameraSpec, ColorBy, IsolationMode, ObjectKind,
    ObjectRecord, ObjectTargetRef, PresentCommand, SceneData, SectionAxis, SectionSpec,
    SpatialPin, ValidationIssue, ViewportSnapshot,
};
use rune::Pixels;
use rune_kit::shell::PaneState;

use crate::engine::{
    CpuCameraBackend, SceneCameraBackend, ViewerPickHit, ViewerRenderState, ViewerRenderer,
};
use crate::i18n::{self, Locale};
use crate::outliner::{
    OutlinerTree, build_outliner, expand_render_ids, find_owner_room_id, find_parent_room,
};

/// Active toolbar overlay (`ColorBy` dropdown or `View` popover).
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum TopMenu {
    ColorBy,
    View,
}

/// Compute a lightweight `(byte_len, fnv1a_64)` fingerprint for detecting in-place model edits.
#[cfg(not(target_arch = "wasm32"))]
pub fn file_fingerprint(path: &std::path::Path) -> Option<(u64, u64)> {
    let bytes = std::fs::read(path).ok()?;
    let mut hash: u64 = 0xcbf29ce484222325;
    for &b in &bytes {
        hash ^= u64::from(b);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    Some((bytes.len() as u64, hash))
}

/// Complete viewer UI + 3D state driven by Rune and `rune-kit`.
pub struct ViewerState {
    pub locale: Locale,
    pub dark_mode: bool,
    pub sidebar_pane: PaneState,
    pub inspector_pane: PaneState,
    pub show_legend: bool,
    pub outliner_expanded: BTreeSet<String>,

    pub model_label: String,
    pub model_path: Option<String>,
    pub model_fingerprint: Option<(u64, u64)>,
    pub garden_root: Option<PathBuf>,
    pub garden_id: Option<String>,
    pub present_revision: u64,
    pub present_title: Option<String>,
    pub present_note: Option<String>,

    pub scene: SceneData,
    pub outliner: OutlinerTree,
    pub color_by: ColorBy,
    /// Preserved from `PresentCommand` for protocol compatibility; never forces display tints.
    pub isolation_mode: IsolationMode,
    pub show_edges: bool,

    /// SketchUp/OpenStudio-style Room Edit Mode active Room object ID (`None` = Model mode).
    pub editing_room_id: Option<u32>,
    pub selected_ids: Vec<u32>,
    /// Preserved for `FitHighlights` camera bounds; never forces geometry color overrides.
    pub highlight_ids: Vec<u32>,
    /// Preserved for Garden protocol compatibility; never rendered or color-tinted.
    pub validation_issues: Vec<ValidationIssue>,
    /// Preserved for Garden protocol compatibility; never rendered over the 3D viewport.
    pub callouts: Vec<Callout>,
    /// Preserved for lossless `interaction_state.json` round-trip; never rendered in UI.
    pub annotations: Vec<SpatialPin>,

    pub section: SectionSpec,
    pub open_menu: Option<TopMenu>,
    pub status_banner: Option<String>,

    pub viewport_pixels: Pixels,
    pub viewport_pts: [f32; 2],
    pub viewport_scale: f32,
    pub backing_px: [u32; 2],
    pub render_buf: Vec<u8>,
    pub render_dirty: bool,
    pub use_compositor: bool,
    pub scene_version: u64,
    pub web_connected: bool,
    pub renderer: Box<dyn ViewerRenderer>,

    pub drag_pan: bool,
    pub drag_prev_xy: [f32; 2],
    pub drag_start_pose: Option<CameraPose>,
    pub drag_moved: bool,

    #[cfg(not(target_arch = "wasm32"))]
    pub watcher: Option<GardenWatcher>,
    #[cfg(not(target_arch = "wasm32"))]
    pub bridge: Option<GardenBridge>,
    #[cfg(not(target_arch = "wasm32"))]
    pub garden_stop: Option<Arc<AtomicBool>>,
    pub camera_flush_due: Option<f64>,
}

impl ViewerState {
    /// Construct initial viewer state with an optional GPU renderer or CPU camera fallback.
    pub fn new(
        scene: SceneData,
        model_label: impl Into<String>,
        renderer: Option<Box<dyn ViewerRenderer>>,
    ) -> Self {
        let renderer = renderer.unwrap_or_else(|| Box::new(CpuCameraBackend::default()));
        let locale = Locale::EnUs;
        i18n::apply_rune_language(locale);
        let mut state = Self {
            locale,
            dark_mode: true,
            sidebar_pane: PaneState::new(260.0).range(190.0, 420.0),
            inspector_pane: PaneState::new(256.0).range(210.0, 380.0).collapsed(),
            show_legend: true,
            outliner_expanded: BTreeSet::new(),
            model_label: model_label.into(),
            model_path: scene.source_path.clone(),
            model_fingerprint: None,
            garden_root: None,
            garden_id: None,
            present_revision: 0,
            present_title: None,
            present_note: None,
            scene,
            outliner: OutlinerTree::default(),
            color_by: ColorBy::Type,
            isolation_mode: IsolationMode::Highlight,
            show_edges: true,
            editing_room_id: None,
            selected_ids: Vec::new(),
            highlight_ids: Vec::new(),
            validation_issues: Vec::new(),
            callouts: Vec::new(),
            annotations: Vec::new(),
            section: SectionSpec {
                enabled: false,
                axis: SectionAxis::Z,
                value: None,
                story: None,
                invert: false,
            },
            open_menu: None,
            status_banner: None,
            viewport_pixels: Pixels::new(),
            viewport_pts: [960.0, 680.0],
            viewport_scale: 1.0,
            backing_px: [960, 680],
            render_buf: Vec::new(),
            render_dirty: true,
            use_compositor: cfg!(target_arch = "wasm32"),
            scene_version: 1,
            web_connected: false,
            renderer,
            drag_pan: false,
            drag_prev_xy: [0.0, 0.0],
            drag_start_pose: None,
            drag_moved: false,
            #[cfg(not(target_arch = "wasm32"))]
            watcher: None,
            #[cfg(not(target_arch = "wasm32"))]
            bridge: None,
            #[cfg(not(target_arch = "wasm32"))]
            garden_stop: None,
            camera_flush_due: None,
        };
        state.rebuild_scene_derived(true);
        state.render_viewport_now();
        state
    }

    /// Construct a compositor-backed viewer state (used for browser WASM and desktop GUI).
    pub fn new_compositor(scene: SceneData, model_label: impl Into<String>) -> Self {
        let mut s = Self::new(scene, model_label, Some(Box::new(SceneCameraBackend::new())));
        s.use_compositor = true;
        s
    }

    /// Toggle a mutually-exclusive toolbar overlay (`ColorBy` dropdown or `View` popover).
    pub fn toggle_top_menu(&mut self, menu: TopMenu) {
        self.open_menu = if self.open_menu == Some(menu) {
            None
        } else {
            Some(menu)
        };
    }

    /// Close `menu` if it is currently open.
    pub fn close_top_menu(&mut self, menu: TopMenu) {
        if self.open_menu == Some(menu) {
            self.open_menu = None;
        }
    }

    /// Switch the UI locale and synchronize Rune's shaping language tag.
    pub fn set_locale(&mut self, locale: Locale) {
        self.locale = locale;
        i18n::apply_rune_language(locale);
    }

    /// Toggle between Chinese (`ZhCn`) and English (`EnUs`).
    pub fn toggle_locale(&mut self) {
        self.set_locale(self.locale.toggle());
    }

    /// Set Dark or Light theme and re-render the 3D viewport.
    pub fn set_dark_mode(&mut self, dark: bool) {
        if self.dark_mode != dark {
            self.dark_mode = dark;
            self.sync_render_state();
            self.render_viewport_now();
        }
    }

    /// Show or hide the Ladybug Tools 2D Legend.
    pub fn set_show_legend(&mut self, show: bool) {
        self.show_legend = show;
    }

    /// Toggle the docked Ladybug Tools Legend widget.
    pub fn toggle_legend(&mut self) {
        self.show_legend = !self.show_legend;
    }

    /// Show or hide wireframe edges and re-render.
    pub fn set_show_edges(&mut self, show: bool) {
        if self.show_edges != show {
            self.show_edges = show;
            self.sync_render_state();
            self.render_viewport_now();
        }
    }

    /// Return whether an outliner tree node key is expanded.
    pub fn is_node_expanded(&self, key: &str) -> bool {
        self.outliner_expanded.contains(key)
    }

    /// Toggle expansion of a schema tree node key.
    pub fn toggle_node_expanded(&mut self, key: &str) {
        if self.outliner_expanded.contains(key) {
            self.outliner_expanded.remove(key);
        } else {
            self.outliner_expanded.insert(key.to_owned());
        }
    }

    /// Expand the outliner path down to `room_id` (`Model -> Room`).
    pub fn expand_room_path(&mut self, room_id: u32) {
        self.outliner_expanded.insert("model".to_owned());
        self.outliner_expanded.insert(format!("room:{room_id}"));
    }

    /// Enter SketchUp/OpenStudio-style Room Edit Mode for `room_id`.
    pub fn enter_room_edit_mode(&mut self, room_id: u32) {
        let Some(room) = self.scene.object_by_id(room_id) else {
            return;
        };
        if room.kind != ObjectKind::Room {
            return;
        }
        self.open_menu = None;
        self.editing_room_id = Some(room_id);
        self.selected_ids = vec![room_id];
        self.inspector_pane.set_open(true);
        self.expand_room_path(room_id);
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Exit Room Edit Mode back to top-level Model mode cleanly.
    pub fn exit_room_edit_mode(&mut self) {
        if self.editing_room_id.take().is_some() {
            self.selected_ids.clear();
            self.inspector_pane.set_open(false);
            self.sync_render_state();
            self.render_viewport_now();
            self.flush_interaction_state();
        }
    }

    /// Active Room record when in Room Edit Mode, if any.
    pub fn editing_room(&self) -> Option<&ObjectRecord> {
        let rid = self.editing_room_id?;
        self.scene.object_by_id(rid)
    }

    /// Return `(min, max)` bounds along the given section axis, guaranteed finite with span >= 0.1m.
    pub fn section_axis_bounds(&self, axis: SectionAxis) -> (f32, f32) {
        if !self.scene.is_empty() && self.scene.bounds.is_valid() {
            let idx = match axis {
                SectionAxis::X => 0,
                SectionAxis::Y => 1,
                SectionAxis::Z => 2,
            };
            let lo = self.scene.bounds.min[idx];
            let hi = self.scene.bounds.max[idx];
            if lo.is_finite() && hi.is_finite() {
                if hi - lo >= 0.1 {
                    return (lo, hi);
                }
                return (lo - 0.5, hi + 0.5);
            }
        }
        (0.0, 10.0)
    }

    /// Active section cut position clamped to the current axis bounds.
    pub fn section_current_value(&self) -> f32 {
        let (lo, hi) = self.section_axis_bounds(self.section.axis);
        let fallback = ((lo + hi) * 0.5 * 10.0).round() / 10.0;
        self.section.value.unwrap_or(fallback).clamp(lo, hi)
    }

    /// Recompute outliner, default tree expansion, and section elevation after loading a scene.
    pub fn rebuild_scene_derived(&mut self, fit_camera: bool) {
        self.scene_version = self.scene_version.wrapping_add(1).max(1);
        if let Some(rid) = self.editing_room_id
            && self
                .scene
                .object_by_id(rid)
                .is_none_or(|r| r.kind != ObjectKind::Room)
        {
            self.editing_room_id = None;
        }
        self.outliner = build_outliner(&self.scene);
        self.outliner_expanded.clear();
        self.outliner_expanded.insert("model".to_owned());
        if let Some(first_room) = self.outliner.rooms.first() {
            self.outliner_expanded
                .insert(format!("room:{}", first_room.object_id));
        }
        if self.section.value.is_none()
            && !self.scene.is_empty()
            && self.scene.bounds.is_valid()
            && self.scene.bounds.diagonal() > 1e-4
        {
            let (lo, hi) = self.section_axis_bounds(self.section.axis);
            self.section.value = Some(((lo + hi) * 0.5 * 10.0).round() / 10.0);
        }
        self.renderer.set_scene(&self.scene);
        if fit_camera && !self.scene.is_empty() && self.scene.bounds.is_valid() {
            self.renderer
                .apply_camera_preset(CameraPreset::Axon, self.scene.bounds, None);
        }
        self.sync_render_state();
    }

    /// Build the normalized [`ViewerRenderState`] strictly preserving authentic Honeybee SDK colors.
    ///
    /// Never emits forced `validation_error_ids`, `validation_warning_ids`, or `highlighted_ids`
    /// color overrides; only user selection (`selected_ids`) and Room Edit Mode (`editing_room_id`)
    /// affect appearance.
    pub fn current_render_state(&self) -> ViewerRenderState {
        let selected_render = expand_render_ids(&self.scene, &self.selected_ids);
        let section = if self.section.enabled {
            Some(self.section.clone())
        } else {
            None
        };

        ViewerRenderState {
            color_by: self.color_by,
            selected_ids: selected_render,
            highlighted_ids: Vec::new(),
            isolation_mode: IsolationMode::Highlight,
            validation_error_ids: Vec::new(),
            validation_warning_ids: Vec::new(),
            section,
            dark_mode: self.dark_mode,
            show_edges: self.show_edges,
            editing_room_id: self.editing_room_id,
        }
    }

    /// Synchronize current selection, Room Edit Mode, display mode, and section into the renderer.
    pub fn sync_render_state(&mut self) {
        let rs = self.current_render_state();
        self.renderer.set_render_state(&rs);
        self.render_dirty = true;
    }

    /// Render the 3D scene immediately into `self.viewport_pixels` (or mark ready for compositor).
    pub fn render_viewport_now(&mut self) {
        if self.use_compositor {
            self.render_dirty = false;
            return;
        }
        let w = self.backing_px[0].clamp(1, 4096);
        let h = self.backing_px[1].clamp(1, 4096);
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
        let pw = (w_pts * scale).round().clamp(1.0, 4096.0) as u32;
        let ph = (h_pts * scale).round().clamp(1.0, 4096.0) as u32;
        let size_changed =
            (self.viewport_pts[0] - w_pts).abs() > 0.5 || (self.viewport_pts[1] - h_pts).abs() > 0.5;
        let backing_changed =
            self.backing_px != [pw, ph] || (self.viewport_scale - scale).abs() > 1e-3;
        self.viewport_pts = [w_pts.max(1.0), h_pts.max(1.0)];
        self.viewport_scale = scale;
        if backing_changed || size_changed || self.render_dirty {
            self.backing_px = [pw, ph];
            self.render_viewport_now();
        }
    }

    /// Bounds of currently highlighted or selected objects, if any (for `FitHighlights` camera framing).
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

    /// Select a single object (or toggle when `additive == true`), optionally focusing camera on it.
    pub fn select_object(&mut self, object_id: u32, additive: bool, focus_camera: bool) {
        if object_id == 0 || self.scene.object_by_id(object_id).is_none() {
            if !additive {
                self.selected_ids.clear();
                self.inspector_pane.set_open(false);
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
        self.inspector_pane.set_open(!self.selected_ids.is_empty());
        if focus_camera && !self.selected_ids.is_empty() {
            self.focus_on_object(object_id);
        }
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Focus camera target on `object_id`.
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

    /// Handle a single click on the 3D viewport at local logical coordinates `(lx, ly)`.
    ///
    /// Implements SketchUp/OpenStudio-style Room-first picking:
    /// - In Model mode (`editing_room_id == None`): hitting any Room geometry selects the owning
    ///   `Room` (`owner_room_id`); hitting orphaned geometry selects it directly.
    /// - In Room Edit Mode (`editing_room_id == Some(active_rid)`): hitting a child belonging to
    ///   `active_rid` selects that child (`Face`, `Aperture`, `Door`, `Shade`); hitting empty
    ///   background or outside `active_rid` exits Room Edit Mode cleanly.
    pub fn handle_viewport_click(&mut self, lx: f32, ly: f32, shift: bool) {
        self.open_menu = None;
        let scale = self.viewport_scale.max(1.0);
        let [pw, ph] = self.backing_px;
        let rs = self.current_render_state();
        let hit = self
            .renderer
            .pick_in_scene(&self.scene, &rs, lx * scale, ly * scale, pw, ph)
            .ok()
            .flatten()
            .filter(|h| h.object_id != 0);

        if let Some(active_rid) = self.editing_room_id {
            match hit {
                Some(ViewerPickHit { object_id, .. })
                    if find_owner_room_id(&self.scene, object_id) == Some(active_rid) =>
                {
                    self.select_object(object_id, shift, false);
                }
                _ => {
                    self.exit_room_edit_mode();
                }
            }
            return;
        }

        match hit {
            Some(ViewerPickHit { object_id, .. }) => {
                let target_id = find_owner_room_id(&self.scene, object_id).unwrap_or(object_id);
                self.select_object(target_id, shift, false);
            }
            None if !shift => {
                self.clear_selection();
            }
            None => {}
        }
    }

    /// Handle double-click in the 3D viewport: enter SketchUp/OpenStudio Room Edit Mode when
    /// double-clicking any Room geometry while in Model mode.
    pub fn handle_viewport_double_click(&mut self, lx: f32, ly: f32) {
        if self.editing_room_id.is_some() {
            return;
        }
        let scale = self.viewport_scale.max(1.0);
        let [pw, ph] = self.backing_px;
        let rs = self.current_render_state();
        let hit = self
            .renderer
            .pick_in_scene(&self.scene, &rs, lx * scale, ly * scale, pw, ph)
            .ok()
            .flatten()
            .filter(|h| h.object_id != 0);
        if let Some(hit) = hit
            && let Some(rid) = find_owner_room_id(&self.scene, hit.object_id)
        {
            self.enter_room_edit_mode(rid);
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

    /// Resolve a localized `Select` option label to `ColorBy` and apply it.
    pub fn set_color_by_label(&mut self, label: &str) {
        if let Some(mode) = i18n::parse_color_by_label(label) {
            self.set_color_by(mode);
        }
    }

    /// Apply a named camera preset and re-render.
    pub fn apply_camera_preset(&mut self, preset: CameraPreset) {
        let hi_bounds = self.active_highlight_bounds();
        self.renderer
            .apply_camera_preset(preset, self.scene.bounds, hi_bounds);
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Set perspective (`false`) or orthographic (`true`) projection and re-render.
    pub fn set_orthographic(&mut self, ortho: bool) {
        if self.renderer.is_orthographic() != ortho {
            self.renderer.set_orthographic(ortho);
            self.render_viewport_now();
            self.flush_interaction_state();
        }
    }

    /// Toggle perspective vs orthographic projection and re-render.
    pub fn toggle_orthographic(&mut self) {
        self.set_orthographic(!self.renderer.is_orthographic());
    }

    /// Toggle section plane enable/disable and re-render.
    pub fn toggle_section(&mut self) {
        self.section.enabled = !self.section.enabled;
        if self.section.enabled && self.section.value.is_none() {
            let (lo, hi) = self.section_axis_bounds(self.section.axis);
            self.section.value = Some(((lo + hi) * 0.5 * 10.0).round() / 10.0);
        }
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Switch section plane axis (`X`, `Y`, or `Z`) and center the cut position along that axis.
    pub fn set_section_axis(&mut self, axis: SectionAxis) {
        if self.section.axis != axis {
            self.section.axis = axis;
            let (lo, hi) = self.section_axis_bounds(axis);
            self.section.value = Some(((lo + hi) * 0.5 * 10.0).round() / 10.0);
            self.sync_render_state();
            self.render_viewport_now();
            self.flush_interaction_state();
        }
    }

    /// Set continuous section cut coordinate from slider drag (`commit == false`) or release (`commit == true`).
    pub fn set_section_value(&mut self, value: f32, commit: bool) {
        if !value.is_finite() {
            return;
        }
        let (lo, hi) = self.section_axis_bounds(self.section.axis);
        let snapped = ((value.clamp(lo, hi)) * 10.0).round() / 10.0;
        self.section.value = Some(snapped);
        self.section.enabled = true;
        self.sync_render_state();
        self.render_viewport_now();
        if commit {
            self.flush_interaction_state();
        }
    }

    /// Invert the clipped half-space of the active section plane.
    pub fn set_section_invert(&mut self, invert: bool) {
        if self.section.invert != invert {
            self.section.invert = invert;
            self.sync_render_state();
            self.render_viewport_now();
            self.flush_interaction_state();
        }
    }

    /// Clear current selection and auto-collapse the inspector pane.
    pub fn clear_selection(&mut self) {
        self.selected_ids.clear();
        self.inspector_pane.set_open(false);
        self.sync_render_state();
        self.render_viewport_now();
        self.flush_interaction_state();
    }

    /// Parent room label for a given object record.
    pub fn parent_room_label(&self, rec: &ObjectRecord) -> Option<String> {
        find_parent_room(&self.scene, rec).map(|r| {
            r.display_name
                .as_deref()
                .filter(|s| !s.trim().is_empty())
                .unwrap_or(&r.identifier)
                .to_owned()
        })
    }

    fn apply_present_non_model_fields(&mut self, cmd: &PresentCommand) {
        self.present_revision = cmd.revision;
        if cmd.garden_id.is_some() {
            self.garden_id = cmd.garden_id.clone();
        }
        self.present_title = cmd.title.clone();
        self.present_note = cmd.note.clone();
        self.color_by = cmd.color_by;
        self.isolation_mode = cmd.isolation_mode;
        self.validation_issues = cmd.validation_issues.clone();
        self.callouts = cmd.callouts.clone();
        if let Some(sec) = &cmd.section {
            self.section = sec.clone();
        } else {
            self.section.enabled = false;
        }
    }

    fn finish_present_camera_and_highlights(
        &mut self,
        cmd: Option<&PresentCommand>,
        model_reloaded: bool,
        was_empty: bool,
        path_changed: bool,
        preserve_restored_pose: bool,
    ) {
        if let Some(cmd) = cmd {
            self.highlight_ids = cmd
                .highlight_targets
                .iter()
                .filter_map(|t| self.scene.find_by_target(t).map(|r| r.object_id))
                .collect();
        }
        self.sync_render_state();

        let hi_bounds = self.active_highlight_bounds();
        let cam_spec = cmd
            .map(|c| &c.camera)
            .cloned()
            .unwrap_or_else(CameraSpec::keep);
        match cam_spec {
            CameraSpec::Preset(CameraPreset::Keep) => {
                if !preserve_restored_pose
                    && model_reloaded
                    && (was_empty || path_changed)
                    && !self.scene.is_empty()
                    && self.scene.bounds.is_valid()
                {
                    self.renderer
                        .apply_camera_preset(CameraPreset::Axon, self.scene.bounds, hi_bounds);
                }
            }
            CameraSpec::Preset(preset) => {
                self.renderer
                    .apply_camera_preset(preset, self.scene.bounds, hi_bounds);
            }
            CameraSpec::Pose(pose) => {
                self.renderer.apply_camera_pose(&pose);
            }
        }
        self.render_viewport_now();
    }

    /// Apply a scene & metadata update received over browser HTTP sync (`wasm32`).
    #[cfg(target_arch = "wasm32")]
    pub fn apply_web_scene_and_state(
        &mut self,
        next_scene: Option<SceneData>,
        next_model_path: Option<String>,
        present: Option<&PresentCommand>,
        initial_interaction: Option<&lbt_scene::InteractionState>,
    ) {
        if let Some(cmd) = present {
            self.apply_present_non_model_fields(cmd);
        }
        let was_empty = self.scene.is_empty();
        let path_changed = next_model_path.is_some()
            && self.model_path.as_deref() != next_model_path.as_deref();
        let mut model_reloaded = false;
        if let Some(scene) = next_scene {
            self.model_label = scene
                .display_name
                .clone()
                .unwrap_or_else(|| scene.model_identifier.clone());
            if let Some(rel) = next_model_path {
                self.model_path = Some(rel);
            }
            self.scene = scene;
            self.rebuild_scene_derived(false);
            model_reloaded = true;
        }
        let mut restored_pose = false;
        if let Some(state) = initial_interaction {
            if state.garden_id.is_some() {
                self.garden_id = state.garden_id.clone();
            }
            self.annotations = state.annotations.clone();
            self.selected_ids = state
                .selected_targets
                .iter()
                .filter_map(|t| self.scene.find_by_target(t).map(|r| r.object_id))
                .collect();
            self.inspector_pane.set_open(!self.selected_ids.is_empty());
            if present.is_none()
                && let Some(vp) = &state.viewport
            {
                if let Some(cb) = vp.color_by {
                    self.color_by = cb;
                }
                if let Some(sec) = &vp.section {
                    self.section = sec.clone();
                }
                if let Some(CameraSpec::Pose(pose)) = &vp.camera {
                    self.renderer.apply_camera_pose(pose);
                    restored_pose = true;
                }
            }
        }
        self.finish_present_camera_and_highlights(
            present,
            model_reloaded,
            was_empty,
            path_changed,
            restored_pose,
        );
    }

    /// Apply a `PresentCommand` received from `<garden>/tmp/web_view/present.json`.
    #[cfg(not(target_arch = "wasm32"))]
    pub fn apply_present_command(
        &mut self,
        cmd: &PresentCommand,
        load_model: impl FnOnce(&std::path::Path) -> Result<SceneData, String>,
    ) {
        self.apply_present_non_model_fields(cmd);

        let mut model_reloaded = false;
        let was_empty = self.scene.is_empty();
        let path_changed = self.model_path.as_deref() != cmd.model_path.as_deref();
        if let Some(watcher) = &self.watcher
            && let Ok(Some(resolved_path)) = watcher.resolve_model_path(cmd)
        {
            let next_fp = file_fingerprint(&resolved_path);
            let content_changed = next_fp.is_some() && next_fp != self.model_fingerprint;
            let should_reload = path_changed || content_changed || was_empty;
            if should_reload {
                match load_model(&resolved_path) {
                    Ok(scene) => {
                        self.model_label = scene
                            .display_name
                            .clone()
                            .unwrap_or_else(|| scene.model_identifier.clone());
                        self.model_path = cmd.model_path.clone();
                        self.model_fingerprint = next_fp;
                        self.scene = scene;
                        model_reloaded = true;
                    }
                    Err(err) => {
                        self.status_banner = Some(format!("Error: {err}"));
                    }
                }
            }
        }

        if model_reloaded {
            self.rebuild_scene_derived(false);
        }

        self.finish_present_camera_and_highlights(
            Some(cmd),
            model_reloaded,
            was_empty,
            path_changed,
            false,
        );
    }

    /// Answer a pending `capture_request.json` using the live renderer without corrupting the user's pose.
    #[cfg(not(target_arch = "wasm32"))]
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
        let rs = self.current_render_state();
        let png_res = self.renderer.render_scene_png(&self.scene, &rs, w, h);
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

    /// Load existing `interaction_state.json` selection/viewport when attaching a Garden.
    #[cfg(not(target_arch = "wasm32"))]
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
            self.inspector_pane.set_open(!self.selected_ids.is_empty());
            self.sync_render_state();
        }
    }

    /// Atomically flush selection and viewport snapshot to `interaction_state.json`
    /// (on desktop) or `POST /api/interaction` (in browser WASM).
    pub fn flush_interaction_state(&mut self) {
        self.camera_flush_due = None;
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

        #[cfg(not(target_arch = "wasm32"))]
        {
            let Some(bridge) = &self.bridge else {
                return;
            };
            let _ = bridge.update_interaction_state(|state| {
                if state.garden_id.is_none() {
                    state.garden_id = garden_id;
                }
                state.selected_targets = selected_targets;
                state.annotations = annotations;
                state.viewport = Some(viewport);
            });
        }

        #[cfg(target_arch = "wasm32")]
        {
            if self.web_connected {
                crate::web_sync::queue_interaction_post(
                    crate::web_sync::InteractionUpdatePayload {
                        garden_id,
                        selected_targets,
                        annotations,
                        viewport: Some(viewport),
                    },
                );
            }
        }
    }

    /// Stop background watcher (if any) and clear viewer PID in `interaction_state.json`.
    pub fn shutdown_garden(&mut self) {
        #[cfg(not(target_arch = "wasm32"))]
        {
            if let Some(flag) = self.garden_stop.take() {
                flag.store(true, Ordering::Relaxed);
            }
            if let Some(bridge) = &self.bridge {
                let _ = bridge.set_viewer_pid(None);
            }
        }
    }
}

/// Default English label helper for an `ObjectKind`.
pub fn object_kind_label(kind: ObjectKind) -> &'static str {
    i18n::object_kind_label(Locale::EnUs, kind)
}
