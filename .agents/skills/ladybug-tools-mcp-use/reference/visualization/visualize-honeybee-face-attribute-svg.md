# Visualize Honeybee Face Attributes To SVG

Use this when the user wants Honeybee Face-level attributes filtered by face type or boundary condition and exported as SVG with a 2D legend.

## Preconditions

- Use real Honeybee Face attribute paths such as `identifier`.
- Use `face_types` and `boundary_conditions` to limit the layer when requested.
- Create a 2D LegendParameter and pass its full `object_dict`.

## MCP Route

1. Create a 2D LegendParameter.
2. Call `visualization_honeybee_model_to_visualization_set` with `color_by="none"` and `face_attributes`.
3. Include filters such as `face_types=["Wall"]` and `boundary_conditions=["Outdoors"]` when needed.
4. Export with `visualization_set_to_svg`.

## Code Mode Pattern

```python
legend = await call_tool("visualization_create_2d_legend_parameter", {
    "title": "Exterior Wall Identifier",
    "orientation": "vertical",
    "position_2d": {"origin_x": "4%", "origin_y": "12%"},
    "color_set": "ecotect"
})
vis = await call_tool("visualization_honeybee_model_to_visualization_set", {
    "garden_root": garden_root,
    "color_by": "none",
    "face_attributes": [{
        "name": "Exterior Wall Identifier",
        "attrs": ["identifier"],
        "legend_parameter": legend["object_dict"],
        "face_types": ["Wall"],
        "boundary_conditions": ["Outdoors"]
    }],
    "name": "agent_face_attribute_svg",
    "return_visualization_set": False
})
svg = await call_tool("visualization_set_to_svg", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "agent_face_attribute_svg",
    "width": 640,
    "height": 360,
    "render_2d_legend": True
})
```

## Success Criteria

- `summary_view.face_attributes[0].name` matches the attribute layer.
- Filters remain visible in summary, such as `["Wall"]` and `["Outdoors"]`.
- The VisualizationSet contains attribute-colored `AnalysisGeometry`.
- SVG contains the legend title.

## Stop Conditions

- Do not describe this as a continuous heat map.
- Do not use unverified filter values as if they were known valid SDK attributes.
- Do not pass a partial legend object.
