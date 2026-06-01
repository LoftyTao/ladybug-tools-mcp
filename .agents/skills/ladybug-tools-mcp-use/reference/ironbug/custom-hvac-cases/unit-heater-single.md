# Case Skill: unit_heater_single

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 添加热水盘管单元加热器。`. Keep the system family and served-room list exactly aligned with this case (["Room1"]) unless you intentionally switch to the family workflow for a variant.

Python Ironbug Console matrix status: `mimo-v25-case-pass` on the direct OSM
runtime path. The accepted path must preserve exact OpenStudio
`ZoneHVAC:UnitHeater` fan/coil semantics; the older
`Baseboard/DHWBaseboard` surrogate remains rejected diagnostic history only.

## User Prompt And Keywords

- Prompt: `对 Room1 添加热水盘管单元加热器。`
- Keywords: Room1, unit heater, hot-water coil, zone equipment

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- For the Python Ironbug Console matrix, start from a fresh Garden when the user asks for a complete MCP proof. Create the Honeybee Model, Room1, setpoint, and weather evidence through Ladybug Tools MCP in that Garden.
- A retained prepared Garden is still valid for replay or diagnosis only if it already contains configured Room1 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same room.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

1. Create Room1 ThermalZone.
2. Create `detailed_hvac_fan_on_off`.
3. Create `detailed_hvac_coil_heating_water` with numeric water flow, UA, and
   rated inlet/outlet water and air temperatures.
4. Create `detailed_hvac_zone_equipment_unit_heater` with fan, heating coil, and
   ThermalZone.
5. Create hot-water loop: constant-speed pump plus either
   `detailed_hvac_district_heating_water` or `detailed_hvac_boiler_hot_water`
   on supply, heating coil on demand. For the current district-heating path,
   use a hot-water loop setpoint around `82.2` C to match the water coil rated
   inlet temperature and avoid EnergyPlus UA autosizing failure.
6. Use a cold-weather EPW query such as Chicago, Boston, or Minneapolis so the
   heating-only unit heater produces positive EUI. Do not use Sanya or Miami
   for this case.
7. Apply, run Energy, read EUI/ERR/SQL.

## Short Anti-Patterns

- `detailed_hvac_thermal_zone` has no `honeybee_room_identifier` parameter. Use
  `identifier` and `name` for Room1, then select Room1 when applying HVAC.
- `detailed_hvac_zone_equipment_unit_heater` uses `fan_target`, not
  `supply_fan_target`.
- `detailed_hvac_pump_constant_speed` uses `rated_pump_head`,
  `rated_flow_rate`, `motor_efficiency`, and `pump_control_type`; do not use
  `nominal_flow_rate` or `nominal_head`.
- `energyplus_start_simulation` uses `model_target`, not
  `honeybee_model_target`. Read the run id from the returned run target.
- `energyplus_read_eui` exposes the positive EUI value at
  `eui_result["eui"]["eui"]`; do not let `total_energy == 0` overwrite the
  acceptance EUI value.
- Code Mode does not support `with` statements.
- If a retry sees an existing Ironbug object, reuse the target or call the same
  create tool with the same identifier and `overwrite=True`; do not keep
  replaying the whole Garden.

## Expected MCP Return

Return compact JSON-compatible evidence with `case_id`, `status`,
`garden_target`, `building_model_target`, `rooms`, `ironbug_model_target`,
`detailed_hvac_application`, optional `energy_run_id`, optional
`energy_run_target`, optional structured `eui`, optional structured `err`,
optional structured `sql`, `python_ironbug_console_runtime`, `rerun_command`,
and `blocker`. For a pass, set `status` to `mimo-v25-case-pass`, make
`blocker` null, and include Python Console runtime evidence with
`simulation_input_kind="openstudio_osm"`,
`csharp_ironbug_console_required=false`, empty `writer_diagnostics`, and
`compiler_reports` showing
`IB_ZoneHVACUnitHeater -> OS:ZoneHVAC:UnitHeater`.

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard Ladybug Tools
MCP Energy simulation and same-run EUI/ERR/SQL readback. For Python-only matrix
acceptance, the run must be under
`LBT_REQUIRE_PYTHON_IRONBUG_CONSOLE_ONLY=1`, must report
`csharp_ironbug_console_required=false`, must have positive finite EUI, ERR
severe/fatal counts of 0, SQL present, and must preserve exact UnitHeater
semantics. If the runtime can only translate to `Baseboard/DHWBaseboard`, return
the precise blocker and any available ERR/SQL paths instead of reporting a pass.

This operation path is projected from
`docs/llm-wiki/evidence/python-ironbug-console-matrix-2026-05-29.md`; keep run
ids, EUI values, ERR counts, token/cost, and artifact paths in that evidence
page rather than copying them into this Skill.

Do not use `detailed_hvac_district_heating`. Do not create DOAS, chilled-water
loops, load-profile plant demand, or generic PlantLoop tools.
