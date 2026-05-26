# Dragonfly Authoring

Use this when the user explicitly asks for Dragonfly, district/building massing, Room2D/Story/Building authoring, Dragonfly validation, Dragonfly Display, UWG, or Dragonfly-to-Honeybee conversion.

## Preconditions

- Use Dragonfly tools and Dragonfly typed targets. Do not route through Honeybee unless the user requests conversion.
- Keep base slots separate: `base_dragonfly_model` and `base_honeybee_model` are different Garden fields.
- Use Code Mode for dependent chains because Room2D, Story, Building, visualization, and conversion targets are passed step by step.

## Core Authoring Route

1. `garden_create` if the Garden does not exist.
2. `dragonfly_create_model`.
3. `dragonfly_create_room2d` with `vertices`, `floor_height`, and `floor_to_ceiling_height`.
4. `dragonfly_create_story` with `room2d_targets: [room["room2d_target"]]`.
5. `dragonfly_create_building` with `story_targets: [story["story_target"]]`.
6. Optional context: `dragonfly_create_context_shade`.
7. `dragonfly_validate_model`.
8. Optional preview: `dragonfly_model_to_visualization_set` then `visualization_set_to_vtkjs`.
9. Optional handoff: `dragonfly_model_to_honeybee` with `set_base=true`.
10. Confirm base slots with `garden_get_base_dragonfly_model` and, after conversion, `garden_get_base_honeybee_model`.

## Code Mode Pattern

```python
garden = await call_tool("garden_create", {"name": "Dragonfly Garden", "root_dir": garden_root})
model = await call_tool("dragonfly_create_model", {"garden_root": garden_root, "identifier": "df_model"})
room = await call_tool("dragonfly_create_room2d", {
    "garden_root": garden_root,
    "identifier": "room_a",
    "vertices": [[0, 0], [6, 0], [6, 4], [0, 4]],
    "floor_height": 0,
    "floor_to_ceiling_height": 3
})
story = await call_tool("dragonfly_create_story", {
    "garden_root": garden_root,
    "identifier": "story_1",
    "room2d_targets": [room["room2d_target"]]
})
building = await call_tool("dragonfly_create_building", {
    "garden_root": garden_root,
    "identifier": "building_1",
    "story_targets": [story["story_target"]]
})
validation = await call_tool("dragonfly_validate_model", {"garden_root": garden_root})
```

## Editing And Properties

- Search with `dragonfly_search_model_objects`; use `object_type` values `building`, `story`, `room2d`, `context_shade`, or `all`.
- Summarize with `dragonfly_get_model_summary`; do not request full DFJSON bodies for routine inspection.
- Edit metadata with `dragonfly_edit_model`, `dragonfly_edit_story`, `dragonfly_edit_building`, or `dragonfly_edit_room2d`.
- Add/remove Stories with `dragonfly_add_stories_to_building` and `dragonfly_remove_stories_from_building`.
- Solve or reset Story adjacency with `dragonfly_solve_story_adjacency` and `dragonfly_reset_story_adjacency`.
- Clean Room2D boundaries with `dragonfly_clean_room2d_geometry`.
- Apply Dragonfly-native window and shading parameters with `dragonfly_create_window_parameter`, `dragonfly_apply_window_parameter`, `dragonfly_create_shading_parameter`, and `dragonfly_apply_shading_parameter`.
- Apply Energy properties with `dragonfly_apply_energy_properties` using library identifiers for Room2D, Story, or Building targets. HVAC, SHW, schedules, and arbitrary property dict bridges are not stable in this path.
- Apply Radiance properties with `dragonfly_apply_radiance_properties`. Story grid parameters are intentionally rejected.

## Visualization And Handoff

- Use `dragonfly_model_to_visualization_set` for a model VisualizationSet.
- Use `dragonfly_model_envelope_edges_to_visualization_set` for envelope-edge display; if it returns `report.status="degraded"`, use the returned wireframe target instead of retrying edge options.
- Use `dragonfly_models_to_comparison_visualization_set` for comparison display.
- Use `visualization_set_to_vtkjs` for Web 3D, React viewer, Remotion, or reusable geometry assets; use `visualization_set_to_html` only for a standalone HTML artifact.
- Use `dragonfly_model_to_honeybee` before Honeybee-only workflows.

## UWG Alternative Weather Route

Use this only when the user asks for Urban Weather Generator, urban microclimate weather morphing, rural/airport EPW to urban EPW, or Dragonfly UWG properties.

1. Read properties with `uwg_get_dragonfly_properties_summary`.
2. Apply properties with `uwg_apply_dragonfly_properties` on Model, Building, or ContextShade targets.
3. Create parameters with `uwg_create_simulation_parameter` when custom run settings are needed.
4. Start with `uwg_start_simulation` and poll with `uwg_poll_simulation`.
5. Use `summary_view.run.outputs.weather_target` for downstream Energy only after completion.

```python
props = await call_tool("uwg_apply_dragonfly_properties", {
    "garden_root": garden_root,
    "host_target": building_target,
    "program": "MediumOffice",
    "vintage": "New",
    "roof_albedo": 0.65,
    "roof_veg_fraction": 0.3
})
started = await call_tool("uwg_start_simulation", {
    "garden_root": garden_root,
    "weather_target": weather_target,
    "run_id": "summer_urban_weather"
})
poll = await call_tool("uwg_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["target"]
})
```

## Success Criteria

- Dragonfly hierarchy exists as Room2D -> Story -> Building.
- `dragonfly_validate_model` reports valid when the workflow claims a usable model.
- Visualization calls return `visualization_set_target` and exporter artifacts when requested.
- Conversion returns Honeybee model targets and updates `base_honeybee_model` only when requested.
- UWG completion returns a morphed weather target before Energy handoff.

## Stop Conditions

- Do not use `room2ds` or `room_2ds`; `dragonfly_create_story` takes `room2d_targets`.
- Do not invent Building or Room2D deletion tools.
- Do not call or invent `run_urbanopt`.
- Do not pass `terrain` as a label such as `Suburban`; omit it unless a real Terrain dictionary is available.
- Use UWG program identifiers such as `MediumOffice`, `LargeOffice`, `SmallOffice`, or `MidriseApartment`; do not pass broad labels like `Office`.
- Use UWG vintage values `New`, `1980_Present`, or `Pre1980`; do not pass ASHRAE labels.
