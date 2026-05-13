# Operate Honeybee Objects

本路径已通过本地 deterministic tests 验证。2026-04-25 披露加固后，
OpenAI Agents focused smoke 已通过 `create_honeybee_shades_by_parameters -> move_object -> relate_honeybee_model` 组合链路验证，其中 `move_object` 成功接收 Face typed target 和 Vector3D dict。

## 适用场景

- 对已有 `Model / Room / Face / Aperture / Door / Shade` 做几何变换。
- 用户说“移动这个 shade”“把这面墙绕 Z 轴旋转”“把模型镜像到另一侧”。

## 最短路径

1. `search_tools` 查询 `move honeybee object transform` 或具体操作。
2. 如还没有目标，先用 `search_honeybee_model_objects` 找 typed target；整体模型可用 `get_base_honeybee_model`。
3. 调用四个工具之一：
   - `move_object`
   - `rotate_object`
   - `scale_object`
   - `mirror_object`
4. 查看 `summary_view.postprocess`。局部 `Room / Face / Aperture / Door` 变换默认会尝试 `auto_relate_intersect_clone_single`；`Model` 整体变换默认只自动 validate；`Shade` 默认只提示 validate。

## 成功调用形态

```json
{
  "name": "move_object",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "target": {"target_type": "honeybee_object", "object_type": "face"},
    "vector": {"type": "Vector3D", "x": 0.5, "y": 0, "z": 0}
  }
}
```

```json
{
  "name": "mirror_object",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "target": {"target_type": "model", "domain": "honeybee"},
    "plane": {"type": "Plane", "n": [1, 0, 0], "o": [0, 0, 0]}
  }
}
```

## 注意事项

局部对象变换可能破坏 adjacency、父级边界、共面关系或 Radiance dynamic state geometry。自动 relate 在工作副本上运行；成功才保存关系结果，失败时保留原始变换写回并返回 warning。不要把 warning 当成工具调用失败，但要根据任务继续 `relate_honeybee_model` 或 `validate_honeybee_model`。

## 已观察 Agent 失败模式

- 2026-04-24 全量 agent integration 中，组合场景把 `create_honeybee_shades_by_parameters`、`move_object`、`relate_honeybee_model` 串在同一个 prompt 里时，低智能模型反复用 `arguments: null` 调 `move_object`。`move_object` 必须带 `garden_root`、`target` 和 `vector`；一旦参数缺失，应停止空参重试并回到上一条成功 search/create 返回的 typed target。
- 2026-04-25 focused 复测中，工具描述补充 required shape 后，同一组合场景没有重复调用 `move_object`。后续仍建议把更长的多写工具任务拆短。
- 2026-04-28 live Round 12 中，MiniMax 成功创建并变换三个 detached shades 后，
  因一次后续失败重放了 create/transform。服务层现在会拒绝重复 explicit identifier，
  但 Agent 仍可能继续尝试错误的 identifier-string target。恢复时应先 search typed
  target，再传给 `move_object` / `remove_honeybee_shade`。
