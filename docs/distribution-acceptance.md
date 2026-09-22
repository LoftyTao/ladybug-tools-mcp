# 分发实现验收记录

更新日期：2026-09-22。目标版本：1.2.1。工作分支：`codex/distribution-installer`。

交付仍在进行：`accepted` 只表示 ADR 决策已确认；正式发布和三平台 CI 通过之前，不将分发工作标为完成。

## 可交付产物

- wheel：`dist/ladybug_tools_mcp-1.2.1-py3-none-any.whl`
- 源码包：`dist/ladybug_tools_mcp-1.2.1.tar.gz`
- wheel SHA-256：`4dcf54e85c75170f7203de54e433098d988d4471f2fc5c923d2be903515216cb`
- wheel 包含 110 个 Skill 文件、6 个 `.ghuser`、组件清单和 27 个 EPW；`twine check` 对 wheel 和源码包均通过。

安装器提供统一终端向导、固定版本持久运行环境、可选 Flowerpot、Codex 配置合并、Skills 部署、生成配置、冲突备份、重装及卸载。Garden 独立于运行环境；发行依赖图完整固定。用户端使用 wheel，无需构建 MCP 或组件。见[安装和发布说明](distribution.md)。

## 已通过

| 检查 | 实际结果 |
| --- | --- |
| Windows 独立 wheel 安装 | CPython 3.12.13、uv 0.11.15；无 editable 安装，启动使用 `-I`，工作目录为独立测试目录。 |
| 配置与维护 | 中文/空格路径、只生成配置、自动配置、重复安装、同名冲突拒绝、显式替换及备份、保留无关设置、卸载保留修改后的 Skill 和全部 Garden 文件。 |
| MCP 基线 | 正式 stdio 连接；Code Mode 发现及执行、Skill 资源读取、天气目录及完整 EPW 读取、Garden 创建、房间建模、有效性验证、磁盘模型几何复核。 |
| localhost 预览 | 返回 localhost URL；HTTP 页面和 `/api/state` 可读，场景包含实际模型。未更改现有 vtk.js CDN 依赖。 |
| Codex 自然语言流程 | 原生 CLI 读取 Skill，通过已安装 MCP 创建、移动、查询、验证并保存 Garden 版本。独立文件复核：1 个房间，面积 30 m²、体积 90 m³，X=2–8、Y=0–5、Z=0–3 m；版本 `64ed4fb`，无未保存变更。 |
| Grasshopper 原生流程 | 2026-09-22 在新的 Rhino 8 会话（PID 15904）中先安装组件，再正常启动 Grasshopper 1；六个组件由原生目录扫描自动发现，搜索结果路径全部指向受管安装目录。通过 ComponentServer 搜索结果创建实例，核对全部端口，完成 Garden 创建、列表选择及 Honeybee 模型读取；面积 30 m²、体积 90 m³；保存 `.gh` 后重新打开并重算通过。未手工注入组件索引。之前的中文路径原生测试亦通过。 |
| 现有 Flowerpot 回归 | 23 项 pytest 检查通过。 |
| 元数据 | wheel 和源码包均通过 `twine check`。 |

最终 wheel 执行了 `tests/deterministic/validate_distribution.py`。原生 `tests/deterministic/validate_grasshopper_distribution.py` 验收后，仅追加了安装器生成 Codex `required=true` 配置的设置，Flowerpot 运行代码与组件资产未改变。Codex 自然语言验收先于最后的 Flowerpot 编码/布尔默认值修正；之后的最终 wheel 已完成确定性协议和原生 Grasshopper 复验，MCP 建模入口未改变。

原生测试中发现并修正了两个实际问题：IronPython/CPython 之间的非 ASCII JSON 往返导致中文路径损坏；预制 Honeybee Link 的可选 `_write` 没有默认数据，仍被 Ladybug 的输入检查拦截。当前使用 ASCII JSON 传输 Unicode 转义，并为可选布尔端口设置 False。另保留同一 Rhino 会话的 worker，避免组件 reload 重复创建进程。

测试没有修改用户当前画布；原有画布与环境已恢复，临时运行环境、管理的组件文件和 Codex 测试 profile 已卸载，Garden 与证据保留在本地。保存的测试画布位于 `tests/.artifacts/distribution/native/installed-components.gh`；确定性日志在 `tests/.artifacts/distribution/验收 profile 4/`。这些大体积运行产物不加入 Git。

## 限制和发布门槛

- Linux x86_64 与 macOS Apple Silicon 已通过 Python 3.12 的依赖 wheel 解析检查。当前没有完成两平台原生运行；已配置三平台 CI，必须等其实际通过后发布。
- OpenCode2 已实际尝试 `opencode/mimo-v2.5-free`，并核对官方免费目录。已安装的 `0.0.0-beta-18721` 与临时下载的 `0.0.0-beta-19271` 均被服务端以 HTTP 426 拒绝：`OpenCode 1.18.0 or newer is required to use the free tier`。归类为客户端/服务兼容限制，未切换付费模型，也未将其记为 MCP 失败。[免费模型状态](https://opencode.ai/docs/zen/)
- Codex 非交互测试使用独立 profile，仅为本测试服务器的 `execute` 配置预先授权。产品安装器保留宿主原有审批策略。第一次未授权的运行被宿主拦截，授权后的流程完成。
- Grasshopper 正常启动自动发现条件已于 2026-09-22 补齐，证据在 `tests/.artifacts/distribution/native-20260922/grasshopper.json` 和同目录保存的画布。测试使用新会话，没有关闭用户 Rhino 或修改其画布。旧源码粘贴画布不会被安装器自动改写，其迁移方式见分发说明。
- 尚未公开发布。PyPI 项目查询返回 404；需维护者配置 Trusted Publisher 和 GitHub `pypi` 环境，确认上述原生/Agent 验收，再批准版本标签对应的发布。CI 只发布它实际测试过的 wheel，不重新构建。
