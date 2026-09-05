# Web View Mode

Use this when the user wants a local vtk.js sidebar that follows Garden modeling edits without manually exporting a new vtk.js file after every step.

## Preconditions

- A Garden exists or will be created in the same Code Mode block.
- Start Web View Mode before significant model edits and keep the selected `garden_root` unchanged.
- The local sidebar is the user-facing viewer; it is separate from formal reusable VisualizationSet/vtk.js artifacts.

## MCP Route

1. For a blank project, call `GD_create` first and pass its returned `garden_root`; for an existing Garden, pass its literal `garden_root`.
2. Call `GD_web_view_start_mode` once with that `garden_root`.
3. Open `mode["viewer"]["url"]` in the local sidebar and check `mode["viewer"]["local_only"] is True` and `mode["viewer"]["poll_interval_ms"] == 1500`.
4. Continue Honeybee, Dragonfly, Fairyfly, or VisualizationSet operations through their normal Code Mode tools.
5. When the user asks to stop, call `GD_web_view_stop_mode` with the same `garden_root`.
6. Use `LB_set_to_vtkjs` only when the user explicitly wants a reusable artifact.

## Code Mode Pattern

```python
mode = await call_tool("GD_web_view_start_mode", {
    "garden_root": garden_root,
    "name": "Local Web View"
})
return {
    "viewer_url": mode["viewer"]["url"],
    "local_only": mode["viewer"]["local_only"],
    "poll_interval_ms": mode["viewer"]["poll_interval_ms"],
}
```

## Preview Behavior

- `GD_web_view_start_mode` returns `viewer`, `session`, `session_path`, and `summary_view`; the local sidebar URL is `viewer.url`.
- `viewer.local_only` is `True` and `viewer.poll_interval_ms` is `1500`.
- Significant model edits and visualization operations create session-managed previews; the viewer detects them by silent polling.
- Before replacing a scene, the viewer saves its camera and restores it after loading the new scene.
- Session previews are separate from registered `visualization_vtkjs` Garden artifacts.

## Success Criteria

- Web View Mode starts before significant model writes.
- Ordinary tool returns remain normal; do not expect a `web_view` field on every write result.
- `viewer.url` opens in the local sidebar and follows the latest active step automatically.
- After an edit, the scene refreshes without a manual export or refresh action and the camera remains unchanged.
- For existing Dragonfly Gardens, inventory and reuse existing targets instead of rebuilding the district.

## Stop Conditions

- Stop and report if `viewer.url` is missing, `viewer.local_only` is not `True`, or `viewer.poll_interval_ms` is not `1500`; do not construct a URL yourself.
- Do not invent `open_browser`, `refresh_viewer`, `publish_preview`, or `start_web_view_server` tools.
- Do not call `LB_set_to_vtkjs` after every edit just to refresh the viewer.
- Treat `viewer.url` as a local host URL, not a public share link.
