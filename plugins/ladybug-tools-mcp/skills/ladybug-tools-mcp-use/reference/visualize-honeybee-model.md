# Honeybee Model 可视化为 VisualizationSet

## 用户意图

- 预览 Garden base model 或指定 Honeybee model
- 生成可继续交给 HTML / SVG 导出工具使用的 `VisualizationSet`
- 在编辑、删除或验证前做只读视觉确认

## 模拟真实用户 Prompts

```text
把这个 Garden 的 base model 转成 VisualizationSet，先不要导出 HTML。
请预览这个 Honeybee model，返回 VisualizationSet 摘要。
用可视化工具生成模型预览，并告诉我 geometry count。
```

## 已验证推荐路径

Agent 推荐 target-first 路径：

1. `search_tools query='visualize honeybee model as visualization set'`
2. `call_tool name=honeybee_model_to_visualization_set`
3. 传入 `garden_root`
4. 如需自定义输出名，传 `name_`
5. 设置 `return_visualization_set=false`
6. 读取返回中的 `summary_view.geometry_count`、`summary_view.geometry_identifiers` 和 `visualization_set_target`

人工检查或 debug 路径仍可保持默认 `return_visualization_set=true`，此时返回完整 `visualization_set` dict。

## 成功示例输入

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "name_": "agent_preview",
  "return_visualization_set": false
}
```

## 成功输出形态

- `target` / `visualization_set_target` 为 `visualization_set` typed target
- `summary_view.model_target.model_identifier` 指向当前 base model
- `summary_view.geometry_count` 大于 0
- `summary_view.body_returned` 为 `false`
- 对 debug/payload 路径，完整 `visualization_set.type` 为 `VisualizationSet`

## 避坑说明

- `return_visualization_set=false` 会写入 Garden artifact 中的 VisualizationSet JSON；不会修改 Garden base model。
- 默认不生成 HTML 或 SVG 文件；导出 artifact 应交给后续 `Visualization Set To HTML / SVG` 路径。
- `color_by_ = "none"` 在模型级入口会转成 SDK 的 `None` 语义。
- 目前模型级入口支持的 `color_by_` 包括 `type`、`boundary_condition` 和 `none`；不要写 `face_type`。
- `use_mesh_` 默认是 `false`，优先保留 `DisplayFace3D` 语义。
- 2026-04-28 live Garden Round 20 retry verified `honeybee_model_to_visualization_set(return_visualization_set=false, color_by_="type") -> visualization_set_to_html(visualization_set_target=...)`; retry closed at `9,908` tokens and wrote `artifacts/visualization/html/round_20_live_model_preview.html`.
