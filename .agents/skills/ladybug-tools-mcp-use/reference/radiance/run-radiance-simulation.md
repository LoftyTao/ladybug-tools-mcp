# Run Radiance Simulation

Use this when the user asks for point-in-time daylight grids, point-in-time views/images, annual daylight, annual irradiance, cumulative radiation, Direct Sun Hours, Sky View, or Radiance result postprocessing.

For LEED daylight Option 1/2, EN 17037, WELL, or BREEAM 4b, read [daylight-compliance-recipes.md](daylight-compliance-recipes.md) and use its dedicated start tool; the generic matrix route below does not carry compliance-specific inputs.

## Preconditions

- A Garden-backed Honeybee Model exists.
- SensorGrids or Views are attached to the model for recipes that need them.
- Point-in-time runs have a `radiance_sky_file` target.
- Annual/matrix runs have a `wea_file` target.
- For daylight evidence, use a model with at least one exterior Aperture.

## Tool Choice

- `RAD_create_parameters`: recipe type, detail level, and optional raw flags.
- `RAD_start_grid_simulation`: point-in-time grid or daylight-factor grid.
- `RAD_start_view_simulation`: point-in-time view/image.
- `RAD_start_matrix_simulation`: annual daylight, annual irradiance, cumulative radiation, or `direct_sun_hours`.
- `RAD_start_grid_simulation`: point-in-time, daylight factor, or `sky_view`; Sky View accepts `cloudy_sky` as `uniform` or `cloudy`.
- Native daylight compliance starts: see [daylight-compliance-recipes.md](daylight-compliance-recipes.md).
- `RAD_poll_simulation`, `RAD_list_runs`, `RAD_list_run_outputs`: run ledger operations.
- `RAD_list_hdr_images`, `RAD_hdr_to_falsecolor`, `RAD_hdr_to_gif`: view image postprocess.
- `RAD_list_grid_results`, `RAD_grid_result_to_visualization_set`: SensorGrid result postprocess.
- `LB_compose_model_analysis_visualization_set`: overlay model context and analysis/result VisualizationSets.

Radiance run folders use the model display name and retain native recipe and scene subdirectories.
Use `run_folder` from the start or poll result and each output record's `path`; `run_id` is a ledger key, not a filesystem path.

## Point-In-Time Grid Pattern

Create or reuse model, room, aperture, SensorGrid, sky, and parameters. Then start and poll one grid run.

```python
params = await call_tool("RAD_create_parameters", {
    "recipe_type": "point-in-time-grid",
    "detail_level": "low"
})
started = await call_tool("RAD_start_grid_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "sky_file_target": sky_target,
    "sensor_grid_target": grid_target,
    "radiance_parameters": params,
    "run_id": "grid_run",
    "workers": 1
})
ledger = await call_tool("RAD_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2
})
```

After completion, list grid results and convert them to a VisualizationSet. Use `LB_set_to_html` or `LB_set_to_svg` for export.

## Point-In-Time View Pattern

Create or reuse one view, one sky, and one parameter set. Start one view run, then list HDR images before falsecolor or GIF conversion.

```python
started = await call_tool("RAD_start_view_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "view_target": view_target,
    "sky_file_target": sky_target,
    "radiance_parameters": params,
    "run_id": "preview_view_run",
    "workers": 1
})
ledger = await call_tool("RAD_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"],
    "wait_seconds": 60,
    "poll_interval": 2
})
hdrs = await call_tool("RAD_list_hdr_images", {
    "garden_root": garden_root,
    "run_target": started["target"]
})
```

If HDR listing is briefly empty after completion, wait once with `RAD_poll_simulation(wait_seconds=...)`. Do not start a duplicate view run immediately.

## Annual Or Matrix Pattern

```python
params = await call_tool("RAD_create_parameters", {
    "recipe_type": "annual-daylight",
    "detail_level": "medium"
})
started = await call_tool("RAD_start_matrix_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "wea_target": wea_target,
    "calculation_type": "annual_daylight",
    "radiance_parameters": params,
    "run_id": "annual_daylight_run",
    "workers": 1
})
```

Use `RAD_summarize_annual_daylight_metrics` only after completion. Report sDA/ASE with thresholds and provenance; do not declare pass/fail without a user or rating-system rule.

## Imageless Annual Glare

