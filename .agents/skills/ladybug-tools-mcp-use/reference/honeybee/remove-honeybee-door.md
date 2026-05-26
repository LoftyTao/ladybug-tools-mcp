# Remove Honeybee Door

Use this when the user wants to delete an existing Honeybee Door from a Garden model.

## Preconditions

- Locate the Door with `honeybee_search_model_objects(object_type="door")`.
- Pass the Door typed target as `target`.
- For Surface-adjacent interior doors, one side is enough; the service removes the paired Door.

## MCP Route

1. Search for Door objects.
2. Select the intended Door target.
3. Call `honeybee_remove_door`.
4. Search Door objects again or validate.

## Code Mode Pattern

```python
doors = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "door",
    "identifier": "door_1"
})

removed = await call_tool("honeybee_remove_door", {
    "garden_root": garden_root,
    "target": doors["matches"][0]["target"]
})
```

## Success Criteria

- `summary_view.removed_count == 1` for a single Door or `2` for a Surface interior Door pair.
- `summary_view.removed_identifier` matches the target side.
- Follow-up search does not include the removed Door.
- The persisted path remains the registered Honeybee Model path.

## Stop Conditions

- Do not pass non-Door targets.
- Do not manually delete the adjacent paired Door after the service already removed it.
- If a retry stalls on empty arguments, re-search and pass `matches[i].target`.
