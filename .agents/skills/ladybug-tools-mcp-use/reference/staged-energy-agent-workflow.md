# Staged Energy Agent Workflow

## Scope

Use this reference when a user asks for a large Honeybee Energy create/edit/simulate task, especially when the request starts from a blank Garden or combines geometry, windows, shades, Energy properties, weather, simulation, and result reads.

This is an Agent behavior scaffold, not a new MCP tool. It exists because real MiniMax evidence showed that one-shot natural workflows can reach valid Garden state or simulation start but still exceed turns after repeated search, schema, and whole-workflow replay.

## Stage Boundaries

### Stage A: Model And Rooms

Goal: create or confirm the Garden, base Honeybee model, and room targets.

Main tools: `create_garden`, `create_honeybee_model`, `create_honeybee_room`, `get_base_honeybee_model`, `search_honeybee_model_objects`.

Stop when the Garden has the expected base model and rooms. Return a compact stage summary with `garden_root`, `model_target`, `room_targets`, and room counts.

### Stage B: Subfaces And Shades

Goal: add windows, apertures, overhangs, or louvers to existing room faces.

Main tools: `search_honeybee_model_objects`, `create_honeybee_apertures_by_parameters`, `create_honeybee_shades_by_parameters`.

Follow `reference/subface-shade-stage-short-path.md`. Search room targets once, search exterior wall faces with `children_scope`, create apertures from returned face targets, create shades from returned aperture or face targets, verify once, then return a compact stage summary. Do not search for save tools after successful writes.

### Stage C: Energy Properties And HVAC

Goal: create or attach schedules, program type, construction set, setpoint, and HVAC.

Main tools: `search_energy_library_objects`, `create_window_construction`, `create_construction_set`, `create_schedule_ruleset`, `create_setpoint`, `create_program_type`, `search_hvac_templates`, `create_ideal_air_system`, `setup_simple_ventilation_properties`, `setup_airflow_network`, `create_zone_ventilation_fan`, `create_pv_properties`, `create_electric_load_center`, `edit_honeybee_room`, `edit_honeybee_shade`, `edit_honeybee_model`, `validate_honeybee_model`.

Stop when rooms have the requested Energy properties attached and validation/search confirms the intended targets. For the validation flag, call `validate_honeybee_model` with `garden_root`; use `validate_honeybee_model`, not `get_base_honeybee_model`, because `get_base_honeybee_model` only confirms model presence/summary. Return a compact stage summary with `construction_set_target`, `program_target`, `setpoint_target`, `hvac_target`, `edited_room_targets`, and `validation_is_valid`.

When Stage C resumes from an existing Garden with rooms, do not create a new Honeybee model or new rooms. Search current room targets, inspect `matches[i].energy_properties`, and edit only missing or stale Energy properties.

For existing-Garden Stage C low-U window overrides, call `create_window_construction` with `garden_root` and `return_object_dict=false`, then pass its `target` directly to `create_construction_set.aperture_set`. Do not use `save_to_library` or a handwritten `WindowConstruction` dict.

For room edits in Stage C, pass `search_honeybee_model_objects` `matches[i].target` to `edit_honeybee_room.target`. The parameter name is `target`, not `room_target`; do not pass a room identifier string, the whole search response, or `matches[i]` itself.

For Stage C confirmation, search rooms and read `matches[i].energy_properties`.
This compact summary is the preferred way to verify program type, loads, setpoint,
HVAC, and construction set after edits. Do not invent `get_honeybee_room`, and do
not request full room object bodies just to check Energy properties.

For ventilation/PV Stage C additions, use `reference/ventilation-pv-agent-workflow.md`. Keep simple operable-window ventilation, AFN leakage generation, fan-assisted zone ventilation, and PV/load-center settings as separate tool choices; do not collapse them into one generic ventilation or PV dictionary.

### Stage D: Weather And Run

Goal: register Garden-managed weather and start or poll an energy run.

Main tools: `search_epw_map`, `download_epw`, `search_weather_files`, `start_energy_run`, `get_energy_run`.

