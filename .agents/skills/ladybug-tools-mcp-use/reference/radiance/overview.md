# Radiance Skill Overview

Use this category when the Agent needs Honeybee Radiance modifiers, luminaires, dynamic states, skies, WEAs, sensor grids, views, recipe runs, or daylight result postprocessing.

## Preconditions

- Use a Garden-backed Honeybee Model target.
- Attach SensorGrids or Views to the model before recipes that require them.
- Create the correct Radiance sky or WEA target before point-in-time, annual, or matrix workflows.
- Do not report daylight metrics from setup assets alone.

## Common Scenarios

- Search Radiance standards-library identifiers.
- Create project-specific modifiers, luminaires, and dynamic states.
- Create sky, WEA, or SkyMatrix targets.
- Create SensorGrid or View assets and attach them to a Honeybee Model.
- Start and poll grid, view, or matrix Radiance runs.
- Visualize sunpath, sky dome, radiation dome, HDR, or SensorGrid results.

## Usual MCP Route

1. Create or search Radiance setup assets.
2. Attach required grids/views/states to the Honeybee Model.
3. Create sky or WEA inputs.
4. Start the matching Radiance run and poll completion.
5. List outputs before postprocessing.
6. Export result VisualizationSets or image artifacts only after outputs exist.

## Stop Conditions

- Stop when a recipe lacks required setup assets.
- Stop when a Radiance run is still running and return the run target.
- Stop before calling a qualitative HDR/GIF preview a DGP/glare metric.
- Stop before inventing Radiance-owned HTML/SVG exporters; use generic VisualizationSet exporters.

## References

- `search-radiance-library-objects.md`
- `create-radiance-modifiers.md`
- `create-radiance-luminaires.md`
- `create-radiance-dynamic-states.md`
- `create-radiance-sky-wea.md`
- `create-radiance-sensor-view.md`
- `run-radiance-simulation.md`
- `visualize-sunpath-sky-dome.md`
