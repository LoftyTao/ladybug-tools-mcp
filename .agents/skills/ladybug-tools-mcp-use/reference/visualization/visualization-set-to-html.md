# Export VisualizationSet To HTML

Use this when the user wants an existing VisualizationSet exported as an interactive HTML artifact under the Garden.

## Preconditions

- Prefer `visualization_set_target` from an upstream tool.
- Use full VisualizationSet dictionaries only for explicit debug/payload workflows.
- The exporter writes a Garden artifact and updates `garden.json.artifacts`.

## MCP Route

1. Create or retrieve a compact VisualizationSet target.
2. Call `visualization_set_to_html`.
3. Pass `garden_root`, `visualization_set_target`, and optional `name`.
4. Return `artifact_receipt.artifact_path` or top-level artifact fields.

## Code Mode Pattern

```python
html = await call_tool("visualization_set_to_html", {
    "garden_root": garden_root,
    "visualization_set_target": vis["visualization_set_target"],
    "name": "agent_html_preview"
})
```

## Recovery

Exporters can load a Garden `visualization_set_json` artifact record or a Garden-relative path shape such as `{"artifact": "artifacts/visualization_sets/name.json"}` when recovering from `garden_list_artifacts`. This is deterministic-pass recovery; target handoff is the preferred path.

## Success Criteria

- `artifact_receipt.status == "persisted"`.
- `artifact_receipt.artifact_type == "visualization_html"`.
- `artifact_receipt.artifact_path` points under `artifacts/visualization/html/`.
- `summary_view.exists == true`.

## Stop Conditions

- Do not carry full VisualizationSet dictionaries when a target exists.
- Do not repeatedly list Garden artifacts after a successful export unless the user asks for a list.
- `output_subdir` must be Garden-relative.
- Future Agents should create one VisualizationSet target and export each requested format once.
