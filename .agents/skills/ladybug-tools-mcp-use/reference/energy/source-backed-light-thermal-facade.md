# Source-Backed Light Thermal Facade Case

Use this staged workflow when a user asks for a real forum/paper-style Honeybee light-and-thermal facade case with WWR, simplified shading, hot-humid weather, EnergyPlus EUI, and Radiance daylight proof on the same Honeybee Model.

## Preconditions

- Treat this as a simulation-chain proof, not an optimization workflow.
- Keep source framing and retained-run evidence in LLM-Wiki.
- Do not claim annual daylight, comfort, or optimization outcomes unless the corresponding tools and outputs are run.

## Turn 1: Concept

Explain the case and boundaries. Do not inspect or edit the Garden.

## Turn 2: Base Honeybee Room

Create or initialize the Garden, create one Honeybee Model, create one shoebox Room, confirm the base model and Room, then stop.

Tools: `garden_create`, `honeybee_create_model`, `honeybee_create_room`, `garden_get_base_honeybee_model`, `honeybee_search_model_objects`.

## Turn 3: Facade And Validation

Resume from the Garden. Search the existing Room and exterior Face targets, create one by-ratio Aperture, create one simplified overhang/louver, optionally create a low-e window construction and ConstructionSet, assign generic office properties, and validate.

```python
rooms = await call_tool("honeybee_search_model_objects", {"garden_root": garden_root, "object_type": "room"})
room_target = rooms["matches"][0]["target"]
faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_target,
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
front_face_target = None
for match in faces["matches"]:
    if "Front" in match["identifier"]:
        front_face_target = match["target"]
        break
if front_face_target is None:
    return {"status": "blocked", "reason": "front exterior face not found"}
aperture = await call_tool("honeybee_create_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": front_face_target,
    "generation_mode": "by_ratio",
    "ratio": 0.6
})
shade = await call_tool("honeybee_create_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": aperture["target"],
    "generation_mode": "louver_by_count",
    "parameters": {"depth": 0.8, "louver_count": 1}
})
validation = await call_tool("honeybee_validate_model", {"garden_root": garden_root})
```

Use explicit loops over tool results; they are easier to recover than generator shortcuts.

## Turn 4: Energy Proof

Search weather with query `Sanya`, download EPW/DDY into the Garden, start an annual Energy run with the returned weather target, poll with `energyplus_poll_simulation`, and read bounded EUI only after completion.

Tools: `energyplus_search_epw_map`, `energyplus_download_epw`, `energyplus_start_simulation`, `energyplus_poll_simulation`, `energyplus_list_run_outputs`, `energyplus_read_eui`.

If the run is still running, return the Energy run target and status. Do not start a duplicate run.

## Turn 5: Radiance Point-In-Time Proof

Create a tiny explicit desk-height SensorGrid, create a CIE clear sky, create Radiance parameters, start a point-in-time grid run, and poll.

Tools: `radiance_create_sensor_grid`, `radiance_create_cie_standard_sky`, `radiance_create_parameters`, `radiance_start_grid_simulation`, `radiance_poll_simulation`.

## Stop Conditions

- Do not call the Radiance proof UDI, sDA, DA, or annual daylight.
- Do not rebuild the room after a sky parameter failure; repair the sky call.
- Do not claim thermal comfort percentage or PMV without explicit comfort outputs.
- Not yet recommended: full annual UDI/sDA optimization, dynamic louver schedules for EnergyPlus, or complex fenestration/BSDF shade thermal modeling.
