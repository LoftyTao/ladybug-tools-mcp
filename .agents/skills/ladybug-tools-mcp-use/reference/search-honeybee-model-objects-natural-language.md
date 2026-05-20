# Honeybee 自然语言对象发现与搜索收敛

## 适用范围

- 用户用口语说 `模型 / 房间 / 墙 / 窗`
- 需要先把模糊意图收敛成 `room / face / aperture`
- 后续还要继续做 `create / edit / remove`

## 已验证推荐路径

当前自然语言验证里，稳定出现的主链是：

1. 先 `search(...)`
2. 再 `await call_tool(search_honeybee_model_objects)`
3. 从返回结果里读取 typed target
4. 把 target 继续传给后续 `create / remove / edit` 或用于二次确认

关键接力规则：

- 搜索结果返回的是 result object，其中对象 target 在 `matches[i].target`。
- 如果搜索结果只有一个 match，服务也会返回顶层 `target`，可以直接用于下游
  `target` / `host_target`。推荐写法仍是显式检查 `summary_view.count == 1`
  后使用 `result["target"]` 或 `matches[0]["target"]`。
- 下游 `target` / `host_target` 只传 `matches[i].target` 这个嵌套 dict。
- `search_honeybee_model_objects` accepts `object_type` as the canonical field.
- `search_honeybee_model_objects` 是唯一正式 Honeybee 对象搜索工具。不要使用
  `search_honeybee_rooms`、`search_honeybee_apertures`、`search_honeybee_doors`
  这类拆分工具名；它们不是公开 MCP 工具。
- 如果已经知道精确 Honeybee 对象名，用 `identifier`，例如
  `identifier = "office_west_Front"`。不要把房间名当作 face identifier；
  房间下的 face 需要先找 room target，再用 `children_scope` 或明确 face 名继续收敛。
- 如果已经知道 parent face identifier，可以用 `face_identifier` 过滤
  apertures / doors / shades；当 `object_type="face"` 时，`face_identifier`
  会过滤 face 自身 identifier。这比全模型列出后手写 parent 过滤更稳。
- room、face、aperture、door 搜索结果带有 `child_counts`。在决定是否要再搜
  aperture/shade 或是否要重试创建前，先看这个 compact count；不要为了数对象反复做全模型搜索。
- face 搜索结果带有 `normal` dict 和 `normal_vector` list。低智能 Agent 如果要
  用索引方式判断朝向，应读 `normal_vector[1]`，不要把 `normal` dict 当 list。
- To recover from partial writes, pass `children_scope` with a room, face, aperture, or door typed target. This returns only child objects under that host and avoids hand-filtering parent identifiers in Agent code.
- `children_scope` 传 typed target。不要传裸字符串、boolean、`host_target`
  或旧的 shorthand 字段；这些不属于当前公开 contract。
- Code Mode 调用只传需要的 `garden_root/object_type/identifier/query/children_scope/limit`
  等正式字段；搜索结果保持紧凑，不返回完整对象正文。
- room 搜索结果会包含 compact `energy_properties`。做 Stage C / 能耗属性确认时，
  先读 `matches[i].energy_properties`，不要发明 `get_honeybee_room`，也不要要求
  搜索返回完整 room object body。
- 下游工具只接收显式 typed target。搜索后传 `matches[i].target`，不要传完整 response。
- 如果完整搜索结果里有多个 target，会失败并要求选择一个嵌套 target。

这个搜索收敛链已经在以下场景中被验证使用：

- `create_honeybee_room` 前的工具发现
- `remove_honeybee_aperture` 前的 room/face/aperture 收敛
- `create_honeybee_apertures_by_parameters` 前的 host wall/face 收敛
- staged Code Mode recovery before retrying aperture/shade creation on an existing face

## 已验证 discoverability 提示词

在当前测试证据里，以下口语能帮助 Agent 收敛到正确对象层级：

