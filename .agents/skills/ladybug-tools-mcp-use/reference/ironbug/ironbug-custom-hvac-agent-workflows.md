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
- Local passed/candidate from
  `docs/llm-wiki/evidence/ironbug-next-round-tool-tests-2026-05-31`:
  electric convective baseboard, electric radiant-convective baseboard,
  water convective/radiant-convective baseboards, ZoneHVAC ERV,
  air-cooled EIR chiller + FCU, repaired fluid-cooler
  condenser-water loop + FCU, CV no-reheat + DOAS, CV reheat + boiler, and VAV
  HeatAndCool no-reheat/reheat, plus unit ventilator cooling-only /
  heating-only variants, PlantLoop EIR heat pump, parallel/series PIU reheat,
  inlet-side mixer + FCU, cooled beam + DOAS, four-pipe beam, four-pipe
  induction, high-temperature radiant, and low-temperature radiant
  variable-flow, D2 two-speed DX unitary + Fan:SystemModel, D2 explicit
  OAStream air-side ERV, D2 multi-speed heat pump + FanOnOff, D2 evaporative
  DOAS, and D2 humidity/desiccant DOAS.
  Treat these as local tool-test directions, not Agent-verified case playbooks.
- Do not promote the same next-round cohort's blocked/partial records:
  heat-recovery operation scheme is fidelity-partial, headered/tertiary pump
  topology remains blocked.
  Existing retained 24-case guidance remains separate when a specific case file
  has its own pass evidence.

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
| air-cooled chiller + fan coil | `Air-Cooled Chiller FCU` |
| fluid cooler condenser loop + fan coil | `Fluid Cooler FCU` |
| DOAS only | `DOAS Only` |
| fan coils with fresh air / FCU + DOAS | `FCU + DOAS` |
| VRF | `VRF Only` |
| VRF with fresh air / VRF + DOAS | `VRF + DOAS` |
| CAV reheat | `CAV Reheat` |
| PIU reheat | `PIU Reheat` |
| CV no reheat + DOAS | `CV No Reheat + DOAS` |
| VAV without reheat | `VAV No Reheat` |
| VAV with hot-water reheat | `VAV Reheat` |
| VAV HeatAndCool without reheat | `VAV HeatAndCool No Reheat` |
| VAV HeatAndCool with reheat | `VAV HeatAndCool Reheat` |
| four-pipe beam / induction | `Beam And Induction` |
| rooftop unit / unitary rooftop | `Unitary Rooftop` |
| multi-speed heat pump / multi-speed unitary heat pump | `Multi-Speed Heat Pump` |
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

Local tool-test candidate, not external-Agent retained: cooling-only and
heating-only unit ventilators now require the concrete one-coil tools
`detailed_hvac_zone_equipment_unit_ventilator_cooling_only` and
`detailed_hvac_zone_equipment_unit_ventilator_heating_only`; do not route them
through the generic `IB_ZoneHVACUnitVentilator` path. For compact Energy tests,
keep the hot-water coil flow small, around `0.001 m3/s`, and use a moderate hot
water loop setpoint such as `60 C`; oversized `0.05 m3/s` heating coils on a
minimal district-heating loop can clear node checks but run away on plant
temperature.

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

1. Chilled-water loop with pump + cooling source and FCU cooling coils as
   demand. Pass one inner branch list per coil, such as
   `demand_branch_component_targets=[[cooling_coil_1], [cooling_coil_2]]`.
   Use `detailed_hvac_district_cooling` unless the prompt asks for a
   chiller/tower.
2. Hot-water loop with pump + `detailed_hvac_district_heating_water` and all
   FCU heating coils as demand. Pass one inner branch list per coil.

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
   coils as one parallel demand branch per coil.
4. Hot-water loop with pump + `detailed_hvac_district_heating_water` and FCU
   heating coils as one parallel demand branch per coil.

### Air-Cooled Chiller FCU

Local tool-test pass only; not Agent-verified. Use the FCU-only room path with
real FCU cooling-coil demand, then create an EIR chiller in its air-cooled mode
as the chilled-water supply. Do not add a condenser-water loop for the
air-cooled chiller path unless the prompt asks for a separate heat-rejection
variant.

### Fluid Cooler FCU

Local tool-test pass only; not Agent-verified. Use the FCU-only room path, a
condenser-water loop with the repaired fluid-cooler heat-rejection path, and a
chilled-water loop that serves the FCU cooling coils as parallel demand
branches. Stop if the graph requires headered / tertiary pump topology or stale
PlantLoop EIR heat-pump binding; those are blocked/partial records.

### Primary-Secondary FCU

