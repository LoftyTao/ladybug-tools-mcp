# Web View Mode

Use this when the user wants a local vtk.js sidebar for Honeybee model-tree selection and edits that continue to follow Garden changes.

## Preconditions

- A Garden exists or will be created in the same Code Mode block.
- Start Web View Mode before significant model edits and keep the selected `garden_root` unchanged.
- When a specific Honeybee model is requested, keep its exact `model_target` for the start call.
- The local sidebar is the user-facing viewer; it is separate from formal reusable VisualizationSet/vtk.js artifacts.

## MCP Route

1. For a blank project, call `GD_create` first and pass its returned `garden_root`; for an existing Garden, pass its literal `garden_root`.
2. Call `GD_web_view_start_mode` once with `garden_root`; include the exact Honeybee `model_target` when one is specified.
3. Open `mode["viewer"]["url"]` in the local sidebar and check `mode["viewer"]["local_only"] is True` and `mode["viewer"]["poll_interval_ms"] == 1500`.
4. Continue ordinary model operations through Code Mode. In the Honeybee tree, a model-level click selects a Room; double-click that Room before selecting its Face, Aperture, Door, or Shade descendants. Tree and 3D selections refer to the same target.
5. Only after the user asks the Agent to act, call the read-only `GD_web_view_get_selection` with the same `garden_root`; the viewer does not wake the Agent automatically.
6. For `selected`, pass `selection["target"]` to the existing edit or transform tool, preserve the returned `model_target`/`host_target` as required by that tool, and pass `selection["expected_revision"]`; validate the resulting model afterward.
7. For `empty`, wait for a new user selection. A valid `scope_target` may remain when the user is still inside a Room.
8. For `stale`, use the current preview/session to refresh and read selection again; do not edit with the old target. When the user asks to stop, call `GD_web_view_stop_mode` with the same `garden_root`.
9. Use `LB_set_to_vtkjs` only when the user explicitly wants a reusable artifact.

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

After a user selection request:

```python
selection = await call_tool("GD_web_view_get_selection", {
    "garden_root": garden_root
})
return {
    "status": selection["status"],
    "target": selection.get("target"),
    "model_target": selection.get("model_target"),
    "host_target": selection.get("host_target"),
    "scope_target": selection.get("scope_target"),
    "expected_revision": selection.get("expected_revision"),
    "summary_view": selection.get("summary_view"),
}
```

## Preview Behavior

- `GD_web_view_start_mode` returns `session_id`, `session_path`, `viewer`, `selection`, and `summary_view`; the local sidebar URL is `viewer.url`.
- When requested, the start result uses the supplied Honeybee `model_target` and immediately generates its model-tree preview.
- `viewer.local_only` is `True` and `viewer.poll_interval_ms` is `1500`.
- Significant model edits and visualization operations create session-managed previews; the viewer detects them by silent polling.
- Before replacing a scene, the viewer saves its camera and restores it after loading the new scene.
- Session previews are separate from registered `visualization_vtkjs` Garden artifacts.
- `GD_web_view_get_selection` returns `selected`, `empty`, or `stale`; a selected result contains `target`, `model_target`, `host_target`, `scope_target`, `expected_revision`, and `summary_view`.
- `scope_target` is the entered Room. A model-level Room click leaves it `null`; an empty selection inside a Room can retain it.

## Success Criteria

- Web View Mode starts before significant model writes.
- Ordinary tool returns remain normal; do not expect a `web_view` field on every write result.
- `viewer.url` opens in the local sidebar and follows the latest active step automatically.
- A selected Room or descendant target is handed to the existing model edit/transform tool with its revision, then validated.
- After an edit, the scene refreshes without a manual export or refresh action and the camera remains unchanged.
- For existing Dragonfly Gardens, inventory and reuse existing targets instead of rebuilding the district.

## Stop Conditions

- Stop and report if `viewer.url` is missing, `viewer.local_only` is not `True`, or `viewer.poll_interval_ms` is not `1500`; do not construct a URL yourself.
- Stop before editing on `empty` or `stale`; an `empty` result has no object target, and a `stale` result has no editable old target.
- Do not invent `open_browser`, `refresh_viewer`, `publish_preview`, or `start_web_view_server` tools.
- Do not call `LB_set_to_vtkjs` after every edit just to refresh the viewer.
- Treat `viewer.url` as a local host URL, not a public share link.
