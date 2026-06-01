# Web View

`web_view` stores Garden-backed preview coordination for the FastMCP Custom HTML App vtk.js viewer.

Principles:

- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `visualization_set_to_vtkjs`.
- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is an App preview adapter, not a geometry or simulation source.
- Keep the preview local to the Garden and MCP host. Users should not need a project-local Node, npm, or React runtime for this path.

First supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

FastMCP App viewer:

- `web_view_start_mode` is the model-visible App entry. It starts or refreshes `tmp/web_view/session.json` and returns the App resource URI for the host.
- If the host does not advertise the MCP Apps UI extension, `web_view_start_mode` also starts a local-only fallback URL bound to `127.0.0.1`. That fallback serves the same Garden session state and `.vtkjs` payloads through a tiny Python HTTP server; it does not restore the old React, npm, or Node viewer runtime.
- `web_view_preview_state` and `web_view_preview_artifact` are App-only backend tools. They are hidden from normal Code Mode discovery but are reachable through FastMCP App routing.
- In Code Mode, when the mode is active for a Garden, significant Honeybee, Dragonfly, Fairyfly, or VisualizationSet operations automatically export a session-managed `.vtkjs` preview under `tmp/web_view/previews/`, record it in `tmp/web_view/session.json`, and leave the original tool return value unchanged.
- The App polls preview state, loads the active `.vtkjs` payload through MCP, and preserves camera state when the scene revision changes.
- `web_view_stop_mode` marks the session inactive so automatic preview exports stop, and closes the local fallback URL if one was started.

Boundaries:

- Session-managed previews are local Web View state, not formal user-requested Garden artifacts. Explicit `visualization_set_to_vtkjs` still writes registered Garden artifacts.
- Composite views must be produced before Web View: use `compose_visualization_sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `visualization_set_to_vtkjs` / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files. The App only loads, reloads, and frames the `.vtkjs` package.
