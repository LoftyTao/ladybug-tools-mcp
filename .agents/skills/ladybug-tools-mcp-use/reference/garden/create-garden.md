# Create Garden

Use this when the user wants a new Garden project, either in the default
Gardens root or at an exact directory.

## When To Use

- The user asks to create, initialize, or start a new Garden.
- The onboarding gate has resolved to "create a new Garden".
- A later workflow needs a valid Garden before any model or resource tool can
  run.

Do not use this page when the user already gave an existing Garden and only
wants to inspect it; use `garden_get` or a base-model query instead.

## Preconditions

- Decide the Garden name.
- If the user provides a directory, pass it as `root_dir`.
- If no directory is provided, let `garden_create` use the default Gardens root;
  do not substitute the repository root or current working directory.

## MCP Route

1. Search only if the tool name is not already clear:
   `search("create garden")`.
2. Call `garden_create`.
3. Keep the returned `garden_root` for all downstream tools.
4. If the next step is read-only confirmation, call `garden_get` or
   `garden_get_base_honeybee_model`; do not use filesystem probes inside Code Mode.

## Arguments

Default-root candidate path:

```json
{
  "name": "garden_create",
  "arguments": {
    "name": "Office Garden"
  }
}
```

Explicit root path:

```json
{
  "name": "garden_create",
  "arguments": {
    "name": "Office Garden",
    "root_dir": "<exact garden root>"
  }
}
```

`arguments` must be a complete object. If an Agent drops it to `null` or `{}`,
rebuild the full call instead of retrying the empty shape.

## Success Criteria

- The tool returns a reusable `garden_root`.
- `garden.json` exists according to the returned Garden state.
- `.gitignore`, `summary_view.path`, and the persistence receipt are present
  when returned.

## Stop Conditions

- Stop and ask when the Garden name or explicit path is unclear.
- Stop when the path points to a known Garden and the user wanted reuse rather
  than a new project.
- Stop after returning the created Garden unless the user also requested a
  model/resource/simulation step.
