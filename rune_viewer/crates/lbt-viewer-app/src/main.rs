//! Native GPU desktop and headless HBJSON/Garden viewer powered by Rune and wgpu.

use lbt_mcp_bridge::GardenBridgeStub;
use lbt_renderer_wgpu::{RendererConfig, RendererStub};
use lbt_scene::{PROTOCOL_SCHEMA_VERSION, SceneData};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--version" || arg == "-V") {
        println!(
            "lbt-rune-viewer {} (protocol v{})",
            env!("CARGO_PKG_VERSION"),
            PROTOCOL_SCHEMA_VERSION
        );
        return;
    }

    let _gpu_desc = rune::describe_gpu;
    let _renderer = RendererStub::new(RendererConfig::default());
    let _scene = SceneData::default();
    let _bridge = GardenBridgeStub::new(".");
    println!(
        "lbt-rune-viewer skeleton (protocol v{}, rune gpu backend ready)",
        PROTOCOL_SCHEMA_VERSION
    );
}
