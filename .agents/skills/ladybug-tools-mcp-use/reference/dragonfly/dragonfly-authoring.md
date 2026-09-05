# Dragonfly Authoring

Use this when the user explicitly asks for Dragonfly, district/building massing, Room2D/Story/Building authoring, Dragonfly validation, Dragonfly Display, UWG, or Dragonfly-to-Honeybee conversion.

## Preconditions

- Use Dragonfly tools and Dragonfly typed targets. Do not route through Honeybee unless the user requests conversion.
- Keep base slots separate: `base_dragonfly_model` and `base_honeybee_model` are different Garden fields.
- Use Code Mode for dependent chains because Room2D, Story, Building, visualization, and conversion targets are passed step by step.

## Core Authoring Route

1. `GD_create` if the Garden does not exist.
2. `DF_model`.
3. `DF_room2d` with `vertices`, `floor_height`, and `floor_to_ceiling_height`.
4. `DF_story` with `room2d_targets: [room["room2d_target"]]`.
5. `DF_building` with `story_targets: [story["story_target"]]`.
6. Optional context: `DF_context_shade` with `geometry`, `vertices`, or parametric `x_dim` / `y_dim` / `height` / `origin`.
7. `DF_validate_model`.
8. Optional preview: `DF_model_to_visualization_set` then `LB_set_to_vtkjs`.
9. Optional handoff: `DF_model_to_honeybee` with `set_base=true`.
10. Confirm base slots with `GD_get_base_dragonfly_model` and, after conversion, `GD_get_base_honeybee_model`.

## Code Mode Pattern

```python
garden = await call_tool("GD_create", {"name": "Dragonfly Garden", "root_dir": garden_root})
model = await call_tool("DF_model", {"garden_root": garden_root, "identifier": "DF_model"})
room = await call_tool("DF_room2d", {
    "garden_root": garden_root,
    "identifier": "room_a",
    "vertices": [[0, 0], [6, 0], [6, 4], [0, 4]],
    "floor_height": 0,
    "floor_to_ceiling_height": 3
})
story = await call_tool("DF_story", {
    "garden_root": garden_root,
    "identifier": "story_1",
    "room2d_targets": [room["room2d_target"]]
})
building = await call_tool("DF_building", {
    "garden_root": garden_root,
    "identifier": "building_1",
    "story_targets": [story["story_target"]]
})
validation = await call_tool("DF_validate_model", {"garden_root": garden_root})
```

## Editing And Properties

- Search with `DF_search_objects`; use `object_type` values `building`, `story`, `room2d`, `context_shade`, or `all`. Use `children_scope` to inspect a Building or Story, and request `include_counts`, `include_properties`, `include_geometry`, or `limit` only when needed.
- For `DF_context_shade`, use `geometry`, `vertices`, or parametric `x_dim` / `y_dim` / `height` / `origin`; do not pass `faces`.
- When the Room2D attribute name is uncertain, call `DF_room2d_attributes` with `garden_root`; then call `DF_room2ds_by_attribute` to get `values`, `groups`, flat `matches`, and a `dragonfly_selection` handoff. Use `operator` with `equals`, `contains`, `gt`, `lt`, `gte`, or `lte`; do not use symbols such as `>` or `<` in Code Mode calls.
- Do not pass `include_geometry` to `DF_room2ds_by_attribute`. If geometry is needed for review or visualization context, call `DF_search_objects` with `include_geometry=true` and use by-attribute only for screening, grouping, and selection handoff.
- Prefer `DF_search_objects`, `DF_room2d_attributes`, and `DF_room2ds_by_attribute` for routine list/search/filter inspection. Do not request full DFJSON bodies for routine inspection.
- Edit metadata with `DF_edit_model`, `DF_edit_story`, `DF_edit_building`, or `DF_edit_room2d`.
- Add/remove Stories with `DF_add_stories_to_building` and `DF_remove_stories_from_building`.
- Remove Room2Ds, Buildings, or ContextShades with `DF_remove_room2ds`, `DF_remove_buildings`, or `DF_remove_context_shades`. Prefer object targets from `DF_search_objects` or `DF_room2ds_by_attribute` over raw identifiers when available. Check `summary_view.removed_counts` and `summary_view.relationship_cleanup` before claiming the model was cleaned.
- Solve or reset Story adjacency with `DF_solve_story_adjacency` and `DF_reset_story_adjacency`.
- Clean Room2D boundaries with `DF_clean_room2d_geometry`.
- Apply Dragonfly-native window and shading parameters with `DF_create_window_parameter`, `DF_apply_window_parameter`, `DF_create_shading_parameter`, and `DF_apply_shading_parameter`.
- Apply Energy properties with `DF_apply_energy_properties` using library identifiers for Room2D, Story, or Building targets. HVAC, SHW, schedules, and arbitrary property dict bridges are not stable in this path.
- Apply Ironbug-backed DetailedHVAC to Dragonfly Room2D, Story, or Building hosts with `DF_detailed_hvac`. Pass `ironbug_model_target` from the DetailedHVAC/Ironbug route and a Dragonfly `host_target`; do not pass plain strings or Honeybee-only DetailedHVAC bodies. This only writes Dragonfly Energy HVAC properties and does not run EnergyPlus. If `conditioned_only=true` reports no conditioned Room2Ds and the user wants all child Room2Ds served, retry with `conditioned_only=false`; otherwise stop and ask for conditioning/program setup.
- Apply Radiance properties with `DF_apply_radiance_properties`. Story grid parameters are intentionally rejected.

## Room2D Batch Geometry Cleanup

Use this when a Garden already contains Dragonfly Room2Ds and the user asks to align, intersect, or merge small rooms.

### Preconditions And Route