Use the five-room FCU-only room path. Cooling side:

1. `detailed_hvac_heat_exchanger_fluid_to_fluid` with
   `control_type="CoolingDifferentialOnOff"`.
2. Primary chilled-water loop: constant-speed pump + district cooling on
   supply, heat exchanger on demand.
3. Secondary chilled-water loop: variable-speed pump + same heat exchanger on
   supply, all FCU cooling coils on demand as
   `[[cooling_coil_1], [cooling_coil_2], ...]`.
4. Hot-water loop: pump + district-heating-water supply, all FCU heating coils
   on demand as `[[heating_coil_1], [heating_coil_2], ...]`.

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

### CV No Reheat + DOAS

Local tool-test pass only; not Agent-verified. Use the DOAS Only air-loop
assembly, but use the constant-volume no-reheat terminal family for each served
ThermalZone and keep one demand branch per room.

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
   demand as one inner branch list per coil.
3. Hot-water loop with pump + district-heating-water, all FCU heating coils on
   demand as one inner branch list per coil.

Do not use `detailed_hvac_add_hvac_component_fallback`, `detailed_hvac_list_hvac_component_types`, or
extra loop fields such as `display_name`, `loop_name`, or `fluid_type` unless
the schema asks for them.

### Chiller Tower + DOAS + FCU

Use FCU + DOAS across five rooms, but replace district chilled water with:

1. Water-cooled chiller.
2. Condenser pump + variable-speed cooling tower.
3. Condenser-water loop with chiller as demand.
4. Chilled-water loop with pump + chiller as supply and all FCU cooling coils as
   one parallel demand branch per coil.

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
4. Boiler hot-water loop serving all reheat coils as one parallel demand branch
   per terminal reheat coil.

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
`detailed_hvac_air_terminal_vav_reheat`. Hot-water loop demand is the central
heating coil plus terminal reheat coils; pass the central heating coil and each
terminal reheat coil as separate parallel singleton branches. Use
`detailed_hvac_pump_variable_speed` for the hot-water loop. The chilled-water
loop serving only the central cooling coil can use the usual constant-speed
pump. Constant-speed hot-water pump on the correct parallel Row 14 topology
caused EnergyPlus plant-loop runaway; a serial hot-water branch completed only
as a diagnostic and is not accepted for VAV reheat row closure.

### VAV HeatAndCool

Local tool-test pass only; not Agent-verified. Use the VAV central-air-loop
shape, but select the source-backed HeatAndCool no-reheat or reheat terminal
family exposed by the current MCP schema. Preserve room-linked ThermalZones,
AirLoop demand branches, central cooling/heating coils, and one parallel
hot-water demand branch per terminal reheat coil when using the reheat variant.

### PIU Reheat

Local tool-test pass only; not Agent-verified. Parallel and series PIU reheat
both have Codex-direct EnergyPlus passes. Use room-linked ThermalZones,
air-loop demand branches, and real reheat coils; do not reuse this pass for
inlet-side mixer terminals because inlet-side mixer requires a distinct
ZoneHVAC child such as FCU connected through the mixer child path.

### Inlet-Side Mixer + FCU

Local tool-test pass only; not Agent-verified. Use a room-linked
`IB_ThermalZone`, create the `IB_ZoneHVACFourPipeFanCoil` child with real
fan/coils and plant-loop demand, then pass that child as the inlet-side
mixer's zone-equipment child before assigning the mixer as the zone air
terminal. Stop if the translated `AirTerminal:SingleDuct:Mixer` lacks
`ZoneHVAC:FourPipeFanCoil`, the FCU name, or a secondary inlet node.

### Beam And Induction

Local tool-test pass only; not Agent-verified. Four-pipe beam, four-pipe
induction terminals, and cooled beam + DOAS have Codex-direct EnergyPlus
passes. For cooled beam + DOAS, keep a real chilled-water PlantLoop serving
`IB_CoilCoolingCooledBeam`; stop if the coil is not written as
`OS:Coil:Cooling:CooledBeam` or if the terminal is not
`OS:AirTerminal:SingleDuct:ConstantVolume:CooledBeam`.

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

Local Codex-direct EnergyPlus pass: `IB_AirLoopHVACUnitarySystem` can accept a
two-speed DX cooling coil, electric heating coil, and `IB_FanSystemModel` child
combination. Keep the Fan:SystemModel flow-fraction curve nonblank in the
runtime OSM; the retained compact rerun used a short run id and produced clean
ERR/EUI/SQL evidence.

### Multi-Speed Heat Pump

Local Codex-direct EnergyPlus pass only; not Agent-verified. Use one
program/setpoint-ready Honeybee Room with a matching `IB_ThermalZone`, then
create:

