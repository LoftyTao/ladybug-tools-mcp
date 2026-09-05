# Fairyfly Authoring

Use this when the user asks for Fairyfly, 2D heat-transfer model authoring, THERM package export, THERM run results, or Fairyfly VisualizationSets.

Status: Candidate, pending fresh natural Windows MCP acceptance.

## Preconditions

- Code Mode `search` must show Fairyfly tools are available.
- If Code Mode `search` does not show Fairyfly tools, stop and report that the path is unavailable; do not create an empty Garden and claim completion.
- THERM runtime tools may return `blocked` if the THERM executable is not configured; do not fake completion.
- Shape, Boundary, and Material objects live inside the Fairyfly model in this slice; they are not separate Garden resources.

## Candidate Model Authoring Route

1. `GD_create` if the Garden does not exist.
2. `FF_create_model` with `garden_root`, `identifier`, and usually `set_base=true`.
3. `FF_create_solid_material`; this returns an inline `object_dict`.
4. `FF_add_shape_to_model` with `vertices_2d` and `material: material["object_dict"]`.
5. `FF_add_boundary_to_model` with `line_segments_2d`, `temperature`, and `film_coefficient`.
6. `FF_validate_model`.
7. Optional preview: `FF_model_to_visualization_set` then a generic VisualizationSet exporter.
8. Confirm the base slot with `FF_get_base_model`.

## Code Mode Pattern

```python
model = await call_tool("FF_create_model", {
    "garden_root": garden_root,
    "identifier": "ff_model",
    "units": "Millimeters",
    "set_base": True
})
material = await call_tool("FF_create_solid_material", {
    "name": "Insulation",
    "conductivity": 0.04,
    "emissivity": 0.9
})
shape = await call_tool("FF_add_shape_to_model", {
    "garden_root": garden_root,
    "identifier": "wall_section",
    "vertices_2d": [[0, 0], [100, 0], [100, 50], [0, 50]],
    "material": material["object_dict"]
})
boundary = await call_tool("FF_add_boundary_to_model", {
    "garden_root": garden_root,
    "identifier": "indoor_air",
    "line_segments_2d": [[[0, 50], [100, 50]]],
    "temperature": 21,
    "film_coefficient": 8
})
validation = await call_tool("FF_validate_model", {"garden_root": garden_root})
```

## Geometry Rules

- `vertices_2d` is a closed or open list of `[x, y]` points. The service cleans optional duplicate or colinear vertices.
- `line_segments_2d` is a list of `[[x1, y1], [x2, y2]]` segment pairs.
- Continuous adjacent regions with the same material should be one Shape, including L-shaped polygons when geometry allows.
- Split Shapes only for different materials, embedded objects/voids, distinct boundary or tag requirements, or a documented THERM meshing issue.

## THERM Runtime Route

1. `FF_write_model_to_thmz`.
2. `FF_start_simulation` with the same `run_id`.
3. Poll with `FF_poll_simulation`.
4. Read compact result statistics with `FF_read_result`.
5. Read U-Factor with `FF_read_u_factor` when matching boundary tags exist.
6. Convert results with `FF_result_to_visualization_set` if visualization is requested.

```python
written = await call_tool("FF_write_model_to_thmz", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
started = await call_tool("FF_start_simulation", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
run = await call_tool("FF_poll_simulation", {
    "garden_root": garden_root,
    "run_id": "ff_therm"
})
```

## Success Criteria

- Model authoring returns a Fairyfly model target and passes validation.
- Preview calls return a `visualization_set_target`.
- THERM run status is completed before reading result summaries.
- U-Factor readers return data only when matching tags and results exist.

## Stop Conditions

- Do not call generic Honeybee or Dragonfly model-slot tools for Fairyfly.
- Do not add `garden_root` to `FF_create_solid_material`; it returns an inline dictionary.
- Do not invent U-Factor values if tags or completed THERM results are missing.
- THMZ artifacts and run records belong under `runs/fairyfly_therm/`; do not write test artifacts elsewhere.
