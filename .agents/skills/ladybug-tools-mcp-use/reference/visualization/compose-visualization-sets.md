# Compose VisualizationSets

Use this when the user wants several model, object, solar-context, or analysis VisualizationSets combined before export.

## Preconditions

- Prefer compact `visualization_set_target` values from upstream tools.
- Use `conflict_strategy="rename"` when duplicate geometry identifiers are likely.
- Only compose VisualizationSets with compatible units and semantic purpose.

## MCP Route

1. Create or retrieve multiple compact VisualizationSet targets.
2. Call `visualization_compose_visualization_sets`.
3. Pass `garden_root` and `visualization_set_targets`.
4. Set `return_visualization_set=false`.
5. Export the composed target with HTML/SVG/vtk.js exporters when requested.

## Code Mode Pattern

```python
combined = await call_tool("visualization_compose_visualization_sets", {
    "garden_root": garden_root,
    "visualization_set_targets": [model_vis["target"], room_vis["target"]],
    "name": "combined_scene",
    "conflict_strategy": "rename",
    "return_visualization_set": False
})
```

## Success Criteria

- `visualization_set_target.target_type == "visualization_set"`.
- `summary_view.input_count` equals the number of inputs.
- `summary_view.renamed_geometry_ids` records automatically renamed duplicate layers when applicable.
- `summary_view.body_returned == false`.

## Stop Conditions

- Do not handwrite half-targets with only `path`; use full targets or artifact records.
- Do not write `type="visualization_set"`; target field is `target_type`.
- Do not combine geometry previews and Energy/DataCollection charts if units or semantics are incompatible.
- Keep compose/export evidence in LLM-Wiki.
