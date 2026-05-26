# Visualize DataCollection Charts

Use this when the user wants to plot Ladybug `DataCollection` values such as schedule data, weather data, comfort data, or Energy SQL result series.

## Preconditions

- Prefer MCP visualization tools for user-facing result charts.
- Use compact `ladybug_data_collection` targets, not raw 8760 values.
- Use local plotting scripts only when the user explicitly asks for external plotting or the missing MCP capability is disclosed.

## MCP Route

1. Create or read a `ladybug_data_collection` target.
2. For schedules, use `energy_create_schedule_ruleset(include_data=true, return_data=false, return_object_dict=false)`.
3. For Energy SQL, use `energyplus_read_result_data(save_data_collections=true, include_values=false)`.
4. For weather, use `energyplus_read_weather_file_data`.
5. Pass targets into `visualization_data_collection_monthly_chart_to_visualization_set` or `visualization_data_collection_hourly_plot_to_visualization_set`.
6. Export with `visualization_set_to_html` or `visualization_set_to_svg`.

## Schedule Chart Pattern

```python
chart = await call_tool("visualization_data_collection_monthly_chart_to_visualization_set", {
    "garden_root": garden_root,
    "series": [{"data_collection_target": schedule["data_target"], "label": "Generated Schedule"}],
    "time_interval": "monthly",
    "chart_title": "Monthly Generated Schedule",
    "name": "agent_monthly_schedule_chart",
    "return_visualization_set": False
})
html = await call_tool("visualization_set_to_html", {
    "garden_root": garden_root,
    "visualization_set_target": chart["visualization_set_target"],
    "name": "agent_monthly_schedule_chart"
})
```

## Energy Result Source

Use exact output names when known. If the user gives a concept, use `output_query` plus optional `unit`, `data_type`, or `object_type`, then confirm selected outputs from `summary_view.result_context`.

```python
data = await call_tool("energyplus_read_result_data", {
    "garden_root": garden_root,
    "run_id": "completed_run",
    "output_names": ["Zone Ideal Loads Supply Air Total Heating Energy", "Zone Ideal Loads Supply Air Total Cooling Energy"],
    "include_values": False,
    "save_data_collections": True
})
```

## Weather Source

```python
weather_data = await call_tool("energyplus_read_weather_file_data", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "data_type": "dry_bulb_temperature",
    "analysis_period": "7/1 to 7/31 between 0 and 23 @1",
    "identifier": "july_dry_bulb"
})
```

For original EPW vs UWG morphed EPW comparison, read both weather files and pass both targets into `series[]` with explicit labels. Use `time_interval="monthly_per_hour"` for monthly average by hour patterns.

## Raw JSON Or CSV Export

If the user asks for values as a file, use `visualization_data_collection_to_file` with the compact target.

```python
csv = await call_tool("visualization_data_collection_to_file", {
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
