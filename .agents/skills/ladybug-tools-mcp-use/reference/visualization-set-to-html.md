# VisualizationSet 导出为 HTML Artifact

## 用户意图

- 把已有 `VisualizationSet` 导出成交互式 HTML 文件
- 将 HTML artifact 保存到 Garden 的 `artifacts/visualization/html/`
- 让后续 `list_garden_artifacts` 能找到该可视化产物

## 模拟真实用户 Prompts

```text
把上一步生成的 VisualizationSet 导出成 HTML artifact。
请生成 Honeybee model 的 VisualizationSet，并导出 HTML 文件。
把这个可视化结果保存到 Garden artifact 里，文件名用 agent_html_preview。
```

## 已验证推荐路径

新 Agent 路径优先传 `visualization_set_target`，不要搬运完整 `VisualizationSet` dict：

1. 上游 visualize 工具使用 `garden_root` 并设置 `return_visualization_set=false`
2. 从上游结果读取 `target` 或 `visualization_set_target`，并在同一个 `execute` block 内保留这个变量
3. `call_tool name=visualization_set_to_html`
4. 把 `visualization_set_target` 传入，而不是完整 `visualization_set`
5. 读取返回的顶层 `artifact_name`、`artifact_path`、`artifact_type`，或 `artifact_receipt.artifact_path`

Deterministic-pass/candidate for multi-format export:

1. 创建或读取一个 compact `visualization_set_target`
2. 对同一个 `visualization_set_target` 分别调用 HTML、SVG、vtk.js exporter
3. 每个 exporter 成功后直接使用返回的 `artifact_name/artifact_path/artifact_type`
4. 不要再为了确认 artifact 去反复 `list_garden_artifacts`，除非 exporter 返回 `exists=false` 或用户明确要求清单

Deterministic-pass/candidate for object previews:

- `honeybee_room_to_visualization_set` and `honeybee_face_to_visualization_set` now accept `return_visualization_set=false` and return compact `visualization_set_target`.
- Exporters can also load a Garden `visualization_set_json` artifact record or a Garden-relative artifact path shape such as `{"artifact": "artifacts/visualization_sets/name.json"}` when recovering from `list_garden_artifacts`.
- This recovery shape is deterministic-pass only. The broad MiMo `visualization_set_export_matrix` Agent scenario still failed final-output closure after doing the required exports, so do not promote it to a recommended Agent path until a focused rerun passes.

旧 payload/debug 路径仍可传完整 `VisualizationSet` dict：

1. `search query='export visualization set to html artifact'`
2. `call_tool name=honeybee_model_to_visualization_set`
3. 从第 2 步结果中取完整 `visualization_set` 对象
4. `call_tool name=visualization_set_to_html`
5. 把第 2 步的完整 `visualization_set` 对象作为 `_visualization_set` 传入
6. 读取返回的 `artifact_receipt.artifact_path`

## 成功示例输入

target 路径：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "color_by_": "type",
  "name_": "agent_html_preview",
  "return_visualization_set": false
}
```

target 路径第 2 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "visualization_set_target": {
    "target_type": "visualization_set",
    "domain": "visualize",
    "identifier": "agent_monthly_schedule_chart",
    "path": "artifacts/visualization_sets/agent_monthly_schedule_chart.json"
  },
  "name": "agent_monthly_schedule_chart"
}
```

旧 payload 路径第 2 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "name_": "agent_html_preview",
  "wireframe_only_": true
}
```

第 4 步：

```json
{
  "garden_root": "tests/.artifacts/agent_integration/.../garden",
  "_visualization_set": "{use the complete visualization_set object returned by step 2}",
  "name_": "agent_html_preview"
}
```

## 成功输出形态

- `artifact_receipt.status` 为 `persisted`
- `artifact_receipt.artifact_type` 为 `visualization_html`
- `artifact_receipt.artifact_path` 指向 `artifacts/visualization/html/*.html`
- 顶层 `artifact_name` / `artifact_path` / `artifact_type` 与 `summary_view` 中的同名字段一致
- `summary_view.exists` 为 `true`

## 避坑说明

- 优先使用 `visualization_set_target`；完整 `VisualizationSet` dict 可能很大，低智能 Agent 容易压坏其中的 nested geometry。
- 多轮 Agent 场景要在设置阶段保留 compact `visualization_set_target`，下一轮直接使用；如果下一轮丢失 target，再通过 artifact/path 恢复，不要重建模型和 VisualizationSet。
- 最小 agent smoke 推荐先用 `wireframe_only_ = true`，这样中间对象更小。
- `output_subdir_` 必须是 Garden 内部相对目录，不能写出 Garden。
- 这个工具会写 artifact 和更新 `garden.json.artifacts`，不是 read-only。
- 2026-04-28 live Garden Round 20 retry verified the target-first Honeybee model preview path on the Grasshopper-followed Garden. The failed full/context-drift run cost `246,675` tokens; after `honeybee_model_to_visualization_set(return_visualization_set=false)` returned a compact target, retry closed at `9,908` tokens and created `artifacts/visualization/html/round_20_live_model_preview.html`.
- 2026-04-30 supervised external matrix task 12 verified the Honeybee model VisualizationSet target handoff plus both HTML and SVG exports in the stable Honeybee suite. The run closed `ok` but repeated `honeybee_model_to_visualization_set`, `visualization_set_to_html`, and `visualization_set_to_svg`; future Agents should create one VisualizationSet target and export each format once.
