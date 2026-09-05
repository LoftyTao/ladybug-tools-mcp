# Case Skill: unit_heater_single

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 添加热水盘管单元加热器。`. Keep the system family and served-room list exactly aligned with this case (["Room1"]) unless you intentionally switch to the family workflow for a variant.

Python Ironbug Console route: accepted on the direct OSM runtime path. The
accepted path must preserve exact OpenStudio
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
2. Create `IB_fan_on_off`.
3. Create `IB_coil_heating_water` with numeric water flow, UA, and
   rated inlet/outlet water and air temperatures.
4. Create `IB_zone_equipment_unit_heater` with fan, heating coil, and
   ThermalZone.
5. Create hot-water loop: constant-speed pump plus either
   `IB_district_heating_water` or `IB_boiler_hot_water`
   on supply, heating coil on demand. For the current district-heating path,
   use a hot-water loop setpoint around `82.2` C to match the water coil rated
   inlet temperature and avoid EnergyPlus UA autosizing failure.
6. Use a cold-weather EPW query such as Chicago, Boston, or Minneapolis so the
   heating-only unit heater produces positive EUI. Do not use Sanya or Miami
   for this case.
7. Apply, run Energy, read EUI/ERR/SQL.

## Short Anti-Patterns

- `IB_thermal_zone` has no `honeybee_room_identifier` parameter. Use
  `identifier` and `name` for Room1, then select Room1 when applying HVAC.
- `IB_zone_equipment_unit_heater` uses `fan_target`, not
  `supply_fan_target`.
- `IB_pump_constant_speed` uses `rated_pump_head`,
  `rated_flow_rate`, `motor_efficiency`, and `pump_control_type`; do not use
  `nominal_flow_rate` or `nominal_head`.
- `EP_start_simulation` uses `model_target`, not
  `honeybee_model_target`. Use the returned run target for follow-up reads.
- `EP_read_eui` exposes the positive EUI value at
  `eui_result["eui"]["eui"]`; do not let `total_energy == 0` overwrite the
  acceptance EUI value.
- Code Mode does not support `with` statements.
- If a retry sees an existing Ironbug object, reuse the target or call the same
  create tool with the same identifier and `overwrite=True`; do not keep
  replaying the whole Garden.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "<selected Garden root>"
case_id = "unit_heater_single"
rooms = ["Room1"]

base = await call_tool("HB_create_model", {
    "garden_root": garden_root,
    "identifier": case_id + "_model",
})
ironbug = await call_tool("IB_create_model", {
    "garden_root": garden_root,
    "identifier": case_id,
    "overwrite": True,
})

# Create Room1 ThermalZone, OnOff fan, hot-water coil, UnitHeater, pump, and
# hot-water source described in MCP Tool Chain above. Keep returned targets.

applied = await call_tool("IB_apply_to_honeybee_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug["target"],
    "honeybee_model_target": base["target"],
    "room_identifiers": rooms,
    "detailed_hvac_identifier": case_id + "_detailed_hvac",
})
run = await call_tool("EP_start_simulation", {
    "garden_root": garden_root,
    "model_target": applied["updated_model_target"],
    "weather_target": "<cold-weather EPW target created or registered in this Garden>",
    "run_id": case_id + "_run",
})
status = await call_tool("EP_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "wait_seconds": 60,
    "poll_interval": 2,
})
outputs = await call_tool("EP_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": run["target"],
})
eui = await call_tool("EP_read_eui", {
    "garden_root": garden_root,
    "run_target": run["target"],
})
return {
    "case_id": case_id,
    "status": "accepted-case-pass",
    "garden_target": "<garden target>",
    "building_model_target": base["target"],
    "rooms": rooms,
    "ironbug_model_target": ironbug["target"],
    "detailed_hvac_target": applied.get("detailed_hvac_target"),
    "detailed_hvac_application": {
        "status": "applied",
        "model_target": base["target"],
        "ironbug_model_target": ironbug["target"],
        "detailed_hvac_target": applied.get("detailed_hvac_target"),
        "updated_model_target": applied["updated_model_target"],
    },
    "energy_run_id": run["target"]["run_id"],
    "energy_run_target": run["target"],
    "energy_status": status["summary_view"]["status"],
    "eui": {"total": eui["eui"]["eui"], "run_id": run["target"]["run_id"]},
    "err": "<structured ERR exists/path/warning/severe/fatal summary>",
    "sql": "<structured SQL exists/path/run_id summary>",
    "python_ironbug_console_runtime": status.get("python_ironbug_console_runtime"),
    "rerun_command": "<minimum pytest rerun command>",
    "blocker": None,
}
```