- Use the existing `garden_root` containing `garden.json`; omit `model_target` to use the Garden base Dragonfly Model, or pass the latest returned `model_target`.
- For Story or Building scope, set `host_type` to `story` or `building` and pass its typed `host_target`; model scope omits both.
- Treat `DF_align_room2ds`, `DF_intersect_room2ds`, and `DF_join_small_room2ds` as independent on-demand operations; call only the requested operation(s), pass each returned `model_target` forward when chaining, and validate after edits.
- Save only when the model changes, at most once per batch operation.
- `DF_align_room2ds` requires `lines` shaped as `[[[x1, y1], [x2, y2]], ...]`; `distance` and positive `tolerance` are optional.
- `DF_intersect_room2ds` uses the selected host scope and optional positive `tolerance`.
- `DF_join_small_room2ds` requires positive `area_threshold`; optionally set `join_into_large` and positive `tolerance`.

```python
garden_root = r"<existing Garden root>"

aligned = await call_tool("DF_align_room2ds", {
    "garden_root": garden_root,
    "lines": [[[0, 0], [6, 0]], [[0, 4], [6, 4]]],
    "distance": 0.5,
    "tolerance": 0.01,
})
validation = await call_tool("DF_validate_model", {
    "garden_root": garden_root,
    "model_target": aligned["model_target"],
})
return {
    "is_valid": validation["is_valid"],
    "issues": validation["issues"],
    "affected_counts": aligned["summary_view"]["affected_counts"],
}
```

Each write returns `target`, `host_target`, `model_target`, `summary_view`, `persistence_receipt`, and `report`; inspect `operation_result` for runtime status, readiness, revisions, affected targets, receipt, and report. `DF_validate_model` returns top-level `is_valid`, `valid`, `issues`, `summary_view`, and `report`.

`DF_intersect_room2ds` subdivides wall segments and clears original boundary conditions, window/glazing parameters, and shading parameters; run it before assigning those properties because it does not restore or preserve them automatically.

Stop on `operation_result.runtime_status` `failed` or `recovery_blocked`; on `conflict` with `readiness_status="reload_required"`, reread and resume only the intended step with the latest revision. Do not replay earlier writes wholesale, and stop if final validation is not `is_valid=true` with `issues=[]`.

## Visualization And Handoff

- Use `DF_model_to_visualization_set` for a model VisualizationSet.
- Use `DF_building_to_visualization_set`, `DF_story_to_visualization_set`, `DF_room2d_to_visualization_set`, or `DF_context_shade_to_visualization_set` for object previews.
- Use `DF_selection_to_visualization_set` after `DF_search_objects`, and `DF_room2d_attribute_to_visualization_set` after `DF_room2ds_by_attribute`.
- Set `return_visualization_set=false` when the next step is `LB_set_to_vtkjs`, `LB_set_to_svg`, or Web View; pass the returned `visualization_set_target`.
- Use `DF_model_envelope_edges_to_visualization_set` for envelope-edge display; if it returns `report.status="degraded"`, use the returned wireframe target instead of retrying edge options.
- Use `DF_models_to_comparison_visualization_set` for comparison display.
- Use `LB_set_to_vtkjs` when the user explicitly requests a reusable Web 3D artifact; use `LB_set_to_html` only for a standalone HTML artifact.
- Use `DF_model_to_honeybee` before Honeybee-only workflows.

## UWG Alternative Weather Route

Use this only when the user asks for Urban Weather Generator, urban microclimate weather morphing, rural/airport EPW to urban EPW, or Dragonfly UWG properties.

1. Read properties with `DF_uwg_get_dragonfly_properties_summary`.
2. Apply properties with `DF_uwg_apply_dragonfly_properties` on Model, Building, or ContextShade targets.
3. Create parameters with `DF_uwg_create_simulation_parameter` when custom run settings are needed.
4. Start with `DF_uwg_start_simulation` and poll with `DF_uwg_poll_simulation`.
5. If `summary_view.status` or `report.status` is `failed`, preserve the run ledger and stop before Energy handoff.
6. Use `summary_view.run.outputs.weather_target` for downstream Energy only after completion.

```python
props = await call_tool("DF_uwg_apply_dragonfly_properties", {
    "garden_root": garden_root,
    "host_target": building_target,
    "program": "MediumOffice",
    "vintage": "New",
    "roof_albedo": 0.65,
    "roof_veg_fraction": 0.3
})
started = await call_tool("DF_uwg_start_simulation", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "run_id": "summer_urban_weather"
})
poll = await call_tool("DF_uwg_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"]
})
```

## Success Criteria

- Dragonfly hierarchy exists as Room2D -> Story -> Building.
- `DF_validate_model` reports valid when the workflow claims a usable model.
- Visualization calls return `visualization_set_target` and exporter artifacts when requested.
- Removal calls return a persisted `model_target`, `persistence_receipt`, and compact cleanup summary.
- Conversion returns Honeybee model targets and updates `base_honeybee_model` only when requested.
- UWG completion returns a morphed weather target before Energy handoff.

## Stop Conditions

- Do not use `room2ds` or `room_2ds`; `DF_story` takes `room2d_targets`.
- Do not use removal tools for list/search workflows; search with `DF_search_objects` or `DF_room2ds_by_attribute` first, then remove only explicit targets.
- Do not call or invent `run_urbanopt`.
- Do not pass `terrain` as a label such as `Suburban`; omit it unless a real Terrain dictionary is available.
- Use UWG program identifiers such as `MediumOffice`, `LargeOffice`, `SmallOffice`, or `MidriseApartment`; do not pass broad labels like `Office`.
- Use UWG vintage values `New`, `1980_Present`, or `Pre1980`; do not pass ASHRAE labels.
