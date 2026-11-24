# Web View

`web_view` stores Garden-backed preview coordination for the local offline vtk.js sidebar workbench.

Principles:

- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `LB_Export_Visualization_Set` (`export_format="vtkjs"`).
- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is an App preview adapter, not a geometry or simulation source.
- Keep the preview local and fully offline: bundle `vtk.js` locally in `src/web_view/vendor/vtk.js` and serve it at `/vendor/vtk.js` with no external CDN, Node, npm, or React runtime dependency.

First supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

Local sidebar workbench:

- `GD_Web_View_Start_Mode` starts or refreshes `tmp/web_view/session.json` and returns a local-only URL bound to `127.0.0.1`. Omit `port` (`None`) for an ephemeral port (`0`), or pass an explicit `port` (raising a port conflict error if already occupied).
- In Code Mode, when the mode is active for a Garden, significant Honeybee, Dragonfly, Fairyfly, or VisualizationSet operations automatically export a session-managed `.vtkjs` preview under `tmp/web_view/previews/`, record it in `tmp/web_view/session.json`, and leave the original tool return value unchanged (offloaded via `asyncio.to_thread`).
- The workbench polls preview state every 1.5 seconds, renders `.vtkjs` payloads offline with `/vendor/vtk.js`, preserves camera state across revisions, and provides a `steps[]` timeline scrubber, actor/layer visibility toggles, standard view camera buttons (`Ax`, `Top`, `Front`, `Back`, `Left`, `Right`, `Fit`), a 2D colorbar/legend overlay, and an HTML/SVG artifact preview tab (`/api/document`).
- `GD_Web_View_Stop_Mode` marks the session inactive so automatic preview exports stop, and closes the local fallback URL if one was started.

Boundaries:

- Session-managed previews are local Web View state, not formal user-requested Garden artifacts. Explicit `LB_Export_Visualization_Set` (`export_format="vtkjs"`) still writes registered Garden artifacts.
- Composite views must be produced before Web View: use `LB_Compose_Visualization_Sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `LB_Export_Visualization_Set` (`export_format="vtkjs"`) / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files. The App only loads, reloads, and frames the `.vtkjs` package.
