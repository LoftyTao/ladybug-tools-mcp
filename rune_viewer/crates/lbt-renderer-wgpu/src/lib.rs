//! wgpu 3D building renderer and offscreen PNG capture pipeline.

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

/// Placeholder renderer entry point until the wgpu pipeline is implemented.
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