1. `detailed_hvac_coil_cooling_dx_multi_speed` with explicit stage identifiers,
   rated capacities, sensible heat ratios, COPs, and air-flow rates.
2. `detailed_hvac_coil_heating_dx_multi_speed` with explicit stage identifiers,
   rated capacities, COPs, and air-flow rates.
3. `detailed_hvac_fan_on_off`.
4. `detailed_hvac_coil_heating_electric` for supplemental heat.
5. `detailed_hvac_air_loop_unitary_heat_pump_air_to_air_multi_speed` with the
   cooling coil, heating coil, FanOnOff, supplemental coil, controlling
   ThermalZone, and matching speed-level flow fields.
6. `detailed_hvac_setpoint_manager_scheduled` on the air-loop supply path.
7. A constant-volume no-reheat terminal, `detailed_hvac_air_loop_branches`, and
   `detailed_hvac_air_loop_hvac`.

Do not substitute `IB_FanSystemModel` for this retained path; Fan:SystemModel
coverage belongs to the two-speed DX unitary pass. Stop if the runtime OSM/IDF
lacks `AirLoopHVAC:UnitaryHeatPump:AirToAir:MultiSpeed`,
`Coil:Cooling:DX:MultiSpeed`, `Coil:Heating:DX:MultiSpeed`, or their stage data
objects.

### Air-Side ERV

Local Codex-direct EnergyPlus pass for a compact DOAS / exhaust scenario:

1. Create the sensible/latent heat exchanger with
   `supply_air_outlet_temperature_control=False` unless the scenario also
   provides an explicit downstream temperature setpoint.
2. Pass it to `detailed_hvac_outdoor_air_system` through
   `oa_stream_targets=[heat_exchanger_target]`.
3. Do not use `heat_recovery_target` for the retained compact D2-B path.
4. Keep zone exhaust as zone equipment on the matching `IB_ThermalZone`.
5. Use a short run id on deep Windows artifact paths.

Stop if the runtime OSM/IDF lacks
`HeatExchanger:AirToAir:SensibleAndLatent` or the OutdoorAirSystem equipment
list contains only the outdoor-air mixer.

### Evaporative And Humidity DOAS

Local Codex-direct EnergyPlus pass notes:

- For direct / indirect evaporative DOAS, keep the evaporative coolers on the
  air-loop supply path with explicit scheduled temperature setpoint managers.
  Do not place the evaporative coolers inside the OutdoorAirSystem stream for
  the retained compact path.
- For humidity-control two-stage DX + desiccant DOAS, put the desiccant in
  `oa_stream_targets` and do not duplicate it in `supply_component_targets`.
  Use supply order
  `[OutdoorAirSystem, TwoStageHumidityControlDX, ScheduledTemperatureSPM, FanSystemModel]`.
- Stop if `CoilSystem:Cooling:DX` reports a missing temperature setpoint, or if
  the runtime OSM/IDF drops `HeatExchanger:Desiccant:BalancedFlow`.

## Radiant

### Radiant + DOAS

For the retained 24-case `Radiant + DOAS` prompt, use hot-water baseboard
radiant zone equipment.

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
heating coils on demand as one parallel branch per room coil.

For strict low-temperature radiant variants, use the constant-flow path rather
than variable-flow:

1. `detailed_hvac_coil_heating_low_temp_radiant_const_flow` per served room.
2. `detailed_hvac_zone_equipment_low_temp_radiant_const_flow` with the heating
   coil child, a matching cooling coil child if needed, and a matching
   room-linked ThermalZone.
3. Connect the radiant heating/cooling coils to hot-water/chilled-water plant
   loops as demand components, one parallel branch per room coil.
4. Model actual Room floor or ceiling surfaces; the Python Console assigns the
   required internal-source construction to the target surfaces before Energy.

If EnergyPlus reports blank branch component type/name fields or a pump
efficiency fatal for this constant-flow path, treat it as a service regression.

Local tool-test pass only; not Agent-verified: a compact
`detailed_hvac_zone_equipment_low_temp_radiant_var_flow` topology now has
Codex-direct EnergyPlus evidence when the heating control schedule is below the
cooling control schedule. Use a heating control setpoint around `20 C` and a
cooling control setpoint around `26 C`; stop if EnergyPlus reports overlapping
heating and cooling control temperatures.

Local tool-test pass only; not Agent-verified: high-temperature radiant zone
equipment now has Codex-direct EnergyPlus evidence when
`heating_setpoint_temperature_schedule_target` is attached to the object before
DetailedHVAC application.
