# Save Base Honeybee Model On Empty Garden

Use this only for negative-path validation where the user intentionally wants to
observe the failure produced by saving a base Honeybee Model before one exists.

## When To Use

- The user explicitly asks to create an empty Garden and call
  `garden_save_base_honeybee_model`.
- The user is validating error wording or diagnostics.
- The prompt says not to auto-recover.

Do not use this when the user wants a successful model-save workflow. Create or
select a Honeybee Model first in that case.

## Preconditions

- Create or select an empty Garden with no base Honeybee Model.
- Preserve the user's failure-validation intent.
- Prepare complete `call_tool` argument objects; do not allow `arguments: null`
  or `{}` retries.

## MCP Route

1. Call `garden_create` if an empty Garden is not already available.
2. Call `garden_save_base_honeybee_model` against that Garden.
3. Report the failure and compact diagnostic.
4. Stop without creating a model unless the user asks for repair.

## Expected Failure

The expected semantic error is:

```text
Garden has no base model to save
```

## Success Criteria

- The negative-path call is actually attempted.
- The response reports the failure clearly.
- Diagnostics such as tool calls, result summary, run items, or raw responses
  are preserved when the harness produced them.
- No automatic model creation occurs.

## Stop Conditions

- Stop before "fixing" the failure by creating a model.
- Stop if the prompt also demands final success; ask whether the goal is failure
  validation or recovery.
- Stop if the Garden is not actually empty; this path is only meaningful for the
  no-base-model case.
