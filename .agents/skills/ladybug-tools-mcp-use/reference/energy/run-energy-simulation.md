# Run Energy Simulation

Use this when the user needs Garden-managed EPW weather and an annual Honeybee Energy simulation from a Garden model.

## Preconditions

- The Honeybee Model validates and is ready for Energy.
- Rooms have suitable ProgramType, Setpoint, and conditioned/HVAC assumptions for the requested result.
- Weather must be a Garden-managed `weather_file` target.

## Weather Route

A valid Garden is required before weather import or download.
For a new project, call `GD_create` first and carry its returned `garden_root`.

For a bundled station, read `weather://catalog`, select `weather://files/<station>`, and call `EP_import_local_weather` with the current `garden_root` and that URI as `source_path`.
Keep `EP_import_local_weather.weather_file` for `EP_start_simulation.weather_target`.

```python
weather = await call_tool("EP_import_local_weather", {
    "garden_root": garden_root,
    "source_path": "weather://files/<station>"
})
```

For a remote or missing station, call `LB_weather_download` with a specific query and exact `region`, `country`, and `admin_region` values when known.
Use `format="zip"` when DDY/STAT is needed; valid formats are `epw` and `zip`.
The tool performs epwapi-first lookup and epwfile OSS retrieval/fallback internally.

```python
weather = await call_tool("LB_weather_download", {
    "garden_root": garden_root,
    "query": "547360",
    "region": "WMO_Region_2_Asia",
    "country": "CHN_China",
    "admin_region": "SD_Shandong",
    "format": "zip"
})
garden = await call_tool("GD_get", {"garden_root": garden_root})
registered = await call_tool("EP_search_weather_files", {
    "garden_root": garden_root,
    "query": "547360",
    "require_ddy": True
})
weather_target = weather["weather_file"]
```

When using the readback target, pass `registered["matches"][i]["target"]`, not the full match or response.
If the remote tool returns `summary_view.status="blocked"`, stop the weather stage, report `download_recovery`, and retry later or resume with a user-provided local EPW/DDY/STAT folder through `EP_import_local_weather`.
If multiple files match, add exact directory filters or a file name; do not choose the first match.

`LB_weather_download` returns `target`, `weather_file`, `weather_target`, `weather_file_target`, `summary_view`, `report`, and `persistence_receipt`.
Use `summary_view.epw_path`, `summary_view.ddy_path`, `summary_view.stat_path`, and `summary_view.download_source` for compact checks.
`EP_search_weather_files` returns `matches[].target`, `epw_path`, `ddy_path`, `has_ddy`, `summary_view`, and `report`.

Do not treat an API `file_id` as an OSS object key or rebuild it from a file name.
Pass an opaque API id unchanged, or keep the returned Garden `weather_file` target.

## Agent Run Route

1. Start with `EP_start_simulation`.
2. Poll with `EP_poll_simulation` using `EP_start_simulation.target` or `run_id`.
3. If `running`, return the run target and status instead of starting a duplicate run.
4. If `completed`, call `EP_list_run_outputs`, then read requested outputs.
5. If `failed`, call `EP_list_run_outputs` and `EP_read_errors`.

Use `run_folder` from the start or poll result and each output record's `path` from `EP_list_run_outputs` as the filesystem references.
`annual_energy_use` identifies the recipe, while `run_id` identifies the ledger entry; neither supplies a directory segment.
The native Energy layout uses the model display name and retains its `openstudio` subdirectory; preserve SDK-defined files beneath it.

```python
run = await call_tool("EP_start_simulation", {
    "garden_root": garden_root,
    "weather_target": weather["weather_file"],
    "run_id": "baseline_annual_energy",
    "units": "si",
    "workers": 1
})
status = await call_tool("EP_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "wait_seconds": 10,
    "poll_interval": 2
})
```

## Read Completed Outputs

```python
outputs = await call_tool("EP_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": run_target
})
eui = await call_tool("EP_read_eui", {
    "garden_root": garden_root,
    "run_target": run_target
})
```

## Intent Summaries

For a completed run, use `EP_summarize_results` when a compact conclusion is enough:

```python
summary = await call_tool("EP_summarize_results", {
    "garden_root": garden_root,
    "energy_run_target": run_target,
    "summary_kind": "loads",
    "period": "monthly"
})
return {
    "metrics": summary["metrics"],
    "units": summary["units"],
    "time_range": summary["time_range"],
    "filters": summary["filters"],
    "aggregation": summary["aggregation"],
    "source_outputs": summary["source_outputs"],
    "run_id": summary["run_id"],
    "warnings": summary["warnings"]
}
```

Use `summary_kind="energy_use"` for annual EUI/end uses, `"loads"` for annual or monthly loads, and `"peaks"` for annual heating/cooling sizing peaks.
The result also includes `summary_view` and `report`; when output support is missing, inspect `energy_blocker.output_request_suggestion`, create that request, and pass its returned target to the next run's `output_request_target`.
This read-only tool never reruns a simulation; use `EP_read_result_data` when raw SQL or DataCollection targets are required.

## Reusable Simulation Parameters (candidate)

