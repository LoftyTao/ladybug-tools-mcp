# 创建 Honeybee Room

## 用户意图

- 在指定 Garden 的 Honeybee 模型里创建一个 `Room`
- 优先使用自然语言可发现的最短路径，而不是直接记忆工具名

## 已验证自然语言主路径

### Create Room From Polyface3D

当前真实自然语言验证已经稳定通过的路径是：

1. `search("create honeybee room from polyface or box in garden model")`
2. `await call_tool(create_honeybee_room)`，传入 `_garden_root + _identifier + _room_geometry`
3. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "room"`，确认新 room 已进入当前 Garden 模型

## 已验证 prompt 特征

以下这类口语已经被验证能收敛到 `create_honeybee_room`：

```text
我想在当前模型里用这个体块建一个房间，然后确认它真的已经进了 garden 里的 honeybee 模型。
```

配套约束里已验证有效的信息包括：

- 给出确切 `Garden root`
- 指定新 room identifier
- 提供 `Polyface JSON`
- 明确要求先发现工具，再执行写入，再验证结果

## 已验证最小参数形态

### Using `room_geometry`

```json
{
  "name": "create_honeybee_room",
  "arguments": {
    "garden_root": "<exact garden root>",
    "identifier": "polyface_room",
    "room_geometry": {
      "type": "Polyface3D",
      "vertices": [[0, 0, 0], [4, 0, 0], [4, 6, 0], [0, 6, 0], [0, 0, 3.2], [4, 0, 3.2], [4, 6, 3.2], [0, 6, 3.2]],
      "face_indices": [[[0, 1, 2, 3]], [[0, 4, 5, 1]], [[1, 5, 6, 2]], [[2, 6, 7, 3]], [[3, 7, 4, 0]], [[4, 7, 6, 5]]]
    }
  }
}
```

## 已验证成功判据

- 工具调用里同时出现 `search`、`create_honeybee_room`、`search_honeybee_model_objects`
- `search` query 中能收敛到 `room`
- 持久化后的模型里 `len(model.rooms) == 1`
- 新 room 的 identifier 为 `polyface_room`
- 最终回答或确认信息里能提到新建 room

## 候选/未验证路径

### `faces`

`create_honeybee_room` 的 `faces` 输入路径已有 deterministic MCP 覆盖，但这轮文档更新没有找到自然语言验证证据。

因此：

- 可以把它写成 deterministic 已覆盖的候选输入形态
- 不能把它写成当前推荐的自然语言主路径

候选参数形态如下：

```json
{
  "name": "create_honeybee_room",
  "arguments": {
    "garden_root": "<exact garden root>",
    "identifier": "room_1",
    "faces": [
      {
        "type": "Face",
        "identifier": "room_1_Front"
      }
    ]
  }
}
```

## 高价值失败模式与避坑说明

- `faces` 和 `room_geometry` 必须且仅能提供一个
- `faces` 是完整 Honeybee Face object dict 列表，不是 typed targets
- `room_geometry` 必须是合法 `Polyface3D` dict，不要传 `Face3D`
- `create_honeybee_room` 会写入并 auto-attaches 到 Garden base model；do not pass `host_target` in planned calls
- 成功后不要把 `target` / `room_target` 再传给模型级 add：do not pass returned room targets into `edit_honeybee_model.add_objects`
- 如果目标是“给墙开窗”，不要把它误写成 `create_honeybee_room`；这类请求应先定位 host wall/face，再走 `create_honeybee_apertures_by_parameters`
