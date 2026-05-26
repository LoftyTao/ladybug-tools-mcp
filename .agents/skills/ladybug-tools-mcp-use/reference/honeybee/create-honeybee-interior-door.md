# Create Honeybee Interior Door

Use this when the user wants a door between adjacent Honeybee Rooms.

## Preconditions

- Rooms already exist in the same Honeybee Model.
- The target host face must be a `Wall` with `boundary_condition="Surface"`.
- If rooms are adjacent but not related, run `honeybee_relate_model` before creating the interior door.

## MCP Route

1. Search for the involved Room targets.
2. Search faces under the chosen Room with `children_scope=<room target>`, `face_type="Wall"`, and `boundary_condition="Surface"`.
3. Pass one Surface wall target to `honeybee_create_door`.
4. Let the service create or update the paired Door on the adjacent face.
5. Validate the model.

## Code Mode Pattern

```python
faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_target,
    "face_type": "Wall",
    "boundary_condition": "Surface"
})

door = await call_tool("honeybee_create_door", {
    "garden_root": garden_root,
    "host_target": faces["matches"][0]["target"],
    "identifier": "office_corridor_door",
    "door_width": 0.9,
    "door_height": 2.1,
    "sill_height": 0.05
})

validation = await call_tool("honeybee_validate_model", {"garden_root": garden_root})
```

## Exterior Door Shortcut

For an ordinary exterior door, search an `Outdoors` wall face and call `honeybee_create_door` with width/height/sill values. The paired-door rule only applies to `Surface` walls.

## Success Criteria

- `summary_view.is_interior_pair == true` for an interior door.
- `targets` includes both sides of the pair.
- The host face remains `boundary_condition.name == "Surface"`.
- `honeybee_validate_model.summary_view.is_valid == true`.

## Stop Conditions

- Do not manually clear adjacency to add a door.
- Do not create a second door on the adjacent face; call the tool once on one Surface host.
- Avoid geometry exactly on the parent face boundary. Use a small positive sill if needed.
