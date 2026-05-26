# Export VisualizationSet To SVG

Use this when the user wants an existing VisualizationSet exported as a 2D SVG artifact for documents, drawing-style previews, or lightweight delivery.

## Preconditions

- Prefer compact `visualization_set_target` values.
- Create/compose the VisualizationSet before export.
- SVG export writes a Garden artifact and updates `garden.json.artifacts`.

## MCP Route

1. Create or retrieve a compact VisualizationSet target.
2. Call `visualization_set_to_svg`.
3. Pass `garden_root`, `visualization_set_target`, and optional `name`, `width`, `height`, `view`, and legend flags.
4. Return `artifact_receipt.artifact_path`.

## Code Mode Pattern

```python
svg = await call_tool("visualization_set_to_svg", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "agent_room_face_svg",
    "width": 640,
    "height": 360,
    "view": "Top"
})
```

## Success Criteria

- `artifact_receipt.status == "persisted"`.
- `artifact_receipt.artifact_type == "visualization_svg"`.
- `artifact_receipt.artifact_path` points under `artifacts/visualization/svg/`.
- `summary_view.exists == true`.
- `summary_view.view`, width, and height reflect export settings.

## Stop Conditions

- Do not carry full VisualizationSet dictionaries when a target exists.
- Supported view values include `Top`, `Left`, `Right`, `Front`, `Back`, `NE`, `NW`, `SE`, and `SW`.
- `output_subdir` must be Garden-relative.
- Do not invent folder/file tools; visualization exporters write artifacts themselves.
