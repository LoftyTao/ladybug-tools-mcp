---
status: accepted
---

# 通过可配置安装器与 uv 分发本地 MCP

当前使用方式要求用户克隆源码、创建项目环境并分别安装依赖。采用 PyPI 分发与统一安装向导，是为了将这些准备工作移到发布流程和安装器中，同时沿用项目已有的 Python 运行栈。

用户通过同一个 Python 终端交互向导准备本地 MCP，兼顾 Windows、Linux 和 macOS。uv 负责准备 Python 和项目依赖，仅 uv 的首次安装命令按平台区分；后续由客户端启动服务，用户无需克隆源码、手工创建虚拟环境或逐项安装依赖。首次下载与 MCP 握手分开，便于查看安装进度和错误，避免冷启动下载消耗客户端的握手等待时间。

首版优先完成 Windows 验收，验收范围为 MCP 接入、Garden 创建、建模和本地预览；模拟引擎按具体工作流另行准备。Agent 测试使用 OpenCode2 的可用免费模型进行快速检查，以 Codex 完成完整验收；其他客户端提供标准 stdio 配置示例。沿用现有行为：无 Git 仍可创建 Garden，版本保存与恢复才要求用户安装 Git。

正式安装渠道采用 PyPI；MCP 使用固定的已发布版本，由用户主动运行所选版本的安装器升级。GitHub 继续承载源码和发布说明。

MCP 分发包携带现有操作 Skills。Flowerpot 集成作为可选安装项，当前目标平台为 Grasshopper；用户选择安装后，组件必须能在 Grasshopper 中搜索并拖入画布，无需手工导入脚本。必要时提示用户重启 Rhino/Grasshopper。Web View 保持当前 localhost 预览方式，包括现有的 vtk.js CDN 加载行为。

安装器自动配置 Codex 并将随包 Skills 安装到其可识别的本地技能位置，保留并备份现有配置，同时提供仅生成配置的选项。

向导选项为：确认目标版本、程序运行环境目录、默认 Garden 根目录、自动配置 Codex 或仅生成配置，以及是否安装 Flowerpot 集成（Grasshopper）。Garden 根目录由用户选择，建议默认位于用户目录下的 `LadybugTools/Gardens`，与程序和 uv 缓存分开；已有 Garden 继续按原路径使用。默认按当前用户安装，Codex 自动配置写入用户级配置；Flowerpot 默认不选，选中后检测兼容的 Rhino/Grasshopper 并显示组件安装位置。

此边界将基础使用与各模拟工作流所需的外部运行环境分开，避免首次接入就要求用户准备所有模拟引擎。完整方案及分发评估补强已确认，进入实现。

实现时需补齐包的运行依赖和 MCP 命令入口，将现有 MCP 技能资源随包交付，并让数据路径独立于源码目录和运行环境。验收应从没有源码 checkout、没有可编辑安装的独立环境出发，验证技能与天气资源可读、Garden 创建、模型创建及编辑、本地预览；Garden 成果必须保存在运行环境之外，且升级或清理运行环境后仍可继续打开。

Flowerpot 由维护者预先生成可分发的 Grasshopper 用户对象，安装器部署组件产物并配置其使用已安装的运行环境，消除对开发仓库和仓库内 `.venv` 的依赖。此次分发扩展此前首发仅交付源码组件的边界；原有交接语义、安全校验及版本兼容约束继续适用。

## 安装入口

以下命令在正式发布后可用；`<版本>` 指定要安装的发行版本。

```text
uvx --isolated --python 3.12 --prerelease allow ladybug-tools-mcp@<版本> install
```

向导确认选项后安装持久运行环境，配置客户端及技能，并在用户选择时安装 Flowerpot 组件。安装结果应显示所用版本、程序和 Garden 位置、客户端配置结果及可选组件状态。已有配置与技能发生同名冲突时，应保留用户内容并让用户选择处理方式；安装失败时不得删除 Garden 或破坏原有客户端配置。

## 交付与验收

