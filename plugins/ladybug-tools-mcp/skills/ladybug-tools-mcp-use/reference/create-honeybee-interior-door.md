# 创建 Honeybee Interior Door

## 适用场景

- 用户要求在两个相邻房间之间的内墙上添加门。
- 模型中已有 `Surface` 邻接墙面，或者先通过 `relate_honeybee_model` 建立相邻关系。
- Agent 需要继续从现有 Garden 状态建模，而不是手写完整 HBJSON。

## 已验证最短路径

1. `execute` 中设置明确的 `garden_root`。
2. `search_honeybee_model_objects(object_type="room")` 找到两个房间的 typed target。
3. 对其中一个房间调用 `search_honeybee_model_objects(object_type="face", children_scope=<room target>, face_type="Wall", boundary_condition="Surface")`。
4. 把返回的 `matches[0].target` 作为 `create_honeybee_door.host_target`。
5. `create_honeybee_door` 会在相邻墙面上自动创建成对 Door，并恢复 Face/Door 的 `Surface` adjacency。
6. 调用 `validate_honeybee_model` 确认模型有效。

## Code Mode 示例

```python
garden_root = "tests/.artifacts/.../garden"
rooms = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
})
room_targets = {match["identifier"]: match["target"] for match in rooms["matches"]}
faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["room_a"],
    "face_type": "Wall",
    "boundary_condition": "Surface",
})
door = await call_tool("create_honeybee_door", {
    "garden_root": garden_root,
    "identifier": "shared_interior_door",
    "geometry": {
        "type": "Face3D",
        "boundary": [[4, 1.4, 0.05], [4, 2.3, 0.05], [4, 2.3, 2.15], [4, 1.4, 2.15]],
    },
    "host_target": faces["matches"][0]["target"],
})
validation = await call_tool("validate_honeybee_model", {
    "garden_root": garden_root,
})
return {"created_targets": door["targets"], "is_valid": validation["is_valid"]}
```

## 成功判据

- `create_honeybee_door.summary_view.is_interior_pair == true`。
- 返回 `targets` 包含两侧 Door target。
- 两侧 Door 的 `boundary_condition.name == "Surface"`。
- `validate_honeybee_model.is_valid == true`。

## 多内门批量路径

当走廊或门厅需要连接多个相邻房间时，先在走廊房间范围内搜索 `Surface` wall，再按 `identifier` 或 `normal_vector` 选 host target，逐个调用 `create_honeybee_door`。不要把多个写入并行发出。

```python
rooms = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
})
room_targets = {match["identifier"]: match["target"] for match in rooms["matches"]}
faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["east_corridor"],
    "face_type": "Wall",
    "boundary_condition": "Surface",
})
face_targets = {match["identifier"]: match["target"] for match in faces["matches"]}
for identifier, face_identifier, geometry in door_specs:
    await call_tool("create_honeybee_door", {
        "garden_root": garden_root,
        "identifier": identifier,
        "geometry": geometry,
        "host_target": face_targets[face_identifier],
    })
```

## 普通外墙门短路径

当用户只要“普通 900mm 门”“入口门”“补一扇门”，不要先手算 `Face3D`
边界。先搜索宿主外墙，再省略 `geometry`，传 `door_width`、`door_height`
和可选 `sill_height`：

```python
right = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "face_identifier": "MeetingRoom_Right",
})
door = await call_tool("create_honeybee_door", {
    "garden_root": garden_root,
    "identifier": "MeetingRoom_Right_Door",
    "host_target": right["target"],
    "door_width": 0.9,
    "door_height": 2.1,
    "sill_height": 0.0,
})
validation = await call_tool("validate_honeybee_model", {
    "garden_root": garden_root,
})
```

服务会把 `sill_height=0.0` 转成 Honeybee 可接受的最小内缩，并尽量避开
宿主墙上已有 apertures / doors。创建后仍要搜索 host face 的 children 或
搜索 doors 确认 persisted Garden state。

## 边界与避坑

- 不要在 `Surface` 内墙上先手动清 adjacency 再只创建单边 Door；这会留下不完整关系。
- 只在一侧 `Surface` host face 调用一次 `create_honeybee_door`。服务会自动创建相邻侧 Door；不要再对相邻 Face 用同一位置重复创建第二扇门，否则会触发重叠错误。
- 对普通外墙或 orphaned Face，`create_honeybee_door` 仍只创建单个 Door。
- 如果找不到 `Surface` 内墙，先运行 `relate_honeybee_model` 或重新搜索正确房间/墙面。
- `search_honeybee_model_objects(object_type="face")` 的 face match 已包含 compact `geometry.boundary` / `vertices` / `normal_vector`。需要定位门时先读这些边界，不要发明 `get_honeybee_face_geometry` 或绕到 visualization 工具。
- `geometry` 仍必须是位于宿主 Face 内部的合法 `Face3D`；门底边不要正好压在父墙底边，给一个很小正值 sill，例如 `z=0.05` 或 `z=0.15`。
- `create_honeybee_door` 支持 deterministic-pass 的 `boundary=[[x,y,z], ...]` 顶层恢复别名，并会忽略误传的 `is_operable`；推荐路径仍是 `geometry={"type":"Face3D","boundary":[...]}`。

## 验证记录

- 2026-04-28 Agent smoke：`test_agent_can_add_interior_door_between_adjacent_rooms`，一条 `execute`，5 个 inner MCP calls，`5,066` total tokens。
- 2026-04-28 live Garden repair：`tests/.artifacts/agent_integration/live_existing_model_interior_door_repair`，一条 `execute`，5 个 inner MCP calls，`5,180` total tokens；`gardens/test-garden` 的 `meeting_room_Left` 和 `agent_visible_room_Right` 形成一对 Surface Door。
- 2026-04-28 live Garden evolution Round 03：一条 `execute`，5 个 inner MCP calls，`6,665` total tokens；一次创建 3 组 corridor interior door pairs，模型 valid。
- 2026-04-28 live Garden evolution Round 11：删除并重建
  `corridor_to_meeting_door` pair，使用非矩形/trapezoid `Face3D` door geometry；
  最终 valid，但 Agent 重放 remove/create 导致成本 `24,038` tokens。
- 2026-04-28 forum-fuzzy Test-Garden Round 04：多次真实 MiniMax retry 暴露 face geometry 检索不足、Agent 风格 Plane/Point3D 输入、`boundary` 顶层误传、以及 Surface 门 pair 重复创建问题。当前 deterministic fixes 通过；真实 Garden 在 retry_04 后保持 valid，并部分写入 `OpenOffice_EntryDoor` pair，但 Agent 未 final-output 闭合，不能记为推荐成功路径。
- 2026-04-28 forum-fuzzy multitask Task 1：真实 MiniMax 在
  `D:\Desktop\Codex\gardens\test-garden` 上通过普通外墙门短路径和后续恢复写入
  `MeetingRoom_Right_Door`；Agent final-output 超轮次，但 persisted Garden valid。
