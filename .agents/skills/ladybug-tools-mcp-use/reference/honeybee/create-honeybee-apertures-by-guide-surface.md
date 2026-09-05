# Create Honeybee Apertures By Guide Surface

Use this when the user supplies one or more Ladybug Geometry `Face3D` guide surfaces to create apertures on an existing exterior Honeybee Face.

## Preconditions

- The Garden has a base Honeybee Model, or an explicit Honeybee `model_target` is available.
- Search for the host and pass only `matches[i]["target"]` as `host_target`; the host must be a `Face` with `boundary_condition="Outdoors"`.
- Pass each guide as an inline `Face3D` dictionary, such as `{"type": "Face3D", "boundary": [[x, y, z], ...]}`.

## MCP Route

1. Search the narrowest host Face query with `HB_search_model_objects`.
2. Call `HB_create_apertures_by_guide_surface` with `garden_root`, `host_target`, and non-empty `guide_surfaces`.
3. Use `targets`, `created_targets`, `reused_targets`, `summary_view`, and `persistence_receipt` from the result.
4. Confirm with an aperture search using `children_scope=host_target`; validate with `HB_validate_model` when the workflow needs model validity.

## Code Mode Pattern

```python
faces = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
host_target = faces["matches"][0]["target"]

# Replace these points with a Face3D coplanar with the selected host Face.
result = await call_tool("HB_create_apertures_by_guide_surface", {
    "garden_root": garden_root,
    "host_target": host_target,
    "guide_surfaces": [
        {"type": "Face3D", "boundary": [[0.5, 0, 1], [1.5, 0, 1], [1.5, 0, 2], [0.5, 0, 2]]}
    ],
    "tolerance": 0.01,
    "identifier_prefix": "front_window"
})

return {
    "targets": result["targets"],
    "created_count": result["summary_view"]["created_count"],
    "reused_count": result["summary_view"]["reused_count"],
    "skipped": result["skipped"],
    "persistence_receipt": result["persistence_receipt"]
}
```

`model_target` is optional and defaults to the Garden base Honeybee Model.
`tolerance` defaults to `0.01`; `identifier_prefix` is optional.

## Idempotency And Diagnostics

- Repeating the same host and guide surfaces reuses equivalent apertures: expect `created_count=0`, `reused_count>0`, and `persistence_receipt.status="no_change"`.
- Skipped guides are listed in top-level `skipped` and `summary_view.skipped`; each item includes `guide_surface_index`, `reason`, and `message`.
- For invalid placement, inspect `reason`: `non_coplanar` or `outside_tolerance` indicates a coplanarity/tolerance failure, and `outside_host_face` indicates the projected guide is outside the host boundary.
- Skipped guides are not written. If no guide is created, expect `runtime_status="no_change"`; correct the reported geometry before retrying rather than changing targets blindly.

## Stop Conditions

- Stop when the host match is ambiguous or is not an outdoor Face; narrow the search instead of guessing.
- Do not pass a Room target, the full search response, or a `Face3D` under `geometry`; the parameter is `guide_surfaces`.
- Do not create replacement apertures on replay or call an extra Garden save tool after a successful authoring response.
