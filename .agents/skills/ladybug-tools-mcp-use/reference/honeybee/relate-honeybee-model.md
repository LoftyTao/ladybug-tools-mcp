# Relate Honeybee Model

Use this when a Honeybee Model needs adjacency solving, intersection, or relationship cleanup after import, room creation, editing, removal, or geometry transforms.

## Preconditions

- A Garden exists with a base Honeybee Model.
- The caller understands that relation solving may change room face geometry and paired subfaces.
- Validation should follow relation work.

## MCP Route

1. Call `honeybee_relate_model` with the intended `relation_mode`.
2. Call `honeybee_validate_model`.
3. If validation fails, inspect issues before choosing another repair mode.

## Default Relation Pattern

```python
await call_tool("honeybee_relate_model", {
    "garden_root": garden_root,
    "relation_mode": "solve_adjacency"
})
```

Default behavior intersects rooms before solving adjacency. It can clone a single one-sided missing Aperture or Door when the mismatch is simple, but it does not enable the broader overwrite, cleanup, or delete-mismatched-subface behavior used by full repair.

## Explicit Full Repair Pattern

Use `explicit_relate_full` only when the user asks for overwrite, cleanup, mismatched subface repair, or broad adjacency repair.

```python
await call_tool("honeybee_relate_model", {
    "garden_root": garden_root,
    "relation_mode": "explicit_relate_full"
})
```

This mode enables merge coplanar faces, overwrite, mismatched subface cleanup, relationship cleanup, and `subface_mismatch_policy="clone_missing"`.

## Success Criteria

- Relation output reports the intended mode.
- The updated model handoff is `summary_view.model_target` or `persistence_receipt.model_target`; the result does not expose a top-level `target`.
- Validation passes after the relation step.
- Interior Surface faces and paired Apertures/Doors remain coherent.

## Stop Conditions

- Do not pass `_relation_mode_`; use the public field `relation_mode`.
- Do not call subsequent tools with `{}` if a low-context model drops arguments. Rebuild the full call with `garden_root`.
- Do not use full repair as the default for simple room creation; it is a stronger repair mode.
