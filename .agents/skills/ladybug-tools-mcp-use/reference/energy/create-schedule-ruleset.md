# Create Schedule Ruleset

Use this when the user needs a complete Honeybee Energy schedule for loads, controls, shade transmittance, ProgramType creation, or charting.

## Preconditions

- Decide whether the user needs a saved schedule target, generated schedule data, or both.
- Use `garden_root` and `return_object_dict=false` for reusable Garden handoff.
- Use interval shorthand when the user gives rows such as weekday/weekend time ranges.

## MCP Route

1. Create `ScheduleDay` when explicit day values/times are needed.
2. Optionally create `ScheduleRule` from a day schedule.
3. Create `ScheduleRuleset`.
4. Save to Garden when the schedule will be reused.
5. For charts, return a `data_target` and use DataCollection visualization tools.

## Code Mode Pattern

```python
schedule = await call_tool("energy_create_schedule_ruleset", {
    "garden_root": garden_root,
    "identifier": "office_weekday_occupancy",
    "schedule_type": "fraction",
    "default_value": 0.0,
    "rules": [
        {"start_time": "08:00", "end_time": "12:00", "value": 1.0, "days": "weekdays"},
        {"start_time": "13:00", "end_time": "18:00", "value": 0.8, "days": "weekdays"}
    ],
    "include_data": False,
    "return_object_dict": False
})
```

## SDK Object Pattern

```python
day = await call_tool("energy_create_schedule_day", {
    "identifier": "office_day",
    "values": [0.0, 1.0, 0.25],
    "times": [{"hour": 0, "minute": 0}, {"hour": 8, "minute": 0}, {"hour": 18, "minute": 0}]
})
ruleset = await call_tool("energy_create_schedule_ruleset", {
    "identifier": "office_schedule",
    "default_day_schedule": day["object_dict"],
    "schedule_type_limit": "Fractional",
    "garden_root": garden_root,
    "include_data": False,
    "return_object_dict": False
})
```

## Success Criteria

- The result returns a Garden `schedule` target when `garden_root` is provided.
- `object_dict` is omitted when `return_object_dict=false`.
- `summary_view.data.value_count` is usually `8760` when annual data is included.
- `data_target` is returned when `garden_root`, `include_data=true`, and compact data return settings are used.

## Stop Conditions

- `ScheduleDay` and `ScheduleRule` are intermediate payloads; persist the final `ScheduleRuleset`.
- Do not mismatch `values` and `times` lengths.
- Do not copy raw 8760 values unless explicitly requested.
- Keep schedule evidence and metrics in LLM-Wiki.
