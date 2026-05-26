# Ironbug Custom HVAC Agent Workflows

Use this family-level guide for Ironbug custom HVAC variants, mixed requests, and repair work. For exact case prompts, load the one-scenario case skill from `custom-hvac-cases/index.md` first. Evidence matrices and candidate roadmaps live in LLM-Wiki, not in this Skill reference.

## Use First

Use this reference when the user asks for Ironbug-created custom HVAC such as
PTAC, PTHP, unit heater, unit ventilator, FCU, DOAS, VRF, CAV, VAV, rooftop
unitary, chiller/tower, primary-secondary chilled water, or radiant + DOAS.

If the prompt matches one of the 24 short-prompt case skills, use the
dedicated case skill under `custom-hvac-cases/` as the primary
instruction and use this file only for family background.
Before any case or family workflow, run the Room/Room2D preflight in
`ironbug-room-energy-preconditions.md`.

## Preconditions

- Start from a Garden that already has a configured base Honeybee Model or
  Dragonfly Model.
- The model must already contain the Rooms or Room2Ds required by the prompt,
  with identifiers matching the requested room names.
- For the current 24 case skills, use the Honeybee DetailedHVAC
  application route unless a case explicitly records a Dragonfly-retained path.
- Rooms must already have enough Energy setup for simulation, such as
  ProgramType and thermostat setpoints. Honeybee case paths should repair
  missing room setpoints with `energy_create_setpoint` plus `honeybee_edit_room`
  before Ironbug DetailedHVAC application. Dragonfly-native Story/Building
  paths should confirm conditioned Room2Ds when `conditioned_only=True`.
  Reuse a prepared weather target when one exists.

## Ironbug Scope Only

Keep this guide focused on Ironbug HVAC authoring, Ironbug DetailedHVAC
application, and Energy/EUI acceptance. Do not expand this core guide into
geometry creation, facade or Radiance workflows, reusable library authoring,
visualization, or unrelated model setup.

Tool names in this reference are current runtime names. If the MCP schema later
exposes category short names such as `zone_equipment_ptac`,
`air_terminal_vav_reheat`, or `pump_constant_speed`, update the snippets and
case playbooks in the same migration. Until then, call the exact tool names
returned by Code Mode `search` / `get_schema`.

The invariant path is:

1. Reuse or create a Garden and Honeybee Rooms.
2. Give each served Room a ProgramType and thermostat setpoint, then confirm the
   edited Room evidence with search or validation.
3. Create one Ironbug model with `overwrite=True` when recovering.
4. Create one `IB_ThermalZone` per served Room. Its `identifier` and `name`
   must exactly match the Honeybee Room identifier, such as `Room1`.
5. Create source-backed `create_ironbug_*` components.
6. Apply with `detailed_hvac_apply_to_honeybee_model`.
7. Run standard Energy with `energyplus_start_simulation`, poll `energyplus_poll_simulation`, then
   call `energyplus_read_eui` and record `.err` / `.sql`.
8. Once Energy status is `completed` and EUI is read, return final JSON. Do not
   rebuild the HVAC graph or start another run.

Final JSON keys: `case_id`, `garden_root`, `rooms`, `energy_status`, `eui`,
`err_path`, `sql_path`, `blocker`.

## Global Guardrails

- Do not use `run_ironbug_energy` or any Ironbug-only simulation runner.
- Do not use `detailed_hvac_load_profile_plant`, generic PlantLoop tools,
  public relationship helpers, explicit OperationScheme tools, or
  `detailed_hvac_add_hvac_component_fallback`.
- Do not hand-build Ironbug targets, guess `.ibjson` paths, or invent source
  class names.
- Do not call `get_base_ironbug_model`; use the target returned by
  `detailed_hvac_create_model`.
- In Code Mode, do not import `asyncio`, `time`, `os`, `pathlib`, or service
  modules. Call tools sequentially and return compact dicts.
- `detailed_hvac_outdoor_air_system.oa_stream_targets` should usually be
  `[supply_fan]`, not ThermalZones and not branches.
- For semantic water loops, preserve branch topology: a flat target list is one
  serial branch, while a nested list is multiple parallel branches with serial
  order inside each branch.
- For `detailed_hvac_apply_to_honeybee_model`, pass only one room
  selection mode: `room_identifiers`, `room_targets`, or
  `apply_to_all_rooms=true`.
