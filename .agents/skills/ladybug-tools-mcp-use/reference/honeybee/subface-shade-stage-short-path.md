# Subface And Shade Stage Short Path

Use this for staged Honeybee workflows where the user wants windows, subfaces, louvers, extruded borders, or explicit shade geometry added to existing Rooms.

## Preconditions

- A Garden exists with a base Honeybee Model and target Rooms.
- Keep the dependent room -> face -> aperture -> shade chain in one Code Mode `execute` block when possible.
- Treat this as a compact candidate route for staged workflows; store run evidence and metrics in LLM-Wiki.

## MCP Route

1. Search Room targets once.
2. For each selected Room, search exterior Wall faces with `children_scope`.
3. Pick the host face by `local_identifier`, `normal_vector`, or the user's side description.
4. Create Apertures with `honeybee_create_apertures_by_parameters`.
5. Pass the returned Aperture `target` or `targets[0]` directly into `honeybee_create_shades_by_parameters`.
6. Verify once with narrow child searches or child counts.
7. Stop after successful writes; write tools already persist the Garden.

## Code Mode Pattern

```python
garden_root = r"<exact garden root>"

rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})
room_targets = {m["identifier"]: m["target"] for m in rooms["matches"]}

faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["open_office"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
host = next(m["target"] for m in faces["matches"] if m.get("local_identifier") == "Front")

window = await call_tool("honeybee_create_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": host,
    "generation_mode": "by_ratio",
    "ratio": 0.38,
    "identifier_prefix": "open_office_window"
})

shades = await call_tool("honeybee_create_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": window["target"],
    "generation_mode": "louver_by_count",
    "parameters": {
        "depth": 0.45,
        "louver_count": 3,
        "offset": 0.15,
        "base_name": "open_office_louver"
    }
})

return {"window": window["target"], "shades": shades["targets"]}
```

## Recovery After Partial Writes

- Re-declare `garden_root` in each new `execute` block.
- Search the Room or Face with `children_scope`.
- Reuse existing Aperture targets when child counts or narrow searches show the windows already exist.
- Create only missing objects.

## Success Criteria

- For a two-room stage, keep `honeybee_search_model_objects` calls narrow and minimal.
- No inner `get_schema` calls inside `execute`.
- No duplicate apertures or shades.
- Final response includes `garden_root`, created/reused aperture targets, created/reused shade targets, and small counts.

## Stop Conditions

- Do not search for `save_garden`, `garden_save_base_honeybee_model`, `search_garden_assets`, or generic asset tools after successful writes.
- Do not relist the whole model after each write.
- Do not handwrite Aperture targets when create results already returned them.
