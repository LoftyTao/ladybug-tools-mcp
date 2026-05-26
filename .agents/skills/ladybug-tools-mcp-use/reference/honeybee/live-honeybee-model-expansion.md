# Expand A Live Honeybee Model

Use this when the user wants to continue modeling in an existing Garden or Grasshopper-followed Honeybee Model instead of rebuilding a seed model.

## Preconditions

- Use the user's existing `garden_root` exactly.
- Continue from current Garden state after failures. Do not recreate the whole model unless the user asks.
- Keep dependent writes in one Code Mode block when variables and targets are needed across steps.

## MCP Route

1. Create the new Room with `honeybee_create_room`.
2. Run `honeybee_relate_model`, usually `relation_mode="explicit_relate_full"` for complex live expansions.
3. Search Rooms and build an identifier-to-target map.
4. Search exterior Wall faces under the new Room using `children_scope`.
5. Select a host by `local_identifier` or `normal_vector`.
6. Create Apertures, Doors, and Shades with their typed host targets.
7. Validate once and return a compact summary.

## Code Mode Pattern

```python
garden_root = r"<existing garden root>"

room = await call_tool("honeybee_create_room", {
    "garden_root": garden_root,
    "identifier": "north_office",
    "x_dim": 6,
    "y_dim": 4,
    "height": 3,
    "origin": [0, 4, 0]
})

await call_tool("honeybee_relate_model", {
    "garden_root": garden_root,
    "relation_mode": "explicit_relate_full"
})

rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})
room_targets = {m["identifier"]: m["target"] for m in rooms["matches"]}

faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["north_office"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
host = next(m["target"] for m in faces["matches"] if m.get("normal_vector", [0, 0, 0])[1] > 0.8)

window = await call_tool("honeybee_create_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": host,
    "generation_mode": "by_width_height",
    "aperture_width": 1.8,
    "aperture_height": 1.2,
    "sill_height": 0.9,
    "aperture_identifier": "north_office_north_window"
})

validation = await call_tool("honeybee_validate_model", {"garden_root": garden_root})
return {"room": room["target"], "window": window["target"], "is_valid": validation["is_valid"]}
```

## Success Criteria

- New rooms appear in room search results.
- New windows, doors, or shades appear in child counts or narrow child searches.
- `honeybee_validate_model.is_valid == true`.
- No step depends on variables from a previous `execute` block.

## Stop Conditions

- Do not rebuild the user's live Garden to recover from a partial failure.
- Do not pass full search responses downstream.
- Record complex live-round evidence in LLM-Wiki, not in this Skill reference.
