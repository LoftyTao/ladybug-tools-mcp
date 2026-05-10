# Ventilation And PV Agent Workflow

## Scope

Use this reference when a user asks for a small Honeybee Energy workflow that mixes model creation or editing with operable-window natural ventilation, fan-assisted zone ventilation, PV panels on shades, annual energy simulation start, and result visualization.

This is a verified scaffolded Code Mode path. It is not evidence that a fully vague, one-shot natural prompt is stable. In the current evidence, low-capability Agents repeatedly invented parameters for ventilation, PV, search, and result chart tools when the prompt only described the user goal.

## Recommended Shape

Use one Code Mode `execute` block when the prompt already provides concrete Garden/weather/run inputs. Keep the user-facing goal natural, but give the Agent an exact workflow skeleton for the dependent MCP calls:

1. Create or confirm the model and rooms.
2. Search Honeybee face or room targets once and store `matches[i].target`.
3. Create apertures with `create_honeybee_apertures_by_parameters`.
4. Create explicit PV shades with `create_honeybee_shade` and a `Face3D` geometry dict when exact panel geometry is known.
5. Create and attach setpoint/HVAC targets with `create_setpoint`, `create_ideal_air_system`, and `edit_honeybee_room`.
6. Apply simple operable-window natural ventilation with `setup_simple_ventilation_properties`.
7. Create fan-assisted ventilation with `create_zone_ventilation_fan`, then attach it through `edit_honeybee_room.zone_ventilation_fans`.
8. Create PV properties with `create_pv_properties`, attach them through `edit_honeybee_shade.pv_properties`, create a model load center with `create_electric_load_center`, and attach it through `edit_honeybee_model.electric_load_center`.
9. Validate with `validate_honeybee_model`.
10. Start the run with `start_energy_run` and poll once with `get_energy_run`; do not call blocking `run_energy`.
11. For completed SQL results, call `read_energy_result_data(save_data_collections=true, include_values=false)`, then pass the returned `data_collection_targets[]` to generic visualize tools and export with `visualization_set_to_html`.

## Canonical Tool Notes

- Simple natural ventilation uses `setup_simple_ventilation_properties` with `room_identifiers` or `room_targets`, plus fields such as `fraction_area_operable`, `fraction_height_operable`, `discharge_coefficient`, `wind_cross_vent`, and `delta_temperature`.
- AFN or multizone leakage setup uses `setup_airflow_network`; do not use it for simple operable-window ventilation unless the user asks for AFN, AirflowNetwork, cracks, or leakage.
- Fan-assisted ventilation uses `create_zone_ventilation_fan` with `identifier`, `flow_rate`, and `ventilation_type`, then `edit_honeybee_room.zone_ventilation_fans`.
- PV shade properties use `create_pv_properties` with `identifier`, `rated_efficiency`, `active_area_fraction`, and a valid `mounting_type` such as `FixedOpenRack`.
- Inverter sizing belongs in `create_electric_load_center`, not in `create_pv_properties`.
- Monthly result charts should use `data_collection_monthly_chart_to_visualization_set.series[].data_collection_target` with an explicit `label`, followed by `visualization_set_to_html`.

## Known Drift

- Do not pass `room_target`, `opening_area`, or `opening_fraction` to `setup_simple_ventilation_properties`.
- Do not pass `pv_type`, `dc_to_ac_size_ratio`, or inverter settings to `create_pv_properties`.
- Do not pass both `data_collection` and `data_collection_target` in the same chart series item.
- Do not pass the full `search_honeybee_model_objects` response as a target. Use `matches[i].target`.
- Do not use `run_energy` for this Agent path unless the user explicitly asks to wait for a local blocking run.

## Evidence

2026-04-27 real MiniMax Agent smoke passed:

- Test: `tests/agent_integration/test_agent_energy_run_smoke.py::test_agent_fuzzy_user_workflow_models_ventilation_pv_run_and_visualizes`
- Shape: natural user goal plus exact Code Mode skeleton.
- Tool use: one outer `execute`, 22 inner MCP calls.
- Token use: `11,721` total tokens, max input-window ratio `0.028516`.
- Result: created one model/room, aperture, PV shade, simple ventilation, zone exhaust fan, PV properties, electric load center, started a preflight run, read a completed SQL fixture by `output_query="heating energy"`, generated a monthly chart, and exported HTML.

Treat the path as Agent-verified for scaffolded prompts. Fully vague one-shot prompts remain candidate because earlier runs drifted into invented parameter names and invalid target shapes before completion.
