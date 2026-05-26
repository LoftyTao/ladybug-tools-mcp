# Remove Honeybee Aperture

Use this when the user wants to delete an existing Honeybee Aperture from a Garden model.

## Preconditions

- Locate the Aperture with `honeybee_search_model_objects`.
- Pass the Aperture typed target as `target`.
- If the user describes a room or wall, search room -> face -> aperture before removing.

## MCP Route

1. Search the Room or Face if needed.
2. Search Apertures with `children_scope` or `face_identifier`.
3. Call `honeybee_remove_aperture`.
4. Search again to confirm the identifier is gone.
5. Validate when deleting from adjacency-sensitive interior models.

## Code Mode Pattern

```python
apertures = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "aperture",
    "identifier": "Front_Aperture"
})

removed = await call_tool("honeybee_remove_aperture", {
    "garden_root": garden_root,
    "target": apertures["matches"][0]["target"]
})
```

## Success Criteria

- `honeybee_remove_aperture.summary_view.removed_count >= 1`.
- The removed identifier matches the target.
- A follow-up Aperture search does not include the removed identifier.

## Stop Conditions

- Do not handwrite Aperture targets.
- Do not confuse "open a window" with "remove a window"; creation uses `honeybee_create_apertures_by_parameters`.
- Keep broad removal evidence in LLM-Wiki.
