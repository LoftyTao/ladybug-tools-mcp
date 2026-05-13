# 2026-04-24 Agent Integration Full Run

## Run

```powershell
.\.venv\Scripts\python -m pytest -q tests/agent_integration
```

结果：`36 passed, 4 failed`，耗时约 23 分钟。

## 失败摘要

| 场景 | 结果 | 主要信号 | 判断 |
| --- | --- | --- | --- |
| `test_agent_failure_on_empty_garden_save_is_diagnosable` | failed | `MaxTurnsExceeded`，`tool_calls.json` 为空；stderr 显示 `create_garden` 缺少 `_name` | 低智能模型把 `call_tool.arguments` 丢成空对象，未能稳定进入预期失败路径 |
| `test_agent_can_edit_honeybee_subfaces_and_shade_via_mcp` | failed | `MaxTurnsExceeded`，harness 未保留 tool calls | 组合 edit prompt 过大，容易耗尽 turn；需要拆分 shade/aperture/door focused workflow |
| `test_agent_can_use_honeybee_shade_operate_relate_gap_tools` | failed | 反复调用 `create_honeybee_shades_by_parameters / move_object / relate_honeybee_model`，但 `arguments: null`；约 10 万 token | 第一阶段 gap 组合链路在 Agent 层未稳定，不应写成推荐主路径 |
| `test_agent_handles_parameterized_aperture_request_after_host_discovery` | failed | 只搜索到 `room`，最终回答停在“接下来搜索 face”的计划句 | 自然语言对象发现需要明确 room 之后必须继续搜索 face，不能把计划当完成 |

## 新增 disclosure 维护

- `SKILL.md` 增加全局规则：禁止 `arguments: null / {} / renamed argument object`，遇到 required-argument validation error 后停止空参重试。
- `reference/save-base-honeybee-model-on-empty-garden.md` 记录空 Garden failure 场景中的空参重试。
- `reference/create-honeybee-shades-by-parameters.md` 记录 shade/operate/relate 组合场景中的 `arguments: null` 重复调用。
- `reference/operate-honeybee-objects.md` 记录 `move_object` 必填参数丢失模式。
- `reference/edit-honeybee-subfaces-and-shade.md` 记录大型三对象 edit prompt 的 turn 耗尽风险，建议拆成 focused workflows。
- `reference/search-honeybee-model-objects-natural-language.md` 记录 room 搜索后未继续 face 搜索的问题，并补充 room-to-face 收敛调用形态。

## 后续策略

- 不把失败的组合链路写成 Agent 推荐主路径。
- 对写工具组合 smoke，优先缩短为单工具或两工具 focused smoke；复杂端到端链路只在 focused smoke 稳定后再恢复。
- 对自然语言对象发现，后续 disclosure 应强调“计划句不是完成状态”，找到 room 后必须继续找 face/aperture typed target。
- Harness 后续可考虑在 `MaxTurnsExceeded` 时尽量保留部分 tool call trace；当前两个失败因为异常路径导致 `tool_calls.json` 为空，降低了诊断分辨率。

## 2026-04-25 披露加固后复测

执行了第一批 Tool Description / Field description 加固后，针对失败代表场景做 focused 复测：

| 场景 | 结果 | 变化 |
| --- | --- | --- |
| `test_agent_can_use_honeybee_shade_operate_relate_gap_tools` | passed | 从 `arguments: null` 重复调用降为 4 次有效 MCP `call_tool`：`create_honeybee_shades_by_parameters / move_object / relate_honeybee_model / search_honeybee_model_objects` 各 1 次，无 repeated MCP tools。 |
| `test_agent_handles_parameterized_aperture_request_after_host_discovery` | passed by current assertion | 仍只完成 room search 和 aperture-create 工具发现，最终回答仍停在“下一步搜索 face”的计划句；这说明测试当前足够宽松，但 room-to-face 自动继续调用仍未真正稳定。 |

结论：

- 明确 required shape 和禁止 `arguments: null` 对写工具链路有明显帮助。
- 自然语言对象发现还需要继续强化“计划句不是完成状态”：找到 room 后必须立刻继续 `search_honeybee_model_objects(_object_type_="face")`。

## 2026-04-25 Honeybee Core 剩余披露加固

继续加固 Honeybee Core 剩余 create/edit/remove/validate 工具后，新增 deterministic MCP 交叉测试：

- `test_pure_mcp_create_detailed_honeybee_model_workflow`
  - 从空 Garden 出发，只通过正式 MCP 工具创建 detailed Honeybee model。
  - 覆盖 `create_honeybee_model / edit_honeybee_model / create_honeybee_room / create_honeybee_face / create_honeybee_aperture / create_honeybee_door / create_honeybee_shade / create_honeybee_apertures_by_parameters / create_honeybee_shades_by_parameters / search / validate`。
- `test_existing_model_search_edit_remove_validate_cross_workflow`
  - 从既有 HBJSON 模型出发，通过 MCP 搜索 typed target，再编辑 face/room、删除 aperture、新建 hosted shade、最后 validate。

这两条测试验证固定 MCP workflow 的可组合性；自然语言 Agent 是否能稳定从用户口语收敛到同样 target，仍需独立 Agent smoke 证明。

## 2026-04-25 Honeybee Core Agent 交叉测试补充

