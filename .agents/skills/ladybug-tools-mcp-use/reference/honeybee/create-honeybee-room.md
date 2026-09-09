# Create Honeybee Room

Use this when the user wants to add a Room to the current Honeybee Model in a Garden.

## Preconditions

- A Garden exists and has a base Honeybee Model.
- Use one room creation shape per call: either `room_geometry` or `faces`, not both.
- Prefer SDK-backed room geometry inputs. Do not fabricate Honeybee room state from strings.

## MCP Route

1. Search for `HB_create_room`.
2. For a box, call `HB_create_room` once with `garden_root`, `identifier`, `x_dim`, `y_dim`, `height`, and optional `origin` / `orientation_angle`.
3. The tool writes to the Garden base model automatically.
4. Confirm with `HB_search_model_objects(object_type="room")`.
5. For orientation verification, search the Floor with `object_type="face"`, `room_identifier`, and `face_type="Floor"`.

For box orientation, `orientation_angle` is the clockwise angle from world `+X` to the width edge (`x_dim`).
The width direction for `0`, `90`, `180`, and `270` degrees is `+X`, `-Y`, `-X`, and `+Y`; a width direction 30 degrees counterclockwise from `+X` uses `330`.
Identify the Floor width edge by its measured length equal to `x_dim` before checking its direction in `matches[].geometry.boundary` or `vertices`.
Do not add 90 degrees from North/East/Front wording, infer width from the first vertex edge, or create then rotate/save.

## Code Mode Pattern

```python
room = await call_tool("HB_create_room", {
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

rooms = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "open_office"
})
```

For an oriented box, keep the dimensions, origin, and angle in the same write call:

```python
room = await call_tool("HB_create_room", {
    "garden_root": garden_root,
    "identifier": "room6x8",
    "x_dim": 6,
    "y_dim": 8,
    "height": 3.2,
    "origin": [0, 0, 1],
    "orientation_angle": 330,
})
rooms = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "room6x8",
})
floor_faces = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "room_identifier": "room6x8",
    "face_type": "Floor",
})
return {"room": room["target"], "matches": rooms["matches"], "floor": floor_faces["matches"]}
```

## Deterministic Candidate: `faces`

`faces` accepts a list of full Honeybee `Face` dictionaries. It is not a list of typed targets and should not be used as the default natural-language route. Use it only when the caller already has valid Honeybee Face dictionaries.

## Success Criteria

- The result includes a Room typed target.
- The create result includes `target` / `room_target`, `model_target`, `persistence_receipt`, and `report`.
- The room is found by `HB_search_model_objects(object_type="room")`.
- Later face/subface tools can use `children_scope=<room target>`.

## Stop Conditions

- Do not pass `host_target`; rooms are top-level model objects.
- Do not call `HB_edit_model(add_objects)` with the returned room target. The room is already persisted.
- If the model has no base Honeybee Model, create and confirm it first.
