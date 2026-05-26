# Create Radiance Dynamic States

Use this when the user needs switchable Radiance states, seasonal shades, dynamic glazing-related states, or shared `dynamic_group_identifier` values across visible Honeybee objects.

## Preconditions

- Search target Shade, Aperture, or Door objects first.
- Create or search Radiance modifiers before creating states.
- Keep state creation and group setup in one Code Mode block because state objects are passed as `object_dict` values, not persisted targets.

## Tool Choice

- `radiance_create_state_geometry`: creates `StateGeometry`.
- `radiance_create_shade_state`: use for Honeybee Shade targets.
- `radiance_create_subface_state`: use for Honeybee Aperture or Door targets.
- `radiance_setup_dynamic_group`: sets group identifier and states on selected model objects.

## Code Mode Pattern

```python
modifier = await call_tool("radiance_create_opaque_modifier", {
    "garden_root": garden_root,
    "identifier": "winter_screen_modifier",
    "rgb_reflectance": 0.32,
    "return_object_dict": False
})
state_geo = await call_tool("radiance_create_state_geometry", {
    "garden_root": garden_root,
    "identifier": "winter_screen_geo",
    "geometry": {"type": "Face3D", "boundary": [[0, 0, 2.1], [1, 0, 2.1], [1, 1, 2.1], [0, 1, 2.1]]},
    "modifier": modifier["target"]
})
state = await call_tool("radiance_create_shade_state", {
    "garden_root": garden_root,
    "modifier": modifier["target"],
    "shades": [state_geo["object_dict"]]
})
setup = await call_tool("radiance_setup_dynamic_group", {
    "garden_root": garden_root,
    "targets": [shade_target],
    "dynamic_group_identifier": "seasonal_shades",
    "states": [state["object_dict"]]
})
```

## Success Criteria

- `summary_view.updated_count` matches the number of targets.
- Updated objects have the requested `dynamic_group_identifier`.
- Updated objects report the expected Radiance `state_count`.
- Validation has no blocking issue for the final model.

## Stop Conditions

- Do not create a separate `DynamicShadeGroup` or `DynamicSubFaceGroup` object.
- `radiance_create_state_geometry` requires exactly one of `geometry` or `vertices`.
- For replace/add operations, do not pass an empty state list or `state_identifier`.
- Do not call inner `search` inside Code Mode `execute`; use outer search/get_schema first.