Use this candidate path only when the user explicitly asks to reuse Energy settings; it is not a stable default until active MCP reuse is confirmed.

```python
parameter = await call_tool("EP_create_simulation_parameter", {
    "garden_root": garden_root,
    "identifier": "annual_baseline",
    "run_period": {
        "start_month": 1, "start_day": 1,
        "end_month": 12, "end_day": 31
    },
    "design_days": ["99.6/0.4"],
    "weather_target": weather_target,
    "include_body": False
})
run = await call_tool("EP_start_simulation", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "simulation_parameter_target": parameter["simulation_parameter_target"],
    "units": "si"
})
return {
    "simulation_parameter_target": parameter["simulation_parameter_target"],
    "energy_run_target": run["energy_run_target"]
}
```

`run_period` accepts `start_month`, `start_day`, `end_month`, `end_day`, with optional `start_day_of_week` and `leap_year`.
`design_days` accepts `all`, `heating`, `cooling`, `heating_99.6`, `heating_99`, `cooling_0.4`, `cooling_1`, `99.6/0.4`, and `99/1`.
The create result exposes `simulation_parameter_target`, `summary_view.design_day_resolution`, `persistence_receipt`, and `report`.
Pass the exact target to each `EP_start_simulation` or explicitly requested `EP_run_simulation_wait`; `simulation_parameter_target` and inline `sim_par` are mutually exclusive.
If DDY resolution is unavailable or the run preflight blocks, stop and correct the weather target or strategy before retrying.

Use `reload_old=true` on `EP_start_simulation` only when the user asks to reload a known completed run by `run_id`.

## Read And Visualize SQL Results

Prefer MCP visualization tools for user-facing result charts. Use `EP_result_monthly_chart_to_html` for a quick completed-run HTML chart, or `EP_read_result_data(save_data_collections=true)` -> `LB_data_collection_monthly_chart_to_visualization_set` -> `LB_set_to_html` / `LB_set_to_svg` for reusable VisualizationSet artifacts. Do not use matplotlib, ad hoc plotting scripts, or handwritten CSV/JSON chart assembly as the default Agent path.

For completed runs with sizing outputs, call `EP_read_sizing` with the run target or run identifier; use its `zone`, `component`, and `sizing_category` filters to keep the result compact. A run without SQL/ZSZ sizing data returns a structured blocker.

```python
data = await call_tool("EP_read_result_data", {
    "garden_root": garden_root,
    "run_id": "baseline_annual_energy",
    "output_names": [
        "Zone Ideal Loads Supply Air Total Heating Energy",
        "Zone Ideal Loads Supply Air Total Cooling Energy"
    ],
    "include_values": False,
    "save_data_collections": True
})
chart = await call_tool("LB_data_collection_monthly_chart_to_visualization_set", {
    "garden_root": garden_root,
    "series": [
        {"data_collection_target": data["data_collection_targets"][0], "label": "Heating Load"},
        {"data_collection_target": data["data_collection_targets"][1], "label": "Cooling Load"}
    ],
    "time_interval": "monthly",
    "chart_title": "Monthly HVAC Loads",
    "return_visualization_set": False
})
html = await call_tool("LB_set_to_html", {
    "garden_root": garden_root,
    "visualization_set_target": chart["visualization_set_target"],
    "name": "monthly_hvac_loads"
})
```

## EPW DataCollections

For weather time series or original-vs-UWG EPW comparison, call `EP_read_weather_file_data`, then chart returned `data_collection_target` values with `LB_data_collection_monthly_chart_to_visualization_set`.

## Advanced Inputs

Use `output_request_target`, `additional_idf_path`, `additional_idf_text`, `measures_path`, `EP_run_osm_file`, and `EP_run_idf_file` only when the user explicitly asks. All paths must stay inside the Garden.

## Blocking Direct-MCP Route

Use blocking `EP_run_simulation_wait` only for debugging or clients that can safely wait. It is not the default Agent path.

## Success Criteria

- `EP_import_local_weather.weather_file` or `LB_weather_download.weather_file` is a Garden-managed `weather_file` target.
- A remote ZIP requiring design-day data is confirmed by `EP_search_weather_files(require_ddy=True)` returning a match with `has_ddy=true` and `matches[i].target`.
- `EP_start_simulation.target` is an `energy_run` target with poll guidance.
- `EP_poll_simulation.summary_view.run.status` is `running`, `completed`, `failed`, or `superseded`.
- Completed runs expose outputs through `EP_list_run_outputs`.
- Run and output records expose the authoritative `run_folder` and output `path` values.
- Result readers return compact summaries or DataCollection targets, not raw SQL/HTML/EPW payloads.

## Stop Conditions

- Do not pass station IDs, EPW strings, or energy units such as `kWh` to `EP_start_simulation`.
- Keep `units` exactly `si` or `ip`.
- Do not start duplicate runs when a run is still `running`.
- When a recalculation marks an earlier run `superseded`, discard its output entries and use the current run target and returned paths.
- Do not construct a result path from `run_id` or the `annual_energy_use` recipe name.
- Do not call a public `get_energy_simulation_config`; it is service-layer behavior.
- If SQL output is missing, request it before a fresh run with `EP_create_output_request`.
