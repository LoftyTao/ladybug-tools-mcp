# Edit Honeybee Aperture Door And Shade

Use this when an existing Aperture, Door, or Shade must be edited without creating a replacement object.

## Preconditions

- Search the current model and pass `matches[i].target` as `target`.
- Keep large multi-object edits split unless the caller needs a single Code Mode chain.
- Use SDK-compatible geometry and property dictionaries.

## MCP Route

1. Search for the Shade, Aperture, or Door by `object_type` and identifier when known.
2. Call `honeybee_edit_shade`, `honeybee_edit_aperture`, or `honeybee_edit_door`.
3. Search the object again or validate the model.
4. For paired interior doors, edit one side and let the service update the paired side.

## Focused Code Mode Pattern

```python
windows = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "aperture",
    "identifier": "window_1"
})

edited = await call_tool("honeybee_edit_aperture", {
    "garden_root": garden_root,
    "target": windows["matches"][0]["target"],
    "is_operable": True,
    "display_name": "Edited Window",
    "vent_opening": {
        "type": "VentilationOpening",
        "fraction_area_operable": 0.4,
        "fraction_height_operable": 0.8,
        "discharge_coefficient": 0.5,
        "wind_cross_vent": True
    }
})
```

## Supported Edit Fields

- `honeybee_edit_shade`: `geometry`, `display_name`, `user_data`, `is_detached`, `construction`, `transmittance_schedule`, `pv_properties`, `modifier`, `modifier_blk`, `dynamic_group_identifier`, `states`.
- `honeybee_edit_aperture`: `geometry`, `display_name`, `user_data`, `is_operable`, `construction`, `vent_opening`, `modifier`, `modifier_blk`, `dynamic_group_identifier`, `states`.
- `honeybee_edit_door`: `geometry`, `display_name`, `user_data`, `is_glass`, `construction`, `vent_opening`, `modifier`, `modifier_blk`, `dynamic_group_identifier`, `states`.
- `states` supports `replace_all`, `add`, and `clear`; a list is interpreted as `replace_all`.

## Paired Interior Door Geometry

For an interior Surface door pair, search the Door, edit one side with new geometry, then validate. Do not remove and recreate the pair unless the model is already corrupted.

## Success Criteria

- The edit result includes `summary_view.updated_fields`.
- The object remains under the same parent path.
- Edited display name, geometry, energy properties, and Radiance properties are visible after persistence.
- Paired interior door edits preserve a valid model.

## Stop Conditions

- Do not retry an edit with `{}` or missing `target`; re-search and rebuild arguments.
- Surface-adjacent Apertures do not support single-side geometry or operability edits.
- Surface-adjacent Doors do not support single-side `is_glass` edits.
- A hosted Shade cannot be made detached through an in-place edit; that is a re-hosting or recreate operation.
