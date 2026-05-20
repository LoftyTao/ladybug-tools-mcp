# Compose VisualizationSets

## 用户意图

- 把多个 Honeybee model / room / face 可视化结果拼成一个场景
- 在导出 HTML 或 SVG 前组合多个 `VisualizationSet`
- 处理多个输入里重复的 geometry identifier

## 模拟真实用户 Prompts

```text
把房间和一面墙的 VisualizationSet 合成一个。
组合上一步的两个可视化结果，然后导出。
把两个 wireframe 场景合并，重复图层名自动改名。
```

## 已验证推荐路径

1. 先用各类 `*to_visualization_set` 工具生成多个 compact `visualization_set_target`
2. Code Mode 外层可先 `search query='compose visualization sets'`
3. 在 `execute` 内 `await call_tool("compose_visualization_sets", {...})`
4. 传 `garden_root` 和 `visualization_set_targets`
5. 设置 `return_visualization_set=false`，让 compose 结果继续保存为 compact `visualization_set_target`
6. 如果可能存在重复图层，例如多个 wireframe 都叫 `Wireframe`，第一次就传 `conflict_strategy = "rename"`
7. 把返回的 `visualization_set_target` 交给 HTML / SVG / vtk.js 导出工具

## 成功示例输入

```json
{
  "garden_root": "<garden root>",
  "visualization_set_targets": [
    "<honeybee_model_to_visualization_set.visualization_set_target>",
    "<honeybee_room_to_visualization_set.visualization_set_target>"
  ],
  "name": "combined_scene",
  "conflict_strategy": "rename",
  "return_visualization_set": false
}
```

## 成功输出形态

- `visualization_set_target.target_type` 为 `visualization_set`
- `summary_view.input_count` 等于输入数量
- `summary_view.target_input_count` 等于通过 Garden reference 传入的数量
- `summary_view.geometry_count` 为组合后的图层数量
- `summary_view.renamed_geometry_ids` 记录被自动改名的重复图层
- `summary_view.body_returned=false` 表示没有把完整 VisualizationSet dict 搬回 Agent 上下文

## 避坑说明

- 优先传上游工具返回的完整 `visualization_set_target` dict，或 `list_garden_artifacts` 返回的 `visualization_set_json` artifact record。
- 不要手写只有 `path` 的半截引用；不要写 `type="visualization_set"`，正式字段是 `target_type="visualization_set"`。
- `visualization_sets` 仍可用于 debug / payload 模式，但 Agent 默认不要展开大对象。
- 默认 `conflict_strategy = "error"`，重复 geometry identifier 会失败。
- 多个 wireframe VisualizationSet 很容易都包含 `Wireframe` 图层；这类场景建议显式传 `conflict_strategy = "rename"`。
- `units` 省略时要求输入 units 一致；需要强制输出单位时再显式传 `units`。
- 不要把模型几何预览和 Energy/DataCollection 图表强行 compose 到同一个 VisualizationSet；如果 units 不一致，工具会拒绝。把几何场景和结果图分别导出，或只组合单位一致的 VisualizationSet。

## Evidence

- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 18 verified model/room/face VisualizationSets, 2D legend create/edit, `compose_visualization_sets(conflict_strategy="rename")`, HTML/SVG export, and `list_garden_artifacts` recovery. Duplicate `Wireframe` ids were renamed to `set_2_Wireframe` and `set_3_Wireframe`. A first attempt to combine model preview and result chart failed from unit mismatch; the successful path composed same-unit geometry previews and exported the result chart separately.
- 2026-05-17 deterministic MCP verification passed for `compose_visualization_sets(garden_root, visualization_set_targets, conflict_strategy="rename", return_visualization_set=false) -> visualization_set_to_html(visualization_set_target)`.
- 2026-05-17 focused MiMo broad reruns showed the new target-first compose path works functionally for HTML/SVG/vtk.js export, but final-output stream idle can still mark the Agent turn failed after artifacts are already written. Treat this as remaining harness/provider closure risk, not a compose service failure.
