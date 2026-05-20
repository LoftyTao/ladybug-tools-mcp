# Create Radiance Dynamic States

Agent-verified Code Mode path for creating Honeybee Radiance dynamic state objects and applying them to Shade, Aperture, or Door targets in a Garden model.

Use this path when the user needs switchable Radiance states, seasonal shades, dynamic glazing-related states, or a shared `dynamic_group_identifier` across multiple visible objects.

## Tool Choice

- Dynamic state geometry: `create_radiance_state_geometry`
  - SDK object: `StateGeometry`
- Shade state: `create_radiance_shade_state`
  - SDK object: `RadianceShadeState`
  - Use for Honeybee Shade targets.
- Aperture/Door state: `create_radiance_subface_state`
  - SDK object: `RadianceSubFaceState`
  - Use for Honeybee Aperture or Door targets.
- Apply model-side group: `setup_radiance_dynamic_group`
  - Sets `dynamic_group_identifier` and updates `states` on the selected model objects.

## Main Path

In Code Mode, keep the dependent objects inside one `execute` call. The state
object is not a persisted Garden target; `setup_radiance_dynamic_group` needs
the `object_dict` / `state_dict` returned by the state creation tool.

1. Create or search the target Shade / Aperture / Door objects.
2. Create or search a Radiance modifier.
3. Create `StateGeometry` if the state needs extra shade geometry.
4. Create the matching state object.
5. Call `setup_radiance_dynamic_group`.
6. Validate or search the updated model object before reporting success.

Use Garden Properties Library modifier targets directly when possible:

```python
modifier = await call_tool("create_radiance_opaque_modifier", {
    "garden_root": garden_root,
    "identifier": "winter_screen_modifier",
    "rgb_reflectance": 0.32,
    "return_object_dict": False,
})
state_geo = await call_tool("create_radiance_state_geometry", {
    "garden_root": garden_root,
    "identifier": "winter_screen_geo",
    "geometry": {
        "type": "Face3D",
        "boundary": [[0, 0, 2.1], [1, 0, 2.1], [1, 1, 2.1], [0, 1, 2.1]],
    },
    "modifier": modifier["target"],
})
state = await call_tool("create_radiance_shade_state", {
    "garden_root": garden_root,
    "modifier": modifier["target"],
    "shades": [state_geo["object_dict"]],
})
setup = await call_tool("setup_radiance_dynamic_group", {
    "garden_root": garden_root,
    "targets": [shade_target],
    "dynamic_group_identifier": "seasonal_shades",
    "states": [state["object_dict"]],
})
```

## Boundaries

- Do not create or persist a separate `DynamicShadeGroup` / `DynamicSubFaceGroup` object. In the Honeybee model, grouping is expressed through each object's Radiance properties.
- Use `create_radiance_shade_state` for Shade targets.
- Use `create_radiance_subface_state` for Aperture and Door targets.
- `create_radiance_state_geometry` requires exactly one of `geometry` or `vertices`.
- For `replace_all` / `add`, `setup_radiance_dynamic_group` requires at least one state. Do not pass `state_identifier`.
- `create_radiance_shade_state` accepts `shades` or `states` as the list of `StateGeometry` dictionaries. Use `state_geo["object_dict"]` or the full state-geometry result, not `state_geo["target"]`.
- For Garden checks, use `get_garden`, `get_base_honeybee_model`, or `search_honeybee_model_objects`. Do not call an inner `search` tool inside `execute`; Code Mode domain tools are reached only through `await call_tool(...)`.

## Success Criteria

- `setup_radiance_dynamic_group.summary_view.updated_count` matches the number of targets.
- Updated model objects have the requested `dynamic_group_identifier`.
- Updated model objects report the expected Radiance `state_count`.
- `validate_honeybee_model` returns no blocking issue for the final model.

## Evidence

- Agent integration smoke added 2026-04-29 verifies one Code Mode `execute` can create an opaque modifier, create `StateGeometry`, create a `RadianceShadeState`, apply it to a Shade target with `setup_radiance_dynamic_group`, validate the model, and confirm the persisted shade has `state_count=1`.
- Supervised external Matrix task 25 on 2026-04-30 verifies a natural MiniMax Agent can create two `StateGeometry` objects, create a `RadianceShadeState`, assign it to `dynamic_overhang_shade`, validate, and report `state_count=2`. The first attempt exposed a false-positive path where only `dynamic_group_identifier` was set; the MCP surface now rejects non-`clear` setup without real states, and the matrix checks persisted HBJSON state evidence.
