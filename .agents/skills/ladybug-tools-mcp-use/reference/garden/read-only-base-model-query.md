# Read-Only Base Model Query

Use this when the user asks what model is active in a Garden and explicitly
does not want a write operation.

## When To Use

- The user asks for current models, active base model, or model identifier.
- The user says not to modify the model.
- A workflow needs to confirm the current base Honeybee Model before deciding
  whether to edit.

## Preconditions

- The prompt or context must include an exact `garden_root`.
- Know which model family is being queried. Use `garden_get_base_honeybee_model` for
  Honeybee and the matching family-specific base getter for other model
  families.

## MCP Route

1. Do any prior requested writes first; this page is for the query step.
2. Call `garden_get_base_honeybee_model` for Honeybee base-model state.
3. Answer from the returned target and summary.
4. Stop without creating, editing, saving, or validating unless requested.

## Success Criteria

- `garden_get_base_honeybee_model` is called.
- The answer includes the base model identifier or a clear no-base-model
  diagnostic.
- No write tools are called.

## Stop Conditions

- Stop and ask if the user says "model" but the family is ambiguous.
- Stop when the user asks only for read-only state; do not continue into model
  authoring.
- Do not replace this query with filesystem checks.
