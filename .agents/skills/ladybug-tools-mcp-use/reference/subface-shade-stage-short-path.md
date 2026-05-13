# B-stage Subface/Shade Short Path

## Scope

Use this reference when the user wants to add windows, subfaces, shades, overhangs, or louvers to existing Honeybee Rooms in a Garden model.

This page was added after real MiniMax B-stage evidence showed a closed but expensive path: the Agent created windows and louvers, but spent `133,030` tokens across 10 `execute` calls, 6 `search_honeybee_model_objects` calls, and one mistaken inner `get_schema` call.

2026-04-26 short-path reruns lowered some single-request context pressure and proved the server can end with the correct Garden state, but the Agent still failed to return final output before `MaxTurnsExceeded`. Treat the pattern below as a candidate short path, not a fully verified recommended path.

## Target Pattern

Keep the whole dependent chain in one Code Mode `execute` block whenever possible.

1. Search `room` targets once.
2. For each selected room, search `face` once using `children_scope` and exterior-wall filters.
3. Choose a wall face from the compact face search result.
4. Create apertures with `create_honeybee_apertures_by_parameters`.
5. Use the returned aperture `target` or `targets[0]` directly for shade creation.
6. Create shades, overhangs, or louvers with `create_honeybee_shades_by_parameters`. Do not use low-level `create_honeybee_shade` unless the user provides explicit Face3D shade geometry.
7. Verify once at the end with room `child_counts` or narrow `children_scope`, not a full model relist after every write.
8. Stop after successful write results. MCP write tools persist the Garden; do not search for `save_garden` or `save_base_honeybee_model` unless the user explicitly asks for a separate save operation.

## Stage Completion Response

After B-stage write calls succeed and one narrow verification confirms the requested apertures/shades exist, return a compact stage summary and stop. The summary should include the `garden_root`, created or reused aperture targets, created or reused shade targets, and a small count summary such as `{"rooms_checked": 2, "apertures": 2, "shades": 3}`.

Do not continue probing for unrelated model details. Do not search for save_garden or `save_base_honeybee_model`, `search_garden_assets`, or generic asset tools. Successful create/edit tools already persist the Garden, and repeated post-write searches were the failure mode in the latest MiniMax short-path runs.

## Compact Code Mode Shape

```python
garden_root = r"<exact garden root>"

rooms = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})

room_targets = {
    match["identifier"]: match["target"]
    for match in rooms["matches"]
}

office_faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["open_office"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})

office_front = next(
    match["target"]
    for match in office_faces["matches"]
    if match.get("local_identifier") == "Front"
)

office_window = await call_tool("create_honeybee_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": office_front,
    "generation_mode": "by_ratio",
    "ratio": 0.38,
    "identifier_prefix": "open_office_window"
})

office_shades = await call_tool("create_honeybee_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": office_window["target"],
    "generation_mode": "louver_by_count",
    "parameters": {
        "depth": 0.45,
        "louver_count": 3,
        "offset": 0.15
    },
    "identifier_prefix": "open_office_louver"
})

return {
    "office_window": office_window["target"],
    "office_shades": office_shades["targets"],
}
```

Repeat the `face -> aperture -> shade` part for the second room inside the same block. Do not assume variables survive into a later `execute` block.

## Picking The Face

- Prefer `local_identifier` such as `Front`, `Back`, `Left`, or `Right` when the prompt implies a side.
- If the user asks for a solar-facing or exterior window and the exact side is not important, choose one `face_type="Wall"` and `boundary_condition="Outdoors"` result.
- If using normal direction, read `normal_vector`; `normal` is a dict and should not be indexed like a list.
- Do not call `get_schema` inside `execute`; if schema is needed, use outer Code Mode `get_schema` before the next `execute`.

## Recovery After Partial Writes

If the previous block may already have created windows or shades:

1. Recreate `garden_root` literally in the new block.
2. Search the room or face with `children_scope`.
3. Reuse existing aperture targets when `child_counts.apertures` or a narrow aperture search shows windows already exist.
4. Only call create tools for missing objects.

## Success Criteria For Real Agent Runs

- `status=ok`
- `search_honeybee_model_objects <= 3` for a two-room B stage
- `execute <= 4`
- no inner `call_tool("get_schema", ...)`
- total tokens below `100,000`; ideal target is `60,000-80,000`
- no duplicate apertures or shades

## Latest MiniMax Evidence

- `supervised_cross_task_06_honeybee_parameterized_windows`: external supervised MiniMax on the stable Honeybee suite functionally created parameterized apertures without rebuilding the model or rooms, but supervisor stopped repeated `search_honeybee_model_objects` after the write. Treat this as functionally verified but still search-cost-heavy.
- `supervised_cross_task_08_honeybee_louver_shades`: external supervised MiniMax closed cleanly with one `create_honeybee_shades_by_parameters`, three object searches, one validation, and no model/room rebuild.
- `supervised_cross_task_09_honeybee_edit_subfaces_shades`: external supervised MiniMax functionally edited an aperture and a related shade, but repeated search triggered supervisor intervention. The run also confirmed the usefulness of the `room_target` search alias as a recovery compatibility input; canonical guidance remains `children_scope` / `host_target`.
- `manual_staged_metrics_b_subfaces_shades_short_path_v1`: failed at `122,278` tokens, max input-window ratio `0.068477`, with 11 object searches. Exposed point drift: `children_scope` as bare string and shade hints `offset_from_host` / `louver_orientation`.
- `manual_staged_metrics_b_subfaces_shades_short_path_after_fix_v1`: failed at `143,272` tokens, max input-window ratio `0.094229`, but deterministic inspection showed the Garden had the requested state: 2 apertures and 3 open_office shades. The Agent then searched for save tools and exceeded turns.
- `manual_staged_metrics_b_subfaces_shades_short_path_after_fix_v2`: failed at `109,839` tokens, max input-window ratio `0.074902`, and again left the Garden with 2 apertures and 3 open_office shades. Remaining failure is Agent behavior: repeated `get_base_honeybee_model` / object search, result indexing mistakes, and no final answer.
- `manual_staged_metrics_b_subfaces_shades_short_path_staged_scaffold_v1`: failed at `146,354` tokens, max input-window ratio `0.085229`. The fresh staged-scaffold run wrote 2 apertures but 0 shades because the Agent selected low-level `create_honeybee_shade` and attempted explicit louver geometry instead of using `create_honeybee_shades_by_parameters`.
- `manual_staged_metrics_b_subfaces_shades_tool_disclosure_v2`: succeeded at `90,730` tokens, max input-window ratio `0.073066`, and left the Garden with 2 apertures plus 3 open_office louvers. The Agent still attempted low-level `create_honeybee_shade` 3 times before recovering to `create_honeybee_shades_by_parameters`.

Classification: `instruction_noncompliance + result_reuse_gap + search_loop`, with a newer `tool_discovery_gap + schema_disclosure_gap` shade-tool-selection variant. `scope_shape=cluster`. The path is functionally recoverable from Garden state but not yet token-efficient or final-answer-stable.

## Observed Anti-Patterns

- One `execute` call per search or write.
- Referring to `garden_root` from a previous `execute` block instead of redefining it.
- Searching all faces, then both rooms, then all apertures, then all shades before making the first write.
- Re-listing the whole model after each aperture or shade creation.
- Handwriting aperture targets from guessed identifiers when the create result already returned `target` and `targets[]`.