- For `energyplus_read_eui`, use the current schema from the tool if unsure; do not
  retry with guessed aliases after EUI already exists.
- If a write partially succeeds, resume from persisted targets or recreate the
  Ironbug model with `overwrite=True`; do not stack duplicate graphs.
- Deterministic-contract-pass: after overwriting a source-backed component that
  is already embedded in an FCU, terminal, branch, or loop, rebuild the owning
  graph from the latest component targets. If
  `validate_ironbug_energy_readiness` reports
  `ironbug_embedded_component_stale_after_overwrite`, do not apply
  DetailedHVAC or start Energy until the owning graph is rebuilt.
- Deterministic-contract-pass: hot-water coils using
  `UFactorTimesAreaAndDesignWaterFlowRate` need numeric
  `u_factor_times_area_value` and numeric `maximum_water_flow_rate` for
  Energy-ready FCU, reheat, and unit-heater paths.

## Family Selector

| User wording | Use workflow |
|---|---|
| PTAC / packaged terminal AC | `PTAC` |
| PTHP / packaged terminal heat pump | `PTHP` |
| unit heater | `Unit Heater` |
| unit ventilator | `Unit Ventilator` |
| two/five room four-pipe fan coil | `FCU Only` |
| district cooling fan coil | `FCU Only`, district cooling chilled loop |
| boiler reheat | `Boiler Reheat` |
| chiller + cooling tower fan coil | `Chiller FCU` |
| DOAS only | `DOAS Only` |
| fan coils with fresh air / FCU + DOAS | `FCU + DOAS` |
| VRF | `VRF Only` |
| VRF with fresh air / VRF + DOAS | `VRF + DOAS` |
| CAV reheat | `CAV Reheat` |
| VAV without reheat | `VAV No Reheat` |
| VAV with hot-water reheat | `VAV Reheat` |
| rooftop unit / unitary rooftop | `Unitary Rooftop` |
| chiller tower + DOAS + FCU | `Chiller Tower + DOAS + FCU` |
| primary-secondary chilled water FCU | `Primary-Secondary FCU` |
| radiant + DOAS | `Radiant + DOAS` |

## Terminal Systems

### PTAC

Per room:

1. `detailed_hvac_thermal_zone`.
2. `detailed_hvac_fan_on_off` with `"Autosize"` maximum flow.
3. `detailed_hvac_coil_heating_electric`.
4. `detailed_hvac_coil_cooling_dx_single_speed`.
5. `detailed_hvac_zone_equipment_ptac` with fan,
   heating coil, cooling coil, ThermalZone, and autosized operation flows.

No plant loop, DOAS, AirLoopHVAC, or NoAirLoop.

### PTHP

Per room:

1. `detailed_hvac_thermal_zone`.
2. `detailed_hvac_fan_on_off`.
3. `detailed_hvac_coil_heating_dx_single_speed`.
4. `detailed_hvac_coil_cooling_dx_single_speed`.
5. `detailed_hvac_coil_heating_electric` for supplemental heat.
6. `detailed_hvac_zone_equipment_pthp`.

No plant loop, DOAS, AirLoopHVAC, or NoAirLoop.

### Unit Heater

For Room1:

1. `detailed_hvac_thermal_zone`.
2. `detailed_hvac_fan_on_off`.
3. `detailed_hvac_coil_heating_water` with numeric water flow, UA, and rated
   temperatures.
4. `detailed_hvac_zone_equipment_unit_heater`.
5. Hot-water loop: `detailed_hvac_pump_constant_speed`,
   `detailed_hvac_district_heating_water`, `detailed_hvac_plant_loop_hot_water`
   with the heating coil as demand.

### Unit Ventilator

For Room1:

1. `detailed_hvac_thermal_zone`.
2. `detailed_hvac_fan_on_off`.
3. `detailed_hvac_coil_cooling_water`.
4. `detailed_hvac_coil_heating_water`.
5. `detailed_hvac_zone_equipment_unit_ventilator_cooling_heating` with fixed small
   outdoor air flow.
6. Chilled-water loop: pump + `detailed_hvac_district_cooling`, cooling coil
   as demand.
7. Hot-water loop: pump + `detailed_hvac_district_heating_water`, heating coil
   as demand.

