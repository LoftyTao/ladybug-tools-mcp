# Fairyfly Authoring Path

Status: Agent-verified with scaffolded Code Mode. Use this only when Code Mode `search` shows Fairyfly tools are available. They are registered only on Windows when the Fairyfly packages are importable. THERM runtime tools can still return `blocked` if the THERM executable is not configured.

Use this when the user explicitly asks for Fairyfly or two-dimensional heat-transfer model authoring. The verified path covers model authoring, validation, model-preview VisualizationSets, THMZ writing, THERM run ledgers, temperature statistics, U-Factor summaries, and THERM result VisualizationSets.

Core sequence inside one Code Mode `execute` block:

1. `create_garden` with `root_dir` if the Garden does not exist.
2. `create_fairyfly_model` with `garden_root`, `identifier`, and optionally `set_base=true`.
3. `create_fairyfly_solid_material` for an inline THERM `SolidMaterial` `object_dict`.
4. `add_fairyfly_shape_to_model` with `vertices_2d` and `material: material["object_dict"]`.
5. `add_fairyfly_boundary_to_model` with `line_segments_2d`, `temperature`, and `film_coefficient`.
6. `validate_fairyfly_model` with `garden_root`.
7. `fairyfly_model_to_visualization_set` with `return_visualization_set=false` when a compact target is enough.
8. `visualization_set_to_vtkjs`, `visualization_set_to_html`, or `visualization_set_to_svg` with the returned `visualization_set_target` when output is needed.
9. Confirm the split base slot with `get_base_fairyfly_model`.

THERM runtime sequence, after the model validates:

1. `write_fairyfly_model_to_thmz` with `garden_root` and optional `run_id`.
2. `start_fairyfly_therm_run` with the same `run_id`. Prefer this start/poll pattern; do not fake completion if the response is `blocked`.
3. `get_fairyfly_therm_run` to inspect the run ledger.
4. `read_fairyfly_therm_result` with `data_type="temperature"` or `"heat_flux"` for compact result statistics.
5. `read_fairyfly_u_factor_result` when boundaries include matching `u_factor_tag` values.
6. `fairyfly_therm_result_to_visualization_set` with `return_visualization_set=false`, then a generic VisualizationSet exporter such as `visualization_set_to_vtkjs`.

Do not call a mixed `get_base_model`, `set_base_model`, or `save_base_model` path. Fairyfly uses `base_fairyfly_model`, separate from `base_honeybee_model` and `base_dragonfly_model`.

Important boundaries:

- `create_fairyfly_solid_material` returns an inline `object_dict`; it does not take `garden_root` and does not save a target.
- Shape geometry is `vertices_2d`, a closed or open list of `[x, y]` points. The service cleans optional duplicate/colinear vertices and converts to Fairyfly SDK geometry at the boundary.
- Continuous adjacent regions with the same material should be authored as one Shape, including L-shaped or other non-rectangular polygons when geometry allows it. Do not split same-material geometry only for drawing convenience; split only for different materials, embedded objects/voids, distinct boundary/tag requirements, or a documented THERM meshing issue.
- Boundary geometry is `line_segments_2d`, a list of `[[x1, y1], [x2, y2]]` segment pairs.
- Shape, Boundary, and Material are not separate Garden resources in this slice; they live inside the saved Fairyfly model.
- If `search` cannot find Fairyfly tools, explain that the current platform or package setup does not enable Fairyfly tools instead of inventing fallback tools.
- U-Factor summaries need U-Factor tags on the relevant boundaries. If tags or completed THERM results are missing, result readers return `no_results` with a diagnostic rather than fake values.
- THMZ artifacts and THERM run records live under `runs/fairyfly_therm/`; compact result JSON and VisualizationSet artifacts are Garden artifacts.

Minimal Code Mode sketch:

```python
garden = await call_tool("create_garden", {"name": "Fairyfly Garden", "root_dir": garden_root})
model = await call_tool("create_fairyfly_model", {
    "garden_root": garden_root,
    "identifier": "ff_model",
    "units": "Millimeters",
    "set_base": True
})
material = await call_tool("create_fairyfly_solid_material", {
    "name": "Insulation",
    "conductivity": 0.04,
    "emissivity": 0.9
})
shape = await call_tool("add_fairyfly_shape_to_model", {
    "garden_root": garden_root,
    "identifier": "wall_section",
    "vertices_2d": [[0, 0], [100, 0], [100, 50], [0, 50]],
    "material": material["object_dict"]
})
boundary = await call_tool("add_fairyfly_boundary_to_model", {
    "garden_root": garden_root,
    "identifier": "indoor_air",
    "line_segments_2d": [[[0, 50], [100, 50]]],
    "temperature": 21,
    "film_coefficient": 8
})
validation = await call_tool("validate_fairyfly_model", {"garden_root": garden_root})
vis = await call_tool("fairyfly_model_to_visualization_set", {
    "garden_root": garden_root,
    "return_visualization_set": False
})
vtkjs = await call_tool("visualization_set_to_vtkjs", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "ff_model_preview"
})
base = await call_tool("get_base_fairyfly_model", {"garden_root": garden_root})
{
    "model": model["model_target"],
    "validation": validation["summary_view"],
    "vtkjs": vtkjs["artifact_receipt"],
    "base": base["object_dict"]
}
```

Minimal THERM result sketch:

```python
written = await call_tool("write_fairyfly_model_to_thmz", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
started = await call_tool("start_fairyfly_therm_run", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
run = await call_tool("get_fairyfly_therm_run", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
temperature = await call_tool("read_fairyfly_therm_result", {
    "garden_root": garden_root,
    "run_id": "ff_therm",
    "data_type": "temperature"
})
u_factor = await call_tool("read_fairyfly_u_factor_result", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
vis = await call_tool("fairyfly_therm_result_to_visualization_set", {
    "garden_root": garden_root,
    "run_id": "ff_therm",
    "data_type": "temperature",
    "return_visualization_set": False
})
vtkjs = await call_tool("visualization_set_to_vtkjs", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "ff_therm_temperature"
})
{
    "status": run["summary_view"]["status"],
    "temperature": temperature["summary_view"],
    "u_factor": u_factor["summary_view"],
    "vtkjs": vtkjs["artifact_receipt"]
}
```
