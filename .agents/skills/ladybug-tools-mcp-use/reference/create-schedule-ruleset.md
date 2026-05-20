# Create Schedule Ruleset

Use this path when the user needs a complete Honeybee Energy schedule that can feed load, control, or ProgramType creation.

## Shortest Verified Path

1. `search`
   - Query: `create complete schedule ruleset data collection`
2. `call_tool` -> `create_schedule_day`
   - Required:
     - `identifier`
     - `values`
   - Optional:
     - `times`
     - `interpolate`
   - When `times` is omitted, `values` must contain exactly one all-day value.
   - When `times` is provided, `values` and `times` must have the same length.
3. Optional `call_tool` -> `create_schedule_rule`
   - Use `create_schedule_day.object_dict` as `schedule_day`.
   - Set weekday booleans such as `apply_saturday` / `apply_sunday`.
4. `call_tool` -> `create_schedule_ruleset`
   - Required:
     - `identifier`
     - `default_day_schedule`: usually `create_schedule_day.object_dict`
   - Optional:
     - `schedule_rules`: list of `create_schedule_rule.object_dict`
     - `schedule_type_limit`: dict or library identifier such as `Fractional`
     - Agent-friendly shorthand: use `default_value`, `schedule_type`, and `rules` when the user gives interval rows instead of SDK dictionaries.
       - Each `rules[]` row should include `start_time`, `end_time`, `value`, and a day selector such as `days="weekdays"`.
       - Mixed day patterns are accepted. For example, weekday and weekend interval rows in the same call are grouped into separate Honeybee `ScheduleRule` objects.
       - The tool converts this shorthand into real Honeybee `ScheduleDay` and `ScheduleRule` SDK objects.
     - `data_analysis_period`: Ladybug `AnalysisPeriod` dict or string for generated `data`; this can filter date and hour ranges through the SDK DataCollection path.
     - `garden_root`: save the final `ScheduleRuleset` into Garden Properties Library.
     - `include_data`: use `false` when the schedule is being saved for reuse and no time-series inspection is needed.
     - `return_data`: use `false` with `garden_root` when charting or inspecting generated schedule data through a compact `data_target`.
     - `return_object_dict`: use `false` with `garden_root` to pass only target/summary/receipt.

## Minimal Example

```json
{
  "name": "create_schedule_day",
  "arguments": {
    "identifier": "office_day",
    "values": [0.0, 1.0, 0.25],
    "times": [
      {"hour": 0, "minute": 0},
      {"hour": 8, "minute": 0},
      {"hour": 18, "minute": 0}
    ]
  }
}
```

```json
{
  "name": "create_schedule_ruleset",
  "arguments": {
    "identifier": "office_schedule",
    "default_day_schedule": "<create_schedule_day.object_dict>",
    "schedule_type_limit": "Fractional",
    "garden_root": "<garden root>",
    "include_data": false,
    "return_object_dict": false
  }
}
```

Agent-friendly interval shorthand:

```json
{
  "name": "create_schedule_ruleset",
  "arguments": {
    "identifier": "office_weekday_occupancy",
    "garden_root": "<garden root>",
    "schedule_type": "fraction",
    "default_value": 0.0,
    "rules": [
      {"start_time": "08:00", "end_time": "12:00", "value": 1.0, "days": "weekdays"},
      {"start_time": "13:00", "end_time": "18:00", "value": 0.8, "days": "weekdays"}
    ],
    "include_data": false,
    "return_object_dict": false
  }
}
```

Mixed weekday/weekend shorthand:

```json
{
  "name": "create_schedule_ruleset",
  "arguments": {
    "identifier": "office_mixed_occupancy",
    "garden_root": "<garden root>",
    "schedule_type": "fraction",
    "default_value": 0.0,
    "rules": [
      {"start_time": "08:00", "end_time": "18:00", "value": 1.0, "days": "weekdays"},
      {"start_time": "10:00", "end_time": "16:00", "value": 0.3, "days": "weekends"}
    ],
    "include_data": false
  }
}
```

## Expected Output

- `target`: Garden Properties Library `schedule` target when `garden_root` is provided.
- `object_dict`: Honeybee Energy `ScheduleRuleset` dict, omitted when `return_object_dict` is `false`.
- `data`: Ladybug `DataCollection.to_dict()` for the complete schedule.
- `data_target`: Garden-backed `ladybug_data_collection` target when `garden_root` and `include_data=true` are provided.
- `summary_view.data.value_count`: usually `8760` for an annual hourly schedule.
- `summary_view.analysis_period`: present when `data_analysis_period` was used.

## Notes

- `ScheduleDay` and `ScheduleRule` are intermediate objects; they do not default to annual `data`.
- `ScheduleDay` and `ScheduleRule` intentionally remain payload authoring objects for now. Persist the final `ScheduleRuleset` when the schedule needs to be reused by load, control, shade transmittance, or ProgramType paths.
- For Agent chart workflows, prefer `garden_root + include_data=true + return_data=false` and pass the returned `data_target` to the generic DataCollection chart tools.
- `data_analysis_period` supplies the schedule data date/hour range, timestep, and leap-year setting. Keep using `data_start_dow` and `data_holidays` for schedule-specific annual expansion.
- 2026-04-25 deterministic MCP cross-test verified direct Garden library save with `create_schedule_ruleset(garden_root, return_object_dict=false)` and a follow-up `get_garden_properties_library_object`.
- 2026-04-27 Agent smoke verified the compact `data_target` chart handoff through `data_collection_monthly_chart_to_visualization_set`.
- 2026-04-30 supervised external Agent task 13 verified the Garden library schedule path with interval shorthand after an initial failure exposed natural `default_value` / `schedule_type` / `rules` drift. Cost evidence: `68.010s`, 8 outer tool calls, 13 inner MCP calls, provider token usage unavailable in streaming mode.
- 2026-05-01 deterministic regression verifies that one `create_schedule_ruleset` shorthand call can group weekday and weekend interval rows into two SDK `ScheduleRule` objects.
