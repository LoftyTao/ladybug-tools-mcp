# Ladybug Tools MCP Use Skill 协作约定

本目录是 Agent 使用 Ladybug Tools MCP 的官方操作 Skill。它不是项目状态页、证据仓库、测试日志或计划目录。

## 读取规则

- 修改本目录前，必须同时读取：
  - 仓库根目录 `AGENTS.md`
  - `.agents/skills/AGENTS.md`
  - `docs/llm-wiki/AGENTS.md`
  - `docs/llm-wiki/maintenance/update-protocol.md`
- 如果改动来自测试、Agent run、token/cost 或失败模式，先更新 LLM-Wiki，再改 Skill。
- Skill 实质更新由 `mcp_skill_maintainer` 按已有 LLM-Wiki 落点做最小投影，随后由新的 `mcp_tester` 会话使用相同自然语言任务复验。

## 允许进入 Skill 的内容

- 何时使用这个路径。
- 必要前置条件。
- MCP 工具调用顺序。
- 精确参数名和 target 传递方式。
- Code Mode 中的紧凑调用骨架。
- 预期返回字段。
- 停止条件和不要发明的工具。
- 短 prompt trigger 或短 anti-pattern，且必须直接改变 Agent 下一步操作。

## 禁止进入 Skill 的内容

- 日期、run id、artifact 目录、pytest 输出、token/cost、provider/model 名称。
- batch/matrix 状态表、长期测试 ledger、历史 debug 叙事。
- 完整 prompt/transcript 和逐轮模型表现。
- roadmap、implementation plan、candidate backlog。
- EnergyPlus、Ladybug Tools SDK 或 Ironbug 的长文档摘抄；概念背景只保留到能帮助选择 MCP 工具为止。

## Projection Rule

Skill reference 的每一次实质更新都应能回答：

1. Agent 下次会因此多做、少做或改做哪一步？
2. 这条规则对应的证据或背景是否已经在 LLM-Wiki 中有位置？
3. 如果把日期、artifact、token 和 provider 信息删掉，这条 Skill 仍然有用吗？

如果第 1 题答案不明确，不要改 Skill；改 LLM-Wiki。
如果第 2 题答案是否定，先补 LLM-Wiki。
如果第 3 题答案是否定，这段内容属于证据，不属于 Skill。
