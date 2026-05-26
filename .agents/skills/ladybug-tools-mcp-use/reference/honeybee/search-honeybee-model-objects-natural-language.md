# Search Honeybee Model Objects From Natural Language

Use this when a user refers to a room, wall, window, door, shade, or model object in ordinary language and downstream tools need a typed target.

## Preconditions

- A Garden exists and has a base Honeybee Model unless `model_target` is explicitly supplied.
- The next operation must receive `matches[i].target`, not a guessed identifier.
- Use canonical field names such as `object_type`, `identifier`, `children_scope`, `face_type`, and `boundary_condition`.

## MCP Route

1. Call `honeybee_search_model_objects` with the narrowest known filters.
2. If there is one clear match, pass `matches[0].target` to the downstream tool.
3. If the match is ambiguous, narrow by room `children_scope`, face identifier, boundary condition, or object identifier.
4. Use `child_counts`, `parent`, and `normal_vector` from compact matches before making broad follow-up searches.

## Common Queries

```python
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "open_office"
})

faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": rooms["matches"][0]["target"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
```

## Target Handoff

- Use `matches[i].target` for `target` and `host_target` arguments.
- `children_scope` accepts a typed target for Room, Face, Aperture, or Door.
- `face_identifier` filters Apertures, Doors, and Shades by parent face; for faces it filters the face itself.
- `normal_vector` is a list. `normal` is a dict; do not index it like a list.

## Success Criteria

- `summary_view.count` matches the expected ambiguity level.
- The selected match has the expected `object_type`, identifier, and parent.
- The downstream create/edit/remove tool receives only the typed target, not the full search response.

## Stop Conditions

- Do not invent tools such as `search_honeybee_rooms`, `search_honeybee_apertures`, or `get_honeybee_room`.
- Do not stop after finding a Room when the user asked to open windows, remove doors, or shade apertures. Continue to the host Face or child object.
- Do not use a room identifier as a face identifier. Use `children_scope` to move from Room to Face.
