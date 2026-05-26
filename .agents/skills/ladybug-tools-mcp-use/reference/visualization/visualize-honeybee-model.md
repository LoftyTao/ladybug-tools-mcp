# Visualize Honeybee Model

Use this when the user wants a Garden base Honeybee Model or specific Honeybee Model converted to a VisualizationSet for preview or later export.

## Preconditions

- A Garden exists with a base Honeybee Model or a model target is available.
- Choose compact target handoff unless the user asks for debug/payload output.
- This path is read-only for the Honeybee Model.

## MCP Route

1. Call `visualization_honeybee_model_to_visualization_set`.
2. Pass `garden_root` and optionally `model_target`.
3. Set `return_visualization_set=false` for normal Agent use.
4. Read `summary_view.geometry_count`, identifiers, and `visualization_set_target`.
5. Export with `visualization_set_to_html` or `visualization_set_to_svg` only when requested.

## Code Mode Pattern

```python
vis = await call_tool("visualization_honeybee_model_to_visualization_set", {
    "garden_root": garden_root,
    "name": "agent_preview",
    "color_by": "type",
    "return_visualization_set": False
})
```

## Success Criteria

- `target` or `visualization_set_target` has `target_type == "visualization_set"`.
- `summary_view.model_target.model_identifier` points to the intended model.
- `summary_view.geometry_count > 0`.
- `summary_view.body_returned == false` for compact target mode.

## Stop Conditions

- Do not assume this generates HTML or SVG; export is a separate tool call.
- `color_by="none"` maps to SDK `None` semantics.
- Model-level `color_by` supports `type`, `boundary_condition`, and `none`; do not use `face_type`.
- Keep preview artifacts and metrics in LLM-Wiki.
