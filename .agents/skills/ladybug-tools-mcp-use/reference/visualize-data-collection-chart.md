# Visualize DataCollection Charts

Use this path when the user wants to plot Ladybug `DataCollection` values such as schedule data, weather data, comfort data, or Energy SQL result series.

## Shortest Verified Path

1. `search_tools`
   - Query: `monthly chart data collection visualization set schedule data`
2. `call_tool` -> `create_garden`
3. `call_tool` -> `create_schedule_day`
4. `call_tool` -> `create_schedule_ruleset`
   - Use the exact `object_dict` returned by `create_schedule_day` as `default_day_schedule`.
   - Set `garden_root`.
   - Set `include_data=true`.
   - Set `return_data=false`.
   - Set `return_object_dict=false`.
5. `call_tool` -> `data_collection_monthly_chart_to_visualization_set`
   - Set top-level `garden_root`.
   - In `series[]`, pass `data_collection_target` from step 4.
   - Add `label` when the legend name should be explicit.
   - Set `return_visualization_set=false`.
6. `call_tool` -> `visualization_set_to_html`
   - Pass the compact `visualization_set_target` returned by step 5.
7. Reply with the HTML artifact file name or `artifact_receipt.artifact_path`.

## Minimal Example

Step 4:

```json
{
  "name": "create_schedule_ruleset",
  "arguments": {
    "identifier": "agent_chart_schedule",
    "default_day_schedule": "<create_schedule_day.object_dict>",
    "schedule_type_limit": "Fractional",
    "garden_root": "<garden root>",
    "include_data": true,
    "return_data": false,
    "return_object_dict": false
  }
}
```

Step 5:

```json
{
  "name": "data_collection_monthly_chart_to_visualization_set",
  "arguments": {
    "garden_root": "<garden root>",
    "series": [
      {
        "data_collection_target": "<create_schedule_ruleset.data_target>",
        "label": "Generated Schedule"
      }
    ],
    "time_interval": "monthly",
    "chart_title": "Monthly Generated Schedule",
    "name": "agent_monthly_schedule_chart",
    "return_visualization_set": false
  }
}
```

Step 6:

```json
{
  "name": "visualization_set_to_html",
  "arguments": {
    "garden_root": "<garden root>",
    "visualization_set_target": "<data_collection_monthly_chart_to_visualization_set.visualization_set_target>",
    "name": "agent_monthly_schedule_chart"
  }
}
```

Energy SQL result source:

```json
{
  "name": "read_energy_result_data",
  "arguments": {
    "garden_root": "<garden root>",
    "run_id": "<completed energy run id>",
    "output_name": "Zone Ideal Loads Supply Air Total Heating Energy",
    "include_values": false,
    "save_data_collections": true,
    "max_collections": 1
  }
}
```

Use the returned `data_collection_targets[0]` in the same Step 5 shape shown above. For multiple Energy result series, pass `output_names` in one `read_energy_result_data` call and place each returned target in its own `series[]` item with an explicit `label`. If the user does not know the exact EnergyPlus output names, pass `output_query` with optional `unit`, `data_type`, or `object_type` filters first, then use `summary_view.result_context.selected_outputs` to confirm which SQL outputs were selected. Natural heating/cooling requests can use `output_query="heating cooling"` or `"heating or cooling"` to match either load family, but exact `output_names` remains cheaper when available.

For Energy result charts, use `data_collection_hourly_plot_to_visualization_set` for an hourly heatmap-like HourlyPlot. Use `data_collection_monthly_chart_to_visualization_set.time_interval` for line/summary charts:

- `hourly`: keep hourly values in MonthlyChart when the DataCollection is already hourly.
- `daily`: average to daily values.
- `monthly`: monthly average line.
- `monthly_per_hour`: monthly average by hour pattern.
- `total_daily`, `total_monthly`, `total_monthly_per_hour`: total variants when the data type supports totals.

Use `series[].label` for the legend name; the tool writes it into DataCollection header metadata for MonthlyChart legend semantics.

## Raw JSON/CSV Export

If the user asks for the DataCollection values as a file instead of a chart, do not ask the Agent to print or handwrite values. Use `data_collection_to_file` with the compact target:

```json
{
  "name": "data_collection_to_file",
  "arguments": {
    "garden_root": "<garden root>",
    "data_collection_target": "<read_energy_result_data.data_collection_targets[0]>",
    "file_format": "csv",
    "name": "heating_energy_hourly"
  }
}
```

Use `file_format="json"` for SDK-native Ladybug JSON and `file_format="csv"` for a user-openable table. The tool returns `data_collection_target`, `summary_view`, `artifact`, and `persistence_receipt`; do not expect full values in the response.

## Expected Output

- Step 4 returns `data_target.target_type = "ladybug_data_collection"`.
- Step 4 returns `data = null` when `return_data=false`, so the Agent does not carry 8760 values.
- Energy result reads return `data_collection_targets[].target_type = "ladybug_data_collection"` when `save_data_collections=true`.
- DataCollection target loading can recover from bounded Agent-observed target shapes when the artifact still resolves inside the Garden: `artifact_name` instead of `path`, no-extension `.json` / `.csv` paths, or legacy `target_type="data_collection"`.
- Step 5 returns `summary_view.series[].value_count`.
- Step 5 returns `visualization_set_target` plus top-level `target` and omits `visualization_set` when `return_visualization_set=false`.
- Step 6 returns `artifact_receipt.artifact_type = "visualization_html"` and an HTML path under `artifacts/visualization/html/`.
- Step 6 accepts harmless `visualization_set_identifier` and `visualization_set_display_name` metadata hints if an Agent carries them from the upstream VisualizationSet; use `name` for the intended artifact file name.
- `data_collection_to_file(file_format="csv")` returns `persistence_receipt.artifact_type = "data_collection_csv"` and a `.csv` path under `artifacts/data_collections/`.

