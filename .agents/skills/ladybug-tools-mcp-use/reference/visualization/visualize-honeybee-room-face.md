# Visualize Honeybee Room Or Face

Use this when the user wants only one Honeybee Room or Face converted to a VisualizationSet instead of the whole model.

## Preconditions

- Locate the Room or Face with `honeybee_search_model_objects`.
- Pass the full typed target to the visualization tool.
- This path is read-only for the Honeybee Model.

## MCP Route

1. Search the object with `object_type="room"` or `object_type="face"`.
2. Pass `matches[i].target` to `visualization_honeybee_room_to_visualization_set` or `visualization_honeybee_face_to_visualization_set`.
3. Set `return_visualization_set=false` unless debug output is needed.
4. Export or compose the resulting target only when requested.

## Code Mode Pattern

```python
rooms = await call_tool("honeybee_search_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
    "identifier": "open_office"
})
vis = await call_tool("visualization_honeybee_room_to_visualization_set", {
    "garden_root": garden_root,
    "target": rooms["matches"][0]["target"],
    "name": "room_preview",
    "return_visualization_set": False
})
```

## Success Criteria

- `summary_view.object_type` is `room` or `face`.
- `summary_view.object_target` matches the input typed target.
- `summary_view.geometry_count > 0`.
- Wireframe mode returns wireframe-style geometry only.

## Stop Conditions

- Do not handwrite object selectors or identifier-only targets.
- Room/Face SDK paths do not directly support `color_by=None`; MCP `color_by="none"` falls back to wireframe-only semantics.
