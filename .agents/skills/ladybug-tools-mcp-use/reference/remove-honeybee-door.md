# 删除 Honeybee Door（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，删除一个已存在的 `Door`
- 删除后立即确认模型里不再存在该 `Door`
- 第一阶段已验证 face-hosted door 的主链

## 模拟真实用户 Prompts

```text
请在这个 Garden 里找到 door_1 并删除它，然后确认 door 已经被移除。
先搜索当前模型里的 door，再把第一个 door 删掉，最后再查一次确认结果。
不要创建新对象，只删除已有 door 并告诉我删除的是哪个 identifier。
```

## 已验证最短路径

1. `search("search_honeybee_model_objects")`
2. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "door"`
3. 读取第一个 match 的 `target`
4. `await call_tool(remove_honeybee_door)`，将上一步 `target` 传入 `target`
5. `await call_tool(search_honeybee_model_objects)` 再次确认

搜索参数使用正式字段名：

```json
{
  "name": "search_honeybee_model_objects",
  "arguments": {
    "garden_root": "<exact garden root>",
    "object_type": "door"
  }
}
```

## 已验证最小参数形态

```json
{
  "name": "remove_honeybee_door",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "door",
      "object_identifier": "<door identifier>",
      "parent": {
        "face_identifier": "<host face identifier if hosted>"
      }
    }
  }
}
```

## 成功判据

- `remove_honeybee_door` 返回 `summary_view.removed_count == 1`；如果删除的是
  `Surface` interior door pair，其中一侧 target 会删除两侧 Door，此时
  `summary_view.removed_count == 2`。
- `summary_view.removed_identifier` 与目标 door 一致
- 持久化文件仍是原登记模型路径（例如 `models/honeybee/<model>.hbjson`）
- 再次 `search_honeybee_model_objects(_object_type_="door")` 返回 `count == 0`（或不包含该 identifier）

## 高价值失败模式与避坑说明

- `_target.object_type` 不是 `door` 会直接失败
- 如果 door 带有 `Surface` adjacency，传入任意一侧 Door target；服务会删除相邻
  paired Door 并保持模型有效。
- 对 hosted door，不需要手动拆 parent 再找 face；直接把搜索结果中的完整 `target` 传给工具即可
- interior door pair 场景曾在 agent regression 中触发 `MaxTurnsExceeded`。后续诊断优先查看 `tool_calls.json` 和 `agent_metrics.json`，确认模型是否卡在空参、重复 search，还是未把 `matches[i].target` 传给 `target`。

## 验证记录

- 2026-04-28 live Garden evolution Round 11：MiniMax 删除并重建
  `corridor_to_meeting_door` 的 Surface Door pair，最终模型 valid。该轮 token
  成本较高（`24,038`），因为 Agent 在失败后重放 remove/create；但服务行为正确，
  final model only contains `corridor_to_meeting_door_rebuilt` and `_Adjacent`。
