# Staged Energy Agent Workflow

Use this when a user asks for a large Honeybee Energy task that combines blank-Garden setup, geometry, windows, shades, Energy properties, weather, simulation, and result reads.

## Preconditions

- This is an Agent behavior scaffold, not a new MCP tool.
- Each stage must resume from Garden state.
- Start every Code Mode block with the literal `garden_root`.
- Do not replay earlier stages after a later stage fails.

## Stage A: Model And Rooms

Goal: create or confirm the Garden, base Honeybee Model, and Room targets.

Tools: `garden_create`, `honeybee_create_model`, `honeybee_create_room`, `garden_get_base_honeybee_model`, `honeybee_search_model_objects`.

Stop with a compact summary containing `garden_root`, `model_target`, `room_targets`, and counts.

## Stage B: Subfaces And Shades

Goal: add windows, apertures, overhangs, or louvers to existing room faces.

Tools: `honeybee_search_model_objects`, `honeybee_create_apertures_by_parameters`, `honeybee_create_shades_by_parameters`.

Follow `reference/honeybee/subface-shade-stage-short-path.md`. Search room targets once, search exterior walls with `children_scope`, create apertures from face targets, create shades from aperture or face targets, verify once, and stop. Do not search for save tools after successful writes.

## Stage C: Energy Properties And HVAC

Goal: create or attach schedules, ProgramType, ConstructionSet, Setpoint, HVAC, ventilation, PV, and load-center properties.

Tools include `energy_search_energy_library_objects`, `energy_create_window_construction`, `energy_create_construction_set`, `energy_create_schedule_ruleset`, `energy_create_setpoint`, `energy_create_program_type`, `energy_search_hvac_templates`, `energy_create_ideal_air_system`, `energy_setup_simple_ventilation_properties`, `energy_setup_airflow_network`, `energy_create_zone_ventilation_fan`, `energy_create_pv_properties`, `energy_create_electric_load_center`, `honeybee_edit_room`, `honeybee_edit_shade`, `honeybee_edit_model`, and `honeybee_validate_model`.

When resuming from an existing Garden, search current Room targets and inspect `matches[i].energy_properties`. Edit only missing or stale properties. For confirmation, use room search compact `energy_properties`; do not invent `get_honeybee_room`.

Before moving to simulation, confirm Room ProgramType, Setpoint, and conditioned/HVAC assumptions.

## Stage D: Weather And Run

Goal: register Garden-managed weather and start or poll an Energy run.

Tools: `energyplus_search_epw_map`, `energyplus_download_epw`, `energyplus_search_weather_files`, `energyplus_start_simulation`, `energyplus_poll_simulation`.

Use `energyplus_search_epw_map` without `garden_root`, then `energyplus_download_epw` with `garden_root` and `epw_map_target`. Pass the full `energyplus_download_epw.target` into `energyplus_start_simulation.weather_target`. Stop after the run is `running`, `completed`, or `failed`.

If weather download is blocked by an external site failure, return the blocked weather status and recovery fields. Do not replay earlier stages.

## Stage E: Outputs

Goal: read bounded results from an existing completed or failed run.

Tools: `energyplus_poll_simulation`, `energyplus_list_run_outputs`, `energyplus_read_eui`, `energyplus_read_errors`, and SQL/DataCollection result readers when requested.

If completed, list outputs and read requested results. If failed, read bounded errors. If still running, return the Energy run target and status.

## Compact Stage Summary

```python
return {
    "stage": "B",
    "garden_root": garden_root,
    "aperture_targets": aperture_targets,
    "shade_targets": shade_targets,
    "counts": {"rooms_checked": 2, "apertures": len(aperture_targets), "shades": len(shade_targets)},
    "next_stage": "C"
}
```

## Stop Conditions

- Do not request full HBJSON, EPW, SQL, or large SDK dictionaries unless the user asks for export/debug output.
- Do not start a duplicate run for the same `run_id`.
- Do not continue downstream after a stage summary unless the user requested the next stage.
- Keep run identifiers, metrics, and historical failure analysis in LLM-Wiki.