- `当前模型里用这个体块建一个房间`
- `这个模型里 Tiny_House_Office 房间前墙上的 Front_Aperture 不要了`
- `Tiny_House_Office 房间朝前的外墙开几个窗`
- `south_wall 这面墙上按 30% 窗墙比开窗`

已观察到更容易命中的搜索词包括：

- `room`
- `wall`
- `window`
- `boundary`
- `face`
- `aperture`
- `ratio`

## 已验证成功判据

- 工具调用里出现 `search`
- 后续调用里出现 `search_honeybee_model_objects`
- 搜索 query 或最终说明能反映出对象层级收敛，而不是一直停留在泛化的 `model`
- 搜索出来的 target 能继续传给写工具或用于说明当前缺口
- 对参数化开窗，搜索出来的 `face` target 能继续传给 `create_honeybee_apertures_by_parameters`

## 候选/未稳定路径

- `face` 边界条件编辑的自然语言收敛已经有测试覆盖，但结果仍存在不稳定性，不能写成稳定推荐主路径
- 只通过 `get_base_honeybee_model` 理解 `room / wall / window` 层级关系，不是这轮自然语言验证的推荐入口
- `by_width_height` 参数化开窗已有 deterministic 覆盖，但尚未作为自然语言推荐主路径沉淀

## 高价值失败模式与避坑说明

- 用户说 `模型` 时，不要机械理解成只能先操作 `Model object`
- 如果任务目标是删窗、改墙、给墙开窗，优先搜索对象而不是先拉完整模型正文
- 当前测试里已经明确要求避免把 `list_garden_models`、`get_base_honeybee_model` 当成对象发现主链
- 如果已经定位到 room 和 host wall，应优先检查是否可以调用 `create_honeybee_apertures_by_parameters`；旧的“缺少参数化 aperture create”失败模式只适用于该工具实现前的验证记录
- 2026-04-24 全量 agent integration 中，`Tiny_House_Office 房间朝前的外墙开几个窗` 曾只搜索到 `room`，随后最终回答停在“接下来要搜索 faces”的计划句，没有继续调用 `search_honeybee_model_objects(_object_type_="face")`。后续 prompt / disclosure 应明确：找到 room 只是中间状态，必须立刻继续搜索 face 或 aperture，不能把计划当成完成。

## Room 到 Face 的收敛提示

如果第一轮只找到 room，下一步应继续调用：

```json
{
  "name": "search_honeybee_model_objects",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "object_type": "face",
    "query": "Tiny_House_Office Front exterior wall"
  }
}
```

只有拿到 `face` typed target 后，才进入 `create_honeybee_apertures_by_parameters`、`edit_honeybee_face` 或 remove/edit subface 流程。

## Children Scope 恢复查询

当上一段 `execute` 已经成功创建了部分对象，而下一段需要继续或修复时，不要重复开窗或重复加 shade。先用当前 Garden 状态查询 host 下面已有对象：

```json
{
  "name": "search_honeybee_model_objects",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "object_type": "aperture",
    "children_scope": "<face typed target>"
  }
}
```

如果 `summary_view.count > 0`，继续使用 `matches[i].target`；只有确实没有现有 child 时，才再次调用 create 工具。

## Face Identifier 快速定位

当 Agent 已经知道 host face identifier，优先用 `face_identifier` 直接定位 host
或它的 children：

```python
right = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "face_identifier": "entry_lobby_Right",
})
window = await call_tool("create_honeybee_aperture", {
    "garden_root": garden_root,
    "identifier": "entry_lobby_replacement_window",
    "geometry": {"type": "Face3D", "boundary": [[12, -2.65, 0.85], [12, -0.55, 0.85], [12, -0.75, 2.35], [12, -2.35, 2.25]]},
    "host_target": right["target"],
})
```

显式几何创建工具的参数名是 `geometry` 和 `host_target`，不要写成
`Face3D` 或 `host_face`。
