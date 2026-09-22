# 分发实现验收记录

更新日期：2026-09-22。目标版本：1.2.1。[PR #3](https://github.com/LoftyTao/ladybug-tools-mcp/pull/3)，分支 `codex/distribution-installer`。

三平台基线、Codex、OpenCode2、Grasshopper 和浏览器预览已通过；跨版本升级补充检查本地已通过，并已纳入三平台 CI。用户已明确暂不登录 PyPI，因此正式发布仍未完成。ADR 的 `accepted` 表示方案已确认，不能用来代替交付状态。

## 产物与来源

- [首次三平台全部通过的 CI](https://github.com/LoftyTao/ladybug-tools-mcp/actions/runs/35708369534)：提交 `68d2235c`，从源码包构建一次，三个平台安装同一个 wheel。发布 job 在 PR 中跳过。
- 该次 CI wheel SHA-256：`cb02e7f6b88d75ceb8ada9c4b3c5d2c98bd2f876d19284250d5462269b86f1a2`。
- 本地交付路径为 `dist/ladybug_tools_mcp-1.2.1-py3-none-any.whl` 和同目录源码包；后续下载的 CI 产物与哈希记录在 `dist/SHA256SUMS`。最终发布须使用对应发布 CI 实际测试的产物，不能以另一次构建替换。
- wheel 包含 110 个 Skill 文件、6 个 `.ghuser`、组件清单和 27 个 EPW；wheel 与源码包均通过 `twine check`。

安装器、资源和平台边界见[分发说明](distribution.md)。运行时及依赖由 uv 管理，Garden 与程序、缓存分开，用户不需要构建 MCP 或 Grasshopper 组件。

## 已通过

| 检查 | 实际结果 |
| --- | --- |
| 三平台原生运行 | GitHub 托管 Windows x86_64、Linux x86_64、macOS Apple Silicon runner 实际安装并运行 CPython 3.12 wheel；非 editable，服务用 `-I` 启动。 |
| 安装配置与维护 | 中文/空格路径、终端选项、仅生成配置、自动配置、重复安装、损坏 wheel 的失败重试、同名冲突拒绝、显式替换及备份、无关设置保留、卸载保留用户修改和 Garden。 |
| 跨版本升级 | 实际安装合成前版 `1.2.1.dev0`，创建 Garden、模型和 Git 版本，再升级同一运行目录至 `1.2.1`；安装记录更新、Skill 冲突拒绝及显式备份、Codex 配置保留、Garden 字节不变、当前 MCP 继续读取旧 Garden 均通过。 |
| MCP 确定性基线 | 正式 stdio 连接；Code Mode 发现及执行、Skill 资源、完整 EPW、Garden、房间建模、有效性检查、独立几何复核。Git 版本保存和无 Git 创建 Garden 均通过。 |
| localhost HTTP | 页面和 `/api/state` 可读，场景包含实际模型；回归检查在禁止反向 DNS 查询时仍成功提供 HTTP 页面。未更改 vtk.js CDN 依赖。 |
| 浏览器真实预览 | 2026-09-22 在 Codex Browser 实际看到安装包导出的房间模型；Ax 和 Top 相机切换正常，浏览器无 error/warn。截图在 `tests/.artifacts/distribution/native-20260922/preview-axonometric.png` 和 `preview-top.png`。 |
| Codex 自然语言 | 原生 CLI 读取 Skill，通过已安装 MCP 创建、移动、查询、验证并保存 Garden 版本。独立复核：1 个房间，30 m²、90 m³，X=2–8、Y=0–5、Z=0–3 m；版本 `64ed4fb`，无未保存变更。 |
| OpenCode2 免费模型 | 隔离的官方 `@opencode/cli@2.0.12`、`opencode/mimo-v2.5-free`，实际加载 Skill，通过 MCP 创建 Garden、模型、6×5×3 m 房间并验证、开启预览。独立 HBJSON 复核为 1 room、6 faces，X=0–6、Y=0–5、Z=0–3；另以已安装 MCP 重开预览验证 HTTP 200，再停止服务。未使用付费模型。 |
| Grasshopper 正常发现 | 新 Rhino 8 会话（PID 15904）先安装组件，再正常启动 Grasshopper 1；六个组件均由原生目录扫描自动发现，搜索结果指向受管安装目录，无手工索引注入。 |
| Grasshopper 交接 | 从搜索结果实例化六个组件并核对端口；完成 Garden 创建、列表选择、Honeybee 读取；30 m²、90 m³；保存 `.gh` 后重开重算通过。之前的中文路径测试亦通过。 |
| Flowerpot 回归 | 23 项既有 pytest 检查通过。 |

跨版本测试的前版 wheel 是本次代码生成的测试夹具，不对外发布，也不代表曾发布过该版本。升级和整套确定性检查由 `tests/deterministic/validate_distribution.py` 在每个平台执行，最后一次执行状态见 PR CI。

## 发现并修复的问题

- 英文 Windows 的默认输出编码无法打印中文安装路径：安装器 stdout/stderr 明确使用 UTF-8。
- macOS 的单次 localhost 启动耗时超过 Code Mode 30 秒：标准 HTTP 服务器会反向查询地址；预览固定使用 loopback，改为直接绑定并保留服务器地址。修复后三平台均在原有时限内通过，没有提高产品超时来隐藏问题。
- 一次 Code Mode 包含过多验收步骤会累计超时：确定性测试拆为正常的分阶段调用。
- IronPython/CPython JSON 往返破坏中文路径：使用 ASCII JSON Unicode 转义。
- 预制 Honeybee Link 的可选 `_write` 没有默认值：预制布尔端口现在有 False 数据。组件 reload 保留同一 worker。
- 同版本损坏环境的健康检查、Garden/cache 双向重叠、交互选项确定后的 Skills 路径校验、运行时已删除后的卸载清理已补齐。

## Agent 版本与证据边界

Codex 使用独立测试 profile，仅对测试服务器的 `execute` 预先授权；安装器保留用户原有审批策略。证据在 `D:/.garden/distribution-acceptance/codex/`。

OpenCode2 的旧 `@opencode-ai/cli` beta18721/beta19271 曾被免费服务以 HTTP 426 拒绝；官方 V2 安装入口指定的 `@opencode/cli@2.0.12` 已完成实际任务。该版本接受的 MCP 配置与滚动 V2 文档存在差异，分发说明提供实测版本示例。本次动态模型目录抓取失败，按官方 provider 配置机制显式声明免费模型，没有伪造请求头或绕过服务校验。[官方安装入口](https://opencode.ai/v2/docs/)、[免费模型目录](https://opencode.ai/docs/zen/)、[Provider 配置](https://opencode.ai/v2/docs/providers/)

OpenCode2 日志与独立检查位于 `D:/.garden/distribution-acceptance/opencode2-20260922/`：`opencode2-mcp-final-run.jsonl`、`hbjson-check.json`、`preview-http.json`。它与 Rhino/浏览器验收使用此前 wheel `4dcf54e85c75170f7203de54e433098d988d4471f2fc5c923d2be903515216cb`；后续发行改动为安装维护和 localhost 绑定修复，模型服务和组件二进制未变，修复由三平台 wheel CI 覆盖。

Rhino 证据在 `tests/.artifacts/distribution/native-20260922/grasshopper.json` 和 `installed-components.gh`。测试未修改用户画布，已恢复环境并卸载临时受管组件，专用服务已停止，Garden 和证据保留；没有改变全局 OpenCode2 安装。大体积证据不提交 Git。

## 尚未完成的正式发布

1. 用户登录 PyPI，在账户 Publishing 页配置 pending Trusted Publisher。具体字段已列入[分发说明](distribution.md#build-and-release)。此步骤按用户选择暂缓。
2. 审核 PR 并将通过验收的版本合并、创建匹配的版本标签。GitHub `pypi` 环境已要求 `LoftyTao` 审批，并仅允许 `v*` 标签。
3. 审批对应发布 CI，在 PyPI 核对发布文件哈希，再从全新环境执行固定版本的 PyPI 安装命令。完成这一条后，才可将 ADR 的分发交付标为完成。

模拟引擎、Rhino、Ironbug 按已有边界另行准备。旧源码粘贴画布不会自动改写，迁移方式见分发说明；首版 Flowerpot 原生支持范围仍为 Windows/Rhino 8。
