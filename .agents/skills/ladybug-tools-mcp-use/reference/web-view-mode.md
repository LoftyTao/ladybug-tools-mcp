# Web View Mode 演示预览

## 用户意图

- 用户希望开启本地 Web View / demo mode，让浏览器里的 Garden 预览自动跟随 Agent 建模编辑。
- 用户不想每一步手动调用可视化导出或刷新浏览器。
- 用户希望保持普通建模工具返回结构不变，同时看到连续的 `.vtkjs` 预览切换。

## 已验证推荐路径

Agent 推荐在一个 Code Mode `execute` block 里开启 Web View Mode，然后继续普通建模工具链：

```python
garden = await call_tool(
    "create_garden",
    {"name": "Agent Web View Demo Mode", "root_dir": garden_root},
)
await call_tool(
    "start_web_view_mode",
    {"garden_root": garden["garden_root"], "name": "Agent Demo Mode"},
)
await call_tool(
    "create_honeybee_model",
    {
        "garden_root": garden["garden_root"],
        "identifier": "agent_web_view_demo_model",
        "set_base": True,
    },
)
room = await call_tool(
    "create_honeybee_room",
    {
        "garden_root": garden["garden_root"],
        "identifier": "agent_web_view_demo_room",
        "x_dim": 6,
        "y_dim": 4,
        "height": 3,
    },
)
search = await call_tool(
    "search_honeybee_model_objects",
    {"garden_root": garden["garden_root"], "object_type": "room"},
)
edited = await call_tool(
    "edit_honeybee_room",
    {
        "garden_root": garden["garden_root"],
        "target": room["target"],
        "display_name": "Agent Demo Mode Room",
    },
)
```

`start_web_view_mode` starts the Web View session, the local viewer server, and the Garden watcher. It returns a local `viewer.url` for the host app to open in a side-panel browser. After the mode is active, significant Honeybee write calls automatically produce session-managed `.vtkjs` previews. The Agent should keep using normal modeling/editing/search tools; it does not need to call a separate preview-refresh or server-start tool.

## 成功判据

- Exactly one outer `execute` is enough for a short demo-mode modeling/edit flow.
- Inner MCP tools include `start_web_view_mode` before significant Honeybee writes.
- `start_web_view_mode` returns `viewer.status="serving"` and a local `viewer.url`.
- Significant write tools create Web View session steps under `tmp/web_view/session.json`.
- Session preview files live under `tmp/web_view/previews/`.
- The viewer workspace `config.json` follows the latest active step automatically; Agents do not need to manually rebuild the viewer.
- Read/search tools such as `search_honeybee_model_objects` do not create preview steps.
- Automatic previews are local Web View state; they are not registered as formal Garden `visualization_vtkjs` artifacts.
- Ordinary tool returns remain normal; do not expect a `web_view` field on every write result.

## 避坑说明

- Use `start_web_view_mode`, not an invented `open_browser`, `refresh_viewer`, or `publish_preview` tool.
- Do not call a separate `start_web_view_server` tool; server startup is part of `start_web_view_mode`.
- If the viewer port is already occupied, surface the startup error instead of choosing a fallback port silently.
- Do not call `visualization_set_to_vtkjs` after every edit just to refresh demo mode; Web View Mode already does this automatically for significant writes.
- Do not use Python filesystem imports inside `execute` to inspect `tmp/web_view`; return compact MCP tool results and let the service-side viewer/session manage preview files.
- `stop_web_view_mode` disables future automatic previews but preserves the session history.
- If the user explicitly wants a formal reusable vtk.js artifact, call `visualization_set_to_vtkjs`; that is separate from automatic demo-mode previews.

## 证据

- 2026-05-11: `tests/agent_integration/test_agent_web_view_mode_smoke.py::test_agent_can_use_web_view_demo_mode_cross_workflow` passed with a Garden Web View watcher already running.
- Metrics: 1 outer `execute`, 5 inner MCP calls (`start_web_view_mode`, `create_honeybee_model`, `create_honeybee_room`, `search_honeybee_model_objects`, `edit_honeybee_room`), no repeated MCP tools, `6,121` total tokens with MiniMax-M2.7.
