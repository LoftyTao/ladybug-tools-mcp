# Create Radiance Modifiers

Use this when the user needs a project-specific Honeybee Radiance modifier instead of a standards-library identifier.

## Preconditions

- Save reusable modifiers to Garden with `garden_root` and `return_object_dict=false`.
- Pass returned modifier targets directly to Honeybee edit tools.
- Use standards search when a generic library identifier is enough.

## Tool Choice

- `RAD_create_opaque_modifier`: `Plastic`.
- `RAD_create_mirror_modifier`: `Mirror`.
- `RAD_create_metal_modifier`: `Metal`.
- `RAD_create_trans_modifier`: `Trans`.
- `RAD_create_glass_modifier`: `Glass`.

## Code Mode Pattern

```python
opaque = await call_tool("RAD_create_opaque_modifier", {
    "garden_root": garden_root,
    "identifier": "warm_matte_wall",
    "rgb_reflectance": 0.52,
    "return_object_dict": False
})
glass = await call_tool("RAD_create_glass_modifier", {
    "garden_root": garden_root,
    "identifier": "clear_visible_glass",
    "rgb_transmittance": 0.64,
    "refraction_index": 1.52,
    "return_object_dict": False
})
```

## Input Rules

- For opaque, mirror, metal, and trans modifiers, use either `rgb_reflectance` or individual `r_reflectance`, `g_reflectance`, and `b_reflectance`.
- Do not mix `rgb_reflectance` with individual RGB reflectance fields.
- For glass, use transmittance or transmissivity fields, not reflectance.
- Do not describe glass inputs as reflectance in user-facing output.

## Success Criteria

- The create result returns a `garden_properties_library_object` target.
- `domain == "honeybee_radiance"` and `object_family == "modifier"`.
- The target can be passed to `HB_edit_face`, `HB_edit_aperture`, `HB_edit_door`, or `HB_edit_shade`.

## Stop Conditions

- Do not use filesystem probes or Python imports inside Code Mode to confirm Gardens.
- Do not copy full modifier dictionaries when a target exists.
