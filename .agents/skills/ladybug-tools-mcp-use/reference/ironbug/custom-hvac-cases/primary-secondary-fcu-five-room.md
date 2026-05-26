# Case Skill: primary_secondary_fcu_five_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `给五个房间添加一次二次冷冻水系统服务的风机盘管。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2", "Room3", "Room4", "Room5"]) unless you intentionally switch to the family workflow for a variant.

## User Prompt And Keywords

- Prompt: `给五个房间添加一次二次冷冻水系统服务的风机盘管。`
- Keywords: Room1-Room5, primary secondary chilled water, heat exchanger, FCU

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- The Garden must already contain configured Rooms Room1, Room2, Room3, Room4, Room5 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

Use the five-room FCU-only path, then build primary/secondary chilled water.

1. Create one fluid-to-fluid heat exchanger with
   `control_type="CoolingDifferentialOnOff"`.
2. Primary chilled-water loop: constant-speed pump + district cooling on
   supply, heat exchanger on demand.
3. Secondary chilled-water loop: variable-speed pump + same heat exchanger on
   supply, all five FCU cooling coils on demand.
4. Hot-water loop: pump + district-heating-water serving all five FCU heating
   coils.
5. Apply, run Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/prepared-garden"
case_id = "primary_secondary_fcu_five_room"
rooms = ["Room1", "Room2", "Room3", "Room4", "Room5"]

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
  "case_id": "primary_secondary_fcu_five_room",
  "garden_root": "D:/path/to/prepared-garden",
  "rooms": ["Room1", "Room2", "Room3", "Room4", "Room5"],
  "ironbug_model_target": "<detailed_hvac_create_model.target>",
  "detailed_hvac_target": "<detailed_hvac_apply_to_honeybee_model.detailed_hvac_target>",
  "energy_status": "completed",
  "eui": 123.456,
  "err_path": "runs/energy/primary_secondary_fcu_five_room_run/annual_energy_use/run/eplusout.err",
  "sql_path": "runs/energy/primary_secondary_fcu_five_room_run/annual_energy_use/run/eplusout.sql",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and EUI readback. If the run fails, return
the precise blocker and any available ERR/SQL paths instead of rebuilding the
whole graph.

Deterministic-contract-pass: for Energy-ready hot-water coils in FCU, reheat,
or unit-heater paths, use numeric `u_factor_times_area_value` and
`maximum_water_flow_rate` when the coil uses
`UFactorTimesAreaAndDesignWaterFlowRate`. If readiness reports
`ironbug_embedded_component_stale_after_overwrite`, rebuild the owning FCU,
terminal, or plant graph from the latest component targets before applying
DetailedHVAC or starting Energy.

Do not use `CoolingSetpointOnOffWithComponentOverride` unless override inlet
nodes are modeled. Do not add DOAS, AirLoopHVAC, load-profile plant demand, or
generic PlantLoop tools.
