# Create Radiance Luminaires

Use this when the user provides IES LM-63 content or a Garden-contained IES file path and wants a reusable Honeybee Radiance Luminaire. This is Radiance electric lighting, not Honeybee Energy `Lighting`.

## Preconditions

- Provide exactly one of `ies_content` or `ies_path`.
- Use `garden_root` and `return_object_dict=false` for reusable library handoff.
- Attach to a Honeybee Model only when a Radiance scene/run should include the fixtures.

## Create Pattern

```python
luminaire = await call_tool("radiance_create_luminaire", {
    "garden_root": garden_root,
    "ies_content": ies_text,
    "identifier": "sample_luminaire",
    "instances": [{"point": [0, 0, 3], "aiming_point": [0, 0, 0]}],
    "custom_lamp": {"mode": "color_temperature", "name": "warm_lamp", "color_temperature": 3000},
    "return_object_dict": False
})
found = await call_tool("library_search_garden_properties_objects", {
    "garden_root": garden_root,
    "query": "sample",
    "domain": "honeybee_radiance",
    "object_family": "luminaire"
})
```

## Attach Pattern

```python
attached = await call_tool("radiance_add_luminaire_to_model", {
    "garden_root": garden_root,
    "model_target": model_target,
    "luminaires": [luminaire["target"]]
})
```

Use `replace_existing=True` only when intentionally replacing a model luminaire with the same identifier.

## Input Rules

- Each `instances` item uses `point` and optional `spin`, `tilt`, `rotation`, or `aiming_point`.
- `custom_lamp` can be a full SDK dict or simple modes: `color_temperature`, `rgb`, or `xy`.

## Success Criteria

- The create result returns a `garden_properties_library_object` target with `domain="honeybee_radiance"` and `object_family="luminaire"`.
- Model attachment returns updated model persistence and `summary_view.luminaire_count`.

## Stop Conditions

- Do not confuse Radiance luminaires with Honeybee Energy lighting loads.
- Do not attach luminaires unless the downstream scene/run needs them.
- Keep IES evidence in LLM-Wiki.
