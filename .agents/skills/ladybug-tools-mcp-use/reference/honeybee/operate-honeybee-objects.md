# Operate Honeybee Objects

Use this when the user wants to move, rotate, scale, or mirror an existing Honeybee Model, Room, Face, Aperture, Door, or Shade.

## Preconditions

- Locate object targets with `HB_search_model_objects`; use `GD_get_base_honeybee_model` for whole-model transforms.
- Provide complete vector, angle, axis, origin, scale, or plane arguments.
- Expect geometry transforms to require validation and sometimes relation repair.

## MCP Route

1. Search for the operation tool: `HB_move_object`, `HB_rotate_object`, `HB_scale_object`, or `HB_mirror_object`.
2. Search or retrieve the typed target.
3. Call the transform tool with `garden_root`, `target`, and the complete transform input.
4. Inspect `report`, `persistence_receipt.warnings`, and any top-level postprocess result.
5. Validate or run `HB_relate_model` if warnings mention relationship repair; use the independent Room Move route below for Room-specific rejection and readback.

## Independent Room Move

Use this route only for one independent Honeybee Room.

1. Search with `HB_search_model_objects` using `object_type="room"`; pass only `matches[i]["target"]` as `target`.
2. Call `HB_move_object` with a finite `vector`; reuse `operation_id` only for the same intent, and pass `expected_revision` only when its current value is known (otherwise omit it or pass `null`).
3. Inspect `operation_result.runtime_status`, `operation_result.operation_target.operation_id`, `before_revision`, `after_revision`, `persistence_receipt`, `target_changes`, and `report`.
4. Read the current position separately with `HB_search_model_objects` using `object_type="face"` and `room_identifier`; inspect each match's `vertices` or `geometry.boundary`. A replay receipt and its revisions do not establish the current position.
5. Reuse an `operation_id` only with the same Room target, vector, and original `expected_revision`; expect `runtime_status="replayed"` and the original persistence receipt. A zero vector returns `runtime_status="no_change"`, does not advance the revision, and keeps that operation ID bound to the zero-vector intent.
6. Stop when Surface adjacency or dynamic geometry is rejected; do not use another transform or relationship repair to bypass the rejection.
7. If preview or scene readback fails, retry only the readback and do not issue another move.

## Code Mode Patterns

```python
await call_tool("HB_move_object", {
    "garden_root": garden_root,
    "target": face_target,
    "vector": {"type": "Vector3D", "x": 0.5, "y": 0, "z": 0}
})
```

```python
rooms = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": room_identifier,
})
room_target = rooms["matches"][0]["target"]
moved = await call_tool("HB_move_object", {
    "garden_root": garden_root,
    "target": room_target,
    "vector": {"type": "Vector3D", "x": 1, "y": 0, "z": 0},
    "operation_id": operation_id,
    "expected_revision": expected_revision,  # known current revision, or None
})
current_faces = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "room_identifier": room_identifier,
})
return {
    "move": moved,
    "current_faces": [
        {
            "vertices": match["vertices"],
            "geometry_boundary": match["geometry"]["boundary"],
        }
        for match in current_faces["matches"]
    ],
}
```

```python
await call_tool("HB_mirror_object", {
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
