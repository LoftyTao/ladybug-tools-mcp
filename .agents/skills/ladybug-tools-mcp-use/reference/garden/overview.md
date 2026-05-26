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

## Preconditions

- A folder is not a Garden until `garden_create` creates `garden.json`.
- Use literal `garden_root` strings from the user, onboarding gate, or prior
  tool returns.
- Inside Code Mode, confirm Garden state with MCP tools; do not import `os`,
  `pathlib`, or probe the filesystem.

## Usual MCP Route

1. For a new project, call `garden_create`.
2. For an existing project, call `garden_get` or the appropriate base-model
   getter.
3. Carry `garden_root`, typed targets, `summary_view`, and persistence receipts
   into downstream category skills.
4. After a completed user-level write that changes authoring truth, call
   `garden_create_version` once.

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
