# Case Skill: fcu_two_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 和 Room2 添加四管风机盘管。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2"]) unless you intentionally switch to the family workflow for a variant.

Python Ironbug Console matrix status: accepted on the direct OSM runtime path.
The accepted path writes OpenStudio `ZoneHVAC:FourPipeFanCoil`, water coils,
PlantLoops, district sources, pumps, and scheduled setpoints through the Python
Console writer.

## User Prompt And Keywords

- Prompt: `对 Room1 和 Room2 添加四管风机盘管。`
- Keywords: Room1, Room2, four-pipe FCU, chilled water, hot water

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- For a complete MCP proof, start from a fresh Garden and create the Honeybee
  Model, Room1, Room2, setpoint, and weather evidence through Ladybug Tools MCP
  in that Garden. For replay or diagnosis, the Garden must already contain
  configured Rooms Room1 and Room2 in the base Honeybee Model, or an explicitly
  retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

For Room1 and Room2:

1. Create matching ThermalZone.
2. Create OnOff fan.
3. Create hot-water heating coil.
4. Create chilled-water cooling coil.
5. Create four-pipe FCU with heating coil, cooling coil, fan, and ThermalZone.
   Use `fan_target`, `cooling_coil_target`, `heating_coil_target`, and
   `thermal_zone_target`. Set `capacity_control_method="CyclingFan"` and
   autosize supply-air, cold-water, and hot-water flow rates.

Then create one shared chilled-water loop with pump + district cooling serving
both cooling coils, and one shared hot-water loop with pump +
district-heating-water serving both heating coils. Use numeric hot-water coil
readiness fields rather than `"Autosize"` for the UA/water-flow fields that the
tool exposes as numeric-only. Apply, run Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "fcu_two_room"
rooms = ["Room1", "Room2"]

base = await call_tool("garden_get_base_honeybee_model", {"garden_root": garden_root})
ironbug = await call_tool("detailed_hvac_create_model", {
    "garden_root": garden_root,
    "identifier": case_id,
    "include_hvac_system": True,
    "overwrite": True,
})

# Create the source-backed Ironbug components listed in MCP Tool Chain above.
# Keep the returned targets and pass those targets into later create/apply calls.

applied = await call_tool("detailed_hvac_apply_to_honeybee_model", {
    "garden_root": garden_root,
    "ironbug_model_target": ironbug["target"],
    "honeybee_model_target": base["target"],
    "room_identifiers": rooms,
    "detailed_hvac_identifier": case_id + "_detailed_hvac",
})
run = await call_tool("energyplus_start_simulation", {
    "garden_root": garden_root,
    "model_target": applied["updated_model_target"],
    "weather_target": "<prepared Garden weather_file target>",
    "run_id": case_id + "_run",
})
status = await call_tool("energyplus_poll_simulation", {
    "garden_root": garden_root,
    "run_target": run["target"],
    "wait_seconds": 60,
    "poll_interval": 2,
})
outputs = await call_tool("energyplus_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": run["target"],
})
eui = await call_tool("energyplus_read_eui", {
    "garden_root": garden_root,
    "run_target": run["target"],
})
return {
    "case_id": case_id,
    "garden_root": garden_root,
    "rooms": rooms,
    "ironbug_model_target": ironbug["target"],
    "detailed_hvac_target": applied.get("detailed_hvac_target"),
    "energy_status": status["summary_view"]["status"],
    "eui": eui.get("eui"),
    "err_path": "<extract eplusout.err from outputs>",
    "sql_path": "<extract eplusout.sql from outputs>",
    "blocker": None,
}
```

## Expected MCP Return

Return compact JSON-compatible evidence with `case_id`, `garden_root`, `rooms`,
`ironbug_model_target`, `detailed_hvac_target`, `energy_status`, `eui`,
`err_path`, `sql_path`, `python_ironbug_console_runtime`, and `blocker`.
`energy_status` must be `completed`, `eui` must be positive, ERR severe/fatal
counts must be 0, SQL must exist, and `blocker` must be null for a pass. The
runtime evidence must include `simulation_input_kind="openstudio_osm"`,
`csharp_ironbug_console_required=false`, empty `writer_diagnostics`, and
`compiler_reports` showing `IB_ZoneHVACFourPipeFanCoil ->
OS:ZoneHVAC:FourPipeFanCoil`, water coils, `IB_PlantLoop`, district sources,
pumps, and scheduled setpoints.

## Code Mode Return Example

```jsonc
{
  "case_id": "fcu_two_room",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1", "Room2"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/fcu_two_room_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/fcu_two_room_run/annual_energy_use/run/eplusout.sql",
  "python_ironbug_console_runtime": "<runtime dict from Energy run>",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and same-run EUI/ERR/SQL readback. For
Python-only matrix acceptance, the run must be under
`LBT_REQUIRE_PYTHON_IRONBUG_CONSOLE_ONLY=1`, must use a Garden-relative
`pyironbug.osm` runtime model, and must not require C# `Ironbug.Console`. If the
run fails, return the precise blocker and any available ERR/SQL paths instead
of rebuilding the whole graph.

This operation path is projected from
`docs/llm-wiki/evidence/python-ironbug-console-matrix-2026-05-29.md`; keep run
ids, EUI values, ERR counts, token/cost, and artifact paths in that evidence
page rather than copying them into this Skill.

On Windows/OpenStudio, avoid very long Garden roots for full Energy proofs. If
OpenStudio says a seed model or EPW is missing while the file exists, retry
under a shorter Garden path before changing the HVAC graph.

Do not create DOAS, AirLoopHVAC, NoAirLoop, load-profile demand, or generic
PlantLoop tools.
