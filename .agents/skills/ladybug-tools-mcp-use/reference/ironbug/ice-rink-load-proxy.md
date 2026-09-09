# Ice Rink Fixed-Load Proxy

Status: Additional IDF fixed-load accounting verified; Ironbug branch candidate.
This reference covers prescribed ice load, cooling-electricity proxy, and input/output accounting only; it does not cover complete ice physics or closed-loop equipment control.
Source: [Ironbug EMS operation strategy](../../../../../docs/llm-wiki/workflows/ironbug-ems-operation-strategy.md).

When the user requests an ice-rink fixed-load proxy through additional IDF or Ironbug EMS, load `ironbug-ems-operation-strategy.md` and `../energy/run-energy-simulation.md` as needed.
For the Ironbug branch, also load `ironbug-room-energy-preconditions.md` and `ironbug-core-ibjson.md`.

## Boundary

- Treat ice load, performance coefficient, ice-surface target, and hall-air setpoint as inputs.
- A fixed load proves only the program and output/metering path; it does not prove ice-temperature prediction, ice-surface heat/moisture balance, reflooding, slab transfer, refrigeration equipment, or closed-loop control.
- Keep the ice-surface target separate from the hall-air setpoint; for a low-temperature hall, check supply-air temperature against the zone setpoint.
- Disable sizing only when the user explicitly requests an annual proxy without equipment selection; never make it a general default.
- Stop this reference when the user requests ice physics or closed-loop equipment control; use a native or EMS equipment case with explicit physical output checks.

## Additional IDF branch

Call `EP_start_simulation` with `model_target`, `weather_target`, `additional_idf_text`, and `units="si"`.
Do not pass `additional_idf_text` and `additional_idf_path` together.
The snippet may use ordinary `EnergyManagementSystem:OutputVariable` objects for power, temperature, or state, but ordinary power output does not enter the facility meter automatically.
After `EP_poll_simulation` completes, reuse the Energy reference sequence `EP_list_run_outputs` -> `EP_read_errors` -> `EP_read_result_data` -> `EP_read_eui`.
Read the named custom power series through MCP and integrate using its reported time interval; state series are signals and do not prove that refrigeration equipment operated.

```python
run = await call_tool("EP_start_simulation", {
    "garden_root": garden_root,
    "model_target": model_target,
    "weather_target": weather_target,
    "additional_idf_text": additional_idf_text,
    "units": "si",
})
status = await call_tool("EP_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "wait_seconds": 60,
    "poll_interval": 2,
})
if status["summary_view"]["run"]["status"] != "completed":
    return {"run_target": run["target"], "status": status["summary_view"]}
data = await call_tool("EP_read_result_data", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "output_names": custom_output_names,
})
return {"run_target": run["target"], "data": data}
```

Additional IDF ordinary power output is outside the energy account.
Do not compare its whole-building EUI with an Ironbug branch whose custom electricity is metered; compare the named fixed-load series and state the accounting scope.

## Ironbug EMS branch

Use a validated Honeybee model and the standard `.ibjson` path.
When applying DetailedHVAC to Rooms, satisfy the Room preconditions and provide matching `IB_ThermalZone` objects.
Do not use additional IDF to replace the Ironbug EMS objects.

Create the following in order, carrying each write's `updated_model_target` into the next write's `ironbug_model_target`:

1. `IB_energy_management_system_program`: pass Erl source in `body`; do not pass a scalar string to `lines`.
2. `IB_energy_management_system_program_calling_manager`: pass `program["target"]` in `programs_targets` and use a confirmed `calling_point`.
3. Create one `IB_energy_management_system_metered_output_variable` per energy quantity with `update_frequency="ZoneTimestep"`, `units="J"`, a legal `resource_type`, and `group_type="Building"`.
   Use `EnergyTransfer` for cooling energy and `Electricity` for electricity; temperature and state are not energy types.
   For a local Erl variable, pass both `ems_program_target=program["target"]` and `ems_program_or_subroutine_name=program_name`.
   `update_frequency` accepts only `ZoneTimestep` or `SystemTimestep`; use `ZoneTimestep` here to match `SET EnergyJ = PowerW * ZoneTimeStep * 3600.0`.
   Set `output_reporting_frequency` separately for result reporting; `Hourly` belongs there and must not be passed as `update_frequency`.
4. `IB_energy_management_system`: pass the manager target in `program_calling_managers_targets` and meter targets in `variables_targets`.
5. Call `IB_validate_model`, then `IB_search_model_objects` with the current `ironbug_model_target` and `object_type="energy_management_system"`.
6. Call `IB_apply_to_honeybee_model` with exactly one Room-selection mode, then reuse the Energy reference for start, poll, and result reads.

The program must convert power to energy for the current Zone timestep before assigning the meter, for example `SET EnergyJ = PowerW * ZoneTimeStep * 3600.0`.
Do not count the same refrigeration electricity through both an `ElectricEquipment` proxy and an EMS meter.
If `IB_update_model_object` does not expose the required meter field, recreate that exact object with its create tool and `overwrite=True`, then reapply DetailedHVAC.

```python
program = await call_tool("IB_energy_management_system_program", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
    "identifier": program_identifier,
    "name": program_name,
    "body": erl_body,
})
ironbug_model_target = program["updated_model_target"]
manager = await call_tool("IB_energy_management_system_program_calling_manager", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
    "identifier": manager_identifier,
    "name": manager_name,
    "calling_point": calling_point,
    "programs_targets": [program["target"]],
})
ironbug_model_target = manager["updated_model_target"]
meter = await call_tool("IB_energy_management_system_metered_output_variable", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
    "identifier": meter_identifier,
    "update_frequency": "ZoneTimestep",
    "resource_type": "Electricity",
    "group_type": "Building",
    "end_use_category": "Cooling",
    "units": "J",
    "ems_variable_name": energy_variable_name,
    "ems_program_target": program["target"],
    "ems_program_or_subroutine_name": program_name,
})
ironbug_model_target = meter["updated_model_target"]
ems = await call_tool("IB_energy_management_system", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
    "identifier": ems_identifier,
    "program_calling_managers_targets": [manager["target"]],
    "variables_targets": [meter["target"]],
})
return {"target": ems["target"], "ironbug_model_target": ems["updated_model_target"]}
```

Authoring writes expose `target`, `updated_model_target`, `summary_view`, `persistence_receipt`, and `report`.
Energy readback exposes the run target, `summary_view.run.status`, output records, ERR, EUI, and SQL `data_collections` or `data_collection_targets`.
Ironbug runs also require `python_ironbug_console_runtime.status="translated"` and `simulation_input_kind="openstudio_osm"`.

## Stop conditions

- Stop when Room or Honeybee Energy preconditions are not met.
- Stop when an Ironbug run lacks Python Console translation and OpenStudio input evidence, or ERR contains severe/fatal errors.
- Stop when a local metered variable lacks its exact program target, program name, legal resource/group, or when the same electricity is metered twice.
- For shared-model variants, execute `apply DetailedHVAC -> start Energy -> poll -> read` one at a time instead of queuing after several applies.
