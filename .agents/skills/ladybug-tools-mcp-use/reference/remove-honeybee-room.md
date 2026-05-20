# 删除 Honeybee Room（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，删除一个已存在的 `Room`
- 删除后立即确认模型里不再存在该 `Room`

## 模拟真实用户 Prompts

```text
请在这个 Garden 里找到 room_1 并删除它，然后确认房间已经被移除。
先搜索当前模型里的 room，再把第一个房间删掉，最后再查一次确认结果。
不要创建新对象，只删除已有 room 并告诉我删除的是哪个 identifier。
```

## 已验证最短路径

1. Code Mode `execute` 内 `await call_tool("search_honeybee_model_objects", ...)`，`object_type = "room"`
2. 读取第一个 match 的 `target`
3. `await call_tool("remove_honeybee_room", ...)`，将上一步 `target` 传入 `target`
4. `await call_tool("search_honeybee_model_objects", ...)` 再次确认
5. 对相邻房间模型，额外 `validate_honeybee_model` 确认没有残留 `Missing Adjacency`

## 已验证最小参数形态

```json
{
  "name": "remove_honeybee_room",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "room",
      "object_identifier": "<room identifier>",
      "parent": {}
    }
  }
}
```

## 成功判据

- `remove_honeybee_room` 返回 `summary_view.removed_count == 1`
- `summary_view.removed_identifier` 与目标房间一致
- 如果被删房间曾与其他房间有 `Surface` 邻接，`summary_view.adjacency_cleanup.faces` 会显示解除的邻接数量
- 如果保留房间上有指向被删房间的室内 aperture / door 子面，服务会移除这些子面，而不是把它们转成室外窗/门
- 持久化文件仍是原登记模型路径（例如 `models/honeybee/<model>.hbjson`）
- 再次 `search_honeybee_model_objects(_object_type_="room")` 返回 `count == 0`（或不包含该 identifier）
- 删除相邻房间后，保留房间不再引用已删除 room，`validate_honeybee_model.summary_view.is_valid == true`

## 高价值失败模式与避坑说明

- `_target.object_type` 不是 `room` 会直接失败；不要把 `face/aperture/shade` target 误传给该工具
- `target` 必须来自当前模型的真实搜索结果，手写 target 容易出现 `object_identifier` 或 `model_identifier` 不一致
- 删除前后都建议显式搜索一次，避免把“工具调用成功”误当成“目标对象已移除”

## Evidence

- 2026-05-01 Codex `ladybug_mcp_tester` 20-Task Batch A Task 4 exposed a real boundary: deleting one room from a solved-adjacency pair left the surviving room with a `Surface` boundary condition pointing at the deleted room, producing `000204 Missing Adjacency`.
- 2026-05-01 deterministic regression added and passed: `remove_honeybee_room` clears Surface face references and removes hosted aperture/door child objects tied to the deleted room before persistence.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch B Task 06 exposed the next boundary: a surviving room could validate while still keeping an old interior door as an exterior child after the adjacent room was deleted. The service now removes hosted aperture/door child objects whose `Surface` boundary referenced the deleted room.
