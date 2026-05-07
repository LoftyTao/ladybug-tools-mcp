# Create / Edit 2D Legend Parameter

## 用户意图

- 创建可复用的 `LegendParameters` dict
- 调整 SVG 二维 legend 的标题、方向、位置、颜色和分段
- 把 legend 参数交给属性着色或后续结果型 VisualizationSet

## 模拟真实用户 Prompts

```text
创建一个水平的 2D legend 参数，标题是 Room Identifier。
把这个 legend 的位置改到 SVG 下方。
用 viridis 配色做一个属性可视化 legend。
```

## 已验证推荐路径

1. Code Mode 外层可先 `search query='create 2d legend parameter room attribute visualization svg'`
2. 在 `execute` 内 `await call_tool("create_2d_legend_parameter", {...})`
3. 从返回中取完整 `object_dict`
4. 如需修改，在 `execute` 内 `await call_tool("edit_2d_legend_parameter", {"legend_parameter": legend["object_dict"], ...})`
5. 把第 3 或第 4 步的完整 `object_dict` 作为后续属性可视化 spec 的 `legend_parameter`

## 成功示例输入

```json
{
  "title": "Room Identifier",
  "orientation": "horizontal",
  "position_2d": {
    "origin_x": "5%",
    "origin_y": "88%"
  },
  "color_set": "viridis"
}
```

## 成功输出形态

- `object_dict.type` 为 `LegendParameters`
- `object_dict.title` 为 legend 标题
- `summary_view.orientation` 为 `vertical` 或 `horizontal`
- `summary_view.origin_x` / `origin_y` 反映二维位置

## 避坑说明

- 后续工具需要完整 `object_dict`，不是 `summary_view`。
- `position_2d` 使用 `origin_x`、`origin_y`，值应是 Ladybug 支持的 `5%`、`20px` 这类字符串。
- `dimensions_2d` 支持 `segment_height`、`segment_width`、`text_height`。
- 当前只推荐已验证的普通 `LegendParameters`，不要把 categorized legend 当成主路径。
- 这是 payload-only 工具，不需要也不接受 `garden_root`。2026-04-30 Codex `ladybug_mcp_tester` Batch 4b 已验证：即使 Code Mode 上下文里已有 Garden，也不会再被自动注入 `garden_root`。
