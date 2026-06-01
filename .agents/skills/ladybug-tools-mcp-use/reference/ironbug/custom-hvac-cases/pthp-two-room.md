# Case Skill: pthp_two_room

## Applicable Scenario

Use this case when the request matches the retained prompt: `对 Room1 和 Room2 都添加 PTHP。`. Keep the system family and served-room list exactly aligned with this case (["Room1", "Room2"]) unless you intentionally switch to the family workflow for a variant.

## User Prompt And Keywords

- Prompt: `对 Room1 和 Room2 都添加 PTHP。`
- Keywords: Room1, Room2, PTHP, packaged terminal heat pump

## Case Preconditions

- Load `index.md` and `../ironbug-room-energy-preconditions.md` first.
- For the Python Ironbug Console matrix, start from a fresh Garden when the user asks for a complete MCP proof. Create the Honeybee Model, Room1, Room2, setpoint, and weather evidence through Ladybug Tools MCP in that Garden.
- A retained prepared Garden is still valid for replay or diagnosis only if it already contains configured Rooms Room1 and Room2 in the base Honeybee Model, or an explicitly retained Dragonfly path for the same rooms.
- Use the current Honeybee DetailedHVAC route for this retained case unless the test is intentionally validating a Dragonfly variant.

## MCP Tool Chain

Repeat the PTHP path for Room1 and Room2.

1. For each room, create a matching ThermalZone.
2. For each room, create OnOff fan, DX heating coil, DX cooling coil, and
   electric supplemental heating coil.
3. Create one PTHP per room and bind it to the matching ThermalZone.
4. Apply once to both rooms, run standard Energy, read EUI/ERR/SQL.

## Code Mode Call Example

```python
# Inside Ladybug Tools MCP Code Mode execute.
garden_root = "D:/path/to/artifact-garden"
case_id = "pthp_two_room"
rooms = ["Room1", "Room2"]

# Create or reuse the case Garden and create Room1 / Room2 through MCP before
# applying the Ironbug HVAC. For matrix acceptance, do not assume a prebuilt
# Honeybee Model unless the retained artifact explicitly says so.
base = await call_tool("honeybee_create_model", {
    "garden_root": garden_root,
    "identifier": case_id + "_model",
})
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
    "weather_target": "<weather_file target created or downloaded in this Garden>",
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
    "status": "mimo-v25-case-pass",
    "garden_target": "<garden target>",
    "building_model_target": base["target"],
    "rooms": rooms,
    "ironbug_model_target": ironbug["target"],
    "detailed_hvac_application": {
        "status": "applied",
        "model_target": base["target"],
        "ironbug_model_target": ironbug["target"],
        "updated_model_target": applied["updated_model_target"],
    },
    "energy_run_id": run["target"]["run_id"],
    "energy_run_target": run["target"],
    "energy_status": status["summary_view"]["status"],
    "eui": {"total": eui["eui"], "run_id": run["target"]["run_id"]},
    "err": "<structured ERR exists/path/warning/severe/fatal summary>",
    "sql": "<structured SQL exists/path/run_id summary>",
    "python_ironbug_console_runtime": status.get("python_ironbug_console_runtime"),
    "compliant_numeric_result": True,
    "rerun_command": "<minimum pytest rerun command>",
    "blocker": None,
}
```

## Expected MCP Return

Return compact JSON-compatible evidence with `case_id`, `status`,
`garden_target`, `building_model_target`, `rooms`, `ironbug_model_target`,
`detailed_hvac_application`, `energy_run_id`, `energy_run_target`,
`energy_status`, structured `eui`, structured `err`, structured `sql`,
`python_ironbug_console_runtime`, `compliant_numeric_result`, `rerun_command`,
and `blocker`. `energy_status` must be `completed`,
`python_ironbug_console_runtime.csharp_ironbug_console_required` must be false,
and `eui.total` must be non-null for a pass.

## Code Mode Return Example

```jsonc
{
  "case_id": "pthp_two_room",
  "status": "mimo-v25-case-pass",
  "garden_target": {"target_type": "garden", "garden_id": "<garden_id>"},
  "building_model_target": {"target_type": "honeybee_model", "path": "<hbjson path>"},
  "rooms": ["Room1", "Room2"],
  "ironbug_model_target": {"target_type": "ironbug_model", "path": "<ibjson path>"},
  "detailed_hvac_application": {
    "status": "applied",
    "model_target": {"target_type": "honeybee_model", "path": "<source hbjson path>"},
    "ironbug_model_target": {"target_type": "ironbug_model", "path": "<ibjson path>"},
    "updated_model_target": {"target_type": "honeybee_model", "path": "<updated hbjson path>"}
  },
  "energy_run_id": "<energy_run_id>",
  "energy_run_target": {"target_type": "energy_run", "run_id": "<energy_run_id>"},
  "energy_status": "completed",
  "eui": {"total": 123.456, "run_id": "<energy_run_id>"},
  "err": {
    "exists": true,
    "path": "runs/energy/<energy_run_id>/annual_energy_use/run/eplusout.err",
    "warning_count": 0,
    "severe_count": 0,
    "fatal_count": 0
  },
  "sql": {
    "exists": true,
    "path": "runs/energy/<energy_run_id>/annual_energy_use/run/eplusout.sql",
    "run_id": "<energy_run_id>"
  },
  "python_ironbug_console_runtime": {
    "status": "translated",
    "csharp_ironbug_console_required": false,
    "conversion_count": 2
  },
  "compliant_numeric_result": true,
  "rerun_command": "<minimum pytest rerun command>",
  "blocker": null
}
```

## Case Notes

Acceptance requires Ironbug DetailedHVAC application plus standard
Ladybug Tools MCP Energy simulation and same-run EUI/ERR/SQL readback. For
Python-only matrix acceptance, the run must be under
`LBT_REQUIRE_PYTHON_IRONBUG_CONSOLE_ONLY=1`, must report
`csharp_ironbug_console_required=false`, and must have positive finite EUI,
ERR severe/fatal counts of 0, and SQL present. If the run fails, return the
precise blocker and any available ERR/SQL paths instead of rebuilding the whole
graph.

This operation path is projected from
`docs/llm-wiki/evidence/python-ironbug-console-matrix-2026-05-29.md`; keep run
ids, EUI values, ERR counts, token/cost, and artifact paths in that evidence
page rather than copying them into this Skill.

Do not share one PTHP between rooms. Do not create hydronic loops, DOAS, or
AirLoopHVAC.
