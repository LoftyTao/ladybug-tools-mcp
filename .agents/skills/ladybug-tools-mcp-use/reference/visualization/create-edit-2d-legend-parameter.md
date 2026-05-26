# Create Or Edit 2D Legend Parameter

Use this when a VisualizationSet attribute or chart workflow needs a reusable `LegendParameters` dictionary for SVG or 2D legend rendering.

## Preconditions

- This is payload-only. It does not need `garden_root`.
- Downstream tools need the full `object_dict`, not `summary_view`.
- Use this for normal `LegendParameters`; categorized legends are not the stable default path.

## MCP Route

1. Call `visualization_create_2d_legend_parameter`.
2. If needed, call `visualization_edit_2d_legend_parameter` with the returned `object_dict`.
3. Pass the resulting `object_dict` into `room_attributes_`, `face_attributes_`, or result visualization specs.

## Code Mode Pattern

```python
legend = await call_tool("visualization_create_2d_legend_parameter", {
    "title": "Room Identifier",
    "orientation": "horizontal",
    "position_2d": {"origin_x": "5%", "origin_y": "88%"},
    "color_set": "viridis"
})
```

## Success Criteria

- `object_dict.type == "LegendParameters"`.
- `object_dict.title` matches the intended legend title.
- `summary_view.orientation` is `vertical` or `horizontal`.
- `summary_view.origin_x` and `origin_y` reflect the 2D position.

## Stop Conditions

- Do not pass `summary_view` as the legend.
- `position_2d` uses `origin_x` and `origin_y` strings such as `5%` or `20px`.
- `dimensions_2d` supports `segment_height`, `segment_width`, and `text_height`.
- Do not inject `garden_root`.
