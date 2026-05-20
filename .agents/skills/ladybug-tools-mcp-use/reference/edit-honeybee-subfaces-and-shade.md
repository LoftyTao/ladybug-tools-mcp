# 编辑 Honeybee Aperture / Door / Shade（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，原位编辑已有的 `Shade`、`Aperture`、`Door`
- 优先走真实的 `search_honeybee_model_objects -> edit_honeybee_*` 主链
- 修改后立即确认对象仍在原模型里，并且关键字段已经更新

## 模拟真实用户 Prompts

```text
请在这个 Garden 里找到 shade_1、window_1、door_1，并分别更新它们的几何、基础属性和 energy/radiance 热拔插属性。
先搜索对象，再把搜索结果里的 target 传给 edit 工具，不要手写 target。
不要创建新对象；编辑完成后告诉我 Edited Shade、Edited Window、Edited Door 都已经写回模型。
```

## 已验证最短路径

1. `search("edit honeybee shade geometry in model")`
2. `search("edit honeybee aperture operable geometry in model")`
3. `search("edit honeybee door glass geometry in model")`
4. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "shade"`
5. 读取 `shade_1` 的 `target`
6. `await call_tool(edit_honeybee_shade)`，传入 `_target + geometry_ + display_name_ + user_data_ + energy/radiance hot-swap inputs`
7. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "aperture"`
8. 读取 `window_1` 的 `target`
9. `await call_tool(edit_honeybee_aperture)`，传入 `_target + geometry_ + is_operable_ + display_name_ + energy/radiance hot-swap inputs`
10. `await call_tool(search_honeybee_model_objects)`，`_object_type_ = "door"`
11. 读取 `door_1` 的 `target`
12. `await call_tool(edit_honeybee_door)`，传入 `_target + geometry_ + is_glass_ + display_name_ + energy/radiance hot-swap inputs`
13. 如需确认结果，可再次 `search_honeybee_model_objects(_object_type_="all")`

## 已验证最小参数形态

### Edit Honeybee Shade

```json
{
  "name": "edit_honeybee_shade",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "shade",
      "object_identifier": "shade_1",
      "parent": {
        "face_identifier": "wall_1"
      }
    },
    "geometry_": {
      "type": "Face3D",
      "boundary": [[0.2, -0.6, 3.2], [3.8, -0.6, 3.2], [3.8, 0, 3.2], [0.2, 0, 3.2]]
    },
    "display_name": "Edited Shade",
    "user_data": {
      "agent": "ok"
    },
    "construction": {
      "type": "ShadeConstruction",
      "identifier": "shade_construction_1",
      "solar_reflectance": 0.45,
      "visible_reflectance": 0.5,
      "is_specular": false
    },
    "transmittance_schedule_": {
      "type": "ScheduleRuleset",
      "identifier": "shade_schedule_1",
      "day_schedules": [
        {
          "type": "ScheduleDay",
          "identifier": "shade_schedule_1_day",
          "values": [0.25],
          "times": [[0, 0]],
          "interpolate": false
        }
      ],
      "default_day_schedule": "shade_schedule_1_day"
    },
    "modifier": {
      "type": "Plastic",
      "identifier": "shade_mod_1",
      "r_reflectance": 0.35,
      "g_reflectance": 0.35,
      "b_reflectance": 0.35,
      "specularity": 0.0,
      "roughness": 0.05
    },
    "modifier_blk": {
      "type": "Plastic",
      "identifier": "shade_blk_1",
      "r_reflectance": 0.05,
      "g_reflectance": 0.05,
      "b_reflectance": 0.05,
      "specularity": 0.0,
      "roughness": 0.05
    },
    "dynamic_group_identifier_": "shade_group_1",
    "states_": {
      "operation": "replace_all",
      "states": [
        {
          "type": "RadianceShadeState",
          "modifier": {
            "type": "Plastic",
            "identifier": "shade_state_mod_1",
            "r_reflectance": 0.6,
            "g_reflectance": 0.6,
            "b_reflectance": 0.6,
            "specularity": 0.0,
            "roughness": 0.0
          }
        }
      ]
    }
  }
}
```

### Edit Honeybee Aperture

```json
{
  "name": "edit_honeybee_aperture",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "aperture",
      "object_identifier": "window_1",
      "parent": {
        "face_identifier": "wall_1"
      }
    },
    "geometry_": {
      "type": "Face3D",
      "boundary": [[1.1, 0, 1.1], [2.2, 0, 1.1], [2.2, 0, 2.1], [1.1, 0, 2.1]]
    },
    "is_operable_": true,
    "display_name": "Edited Window",
    "construction": {
      "type": "WindowConstruction",
      "identifier": "window_construction_1",
      "materials": [
        {
          "type": "EnergyWindowMaterialSimpleGlazSys",
          "identifier": "window_construction_1 Material",
          "u_factor": 2.8,
          "shgc": 0.35,
          "vt": 0.6
        }
      ]
    },
    "vent_opening_": {
      "type": "VentilationOpening",
      "fraction_area_operable": 0.4,
      "fraction_height_operable": 0.8,
      "discharge_coefficient": 0.5,
      "wind_cross_vent": true
    },
    "modifier": {
      "type": "Plastic",
      "identifier": "window_mod_1",
      "r_reflectance": 0.5,
      "g_reflectance": 0.5,
      "b_reflectance": 0.5,
      "specularity": 0.0,
      "roughness": 0.05
    },
    "dynamic_group_identifier_": "window_group_1",
    "states_": {
      "operation": "replace_all",
      "states": [
        {
          "type": "RadianceSubFaceState",
          "modifier": {
            "type": "Plastic",
            "identifier": "window_state_mod_1",
            "r_reflectance": 0.7,
            "g_reflectance": 0.7,
            "b_reflectance": 0.7,
            "specularity": 0.0,
            "roughness": 0.0
          }
        }
      ]
    }
  }
}
```

