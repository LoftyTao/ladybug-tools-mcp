# Create Honeybee Apertures By Parameters

Use this when the user asks to create windows or apertures on an existing Honeybee Face by ratio or standard width/height rules.

## Preconditions

- The host must be a Face typed target from `honeybee_search_model_objects`.
- The host should usually be `face_type="Wall"` and `boundary_condition="Outdoors"` unless the user asks for interior glazing.
- Check existing child apertures when duplicate windows would be harmful.

## MCP Route

1. Search rooms or faces to locate the host wall.
2. Pass `matches[i].target` as `host_target`.
3. Call `honeybee_create_apertures_by_parameters`.
4. Confirm with a narrow `children_scope` search on the host face.

## Ratio Pattern

```python
faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_target,
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})

apertures = await call_tool("honeybee_create_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": faces["matches"][0]["target"],
    "generation_mode": "by_ratio",
    "ratio": 0.35,
    "identifier_prefix": "office_window"
})
```

## Width/Height Candidate

`generation_mode="by_width_height"` is deterministic-pass. Use it when the user gives explicit dimensions:

```json
{
  "generation_mode": "by_width_height",
  "aperture_width": 1.8,
  "aperture_height": 1.2,
  "sill_height": 0.9
}
```

## Success Criteria

- The result includes `target` or `targets` for created Apertures.
- The host face child count or a `children_scope` aperture search confirms the windows exist.
- `honeybee_validate_model` remains valid after staged room/window/shade workflows.

## Stop Conditions

- Do not pass room targets, identifier-only dictionaries, `face_name`, or `host_face_target`.
- Do not create a second aperture if a retry can first find the existing one.
- Use `honeybee_create_aperture` only when the user provides explicit non-rectangular `Face3D` geometry.
