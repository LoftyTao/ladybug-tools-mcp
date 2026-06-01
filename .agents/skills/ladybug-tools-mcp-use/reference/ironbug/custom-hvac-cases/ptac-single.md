# Case Skill: ptac_single

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 添加 PTAC，并设置风机的供应量为自动调节。`. Keep the system family and served-room list exactly aligned with this case (["Room1"]) unless you intentionally switch to the family workflow for a variant.

## User Prompt And Keywords

- Prompt: `对 Room1 添加 PTAC，并设置风机的供应量为自动调节。`
- Keywords: Room1, PTAC, packaged terminal AC, autosized fan

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- The Garden must already contain configured Rooms Room1 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

Use Room1 only.

1. Create the Ironbug model with `detailed_hvac_create_model` and keep its
   returned `target`.
2. Create one `detailed_hvac_thermal_zone` with the same
   `ironbug_model_target`, `identifier="Room1"`, and `name="Room1"`. Do not
   pass `room_identifier`.
3. Create `detailed_hvac_fan_on_off` with the same `ironbug_model_target` and
   autosized maximum flow.
4. Create `detailed_hvac_coil_heating_electric` with the same
   `ironbug_model_target`.
5. Create `detailed_hvac_coil_cooling_dx_single_speed` with the same
   `ironbug_model_target`.
6. Create `detailed_hvac_zone_equipment_ptac` with the same
   `ironbug_model_target`,
   the fan, heating coil, cooling coil, and ThermalZone targets. Autosize
   cooling/heating/no-load supply air flow rates. The fan argument is
   `fan_target`, not `supply_fan_target`.
7. Apply to the Honeybee model, run standard Energy, read EUI, ERR, and SQL.

For a fresh Python Ironbug Console case, create the Honeybee Model first and pass
that model target into `honeybee_create_room`. Configure Room1 with
`program_type="Generic Office Program"` and pass the `energy_create_setpoint`
returned target as `setpoint`; do not create a ProgramType unless the user asks
for a custom one.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "ptac_single"
rooms = ["Room1"]

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
  "case_id": "ptac_single",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/ptac_single_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/ptac_single_run/annual_energy_use/run/eplusout.sql",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and EUI readback. If the run fails, return
the precise blocker and any available ERR/SQL paths instead of rebuilding the
whole graph.

Use the standard Energy tool argument names: `energyplus_start_simulation`
receives `model_target`, while poll/list/read tools should use the returned
`run_target` or a schema-supported run id field. Avoid ad hoc result-shape
probing; Code Mode `await call_tool(...)` returns the tool result dict.

Do not create plant loops, DOAS, AirLoopHVAC, NoAirLoop, load-profile plant
demand, or Ironbug-only simulation runs.
