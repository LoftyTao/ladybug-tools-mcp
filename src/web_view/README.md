# Web View (Rune 3D Viewer — Desktop & Browser WASM)

`web_view` provides Garden-backed 3D preview and bidirectional spatial coordination for both the native Rust/wgpu `lbt-rune-viewer` desktop application and its browser-native WASM build (WebGPU with automatic WebGL2 fallback).

Principles:

- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is a live viewport adapter, not a geometry or simulation source.
- Coordinate native desktop and browser viewers through atomic Garden-local protocol files under `<garden>/tmp/web_view/`:
  - `session.json` — active session state and step history
  - `present.json` — agent-to-viewer directive (`view_type`, `model_path`, `color_by`, `highlight_targets`, `isolation_mode`, `validation_issues`, `camera`, `section`, `callouts`)
  - `interaction_state.json` — viewer-to-agent spatial context (`selected_targets`, 3D `annotations`, `viewport`, `pending_intents`, `viewer_pid`)
  - `capture_request.json` and `captures/<request_id>.png` + `.json` — live viewport capture handshake and receipts
  - `models/<model>.hbjson` — preview `.hbjson` files converted on demand for Dragonfly models

Browser Web View (`web_view.server` + `rune_viewer/target/web/`):

- Build the WASM bundle (`index.html`, `app.js`, `app_bg.wasm`, `Inter-*.ttf`):
  - `python scripts/build_rune_web.py`
- Loopback HTTP server (`127.0.0.1`) serving the Rune Web View app alongside Garden API routes:
  - `GET /api/bootstrap` — initial Garden metadata, `present.json`, and `interaction_state.json`
  - `GET /api/status` — lightweight change-detection polling (`present_revision`, `present_mtime_ns`, `model_path`, `model_mtime_ns`)
  - `GET /api/present` — current `present.json`
  - `GET /api/interaction` / `POST /api/interaction` — read or atomically persist browser selection, spatial pins, and camera viewport
  - `GET /api/model?path=<rel>` — read contained `.hbjson`/`.json` model inside the Garden
  - `GET /api/session` — current `session.json`
- Standalone launch:
  - `python -m web_view.server --garden <garden_root> --port 8765 [--open]`
  - `python -m web_view.server --hbjson <model.hbjson> --port 8765 [--open]`

Supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

MCP tools and Code Mode workflow:

- `GD_Web_View_Start_Mode(garden_root, name="...", open_window=True, serve_web=True, web_port=None)` initializes `tmp/web_view/session.json`, seeds `tmp/web_view/present.json` from the Garden's base Honeybee or Dragonfly model, initializes `tmp/web_view/interaction_state.json`, starts the local browser HTTP server (`web_url`), and launches `lbt-rune-viewer --garden <garden_root>` when `open_window=True` and a GUI display is available.
- `GD_Web_View_Present` atomically updates `tmp/web_view/present.json` (with monotonic `revision`) to control view mode, active model, `color_by`, highlighted targets, isolation mode, validation issues, camera preset or explicit pose, section plane, and spatial callouts.
- `GD_Web_View_Get_Context` reads user selections, spatial annotation pins, viewport snapshot, and pending intents from `tmp/web_view/interaction_state.json`, and atomically resolves annotations when `resolve_annotations` is provided.
- `GD_Web_View_Capture` captures a verification PNG under `tmp/web_view/captures/` using a three-tier pipeline: live `lbt-rune-viewer` capture handshake first, headless `lbt-rune-viewer --snap` second, and offscreen VTK/matplotlib fallback third.
- In Code Mode, while Web View Mode is active for a Garden, Honeybee model/object edits, `HB_Validate_Model`, and Dragonfly model updates automatically flush `tmp/web_view/present.json` (coalesced per Garden per `execute` block, preserving camera pose on same-file updates). 2D chart `VisualizationSet` calls (`LB_Chart_To_Visualization_Set`) never hijack the 3D Rune viewport.
- `GD_Web_View_Stop_Mode(garden_root)` marks `session.json` inactive and stops any tracked `lbt-rune-viewer` process and local browser HTTP server while preserving protocol history under `tmp/web_view/`.

Boundaries:

- Protocol files, Dragonfly preview `.hbjson` caches, and captures under `tmp/web_view/` are local Web View state, not formal user-requested Garden artifacts.
- Formal durable deliverables (`html`, `svg`, `png`, `vtkjs`, `vtk`, `vtp`, `vsf`, `pkl`) remain explicitly exported via `LB_Export_Visualization_Set` (and composed via `LB_Compose_Visualization_Sets`).
