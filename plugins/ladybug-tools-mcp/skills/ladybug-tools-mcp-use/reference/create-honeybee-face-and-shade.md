# 创建 Honeybee Face 和 Shade

## 用户意图

- 在指定 Garden 的 Honeybee 模型中创建一个 orphaned `Face`
- 再创建一个 `Shade`，并确认两者都已进入模型

## 模拟真实用户 Prompts

```text
在这个 Garden 里创建一个 wall_1，然后再创建一个 shade_1，并确认都存在。
先建一个 Honeybee face，再建一个 detached shade，最后搜索模型对象给我结果。
请用这个确切 Garden root 创建 wall_1 和 shade_1，然后告诉我它们是否写进模型了。
```

## 已验证最短路径

1. `call_tool(create_garden)`
2. `call_tool(create_honeybee_model)`
3. `call_tool(create_honeybee_face)`
4. `call_tool(create_honeybee_shade)`
5. `call_tool(search_honeybee_model_objects)`

## Deterministic 交叉验证补充

2026-04-25 的 MCP deterministic 交叉测试覆盖了纯 MCP 创建较完整模型：

- `create_honeybee_model`
- `edit_honeybee_model`
- `create_honeybee_room(_room_geometry)`
- `create_honeybee_face`
- `create_honeybee_aperture`
- `create_honeybee_door`
- hosted `create_honeybee_shade`
- `create_honeybee_apertures_by_parameters`
- `create_honeybee_shades_by_parameters`
- `search_honeybee_model_objects`
- `validate_honeybee_model`

该证据说明固定参数 MCP workflow 可稳定写回并验证模型，但不等同于新的自然语言 Agent 主路径。

## Agent 交叉验证补充

2026-04-25 的 Agent 交叉测试通过了从空 Garden 创建 `Model -> Face -> Aperture -> Door -> hosted Shade -> Validate` 的长链路。该路径要求 Agent 先搜索 `wall_1`，再把 `search_honeybee_model_objects` 返回的 `matches[0].target` 作为 `host_target` 传给 aperture / door / hosted shade 创建工具。

注意：推荐路径仍是给下游 `host_target` 传嵌套 typed target dict。服务层可以在完整搜索结果或完整 create 返回中只有一个有效 target 时自动 unwrap；如果 response 中有多个 target，会要求明确选择一个。

同一 Garden/model 的多个写工具应避免并行发出。服务端已对同进程 Honeybee model 写入做串行化保护，但推荐节奏仍是：写入 aperture，搜索/确认 host face，再写入 door，搜索/确认 host face，再写入 hosted shade。

## 已验证最小参数形态

```json
{
  "name": "create_honeybee_face",
  "arguments": {
    "garden_root": "<exact garden root>",
    "identifier": "wall_1",
    "geometry": {
      "type": "Face3D",
      "boundary": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]
    }
  }
}
```

```json
{
  "name": "create_honeybee_shade",
  "arguments": {
    "garden_root": "<exact garden root>",
    "identifier": "shade_1",
    "geometry": {
      "type": "Face3D",
      "boundary": [[0, 1, 3.1], [4, 1, 3.1], [4, 0.5, 3.1], [0, 0.5, 3.1]]
    },
    "is_detached": true
  }
}
```

## 成功判据

- `create_honeybee_face` 返回 `target.object_type == "face"`
- `create_honeybee_shade` 返回 `target.object_type == "shade"`
- `search_honeybee_model_objects(_object_type_="all")` 能找到 `wall_1` 和 `shade_1`
- 最终回答中提到这两个 identifier

## 高价值失败模式与避坑说明

- `geometry` 必须是合法 `Face3D` dict，至少包含 `type = "Face3D"` 和 `boundary`
- 显式创建的 `identifier` 必须在模型里唯一。如果失败后重放时对象已经存在，
  不要再次 create；先用 `search_honeybee_model_objects(object_type="shade", identifier=...)`
  找到 typed target，必要时再调用 `remove_honeybee_shade(target=matches[i].target)`。
- `Face` 与 `Shade` 现在都会前置检查平面性和自交；不合法几何会在创建时直接失败
- 如果需要创建附着在宿主上的 `Shade`，应先确认宿主 typed target 正确；deterministic 交叉测试已覆盖 hosted shade，Agent 自然语言路径仍应先搜索宿主 target
- 多步写链路容易触发 Agent turn 上限；如果是验证长链路，应记录 `agent_metrics.json`，不要只看最终是否通过
- 如果 `agent_metrics.json` 显示同一个 response 内连续发出多个写工具，应记录为披露层风险；现在服务端会串行化同进程写入，但 Agent 侧仍应减少这类调用

## Live Round 12 证据

2026-04-28 live Garden evolution Round 12 创建了三个更有变化的 detached shades：

- `courtyard_triangular_sail`
- `entry_marker_kite_shade`
- `angled_service_fin`

第一次 Agent replay 曾写出重复 shade identifiers 并导致 SDK validation errors。
服务层已改为在显式 create 前拒绝重复 identifier；修复后 current-state confirmation
验证模型 valid，最终 live model 为 `14` shades。
