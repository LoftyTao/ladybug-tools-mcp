# Remove Honeybee Room

Use this when the user wants to delete an existing Honeybee Room from a Garden model.

## Preconditions

- Locate the Room with `honeybee_search_model_objects(object_type="room")`.
- Pass the Room typed target as `target`.
- Expect adjacency cleanup if the Room shared Surface faces with other Rooms.

## MCP Route

1. Search Room objects.
2. Select the Room target.
3. Call `honeybee_remove_room`.
4. Search Rooms again to confirm deletion.
5. Validate when the model has adjacent rooms or hosted interior subfaces.

## Code Mode Pattern

```python
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "room_1"
})

removed = await call_tool("honeybee_remove_room", {
    "garden_root": garden_root,
    "target": rooms["matches"][0]["target"]
})

validation = await call_tool("honeybee_validate_model", {"garden_root": garden_root})
```

## Success Criteria

- `summary_view.removed_count == 1`.
- `summary_view.removed_identifier` matches the target Room.
- `summary_view.adjacency_cleanup.faces` reports cleaned adjacent faces when applicable.
- Follow-up Room search does not include the removed identifier.
- Validation passes for the remaining model.

## Stop Conditions

- Do not pass Face, Aperture, Door, or Shade targets.
- Do not assume the tool call alone proves deletion; confirm with search.
- Keep broad adjacency-cleanup evidence in LLM-Wiki.
