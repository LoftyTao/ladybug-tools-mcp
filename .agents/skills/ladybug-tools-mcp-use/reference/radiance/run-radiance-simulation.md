# Run Radiance Simulation

Use this when the user asks for point-in-time daylight grids, point-in-time views/images, annual daylight, annual irradiance, cumulative radiation, or Radiance result postprocessing.

## Preconditions

- A Garden-backed Honeybee Model exists.
- SensorGrids or Views are attached to the model for recipes that need them.
- Point-in-time runs have a `radiance_sky_file` target.
- Annual/matrix runs have a `wea_file` target.
- For daylight evidence, use a model with at least one exterior Aperture.

## Tool Choice

- `radiance_create_parameters`: recipe type, detail level, and optional raw flags.
- `radiance_start_grid_simulation`: point-in-time grid or daylight-factor grid.
- `radiance_start_view_simulation`: point-in-time view/image.
- `radiance_start_matrix_simulation`: annual daylight, annual irradiance, or cumulative radiation.
- `radiance_poll_simulation`, `radiance_list_runs`, `radiance_list_run_outputs`: run ledger operations.
- `radiance_list_hdr_images`, `radiance_hdr_to_falsecolor`, `radiance_hdr_to_gif`: view image postprocess.
- `radiance_list_grid_results`, `radiance_grid_result_to_visualization_set`: SensorGrid result postprocess.
- `visualization_compose_model_analysis_visualization_set`: overlay model context and analysis/result VisualizationSets.

## Point-In-Time Grid Pattern

Create or reuse model, room, aperture, SensorGrid, sky, and parameters. Then start and poll one grid run.

```python
params = await call_tool("radiance_create_parameters", {
    "recipe_type": "point-in-time-grid",
    "detail_level": "low"
})
started = await call_tool("radiance_start_grid_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "sky_file_target": sky_target,
    "sensor_grid_target": grid_target,
    "radiance_parameters": params,
    "run_id": "grid_run",
    "workers": 1
})
ledger = await call_tool("radiance_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2
})
```

After completion, list grid results and convert them to a VisualizationSet. Use `visualization_set_to_html` or `visualization_set_to_svg` for export.

## Point-In-Time View Pattern

Create or reuse one view, one sky, and one parameter set. Start one view run, then list HDR images before falsecolor or GIF conversion.

```python
started = await call_tool("radiance_start_view_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "view_target": view_target,
    "sky_file_target": sky_target,
    "radiance_parameters": params,
    "run_id": "preview_view_run",
    "workers": 1
})
ledger = await call_tool("radiance_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2
})
hdrs = await call_tool("radiance_list_hdr_images", {
    "garden_root": garden_root,
    "run_target": started["target"]
})
```

If HDR listing is briefly empty after completion, wait once with `radiance_poll_simulation(wait_seconds=...)`. Do not start a duplicate view run immediately.

## Annual Or Matrix Pattern

```python
params = await call_tool("radiance_create_parameters", {
    "recipe_type": "annual-daylight",
    "detail_level": "medium"
})
started = await call_tool("radiance_start_matrix_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "wea_target": wea_target,
    "calculation_type": "annual_daylight",
    "radiance_parameters": params,
    "run_id": "annual_daylight_run",
    "workers": 1
})
```

Use `radiance_summarize_annual_daylight_metrics` only after completion. Report sDA/ASE with thresholds and provenance; do not declare pass/fail without a user or rating-system rule.

## Recovery

- If a long setup fails after writes succeeded, search the Garden and resume from existing targets.
- Use `garden_get_base_honeybee_model`, `radiance_search_sensor_grids`, and `radiance_search_sky_files` to recover targets.
- Split broad tasks into setup checkpoint and run/postprocess turns.
- When polling, use `wait_seconds` and `poll_interval` in one `radiance_poll_simulation` call rather than many immediate status calls.

## Success Criteria

- `radiance_create_parameters.summary_view.command_name` is `rtrace`, `rpict`, or `rfluxmtx`.
- `start_radiance_*_run` returns `target.target_type == "radiance_run"` and poll guidance.
- `radiance_list_run_outputs` exposes known outputs.
- HDR postprocess starts from `.hdr` targets only.
- Grid result postprocess returns a compact `visualization_set_target`.
- View GIF/HDR artifacts are visually plausible, not merely non-empty.

## Stop Conditions

- Do not replay Garden/model/library setup from the top after a recoverable later failure.
- Do not start a second run because result visualization export failed; first inspect outputs and reuse the completed run target.
- Do not call qualitative HDR/GIF previews DGP or glare metrics.
- Do not invent Radiance-owned HTML/SVG export tools.
- Do not handwrite VisualizationSet JSON or result HTML in Agent space.
- Keep run evidence, metrics, and visual QA notes in LLM-Wiki.
