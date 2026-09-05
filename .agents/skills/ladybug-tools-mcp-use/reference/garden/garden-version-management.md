# Garden Version Management

Use this when a completed user-level workflow should be saved as a recoverable
Garden version, or when the user asks to undo, go back, list history, or restore
an earlier Garden state.

## When To Use

- A request changed authoring truth: `garden.json`, `models/`, or `libraries/`.
- The user asks for version history, undo, rollback, restore, or go back.
- A restore workflow needs compact history without exposing model bodies.

Do not use version tools as object-diff tools. Confirm object state with Search,
Validate, or Visualization tools after restore.

## Preconditions

- Confirm `garden_root`.
- For version creation, finish the user-level write first.
- A Garden created without Git remains usable for authoring and simulation.
  Once Git is available, the first `GD_get_version_status`,
  `GD_create_version`, `GD_list_versions`, or `GD_restore_version` call
  initializes Garden-local `.git/`; do not recreate the Garden or create `.git`
  manually.
- An empty Garden with no `models/` or `libraries/` can go directly to
  `GD_create_version`; do not create placeholder directories.
- For restore, inspect available versions with `GD_list_versions`.
- If dirty authoring truth exists before restore, ask whether to version the
  current state first.

## MCP Route

Create one version after a completed user request:

1. Finish modeling, edit, library, or validation work.
2. If an Energy run is accepted as the final answer, read EUI or ERR/SQL
   evidence first, then call `GD_create_version` once for that accepted
   scenario.
3. Use a short `subject` and compact structured `summary`.
   For an empty Garden, use the same call with a subject such as
   `init: Garden`; the first version contains the existing authoring truth
   without requiring model or library directories.

Restore:

1. Call `GD_list_versions`.
2. Choose by `subject`, `summary`, `version_id`, or returned `target`.
3. Call `GD_restore_version`.
4. Confirm restored state with search, validation, or visualization.

## Arguments

Create:

```json
{
  "name": "GD_create_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "subject": "feat: add office windows",
    "summary": {
      "operation": "create_windows",
      "targets": ["office_west_Front"],
      "validation": "passed"
    },
    "source": "agent"
  }
}
```

For an empty Garden, use `subject: "init: Garden"` and a compact summary such
as `{ "operation": "initialize_garden" }`.

Restore by id:

```json
{
  "name": "GD_restore_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "version_id": "<version id from GD_list_versions>",
    "summary": {
      "operation": "undo_user_request"
    },
    "source": "agent"
  }
}
```

Restore by target:

```json
{
  "name": "GD_restore_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "version_target": {
      "target_type": "garden_version",
      "garden_id": "<garden id>",
      "version_id": "<version id>"
    },
    "source": "agent"
  }
}
```

## Success Criteria

- `GD_create_version` returns `version_id`, `version_target`,
  `summary_view`, and `persistence_receipt`.
- `GD_list_versions` returns compact history in `matches` / `versions`.
- `GD_restore_version` returns `restored_from_version` and `new_version`.
- Restore creates new history; it does not rewrite old history.

## Stop Conditions

- Do not request or manufacture Git diffs.
- If Git is unavailable, stop version, history, and restore operations and
  report that Git must be installed; continue other Garden workflows.
- Do not place HBJSON, DFJSON, full library objects, or model snapshots in
  `summary`.
- Do not clean `models/` or `libraries/` to unblock restore.
- If only `tmp` or regenerable artifacts are dirty, inspect status and use the
  cleanup skill with approved scopes.
