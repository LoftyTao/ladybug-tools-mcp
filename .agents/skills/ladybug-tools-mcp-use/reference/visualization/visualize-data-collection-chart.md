# Visualize DataCollection Charts

Use this when the user wants to plot Ladybug `DataCollection` values such as schedule data, weather data, comfort data, or Energy SQL result series.

## Preconditions

- Prefer MCP visualization tools for user-facing result charts.
- Use compact `ladybug_data_collection` targets, not raw 8760 values.
- Use local plotting scripts only when the user explicitly asks for external plotting or the missing MCP capability is disclosed.

## MCP Route

1. Create or read a `ladybug_data_collection` target.
2. For schedules, use `EP_create_schedule_ruleset(include_data=true, return_data=false, return_object_dict=false)`.
3. For Energy SQL, use `EP_read_result_data(save_data_collections=true, include_values=false)`.
4. For weather, use `EP_read_weather_file_data`.
5. Pass targets into `LB_data_collection_monthly_chart_to_visualization_set` or `LB_data_collection_hourly_plot_to_visualization_set`.
6. Export with `LB_set_to_html` or `LB_set_to_svg`.

## Schedule Chart Pattern

```python
chart = await call_tool("LB_data_collection_monthly_chart_to_visualization_set", {
    "garden_root": garden_root,
    "series": [{"data_collection_target": schedule["data_target"], "label": "Generated Schedule"}],
    "time_interval": "monthly",
    "chart_title": "Monthly Generated Schedule",
    "name": "agent_monthly_schedule_chart",
    "return_visualization_set": False
})
html = await call_tool("LB_set_to_html", {
    "garden_root": garden_root,
    "visualization_set_target": chart["visualization_set_target"],
    "name": "agent_monthly_schedule_chart"
})
```

## Energy Result Source

Use exact output names when known. If the user gives a concept, use `output_query` plus optional `unit`, `data_type`, or `object_type`, then confirm selected outputs from `summary_view.result_context`.

```python
data = await call_tool("EP_read_result_data", {
    "garden_root": garden_root,
    "run_id": "completed_run",
    "output_names": ["Zone Ideal Loads Supply Air Total Heating Energy", "Zone Ideal Loads Supply Air Total Cooling Energy"],
    "include_values": False,
    "save_data_collections": True
})
```

## Weather Source

```python
weather_data = await call_tool("EP_read_weather_file_data", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "data_type": "dry_bulb_temperature",
    "analysis_period": "7/1 to 7/31 between 0 and 23 @1",
    "identifier": "july_dry_bulb"
})
```

For original EPW vs UWG morphed EPW comparison, read both weather files and pass both targets into `series[]` with explicit labels. Use `time_interval="monthly_per_hour"` for monthly average by hour patterns.

## Garden Comfort Source

Use this route when the user asks for UTCI, Adaptive, or PMV from Garden DataCollections and wants a chart or export.

1. Start from existing `ladybug_data_collection` targets; when inputs come from an EPW, read each required weather field with `EP_read_weather_file_data` using `garden_root`, exactly one of `weather_target` or `epw_path`, the matching `data_type`, and `return_data_collection=false`, then retain each returned `data_collection_target`.
2. Call one comfort tool with `garden_root` and those targets:
   - `LB_calculate_utci`: required `air_temperature_target` and `relative_humidity_target`; optional `mean_radiant_temperature_target`, `wind_speed_target`, `comfort_parameter` (`UTCIParameter`), and `identifier`.
   - `LB_calculate_adaptive`: required `outdoor_temperature_target` and `operative_temperature_target`; optional `air_speed_target`, `comfort_parameter` (`AdaptiveParameter`), and `identifier`. The outdoor target must be annual continuous data unless its data type is prevailing outdoor temperature.
   - `LB_calculate_pmv`: required `air_temperature_target` and `relative_humidity_target`; optional `mean_radiant_temperature_target`, `air_speed`, `met_rate`, `clo_value`, `external_work` (each a scalar or DataCollection target), `comfort_parameter` (`PMVParameter`), and `identifier`.
3. Keep `return_data_collection=false`, then pass `comfort_result["data_collection_target"]` as `series[i]["data_collection_target"]` to the chart tool.

```python
air = await call_tool("EP_read_weather_file_data", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "data_type": "dry_bulb_temperature",
    "identifier": "air_temperature",
    "return_data_collection": False,
})
humidity = await call_tool("EP_read_weather_file_data", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "data_type": "relative_humidity",
    "identifier": "relative_humidity",
    "return_data_collection": False,
})
comfort = await call_tool("LB_calculate_utci", {
    "garden_root": garden_root,
    "air_temperature_target": air["data_collection_target"],
    "relative_humidity_target": humidity["data_collection_target"],
    "identifier": "utci",
    "return_data_collection": False,
})
chart = await call_tool("LB_data_collection_monthly_chart_to_visualization_set", {
    "garden_root": garden_root,
    "series": [{"data_collection_target": comfort["data_collection_target"], "label": "UTCI"}],
    "time_interval": "monthly",
    "name": "utci_chart",
    "return_visualization_set": False,
})
return {"data_collection_target": comfort["data_collection_target"], "visualization_set_target": chart["visualization_set_target"]}
```

Comfort tools return `target`, `data_collection_target`, `summary_view`, `persistence_receipt`, and `report`; PMV additionally reports PPD statistics.
The chart tool returns `visualization_set_target` and a compact summary; use [visualization-set-to-html.md](visualization-set-to-html.md) for an HTML artifact.

Stop on missing required targets, invalid units, non-continuous Adaptive outdoor data, or a non-OK report.
Do not pass full hourly arrays when a Garden target exists.

## Raw JSON Or CSV Export

If the user asks for values as a file, use `LB_data_collection_to_file` with the compact target.

```python
csv = await call_tool("LB_data_collection_to_file", {
    "garden_root": garden_root,
    "data_collection_target": data["data_collection_targets"][0],
    "file_format": "csv",
    "name": "heating_energy_hourly"
})
```

## Success Criteria

- Upstream readers return `data_collection_target` or `data_collection_targets`.
- Chart tools return `visualization_set_target` and compact series summaries.
- HTML/SVG exporters return Garden artifact receipts.
- CSV/JSON export returns a `data_collection_csv` or JSON artifact receipt.

## Stop Conditions

- Do not pass full `data` objects between tools when targets exist.
- Do not handwrite CSV, SQL, JSON, or DataCollection values.
- Do not put `data_collection_target` or `label` at the chart tool top level; they belong inside `series[]`.
- Do not omit top-level `garden_root` when using a target.
- Export/visualize tools use `name`, not `identifier`.