Use `search_epw_map` without `garden_root`, then `download_epw` with `garden_root` and `epw_map_target`. Pass `download_epw.target` or `weather_target` directly into `start_energy_run.weather_target`. Stop after the run is `running`, `completed`, or `failed`; do not start a duplicate run for the same `run_id`.

### Stage E: Outputs

Goal: read bounded results from an existing completed or failed run.

Main tools: `get_energy_run`, `list_energy_run_outputs`, `read_energy_eui`, `read_energy_errors`.

If the run is completed, list outputs and read EUI or the requested bounded result. If the run failed, read bounded errors. If it is still running, return the `energy_run` target and status instead of retrying the run.

## Resume Rule

Each stage must resume from Garden state. Start every `execute` block with the literal `garden_root` from the prompt or previous stage summary. Search for existing room, face, aperture, shade, Energy library, weather, or run targets before retrying writes that may already have succeeded.

Do not replay earlier stages after a later stage fails. For example, if Stage D weather download fails, keep the Stage A/B/C Garden state and repair only the weather/run step.

## Compact Stage Summary

Every stage should return one compact stage summary instead of long model bodies:

```python
return {
    "stage": "B",
    "garden_root": garden_root,
    "aperture_targets": aperture_targets,
    "shade_targets": shade_targets,
    "counts": {
        "rooms_checked": 2,
        "apertures": len(aperture_targets),
        "shades": len(shade_targets),
    },
    "next_stage": "C"
}
```

Do not request full HBJSON, EPW, SQL, or large SDK `object_dict` payloads unless the user explicitly asks for export/debug output.

## Current Evidence Level

- Stage A, B, and D have real segmented MiniMax evidence. B is functionally closed but still token-heavy and final-output-fragile.
- Stage C can close in real MiniMax after targeted guidance but remains token-heavy.
- 2026-04-27 focused C construction handoff rerun closed at `55,937` tokens with a low-U `create_window_construction.target -> create_construction_set.aperture_set -> edit_honeybee_room` path. A follow-up validation fix rerun closed at `40,445` tokens with `Validation Valid=true` after Stage C guidance and `validate_honeybee_model` result helpers were tightened.
- 2026-04-27 room-target disclosure rerun `manual_room_target_edit_disclosure_v1` closed at `55,706` tokens with `validation_is_valid=true`; all successful `edit_honeybee_room` calls used `target: room_targets[i]`. A seeded isolation rerun still failed before completion from Energy construction target drift, but its room edit attempts also used `room["target"]`, not `room_target` or identifier-only edits.
- 2026-04-27 pre-edit replay rerun `manual_pre_edit_replay_seeded_v2` closed the seeded existing-Garden Stage C handoff at `11,554` tokens with one outer `execute`, five inner tools, no repeated tools, and `validation_is_valid=true`.
- 2026-04-30 supervised external Agent matrix tasks 14-16 verified sequential Stage C recovery on the stable `energy_results` Garden. Task 16 initially rebuilt the model and overwrote construction/program state; after the matrix forbade model/room creation for follow-on Energy-property tasks and state evidence checked room Energy summaries, tasks 14-16 retained `LowU_Construction_Set`, `OfficeProgram`, `ideal_air_office`, and `office_setpoint` on both rooms.
- 2026-04-27 ventilation/PV scaffolded workflow closed at `11,721` tokens with one outer `execute`: model/room, aperture, PV shade, setpoint/HVAC, simple ventilation, zone exhaust fan, PV/load center, validation, `start_energy_run -> get_energy_run`, SQL result query, monthly chart, and HTML export.
- 2026-04-28 forum-fuzzy multitask Task 3 initial run wrote program/load/setpoint/HVAC assignments for `OpenOffice` and `MeetingRoom` but exceeded turns during verification. After room search `energy_properties` summaries and compatibility fixes, `task_03_energy_properties_confirm_retry_01` closed at `25,088` tokens without duplicate writes.
- Stage E has direct MCP completed-run evidence and should be used after a run is completed, but full low-intelligence Agent T0/T1 result reading still needs a short repeatable external validation.

Treat this scaffold as the recommended segmentation strategy for large Agent workflows, while keeping individual scenario paths evidence-labeled in their own reference pages.
