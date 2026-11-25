//! Real `lbt_scene` + `lbt_renderer_wgpu` backend for standalone `--mcp` stdio mode.

use std::collections::BTreeMap;
use std::path::Path;

use lbt_renderer_wgpu::{BuildingRenderer, RenderState};
use lbt_scene::{
    CameraPose, CameraPreset, CameraSpec, ColorBy, ObjectKind, SceneData, SectionAxis, SectionSpec,
    load_hbjson_file,
};
use serde_json::{Value, json};

use crate::mcp_server::{
    McpCaptureOptions, McpCapturedPng, McpSceneSummary, McpServer, McpViewerBackend,
};

/// Standalone offscreen MCP viewer backend powered by [`lbt_scene`] and [`BuildingRenderer`].
pub struct WgpuMcpBackend {
    renderer: Option<BuildingRenderer>,
    scene: Option<SceneData>,
    render_state: RenderState,
    camera_spec: CameraSpec,
    camera_dirty: bool,
    scene_dirty: bool,
}

impl Default for WgpuMcpBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl WgpuMcpBackend {
    /// Construct an empty standalone MCP backend (GPU device initialized lazily on first capture).
    pub fn new() -> Self {
        Self {
            renderer: None,
            scene: None,
            render_state: RenderState::default(),
            camera_spec: CameraSpec::Preset(CameraPreset::Axon),
            camera_dirty: true,
            scene_dirty: false,
        }
    }

    /// Construct a standalone MCP backend and preload `hbjson_path` if provided.
    pub fn with_hbjson(hbjson_path: Option<&Path>) -> Result<Self, String> {
        let mut backend = Self::new();
        if let Some(path) = hbjson_path {
            backend.load_hbjson(path)?;
        }
        Ok(backend)
    }

    fn ensure_renderer_synced(&mut self) -> Result<&mut BuildingRenderer, String> {
        if self.renderer.is_none() {
            let renderer = BuildingRenderer::new().map_err(|err| format!("GPU init failed: {err}"))?;
            self.renderer = Some(renderer);
            self.scene_dirty = self.scene.is_some();
            self.camera_dirty = true;
        }
        let renderer = self.renderer.as_mut().expect("renderer initialized");
        if self.scene_dirty {
            if let Some(ref scene) = self.scene {
                renderer.set_scene(scene);
            }
            self.scene_dirty = false;
        }
        renderer.set_render_state(&self.render_state);
        if self.camera_dirty {
            if let Some(ref scene) = self.scene {
                apply_camera_spec(renderer.camera_mut(), &self.camera_spec, scene);
            }
            self.camera_dirty = false;
        }
        Ok(renderer)
    }
}

impl McpViewerBackend for WgpuMcpBackend {
    fn load_hbjson(&mut self, path: &Path) -> Result<McpSceneSummary, String> {
        let scene = load_hbjson_file(path, None).map_err(|err| format!("Failed to load HBJSON: {err}"))?;
        let summary = McpSceneSummary {
            model_identifier: scene.model_identifier.clone(),
            source_path: scene.source_path.clone(),
            units: scene.units.clone(),
            object_count: scene.objects.len(),
            vertex_count: scene.vertices.len(),
            edge_vertex_count: scene.edge_vertices.len(),
            bounds_min: scene.bounds.min,
            bounds_max: scene.bounds.max,
            stories: scene.stories.clone(),
        };
        self.scene = Some(scene);
        self.scene_dirty = true;
        self.camera_dirty = true;
        Ok(summary)
    }

    fn inspect_scene(&self) -> Result<Value, String> {
        let scene = self
            .scene
            .as_ref()
            .ok_or_else(|| "No HBJSON scene is currently loaded.".to_owned())?;
        let mut counts: BTreeMap<&'static str, usize> = BTreeMap::new();
        for obj in &scene.objects {
            *counts.entry(obj.kind.as_str()).or_insert(0) += 1;
        }
        Ok(json!({
            "model_identifier": scene.model_identifier,
            "display_name": scene.display_name,
            "source_path": scene.source_path,
            "units": scene.units,
            "bounds": scene.bounds,
            "stories": scene.stories,
            "counts": {
                "rooms": counts.get(ObjectKind::Room.as_str()).copied().unwrap_or(0),
                "faces": counts.get(ObjectKind::Face.as_str()).copied().unwrap_or(0),
                "apertures": counts.get(ObjectKind::Aperture.as_str()).copied().unwrap_or(0),
                "doors": counts.get(ObjectKind::Door.as_str()).copied().unwrap_or(0),
                "shades": counts.get(ObjectKind::Shade.as_str()).copied().unwrap_or(0),
            },
            "color_by": self.render_state.color_by.as_str(),
            "section": self.render_state.section,
            "camera": self.camera_spec,
        }))
    }

