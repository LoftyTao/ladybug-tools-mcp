# Case Skill: doas_only_three_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 到 Room3 添加只送新风的 DOAS。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2", "Room3"]) unless you intentionally switch to the family workflow for a variant.

Status: accepted for the direct Python Ironbug Console OpenStudio OSM path. The
Energy model must be produced as `pyironbug.osm`; do not use the C# Console or a
Honeybee template HVAC surrogate.

## User Prompt And Keywords

- Prompt: `对 Room1 到 Room3 添加只送新风的 DOAS。`
- Keywords: Room1-Room3, DOAS, outdoor air, no-reheat terminal

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- The Garden must already contain configured Rooms Room1, Room2, Room3 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

1. Create mechanical ventilation controller.
2. Create outdoor-air controller with `mechanical_ventilation_target`.
3. Create constant- or variable-volume supply fan.
4. Create outdoor-air system with `controller_outdoor_air_target` and
   `oa_stream_targets=[supply_fan]`.
5. For Room1 through Room3, create one no-reheat air terminal and one matching
   ThermalZone with `air_terminal`.
6. Create AirLoopBranches with `[[zone1], [zone2], [zone3]]`.
7. Create AirLoopHVAC with `[outdoor_air_system, supply_fan]` on supply and the
   branch object on demand.
8. Apply, run Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "doas_only_three_room"
rooms = ["Room1", "Room2", "Room3"]

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
`energy_status` must be `completed` and `eui` must be non-null for a pass.
`python_ironbug_console_runtime` must report `status == "translated"`,
`simulation_input_kind == "openstudio_osm"`, a `runtime_model_path` ending in
`pyironbug.osm`, `compiled_room_count == 3`, and
`csharp_ironbug_console_required == false`.

## Code Mode Return Example

```jsonc
{
  "case_id": "doas_only_three_room",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1", "Room2", "Room3"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/doas_only_three_room_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/doas_only_three_room_run/annual_energy_use/run/eplusout.sql",
  "python_ironbug_console_runtime": {
    "status": "translated",
    "simulation_input_kind": "openstudio_osm",
    "runtime_model_path": "runs/energy/doas_only_three_room_run/pyironbug.osm",
    "compiled_room_count": 3,
    "csharp_ironbug_console_required": false,
    "expected_openstudio_objects": {
      "OS:AirLoopHVAC": 1,
      "OS:AirLoopHVAC:OutdoorAirSystem": 1,
      "OS:Controller:OutdoorAir": 1,
      "OS:Controller:MechanicalVentilation": 1,
      "OS:Fan:ConstantVolume": 1,
      "OS:AirTerminal:SingleDuct:ConstantVolume:NoReheat": 3
    }
  },
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and EUI readback from the Python Console
OSM. If the run fails, return the precise blocker and any available ERR/SQL
paths instead of rebuilding the whole graph.

Do not bind `oa_stream_targets` to ThermalZones or branches. Do not create FCUs,
plant loops, or load-profile demand.
