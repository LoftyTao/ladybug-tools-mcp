# Cleanup Garden Workspace

Use this when the user explicitly wants to clean generated or temporary content
inside a Garden without touching authoring truth.

## When To Use

- The user asks to clear temporary files, generated previews, runs, imports, or
  non-authoring artifacts.
- A restore/version workflow is blocked by dirty generated files that can be
  regenerated.
- The user asks for a dry-run cleanup report.

Do not use this for deleting a Garden, model files, libraries, final reports,
or user-requested deliverables.

## Preconditions

- Confirm `garden_root`.
- Confirm cleanup scopes from the allowed enum.
- Prefer `_dry_run_=true` when the user is asking what would be removed.

Allowed cleanup scopes:

- `artifacts`
- `flowerpots`
- `imports`
- `payloads`
- `runs`
- `tmp`

## MCP Route

1. Search if needed:
   `search("cleanup garden workspace tmp artifacts without touching models")`.
2. Call `garden_cleanup_workspace` with `garden_root` and `_cleanup_scopes`.
3. Read `removed`, `skipped`, `summary_view`, and `persistence_receipt`.
4. Report only the cleaned scopes and any skipped scopes.

## Arguments

```json
{
  "name": "garden_cleanup_workspace",
  "arguments": {
    "garden_root": "<exact garden root>",
    "_cleanup_scopes": ["tmp"]
  }
}
```

Dry run:

```json
{
  "name": "garden_cleanup_workspace",
  "arguments": {
    "garden_root": "<exact garden root>",
    "_cleanup_scopes": ["tmp", "artifacts", "flowerpots"],
    "_dry_run_": true
  }
}
```

## Success Criteria

- The response includes `report`, `summary_view`, `persistence_receipt`,
  `removed`, and `skipped`.
- Cleaned non-authoring directories may be recreated as empty skeletons.
- `garden.json`, `models/`, and `libraries/` remain unchanged.

## Stop Conditions

- Stop before accepting arbitrary relative paths as cleanup scopes.
- Stop before deleting the Garden root.
- Stop before cleaning user-requested final charts, reports, run results, or
  library resources unless the user explicitly includes them and the tool scope
  supports it.
