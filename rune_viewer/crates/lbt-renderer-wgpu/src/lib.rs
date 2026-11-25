//! wgpu 3D building renderer, embedded Rune compositor pipeline, ray picking, and offscreen PNG pipeline.

pub mod camera;
pub mod core;
pub mod embedded;
pub mod error;
pub mod palette;
pub mod raypick;
#[cfg(not(target_arch = "wasm32"))]
pub mod renderer;

pub use camera::OrbitCamera;
pub use core::{PickHit, RenderState};
pub use embedded::EmbeddedSceneRenderer;
pub use error::RendererError;
pub use palette::{color_for_object, color_for_object_in_scene, resolve_scene_colors};
pub use raypick::pick_scene_ray;
#[cfg(not(target_arch = "wasm32"))]
pub use renderer::BuildingRenderer;

use lbt_scene::{ColorBy, IsolationMode, SceneData};

/// Basic viewport dimensions and rendering options for [`RendererStub`].
#[derive(Clone, Debug, PartialEq)]
pub struct RendererConfig {
    pub width: u32,
    pub height: u32,
    pub color_by: ColorBy,
    pub isolation_mode: IsolationMode,
}

impl Default for RendererConfig {
    fn default() -> Self {
        Self {
            width: 1280,
            height: 720,
            color_by: ColorBy::Type,
            isolation_mode: IsolationMode::Highlight,
        }
    }
}

/// Legacy placeholder kept for pure-CPU metadata inspection in tests.
#[derive(Clone, Debug, Default)]
pub struct RendererStub {
    pub config: RendererConfig,
}

impl RendererStub {
    /// Create a new renderer stub with the given configuration.
    pub fn new(config: RendererConfig) -> Self {
        Self { config }
    }

    /// Inspect scene geometry counts without creating a GPU device yet.
    pub fn scene_summary(&self, scene: &SceneData) -> (usize, usize, usize) {
        (
            scene.vertices.len(),
            scene.indices.len(),
            scene.edge_vertices.len(),
        )
    }
}