- 发布 wheel 和配套版本说明，包内包含运行所需的技能、天气及组件资源；用户端不构建 MCP 或 Grasshopper 组件。
- 三平台检查安装向导、配置生成和 MCP 启动；OpenCode2 使用免费模型快速检查 Agent 交互，首版完整交互验收仍优先 Windows/Codex。其他客户端提供标准 stdio 配置示例。
- Flowerpot 首版完整验收沿用当前 Windows/Rhino 8 的支持矩阵。六个组件都必须可搜索、可拖入、端口正确；通过已安装的运行环境实际完成 Garden 创建、选择和 Honeybee 交接。尚未验证的平台或 Rhino 版本不得显示为已支持。
- 从独立安装环境验证 MCP 接入、技能资源、Garden 创建、模型创建及编辑、localhost 预览，并确认不依赖开发机源码路径。
- 验证重复安装和主动升级保留已有客户端配置、用户修改的技能及 Garden 成果；缺少 Git 或模拟引擎时，按已有功能边界提示，不阻断基础使用。

安装器不随包安装 Rhino、Ironbug 或模拟引擎；保留现有模拟工具，所需外部运行环境由用户按工作流准备。

## Agent 测试环境

| 环境 | 用途 |
| --- | --- |
| OpenCode2 | 使用实际可用的免费模型，以纯自然语言通过正式 MCP 工具完成快速检查，覆盖 MCP 接入、工具发现与调用、Skills 读取、Garden、小模型及 localhost 预览。 |
| Codex | 完整用户流程和发布验收，并独立检查快速测试产生的实际成果。 |

两种环境连接同一待发布版本的已安装 MCP，使用专用测试目录与 Garden，不借用源码 checkout 的可编辑安装。OpenCode2 直接使用原生 CLI 的模型列举、MCP 检查与非交互运行能力；按实际可用模型显式指定 `--model`，通过 `--format json` 保存原生执行记录，并记录客户端版本、模型标识、MCP 版本与产物位置。

每次运行前核对免费模型的可用性和费用状态，不将某个型号永久视为免费；无可用免费模型或遇到配额、限流时记录为测试环境不可用，不自动切换到付费模型，也不据此判定 MCP 失败。测试协议参考 [OpenCode V2 CLI](https://opencode.ai/v2/docs/cli/commands/)，免费模型状态以 [OpenCode Zen](https://opencode.ai/docs/zen/) 与当次可用列表为准。

实现所依据的原生机制：[uv 工具环境](https://docs.astral.sh/uv/guides/tools/)、[Grasshopper 用户对象保存 API](https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_Kernel_GH_UserObject_SaveToFile.htm)。

## 已确认的分发评估补充

[官方机制与实现风险评估](../research/mcp-distribution-patterns.md) 支持保留现有主路线，并建议在实现前补齐以下约束：

- 向导的启动环境与持久运行环境分开；Flowerpot 连接持久环境，程序升级不在正在使用的目标环境内自我替换。环境和依赖管理使用 uv 原生能力。
- 固定发行版本之外，还需控制并验证实际依赖解析结果；支持矩阵明确到系统、架构、Python 和功能组合。
- 记录安装器管理的配置和复制资产，定义重复安装、升级失败重试及卸载行为，保留用户修改和 Garden。
- Flowerpot 的新组件搜索/拖入与旧画布兼容分别验收；MCP、Skills、组件资产使用同一发行版本。
- 增加不依赖模型的安装、资源与 MCP 协议/工具检查作为确定性基线；OpenCode2 与 Codex 检查真实 Agent 使用体验。向导支持参数化、无人值守验证。
- 从构建出的 wheel 验证资源、启动和功能，发布同一被测产物；保留现有 localhost/CDN 行为并明确网络要求。宿主插件、MCPB 和 Registry 为可按需增加的入口。

安装、恢复及发布机制见[分发说明](../distribution.md)。本 ADR 的 `accepted` 表示方案已确认，不表示交付完成。交付状态和剩余条件统一记录在[验收记录](../distribution-acceptance.md)；三平台实际运行、Grasshopper 正常启动发现和正式安装渠道均须有证据，依赖解析成功不能替代原生验收。
