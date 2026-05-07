# Create Honeybee Shades By Parameters

本路径已通过本地 deterministic tests 验证。2026-04-25 披露加固后，
OpenAI Agents focused smoke 已通过 `create_honeybee_shades_by_parameters -> move_object -> relate_honeybee_model -> search_honeybee_model_objects` 组合链路验证；推荐使用本文件中的短 JSON 参数形态。

## 适用场景

- 已有 `Face` 或 `Aperture` typed target，需要生成遮阳板、百叶或窗洞外框。
- 用户说“给这面墙加百叶”“给这个窗加外框/窗套/遮阳边框”。

## 最短路径

1. `search_tools` 查询 `create honeybee shade louver by parameters`。
2. 如还没有宿主 target，先用 `search_honeybee_model_objects` 找到 `face` 或 `aperture`。
3. 调用 `create_honeybee_shades_by_parameters`。
4. 用 `search_honeybee_model_objects` 验证生成的 `shade`。

Compatibility note: `create_honeybee_shades_by_ratio` exists only as a bounded
fallback for low-capability Agents that invent that tool name during simple
overhang/louver tasks. Planned calls should still use
`create_honeybee_shades_by_parameters`.

## 成功调用形态

```json
{
  "name": "create_honeybee_shades_by_parameters",
  "arguments": {
    "garden_root": "tests/.artifacts/.../garden",
    "host_target": {"target_type": "honeybee_object", "object_type": "face"},
    "generation_mode": "louver_by_count",
    "parameters": {
      "depth": 0.35,
      "louver_count": 2,
      "offset": 0.05
    }
  }
}
```

Deterministic fallback: if a low-capability Agent writes `mode` instead of
`generation_mode`, or puts `depth`, `count`, `louver_count`, `distance`,
`offset`, `angle`, `indoor`, or a harmless `width` hint at the top level, the
tool normalizes those into the canonical `generation_mode` and `parameters`
shape. Prefer the compact canonical JSON above in planned calls; current SDK
shade parameter methods use `depth` plus `count/distance`, not `width`.
2026-04-26 token-sink 修复后，服务还接受真实 MiniMax 已生成的
`parameters.louver_depth`、`parameters.louver_angle`，并把顶层
`identifier` / `identifier_prefix` 作为 shade `base_name`。推荐调用仍使用
`parameters.depth`、`parameters.angle` 和可选 `identifier_prefix`，这些
fallback 只是为了避免 Agent 因自然命名重试。
2026-04-26 B-stage short-path rerun 又观察到顶层 `offset_from_host` 和
`louver_orientation="horizontal"`。服务现在把 `offset_from_host` 归一到
`parameters.offset`，并接受 `louver_orientation` 作为无害自然 hint。推荐调用仍使用
`parameters.offset`；精确方向控制应继续用已支持的几何/角度参数。
2026-04-28 forum-fuzzy Test-Garden probe verified that natural
`generation_mode="overhang"` works for aperture-hosted overhangs. The service
normalizes it to one `louver_by_count` shade when only `depth` is provided, and
also accepts top-level `vertical_offset` as `parameters.offset`. Recommended
planned calls should still use the canonical shape below, but Agents can recover
from common forum-style wording without switching to low-level explicit shade
geometry:

```json
{
  "name": "create_honeybee_shades_by_parameters",
  "arguments": {
    "garden_root": "D:/Desktop/Codex/gardens/test-garden",
    "host_target": {"target_type": "honeybee_object", "object_type": "aperture"},
    "generation_mode": "overhang",
    "depth": 0.6,
    "identifier_prefix": "window_overhang"
  }
}
```

## Mixed Shade Systems on Existing Apertures

2026-04-28 live Garden evolution Round 06 verified a compact path for adding
different shade systems to existing apertures in one Code Mode block:

1. `search_honeybee_model_objects(object_type="aperture")`
2. Build `aperture_targets = {match["identifier"]: match["target"] ...}`
3. Use `create_honeybee_shades_by_parameters` with `generation_mode="extruded_border"`
   for a non-rectangular explicit aperture
4. Use `create_honeybee_shades_by_parameters` with `generation_mode="louver_by_count"`
   for a narrow/tall standard window
5. `validate_honeybee_model`

Round 06 created an extruded border around `entry_lobby_trapezoid_window` and
three louvers on `north_office_tall_side_window` in one `execute`, with `5,932`
total tokens and no validation errors.

## 模式边界

- `louver_by_count`：`face` 或 `aperture` 宿主；需要 `depth` 和 `louver_count`。
- `louver_by_distance_between`：`face` 或 `aperture` 宿主；需要 `depth` 和 `distance`。
- `extruded_border`：只允许 `aperture` 宿主；需要 `depth`。

返回里的 `targets` 是新建 shade 的 typed targets，可继续接 `edit_honeybee_shade`、`remove_honeybee_shade`、`move_object` 或 `validate_honeybee_model`。

Shade 参数化生成默认只走 `suggest_validate` 后处理，不自动运行 Room adjacency
relate。返回的 `summary_view.postprocess` 会提示是否需要继续显式
`validate_honeybee_model`。

## 已观察失败模式

- 2026-04-24 的最小 agent smoke 重跑中，低智能模型曾找到 `create_honeybee_shades_by_parameters`，但反复用空 `{}` 调用工具，导致 `garden_root`、`host_target`、`generation_mode`、`parameters` 全部缺失。
- 遇到这种 validation error 时，不要继续空参重试；必须回到上一步搜索或已知结果中取出 host typed target，并完整传入四个必填参数。
- 对 prompt / disclosure 的后续优化方向：工具说明和场景 reference 应更强调“本工具没有默认宿主，不能从自然语言自动猜 host target”。
- 2026-04-24 全量 agent integration 中，组合场景 `create_honeybee_shades_by_parameters -> move_object -> relate_honeybee_model` 暴露了更强的重复失败：模型连续 6 轮用 `arguments: null` 调三个写工具，消耗约 10 万 token。2026-04-25 加强 tool description 后，同一 focused smoke 以 4 次 MCP `call_tool` 完成且无重复 MCP 工具调用；后续仍应避免把更多写操作塞进同一 prompt。
- 2026-04-26 staged MiniMax repair prompt 成功给已有外窗补了 9 个 shade，但仍花费约 83k tokens。高成本来自先前 all-in-one subface/shade 阶段耗尽、随后 repair prompt 里又经历 `return_object_dict`、虚构 shade 工具名和 `width` 参数漂移。当前推荐是：如果窗已存在，直接搜索 aperture，并只对选中的 `matches[i].target` 调 `create_honeybee_shades_by_parameters`。
- 2026-04-26 seeded MiniMax v8 已经能在同一自然 B 段里完成两个房间开窗和 open_office louvers，但仍用了 `133,509` tokens；主要剩余成本是过多 `search_honeybee_model_objects` 和 face normal 探测。后续 Agent 行为层应直接按 room -> exterior wall -> aperture -> shade 的短路径行动。
