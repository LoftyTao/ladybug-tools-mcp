# Web View

`web_view` stores local preview coordination code for React + vtk.js views.

Principles:

- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `visualization_set_to_vtkjs`.
- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is a local preview adapter, not a geometry or simulation source.
- Keep the first path local-only and easy for MCP tools or agents to hand off through compact Garden paths.

First supported preview kinds:

- `base_honeybee_model`
- `base_dragonfly_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

Local viewer:

- `python -m web_view.local_viewer <file.vtkjs>` builds a static React + vtk.js preview workspace and serves it locally.
- `python -m web_view.local_viewer --garden-root <garden>` builds a live local preview workspace from the Garden Web View session. The browser follows the active preview step when `record_preview_step` points to a new Garden-registered `.vtkjs` artifact.
- Pass `--watch` to rebuild the local workspace when the source `.vtkjs` or optional HBJSON changes. The browser polls `config.json` and reloads the current native `.vtkjs` scene when the revision changes.
- In Garden mode, `--watch` monitors `garden.json`, `tmp/web_view/session.json`, and the active `.vtkjs` artifact, so an already-open browser can switch to new Agent-authored previews without manual refresh.
- When the active `.vtkjs` changes, the viewer preserves the current vtk.js camera state so user orbit/zoom context survives scene reloads.
- The browser keeps the same vtk.js render window across active `.vtkjs` changes and only replaces scene props, reducing canvas/interactor churn during live preview updates.
- `start_web_view_mode` / `stop_web_view_mode` expose Web View Mode to MCP. Starting the mode also starts the local viewer server and Garden watcher, returning a local URL for the host app to open. In Code Mode, when the mode is active for a Garden, significant Honeybee, Dragonfly, or Fairyfly model/object edits automatically export a session-managed `.vtkjs` preview under `tmp/web_view/previews/`, record it in `tmp/web_view/session.json`, and leave the original tool return value unchanged. Fairyfly authoring previews cover Shape/Boundary writes, and Fairyfly VisualizationSet result tools are recorded as `analysis_overlay` previews when they return a VisualizationSet body or target.
- If the requested viewer port is already occupied, startup fails with a clear error instead of switching ports or leaving the browser on an older Garden.
- Session-managed previews are local Web View state, not formal user-requested Garden artifacts. Explicit `visualization_set_to_vtkjs` still writes registered Garden artifacts.
- Pass `--model-path <model.hbjson>` only to copy the native Honeybee Model into the local preview workspace for metadata/context. The viewer does not generate a parallel properties sidecar or a custom property scene.
- Composite views must be produced before Web View: use `compose_visualization_sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `visualization_set_to_vtkjs` / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and any other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files. React only loads, reloads, and frames the `.vtkjs` package.
