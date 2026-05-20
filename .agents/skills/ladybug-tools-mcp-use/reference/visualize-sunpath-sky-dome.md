# Visualize Sunpath, Sky Dome, And Radiation Dome

Deterministic-pass candidate path for creating solar context `VisualizationSet` targets in a Garden. This path is not yet retained Agent-verified, so describe it as deterministic-pass rather than recommended for fully natural discovery.

Use this when the user asks to add Sunpath, Sky Dome, cumulative sky radiation, or Radiation Dome context to a model or analysis visualization scene.

## Tool Choice

- `sunpath_to_visualization_set`
  - Use with exactly one of `location`, `weather_target`, or `epw_path`.
  - Set `return_visualization_set=false` for compact Agent handoff.
- `sky_matrix_to_skydome_visualization_set`
  - Use after `create_sky_matrix`.
  - Produces a Sky Dome context VisualizationSet from a Garden `sky_matrix` target.
- `sky_matrix_to_radiation_dome_visualization_set`
  - Use after `create_sky_matrix`.
  - Cumulative mode only. Do not ask for or invent benefit-sky mode.

## Main Path

```python
sunpath = await call_tool("sunpath_to_visualization_set", {
    "garden_root": garden_root,
    "location": {
        "type": "Location",
        "city": "Boulder",
        "latitude": 40.0,
        "longitude": -105.2,
        "time_zone": -7,
        "elevation": 1600,
    },
    "name": "boulder_sunpath",
    "return_visualization_set": False,
})

sky = await call_tool("create_sky_matrix", {
    "garden_root": garden_root,
    "identifier": "boulder_sky_matrix",
    "location": {
        "type": "Location",
        "city": "Boulder",
        "latitude": 40.0,
        "longitude": -105.2,
        "time_zone": -7,
        "elevation": 1600,
    },
    "compute": False,
})

radiation_dome = await call_tool("sky_matrix_to_radiation_dome_visualization_set", {
    "garden_root": garden_root,
    "sky_matrix_target": sky["target"],
    "name": "boulder_radiation_dome",
    "return_visualization_set": False,
})

scene = await call_tool("compose_visualization_sets", {
    "garden_root": garden_root,
    "visualization_set_targets": [
        sunpath["target"],
        radiation_dome["target"],
    ],
    "name": "solar_context_scene",
    "conflict_strategy": "rename",
    "return_visualization_set": False,
})
```

## Boundaries

- Do not move sky patch arrays, full WEA text, or full VisualizationSet bodies through Agent context unless debugging.
- Use `visualization_set_target` handoff and export later with `visualization_set_to_html`, `visualization_set_to_svg`, or `visualization_set_to_vtkjs`.
- `sky_matrix_to_radiation_dome_visualization_set.summary_view.mode` is `cumulative`. There is no benefit mode in the current public contract.

## Evidence

- 2026-05-18 deterministic MCP tests verify:
  - `sunpath_to_visualization_set(return_visualization_set=false)` saves a Garden `visualization_set` target.
  - `create_sky_matrix(location=..., compute=false) -> sky_matrix_to_skydome_visualization_set` returns structured `Radiation_Data` geometry.
  - `create_sky_matrix(location=..., compute=false) -> sky_matrix_to_radiation_dome_visualization_set(return_visualization_set=false)` saves a cumulative `visualization_set` target.
