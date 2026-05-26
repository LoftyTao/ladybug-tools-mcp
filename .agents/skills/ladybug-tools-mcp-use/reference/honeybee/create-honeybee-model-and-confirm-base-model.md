# Create Honeybee Model And Confirm Base Model

Use this when a Garden needs a new Honeybee Model and later tools must operate on the same registered base Honeybee Model.

## Preconditions

- A Garden exists. If not, run `garden_create` first.
- The user is asking for a Honeybee Model, not a Dragonfly Model or an exported HBJSON outside the Garden.
- The model identifier is known or can be derived safely from the user request.

## MCP Route

1. Search for the model creation and base-model query tools.
2. Call `honeybee_create_model` with the exact `garden_root`.
3. Set `set_base = true` for the model that should become the Garden's active Honeybee Model.
4. Set `save_back = true` unless the user explicitly asks for a dry object.
5. Call `garden_get_base_honeybee_model` to confirm the Garden registry points to the model you just created.

## Code Mode Pattern

```python
garden_root = r"<exact garden root>"

model = await call_tool("honeybee_create_model", {
    "garden_root": garden_root,
    "identifier": "office_model",
    "set_base": True,
    "save_back": True
})

base = await call_tool("garden_get_base_honeybee_model", {
    "garden_root": garden_root
})

return {
    "created_model": model["target"],
    "base_model": base["target"],
    "base_identifier": base["summary_view"]["model_identifier"]
}
```

## Adding Initial Objects

`honeybee_create_model` can receive `add_objects` with full Honeybee object dictionaries such as `Room`, `Face`, `Aperture`, `Door`, or `Shade`. This is a deterministic object-dict path. Do not pass typed targets from create tools into `add_objects`; create tools already persist their own results.

## Success Criteria

- `models/honeybee/<identifier>.hbjson` exists in the Garden.
- `garden.json.base_honeybee_model.model_identifier` equals the created model identifier.
- `garden_get_base_honeybee_model` returns a `honeybee_model` target for the same model.

## Stop Conditions

- Do not use list or search tools as base-model confirmation. Confirm with `garden_get_base_honeybee_model`.
- Do not create a second model when the user's real request is to edit or validate the current base model.
- If the Garden has no base model and the user wants to create rooms, create and confirm the base model before room tools.
