# Case Skill: cav_reheat_two_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 和 Room2 添加定风量再热中央空调。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2"]) unless you intentionally switch to the family workflow for a variant.

## User Prompt And Keywords

- Prompt: `对 Room1 和 Room2 添加定风量再热中央空调。`
- Keywords: Room1, Room2, CAV, constant volume, hot-water reheat

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- The Garden must already contain configured Rooms Room1, Room2 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.
- Acceptance requires Python Console direct OpenStudio OSM runtime evidence. Do
  not accept C# `Ironbug.Console`, Honeybee template HVAC, load-profile demand,
  or runtime HBJSON surrogate evidence for this case.

## MCP Tool Chain

For Room1 and Room2:

1. Create matching ThermalZone with
   `is_air_terminal_before_zone_equipments=True`.
2. Create hot-water reheat coil with numeric sizing/rated values.
3. Create constant-volume reheat terminal.

Then:

1. Create constant-volume supply fan.
2. Create AirLoopBranches with one branch per ThermalZone.
3. Create AirLoopHVAC with fan on supply and branches on demand.
4. Create boiler hot-water loop for all reheat coils, using one singleton
   parallel demand branch per reheat coil:
   `[[reheat_coil_1], [reheat_coil_2]]`.
5. Apply, run Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "cav_reheat_two_room"
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
    "python_ironbug_console_runtime": eui.get("python_ironbug_console_runtime"),
    "blocker": None,
}
```

## Expected MCP Return

Return compact JSON-compatible evidence with `case_id`, `garden_root`, `rooms`,
`ironbug_model_target`, `detailed_hvac_target`, `energy_status`, `eui`,
`err_path`, `sql_path`, `python_ironbug_console_runtime`, and `blocker`.
`energy_status` must be `completed` and `eui` must be non-null for a pass.
`python_ironbug_console_runtime` must show:

- `status == "translated"`.
- `compiler_stage == "detailed_hvac_specification_to_openstudio_model"`.
- `compiler_output_kind == "openstudio_model"`.
- `simulation_input_kind == "openstudio_osm"`.
- `compiled_room_count == 2`.
- A Garden-relative `.osm` runtime model path, normally `pyironbug.osm` under
  the Energy run directory.
- Empty writer diagnostics.
- `csharp_ironbug_console_required == false`.

Writer evidence must include at least:

- `IB_AirLoopHVAC -> OS:AirLoopHVAC`.
- `IB_AirLoopBranches -> OS:AirLoopHVAC:Branches`.
- Two `IB_AirTerminalSingleDuctConstantVolumeReheat ->
  OS:AirTerminal:SingleDuct:ConstantVolume:Reheat` objects.
- Two `IB_CoilHeatingWater -> OS:Coil:Heating:Water` objects.
- `IB_FanConstantVolume -> OS:Fan:ConstantVolume`.
- `IB_PlantLoop -> OS:PlantLoop`.
- `IB_PumpConstantSpeed -> OS:Pump:ConstantSpeed`.
- `IB_BoilerHotWater -> OS:Boiler:HotWater`.
- `IB_SetpointManagerScheduled -> OS:SetpointManager:Scheduled`.

## Code Mode Return Example

```jsonc
{
  "case_id": "cav_reheat_two_room",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1", "Room2"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/cav_reheat_two_room_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/cav_reheat_two_room_run/annual_energy_use/run/eplusout.sql",
  "python_ironbug_console_runtime": {
    "status": "translated",
    "runtime_model_path": "runs/energy/cav_reheat_two_room_run/pyironbug.osm",
    "compiler_stage": "detailed_hvac_specification_to_openstudio_model",
    "compiler_output_kind": "openstudio_model",
    "simulation_input_kind": "openstudio_osm",
    "writer_diagnostics": [],
    "compiled_room_count": 2,
    "csharp_ironbug_console_required": false
  },
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and EUI readback from the Python Console
OSM runtime. If the run fails, return the precise blocker and any available
ERR/SQL paths instead of rebuilding the whole graph.

Do not use load-profile demand, FCU, VRF, VAV, unitary rooftop, DOAS, or skip
the AirLoop demand branches.
