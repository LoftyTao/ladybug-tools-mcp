# Honeybee Room 属性可视化并导出 SVG

## 用户意图

- 用 Honeybee Room 的稳定 SDK 属性生成属性着色 `VisualizationSet`
- 使用独立创建的 `2D Legend Parameter`
- 导出带二维 legend 的 SVG artifact

## 模拟真实用户 Prompts

```text
按 Room identifier 做属性着色并导出 SVG。
创建一个 2D legend，然后用它显示房间属性。
把房间属性可视化保存为 SVG artifact。
```

## 已验证推荐路径

1. `search_tools query='create 2d legend parameter room attribute visualization svg'`
2. `call_tool name=create_2d_legend_parameter`
3. `call_tool name=honeybee_model_to_visualization_set`
4. 第 3 步传 `color_by_ = "none"`
5. 第 3 步传 `room_attributes_`
6. `room_attributes_[0].legend_parameter` 使用第 2 步返回的完整 `object_dict`
7. `call_tool name=visualization_set_to_svg`
8. 第 7 步传第 3 步返回的完整 `visualization_set`
9. 读取 `artifact_receipt.artifact_path`

## 成功示例输入

第 2 步：

```json
{
  "title_": "Room Identifier",
  "orientation_": "horizontal",
  "position_2d_": {
    "origin_x": "5%",
    "origin_y": "88%"
  },
  "color_set_": "viridis"
}
```

第 3 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "color_by_": "none",
  "room_attributes_": [
    {
      "name": "Room Identifier",
      "attrs": ["identifier"],
      "legend_parameter": "{use the complete object_dict returned by create_2d_legend_parameter}"
    }
  ],
  "name_": "agent_attribute_svg"
}
```

第 7 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "_visualization_set": "{use the complete visualization_set object returned by step 3}",
  "name_": "agent_attribute_svg",
  "width_": 640,
  "height": 360,
  "render_2d_legend_": true
}
```

## 成功输出形态

- `honeybee_model_to_visualization_set.summary_view.room_attributes[0].name` 为属性图层名
- `visualization_set.geometry` 包含属性着色的 `AnalysisGeometry`
- SVG artifact 路径指向 `artifacts/visualization/svg/*.svg`
- SVG 文本中能看到 legend 标题

## 避坑说明

- 这是已验证的属性分类着色路径，不要描述成连续数值热图。
- `room_attributes_` 中的 `attrs` 应使用真实 Honeybee Room 属性路径，例如 `identifier`。
- `legend_parameter` 必须是完整 `LegendParameters` dict。
- `color_by_ = "none"` 可避免同时输出默认模型类型着色，只保留属性图层和 wireframe。
