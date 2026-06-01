# Web View Mode

Use this when the user wants a vtk.js preview panel that follows Garden modeling edits without manually exporting a new vtk.js file after every step.

## Preconditions

- A Garden exists or will be created in the same Code Mode block.
- Web View Mode is a FastMCP App preview session. It is separate from formal reusable VisualizationSet/vtk.js artifacts.
- The MCP host must advertise the Apps UI extension for an iframe to render. Check `web_view_start_mode["app"]["client_supports_ui_extension"]`; if it is `false`, the session can still record previews and `viewer.url` gives a local-only fallback URL for hosts such as current Codex.
- Continue using normal model tools after the mode starts.

## MCP Route

1. Call `web_view_start_mode` with `garden_root` to open or refresh the host App panel.
2. Continue Honeybee, Dragonfly, or Fairyfly writes through their normal Code Mode tools.
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
    "set_base": True
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

- `web_view_start_mode` starts the session and returns `app.resource_uri`, `viewer`, `session`, `session_path`, and `summary_view`.
- `app.client_supports_ui_extension=false` means the MCP client did not advertise `io.modelcontextprotocol/ui`; do not describe that as a rendered App. Open or share `viewer.url` when present to use the local fallback viewer.
- The App resource is `ui://web_view/ladybug-tools/vtkjs-preview.html`.
- The App polls MCP preview state and reads active `.vtkjs` bytes through App-only backend tools.
- The fallback URL is local-only, bound to `127.0.0.1`, and reads the same Garden session state and `.vtkjs` payloads without requiring a separate frontend project runtime.
- Significant Honeybee, Dragonfly, and deterministic-pass Fairyfly writes create session steps under `tmp/web_view/session.json`.
- Preview files live under `tmp/web_view/previews/`.
- Search/read tools do not create preview steps.
- Automatic previews are session state, not registered `visualization_vtkjs` Garden artifacts.

## Success Criteria

- Web View Mode starts before significant model writes.
- Ordinary tool returns remain normal; do not expect a `web_view` field on every write result.
- If `client_supports_ui_extension=true`, the FastMCP App follows the latest active step automatically.
- If `client_supports_ui_extension=false`, `viewer.url` should be reachable in the local host browser and follows the same latest active step.
- For existing Dragonfly Gardens, inventory and reuse existing targets instead of rebuilding the district.

## Stop Conditions

- Do not invent `open_browser`, `refresh_viewer`, `publish_preview`, or `start_web_view_server` tools.
- Do not call `visualization_set_to_vtkjs` after every edit just to refresh demo mode.
- Do not inspect `tmp/web_view` from inside Code Mode; return compact MCP tool results.
- Do not treat the fallback URL as a public share link; it is a local Agent/Codex handoff only.
- Keep Web View test commands, run metrics, and retained evidence in LLM-Wiki.
