# 删除 Honeybee Aperture（基于 typed target）

## 用户意图

- 在指定 Garden 的 Honeybee 模型中，删除一个已存在的 `Aperture`
- 先用自然语言定位 room/face/aperture，再执行删除并确认结果
- 第一阶段已验证 face-hosted aperture 的主链

## 已验证自然语言主路径

当前自然语言验证已经稳定通过的路径是：

1. `search_tools("remove a window or aperture from a room wall in garden model")`
2. `call_tool(search_honeybee_model_objects)`，定位 `Tiny_House_Office`、前墙和 `Front_Aperture`
3. 读取 aperture 的 typed target
4. `call_tool(remove_honeybee_aperture)`，将该 target 传入 `target`
5. 用后续确认说明或再次搜索确认 aperture 已被删除

## 已验证 prompt 特征

以下这类口语已经被验证能收敛到删除 aperture 主链：

```text
这个模型里 Tiny_House_Office 房间前墙上的 Front_Aperture 不要了，帮我删掉并确认已经删掉。
```

在当前测试里，以下提示对 discoverability 有帮助：

- 明确 room identifier
- 明确 host wall 位置
- 明确 aperture identifier
- 明确要求“先找对对象再删”

## 已验证最小参数形态

```json
{
  "name": "remove_honeybee_aperture",
  "arguments": {
    "garden_root": "<exact garden root>",
    "target": {
      "target_type": "honeybee_object",
      "garden_id": "<garden id>",
      "domain": "honeybee",
      "model_identifier": "<model identifier>",
      "object_type": "aperture",
      "object_identifier": "Front_Aperture",
      "parent": {
        "face_identifier": "Tiny_House_Office_Front"
      }
    }
  }
}
```

## 已验证成功判据

- 工具调用里出现 `search_tools`
- 后续出现 `search_honeybee_model_objects`
- 后续出现 `remove_honeybee_aperture`
- 搜索 query 中出现 `room`、`wall` 或 `window`
- 持久化后的 `Tiny_House_Office_Front` 不再包含 aperture
- 最终回答里会说明删除动作已发生，或提到 `Front_Aperture`

## 候选/未扩展路径

- 内窗成对删除逻辑是已有工具能力，但本轮自然语言验证证据聚焦的是 `Front_Aperture` 这条单窗删除路径
- 更复杂的多 aperture 批量删除，还没有这轮自然语言验证证据
- 2026-04-25 的 MCP deterministic 交叉测试覆盖了从已有模型搜索 aperture typed target 后调用 `remove_honeybee_aperture`，再与 face/room edit、shade create 和 validate 串联收口。该证据属于固定 MCP workflow，不自动升级为自然语言推荐主路径。

## 高价值失败模式与避坑说明

- 不要直接手写 aperture target；优先把搜索结果里的完整 `target` 传入工具
- 当前自然语言主链强调 room -> face -> aperture 的收敛过程；如果直接跳到泛化 `model` 层，命中率会下降
- 如果目标其实是“给墙开窗”而不是“删窗”，不要误走删除链；应先定位 host wall/face，再调用 `create_honeybee_apertures_by_parameters`
