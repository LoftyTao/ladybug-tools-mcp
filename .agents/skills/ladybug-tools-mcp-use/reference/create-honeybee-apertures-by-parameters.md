# 参数化创建 Honeybee Aperture

## 用户意图

- 用户说“给这面墙开窗”“按窗墙比开窗”“按宽高开一个窗”
- 已经有 Garden 和 Honeybee base model
- 需要先定位 `Face` host target，再创建 aperture/window

## 已验证推荐路径

### By Ratio

1. `search("open windows on a wall face by ratio")`
2. `await call_tool(search_honeybee_model_objects)`，`object_type = "face"`
3. 读取目标墙面的 typed target
4. 如是恢复/重试路径，先 `await call_tool(search_honeybee_model_objects)`，传入 `object_type = "aperture"` 和 `children_scope = "<face target>"`，确认该 face 下没有已创建 aperture
5. `await call_tool(create_honeybee_apertures_by_parameters)`，传入 `host_target + generation_mode = "by_ratio" + ratio`
6. `await call_tool(search_honeybee_model_objects)`，传入 `object_type = "aperture"` 和 `children_scope = "<face target>"`，确认 aperture 已存在

这条路径已经通过 deterministic tests 和 OpenAI Agents 自然语言验证。验证 prompt 使用“在 south_wall 这面墙上按 30% 窗墙比开窗”。

## 已验证最小参数形态

```json
{
  "name": "create_honeybee_apertures_by_parameters",
  "arguments": {
    "garden_root": "<exact garden root>",
    "host_target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "face",
      "object_identifier": "south_wall",
      "parent": {}
    },
    "generation_mode": "by_ratio",
    "ratio": 0.3
  }
}
```

## Deterministic 覆盖但尚未作为自然语言推荐主路径

`by_width_height` 已有 deterministic tests，适合“给这面墙开一个 1.2m x 1.5m 的窗”这类精确参数输入。

```json
{
  "name": "create_honeybee_apertures_by_parameters",
  "arguments": {
    "garden_root": "<exact garden root>",
    "host_target": "<face typed target>",
    "generation_mode": "by_width_height",
    "aperture_width": 1.2,
    "aperture_height": 1.5,
    "sill_height": 0.9
  }
}
```

`generation_mode` 时会被归一化；自然 prompt 中附带的 `count` 会被接受为
意图提示，避免因 SDK ratio 模式暂不消费 count 而直接触发 schema 重试。
2026-04-26 staged MiniMax validation 又观察到 `generation_mode =
"by_count_and_ratio"`；服务会将其归一化为 `by_ratio`，并从
`parameters.window_ratio` 读取 ratio。推荐调用仍是上面的
`generation_mode = "by_ratio"` + 顶层 `ratio`。
2026-04-26 token-sink 修复后，服务还会接受低智能 Agent 已实际生成的
`identifier_prefix`、`aperture_name_prefix`、`name_prefix` 来命名 ratio
模式生成的窗，并可把 `{type:"Face", identifier:"Front", host:{type:"Room",
identifier:"open_office"}}` 这类自然 face 引用解析成 typed target。推荐路径
2026-04-27 disclosure 推广：工具描述和 tags 已补充官方 Primer / 论坛常见
说法，包括 `Apertures by Ratio`、`window-to-wall ratio`、`WWR`、`glazing
ratio`、`rectangular windows`。同轮 deterministic search probes 显示这些
自然查询会优先命中 `create_honeybee_apertures_by_parameters`；这属于
`deterministic-pass`，不是新的 real-Agent 推荐路径证据。
Current calls must search the host wall face first, pass `matches[i].target`,
and use `aperture_width` / `aperture_height` or `ratio`. Do not pass room
targets, identifier-only dictionaries, `face_name`, or `host_face_target`.

## Mixed Explicit + Parameterized Window Path

2026-04-28 live Garden evolution Round 05 verified a compact mixed path on an
existing Grasshopper-followed model:

1. `search_honeybee_model_objects(object_type="room")`
2. Build `room_targets = {match["identifier"]: match["target"] ...}`
3. For each room, search `object_type="face"` with `children_scope=<room target>`,
   `face_type="Wall"`, and `boundary_condition="Outdoors"`
4. Use `create_honeybee_aperture` for non-rectangular explicit `Face3D` geometry
5. Use `create_honeybee_apertures_by_parameters` for standard narrow/tall or
   rectangular windows
6. `validate_honeybee_model`

The verified Round 05 shape created `entry_lobby_trapezoid_window` through
explicit `Face3D` and `north_office_tall_side_window` through `by_width_height`
in one `execute`, with `6,353` total tokens and no validation errors.

## 成功判据

- `search` 能用 `window / aperture / wall / face / ratio / width height` 命中新工具
- `create_honeybee_apertures_by_parameters.summary_view.created_count >= 1`
- 返回 `targets[]`，每个 target 都是 `object_type == "aperture"`
- `persistence_receipt.status == "persisted"`
- 后续 `search_honeybee_model_objects(object_type="aperture", children_scope="<face target>")` 能找到新 aperture

## 高价值失败模式与避坑说明

- `host_target` 必须是 `face` typed target，不能直接传 room/model target
- 如果已经传错成 room target，服务会尝试按 `wall_index` / `wall_indices`
- `by_ratio` 必须提供 `ratio`，且范围是 0 到 1 之间
- `by_width_height` 必须同时提供 `aperture_width` 和 `aperture_height`
- 如果用户只说“给房间开窗”，先搜索并缩小到具体 wall/face，再调用本工具
- 如果这是失败恢复或第二段 `execute`，先用 `children_scope` 查询 host face 下是否已经有 aperture；不要对已开窗的同一 face 直接重复调用 ratio 创建，否则可能触发 aperture overlap 校验错误。
