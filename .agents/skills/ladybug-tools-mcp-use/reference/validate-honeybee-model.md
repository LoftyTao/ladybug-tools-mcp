# 验证 Honeybee Model（基于 Garden/base model）

## 用户意图

- 对当前 Garden 里的 Honeybee base model 做正式 MCP 级校验
- 不导出完整模型正文，只拿 `report`、`summary_view` 和结构化 `issues`
- 在 create / edit / remove 后快速确认模型仍然有效，或定位真实问题

## 已验证最短路径

1. `search("validate honeybee model in garden")`
2. `await call_tool(validate_honeybee_model)`，传入 `garden_root`
3. 读取返回里的：
   - `report.status`
   - `is_valid` / `valid`（Agent 摘要用的顶层 helper）
   - `summary_view.is_valid`
   - `summary_view.issue_count`
   - `issues`

如果需要验证显式模型而不是当前 base model，再补 `model_target`。

## 已验证最小参数形态

```json
{
  "name": "validate_honeybee_model",
  "arguments": {
    "garden_root": "<exact garden root>"
  }
}
```

## 返回重点

- 顶层 helper
  - `is_valid`
  - `valid`
- `report`
  - `status = "ok"` 表示当前没有发现 validation issues
  - `status = "invalid"` 表示发现了结构化 issues
- `summary_view`
  - `garden_target`
  - `model_target`
  - `model_identifier`
  - `is_valid`
  - `issue_count`
  - `issue_codes`
  - `issue_types`
  - `issue_counts_by_code`
  - `object_counts`
- `issues`
  - 直接保留 Honeybee SDK 的详细校验结果，适合机器继续消费

## 成功判据

- 有效模型时：
  - `report.status == "ok"`
  - `is_valid == true`
  - `valid == true`
  - `summary_view.is_valid == true`
  - `summary_view.issue_count == 0`
  - `issues == []`
- 无效模型时：
  - `report.status == "invalid"`
  - `is_valid == false`
  - `valid == false`
  - `summary_view.is_valid == false`
  - `summary_view.issue_count > 0`
  - `issues[*].type == "ValidationError"`

## 高价值说明与避坑

- 这个工具当前直接走 Honeybee SDK 官方 `Model.check_all(..., detailed=True)`，不是 MCP 自造的平行验证规则
- 默认验证的是 Garden 当前 base model；如果线程上下文里 base model 已切换，结果也会随之变化
- `issues` 里会直接暴露 SDK 的 `code / error_type / element_type / message`，优先消费这些字段，不要自己从 `report.message` 反推问题
- 这个工具是正式只读入口，适合放在 `create / edit / remove` 之后做收口确认
- 2026-04-25 的 MCP deterministic 交叉测试覆盖了两种 validate 收口：纯 MCP 从空 Garden 创建详细模型后校验，以及从已有模型搜索 target、编辑、删除、再校验。两条路径均不要求返回完整模型正文。