## Avoid

- Do not pass the full `data` object between tools when `data_target` is available.
- Do not pass the full `visualization_set` object into `visualization_set_to_html` when `visualization_set_target` is available.
- Do not handwrite CSV, SQL, JSON, or DataCollection values for charts or raw exports.
- Do not use Energy-owned direct chart tools for new visualization workflows when a generic DataCollection target path is available.
- Do not pass a `ScheduleRuleset` dict as `data_collection`.
- Do not put `data_collection_target` or `label` at the tool's top level for monthly charts. They must be inside `series[]`.
- Do not omit top-level `garden_root` when using `data_collection_target`.
- Do not pass `identifier` to `data_collection_to_file`, `data_collection_hourly_plot_to_visualization_set`, `data_collection_monthly_chart_to_visualization_set`, `visualization_set_to_html`, or `visualization_set_to_svg`; these export/visualize tools use `name` for the artifact or VisualizationSet file stem.

## Evidence

- 2026-04-27 Agent smoke passed with `search_tools -> create_garden -> create_schedule_day -> create_schedule_ruleset(return_data=false) -> data_collection_monthly_chart_to_visualization_set(data_collection_target, return_visualization_set=false) -> visualization_set_to_html(visualization_set_target)`.
- A later verification rerun also passed, but the Agent first tried a flattened chart shape with top-level `data_collection_target` and recovered after FastMCP validation. Keep the `series[]` shape explicit in prompts.
- 2026-04-27 deterministic MCP verification passed for a real EnergyPlus SQL sample copied from `resources/honeybee-schema-samples/.../single_family_home_eplusout.sql`: `read_energy_result_data(save_data_collections=true) -> data_collection_monthly_chart_to_visualization_set(data_collection_target, return_visualization_set=false) -> visualization_set_to_html(visualization_set_target)`.
- 2026-04-27 deterministic MCP verification passed for the Energy result visualize matrix: `read_energy_result_data(output_query="heating energy", unit="kWh", data_type="Energy", save_data_collections=true)` then generic hourly plot plus MonthlyChart `hourly`, `daily`, `monthly`, and `monthly_per_hour` intervals.
- 2026-04-27 Agent smoke passed for the natural result-query monthly chart path: no exact EnergyPlus output name, one `execute`, `read_energy_result_data(output_query="heating energy", unit="kWh", data_type="Energy", save_data_collections=true) -> data_collection_monthly_chart_to_visualization_set(return_visualization_set=false) -> visualization_set_to_html`, no repeated tools.
- 2026-04-27 deterministic MCP verification passed for SDK-native DataCollection persistence/export: new JSON targets are readable by `ladybug.datautil.collections_from_json`, and `data_collection_to_file(file_format="csv")` exports a CSV readable by `collections_from_csv`.
- 2026-04-27 Agent smoke passed for compact CSV export: `search_tools -> create_garden -> create_schedule_day -> create_schedule_ruleset(return_data=false) -> data_collection_to_file(file_format="csv")`.
- 2026-04-30 supervised external Agent task 20 persisted heating/cooling Energy SQL result DataCollections from a fresh completed background run after `read_energy_result_data` gained natural two-intent query matching. The run was `intervened_functional` because the supervisor stopped final-output idle after artifacts existed; repeated result reads remain a cost smell.
- 2026-04-30 supervised external Agent task 21 created an HourlyPlot VisualizationSet and HTML artifact from the task 20 SQL DataCollection target. A pre-fix run failed from hand-built target-shape drift; after bounded target normalization and top-level `target` output, the rerun passed with 4 inner MCP calls.
- 2026-04-30 supervised external Agent task 22 created a monthly chart VisualizationSet and HTML artifact from saved SQL DataCollection targets. After HTML/SVG export accepted metadata hints, the rerun passed with 3 inner MCP calls and no repeated MCP tools.
- 2026-05-01 Codex main-process follow-up to `ladybug_mcp_tester` Batch C verified a real completed Energy SQL run path: `read_energy_result_data(output_name="Electricity:Facility", save_data_collections=true) -> data_collection_to_file(file_format=json/csv, name=...) -> data_collection_monthly_chart_to_visualization_set(name=..., return_visualization_set=false) -> data_collection_hourly_plot_to_visualization_set(name=..., return_visualization_set=false) -> visualization_set_to_html(name=...) -> visualization_set_to_svg(name=..., view="Top")`. The run used `data_collection_targets[0]`; no full 52,560-value collection was passed through Agent context.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch C Task 15 verified the same path from a fresh completed run. The retained artifacts included non-empty JSON, CSV, monthly HTML/SVG, hourly HTML, and VisualizationSet JSON files. Do not treat the recipe-generated `visual-report` output as the chart deliverable unless it is non-empty; create explicit DataCollection/VisualizationSet exports for user-facing charts.
