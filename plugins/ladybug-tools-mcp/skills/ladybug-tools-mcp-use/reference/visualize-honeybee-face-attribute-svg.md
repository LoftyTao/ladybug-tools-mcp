# Honeybee Face 属性过滤可视化并导出 SVG

## 用户意图

- 用 Honeybee Face / Aperture / Shade 等 face-level 对象的稳定 SDK 属性生成属性着色 `VisualizationSet`
- 使用 `face_types` 和 `boundary_conditions` 缩小可视化对象范围
- 使用独立创建的 `2D Legend Parameter`
- 导出带二维 legend 的 SVG artifact

## 模拟真实用户 Prompts

```text
只把 Outdoors Wall 的 face identifier 做属性可视化并导出 SVG。
用 2D legend 显示外墙面的 identifier。
把 exterior wall face attribute visualization 保存成 SVG。
```

## 已验证推荐路径

1. `search_tools query='face attribute wall outdoors legend visualization svg'`
2. `call_tool name=create_2d_legend_parameter`
3. `call_tool name=honeybee_model_to_visualization_set`
4. 第 3 步传 `color_by_ = "none"`
5. 第 3 步传 `face_attributes_`
6. `face_attributes_[0].legend_parameter` 使用第 2 步返回的完整 `object_dict`
7. 需要限定对象范围时，传 `face_types` 和 `boundary_conditions`
8. `call_tool name=visualization_set_to_svg`
9. 第 8 步传第 3 步返回的完整 `visualization_set`
10. 读取 `artifact_receipt.artifact_path`

## 成功示例输入

第 2 步：

```json
{
  "title_": "Exterior Wall Identifier",
  "orientation_": "vertical",
  "position_2d_": {
    "origin_x": "4%",
    "origin_y": "12%"
  },
  "color_set_": "ecotect"
}
```

第 3 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "color_by_": "none",
  "face_attributes_": [
    {
      "name": "Exterior Wall Identifier",
      "attrs": ["identifier"],
      "legend_parameter": "{use the complete object_dict returned by create_2d_legend_parameter}",
      "face_types": ["Wall"],
      "boundary_conditions": ["Outdoors"]
    }
  ],
  "name_": "agent_face_attribute_svg"
}
```

第 8 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "_visualization_set": "{use the complete visualization_set object returned by step 3}",
  "name_": "agent_face_attribute_svg",
  "width_": 640,
  "height": 360,
  "render_2d_legend_": true
}
```

## 成功输出形态

- `honeybee_model_to_visualization_set.summary_view.face_attributes[0].name` 为属性图层名
- `summary_view.face_attributes[0].face_types` 保留 `["Wall"]`
- `summary_view.face_attributes[0].boundary_conditions` 保留 `["Outdoors"]`
- `visualization_set.geometry` 包含属性着色的 `AnalysisGeometry`
- SVG 文本中能看到 legend 标题

## 避坑说明

- 这是已验证的属性分类着色路径，不要描述成连续数值热图。
- `face_attributes_` 中的 `attrs` 应使用真实 Honeybee face-level 属性路径，例如 `identifier`。
- 当前已验证的过滤值包括 `face_types: ["Wall"]` 和 `boundary_conditions: ["Outdoors"]`。
- `legend_parameter` 必须是完整 `LegendParameters` dict。
- `color_by_ = "none"` 可避免同时输出默认模型类型着色，只保留属性图层和 wireframe。
