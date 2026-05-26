# Run Energy Simulation

Use this when the user needs Garden-managed EPW weather and an annual Honeybee Energy simulation from a Garden model.

## Preconditions

- The Honeybee Model validates and is ready for Energy.
- Rooms have suitable ProgramType, Setpoint, and conditioned/HVAC assumptions for the requested result.
- Weather must be a Garden-managed `weather_file` target.

## Weather Route

1. Call `energyplus_search_epw_map` without `garden_root`.
2. Select `matches[i].target`.
3. Call `energyplus_download_epw` with the same `garden_root` as the model Garden and `epw_map_target`.
4. Keep `energyplus_download_epw.target` for `energyplus_start_simulation`.

```python
stations = await call_tool("energyplus_search_epw_map", {
    "query": "Boston",
    "source": "TMY3",
    "host": "doe",
    "max_results": 3
})
weather = await call_tool("energyplus_download_epw", {
    "garden_root": garden_root,
    "epw_map_target": stations["matches"][0]["target"]
})
```

If `energyplus_download_epw.report.status == "blocked"` with `download_recovery.reason == "external_weather_download_failed"`, stop the weather stage. Report the remote HTTPS/TLS download failure and include recovery fields; do not blame the Garden or model.

## Agent Run Route

1. Start with `energyplus_start_simulation`.
2. Poll with `energyplus_poll_simulation` using `energyplus_start_simulation.target` or `run_id`.
3. If `running`, return the run target and status instead of starting a duplicate run.
4. If `completed`, call `energyplus_list_run_outputs`, then read requested outputs.
5. If `failed`, call `energyplus_list_run_outputs` and `energyplus_read_errors`.

```python
run = await call_tool("energyplus_start_simulation", {
    "garden_root": garden_root,
    "weather_target": weather["target"],
    "run_id": "baseline_annual_energy",
    "units": "si",
    "workers": 1
})
status = await call_tool("energyplus_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "wait_seconds": 10,
    "poll_interval": 2
})
```

## Read Completed Outputs

```python
outputs = await call_tool("energyplus_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": run_target
})
eui = await call_tool("energyplus_read_eui", {
    "garden_root": garden_root,
    "run_target": run_target
})
```

Use `reload_old=true` on `energyplus_start_simulation` only when the user asks to reload a known completed run by `run_id`.

## Read And Visualize SQL Results

Prefer MCP visualization tools for user-facing result charts. Use `energyplus_result_monthly_chart_to_html` for a quick completed-run HTML chart, or `energyplus_read_result_data(save_data_collections=true)` -> `visualization_data_collection_monthly_chart_to_visualization_set` -> `visualization_set_to_html` / `visualization_set_to_svg` for reusable VisualizationSet artifacts. Do not use matplotlib, ad hoc plotting scripts, or handwritten CSV/JSON chart assembly as the default Agent path.

```python
data = await call_tool("energyplus_read_result_data", {
    "garden_root": garden_root,
    "run_id": "baseline_annual_energy",
    "output_names": [
        "Zone Ideal Loads Supply Air Total Heating Energy",
        "Zone Ideal Loads Supply Air Total Cooling Energy"
    ],
    "include_values": False,
    "save_data_collections": True
})
chart = await call_tool("visualization_data_collection_monthly_chart_to_visualization_set", {
    "garden_root": garden_root,
    "series": [
        {"data_collection_target": data["data_collection_targets"][0], "label": "Heating Load"},
        {"data_collection_target": data["data_collection_targets"][1], "label": "Cooling Load"}
    ],
    "time_interval": "monthly",
    "chart_title": "Monthly HVAC Loads",
    "return_visualization_set": False
})
html = await call_tool("visualization_set_to_html", {
    "garden_root": garden_root,
    "visualization_set_target": chart["visualization_set_target"],
    "name": "monthly_hvac_loads"
})
```

## EPW DataCollections

For weather time series or original-vs-UWG EPW comparison, call `energyplus_read_weather_file_data`, then chart returned `data_collection_target` values with `visualization_data_collection_monthly_chart_to_visualization_set`.

## Advanced Inputs

Use `output_request_target`, `additional_idf_path`, `additional_idf_text`, `measures_path`, `energyplus_run_osm_file`, and `energyplus_run_idf_file` only when the user explicitly asks or during deterministic checks. All paths must stay inside the Garden.

## Blocking Direct-MCP Route

Use blocking `energyplus_run_simulation_wait` only for deterministic direct-MCP tests, debugging, or clients that can safely wait. It is not the default Agent path.

## Success Criteria

- `energyplus_download_epw.target` is a Garden-managed `weather_file` target.
- `energyplus_start_simulation.target` is an `energy_run` target with poll guidance.
- `energyplus_poll_simulation.summary_view.run.status` is `running`, `completed`, or `failed`.
- Completed runs expose outputs through `energyplus_list_run_outputs`.
- Result readers return compact summaries or DataCollection targets, not raw SQL/HTML/EPW payloads.

## Stop Conditions

- Do not pass station IDs, EPW strings, or energy units such as `kWh` to `energyplus_start_simulation`.
- Keep `units` exactly `si` or `ip`.
- Do not start duplicate runs when a run is still `running`.
- Do not call a public `get_energy_simulation_config`; it is service-layer behavior.
- If SQL output is missing, request it before a fresh run with `energyplus_create_output_request`.
- Keep run evidence, EUI values, artifacts, and metrics in LLM-Wiki.
