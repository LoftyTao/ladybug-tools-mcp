# Web View

`web_view` stores local preview coordination code for React + vtk.js views.

Principles:

- Use Ladybug Tools SDK and Ladybug Tools MCP native artifacts first, especially Garden-registered `.vtkjs` files from `visualization_set_to_vtkjs`.
- Keep model and analysis truth in Garden files, run ledgers, and artifact receipts. The Web View layer is a local preview adapter, not a geometry or simulation source.
- Keep the first path local-only and easy for MCP tools or agents to hand off through compact Garden paths.

First supported preview kinds:

- `base_model`
- `object_edit`
- `search_highlight`
- `analysis_overlay`

Local viewer:

- `python -m web_view.local_viewer <file.vtkjs>` builds a static React + vtk.js preview workspace and serves it locally.
- Pass `--watch` to rebuild the local workspace when the source `.vtkjs` or optional HBJSON changes. The browser polls `config.json` and reloads the current native `.vtkjs` scene when the revision changes.
- Pass `--model-path <model.hbjson>` only to copy the native Honeybee Model into the local preview workspace for metadata/context. The viewer does not generate a parallel properties sidecar or a custom property scene.
- Composite views must be produced before Web View: use `compose_visualization_sets` or SDK `VisualizationSet.add_vis_set`, then export the composed result with `visualization_set_to_vtkjs` / `VisualizationSet.to_vtkjs`.
- Color Room, Color Face, 2D legend parameters, and any other visual effects belong inside SDK/MCP-generated VisualizationSet `.vtkjs` files. React only loads, reloads, and frames the `.vtkjs` package.
