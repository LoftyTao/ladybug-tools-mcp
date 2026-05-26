# Edit Honeybee Model

Use this when the current Honeybee Model needs model-level metadata changes, full top-level object additions, or removal of objects directly owned by the model.

## Preconditions

- Get the base model target with `garden_get_base_honeybee_model`.
- Use `honeybee_edit_model` for model metadata and top-level object operations only.
- Use object-specific create/remove tools for hosted children.

## MCP Route

1. Call `garden_get_base_honeybee_model` for the model target.
2. Call `honeybee_edit_model` with metadata fields, `add_objects`, or `remove_targets`.
3. Validate the model.
4. Search specific objects when the user needs confirmation.

## Add Object Pattern

```python
base = await call_tool("garden_get_base_honeybee_model", {"garden_root": garden_root})

edited = await call_tool("honeybee_edit_model", {
    "garden_root": garden_root,
    "target": base["target"],
    "display_name": "Edited Model",
    "user_data": {"agent": "ok"},
    "units": "Feet",
    "tolerance": 0.02,
    "angle_tolerance": 2.0,
    "add_objects": [full_honeybee_face_dict]
})
```

## Remove Top-Level Object Pattern

```python
objects = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "identifier": "seed_face"
})

base = await call_tool("garden_get_base_honeybee_model", {"garden_root": garden_root})

edited = await call_tool("honeybee_edit_model", {
    "garden_root": garden_root,
    "target": base["target"],
    "remove_targets": [objects["matches"][0]["target"]]
})
```

## Success Criteria

- `summary_view.updated_fields` lists the metadata, `add_objects`, or `remove_objects` operation.
- Add operations return added counts and object types.
- Remove operations return removed counts and object types.
- `persistence_receipt.persisted_path` remains the registered model path.
- `honeybee_validate_model.summary_view.is_valid == true`.

## Stop Conditions

- `add_objects` requires complete Honeybee object dictionaries, not typed targets or partial geometry snippets.
- Do not use this tool to add a room already created by `honeybee_create_room`.
- `remove_targets` is for model-owned Rooms and orphaned Face/Aperture/Door/Shade objects. Use object-specific remove tools for hosted children.
- Do not describe replace behavior as stable unless it has fresh Agent evidence.
