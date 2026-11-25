# Web View

`web_view` stores Garden-backed preview coordination for both the native `lbt-rune-viewer` 3D viewport protocol and the local offline vtk.js sidebar workbench.

Principles:

- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is an App preview adapter, not a geometry or simulation source.
- Coordinate the native Rune 3D viewer through atomic Garden-local protocol files under `tmp/web_view/` (`present.json`, `interaction_state.json`, `capture_request.json`, and `captures/<id>.png` + `.json`).
- Keep the web fallback local and fully offline: bundle `vtk.js` locally in `src/web_view/vendor/vtk.js` and serve it at `/vendor/vtk.js` with no external CDN, Node, npm, or React runtime dependency.
- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `LB_Export_Visualization_Set` (`export_format="vtkjs"`).

First supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

MCP tools and local workbenches:

- `GD_Web_View_Start_Mode` starts or refreshes `tmp/web_view/session.json`, populates `tmp/web_view/present.json` from the Garden's base Honeybee model if present, optionally opens `lbt-rune-viewer`, and (in `web` or default `auto` fallback mode) returns a local-only URL bound to `127.0.0.1`. Omit `port` (`None`) for an ephemeral port (`0`), or pass an explicit `port` (raising a port conflict error if already occupied).
- `GD_Web_View_Present` atomically updates `tmp/web_view/present.json` (with monotonic `revision`) to direct view type, model target, `color_by`, highlighted targets, isolation mode, validation issues, camera, section plane, and callouts.
- `GD_Web_View_Get_Context` reads `tmp/web_view/interaction_state.json` (`selected_targets`, spatial `annotations`, `viewport`, `pending_intents`) and atomically resolves annotations when `resolve_annotations` is provided.
- `GD_Web_View_Capture` captures a PNG under `tmp/web_view/captures/` using the live Rune viewer capture handshake first, headless `lbt-rune-viewer --snap` second, and offscreen VTK rendering third.
- In Code Mode, when the mode is active for a Garden, Honeybee model edits update `tmp/web_view/present.json` with changed targets (without triggering `.vtkjs` exports when Rune is active), active web sessions record session-managed `.vtkjs` previews under `tmp/web_view/previews/`, and 2D chart `VisualizationSet`s (`LB_Chart_To_Visualization_Set`) are never converted to 3D `.vtkjs` previews.
- The web workbench polls preview state every 1.5 seconds, renders `.vtkjs` payloads offline with `/vendor/vtk.js`, preserves camera state across revisions, and provides a `steps[]` timeline scrubber, actor/layer visibility toggles, standard view camera buttons (`Ax`, `Top`, `Front`, `Back`, `Left`, `Right`, `Fit`), a 2D colorbar/legend overlay, and an HTML/SVG artifact preview tab (`/api/document`).
- `GD_Web_View_Stop_Mode` marks the session inactive so automatic preview exports stop, closes any local fallback URL, and stops any tracked Rune viewer process.

Boundaries:

- Session-managed previews and captures under `tmp/web_view/` are local Web View state, not formal user-requested Garden artifacts. Explicit `LB_Export_Visualization_Set` (`export_format="vtkjs"`) still writes registered Garden artifacts.
- Composite views must be produced before Web View: use `LB_Compose_Visualization_Sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `LB_Export_Visualization_Set` (`export_format="vtkjs"`) / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files or `GD_Web_View_Present` directives.