Do not use `detailed_hvac_district_heating`.

## FCU And Hydronic Systems

### FCU Only

For each served room:

1. `detailed_hvac_thermal_zone`.
2. `detailed_hvac_fan_on_off`.
3. `detailed_hvac_coil_heating_water`; use numeric UA and maximum water flow
   when using the UA/design-water-flow input method.
4. `detailed_hvac_coil_cooling_water`.
5. `detailed_hvac_zone_equipment_four_pipe_fan_coil`.

Then:

1. Chilled-water loop with pump + cooling source and all FCU cooling coils as
   demand. Use `detailed_hvac_district_cooling` unless the prompt asks for a
   chiller/tower.
2. Hot-water loop with pump + `detailed_hvac_district_heating_water` and all
   FCU heating coils as demand.

For the FCU tool, provide `heating_coil_target`, `cooling_coil_target`, and
`fan_target` together. Do not create DOAS, AirLoopHVAC, or NoAirLoop.

### Boiler Reheat

For Room1:

1. `detailed_hvac_thermal_zone` with
   `is_air_terminal_before_zone_equipments=True`.
2. `detailed_hvac_coil_heating_water` with numeric sizing/rated values.
3. `detailed_hvac_air_terminal_single_duct_constant_volume_reheat`.
4. `detailed_hvac_fan_constant_volume`.
5. `detailed_hvac_air_loop_branches` with `[[zone]]`.
6. `detailed_hvac_air_loop_hvac` with fan on supply and branches on demand.
7. Hot-water loop with pump + `detailed_hvac_boiler_hot_water`, reheat coil as
   demand.

### Chiller FCU

Use the FCU-only room path, then:

1. `detailed_hvac_chiller_electric_eir` with `condenser_type="WaterCooled"`.
2. Condenser loop with condenser pump + `detailed_hvac_cooling_tower_variable_speed`
   on supply and chiller on demand.
3. Chilled-water loop with chilled pump + chiller on supply and FCU cooling
   coils as demand.
4. Hot-water loop with pump + `detailed_hvac_district_heating_water` and FCU
   heating coils as demand.

### Primary-Secondary FCU

Use the five-room FCU-only room path. Cooling side:

1. `detailed_hvac_heat_exchanger_fluid_to_fluid` with
   `control_type="CoolingDifferentialOnOff"`.
2. Primary chilled-water loop: constant-speed pump + district cooling on
   supply, heat exchanger on demand.
3. Secondary chilled-water loop: variable-speed pump + same heat exchanger on
   supply, all FCU cooling coils on demand.
4. Hot-water loop: pump + district-heating-water supply, all FCU heating coils
   on demand.

Do not use `CoolingSetpointOnOffWithComponentOverride` unless override nodes are
explicitly modeled. Do not add DOAS or AirLoopHVAC.

## Outdoor-Air And Combined Systems

### DOAS Only

1. Create mechanical ventilation controller.
2. Create outdoor-air controller with `mechanical_ventilation_target`.
3. Create one supply fan.
4. Create outdoor-air system with `controller_outdoor_air_target` and
   `oa_stream_targets=[supply_fan]`.
5. Per room: no-reheat air terminal, then matching ThermalZone with
   `air_terminal` and `is_air_terminal_before_zone_equipments=True`.
6. Create `detailed_hvac_air_loop_branches` with one branch per ThermalZone.
7. Create `detailed_hvac_air_loop_hvac` with `[outdoor_air_system, supply_fan]`
   on supply and branches on demand.

### FCU + DOAS

Per room:

1. No-reheat DOAS air terminal.
2. Matching ThermalZone with `air_terminal`.
3. FCU fan, heating coil, cooling coil.
4. Four-pipe FCU.

Then:

1. DOAS air loop: mechanical ventilation, outdoor-air controller with
   `mechanical_ventilation_target`, supply fan, outdoor-air system with
   `controller_outdoor_air_target` and `oa_stream_targets=[supply_fan]`,
   `detailed_hvac_air_loop_branches`, and AirLoopHVAC.
2. Chilled-water loop with pump + district cooling, all FCU cooling coils on
   demand.
3. Hot-water loop with pump + district-heating-water, all FCU heating coils on
   demand.

