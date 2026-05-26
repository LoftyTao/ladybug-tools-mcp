# Create Honeybee Room

Use this when the user wants to add a Room to the current Honeybee Model in a Garden.

## Preconditions

- A Garden exists and has a base Honeybee Model.
- Use one room creation shape per call: either `room_geometry` or `faces`, not both.
- Prefer SDK-backed room geometry inputs. Do not fabricate Honeybee room state from strings.

## MCP Route

1. Search for `honeybee_create_room`.
2. Call `honeybee_create_room` with `garden_root`, `identifier`, and either box dimensions or `room_geometry`.
3. The tool writes to the Garden base model automatically.
4. Confirm with `honeybee_search_model_objects(object_type="room")`.

## Code Mode Pattern

```python
room = await call_tool("honeybee_create_room", {
    "garden_root": garden_root,
    "identifier": "open_office",
    "room_geometry": {
        "type": "Polyface3D",
        "vertices": [
            [0, 0, 0], [6, 0, 0], [6, 4, 0], [0, 4, 0],
            [0, 0, 3], [6, 0, 3], [6, 4, 3], [0, 4, 3]
        ],
        "face_indices": [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    }
})

rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "open_office"
})
```

## Deterministic Candidate: `faces`

`faces` accepts a list of full Honeybee `Face` dictionaries. It is not a list of typed targets and should not be used as the default natural-language route. Use it only when the caller already has valid Honeybee Face dictionaries.

## Success Criteria

- The result includes a Room typed target.
- The room is found by `honeybee_search_model_objects(object_type="room")`.
- Later face/subface tools can use `children_scope=<room target>`.

## Stop Conditions

- Do not pass `host_target`; rooms are top-level model objects.
- Do not call `honeybee_edit_model(add_objects)` with the returned room target. The room is already persisted.
- If the model has no base Honeybee Model, create and confirm it first.
