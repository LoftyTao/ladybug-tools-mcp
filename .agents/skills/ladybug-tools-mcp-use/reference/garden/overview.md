# Garden Skill Overview

Garden is the persistent project context for Ladybug Tools MCP. Use this
category before authoring, simulation, visualization, or platform handoff when
the Agent must create, select, inspect, version, or clean a project.

## Common Scenarios

- The user wants a new Garden or asks which Garden to continue with.
- The user gives an existing Garden path and wants state confirmation.
- A workflow needs the current Honeybee/Dragonfly/Fairyfly base model target.
- A completed user-level write should be versioned.
- The user asks to undo, restore, or clean temporary Garden content.
- Reuse the selected Garden for follow-up edits, reruns, and result reads within the same user session unless the user requests a new Garden.

## Preconditions

- A folder is not a Garden until `GD_create` creates `garden.json`.
- Use literal `garden_root` strings from the user, onboarding gate, or prior
  tool returns.
- Inside Code Mode, confirm Garden state with MCP tools; do not import `os`,
  `pathlib`, or probe the filesystem.

## Usual MCP Route

1. For a new project, call `GD_create`.
2. For an existing project, call `GD_get` or the appropriate base-model
   getter.
3. Carry `garden_root`, typed targets, `summary_view`, and persistence receipts
   into downstream category skills.
4. After a completed user-level write that changes authoring truth, call
   `GD_create_version` once.

## Authoring Results And Retries

Garden authoring writes return a unified `operation_result`. Read
`operation_target`, `runtime_status`, `readiness_status`, `before_revision`,
`after_revision`, `affected_targets`, `persistence_receipt`, and `report`.

- Pass the latest known Garden revision as `expected_revision` when available.
- Reuse `result["operation_result"]["operation_target"]["operation_id"]` as
  `operation_id` only for retrying the same immutable intent. A replay returns
  `runtime_status="replayed"` and does not advance the revision.
- If the result is `runtime_status="conflict"` with
  `readiness_status="reload_required"`, reread current Garden/model state,
  set `expected_revision` to the current revision (the conflict result's
  `after_revision`), and retry the intended write. Do not overwrite newer state
  or reuse an operation ID for changed arguments.

## Stop Conditions

- Ask the user before creating a Garden when the path/name is ambiguous.
- Stop before cleanup when the requested scope would touch `garden.json`,
  `models/`, `libraries/`, final reports, or user-requested deliverables.
- Stop before restore when the Garden has unsaved authoring truth changes,
  unless the user explicitly accepts discarding or first versioning them.

## References

- `create-garden.md`
- `read-only-base-model-query.md`
- `save-base-honeybee-model-on-empty-garden.md`
- `garden-version-management.md`
- `cleanup-garden-workspace.md`