Do not use `detailed_hvac_add_hvac_component_fallback`, `detailed_hvac_list_hvac_component_types`, or
extra loop fields such as `display_name`, `loop_name`, or `fluid_type` unless
the schema asks for them.

### Chiller Tower + DOAS + FCU

Use FCU + DOAS across five rooms, but replace district chilled water with:

1. Water-cooled chiller.
2. Condenser pump + variable-speed cooling tower.
3. Condenser-water loop with chiller as demand.
4. Chilled-water loop with pump + chiller as supply and all FCU cooling coils as
   demand.

Keep hot-water loop as district-heating-water serving FCU heating coils.

## Refrigerant Systems

### VRF Only

Per room:

1. Matching ThermalZone.
2. VRF cooling DX coil.
3. VRF heating DX coil.
4. OnOff fan.
5. `detailed_hvac_zone_equipment_terminal_unit_variable_refrigerant_flow`.

Then call `detailed_hvac_air_conditioner_variable_refrigerant_flow` with all
terminal targets in `terminals_targets`.

No DOAS, AirLoopHVAC, PlantLoop, or NoAirLoop.

### VRF + DOAS

Per room:

1. No-reheat DOAS air terminal.
2. Matching ThermalZone with that `air_terminal`.
3. VRF cooling coil, heating coil, fan, and VRF terminal.

Then:

1. VRF root with all terminal targets.
2. DOAS air loop using the DOAS Only pattern.

No plant loops or NoAirLoop.

## Central Air Loops

### CAV Reheat

Per room:

1. Matching ThermalZone with
   `is_air_terminal_before_zone_equipments=True`.
2. Hot-water reheat coil with numeric sizing/rated values.
3. Constant-volume reheat terminal.

Then:

1. Constant-volume supply fan.
2. AirLoopBranches with one branch per ThermalZone.
3. AirLoopHVAC with fan on supply and branches on demand.
4. Boiler hot-water loop serving all reheat coils.

### VAV No Reheat

Per room:

1. Matching ThermalZone.
2. `detailed_hvac_air_terminal_vav_no_reheat` with autosized max
   air flow and constant minimum air-flow fraction.

Central supply order:

1. Cooling water coil.
2. Cooling scheduled setpoint manager around 13 C.
3. Heating water coil.
4. Heating scheduled setpoint manager around 32 C.
5. Variable-volume supply fan.

Plant loops: chilled-water loop serves central cooling coil; hot-water loop
serves central heating coil only.

### VAV Reheat

Use the VAV No Reheat central path. Per room, use a hot-water reheat coil plus
`detailed_hvac_air_terminal_vav_reheat`. Hot-water loop demand is
the central heating coil plus all terminal reheat coils.

### Unitary Rooftop

Per room:

1. No-reheat air terminal.
2. Matching ThermalZone with `air_terminal`.

Supply side:

1. DX single-speed cooling coil.
2. DX single-speed heating coil.
3. Supplemental electric heating coil.
4. OnOff fan.
5. `detailed_hvac_air_loop_unitary_system` as the supply wrapper.
6. AirLoopBranches with one branch per ThermalZone.
7. AirLoopHVAC with the unitary system on supply and branches on demand.

Do not use `detailed_hvac_air_loop_unitary_heat_pump_air_to_air` for the
retained Energy path.

## Radiant

### Radiant + DOAS

Use hot-water baseboard radiant zone equipment, not low-temperature radiant
variable-flow plant demand.

Per room:

1. No-reheat DOAS air terminal.
2. `detailed_hvac_coil_heating_water_baseboard_radiant` with exact
   `"Autosize"` strings for water flow and design capacity.
3. `detailed_hvac_zone_equipment_baseboard_radiant_convective_water` with
   `fraction_radiant=0.5`.
4. Matching ThermalZone with `air_terminal` and
   `zone_equipments_targets=[baseboard_target]`.

DOAS supply order:

1. Outdoor-air system.
2. DX single-speed cooling coil.
3. Cooling scheduled setpoint manager around 13 C.
4. Constant-volume supply fan.

Hot-water loop: pump + district-heating-water supply, all baseboard radiant
heating coils on demand.

Do not use `detailed_hvac_zone_equipment_low_temp_radiant_var_flow` for current
Energy acceptance. That path failed branch/component translation in retained
tests.
