# Web View Mode

Use this when the user wants a local browser preview that follows Garden modeling edits without manually exporting a new vtk.js file after every step.

## Preconditions

- A Garden exists or will be created in the same Code Mode block.
- Web View Mode is a local preview session. It is separate from formal reusable VisualizationSet/vtk.js artifacts.
- Continue using normal model tools after the mode starts.

## MCP Route

1. Call `web_view_start_mode` with `garden_root`.
2. Continue Honeybee, Dragonfly, or Fairyfly writes through their normal tools.
3. Let significant writes create session-managed preview steps.
4. Use `web_view_stop_mode` only when the user asks to stop automatic previews.
5. Use `visualization_set_to_vtkjs` only when the user explicitly wants a reusable artifact.

## Code Mode Pattern

```python
garden = await call_tool("garden_create", {
    "name": "Agent Web View Demo Mode",
    "root_dir": garden_root
})
mode = await call_tool("web_view_start_mode", {
    "garden_root": garden["garden_root"],
    "name": "Agent Demo Mode"
})
model = await call_tool("honeybee_create_model", {
    "garden_root": garden["garden_root"],
    "identifier": "agent_web_view_demo_model",
    "_set_base_": True
})
room = await call_tool("honeybee_create_room", {
    "garden_root": garden["garden_root"],
    "identifier": "agent_web_view_demo_room",
    "x_dim": 6,
    "y_dim": 4,
    "height": 3
})
```

## Preview Behavior

- `web_view_start_mode` starts the session, local viewer server, and Garden watcher.
- It returns `viewer.status="serving"` and a local `viewer.url`.
- Significant Honeybee, Dragonfly, and deterministic-pass Fairyfly writes create session steps under `tmp/web_view/session.json`.
- Preview files live under `tmp/web_view/previews/`.
- Search/read tools do not create preview steps.
- Automatic previews are session state, not registered `visualization_vtkjs` Garden artifacts.

## Success Criteria

- Web View Mode starts before significant model writes.
- Ordinary tool returns remain normal; do not expect a `web_view` field on every write result.
- The viewer workspace follows the latest active step automatically.
- For existing Dragonfly Gardens, inventory and reuse existing targets instead of rebuilding the district.

## Stop Conditions

- Do not invent `open_browser`, `refresh_viewer`, `publish_preview`, or `start_web_view_server` tools.
- Do not call `visualization_set_to_vtkjs` after every edit just to refresh demo mode.
- Do not inspect `tmp/web_view` from inside Code Mode; return compact MCP tool results.
- Keep Web View test commands, run metrics, and retained evidence in LLM-Wiki.
