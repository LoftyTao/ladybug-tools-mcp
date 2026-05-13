# Create Radiance Sensor Grid / View

Agent-verified Code Mode path for creating Honeybee Radiance SensorGrid and View assets in a Garden.

Use this path when the user asks for daylight sensors, workplane test points, Radiance `.pts` files, camera/view setup, `.vf` files, rpict views, glare views, or pre-steps before Radiance recipes.

## Tool Choice

- Sensor grid from explicit points: `create_radiance_sensor_grid`
  - Use `positions` plus one shared `direction` for ordinary workplanes.
  - Use `positions` plus `directions` when each sensor has its own direction.
- Sensor grid from a Honeybee object surface: `create_radiance_sensor_grid_from_object`
  - Use `object_target`, `shade_target`, or `surface_target` from `search_honeybee_model_objects` or a create result.
  - Use this for irradiance-style sensors on shades, PV panels, apertures, doors, or faces.
  - Do not pass a shade target to `create_radiance_sensor_grid.host_target`; that parameter remains a model attachment alias.
- View from explicit camera vectors: `create_radiance_view`
  - Use `position`, `direction`, `up_vector`, `view_type`, `h_size`, and `v_size`.
  - Radiance view types include `v`, `h`, `l`, `c`, `a`, and `s`; Radiance CLI tokens such as `vtv` / `vtc` and natural perspective hints such as `perspective` / `vterrain` are accepted.

## Main Path

```python
model = await call_tool("create_honeybee_model", {
    "garden_root": garden_root,
    "identifier": "radiance_model",
})
grid = await call_tool("create_radiance_sensor_grid", {
    "garden_root": garden_root,
    "identifier": "workplane_grid",
    "positions": [[0, 0, 0.8], [1, 0, 0.8]],
    "direction": [0, 0, 1],
    "model_target": model["target"],
    "attach_to_model": True,
    "return_object_dict": False,
})
view = await call_tool("create_radiance_view", {
    "garden_root": garden_root,
    "identifier": "north_view",
    "position": [0, -5, 1.5],
    "direction": [0, 1, 0],
    "up_vector": [0, 0, 1],
    "view_type": "v",
    "h_size": 60,
    "v_size": 45,
    "model_target": model["target"],
    "attach_to_model": True,
    "return_object_dict": False,
})
```

Object-hosted shade grid:

```python
shade_grid = await call_tool("create_radiance_sensor_grid_from_object", {
    "garden_root": garden_root,
    "identifier": "shade_irradiance_grid",
    "object_target": shade["target"],
    "grid_spacing": 0.5,
    "offset": 0.01,
    "model_target": model["target"],
    "attach_to_model": True,
    "return_object_dict": False,
})
```

## Boundaries

- With `garden_root`, sensor grids create `radiance_sensor_grid` targets and `.pts` artifacts.
- With `garden_root`, views create `radiance_view` targets and `.vf` artifacts.
- Set `attach_to_model=true` when the asset should be included in the Honeybee model Radiance properties for later recipe execution. Passing `model_target` or `host_target` is treated as an attach intent by the Agent-facing tools.
- `create_radiance_sensor_grid_from_object` samples Face3D-backed Honeybee objects. It is suitable for surface irradiance/radiation style studies on shades and PV panels; it is not the same assumption as an indoor workplane illuminance grid.
- Deterministic-pass/candidate: object-hosted SensorGrids now preserve the SDK `SensorGrid.mesh` when attached to a model, so downstream Radiance grid result VisualizationSets can render surface mesh color instead of falling back to point coloring.
- Natural output folders such as `radiance/sensorgrids` and `radiance/views` are normalized to `artifacts/radiance/sensors` and `artifacts/radiance/views`.
- For a quick rectangular grid, `x_count` / `y_count` can stand alone and imply 1 model-unit spacing; provide `x_dim` / `y_dim` for explicit dimensions.
- These tools create setup assets only. They do not run Radiance binaries, build octrees, render images, or calculate daylight metrics; use `reference/run-radiance-simulation.md` for the deterministic-pass start/poll path.
- For compact Agent handoff, pass targets and `summary_view`; do not copy `.pts`, `.vf`, or full object dictionaries through context unless explicitly needed.

## Success Criteria

- `create_radiance_sensor_grid` returns `sensor_grid_target.target_type == "radiance_sensor_grid"` and `summary_view.sensor_count`.
- `create_radiance_sensor_grid_from_object` also returns a `radiance_sensor_grid` target and includes `summary_view.source_object`.
- `create_radiance_view` returns `view_target.target_type == "radiance_view"` and `summary_view.view_type`.
- When `attach_to_model=true`, `summary_view.attached_to_model` is `true` and the Garden HBJSON contains the asset under `properties.radiance.sensor_grids` or `properties.radiance.views`.
- For object-hosted grids, `summary_view.has_mesh` should be `true` and the attached HBJSON SensorGrid should include a `mesh` object.

## Evidence

- Agent integration smoke added 2026-04-29 verifies one Code Mode `execute` can create a Honeybee model, attach one SensorGrid and one View, and persist both Garden artifacts.
- Supervised external Matrix task 28 on 2026-04-30 verifies a natural MiniMax Agent can attach a compact SensorGrid and View to the current Honeybee model. Pre-fix runs exposed `host_target`, missing identifier, `radiance/sensorgrids`, `center`, `vtc` / `vterrain`, and implicit attach drift; after bounded compatibility, the retained run passed at `31.128s`, with one SensorGrid create and one View create. Residual cost smell: repeated `get_base_honeybee_model`.
- 2026-05-01 deterministic regression verifies `create_radiance_sensor_grid_from_object` can create and attach a SensorGrid from a detached Honeybee Shade target.
- 2026-05-01 deterministic regression verifies the same object-hosted path persists `SensorGrid.mesh` for surface-result VisualizationSet mesh coloring.
