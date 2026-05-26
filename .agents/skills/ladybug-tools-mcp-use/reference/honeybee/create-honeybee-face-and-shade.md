# Create Honeybee Face And Shade

Use this when the user needs an orphaned Honeybee Face, a detached Shade, or a hosted shade on an existing Face/Aperture/Door.

## Preconditions

- A Garden exists and has a base Honeybee Model.
- For hosted objects, first locate the host with `honeybee_search_model_objects` and pass only `matches[i].target`.
- For orphaned objects, provide complete SDK-compatible `Face3D` geometry.

## MCP Route

1. Create or confirm the base Honeybee Model.
2. For orphaned geometry, call `honeybee_create_face` or `honeybee_create_shade`.
3. For hosted shades, search the host face/aperture/door and pass its typed target to the shade tool.
4. Search the relevant object type to confirm persistence.
5. Run `honeybee_validate_model` after multi-object writes.

## Code Mode Pattern

```python
face = await call_tool("honeybee_create_face", {
    "garden_root": garden_root,
    "identifier": "south_wall",
    "geometry": {
        "type": "Face3D",
        "boundary": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]
    }
})

shade = await call_tool("honeybee_create_shade", {
    "garden_root": garden_root,
    "identifier": "south_overhang",
    "geometry": {
        "type": "Face3D",
        "boundary": [[0.2, -0.6, 3.1], [3.8, -0.6, 3.1], [3.8, 0, 3.1], [0.2, 0, 3.1]]
    }
})
```

## Success Criteria

- Created objects return typed targets.
- Search by `object_type="face"` or `object_type="shade"` finds the identifiers.
- Hosted shade targets retain the correct parent path.

## Stop Conditions

- Do not pass a full search response as `host_target`; use `matches[i].target`.
- `honeybee_create_face` does not accept `face_type` or `boundary_condition`; use room/model edit paths when semantic face properties must be assigned.
- Do not write duplicate identifiers. Search before retrying after an uncertain failure.
- Avoid parallel writes to the same model. Chain dependent create/search/validate calls in one Code Mode block.
