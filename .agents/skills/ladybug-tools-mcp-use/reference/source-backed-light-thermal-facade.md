# Source-Backed Light/Thermal Facade Case

## Scope

Use this reference when a user asks for a real forum/paper-style Honeybee light-and-thermal facade case: WWR, simplified shading, Sanya or hot-humid weather, EnergyPlus EUI, and Radiance daylight proof on the same Honeybee Model.


## Source Case

- Paper source: PLOS One 2025, hot-humid fenestration and shading system optimization for energy, view, daylight, and thermal comfort.
- Forum boundary: complex sub-centimeter shade geometry is not practical for EnergyPlus; use simplified shade geometry for Energy and reserve detail for Radiance when needed.
- Reference geometry: single south office room, approximately `7.2 m x 8.4 m x 3 m`, `0.6` WWR, simplified horizontal overhang or louver.

## Verified Stage Shape

### Turn 1: Concept Only

Explain the case and boundaries. Do not inspect or edit the Garden.

### Turn 2: Base Honeybee Room

Create or initialize the Garden, create one Honeybee Model, create one shoebox Room, and stop. Do not add windows, shades, weather, Energy, or Radiance in this turn.

Main tools:

- `create_garden`
- `create_honeybee_model`
- `create_honeybee_room`
- `get_base_honeybee_model`
- `search_honeybee_model_objects`

### Turn 3: Facade And Validation

Resume from the existing Garden. Search the existing room/face targets, create one by-ratio aperture, create one simplified overhang/louver, optionally create a simple low-e window construction and construction set, apply a generic office program/construction set to the room, then validate once.

Main tools:

- `search_honeybee_model_objects`
- `create_honeybee_apertures_by_parameters`
- `create_honeybee_shades_by_parameters`
- `create_window_construction`
- `create_construction_set`
- `edit_honeybee_room`
- `validate_honeybee_model`

Recommended aperture/shade pattern:

```python
rooms = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
})
room_target = rooms["matches"][0]["target"]
faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_target,
    "face_type": "Wall",
    "boundary_condition": "Outdoors",
})
front_face_target = None
for match in faces["matches"]:
    if "Front" in match["identifier"]:
        front_face_target = match["target"]
        break
if front_face_target is None:
    return {"status": "blocked", "reason": "front exterior face not found"}
aperture = await call_tool("create_honeybee_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": front_face_target,
    "generation_mode": "by_ratio",
    "ratio": 0.6,
})
shade = await call_tool("create_honeybee_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": aperture["target"],
    "generation_mode": "louver_by_count",
    "count": 1,
    "depth": 0.8,
})
validation = await call_tool("validate_honeybee_model", {
    "garden_root": garden_root,
})
return {
    "aperture_target": aperture["target"],
    "shade_target": shade["target"],
    "validation_is_valid": validation["summary_view"].get("is_valid"),
}
```

Do not use Python `next(...)` generator shortcuts over tool results; explicit loops make recovery easier for Agents.

### Turn 4: Energy Proof

Resume from the validated Garden. Search Sanya weather with the plain query `Sanya`, download the selected EPW/ DDY into the Garden, start an annual Energy run with the returned weather target, poll with `get_energy_run`, and read bounded EUI only after completion.

Main tools:

- `search_epw_map`
- `download_epw`
- `start_energy_run`
- `get_energy_run`
- `list_energy_run_outputs`
- `read_energy_eui`

Boundaries:

- Pass the full `weather_target` dict returned by `download_epw`, not a weather identifier string.
- If the run is still running, return the `energy_run` target and status. Do not start a duplicate run.
- If the EUI summary only includes lighting/equipment, report that HVAC assumptions are too simple for paper-grade thermal conclusions.

### Turn 5: Radiance Point-In-Time Proof

Resume from the same Garden. Create a tiny explicit desk-height SensorGrid, create a CIE clear sky with supported timezone shorthand, create grid parameters, start a point-in-time grid run, then poll with `get_radiance_run`.

Main tools:

- `create_radiance_sensor_grid`
- `create_cie_standard_sky`
- `create_radiance_parameters`
- `start_radiance_grid_run`
- `get_radiance_run`

Boundaries:

- This proves the daylight simulation chain only. Do not call it UDI, sDA, DA, or annual daylight.
- Use annual/matrix recipes later for UDI/sDA.
- If a sky call fails from timezone or missing month/day, repair the CIE sky call rather than rebuilding the room, aperture, or shade.

## Evidence

2026-05-18 OpenAI Agents SDK harness with `profile=mimo`, `model_name=mimo-v2.5-pro`, retained pass:

- Artifact root: `tests/.artifacts/agent_integration/honeybee_light_thermal_facade_mimo_v25_20260518_attempt1/honeybee_light_thermal_facade/`
- Scenario: `honeybee_light_thermal_facade`
- Result: `scenario_passed=true`, expected phrase found, no missing expected tools, no forbidden tools.
- Total cost: `432,574` tokens, `30` requests, `1 passed in 456.49s`.
- Energy: completed annual EnergyPlus run on Sanya weather, run `energy_20260517t165310`, EUI total `69.261 kWh/m2`, with persisted SQL and HTML outputs.
- Radiance: completed point-in-time grid run, run `radiance_20260517t165600`, 9 explicit sensors, CIE clear summer 10am sky, completed `rtrace`.

This pass is real but high-cost and noisy. It included recoverable drift such as duplicate weather/run starts, repeated Radiance setup calls, one invented Honeybee summary call, and several failed sky/parameter attempts. Treat this as a retained functional path, not a low-cost optimized path.

## Not Yet Recommended

- Full annual UDI/sDA optimization.
- Dynamic louver state schedules for EnergyPlus.
- Complex fenestration / BSDF shade thermal modeling.
- Claims about thermal comfort percentage or PMV without explicit comfort outputs.