    fn set_view_state(&mut self, opts: &McpCaptureOptions) -> Result<Value, String> {
        if let Some(ref raw_color_by) = opts.color_by {
            self.render_state.color_by = parse_color_by(raw_color_by)?;
        }
        if let Some(z) = opts.section_z {
            self.render_state.section = Some(SectionSpec {
                enabled: true,
                axis: SectionAxis::Z,
                value: Some(z),
                story: None,
                invert: false,
            });
        }
        if let Some(ref view_val) = opts.view {
            self.camera_spec = parse_camera_spec(view_val)?;
            self.camera_dirty = true;
        }
        Ok(json!({
            "status": "ok",
            "color_by": self.render_state.color_by.as_str(),
            "section": self.render_state.section,
            "camera": self.camera_spec,
        }))
    }

    fn capture_png(&mut self, opts: &McpCaptureOptions) -> Result<McpCapturedPng, String> {
        if self.scene.is_none() {
            return Err("No HBJSON scene loaded; call viewer_load_hbjson first.".to_owned());
        }
        self.set_view_state(opts)?;
        let width = opts.width.unwrap_or(1280).clamp(64, 4096);
        let height = opts.height.unwrap_or(720).clamp(64, 4096);
        let color_by_label = self.render_state.color_by.as_str().to_owned();
        let view_label = camera_label(&self.camera_spec);

        let renderer = self.ensure_renderer_synced()?;
        let png_bytes = renderer
            .render_png(width, height)
            .map_err(|err| format!("Offscreen PNG render failed: {err}"))?;

        Ok(McpCapturedPng {
            png_bytes,
            width,
            height,
            view_label,
            color_by: color_by_label,
        })
    }
}

/// Launch the standalone stdio JSON-RPC MCP server backed by `lbt_scene` + `BuildingRenderer`.
pub fn run_default_mcp_stdio(initial_hbjson: Option<&Path>) -> Result<(), String> {
    let backend = WgpuMcpBackend::with_hbjson(initial_hbjson)?;
    let mut server = McpServer::new(backend);
    server
        .serve_stdio()
        .map_err(|err| format!("MCP stdio I/O failed: {err}"))
}

fn parse_color_by(raw: &str) -> Result<ColorBy, String> {
    match raw.trim().to_ascii_lowercase().as_str() {
        "type" => Ok(ColorBy::Type),
        "boundary_condition" | "bc" => Ok(ColorBy::BoundaryCondition),
        "story" => Ok(ColorBy::Story),
        "zone" => Ok(ColorBy::Zone),
        "program_type" | "program" => Ok(ColorBy::ProgramType),
        "construction_set" | "construction" => Ok(ColorBy::ConstructionSet),
        "hvac" => Ok(ColorBy::Hvac),
        other => Err(format!("Unsupported color_by mode: {other:?}")),
    }
}

fn parse_camera_spec(val: &Value) -> Result<CameraSpec, String> {
    if let Some(s) = val.as_str() {
        let preset = match s.trim().to_ascii_lowercase().as_str() {
            "keep" => CameraPreset::Keep,
            "fit" => CameraPreset::Fit,
            "fit_highlights" => CameraPreset::FitHighlights,
            "axon" | "ne" | "nw" | "se" | "sw" => CameraPreset::Axon,
            "top" => CameraPreset::Top,
            "north" | "back" => CameraPreset::North,
            "south" | "front" => CameraPreset::South,
            "east" | "right" => CameraPreset::East,
            "west" | "left" => CameraPreset::West,
            other => return Err(format!("Unsupported camera preset: {other:?}")),
        };
        return Ok(CameraSpec::Preset(preset));
    }
    serde_json::from_value::<CameraPose>(val.clone())
        .map(CameraSpec::Pose)
        .map_err(|err| format!("Invalid camera specification: {err}"))
}

fn camera_label(spec: &CameraSpec) -> String {
    match spec {
        CameraSpec::Preset(p) => p.as_str().to_owned(),
        CameraSpec::Pose(_) => "custom_pose".to_owned(),
    }
}

fn apply_camera_spec(camera: &mut lbt_renderer_wgpu::OrbitCamera, spec: &CameraSpec, scene: &SceneData) {
    match spec {
        CameraSpec::Preset(preset) => {
            let effective = match preset {
                CameraPreset::Keep => CameraPreset::Fit,
                other => *other,
            };
            camera.apply_preset(effective, scene.bounds, None);
        }
        CameraSpec::Pose(pose) => camera.apply_pose(pose),
    }
}
