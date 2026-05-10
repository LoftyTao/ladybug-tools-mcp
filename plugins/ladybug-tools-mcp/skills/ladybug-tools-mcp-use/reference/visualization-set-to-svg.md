# VisualizationSet 导出为 SVG Artifact

## 用户意图

- 把已有 `VisualizationSet` 导出成 SVG 文件
- 将 SVG artifact 保存到 Garden 的 `artifacts/visualization/svg/`
- 用二维投影结果做文档嵌入、图纸式预览或轻量交付

## 模拟真实用户 Prompts

```text
把这个 VisualizationSet 导出为 SVG。
生成房间和墙面的组合可视化，并保存成 SVG artifact。
用 Top view 导出一个 640 x 360 的 SVG。
```

## 已验证推荐路径

1. `search_tools query='export visualization set to svg artifact'`
2. 优先用 `honeybee_model_to_visualization_set`、
   `honeybee_room_to_visualization_set`、`honeybee_face_to_visualization_set`
   或 `compose_visualization_sets`，并设置 `return_visualization_set=false`
3. 从返回结果读取 `visualization_set_target`
4. `call_tool name=visualization_set_to_svg`
5. 传 `garden_root`、`visualization_set_target` 和可选 `name_`、`width_`、
   `height`、`view_`
6. 读取返回的 `artifact_receipt.artifact_path`

## 成功示例输入

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "visualization_set_target": "{use the target returned by honeybee_model_to_visualization_set}",
  "name_": "agent_room_face_svg",
  "width_": 640,
  "height": 360,
  "view_": "Top"
}
```

## 成功输出形态

- `artifact_receipt.status` 为 `persisted`
- `artifact_receipt.artifact_type` 为 `visualization_svg`
- `artifact_receipt.artifact_path` 指向 `artifacts/visualization/svg/*.svg`
- `summary_view.exists` 为 `true`
- `summary_view.view`、`summary_view.width`、`summary_view.height` 反映导出设置

## 避坑说明

- 不要把 `_visualization_set` 写成占位符、路径或摘要。Agent 路径优先传
  `visualization_set_target`，不要把完整 `VisualizationSet` 大对象搬进上下文。
- `view_` 第一阶段支持 `Top`、`Left`、`Right`、`Front`、`Back`、`NE`、`NW`、`SE`、`SW`。
- `output_subdir_` 必须是 Garden 内部相对目录，不能写出 Garden。
- 这个工具会写 artifact 和更新 `garden.json.artifacts`，不是 read-only。
- 不要发明通用 `create_honeybee_folder`、`save_honeybee_file` 之类文件工具。
  可视化导出工具会自己在 Garden 内写 artifact。

## 验证记录

- 2026-04-28 forum-fuzzy multitask Task 4：真实 MiniMax 在
  `D:\Desktop\Codex\gardens\test-garden` 上使用
  `honeybee_model_to_visualization_set(return_visualization_set=false)` 和
  `visualization_set_to_svg`，最终写入
  `artifacts/visualization/svg/visualization_set.svg`。路径功能闭合，但仍观察到
  invented folder/file tool 和重复搜索，后续 prompt 应强调 target-first 导出。