Use this route for annual image-free glare metrics (DGP and glare autonomy, GA).

Preconditions:

- The Garden-backed Honeybee Model has a Radiance View matching `view_filter` and SensorGrid(s) matching `grid_filter`.
- Pass exactly one of `wea_target` or `wea_path` to `RAD_start_imageless_annual_glare`; prefer the Garden WEA target.
- `view_target` selects one attached View when `view_filter="*"`; the wrapper derives its identifier. The View is a model precondition and handoff context, not an independent recipe input.

Start with `RAD_start_imageless_annual_glare`, retaining its `target` (also exposed as `run_target`) and `summary_view.poll_next`:

```python
started = await call_tool("RAD_start_imageless_annual_glare", {
    "garden_root": garden_root,
    "model_target": model_target,
    "wea_target": wea_target,
    "view_target": view_target,
    "view_filter": "*",
    "grid_filter": "*",
    "dgp_threshold": 0.4,
    "luminance_factor": 2000.0,
    "min_sensor_count": 1,
    "radiance_parameters": radiance_parameters,
    "workers": 1,
    "silent": True,
})
run_target = started["target"]
poll = await call_tool("RAD_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run_target,
    "wait_seconds": 10,
    "poll_interval": 2,
})
while poll["summary_view"]["status"] in {"queued", "running"}:
    poll = await call_tool("RAD_poll_simulation", {
        "garden_root": garden_root,
        "run_target": run_target,
        "wait_seconds": 10,
        "poll_interval": 2,
    })
if poll["summary_view"]["status"] in {"failed", "blocked"}:
    return {"run_target": run_target, "status": poll["summary_view"]["status"], "report": poll["report"]}
outputs = await call_tool("RAD_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": run_target,
})
summary = await call_tool("RAD_summarize_glare_metrics", {
    "garden_root": garden_root,
    "run_target": run_target,
    "dgp_threshold": 0.4,
    "save_report": True,
    "include_values": False,
})
return {"run_target": run_target, "outputs": outputs["matches"], "metrics": summary["metrics"], "report": summary["report"]}
```

Continue only while `summary_view.status` is `queued` or `running`; stop on `failed` or `blocked` and preserve `report`.
After completion, `RAD_list_run_outputs.matches` should expose DGP results under `results` and GA outputs under `metrics/ga` before summarizing.
The summary returns compact DGP statistics and GA statistics when GA files exist; missing GA remains a report warning while DGP is retained.
Keep `include_values=false`, and pass a known View identifier to `view_identifier` only for summary provenance.
Do not invent a View recipe parameter, rerun after a missing-View diagnostic without attaching/selecting a real View, or treat HDR/GIF previews as DGP.

## Recovery

- If a long setup fails after writes succeeded, search the Garden and resume from existing targets.
- Use `GD_get_base_honeybee_model`, `RAD_search_sensor_grids`, and `RAD_search_sky_files` to recover targets.
- Split broad tasks into setup checkpoint and run/postprocess turns.
- When polling, use `wait_seconds` and `poll_interval` in one `RAD_poll_simulation` call rather than many immediate status calls.

## Success Criteria

- `RAD_create_parameters.summary_view.command_name` is `rtrace`, `rpict`, or `rfluxmtx`.
- `start_radiance_*_run` returns `target.target_type == "radiance_run"` and poll guidance.
- `RAD_list_run_outputs` exposes known outputs.
- Start and poll results expose the authoritative `run_folder`; output listings expose the authoritative output paths.
- HDR postprocess starts from `.hdr` targets only.
- Grid result postprocess returns a compact `visualization_set_target`.
- Direct Sun Hours grid visualization defaults to the cumulative one-value-per-sensor result; do not select the per-timestep `.ill` directory.
- View GIF/HDR artifacts are visually plausible, not merely non-empty.

## Stop Conditions

- Do not replay Garden/model/library setup from the top after a recoverable later failure.
- Do not start a second run because result visualization export failed; first inspect outputs and reuse the completed run target.
- If a recalculation marks an earlier run `superseded`, treat that run's outputs as unavailable and read the current run's returned paths.
- Do not assume a random or run-id-named Radiance folder.
- Do not call qualitative HDR/GIF previews DGP or glare metrics.
- Do not invent Radiance-owned HTML/SVG export tools.
- Do not handwrite VisualizationSet JSON or result HTML in Agent space.
