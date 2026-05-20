# 编辑 Honeybee Model（模型级元数据 + top-level add/remove）

## 用户意图

- 在指定 Garden 的当前 Honeybee base model 上更新模型级元数据
- 通过 `edit_honeybee_model` 追加完整 top-level 对象
- 或移除当前 model 直接持有的 `Room / orphaned Face / orphaned Aperture / orphaned Door / orphaned Shade`

## 已验证最短路径

### Edit Model Metadata + Add Object

1. `search("edit honeybee model add object and update metadata in garden")`
2. `await call_tool(get_base_honeybee_model)`，传入 `garden_root`
3. 读取返回的 `object_dict` 作为 `target`
4. `await call_tool(edit_honeybee_model)`，传入 `_target + display_name_ + user_data_ + _units_ + _tolerance_ + _angle_tolerance_ + add_objects_`
5. `await call_tool(validate_honeybee_model)`

### Remove Top-level Object Through Edit Model

1. `await call_tool(search_honeybee_model_objects)`，传入 `object_type`
2. 读取要移除对象的 `target`
3. `await call_tool(get_base_honeybee_model)`，传入 `garden_root`
4. `await call_tool(edit_honeybee_model)`，传入 `_target + remove_targets_`
5. `await call_tool(validate_honeybee_model)`

## 已验证最小参数形态

### Add Object While Editing Model

```json
{
  "name": "edit_honeybee_model",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_model",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "id": "<model identifier>",
      "model_identifier": "<model identifier>",
      "path": "models/honeybee/<model identifier>.hbjson"
    },
    "display_name": "Edited Model",
    "user_data": {
      "agent": "ok"
    },
    "_units_": "Feet",
    "_tolerance_": 0.02,
    "_angle_tolerance_": 2.0,
    "add_objects_": [
      {
        "type": "Face",
        "identifier": "agent_face_1",
        "display_name": "agent_face_1",
        "geometry": {
          "type": "Face3D",
          "boundary": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]
        },
        "face_type": "Wall",
        "boundary_condition": {
          "type": "Outdoors",
          "sun_exposure": true,
          "wind_exposure": true,
          "view_factor": {
            "type": "Autocalculate"
          }
        },
        "properties": {
          "type": "FacePropertiesAbridged"
        }
      }
    ]
  }
}
```

### Remove Top-level Object While Editing Model

```json
{
  "name": "edit_honeybee_model",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_model",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "id": "<model identifier>",
      "model_identifier": "<model identifier>",
      "path": "models/honeybee/<model identifier>.hbjson"
    },
    "remove_targets_": [
      {
        "target_type": "honeybee_object",
        "garden_id": "<garden id>",
        "domain": "honeybee",
        "model_identifier": "<model identifier>",
        "object_type": "face",
        "object_identifier": "seed_face",
        "parent": {}
      }
    ]
  }
}
```

## 成功判据

- `summary_view.updated_fields` 会显式包含：
  - `add_objects`
  - 或 `remove_objects`
  - 或模型级元数据字段
- add 路径会返回：
  - `summary_view.added_object_count`
  - `summary_view.added_object_types`
- remove 路径会返回：
  - `summary_view.removed_object_count`
  - `summary_view.removed_object_types`
- `persistence_receipt.persisted_path` 保持原登记模型路径
- `validate_honeybee_model.summary_view.is_valid == true`

## 高价值失败模式与避坑说明

- `add_objects_` 当前要求传完整 Honeybee 对象 dict；不要只传几何和 identifier 的半成品 dict
- `add_objects_` 不是 typed target 接口，not `create_honeybee_room.target`
- `create_honeybee_room` 已经把房间写入模型；do not use this to add rooms already created by `create_honeybee_room`
- `remove_targets_` 当前只支持 model 直接持有的对象：
  - `Room`
  - orphaned `Face`
  - orphaned `Aperture`
  - orphaned `Door`
  - orphaned `Shade`
- hosted 子对象删除仍优先走各自 `remove_honeybee_*` 工具；不要把 `face/aperture/door/shade` 的宿主内删除回流到 `edit_honeybee_model`
- 这轮没有把 `replace` 写成已验证主路径
