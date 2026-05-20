# Flowerpot / Grasshopper 建模接力

## 当前 Grasshopper 组件

- `FP Garden List`：列出已有 Garden，并把每个 Garden 包装成可继续传递的 Flowerpot。
- `FP Create Garden`：新建 Garden，并输出一个新的 Flowerpot。
- `FP Honeybee Link`：把 Honeybee Model 写入 Flowerpot 对应的 Garden，或从该 Garden 跟随当前 base model。
- `FP Energy Properties Input`：从 Flowerpot 对应的 Garden 里读取现有 Energy Properties Library 资源。
- `FP Radiance Properties Input`：从 Flowerpot 对应的 Garden 里读取现有 Radiance Properties Library 资源。

这 5 个组件里，真正构成协作主链的是 `FP Garden List` / `FP Create Garden` 加 `FP Honeybee Link`；两个 Properties Input 组件是辅助读取器，不负责创建资源，也不负责把资源直接应用到模型。

## 推荐连接方式

- 继续已有 Garden：`FP Garden List -> FP Honeybee Link`
- 新建 Garden：`FP Create Garden -> FP Honeybee Link`
- 读取已有 Energy 资源：`Flowerpot -> FP Energy Properties Input`
- 读取已有 Radiance 资源：`Flowerpot -> FP Radiance Properties Input`

`FP Honeybee Link` 的 `_write` 适合在你希望把当前 Grasshopper 里的 Honeybee Model 正式写入 Garden 时使用；`follow_ = True` 适合在你希望 Grasshopper 跟随 Garden 中已经存在的模型变化时使用。`FP Energy Properties Input` 和 `FP Radiance Properties Input` 使用同一个 Flowerpot 即可，它们输出资源对象和 compact `report`，不会自动改写当前模型。

## 与 MCP 的协作方式

- MCP 不要求用户手动拆 Flowerpot。
- 当用户说“当前 Grasshopper 模型”“当前模型”或“正在编辑的模型”时，Agent 应优先通过 `get_active_flowerpot_context` 或 `get_flowerpot` 恢复上下文。
- 恢复到 `summary_view.garden_root` 后，后续操作就回到普通的 Garden 工具链，例如搜索对象、创建房间、编辑窗/遮阳、修改属性或验证模型。

## 用户意图

- Grasshopper 组件创建或接收到一个 opaque `Flowerpot`
- `FP Honeybee Link` 已经把 Honeybee model 写入 Garden，或通过 `follow_` 读取了 Garden base model
- Agent 继续在同一个 Garden base model 上建模、搜索和验证，而不手动拆 `payload_context`

## 已验证最短路径

1. Flowerpot runtime 或 FP 组件创建 Garden Flowerpot
2. `FP Honeybee Link` / Flowerpot worker 将 Honeybee model 写为 Garden base model，并返回 `kind=base_honeybee_model` 的 Flowerpot
3. Agent 在 Code Mode 中调用：
   - Prefer `get_active_flowerpot_context(garden_root=...)` when the Garden root is known and the user says "current Grasshopper model" or "active context".
   - `get_flowerpot(flowerpot=<opaque Flowerpot>)`
   - 从 `summary_view.garden_root` 获取正式 Garden root
   - `create_honeybee_room`
   - `search_honeybee_model_objects`
   - `validate_honeybee_model`

## 已验证 Code Mode 形态

```python
context = await call_tool("get_flowerpot", {"flowerpot": flowerpot})
garden_root = context["summary_view"]["garden_root"]
room = await call_tool(
    "create_honeybee_room",
    {
        "garden_root": garden_root,
        "identifier": "agent_room_from_flowerpot",
        "x_dim": 4,
        "y_dim": 5,
        "height": 3,
    },
)
search = await call_tool(
    "search_honeybee_model_objects",
    {"garden_root": garden_root, "object_type": "room"},
)
validation = await call_tool(
    "validate_honeybee_model",
    {"garden_root": garden_root},
)
```

## 成功判据

- Agent 不直接读取或解释 `flowerpot["payload_context"]`
- `get_flowerpot` 返回 `summary_view.garden_root`
- 新 Room 被写入 Grasshopper link 产生的 Garden base model
- `validate_honeybee_model.is_valid == true`
- metrics 中只有一次外层 `execute`，内层工具为 `get_flowerpot`、`create_honeybee_room`、`search_honeybee_model_objects`、`validate_honeybee_model`
- Grasshopper 侧 `FP Honeybee Link follow_=True` 会在文件变化后自动安排组件刷新；用户不应需要手动切换 `follow_` 才能看到 Agent 写回的模型。

## 证据

- 2026-04-28：`tests/agent_integration/test_agent_flowerpot_modeling_smoke.py::test_agent_can_continue_modeling_from_grasshopper_flowerpot`
- 最新通过指标：一次外层 `execute`，四个内层 MCP 调用，无重复工具，`5,277` total tokens。
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 19 verified an independent Garden handoff path through `create_flowerpot -> get_flowerpot -> create_honeybee_room -> search_honeybee_model_objects -> validate_honeybee_model`. The final model validated with two rooms while treating Flowerpot as opaque. Caveat: `get_active_flowerpot_context` returned `found=false` and earlier retries created 5 Flowerpot records, so active-context discovery and duplicate-registration cost remain product polish gaps.
- 2026-05-01 deterministic regression verifies `create_flowerpot` reuses an existing same source/target/platform record by default, and `get_active_flowerpot_context` falls back to the latest registered Flowerpot when no platform active-context file exists.

## 避坑说明

- 不要让 Agent 手动拆 `payload_context.garden_root`；这会破坏 Flowerpot 的 opaque handoff 目标。
- `get_flowerpot(..., include_body=True)` 仍不会返回模型正文；建模链路应继续使用 Garden root 和 typed targets。
- Repeated `create_flowerpot` calls now default to reuse for the same source, target, and platform context. Only use `force_new=true` when the user explicitly needs a separate handoff record.
- 当前打开的 GH 文档如果还运行的是旧脚本，需要让组件至少解算一次以加载新版 runtime；之后 `follow_=True` 的 refresh poll 才会持续存在。
- Rhino/GH UI 运行时仍需要单独平台 smoke；本路径验证的是 Flowerpot worker 到 MCP Agent 建模的服务侧链路。

## 分工建议

- 建议优先在 Grasshopper 做：组件连线、几何草模、滑块驱动的形体调整、需要即时图形反馈的可视操作。
- 建议优先交给 MCP 做：Program / HVAC / Construction / Modifier 等属性批量创建与赋值、窗和遮阳的批量参数化调整、模型搜索与验证、结果摘要。
- Properties Input 组件适合在 Grasshopper 侧读取 MCP 已经存进 Garden 的资源；如果目标是“先创建资源，再决定稍后怎么用”，更适合让 MCP 先在 Garden 里创建它们。
