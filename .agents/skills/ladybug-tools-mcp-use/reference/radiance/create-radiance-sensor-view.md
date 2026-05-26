# Create Radiance Sensor Grid And View

Use this when the user asks for daylight sensors, workplane test points, Radiance `.pts` files, camera/view setup, `.vf` files, point-in-time views, or pre-steps before Radiance recipes.

## Preconditions

- Use `attach_to_model=true` when the asset should be included in recipe inputs.
- Use explicit points for workplanes and object-hosted grids for surface irradiance or PV/shade studies.
- Do not treat these setup assets as completed daylight metrics.

## Tool Choice

- `radiance_create_sensor_grid`: explicit positions and directions.
- `radiance_create_sensor_grid_from_object`: sample a Face3D-backed Honeybee object surface.
- `radiance_create_view`: explicit camera vectors and Radiance view type tokens `v`, `h`, `l`, `c`, `a`, or `s`.

## Code Mode Pattern

```python
grid = await call_tool("radiance_create_sensor_grid", {
    "garden_root": garden_root,
    "identifier": "workplane_grid",
    "positions": [[0, 0, 0.8], [1, 0, 0.8]],
    "direction": [0, 0, 1],
    "model_target": model_target,
    "attach_to_model": True,
    "return_object_dict": False
})
view = await call_tool("radiance_create_view", {
    "garden_root": garden_root,
    "identifier": "north_view",
    "position": [0, -5, 1.5],
    "direction": [0, 1, 0],
    "up_vector": [0, 0, 1],
    "view_type": "v",
    "h_size": 60,
    "v_size": 45,
    "model_target": model_target,
    "attach_to_model": True,
    "return_object_dict": False
})
```

Object-hosted grid:

```python
shade_grid = await call_tool("radiance_create_sensor_grid_from_object", {
    "garden_root": garden_root,
    "identifier": "shade_irradiance_grid",
    "object_target": shade_target,
    "grid_spacing": 0.5,
    "offset": 0.01,
    "model_target": model_target,
    "attach_to_model": True,
    "return_object_dict": False
})
```

## Success Criteria

- Sensor grid tools return `radiance_sensor_grid` targets and `.pts` artifacts.
- View tools return `radiance_view` targets and `.vf` artifacts.
- When attached, the Honeybee Model contains the assets under `properties.radiance.sensor_grids` or `properties.radiance.views`.
- Object-hosted grids report `summary_view.has_mesh == true`.

## Stop Conditions

- Do not use object-hosted grids as indoor workplane illuminance assumptions.
- Do not copy `.pts`, `.vf`, or full object dicts unless explicitly needed.
- In multi-turn workflows, create setup assets once, report the checkpoint, and stop.
