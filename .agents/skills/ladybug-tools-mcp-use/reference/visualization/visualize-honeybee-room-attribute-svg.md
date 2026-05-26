# Visualize Honeybee Room Attributes To SVG

Use this when the user wants Honeybee Room attributes converted to a classified VisualizationSet layer and exported as SVG with a 2D legend.

## Preconditions

- Use stable Honeybee Room attribute paths such as `identifier`.
- Create a 2D LegendParameter and pass its full `object_dict`.
- Use `color_by="none"` to avoid mixing default model coloring with the attribute layer.

## MCP Route

1. Call `visualization_create_2d_legend_parameter`.
2. Call `visualization_honeybee_model_to_visualization_set` with `room_attributes_`.
3. Pass `return_visualization_set=false` for target-first export when possible.
4. Call `visualization_set_to_svg` with the target or, for debug, the full VisualizationSet.

## Code Mode Pattern

```python
legend = await call_tool("visualization_create_2d_legend_parameter", {
    "title": "Room Identifier",
    "orientation": "horizontal",
    "position_2d": {"origin_x": "5%", "origin_y": "88%"},
    "color_set": "viridis"
})
vis = await call_tool("visualization_honeybee_model_to_visualization_set", {
    "garden_root": garden_root,
    "color_by": "none",
    "room_attributes": [{
        "name": "Room Identifier",
        "attrs": ["identifier"],
        "legend_parameter": legend["object_dict"]
    }],
    "name": "agent_attribute_svg",
    "return_visualization_set": False
})
svg = await call_tool("visualization_set_to_svg", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "agent_attribute_svg",
    "width": 640,
    "height": 360,
    "render_2d_legend": True
})
```

## Success Criteria

- `summary_view.room_attributes[0].name` matches the attribute layer name.
- The VisualizationSet contains attribute-colored `AnalysisGeometry`.
- SVG artifact path points under `artifacts/visualization/svg/`.
- The SVG contains the legend title.

## Stop Conditions

- Do not describe this classified attribute path as a continuous numeric heat map.
- Do not pass `summary_view` as the legend parameter.
- Do not use fake Room attributes.
