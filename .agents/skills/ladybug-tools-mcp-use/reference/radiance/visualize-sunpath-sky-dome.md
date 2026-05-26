# Visualize Sunpath Sky Dome And Radiation Dome

Use this deterministic-pass path when the user asks to add Sunpath, Sky Dome, cumulative sky radiation, or Radiation Dome context to a model or analysis VisualizationSet.

## Preconditions

- This is a deterministic-pass candidate, not a fully natural Agent-verified discovery path.
- Use compact VisualizationSet targets and generic exporters.
- Create or reuse a Garden `sky_matrix` target before dome visualization.

## Tool Choice

- `visualization_sunpath_to_visualization_set`: use exactly one of `location`, `weather_target`, or `epw_path`.
- `visualization_sky_matrix_to_skydome_visualization_set`: Sky Dome context from a `sky_matrix` target.
- `visualization_sky_matrix_to_radiation_dome_visualization_set`: cumulative Radiation Dome only.
- `visualization_compose_visualization_sets`: combine solar context VisualizationSets.

## Code Mode Pattern

```python
sunpath = await call_tool("visualization_sunpath_to_visualization_set", {
    "garden_root": garden_root,
    "location": {
        "type": "Location",
        "city": "Boulder",
        "latitude": 40.0,
        "longitude": -105.2,
        "time_zone": -7,
        "elevation": 1600
    },
    "name": "boulder_sunpath",
    "return_visualization_set": False
})
sky = await call_tool("radiance_create_sky_matrix", {
    "garden_root": garden_root,
    "identifier": "boulder_sky_matrix",
    "location": {
        "type": "Location",
        "city": "Boulder",
        "latitude": 40.0,
        "longitude": -105.2,
        "time_zone": -7,
        "elevation": 1600
    },
    "compute": False
})
radiation_dome = await call_tool("visualization_sky_matrix_to_radiation_dome_visualization_set", {
    "garden_root": garden_root,
    "sky_matrix_target": sky["target"],
    "name": "boulder_radiation_dome",
    "return_visualization_set": False
})
scene = await call_tool("visualization_compose_visualization_sets", {
    "garden_root": garden_root,
    "visualization_set_targets": [sunpath["target"], radiation_dome["target"]],
    "name": "solar_context_scene",
    "conflict_strategy": "rename",
    "return_visualization_set": False
})
```

## Success Criteria

- Each producer returns a compact `visualization_set_target` or `target`.
- The composed scene can be passed to `visualization_set_to_html`, `visualization_set_to_svg`, or `visualization_set_to_vtkjs`.
- Radiation Dome summary reports cumulative mode.

## Stop Conditions

- Do not move sky patch arrays, WEA text, or full VisualizationSet bodies through Agent context.
- Do not invent benefit-sky mode; current public Radiation Dome mode is cumulative.
- Keep solar-context evidence in LLM-Wiki.
