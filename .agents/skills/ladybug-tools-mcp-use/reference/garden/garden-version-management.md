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
- For restore, inspect available versions with `garden_list_versions`.
- If dirty authoring truth exists before restore, ask whether to version the
  current state first.

## MCP Route

Create one version after a completed user request:

1. Finish modeling, edit, library, or validation work.
2. If an Energy run is accepted as the final answer, read EUI or ERR/SQL
   evidence first, then call `garden_create_version` once for that accepted
   scenario.
3. Use a short `subject` and compact structured `summary`.

Restore:

1. Call `garden_list_versions`.
2. Choose by `subject`, `summary`, `version_id`, or returned `target`.
3. Call `garden_restore_version`.
4. Confirm restored state with search, validation, or visualization.

## Arguments

Create:

```json
{
  "name": "garden_create_version",
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

Restore by id:

```json
{
  "name": "garden_restore_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "version_id": "<version id from garden_list_versions>",
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
  "name": "garden_restore_version",
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

- `garden_create_version` returns `version_id`, `version_target`,
  `summary_view`, and `persistence_receipt`.
- `garden_list_versions` returns compact history in `matches` / `versions`.
- `garden_restore_version` returns `restored_from_version` and `new_version`.
- Restore creates new history; it does not rewrite old history.

## Stop Conditions

- Do not request or manufacture Git diffs.
- Do not place HBJSON, DFJSON, full library objects, or model snapshots in
  `summary`.
- Do not clean `models/` or `libraries/` to unblock restore.
- If only `tmp` or regenerable artifacts are dirty, inspect status and use the
  cleanup skill with approved scopes.
