# Remove Honeybee Face

Use this when the user wants to delete an orphaned Honeybee Face directly owned by the model.

## Preconditions

- The target Face must be orphaned. Room-hosted Faces are part of a closed Room solid and should not be removed with this tool.
- Locate the Face with `honeybee_search_model_objects`.
- Pass the typed Face target as `target`.

## MCP Route

1. Search `object_type="face"`.
2. Confirm the selected match has no Room parent.
3. Call `honeybee_remove_face`.
4. Search again to confirm removal.
5. Validate if the model will be simulated or reused.

## Code Mode Pattern

```python
faces = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "identifier": "wall_1"
})

removed = await call_tool("honeybee_remove_face", {
    "garden_root": garden_root,
    "target": faces["matches"][0]["target"]
})
```

## Success Criteria

- `summary_view.removed_count == 1`.
- `summary_view.removed_identifier` matches the selected Face.
- Follow-up face search does not include the removed identifier.

## Stop Conditions

- Do not remove room-hosted Faces; the tool should reject targets with `parent.room_identifier`.
- Do not pass Room, Aperture, Door, or Shade targets.
- Do not handwrite targets when the model can be searched.
