# Subface And Shade Stage Short Path

Use the bounded checkpoint route below when the user wants one Room's exterior Wall Face opened by ratio and fitted with horizontal louvers. For other windows, subfaces, or explicit shade geometry, use the low-level route and the specific create references.

## Preconditions

- A Garden exists with a base Honeybee Model and a target Room.
- `room_target`, `face_target`, and `model_target` are typed targets from MCP results; `face_target` must be an exterior Wall Face on `room_target`.
- On the first call choose a stable `checkpoint_id` and provide `aperture_ratio`, `shade_depth`, and positive integer `shade_count`; `tolerance` defaults to `0.01`.
- Re-declare the exact `garden_root` in every Code Mode `execute` block.

## Bounded Checkpoint Route

1. If no model target is already held, call `GD_get_base_honeybee_model`.
2. Search the Room once with `HB_search_model_objects`; require one clear match and pass its `target` as `room_target`.
3. Search exterior Wall faces once with `children_scope=room_target` and pass the clear match `target` as `face_target`.
4. Call `HB_complete_opening_shade_stage` with the exact first-call arguments below.
5. Read `validation_state`, `next_action`, target lists, and the persistence result before deciding whether to stop or resume.

## First-call Code Mode Pattern

```python
garden_root = r"<exact garden root>"

base = await call_tool("GD_get_base_honeybee_model", {
    "garden_root": garden_root
})
model_target = base["target"]

rooms = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "model_target": model_target,
    "object_type": "room",
    "identifier": "<room identifier>"
})
if rooms["summary_view"]["count"] != 1:
    return {"next_action": "resolve_room_target"}
room_target = rooms["matches"][0]["target"]

faces = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "model_target": model_target,
    "object_type": "face",
    "children_scope": room_target,
    "face_type": "Wall",
    "boundary_condition": "Outdoors",
    "identifier": "<face identifier>"
})
if faces["summary_view"]["count"] != 1:
    return {"next_action": "resolve_face_target"}
face_target = faces["matches"][0]["target"]

stage = await call_tool("HB_complete_opening_shade_stage", {
    "garden_root": garden_root,
    "checkpoint_id": "<stable checkpoint id>",
    "room_target": room_target,
    "face_target": face_target,
    "model_target": model_target,
    "aperture_ratio": 0.30,
    "shade_depth": 0.40,
    "shade_count": 2
})

return stage
```

## Checkpoint Resume

In a new `execute` block, bind `checkpoint_target` to the complete target returned by the previous stage and pass it unchanged. Do not pass only its `checkpoint_id` or `path`, and do not resend the room, face, model, or stage parameters.

```python
garden_root = r"<exact garden root>"
# checkpoint_target is the complete prior result["checkpoint_target"] dict.
resumed = await call_tool("HB_complete_opening_shade_stage", {
    "garden_root": garden_root,
    "checkpoint_target": checkpoint_target
})

return resumed
```

## Bounded Stage Success And Stops

- Success requires `missing_requirements == []`, `validation_state["is_valid"] is True`, and `next_action == "stage_complete"`.
- The result includes `created_targets`, `reused_targets`, `missing_requirements`, `validation_state`, `next_action`, `checkpoint_target`, `model_target`, `summary_view`, `persistence_receipt`, and `report`; `operation_result` exposes `runtime_status`, `readiness_status`, `before_revision`, and `after_revision` when present.
- A completed replay can return `operation_result["runtime_status"] == "no_change"` with all stage targets in `reused_targets`; do not create another aperture or shade and do not search for a save tool.
- If `missing_requirements` is non-empty or `next_action == "resolve_conflict"`, stop and surface the requirements. Do not silently overwrite same-name or parameter-conflicting Apertures/Shades, replay the whole stage, or fall back to guessed targets.
- If a new first call reports that `checkpoint_id` already exists, pass the original complete `checkpoint_target` to resume or choose a new identifier; never reuse the occupied identifier for another Room or Face.
- If `next_action == "review_validation"` or the checkpoint target is missing or mismatched, stop for model/checkpoint review before downstream work.

## Low-Level MCP Route For Other Geometry

1. Search Room targets once.
2. For each selected Room, search exterior Wall faces with `children_scope`.
3. Pick the host face by `local_identifier`, `normal_vector`, or the user's side description.
4. Create Apertures with `HB_create_apertures_by_parameters`.
5. Pass the returned Aperture `target` or `targets[0]` directly into `HB_create_shades_by_parameters`.
6. Verify once with narrow child searches or child counts.
7. Stop after successful writes; write tools already persist the Garden.

## Code Mode Pattern

```python
garden_root = r"<exact garden root>"

rooms = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room"
})
room_targets = {m["identifier"]: m["target"] for m in rooms["matches"]}

faces = await call_tool("HB_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["open_office"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors"
})
host = next(m["target"] for m in faces["matches"] if m.get("local_identifier") == "Front")

window = await call_tool("HB_create_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": host,
    "generation_mode": "by_ratio",
    "ratio": 0.38,
    "identifier_prefix": "open_office_window"
})

shades = await call_tool("HB_create_shades_by_parameters", {
    "garden_root": garden_root,
    "host_target": window["target"],
    "generation_mode": "louver_by_count",
    "parameters": {
        "depth": 0.45,
        "louver_count": 3,
        "offset": 0.15,
        "base_name": "open_office_louver"
    }
})

return {"window": window["target"], "shades": shades["targets"]}
```

## Recovery After Partial Writes

- Re-declare `garden_root` in each new `execute` block.
- Search the Room or Face with `children_scope`.
- Reuse existing Aperture targets when child counts or narrow searches show the windows already exist.
- Create only missing objects.

## Success Criteria

- For a two-room stage, keep `HB_search_model_objects` calls narrow and minimal.
- No inner `get_schema` calls inside `execute`.
- No duplicate apertures or shades.
- Final response includes `garden_root`, created/reused aperture targets, created/reused shade targets, and small counts.

## Stop Conditions

- Do not search for `save_garden`, `GD_save_base_honeybee_model`, `search_garden_assets`, or generic asset tools after successful writes.
- Do not relist the whole model after each write.
- Do not handwrite Aperture targets when create results already returned them.
