# Honeybee Room / Face 可视化为 VisualizationSet

## 用户意图

- 只预览某个 Room 或 Face，而不是整个 model
- 用 `search_honeybee_model_objects` 返回的 typed target 精确定位对象
- 生成可继续交给 `compose_visualization_sets`、HTML 或 SVG 导出的 `VisualizationSet`

## 模拟真实用户 Prompts

```text
只把这个房间转成 VisualizationSet。
找一个 Honeybee face，生成它的 wireframe 可视化。
预览第一面墙，不要导出文件。
```

## 已验证推荐路径

1. `search_tools query='visualize honeybee room as visualization set'` 或 `search_tools query='visualize honeybee face as visualization set'`
2. `call_tool name=search_honeybee_model_objects`
3. Room 使用 `_object_type_ = "room"`，Face 使用 `_object_type_ = "face"`
4. 从搜索结果中取 `matches[0].target`
5. `call_tool name=honeybee_room_to_visualization_set` 或 `call_tool name=honeybee_face_to_visualization_set`
6. 把完整 typed target 作为 `target` 传入
7. 读取返回的 `summary_view.object_target`、`summary_view.geometry_count` 和 `visualization_set`

## 成功示例输入

搜索 Room：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "object_type": "room"
}
```

Room 可视化：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "target": "{use the complete room target returned by search_honeybee_model_objects}",
  "name_": "room_preview"
}
```

Face wireframe 可视化：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "target": "{use the complete face target returned by search_honeybee_model_objects}",
  "wireframe_only_": true,
  "name_": "face_wireframe"
}
```

## 成功输出形态

- `visualization_set.type` 为 `VisualizationSet`
- `summary_view.object_type` 为 `room` 或 `face`
- `summary_view.object_target` 保留输入 typed target
- `summary_view.geometry_count` 大于 0
- `wireframe_only_ = true` 时通常只返回 `Wireframe` 图层

## 避坑说明

- 不要手写对象 selector；先用 `search_honeybee_model_objects` 拿 typed target。
- `target` 必须是完整 typed target，不是对象 identifier 字符串。
- 这是只读路径，不会修改 Garden base model。
- Room / Face SDK 入口不直接支持 `color_by=None`；MCP 中 `color_by_ = "none"` 会落到 wireframe-only 语义。
