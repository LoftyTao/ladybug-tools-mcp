# 空 Garden 上保存 Base Model

## 用户意图

- 故意验证空 Garden 上 `save_base_honeybee_model` 的失败表现与诊断信息

## 模拟真实用户 Prompts

```text
创建一个空 Garden，不要创建任何 model，然后直接保存 base model。
请在这个空 Garden 上调用 save_base_honeybee_model，如果失败就报告失败，不要自动恢复。
帮我验证一个空 Garden 上 save_base_honeybee_model 的报错是否清晰。
```

## 已验证失败路径

1. `call_tool(create_garden)`
2. `call_tool(save_base_honeybee_model)`

## 典型错误语义

- `Garden has no base model to save`

## 推荐处理

- 报告失败
- 保留诊断信息
- 不要擅自恢复为“自动创建一个 model 再保存”，除非用户明确要求你这样做

## 优先保留的诊断产物

- `tool_calls.json`
- `result_summary.json`
- `run_items.json`
- `raw_responses.json`（如果存在）

## Prompt 约束

- 明确写出不要自动恢复
- 明确要求先建空 Garden，再调用 `save_base_honeybee_model`
- 如果目标是验证失败路径，不要让 prompt 同时暗示“最后一定要成功”
- 低智能模型可能把 `create_garden` 或 `save_base_honeybee_model` 的参数丢成 `{}`，随后反复空参重试直到 turn 耗尽；prompt 中应给出完整 `call_tool` JSON 形态，并明确禁止 `arguments: null` 或 `{}`。

## 2026-04-24 全量 Agent 回归观察

- 全量 `tests/agent_integration` 中，本场景曾失败为 `MaxTurnsExceeded`，`tool_calls.json` 为空，但 stderr 显示模型反复用空参数调用 `create_garden`。
- 这不是 `save_base_honeybee_model` 服务层语义变化，而是 Agent 参数构造失败；后续 disclosure 应优先减少自然语言步骤，直接给出 `create_garden` 与 `save_base_honeybee_model` 的完整参数对象。

