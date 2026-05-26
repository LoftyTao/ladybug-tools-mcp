# Edit Honeybee Face And Room

Use this when an existing Honeybee Face or Room must be edited in place through a typed target.

## Preconditions

- Locate the Face or Room with `honeybee_search_model_objects`.
- Pass the selected `matches[i].target` to the edit tool as `target`.
- Use Garden Properties Library targets or standards identifiers for energy properties when available.

## MCP Route

1. Search the object with the narrowest filters available.
2. Call `honeybee_edit_face` or `honeybee_edit_room`.
3. Search the same object again if field confirmation is needed.
4. Run `honeybee_validate_model` after edits that affect boundary conditions, constructions, adjacency, or energy properties.

## Face Edit Pattern

```python
faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "identifier": "Tiny_House_Office_Right"
})

edited = await call_tool("honeybee_edit_face", {
    "garden_root": garden_root,
    "target": faces["matches"][0]["target"],
    "boundary_condition": {"type": "Ground"},
    "construction": construction_target
})
```

## Room Edit Pattern

```python
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "room_1"
})

edited = await call_tool("honeybee_edit_room", {
    "garden_root": garden_root,
    "target": rooms["matches"][0]["target"],
    "program_type": "1980_2004::SmallOffice::OpenOffice",
    "construction_set": construction_set_target
})
```

## Supported Stable Uses

- `honeybee_edit_face`: update `display_name`, `user_data`, `modifier`, construction target, and non-Surface boundary-condition changes.
- `honeybee_edit_room`: update `story`, `zone`, `program_type`, `construction_set`, `setpoint`, Honeybee Energy HVAC-template target, and Radiance `modifier_set`.
- Low-context property handoff: create material target, create construction target from it, then pass the construction target to the face edit.

## Success Criteria

- The edit result lists the changed fields in `summary_view.updated_fields`.
- The persisted object still appears under the same parent path.
- Energy property edits can be found in the compact room search result.
- Validation passes when the edit should leave the model simulatable.

## Stop Conditions

- Do not pass `room_target`; the parameter name is `target`.
- Do not pass object identifiers, full search responses, or `matches[i]` as the edit target.
- Do not describe a Honeybee Room edit as Ironbug ThermalZone or DetailedHVAC equipment placement.
