# Web View

`web_view` stores Garden-backed preview coordination for the local vtk.js sidebar viewer.

Principles:

- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `LB_Set_To_VTKJS`.
- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is an App preview adapter, not a geometry or simulation source.
- Keep the preview local to the Garden and MCP host. Users should not need a project-local Node, npm, or React runtime for this path.

First supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

Local sidebar viewer:

- `GD_Web_View_Start_Mode` starts or refreshes `tmp/web_view/session.json` and returns a local-only URL bound to `127.0.0.1` for the host sidebar.
- In Code Mode, when the mode is active for a Garden, significant Honeybee, Dragonfly, Fairyfly, or VisualizationSet operations automatically export a session-managed `.vtkjs` preview under `tmp/web_view/previews/`, record it in `tmp/web_view/session.json`, and leave the original tool return value unchanged.
- The viewer polls preview state every 1.5 seconds, loads the active `.vtkjs` payload, and preserves camera state when the scene revision changes.
- `GD_Web_View_Stop_Mode` marks the session inactive so automatic preview exports stop, and closes the local fallback URL if one was started.

Boundaries:

- Session-managed previews are local Web View state, not formal user-requested Garden artifacts. Explicit `LB_Set_To_VTKJS` still writes registered Garden artifacts.
- Composite views must be produced before Web View: use `LB_Compose_Visualization_Sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `LB_Set_To_VTKJS` / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files. The App only loads, reloads, and frames the `.vtkjs` package.