### Edit Honeybee Door

```json
{
  "name": "edit_honeybee_door",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "door",
      "object_identifier": "door_1",
      "parent": {
        "face_identifier": "wall_1"
      }
    },
    "geometry_": {
      "type": "Face3D",
      "boundary": [[2.2, 0, 0.1], [3.1, 0, 0.1], [3.1, 0, 2.2], [2.2, 0, 2.2]]
    },
    "is_glass_": true,
    "display_name": "Edited Door",
    "construction": {
      "type": "WindowConstruction",
      "identifier": "door_construction_1",
      "materials": [
        {
          "type": "EnergyWindowMaterialSimpleGlazSys",
          "identifier": "door_construction_1 Material",
          "u_factor": 2.8,
          "shgc": 0.35,
          "vt": 0.6
        }
      ]
    },
    "modifier": {
      "type": "Plastic",
      "identifier": "door_mod_1",
      "r_reflectance": 0.45,
      "g_reflectance": 0.45,
      "b_reflectance": 0.45,
      "specularity": 0.0,
      "roughness": 0.05
    }
  }
}
```

## 成功判据

- 三个 edit 工具都返回 `summary_view.updated_fields`
- `persistence_receipt.persisted_path` 仍指向原登记模型路径
- 模型文件中：
  - `shade_1.display_name == "Edited Shade"`
  - `shade_1` 的 `construction / transmittance_schedule / modifier_blk / states` 已持久化
  - `window_1.display_name == "Edited Window"` 且 `is_operable == true`
  - `window_1` 的 `construction / vent_opening / states` 已持久化
  - `door_1.display_name == "Edited Door"` 且 `is_glass == true`
  - `door_1` 的 `construction / modifier` 已持久化
- 编辑不会把对象从原宿主路径上移走

## 高价值失败模式与避坑说明

- `target` 最好总是来自当前模型的真实搜索结果；不要手写 target
- 大型“一次改 shade、aperture、door 三类对象”的 Agent prompt 容易在低智能模型上耗尽 turn 或丢失工具参数。若目标是稳定执行，优先拆成三个 focused workflows：先搜索并编辑 shade，再搜索并编辑 aperture，最后搜索并编辑 door。
- 遇到 `arguments: null`、`arguments: {}` 或 `target` 缺失时，不要重复调用同一个 edit 工具；必须重新调用 `search_honeybee_model_objects` 拿到 typed target，并重建完整参数对象。
- `edit_honeybee_shade` 当前支持更新 `geometry / display_name / user_data / is_detached / construction / transmittance_schedule / pv_properties / modifier / modifier_blk / dynamic_group_identifier / states`
- `edit_honeybee_aperture` 当前支持更新 `geometry / display_name / user_data / is_operable / construction / vent_opening / modifier / modifier_blk / dynamic_group_identifier / states`
- `edit_honeybee_door` 当前支持更新 `geometry / display_name / user_data / is_glass / construction / vent_opening / modifier / modifier_blk / dynamic_group_identifier / states`
- `states_` 当前支持 `replace_all / add / clear` 三种操作；如果传 list，会按 `replace_all` 处理
- `Aperture` 如果是 `Surface` 邻接，当前不支持单边改几何，也不支持单边改 `is_operable`
- `Door` 如果是 `Surface` 邻接，geometry edit 会自动投影并更新相邻 paired Door；仍不支持单边改 `is_glass`
- `Aperture / Door` 的 `construction` 类型仍受 SDK 约束；例如玻璃门需要可用于 glass door 的 window construction
- 这轮同时补了 HBJSON round-trip 资源修复：显式挂上的 `shade transmittance_schedule`、`modifier_blk` 和 `state modifiers` 会在保存后自动补进模型资源区
- `Shade` 如果已有父级，当前不能直接把它设成 detached；这类语义更接近重新挂接而不是原位编辑

## Paired Interior Door Geometry Edit

2026-04-28 live Garden evolution Round 09 first failed because
`edit_honeybee_door` rejected `Surface` door geometry changes and MiniMax drifted
into remove/recreate retries. The service now supports the direct path:

1. `search_honeybee_model_objects(object_type="door", identifier="<interior door>")`
2. Pass `matches[0].target` to `edit_honeybee_door`
3. Include `geometry` on one side of the Surface pair
4. Call `validate_honeybee_model`

The retry updated both sides of `corridor_to_lobby_door` in one `execute`, with
`4,837` total tokens and no validation errors. Do not use remove/recreate for
paired door geometry updates unless explicitly repairing corrupted state.
