# Garden Version Management

## 状态

`stable`：当前路径已有确定性 MCP 测试覆盖，并在 2026-04-30 通过 Codex 项目专用 `ladybug_mcp_tester` 子代理验证。真实 Code Mode 路径完成了 `create_garden -> create_honeybee_model -> get_garden_version_status -> create_garden_version -> list_garden_versions -> edit_honeybee_model -> create_garden_version -> restore_garden_version -> get_garden_version_status`，没有再出现版本工具 `execute` 超时。

## 用户意图

- 保存当前 Garden 的一个可恢复版本
- 在一轮用户请求完成后保存整体历史
- 撤销、回退、恢复到之前某一步

## 确定性验证路径

保存一轮用户请求的结果：

1. 完成建模、编辑、属性库、保存或验证工作流。
2. 如果本轮改动了 `garden.json`、`models/` 或 `libraries/`，调用 `create_garden_version`。
3. `subject` 写一句短标题；`summary` 只写 compact metadata，不写 diff、HBJSON 或完整对象正文。

回退到旧版本：

1. 调用 `list_garden_versions`。
2. 根据 `subject` 和 `summary` 选择版本；列表结果同时有 `matches` 和 `versions`，内容相同。
3. 调用 `restore_garden_version`。可以传 `version_id`，也可以传该记录里的 `target` 作为 `version_target`。
4. 如需确认模型状态，使用 `search_honeybee_model_objects`、`validate_honeybee_model` 或 visualize 工具。

## 最小参数形态

```json
{
  "name": "create_garden_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "subject": "feat: add office windows",
    "summary": {
      "operation": "create_windows",
      "targets": ["office_west_Front"],
      "validation": "passed"
    },
    "source": "agent"
  }
}
```

```json
{
  "name": "restore_garden_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "version_id": "<version id from list_garden_versions>",
    "summary": {
      "operation": "undo_user_request"
    },
    "source": "agent"
  }
}
```

或者：

```json
{
  "name": "restore_garden_version",
  "arguments": {
    "garden_root": "<exact garden root>",
    "version_target": {
      "target_type": "garden_version",
      "garden_id": "<garden id>",
      "version_id": "<version id>"
    },
    "source": "agent"
  }
}
```

## 成功判据

- `create_garden_version` 返回 `version_id`、`version_target`、`summary_view` 和 `persistence_receipt`。
- `list_garden_versions` 只返回 compact history，不返回 patch。
- `restore_garden_version` 返回 `restored_from_version` 和新的 `new_version`。
- 回退本身是新历史，不改写旧历史。

## 避坑说明

- 不要请求或制造 Git diff。
- 不要把 HBJSON、DFJSON、library object body 或完整模型快照写入 `summary`。
- 如果 restore 报当前 Garden 有未保存 authoring truth 改动，先问用户是否保存当前状态，或先调用 `create_garden_version`。
- 如果 restore 前只是 `tmp`、中间预览或可再生成 artifacts 造成 dirty，先用 `get_garden_version_status` 看清 dirty 文件，再用 `cleanup_garden_workspace` 做受限清理；不要清理 `models/`、`libraries/` 或用户要求保留的最终图表/报告。
- 不要把 version 工具当作对象 diff 工具；对象确认走 Search / Validate / Visualize。
- 推荐拆成短 `execute` 块：创建/编辑、版本保存、版本列表、恢复可以分段执行，避免把大模型编辑和恢复验证塞进一个超长块。
- 2026-04-30 前的问题边界：Git 子进程曾继承 stdio MCP transport，导致版本工具在真实 Code Mode 下卡住。服务层已改为 `stdin=subprocess.DEVNULL`，回归测试和专用子代理 Batch 1 均已验证修复。
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 20 verified restore + conservative cleanup + final artifact retention. The Agent restored a `pre-shading baseline` version, confirmed shade count returned to 0 and Garden status was clean, then regenerated and retained final HTML/SVG report artifacts. A first restore attempt failed while temporary artifacts made the Garden dirty, confirming the need for explicit scoped cleanup before restore.
