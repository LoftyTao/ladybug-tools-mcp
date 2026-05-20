# Dragonfly Authoring Path


Use this when the user explicitly wants Dragonfly, district/building massing, Room2D/Story/Building authoring, Dragonfly validation, Dragonfly Display, or Dragonfly-to-Honeybee conversion.

Core sequence inside one Code Mode `execute` block:

1. `create_garden` with `root_dir` if the Garden does not exist.
2. `create_dragonfly_model` with `garden_root` and `identifier`.
3. `create_dragonfly_room2d` with `vertices`, `floor_height`, and `floor_to_ceiling_height`.
4. `create_dragonfly_story` with `room2d_targets: [room["room2d_target"]]`.
5. `create_dragonfly_building` with `story_targets: [story["story_target"]]`.
6. Optionally create surrounding urban context or tree canopy with `create_dragonfly_context_shade` using 3D face geometry.
7. `validate_dragonfly_model` with `garden_root`.
8. `dragonfly_model_to_visualization_set` with `return_visualization_set=false` when a compact target is enough.
9. `visualization_set_to_vtkjs` with the returned `visualization_set_target` when vtk.js is needed.
10. `dragonfly_model_to_honeybee` with `set_base=true` when downstream Honeybee tools are needed.
11. Confirm split base slots with `get_base_dragonfly_model` and `get_base_honeybee_model`.

Do not call generic model-slot tools for Dragonfly. The Garden manifest writes `base_dragonfly_model` and `base_honeybee_model` separately.

Expanded SDK-backed operations:

- Search Dragonfly objects with `search_dragonfly_model_objects` before editing existing content. Use `object_type` values `building`, `story`, `room2d`, `context_shade`, or `all`; pass returned `matches[i].target` into downstream tools.
- Read compact model counts and metadata with `get_dragonfly_model_summary`; this does not return full DFJSON bodies.
- Create detached surrounding context, adjacent buildings, or tree canopy with `create_dragonfly_context_shade`. Pass `geometry` as one or more 3D face boundaries `[[[x, y, z], ...], ...]`; the tool uses Dragonfly SDK `ContextShade` and `Model.add_context_shade`, persists the DFJSON, and returns `context_shade_target` for search and UWG vegetation properties.
- Edit Dragonfly Model metadata with `edit_dragonfly_model`. Supported fields are `display_name`, `units`, `tolerance`, and `angle_tolerance`; do not use it as a generic DFJSON patch tool.
- Edit embedded Story metadata with `edit_dragonfly_story`. Supported fields are `display_name`, `floor_height`, `floor_to_floor_height`, and `multiplier`; pass `story_target` when available.
- Edit embedded Building metadata with `edit_dragonfly_building`. Supported operations are `display_name` and `sort_stories`; story add/remove still use the dedicated add/remove tools below.
- Edit a Room2D with `edit_dragonfly_room2d`. The parameter is `room2d_target`, not `identifier`; use a returned `room["room2d_target"]` or an equivalent Dragonfly Room2D typed target.
- Add Story objects to an existing Building with `add_dragonfly_stories_to_building`. The existing Building is selected by `building_identifier`; pass draft Story targets in `story_targets`.
- Remove Story objects with `remove_dragonfly_stories_from_building`. This uses Dragonfly SDK `Building.remove_stories_by_identifier`. Do not invent Building or Room2D deletion tools; those are not exposed as stable public SDK methods.
- Deterministic-pass: Building-level create/add/remove operations call Dragonfly SDK `Building.separate_top_bottom_floors()` before saving. A repeated Story multiplier is split into explicit ground / typical / top Stories where needed; the ground Story's Room2Ds are saved with `is_ground_contact=true`, and the top Story's Room2Ds are saved with `is_top_exposed=true`. Agents do not need to add an extra Room2D edit step for normal roof/ground assignment after creating or changing a Building.
- Agent-observed parameter trap: `create_dragonfly_story` takes `room2d_targets`, exactly, with `room["room2d_target"]` values. Do not use `room2ds` and do not use `room_2ds`.
- Solve/reset Room2D adjacency on an embedded Story with `solve_dragonfly_story_adjacency` and `reset_dragonfly_story_adjacency`.
- Clean Room2D boundaries with `clean_dragonfly_room2d_geometry`, which calls SDK cleanup methods and does not handwrite geometry algorithms.
- Create and apply Dragonfly-native window parameters with `create_dragonfly_window_parameter` and `apply_dragonfly_window_parameter`. Supported types are `simple_window_ratio` and `repeating_window_ratio`.
- Create and apply Dragonfly-native shading parameters with `create_dragonfly_shading_parameter` and `apply_dragonfly_shading_parameter`. Supported types are `overhang` and `extruded_border`.
- Read Dragonfly Energy/Radiance extension properties with `get_dragonfly_properties_summary`.
- Apply Dragonfly Energy ProgramType and ConstructionSet library identifiers with `apply_dragonfly_energy_properties`. Supported hosts are Room2D, Story, and Building targets. This is a narrow SDK-backed identifier path, not a generic `apply_properties_from_dict` bridge; HVAC, SHW, schedules, and arbitrary property dictionaries remain omitted.
- Apply Dragonfly Radiance ModifierSet identifiers and grid parameters with `apply_dragonfly_radiance_properties`. Supported hosts for `modifier_set_identifier` are Room2D, Story, and Building targets. Supported hosts for `grid_parameter_type` are Room2D and Building targets; Story grid parameters are intentionally rejected. Supported grid parameter types are `room_grid`, `room_radial_grid`, `exterior_face_grid`, and `exterior_aperture_grid`. This uses `dragonfly_radiance.gridpar` and Honeybee Radiance ModifierSet library identifiers, not a Radiance simulation setup or a generic property-dict bridge.
- Create envelope-edge display with `dragonfly_model_envelope_edges_to_visualization_set`. If Dragonfly Display cannot create the strict envelope-edge view for the current model, the tool returns `report.status="degraded"` and a wireframe model `visualization_set_target`; use that target for `visualization_set_to_vtkjs` rather than retrying edge parameters.
- Create model comparison display with `dragonfly_models_to_comparison_visualization_set`.
- Convert Honeybee to Dragonfly with `honeybee_model_to_dragonfly`, then confirm `base_dragonfly_model` with `get_base_dragonfly_model`.
- Skylight parameter tools are intentionally not exposed in this path yet; this round did not find a stable public `set_*` application route equivalent to windows/shading.

