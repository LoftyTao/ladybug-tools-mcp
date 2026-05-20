# 编辑 Honeybee Face / Room（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，先搜索已有 `Face` 或 `Room`，再原位编辑
- 这轮优先关注自然语言对象发现是否能收敛，而不是把所有 edit 能力都写成稳定主路径

## 当前证据分级

### 已验证内容

这轮自然语言测试已经验证了以下事实：

- Agent 会先尝试 `search`
- 后续会把 `room / wall / face / boundary` 这些口语收敛到 `search_honeybee_model_objects`
- 对于 `Face` 边界条件修改，测试已经覆盖到 `search -> edit -> confirm` 这条链路的目标形态

2026-04-25 的 MCP deterministic 交叉测试还验证了：

- 从已有 HBJSON 模型出发，先 `search_honeybee_model_objects(_object_type_="face")` 获取 face typed target。
- 调用 `edit_honeybee_face` 更新 `display_name_ / user_data_ / modifier_`。
- 再搜索 room target，调用 `edit_honeybee_room` 更新 `story_ / zone_`。
- 与 `remove_honeybee_aperture`、`create_honeybee_shade`、`validate_honeybee_model` 串联后仍能持久化并通过校验。

2026-04-25 的后续 MCP deterministic 交叉测试还验证了低 token 属性复用链路：

- 先用 `create_opaque_material(garden_root_, return_object_dict_=false)` 保存 material target。
- 再用 `create_opaque_construction(_materials=[material.target], garden_root_, return_object_dict_=false)` 保存 construction target。
- 最后将 `construction.target` 直接传给 `edit_honeybee_face.construction_`，持久化后的 face energy construction identifier 与目标一致。

2026-04-26 的 MiniMax Code Mode smoke 还验证了 Room 级 energy 属性的低 token 链路：

- `edit_honeybee_room.program_type_` 可以直接传 Honeybee Energy standards library identifier，例如 `1980_2004::SmallOffice::OpenOffice`。
- `edit_honeybee_room.construction_set_` 可以传 Garden Properties Library `construction_set` target。
- 该路径在自然提示的 create/edit 小型 workflow 中成功写回房间，不需要让 Agent 搬运完整 ProgramType 或 ConstructionSet dict。

### 候选/未稳定内容

以下内容当前不能写成稳定推荐主路径：

- `edit_honeybee_face` 的自然语言成功写回
- room 级 `hvac / modifier_set` 自然语言修改

原因是当前自然语言 face 编辑测试允许以合理失败结束；Room 编辑已有 energy 属性写回证据，但 hvac / modifier_set 等更宽属性仍需要独立 Agent 验证。

## 候选自然语言路径

### Edit Honeybee Face Boundary Condition

当前测试想要验证的目标路径是：

1. `search("edit honeybee face boundary condition in garden model")`
2. `await call_tool(search_honeybee_model_objects)`，收敛到目标 `face`
3. `await call_tool(edit_honeybee_face)`，传入 `_target + boundary_condition_`
4. 再做结果确认

已观察到的真实口语示例：

```text
把这个模型里 Tiny_House_Office 房间右侧墙的边界条件改成 Ground，并确认已经生效。
```

### Edit Honeybee Room

`edit_honeybee_room` 当前仅保留为候选入口说明，不写成已验证自然语言主路径。

Room target 交接必须保持单一公开参数名：

- 先调用 `search_honeybee_model_objects(object_type="room")`，并把选中的 `matches[i].target` 传给 `edit_honeybee_room` 的 `target`。
- 如果上游刚创建房间，也可以把 `create_honeybee_room.target` 传给 `edit_honeybee_room.target`。
- 参数名必须是 parameter named `target`，not `room_target`。
- `target` 值必须是 room typed target dict，not a room identifier。
- 不要把完整搜索结果、`matches[i]` 整个对象、或 full tool response 作为 room edit target；not the full search response。

## 候选最小参数形态

### Edit Honeybee Face

```json
{
  "name": "edit_honeybee_face",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "face",
      "object_identifier": "Tiny_House_Office_Right",
      "parent": {}
    },
    "boundary_condition_": {
      "type": "Ground"
    },
    "construction": "<create_opaque_construction.target>"
  }
}
```

### Edit Honeybee Room

Room energy 属性写回的最小形态：

```json
{
  "name": "edit_honeybee_room",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "room",
      "object_identifier": "room_1",
      "parent": {}
    },
    "program_type": "1980_2004::SmallOffice::OpenOffice",
    "construction_set": "<create_construction_set.target>"
  }
}
```

## 已观察到的成功判据与失败模式

### 候选成功判据

如果 face 编辑自然语言路径成功，当前应至少满足：

- 工具调用里出现 `search`
- 后续出现 `search_honeybee_model_objects`
- query 里出现 `boundary`、`wall` 或 `face`
- 持久化后的目标 face 边界条件为 `Ground`

### 已观察失败模式

- `search_honeybee_model_objects` 在自然语言链路里未被正常找到
- 因输入要求未满足而报出 `garden_root` 相关错误
- Agent 先走了不推荐的读取路径，导致对象发现不稳定

## 避坑说明

- 当前如果任务是自然语言改墙，先把它视为“对象发现稳定性验证”，不要把 `edit_honeybee_face` 写成已经稳定可复用的推荐主路径
- `target` 仍然优先来自真实搜索结果，不要手写 target
- 对 `construction`、Radiance `modifier_ / modifier_blk_` 等对象级属性，优先使用 Garden Properties Library target；不要让 Agent 在多步流程中搬运完整 material/construction/modifier dict
- `edit_honeybee_room` 的 `program_type` / `construction_set` 可走 standards identifier 或 Garden target；更复杂的 `hvac_ / modifier_set_` 自然语言路径应等待独立 Agent 验证后再升级
- deterministic MCP 交叉测试已经覆盖 `search -> edit face/room -> validate`，但自然语言 Agent 仍需要先证明能稳定从用户口语收敛到正确 typed target
