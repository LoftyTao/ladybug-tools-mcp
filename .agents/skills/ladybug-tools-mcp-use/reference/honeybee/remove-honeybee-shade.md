# Remove Honeybee Shade

Use this when the user wants to delete an existing orphaned or hosted Honeybee Shade.

## Preconditions

- Locate the Shade with `honeybee_search_model_objects(object_type="shade")`.
- Pass the Shade typed target as `target`.
- Hosted shades keep their parent path in the search target; do not rebuild it manually.

## MCP Route

1. Search Shade objects.
2. Select the intended target.
3. Call `honeybee_remove_shade`.
4. Search Shade objects again or use `children_scope` on the parent to confirm.

## Code Mode Pattern

```python
shades = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "shade",
    "identifier": "shade_1"
})

removed = await call_tool("honeybee_remove_shade", {
    "garden_root": garden_root,
    "target": shades["matches"][0]["target"]
})
```

## Success Criteria

- `summary_view.removed_count == 1`.
- `summary_view.removed_identifier` matches the selected Shade.
- Follow-up search does not include the removed identifier.
- The persisted path remains the registered Honeybee Model path.

## Stop Conditions

- Do not pass Room, Face, Aperture, or Door targets.
- Do not split parent data out of the target; pass the full typed target.
- Confirm removal before claiming the shade is gone.
