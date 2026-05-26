# Case Skill: radiant_doas_three_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 到 Room3 添加热水辐射末端和带冷却的新风系统。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2", "Room3"]) unless you intentionally switch to the family workflow for a variant.

## User Prompt And Keywords

- Prompt: `对 Room1 到 Room3 添加热水辐射末端和带冷却的新风系统。`
- Keywords: Room1-Room3, hot-water radiant, baseboard radiant, cooled DOAS

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- The Garden must already contain configured Rooms Room1, Room2, Room3 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

Use hot-water baseboard radiant zone equipment plus cooled DOAS.

For Room1 through Room3:

1. Create no-reheat DOAS air terminal.
2. Create `detailed_hvac_coil_heating_water_baseboard_radiant` with exact
   `"Autosize"` strings for maximum water flow and heating design capacity.
3. Create `detailed_hvac_zone_equipment_baseboard_radiant_convective_water` with
   `fraction_radiant=0.5`.
4. Create matching ThermalZone with `air_terminal`,
   `zone_equipments_targets=[baseboard_target]`, and
   `is_air_terminal_before_zone_equipments=True`.

DOAS supply order: outdoor-air system, DX single-speed cooling coil, scheduled
cooling setpoint manager around 13 C, constant-volume supply fan. Create
hot-water loop with pump + district-heating-water serving all radiant coils.
Apply, run Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "radiant_doas_three_room"
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
`err_path`, `sql_path`, and `blocker`. `energy_status` must be `completed` and
`eui` must be non-null for a pass.

## Code Mode Return Example

```jsonc
{
  "case_id": "radiant_doas_three_room",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1", "Room2", "Room3"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/radiant_doas_three_room_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/radiant_doas_three_room_run/annual_energy_use/run/eplusout.sql",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and EUI readback. If the run fails, return
the precise blocker and any available ERR/SQL paths instead of rebuilding the
whole graph.

Do not use low-temperature radiant variable-flow coils or
`detailed_hvac_zone_equipment_low_temp_radiant_var_flow` for current Energy
acceptance.
