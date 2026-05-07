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

1. 先用各类 `*to_visualization_set` 工具生成多个 `visualization_set`
2. Code Mode 外层可先 `search query='compose visualization sets'`
3. 在 `execute` 内 `await call_tool("compose_visualization_sets", {...})`
4. 把完整 `VisualizationSet` dict 列表作为 `visualization_sets` 传入
5. 如果可能存在重复图层，例如多个 wireframe 都叫 `Wireframe`，传 `conflict_strategy = "rename"`
6. 读取返回的 `visualization_set`，继续交给 HTML / SVG 导出工具

## 成功示例输入

```json
{
  "visualization_sets": [
    "{use the complete first visualization_set object}",
    "{use the complete second visualization_set object}"
  ],
  "name": "combined_scene",
  "conflict_strategy": "rename"
}
```

## 成功输出形态

- `visualization_set.type` 为 `VisualizationSet`
- `summary_view.input_count` 等于输入数量
- `summary_view.geometry_count` 为组合后的图层数量
- `summary_view.renamed_geometry_ids` 记录被自动改名的重复图层

## 避坑说明

- 不要把 `visualization_sets` 写成文件路径、摘要、artifact receipt 或外层工具返回包装；必须传完整内层 `visualization_set` dict。
- 默认 `conflict_strategy = "error"`，重复 geometry identifier 会失败。
- 多个 wireframe VisualizationSet 很容易都包含 `Wireframe` 图层；这类场景建议显式传 `conflict_strategy = "rename"`。
- `units` 省略时要求输入 units 一致；需要强制输出单位时再显式传 `units`。
- 不要把模型几何预览和 Energy/DataCollection 图表强行 compose 到同一个 VisualizationSet；如果 units 不一致，工具会拒绝。把几何场景和结果图分别导出，或只组合单位一致的 VisualizationSet。
- 这是 payload-only 工具，不需要也不接受 `garden_root`。2026-04-30 Codex `ladybug_mcp_tester` Batch 4b 已验证：Code Mode 已知 Garden 后，传两个内层 `visualization_set` 并设置 `conflict_strategy="rename"` 可以成功组合，不再触发 `garden_root unexpected keyword argument`。

## Evidence

- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 18 verified model/room/face VisualizationSets, 2D legend create/edit, `compose_visualization_sets(conflict_strategy="rename")`, HTML/SVG export, and `list_garden_artifacts` recovery. Duplicate `Wireframe` ids were renamed to `set_2_Wireframe` and `set_3_Wireframe`. A first attempt to combine model preview and result chart failed from unit mismatch; the successful path composed same-unit geometry previews and exported the result chart separately.
