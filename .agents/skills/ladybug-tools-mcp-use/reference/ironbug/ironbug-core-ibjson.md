# Ironbug Core ibjson Operations

Use this operational reference for Garden-managed Ironbug `.ibjson` create, validate, search, and DetailedHVAC handoff. Evidence, candidate systems, source-backed tool expansion policy, and broad tool maps live in LLM-Wiki, not in this Skill reference.

## Use When

Use this file when the task is to create or inspect an Ironbug model container,
attach Ironbug DetailedHVAC to Honeybee or Dragonfly, or diagnose the basic
target/return-shape contract. For custom HVAC family assembly, load
`ironbug-room-energy-preconditions.md`, then
`custom-hvac-cases/index.md` for exact 24-case prompts or
`ironbug-custom-hvac-agent-workflows.md` for new variants.

## Core Sequence

Keep dependent calls inside one Code Mode `execute` block:

1. `garden_create` if the Garden does not exist.
2. `detailed_hvac_create_model` with `garden_root`, `identifier`,
   `include_hvac_system=True`, and `overwrite=True` only when intentionally
   replacing an existing Ironbug model.
3. Save `created["target"]` as `ironbug_model_target`.
4. `detailed_hvac_validate_model` with that target.
5. `detailed_hvac_search_model_objects` with `garden_root`,
   `ironbug_model_target`, and a concrete `object_type`.
6. If simulation is requested, apply Ironbug DetailedHVAC to Honeybee or
   Dragonfly first, then use the standard Ladybug Tools MCP Energy workflow.

`detailed_hvac_search_model_objects` is not Garden-wide discovery. It always needs
`ironbug_model_target`; do not call it with only `garden_root` and
`object_type="model"`.

## ElectricLoadCenter Notes

For PVWatts or other generator workflows, create the generator, inverter, and
`IB_ElectricLoadCenterDistribution`, then wrap the distribution with the root
`detailed_hvac_electric_load_center` tool before applying DetailedHVAC. During
verification, inspect the runtime compiler writer families and OSM object
presence: accepted compile evidence should include `electric_load_center` and
`OS:Generator:*` / `OS:ElectricLoadCenter:*` objects, not only `.ibjson`
validation.

For a first-stage PVWatts comparison against an Ideal Air baseline, set the
room-linked `IB_ThermalZone` `UseIdealAirLoads=True` so the Python Console
emits `OS:ZoneHVAC:IdealLoadsAirSystem`. Otherwise NoAirLoop PV variants can
produce valid PV SQL outputs but report `conditioned_floor_area=0.0`, which is
not a comparable EUI case.

For simple battery storage, bind `IB_ElectricLoadCenterStorageSimple` through
`electrical_storage_target` and `IB_ElectricLoadCenterStorageConverter` through
`storage_converter_target` on `detailed_hvac_electric_load_center_distribution`.
Use an ElectricLoadCenter buss type that matches the PV/storage arrangement,
such as `DirectCurrentWithInverterDCStorage` for PVWatts with DC storage. If
using `FacilityDemandLeveling`, choose a utility demand target low enough to
exercise discharge; otherwise the run can be valid but show charge-only
storage behavior.

## DetailedHVAC Handoff

Honeybee:

1. Confirm served Rooms have ProgramType and Setpoint with
   `ironbug-room-energy-preconditions.md`.
2. Create one `IB_ThermalZone` per served Honeybee Room.
3. Match each `IB_ThermalZone.identifier` or `Name` to the Honeybee Room
   identifier.
4. Call `detailed_hvac_apply_to_honeybee_model` with exactly one Room
   selection mode: `room_targets`, `room_identifiers`, or
   `apply_to_all_rooms=True`.
5. Use `updated_model_target` for later Honeybee validation or Energy runs.

Minimal no-air-loop Energy closure:

- For a row-1-style no-air-loop EnergyPlus closure, do not stop at
  DetailedHVAC application and do not treat an empty `IB_NoAirLoop` shell as
  runnable HVAC evidence.
- Create a Honeybee Room with ProgramType and thermostat Setpoint, create a
  room-matching `IB_ThermalZone`, set its `use_ideal_air_loads=True`, wrap that
  ThermalZone with `detailed_hvac_no_air_loop`, apply DetailedHVAC to the
  Honeybee Room, then run the standard EnergyPlus workflow and read ERR, SQL,
  and EUI.
- Treat this as a minimal no-air-loop / ideal-loads closure, not evidence for a
  real zone-equipment system.

Dragonfly:

- Use `detailed_hvac_apply_to_dragonfly_energy_properties` for native
  Room2D, Story, or Building HVAC assignment.
- Dragonfly setpoints are managed by ProgramType / program workflows.
- For Story and Building hosts, keep `conditioned_only=True` unless assigning
  HVAC to unconditioned Room2Ds is intentional.

## Public Boundaries

- Do not call or invent `read_ironbug_model`, `get_base_ironbug_model`,
  `run_ironbug_energy`, or `run_ironbug_detailed_hvac_garden_simulation`.
- Do not hand-build Ironbug targets or guess `.ibjson` paths for tool inputs.
- Do not use generic PlantLoop, relationship helper, readiness validator, or
  output-request helper names as public MCP calls.
- Do not pass generic `custom_attributes`, `ib_properties`, `children`,
  `IB_objParams`, or raw source metadata payloads to public create tools.
- Use exact source-backed `create_ironbug_*` tools and reviewed explicit
  parameters. Missing source-backed public surface is a project implementation
  task, not permission to smuggle values through generic payloads.

## Minimal Code Mode Sketch

```python
garden = await call_tool("garden_create", {"root_dir": garden_root})
garden_root = garden["garden_root"]

created = await call_tool("detailed_hvac_create_model", {
    "garden_root": garden_root,
    "identifier": "case_ironbug",
    "include_hvac_system": True,
    "overwrite": True,
})
ironbug_model_target = created["target"]

validation = await call_tool("detailed_hvac_validate_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
})
hvac = await call_tool("detailed_hvac_search_model_objects", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug_model_target,
    "object_type": "hvac_system",
})

return {
    "is_valid": validation["is_valid"],
    "hvac_system_count": len(hvac["matches"]),
    "ironbug_model_target": ironbug_model_target,
}
```

## Return Shape Notes

- `detailed_hvac_create_model` returns `target`, `model_target`, `summary_view`,
  `persistence_receipt`, and `report`.
- `detailed_hvac_validate_model` returns `is_valid`, `valid`, `target`, `issues`,
  `summary_view`, and `report`.
- `detailed_hvac_search_model_objects` returns `matches`; there is no
  `ironbug_model_objects` list.
- Component matches include top-level `component_type`, `source_class`,
  `identifier`, and `target`.
- The persisted `.ibjson` path is in the returned target `path` under
  `models/ironbug/`.
