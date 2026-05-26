# Operate Honeybee Objects

Use this when the user wants to move, rotate, scale, or mirror an existing Honeybee Model, Room, Face, Aperture, Door, or Shade.

## Preconditions

- Locate object targets with `honeybee_search_model_objects`; use `garden_get_base_honeybee_model` for whole-model transforms.
- Provide complete vector, angle, axis, origin, scale, or plane arguments.
- Expect geometry transforms to require validation and sometimes relation repair.

## MCP Route

1. Search for the operation tool: `honeybee_move_object`, `honeybee_rotate_object`, `honeybee_scale_object`, or `honeybee_mirror_object`.
2. Search or retrieve the typed target.
3. Call the transform tool with `garden_root`, `target`, and the complete transform input.
4. Inspect `report`, `persistence_receipt.warnings`, and any top-level postprocess result.
5. Validate or run `honeybee_relate_model` if warnings mention relationship repair.

## Code Mode Patterns

```python
await call_tool("honeybee_move_object", {
    "garden_root": garden_root,
    "target": face_target,
    "vector": {"type": "Vector3D", "x": 0.5, "y": 0, "z": 0}
})
```

```python
await call_tool("honeybee_mirror_object", {
    "garden_root": garden_root,
    "target": model_target,
    "plane": {"type": "Plane", "n": [1, 0, 0], "o": [0, 0, 0]}
})
```

## Success Criteria

- The transform tool returns the original `target` plus a `persistence_receipt` whose `model_target` is the updated model handoff.
- If the transformed target is the whole model, `summary_view.target` is the updated model target.
- Warnings or top-level postprocess output do not contain unresolved repair failures, or the next step handles them.
- Validation passes when the workflow claims a usable model.

## Stop Conditions

- Do not call a transform with empty arguments after a failure. Re-search the target and rebuild the vector, angle, or plane.
- Do not rely on identifier-only targets.
- Do not ignore warnings for local Room/Face/Aperture/Door transforms; they may indicate adjacency or parent-boundary issues.
