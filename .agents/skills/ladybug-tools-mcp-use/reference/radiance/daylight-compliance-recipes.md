# Radiance Daylight Compliance Recipes

Use this reference for LEED daylight Option 1/2, EN 17037, WELL daylight, or BREEAM 4b.
## Select the recipe and inputs

Use a Garden Honeybee Model with exterior apertures and attached SensorGrids.
Select unique grid identifiers; LEED Option 2, EN 17037, and BREEAM require empty `group_identifier` values.
For results based on actual area, create grids from room floor Faces and attach them directly to retain the mesh.
BREEAM also requires a valid room association; a room floor Face supplies it automatically.

| Recipe | Start tool | Weather and specific inputs |
| --- | --- | --- |
| LEED Option 2 | `RAD_start_leed_daylight_option_two` | Annual `wea_target`; use `glare_control_devices="no-glare-control"` unless view-preserving automatic controls with manual override exist |
| EN 17037 | `RAD_start_annual_daylight_en17037` | Annual hourly EPW `weather_file_target`; optional `grid_metrics` and `thresholds` only affect accompanying annual metrics |
| LEED Option 1 | `RAD_start_leed_daylight_option_one` | Annual `wea_target`; optional `diffuse_transmission` and `specular_transmission` |
| WELL | `RAD_start_well_daylight` | Annual hourly EPW `weather_file_target`; optional `diffuse_transmission` and `specular_transmission` |
| BREEAM 4b | `RAD_start_breeam_daylight_4b` | Annual `wea_target`; confirm the room program type, since unrecognized types use office criteria |

Use weather targets from `EP_import_local_weather` or `EP_search_weather_files`.
Create WEA targets with `RAD_create_wea_from_weather_file` when required.
Keep user-requested worker counts and Radiance settings; `min_sensor_count` controls parallel batch size, not grid eligibility.

## Area-based EN 17037 example

Reuse the previously obtained `garden_root`, `model_target`, `floor_face_target`, and `weather_file_target`.

```python
grid = await call_tool("RAD_create_sensor_grid_from_object", {
    "garden_root": garden_root,
    "object_target": floor_face_target,
    "identifier": "room_workplane_mesh",
    "offset": 0.8,
    "flip_direction": True,
    "model_target": model_target,
    "attach_to_model": True,
    "return_object_dict": False
})
started = await call_tool("RAD_start_annual_daylight_en17037", {
    "garden_root": garden_root,
    "model_target": model_target,
    "weather_file_target": weather_file_target,
    "grid_filter": grid["target"]["identifier"],
    "workers": 2
})
run_target = started["run_target"]
run = started
while run.get("status") in {"queued", "running"}:
    run = await call_tool("RAD_poll_simulation", {
        "garden_root": garden_root,
        "run_target": run_target,
        "wait_seconds": 10,
        "poll_interval": 2
    })
if run.get("status") != "completed":
    return run
return await call_tool("RAD_read_daylight_compliance", {
    "garden_root": garden_root,
    "run_target": run_target
})
```

All five recipes use this poll/read sequence after their dedicated start call.
Read `compliance_summary`, paginated `space_summary`, and `output_paths`.
For area-weighted EN 17037, confirm `Total Floor Area` in the aggregate and grid summaries; sensor counts alone do not confirm area weighting.
WELL has no separate space-summary output; read L01, L06, and the WELL version in `compliance_summary`.
Pass `visualization_set_target` directly to `LB_set_to_html` or `LB_set_to_svg` for requested exports.
Use returned `run_folder` and output paths rather than constructing paths from `run_id`.
A completed run means the calculation finished; use the actual criteria results and preserve notes such as excessive sunlight instead of claiming automatic compliance.
