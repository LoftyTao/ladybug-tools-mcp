# 删除 Honeybee Face（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，删除一个已存在的 orphaned `Face`
- 删除后立即确认模型里不再存在该 `Face`
- 第一阶段只支持 orphaned face，不支持 room-hosted face

## 模拟真实用户 Prompts

```text
请在这个 Garden 里找到 wall_1 并删除它，然后确认 face 已经被移除。
先搜索当前模型里的 face，再把第一个 orphaned face 删掉，最后再查一次确认结果。
不要创建新对象，只删除已有 face 并告诉我删除的是哪个 identifier。
```

## 已验证最短路径

1. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "face"`
2. 读取第一个 orphaned face 的 `target`
3. `await call_tool(remove_honeybee_face)`，将上一步 `target` 传入 `target`
4. `await call_tool(search_honeybee_model_objects)` 再次确认

## 已验证最小参数形态

```json
{
  "name": "remove_honeybee_face",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "face",
      "object_identifier": "<face identifier>",
      "parent": {}
    }
  }
}
```

## 成功判据

- `remove_honeybee_face` 返回 `summary_view.removed_count == 1`
- `summary_view.removed_identifier` 与目标 face 一致
- 持久化文件仍是原登记模型路径（例如 `models/honeybee/<model>.hbjson`）
- 再次 `search_honeybee_model_objects(_object_type_="face")` 返回 `count == 0`（或不包含该 identifier）

## 高价值失败模式与避坑说明

- `_target.object_type` 不是 `face` 会直接失败
- 当前不支持删除 room-hosted face；如果 `target.parent.room_identifier` 存在，工具会直接拒绝，因为这会破坏 Room 的 closed solid
- `target` 最好来自当前模型的真实搜索结果；手写 target 容易删错模型或删错对象