- 新增 focused agent workflow，验证从既有模型搜索 face / aperture / room 后执行 edit / remove / create hosted shade / validate。这条路径已通过，metrics 显示 `search_honeybee_model_objects` 被重复调用 3 次，属于预期的对象收敛成本。
- 从空 Garden 连续创建 model / face / aperture / door / hosted shade / validate 的长链路暴露了三个实用风险：默认 `max_turns=10` 容易截断长写流程；Agent 需要被明确告知优先把 `matches[i].target` 或写工具返回的 `target` 传给下游 `_target/_host_target`；同一 Garden/model 的多个写工具并行发出时可能出现后写覆盖先写的对象。后续已在业务层补充唯一 target envelope auto-unwrap 和同进程 Honeybee model 写锁。
- 后续披露层应继续强化 target handoff：`target` 是可复用对象引用，`summary_view/report/persistence_receipt` 只用于确认和诊断。

## 2026-04-25 写锁与 target unwrap 后全量复测

执行：

```powershell
.\.venv\Scripts\python -m pytest -q tests\agent_integration
```

结果：`39 passed, 3 failed`，耗时约 31 分钟。

与本轮业务逻辑直接相关的 Honeybee Core 交叉路径通过，包括：

- 从空 Garden 创建 `model / face / aperture / door / hosted shade / validate`。
- 从既有模型搜索 target 后执行 `edit / remove / create shade / validate`。
- Honeybee create/remove/edit/validate 既有 focused smoke 大部分通过。

剩余失败信号：

| 场景 | 主要信号 | 判断 |
| --- | --- | --- |
| `test_agent_can_discover_and_create_garden` | Agent 反复以 `arguments:null` 调用 `create_garden`，最终回答但没有创建 Garden | 仍是低智能模型空参失败；不是 Honeybee 写锁/target unwrap 回归 |
| `test_agent_can_remove_honeybee_interior_door_pair_via_mcp` | `MaxTurnsExceeded`，当前异常路径没有保留部分 tool trace | 需要后续改善 harness 对 MaxTurns 的部分 trace 保留，或针对 interior door pair 继续加 focused disclosure |
| `test_agent_can_search_radiance_library_modifier` | `MaxTurnsExceeded`，stderr 显示反复空参调用 `search_radiance_library_objects` | Radiance library search 的 required shape 披露仍需后续加固 |

结论：本轮新增的业务层兜底降低了 Honeybee Core 真实 Agent 使用风险，但全量 agent integration 仍暴露跨域空参问题；后续应优先处理 `create_garden` 和 Radiance library search 的 required shape，以及 MaxTurns 异常路径的 trace 保留。

随后对这 3 个失败用例做 focused 复测，结果仍为 `3 failed`，说明它们不是一次性波动：

```powershell
.\.venv\Scripts\python -m pytest -q `
  tests\agent_integration\test_agent_foundation_smoke.py::test_agent_can_discover_and_create_garden `
  tests\agent_integration\test_agent_honeybee_remove_smoke.py::test_agent_can_remove_honeybee_interior_door_pair_via_mcp `
  tests\agent_integration\test_agent_radiance_library_smoke.py::test_agent_can_search_radiance_library_modifier
```

其中 `create_garden` 和 Radiance library search 的失败均出现反复空参调用；interior door pair remove 仍是 `MaxTurnsExceeded` 且没有部分 tool trace。下一轮建议先补 harness 的 partial trace，再决定是增强 tool description、增加兼容 alias，还是拆分对应 agent prompt。

## 2026-04-25 空参与 MaxTurns 诊断修复

本轮针对上面的三个重复问题做 focused 修复：

- `create_garden` tool description 增加完整 `call_tool` JSON 形态，明确使用 `root_dir`，不要改写为 `root_dir`，并禁止 `arguments: null / {}`。
- `search_radiance_library_objects` tool description 和 `query` 参数说明增加完整 required shape，明确 `query` 必须是非空搜索短语。
- agent integration harness 在失败路径读取 Agents SDK exception 的 `run_data.new_items/raw_responses`，因此 `MaxTurnsExceeded` 后也会尽量写出部分 `tool_calls.json`、`run_items.json`、`agent_metrics.json` 和 `raw_responses.json`。
- `test_agent_can_discover_and_create_garden` prompt 改用正式 `root_dir` 字段；`test_agent_can_remove_honeybee_interior_door_pair_via_mcp` prompt 改用正式 `_garden_root/_object_type_` 搜索字段。

这些修改不改变业务工具语义，目标是把低智能模型从空参重试和旧字段名漂移中拉回正式 MCP contract。

随后全量 agent regression 暴露了一个新的披露反效果：harness 系统指令里的负面示例 `arguments null or {}` 会被 MiniMax 在部分场景里误读成“应该这么调用”。修复策略改为正向表述：

- 每个 `call_tool` 都必须提供非空 JSON object。
- 使用 tool 的 required parameter names。
- Windows 路径放入 JSON 字符串时必须转义反斜杠。
- 如果出现 required-argument validation error，重建完整 arguments object，而不是围绕错误形态重试。

另外，`test_agent_can_remove_honeybee_room_via_mcp` 的 prompt 开始用 `json.dumps` 生成 arguments 示例，避免 Windows path 反斜杠破坏 JSON 形态。
