# Ventilation And PV Agent Workflow

Use this scaffold when a Honeybee Energy task mixes model creation/editing with operable-window ventilation, fan-assisted zone ventilation, PV panels on shades, Energy simulation start, and result visualization.

## Preconditions

- Prefer one Code Mode block when the prompt already provides concrete Garden, weather, and run inputs.
- Use exact workflow skeletons for mixed ventilation/PV/Energy requests; fully vague one-shot prompts are not assumed stable.
- Use typed Room, Face, Aperture, and Shade targets from searches or create results.

## MCP Route

1. Create or confirm the model and Rooms.
2. Search Face or Room targets once and store `matches[i].target`.
3. Create Apertures with `HB_create_apertures_by_parameters`.
4. Create explicit PV Shades with `HB_create_shade` when exact panel geometry is known.
5. Create and attach Setpoint/HVAC targets with `EP_create_setpoint`, `EP_create_ideal_air_system`, and `HB_edit_room`.
6. Apply simple operable-window ventilation with `EP_setup_simple_ventilation_properties`.
7. Create fan-assisted ventilation with `EP_create_zone_ventilation_fan`, then attach it with `HB_edit_room.zone_ventilation_fans`.
8. Create PV properties with `EP_create_pv_properties`, attach them through `HB_edit_shade.pv_properties`, create a load center with `EP_create_electric_load_center`, and attach it through `HB_edit_model.electric_load_center`.
9. Validate.
10. Start with `EP_start_simulation` and poll with `EP_poll_simulation`.
11. For completed SQL results, use `EP_read_result_data(save_data_collections=true, include_values=false)` and generic visualization tools.

## Tool Choices

- Simple natural ventilation: `EP_setup_simple_ventilation_properties` with `room_identifiers` or `room_targets`, plus operable fraction, discharge coefficient, cross-ventilation, and delta-temperature fields.
- AFN or leakage: `EP_setup_airflow_network`; use only when the user asks for AFN, AirflowNetwork, cracks, or leakage.
- Fan-assisted ventilation: `EP_create_zone_ventilation_fan` with `identifier`, `flow_rate`, and `ventilation_type`.
- PV shade properties: `EP_create_pv_properties` with `identifier`, `rated_efficiency`, `active_area_fraction`, and `mounting_type` such as `FixedOpenRack`.
- Inverter/load-center sizing: `EP_create_electric_load_center`.
- Monthly charts: `LB_data_collection_monthly_chart_to_visualization_set` then `LB_set_to_html`.

## Stop Conditions

- Do not pass `room_target`, `opening_area`, or `opening_fraction` to `EP_setup_simple_ventilation_properties`.
- Do not pass `pv_type`, `dc_to_ac_size_ratio`, or inverter settings to `EP_create_pv_properties`.
- Do not pass both `data_collection` and `data_collection_target` in the same chart series item.
- Do not pass full search responses as targets.
- Do not use blocking `EP_run_simulation_wait` unless the user explicitly asks to wait.
