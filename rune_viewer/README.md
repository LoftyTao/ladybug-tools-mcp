# `rune_viewer` — Native GPU HBJSON & Garden Viewer

`rune_viewer` is the Rust/Rune/wgpu desktop and headless rendering workspace for **ladybug-tools-mcp**. It connects directly to Garden projects via `<garden>/tmp/web_view/` (`present.json`, `interaction_state.json`, `capture_request.json`, `captures/`) while rendering Honeybee `.hbjson` models with native GPU acceleration.

## Workspace Crates

- `crates/lbt-scene` — Shared GPU vertex formats (`MeshVertex`, `EdgeVertex`), `SceneData`, `ObjectRecord`, `ObjectTargetRef`, and snake_case Garden Web View protocol structs (`PresentCommand`, `InteractionState`, `CaptureRequest`, `CaptureReceipt`).
- `crates/lbt-renderer-wgpu` — `wgpu` 3D building geometry renderer, attribute coloring, section planes, GPU picking, and offscreen PNG capture.
- `crates/lbt-mcp-bridge` — Atomic reader/writer bridge for `<garden>/tmp/web_view/` synchronization.
- `crates/lbt-viewer-app` — `lbt-rune-viewer` binary integrating the Rune UI shell, 3D viewport, Garden watcher, and headless `--snap` capture mode.

## Vendored Rune Dependency

Rune is tracked as a git submodule at `../vendor/rune` (`branch = dev`, pinned commit `5d70a78dcaa141ee9e33f100caa79d86e7553754`).

Because Cargo only reads `[patch.crates-io]` and `[profile.*]` from the root workspace manifest, [`Cargo.toml`](Cargo.toml) mirrors:
- All eight `[patch.crates-io]` entries from `../vendor/rune/Cargo.toml` (`wgpu-hal`, `naga`, `winit`, `sctk-adwaita`, `parley_engine`, `accesskit_windows`, `accesskit_atspi_common`, `accesskit_macos`).
- `[profile.dev]` (`debug = "line-tables-only"`, `[profile.dev.package."*"] debug = false`) to keep Windows link memory usage low.
- OS-specific `wgpu` backend features in `crates/lbt-renderer-wgpu/Cargo.toml` (`dx12` on Windows, `metal` on Apple, `vulkan` elsewhere).

## Building & Checking

Run from `rune_viewer/`:

```powershell
cargo check --workspace
cargo test -p lbt-scene
cargo build -p lbt-viewer-app --bin lbt-rune-viewer
```