## Expected MCP Return

Return compact JSON-compatible evidence with `case_id`, `status`,
`garden_target`, `building_model_target`, `rooms`, `ironbug_model_target`,
`detailed_hvac_target`, `detailed_hvac_application`, optional `energy_run_id`, optional
`energy_run_target`, `energy_status`, optional structured `eui`, optional structured `err`,
optional structured `sql`, `python_ironbug_console_runtime`, `rerun_command`,
and `blocker`. For a pass, set `status` to `accepted-case-pass`, make
`blocker` null, and include Python Console runtime evidence with
`simulation_input_kind="openstudio_osm"`,
`csharp_ironbug_console_required=false`, empty `writer_diagnostics`, and
`compiler_reports` showing
`IB_ZoneHVACUnitHeater -> OS:ZoneHVAC:UnitHeater`.

## Code Mode Return Example

```jsonc
{
  "case_id": "unit_heater_single",
  "status": "accepted-case-pass",
  "garden_target": {"target_type": "garden", "garden_id": "<garden_id>"},
  "building_model_target": {"target_type": "honeybee_model", "path": "<hbjson path>"},
  "rooms": ["Room1"],
  "ironbug_model_target": {"target_type": "ironbug_model", "path": "<ibjson path>"},
  "detailed_hvac_target": "<IB_apply_to_honeybee_model.detailed_hvac_target>",
  "detailed_hvac_application": {
    "status": "applied",
    "model_target": {"target_type": "honeybee_model", "path": "<source hbjson path>"},
    "ironbug_model_target": {"target_type": "ironbug_model", "path": "<ibjson path>"},
    "detailed_hvac_target": "<IB_apply_to_honeybee_model.detailed_hvac_target>",
    "updated_model_target": {"target_type": "honeybee_model", "path": "<updated hbjson path>"}
  },
  "energy_run_id": "<energy_run_id>",
  "energy_run_target": {"target_type": "energy_run", "run_id": "<energy_run_id>"},
  "energy_status": "completed",
  "eui": {"total": 123.456, "run_id": "<energy_run_id>"},
  "err": {
    "exists": true,
    "path": "<extract eplusout.err from outputs>",
    "warning_count": 0,
    "severe_count": 0,
    "fatal_count": 0
  },
  "sql": {
    "exists": true,
    "path": "<extract eplusout.sql from outputs>",
    "run_id": "<energy_run_id>"
  },
  "python_ironbug_console_runtime": {
    "status": "translated",
    "simulation_input_kind": "openstudio_osm",
    "csharp_ironbug_console_required": false,
    "compiler_reports": ["IB_ZoneHVACUnitHeater -> OS:ZoneHVAC:UnitHeater"]
  },
  "rerun_command": "<minimum pytest rerun command>",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard Ladybug Tools
MCP Energy simulation and same-run EUI/ERR/SQL readback. For Python-only matrix
acceptance, the run must be under
`LBT_REQUIRE_PYTHON_IRONBUG_CONSOLE_ONLY=1`, must report
`csharp_ironbug_console_required=false`, must have positive finite EUI, ERR
severe/fatal counts of 0, SQL present, and must preserve exact UnitHeater
semantics. If the runtime can only translate to `Baseboard/DHWBaseboard`, return
the precise blocker and any available ERR/SQL paths instead of reporting a pass.


Do not use `IB_district_heating`. Do not create DOAS, chilled-water
loops, load-profile plant demand, or generic PlantLoop tools.
