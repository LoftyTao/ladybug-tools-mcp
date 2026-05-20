# 删除 Honeybee Shade（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，删除一个已存在的 `Shade`
- 删除后立即确认模型里不再存在该 `Shade`
- 适用于 orphaned shade，以及挂在 `Room / Face / Aperture / Door` 上的 hosted shade

## 模拟真实用户 Prompts

```text
请在这个 Garden 里找到 shade_1 并删除它，然后确认 shade 已经被移除。
先搜索当前模型里的 shade，再把第一个 shade 删掉，最后再查一次确认结果。
不要创建新对象，只删除已有 shade 并告诉我删除的是哪个 identifier。
```

## 已验证最短路径

1. `search("search_honeybee_model_objects")`
2. `search("remove_honeybee_shade")`
3. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "shade"`
4. 读取第一个 match 的 `target`
5. `await call_tool(remove_honeybee_shade)`，将上一步 `target` 传入 `target`
6. `await call_tool(search_honeybee_model_objects)` 再次确认

## 已验证最小参数形态

```json
{
  "name": "remove_honeybee_shade",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "shade",
      "object_identifier": "<shade identifier>",
      "parent": {
        "face_identifier": "<host face identifier if hosted>"
      }
    }
  }
}
```

## 成功判据

- `remove_honeybee_shade` 返回 `summary_view.removed_count == 1`
- `summary_view.removed_identifier` 与目标 shade 一致
- 持久化文件仍是原登记模型路径（例如 `models/honeybee/<model>.hbjson`）
- 再次 `search_honeybee_model_objects(_object_type_="shade")` 返回 `count == 0`（或不包含该 identifier）

## 高价值失败模式与避坑说明

- `_target.object_type` 不是 `shade` 会直接失败；不要把 `room/face/aperture/door` target 误传给该工具
- `target` 最好来自当前模型的真实搜索结果；手写 target 容易出现 `model_identifier` 或 parent 路径不一致
- 对 hosted shade，不需要手动拆 `parent` 再定位宿主；直接把搜索结果中的完整 `target` 传给工具即可
- 删除前后都建议显式搜索一次，避免把“工具调用成功”误当成“目标对象已移除”
