# 扩建 Existing Live Honeybee Model

## 适用场景

- 用户要求在已有 Garden / Grasshopper-followed model 上继续扩建，而不是新建测试 Garden。
- 需要一轮内组合 `Room` 创建、adjacency 修复、窗/门创建、对象清点和校验。
- 目标是生产式增量建模，失败后应从当前 Garden 状态继续修复，不要重建整套模型。

## 已验证最短路径

1. 在 Code Mode `execute` 中设置已有 `garden_root`。
2. 用 `create_honeybee_room` 创建新增房间；box room 用 `identifier / x_dim / y_dim / height / origin`。
3. 立刻调用 `relate_honeybee_model`，复杂扩建优先用 `relation_mode="explicit_relate_full"`。
4. 调用 `search_honeybee_model_objects(object_type="room")`，建立 `identifier -> target` 映射。
5. 对新增房间用 `children_scope=<room target>` 搜索 `Wall` + `Outdoors` Face。
6. 根据 `normal_vector` 选择目标外墙。
7. 用 `create_honeybee_apertures_by_parameters` 或 `create_honeybee_door` 添加可见窗/门。
8. 调用 `validate_honeybee_model`，再用 compact search 清点目标对象。

## Code Mode 形态

```python
garden_root = "D:/Desktop/Codex/rec-ladybug-tools-mcp/gardens/test-garden"
room = await call_tool("create_honeybee_room", {
    "garden_root": garden_root,
    "identifier": "north_office",
    "x_dim": 6,
    "y_dim": 4,
    "height": 3,
    "origin": [0, 4, 0],
})
relate = await call_tool("relate_honeybee_model", {
    "garden_root": garden_root,
    "relation_mode": "explicit_relate_full",
})
rooms = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "room",
})
room_targets = {match["identifier"]: match["target"] for match in rooms["matches"]}
faces = await call_tool("search_honeybee_model_objects", {
    "garden_root": garden_root,
    "object_type": "face",
    "children_scope": room_targets["north_office"],
    "face_type": "Wall",
    "boundary_condition": "Outdoors",
})
host = [m for m in faces["matches"] if m.get("normal_vector", [0, 0, 0])[1] > 0.8][0]["target"]
window = await call_tool("create_honeybee_apertures_by_parameters", {
    "garden_root": garden_root,
    "host_target": host,
    "generation_mode": "by_width_height",
    "aperture_width": 1.8,
    "aperture_height": 1.2,
    "sill_height": 0.9,
    "aperture_identifier": "north_office_north_window",
})
validation = await call_tool("validate_honeybee_model", {
    "garden_root": garden_root,
})
return {"room": room["target"], "window": window["target"], "is_valid": validation["is_valid"]}
```

## 成功判据

- 新增 room 出现在 `search_honeybee_model_objects(object_type="room")`。
- 新增窗/门出现在对应 host Face 的 child count 或全局对象搜索中。
- `validate_honeybee_model.is_valid == true`。
- SDK 读取 persisted `grasshopper_live_model.hbjson` 时 `check_all(..., detailed=True)` 为空。

## 注意事项

- `explicit_relate_full` 可能把原本外墙上的 Door/Aperture 克隆为相邻侧 paired subface；这是有效 Honeybee adjacency，但应在台账中记录对象数量变化。
- 不要把完整搜索响应传给下游 `host_target`；选择 `matches[i].target`。
- 如果 PowerShell 运行 live-round snippet，避免直接打印 MiniMax final output 中的 Unicode checkmarks；写 artifact 或用 ASCII summary。
- 后续如果要制造更丰富几何，优先在可见窗/门/遮阳上使用显式 `Face3D` 或多边形 shade，而不是把所有复杂度塞进 Room box 创建。

## 验证记录

- 2026-04-30 supervised external matrix task 04 verified that an external Agent can create two adjacent rooms and call `relate_honeybee_model` in the stable Honeybee suite. The persisted state was functional, but supervisor stopped a later outer-tool loop, so this is evidence for the relationship path and for the need to stop after compact verification.
- 2026-04-30 supervised external matrix task 07 verified exterior door creation on the existing suite model with `create_honeybee_door`, no model/room rebuild, and final `ok`.
- 2026-04-28 Round 01 live Garden evolution：一条 `execute`，8 个 inner MCP calls，`6,911` total tokens；模型从 2 rooms 扩到 4 rooms，valid。
- 2026-04-28 Round 02 live Garden evolution：一条 `execute`，10 个 inner MCP calls，`7,899` total tokens；新增 east corridor 和 entry lobby，valid。
- 2026-04-28 Round 10 repair：从当前 Garden 状态重建 entry lobby replacement window / glass door / canopy，一条 `execute`，6 个 inner MCP calls，`6,794` total tokens；valid。失败重试显示：恢复类建模要先接受“当前 Garden 状态就是事实”，不要从旧 prompt 假设原对象仍存在。
- 2026-04-28 Rounds 13-17：同一 live Garden 上继续完成低 U 值窗构造集、opaque envelope、door construction、ProgramType/load、HVAC/setpoint/fan 和额外遮阳。Round 16 的写入轮次虽然 `MaxTurnsExceeded`，但 MiniMax confirmation run 证明 persisted Garden 正确；这种情况必须用 Agent confirmation 或 SDK inspection 记录，不能只看 final status。
- 2026-04-28 Round 18 retry：Radiance modifier identifier handoff 修复后，MiniMax 在同一 live model 上完成 aperture/door/shade modifier 和 trapezoid baffle，valid，`11,797` tokens。
- 2026-04-28 Round 20 retry：MiniMax 通过 compact `visualization_set_target` 生成 live model HTML 预览，valid，`9,908` tokens。当前 live model 清点为 6 rooms、37 faces、7 apertures、14 doors、21 shades、SDK validation errors 0。