## UWG Alternative Weather Candidate

Status: deterministic-pass with scaffolded Agent cross-suite. Use this only when the user explicitly asks for Urban Weather Generator, urban microclimate weather morphing, rural/airport EPW to urban EPW, or Dragonfly UWG properties. Do not present it as full URBANopt district simulation, and do not treat broad natural UWG discovery as fully verified yet.

Validated MCP surface:

- Read UWG properties with `get_dragonfly_uwg_properties_summary`.
- Edit UWG properties with `apply_dragonfly_uwg_properties`. Supported hosts are Dragonfly Model, Building, and ContextShade targets. Room2D and Story targets intentionally raise a clear unsupported-host error in this slice.
- Create saved simulation parameters with `create_uwg_simulation_parameter`; pass nested `run_period`, `vegetation_parameter`, `reference_epw_site`, and `boundary_layer_parameter` only when needed.
- Write UWG JSON artifacts with `dragonfly_model_to_uwg` when the user needs setup inspection without running UWG.
- Prefer `start_uwg_run` for Agents, then poll with `get_uwg_run`. Use `run_uwg` only when the user explicitly asks to wait for local completion.
- Inspect outputs with `list_uwg_runs` and `list_uwg_run_outputs`.
- When a UWG run completes, pass `summary_view.run.outputs.weather_target` into existing Energy tools such as `start_energy_run` only if downstream Energy simulation is requested.

Common UWG boundaries:

- Do not call or invent `run_urbanopt`; URBANopt Energy, Electric Grid, and District Thermal are separate backlog directions.
- Do not return full UWG JSON, full EPW text, or full DFJSON bodies by default.
- Treat water-body modeling, wind-speed expectation changes, and terrain/water limitations as UWG scope notes rather than silently creating fake parameters.
- If the EPW preflight fails, inspect the failed `uwg_run` ledger; do not proceed into Energy with the bad weather.
- Agent-observed parameter trap: `terrain` is a Dragonfly UWG Terrain dictionary, not a label like `Suburban`; omit it in simple Agent workflows unless a real Terrain object dictionary is already available.
- Agent-observed enum trap: use UWG program identifiers such as `MediumOffice`, `LargeOffice`, `SmallOffice`, or `MidriseApartment`; do not pass broad labels like `Office`.
- Agent-observed enum trap: UWG vintage values are `New`, `1980_Present`, and `Pre1980`; do not pass EnergyPlus or ASHRAE labels like `ASHRAE_2019`.
- For simple cool-roof / green-roof setup, edit model-level tree and grass cover on the Dragonfly Model target, then edit each Building target once with `program`, `vintage`, `roof_albedo`, and `roof_veg_fraction`. Read `get_dragonfly_uwg_properties_summary` once after the edits and avoid looping over the same Building unless the summary shows a real mismatch.

Minimal Code Mode sketch:

```python
model_props = await call_tool("apply_dragonfly_uwg_properties", {
    "garden_root": garden_root,
    "host_target": model_target,
    "tree_coverage_fraction": 0.18,
    "grass_coverage_fraction": 0.12
})
props = await call_tool("apply_dragonfly_uwg_properties", {
    "garden_root": garden_root,
    "host_target": building_target,
    "program": "MediumOffice",
    "vintage": "New",
    "roof_albedo": 0.65,
    "roof_veg_fraction": 0.3
})
summary = await call_tool("get_dragonfly_uwg_properties_summary", {
    "garden_root": garden_root
})
param = await call_tool("create_uwg_simulation_parameter", {
    "garden_root": garden_root,
    "identifier": "summer_uwg",
    "run_period": {"start_month": 6, "start_day": 1, "end_month": 8, "end_day": 31}
})
started = await call_tool("start_uwg_run", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "simulation_parameter_target": param["target"],
    "run_id": "summer_urban_weather"
})
poll = await call_tool("get_uwg_run", {
    "garden_root": garden_root,
    "run_target": started["target"]
})
return {
    "uwg_status": poll["summary_view"]["run"]["status"],
    "next_weather_target": poll["summary_view"]["run"]["outputs"].get("weather_target")
}
```

Common parameter pitfalls:

- `visualization_set_to_vtkjs` takes `visualization_set_target`, not `visualization_target`.
- For Web 3D, vtk.js, React viewer, Remotion, or reusable geometry asset requests, use `visualization_set_to_vtkjs`; use `visualization_set_to_html` only for a standalone HTML page artifact.
- `dragonfly_model_to_visualization_set` does not take `object_type`; pass `garden_root` and optionally `model_target`.
- Do not call nonexistent Dragonfly-specific exporters such as `export_dragonfly_visualization_to_vtkjs`; use `dragonfly_model_to_visualization_set` followed by `visualization_set_to_vtkjs`.

Minimal Code Mode sketch:

```python
garden = await call_tool("create_garden", {"name": "Dragonfly Garden", "root_dir": garden_root})
model = await call_tool("create_dragonfly_model", {"garden_root": garden_root, "identifier": "df_model"})
room = await call_tool("create_dragonfly_room2d", {
    "garden_root": garden_root,
    "identifier": "room_a",
    "vertices": [[0, 0], [6, 0], [6, 4], [0, 4]],
    "floor_height": 0,
    "floor_to_ceiling_height": 3
})
story = await call_tool("create_dragonfly_story", {
    "garden_root": garden_root,
    "identifier": "story_1",
    "room2d_targets": [room["room2d_target"]]
})
building = await call_tool("create_dragonfly_building", {
    "garden_root": garden_root,
    "identifier": "building_1",
    "story_targets": [story["story_target"]]
})
validation = await call_tool("validate_dragonfly_model", {"garden_root": garden_root})
vis = await call_tool("dragonfly_model_to_visualization_set", {
    "garden_root": garden_root,
    "return_visualization_set": False
})
vtkjs = await call_tool("visualization_set_to_vtkjs", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "df_model"
})
hb = await call_tool("dragonfly_model_to_honeybee", {"garden_root": garden_root, "set_base": True})
return {
    "dragonfly_valid": validation["valid"],
    "building_target": building["building_target"],
    "visualization_set_target": vis["visualization_set_target"],
    "vtkjs_exists": vtkjs["summary_view"]["exists"],
    "honeybee_model_targets": hb["honeybee_model_targets"]
}
```
