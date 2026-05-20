# 清理 Garden Workspace

## 用户意图

- 清理某个指定 Garden 里的临时内容
- 允许清理任意一个 Garden，但清理范围必须受正式枚举约束
- 不删除整个 Garden，也不改动 `garden.json`、`models/`、`libraries/`

## 已验证最短路径

1. `search("cleanup garden workspace tmp artifacts without touching models")`
2. `await call_tool(cleanup_garden_workspace)`，传入 `garden_root + cleanup_scopes`
3. 如需确认结果，可检查对应 scope 目录是否仍存在且已清空

## 已验证最小参数形态

```json
{
  "name": "cleanup_garden_workspace",
  "arguments": {
    "garden_root": "<exact garden root>",
    "_cleanup_scopes": ["tmp"]
  }
}
```

可选：

```json
{
  "name": "cleanup_garden_workspace",
  "arguments": {
    "garden_root": "<exact garden root>",
    "_cleanup_scopes": ["tmp", "artifacts", "flowerpots"],
    "_dry_run_": true
  }
}
```

## 成功判据

- `cleanup_garden_workspace` 能被 `search` 找到
- 返回包含：
  - `report`
  - `summary_view`
  - `persistence_receipt`
  - `removed`
  - `skipped`
- 非 authoring truth 目录被清空后会自动重建目录骨架
- `garden.json`、`models/`、`libraries/` 保持不变

## 高价值失败模式与避坑说明

- `_cleanup_scopes` 当前只接受正式枚举：
  - `artifacts`
  - `flowerpots`
  - `imports`
  - `payloads`
  - `runs`
  - `tmp`
- 这轮不支持任意相对路径字符串，也不支持删除整个 Garden 根目录
- `dry_run = true` 时只报告计划动作，不会删文件
- 对不存在的 scope 或已空目录，工具会稳定返回到 `skipped`，而不是抛出模糊异常
- 在 Garden version restore 前，只有在确认 dirty 文件属于 `tmp`、中间预览或可再生成 artifact 时才清理。用户要求保留的最终报告、关键图、run result 和 library resources 不应被纳入 broad cleanup。

## Evidence

- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch D Task 20 verified scoped cleanup before version restore: temporary preview artifacts blocked restore while the Garden was dirty; after conservative `tmp` / intermediate artifact cleanup, restore succeeded and final HTML/SVG report artifacts were regenerated and retained.
