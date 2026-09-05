# Ladybug Tools MCP

[English](README.md) | [简体中文](README.zh-CN.md)

## 概览

Ladybug Tools MCP 是基于 FastMCP 构建、面向代理应用的 MCP 服务。
用户可以通过自然语言对话调用 Ladybug Tools 的核心能力，完成建模、编辑、查询、模拟和数据可视化等常见工作，无需依赖 CAD 界面。

![OpenCode Honeybee 建模流程](https://raw.githubusercontent.com/LoftyTao/ladybug-tools-mcp/f530e12d9836db518b187639eee4e7644a6a7e9f/resources/remotion/snapshots/videos/opencode-honeybee-modeling-vtkjs-flow-en/opencode-honeybee-modeling-vtkjs-flow-en-latest.gif)

## 目录

- [概览](#概览)
- [适用人群](#适用人群)
- [核心概念](#核心概念)
- [快速开始](#快速开始)
- [Web View 预览模式](#web-view-预览模式)
- [首次使用](#首次使用)
- [工作流示例](#工作流示例)
- [如何贡献](#如何贡献)
- [后续计划](#后续计划)
- [致谢](#致谢)
- [开源许可证](#开源许可证)
- [联系方式](#联系方式)

## 适用人群

Ladybug Tools MCP 最初的目标是将设计或技术概念快速转化为具体成果。
例如，教师在建筑技术课上讲解“什么是特朗布墙”时，学生可以开启 Codex 语音模式；讲解结束时，Codex 已可将这个概念转化为能够检查的模型、文件和图形化工作流成果。

因此，本项目主要面向学生和教师，其次是建筑从业者与资深工程师。
他们可以让代理承担部分繁琐工作，同时保留大多数任务的最终决策权。
对于不熟悉三维软件工作流的用户，Ladybug Tools MCP 也提供了一种体验 Ladybug Tools 生态的方式。

## 核心概念

Ladybug Tools MCP 与在 Rhino / Grasshopper 中使用 Ladybug Tools 的方式有所不同。
了解 MCP、代理、Skill、Token、Garden 和 Flowerpot 等核心概念，有助于更好地使用本项目。

### 模型上下文协议

[模型上下文协议（MCP）](https://modelcontextprotocol.io/docs/getting-started/intro)是连接外部系统与代理应用的开放标准。
Ladybug Tools 通常在 Rhino / Grasshopper 中提供面向用户的交互界面。
Ladybug Tools MCP 则提供一组可由代理通过自然语言调用的工具。
它将 Ladybug Tools Core SDK 的核心能力整理为标准化工具和操作说明，并通过 MCP 提供给代理应用。

### 代理

[代理（Agent）](https://openai.github.io/openai-agents-python/agents/)是配有指令和工具的大语言模型。
Ladybug Tools MCP 通常作为工具集，在代理应用中被调用。

### 代理操作技能

[操作技能（Skills）](https://agentskills.io/home)将提示词与操作经验整理为可复用的说明。
它通过 Markdown 归纳领域知识和工作流，为代理提供“操作手册”，帮助代理更准确地执行用户意图。

### Token

Token 是代理应用计算用量和费用的单位。
不同模型的性能、速度和单价各不相同；为了获得良好的 Ladybug Tools MCP 使用体验，建议在可承受的范围内选择能力和性价比合适的模型。

较长的建模与模拟工作流通常受益于更大的上下文窗口。
实际用量和费用取决于模型、客户端与任务。

### Garden

Garden 是保存和管理 Ladybug Tools MCP 生成内容的本地目录，其中的主要成果通过 Git 进行版本管理。

代理在实际工作中可能执行超出预期的操作，因此本项目的一项重要工作是让代理围绕 Garden 内的内容开展任务。
这是数月开发实践中积累的一项主要经验。

### Flowerpot

Flowerpot 是 Ladybug Tools MCP 与其他交互界面交换信息的中间层。
例如，本项目为 Ladybug Tools 开发的 Flowerpot 组件主要承担生态内的数据交接，帮助用户完成必要的手动操作。

本项目希望用户将更多精力用于与代理交互，因此没有为 Ladybug Tools MCP 另行构建独立的平台界面。
建议使用已有的 Ladybug Tools 基础设施，并通过 Flowerpot 传递数据与信息。

## 快速开始

### 环境要求

使用 Ladybug Tools MCP 前，通常需要准备以下环境：

- Python 3.12
- 符合下方 `v1.2.0` 版本要求的 Ladybug Tools 运行环境
- Git
- uv
- 任意代理应用，例如 [Codex](https://chatgpt.com/codex)、[Claude Code](https://code.claude.com/docs/en/desktop-quickstart)、[Open Code](https://opencode.ai/) 或 [OpenClaw](https://openclaw.ai/)

如果你尚不熟悉代理应用，可以从 [Codex](https://chatgpt.com/codex) 开始。

下表列出了 Ladybug Tools MCP `v1.2.0` 所采用的外部运行环境版本要求。
请按具体工作流安装所需引擎；Ironbug 建模使用项目内的 Python 实现。

Ladybug Tools MCP | Python | Radiance | OpenStudio SDK | EnergyPlus | OpenStudio App | URBANopt CLI | THERM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `v1.2.0` | 3.12 | [5.4 (2023-11-05)](https://github.com/LBNL-ETA/Radiance/releases/tag/rad5R4) | [3.11.0](https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.11.0) | 25.1.0 | [1.11.1](https://github.com/openstudiocoalition/OpenStudioApplication/releases/tag/v1.11.1) | [1.4.0](https://github.com/urbanopt/urbanopt-cli/releases/tag/v1.4.0.rc1) | [8.1.30 beta](https://windows-downloads.lbl.gov/software/therm/THERM8_1_30_SetupFull.exe) |

使用 `LB_get_runtime_config` 检查已安装引擎，并获取缺失运行环境的配置指引。

### 安装指南

如果你不了解 MCP，或希望由代理完成安装，可以将任务交给 [Codex](https://chatgpt.com/codex) 或其他代理应用。

以 Codex 为例：

- 安装 Codex。
- 打开本地工作目录。
- 将本项目链接发给 Codex。
- 输入：

```text
请帮我将这个项目的 MCP 安装并配置到当前工作目录。
```

#### 本地安装命令

在目标工作目录中运行以下命令。
将 `<repo-url>` 替换为本项目的仓库地址，将 `<repo-dir>` 替换为克隆后的目录名称。

Windows PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

macOS / Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

随后在各平台运行：

```bash
git clone <repo-url>
cd <repo-dir>
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
uv pip install -e .
uv run --no-project python -c "import ladybug_tools_mcp; print(ladybug_tools_mcp.__version__)"
```

`requirements.txt` 固定了依赖版本，便于重复安装相同环境。

#### MCP 配置示例

将 `<absolute-repo-path>` 替换为本机仓库的绝对路径，将 `<python-command>` 替换为项目虚拟环境中的 Python 可执行文件路径。

Windows：

```text
<absolute-repo-path>\.venv\Scripts\python.exe
```

macOS / Linux：

```text
<absolute-repo-path>/.venv/bin/python
```

Codex 使用 TOML：

```toml
[mcp_servers.ladybug-tools-mcp]
command = "<python-command>"
args = ["-m", "ladybug_tools_mcp.server"]
cwd = "<absolute-repo-path>"
```

使用 `mcpServers` 配置的 Cursor、OpenCode 或其他代理应用可以采用 JSON：

```json
{
  "mcpServers": {
    "ladybug-tools-mcp": {
      "command": "<python-command>",
      "args": ["-m", "ladybug_tools_mcp.server"],
      "cwd": "<absolute-repo-path>"
    }
  }
}
```

Claude Code 建议通过命令行添加本地标准输入输出 MCP 服务：

```text
claude mcp add ladybug-tools-mcp -- "<python-command>" -m ladybug_tools_mcp.server
```

如果需要项目级共享配置，可以使用：

```text
claude mcp add ladybug-tools-mcp --scope project -- "<python-command>" -m ladybug_tools_mcp.server
```

Claude Code 的项目级 `.mcp.json` 文件也使用 `mcpServers` 结构：

```json
{
  "mcpServers": {
    "ladybug-tools-mcp": {
      "command": "<python-command>",
      "args": ["-m", "ladybug_tools_mcp.server"],
      "env": {}
    }
  }
}
```

OpenClaw 在其 MCP 客户端配置中使用 `mcp.servers`：

```json
{
  "mcp": {
    "servers": {
      "ladybug-tools-mcp": {
        "command": "<python-command>",
        "args": ["-m", "ladybug_tools_mcp.server"],
        "cwd": "<absolute-repo-path>"
      }
    }
  }
}
```

配置完成后，重启代理应用并确认 MCP 服务已连接。

#### Grasshopper 组件路径

如需与 Grasshopper 协同，请使用[开发仓库中的组件源码](https://github.com/LoftyTao/rec-ladybug-tools-mcp/tree/main/src/grasshopper_components)。
本小节中的 `<absolute-repo-path>` 指开发仓库的本地路径，Grasshopper 需要能够找到该目录。

建议先设置环境变量。

Windows PowerShell：

```powershell
[Environment]::SetEnvironmentVariable("LADYBUG_TOOLS_MCP_ROOT", "<absolute-repo-path>", "User")
```

macOS / Linux：

```bash
export LADYBUG_TOOLS_MCP_ROOT="<absolute-repo-path>"
```

如果需要将组件脚本复制到另一台机器，或单独交付组件，还应检查并修改各个 `FP *.py` 文件顶部附近的 `_DEVELOPMENT_SRC_ROOT`。
在 Windows 上，该路径应指向：

```text
<absolute-repo-path>\src
```

在 macOS / Linux 上，应指向：

```text
<absolute-repo-path>/src
```

组件启动时会将该路径加入 `sys.path`，以加载 `flowerpot.runtime` 和项目内的 Grasshopper 协同代码。

## Web View 预览模式

Web View 模式为建模过程提供本地 vtk.js 预览。
代理创建或编辑 Honeybee、Dragonfly、Fairyfly 或 VisualizationSet 成果时，宿主应用可以显示当前 Garden 的预览。

预览服务在本地 `127.0.0.1` 运行。
在客户端的浏览器或侧边栏中打开返回的网址，即可查看 Garden 的变化。

### 开启

建模或编辑前，让代理开启 Web View 模式：

```text
请为这个 Garden 开启 Web View 模式，然后创建或编辑 Honeybee 模型。
```

代理通过 MCP 代码模式调用：

```text
GD_web_view_start_mode(garden_root, name="...")
```

开启后，服务会在 Garden 中创建本地预览会话，并返回 `viewer.url`，例如：

```text
http://127.0.0.1:3127
```

打开返回的 `viewer.url` 即可显示预览。

### 关闭

让代理停止 Web View 模式，或调用：

```text
GD_web_view_stop_mode(garden_root)
```

这会停止后续自动预览，并关闭已经启动的对应本地预览服务。
`tmp/web_view/` 中的预览历史会保留。

### 与普通模式的区别

普通模式下，建模工具将文件写入 Garden，并返回精简的目标引用、摘要和回执。
服务不会启动预览窗口，也不会在每次编辑后自动导出预览文件。

Web View 模式下，Honeybee、Dragonfly、Fairyfly 和 VisualizationSet 的主要操作会自动导出由会话管理的 `.vtkjs` 预览，保存于：

```text
<garden>/tmp/web_view/previews/
```

预览页面会轮询 Garden 的会话状态，并自动加载最新的 `.vtkjs` 文件，无需手动刷新。
这些自动预览用于当前会话，不属于用户明确要求导出的正式成果。
如果需要长期保存和重复使用的成果，仍应让代理通过 `LB_set_to_vtkjs` 导出可视化集。

本地预览服务使用明确指定的端口。
如果请求的端口已被占用，启动会明确报错，不会自动切换到其他端口或让浏览器继续显示旧 Garden。

## 首次使用

在代理应用中配置好 MCP 服务后，新建一个任务，并让代理使用 Ladybug Tools MCP。
在 Codex 中，可以按照上方 TOML 示例配置 `~/.codex/config.toml`，重启后直接描述 Garden 或建模任务。

如果宿主支持 Skill，可通过 `/` 调用 `ladybug-tools-mcp-use`，再输入 `HI , Ladybug Tools !`，启动三类主要使用方向的引导流程。
完成引导后，即可按照自己的意图开始构建。

![首次使用引导](https://raw.githubusercontent.com/LoftyTao/ladybug-tools-mcp/f530e12d9836db518b187639eee4e7644a6a7e9f/resources/remotion/snapshots/videos/opencode-onboarding-flows/welcome-fixed-3-options-en-latest.gif)

通常，代理应用会根据 Skill 输出引导内容；实际表现也取决于宿主应用的指令和语言模型能力。
建议在可承受的范围内使用能力较强的模型，以获得更好的工具使用体验。

## 工作流示例

在交叉测试中，代理应用已完成下列类型的工作。
这些工作流的稳定性和 Token 用量相对稳定，可以作为开始学习的参考。

### 从空白项目建立小型模型

- 创建 Garden。
- 创建 Honeybee 模型。
- 创建一至两个房间。
- 在外墙上添加窗、门和遮阳。
- 检查模型是否缺面、相邻关系是否完整，以及边界条件是否正确。

### 继续编辑已有模型

- 找到指定的房间、墙、窗或门。
- 修改窗的位置、尺寸和构造。
- 添加低传热系数窗、重质墙体构造、人员负荷和设备负荷。
- 为房间赋予功能类型、设定温度和简单暖通系统。
- 编辑后重新校验模型。

### 建筑性能模拟

- 检索并下载指定城市的 EPW 气象文件。
- 将气象文件保存到 Garden。
- 启动能耗模拟。
- 读取单位面积能耗、错误信息和部分逐时结果。
- 将结果导出为月度图表、逐时图表或 HTML 页面。

### 准备可复用的能耗资源

- 创建时间表、房间功能类型、构造集、设定温度和暖通模板。
- 将资源保存到 Garden 属性库。
- 在后续模型中检索并复用这些资源。
- 对于不完整的来源，只记录能够确定的信息，不推测材料分层或窗参数。

### 使用 Ironbug 构建自定义暖通系统

- 创建盘管、风机、水泵、锅炉、冷机、末端、冷热水回路、空气回路、设定点管理器和输出请求等 Ironbug 详细暖通对象。
- 根据源码支持的构件，组装整体式空调及热泵（PTAC、PTHP）、风机盘管（FCU）、独立新风系统（DOAS）、变风量系统（VAV）、多联机（VRF）、锅炉再热、冷水机房和冷却水回路等系统。
- 将 Ironbug 热区关联到 Honeybee 或 Dragonfly 房间，应用详细暖通模型后，再运行标准能耗模拟工作流。
- 当暖通模板不足以表达需求，而任务需要明确回路拓扑、子构件以及 OpenStudio / EnergyPlus 设备属性时，使用 Ironbug 工作流。

### 完成基础 Radiance 工作

- 创建天空、WEA 文件、天空矩阵、传感器网格和视图。
- 为模型对象赋予 Radiance 材质修饰器。
- 启动网格或视图模拟。
- 读取 HDR、伪彩色图、GIF 或年度采光指标。
- 将结果转化为可检查的可视化集。

### 连接 Grasshopper 与代理

- 使用 Grasshopper 中的 Flowerpot 组件交接当前模型或项目上下文。
- 让代理在 Garden 中继续建模、编辑、保存和校验。
- 让 Grasshopper 继续承担手动选择、预览和必要的手工操作。
- 这种方式适合在界面中处理几何，并由代理负责整理和连续调用工具的工作流。

### 保存与恢复项目状态

- 在重要操作前创建 Garden 版本。
- 尝试修改模型或模拟资源。
- 如果结果不符合预期，恢复到先前版本。
- 恢复后继续导出 HTML、SVG 和其他检查成果。

## 如何贡献

本项目主要采用代理辅助开发，也欢迎使用代理应用完成的贡献。
为保持项目范围清晰，贡献时请遵循以下原则：

- [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation) 是本项目所有 MCP 工具的核心。
  如果希望新增的能力不属于 SDK 范围，更适合直接向 Ladybug Tools 项目贡献实现。
- 新工具开发应先通过 GitHub Issue 公开讨论，并由人来主导讨论和开发计划。
- 只编写解决当前问题的代码。
  如果 AI 审查提出的问题尚未在正常使用中出现，不必立即处理。
- 仅在确有需要时增加工具和对象，避免无必要的扩展。
- 如果认同这些原则，欢迎加入由社区驱动的维护团队。

## 后续计划

以下是后续开发的主要方向。
在收到更广泛的用户反馈前，项目将继续围绕这些方向推进。

- [x] Dragonfly 模型创建和编辑工具
- [x] URBANopt 支持
- [ ] 更多可视化集前处理与后处理能力
- [ ] 扩充 Ironbug 能耗验收案例，覆盖更多自定义暖通拓扑
- [ ] 支持代理直接协作的 Web View 与模型编辑工具
- [ ] 能够展示全部流程和步骤的演示模式
- [ ] 云服务支持
- [ ] 其他后续方向

## 致谢

特别感谢 [Ladybug Tools 社区](https://discourse.ladybug.tools/)和 [Ladybug Tools 团队](https://www.ladybug.tools/about.html#team)：

- **Mostapha** [提高了 Pydantic 兼容工作的优先级](https://discourse.ladybug.tools/t/upgrade-to-pydantic-2-0/36437/9)，大幅降低了本项目的开发难度。
- **Chris** 帮助 [Visualization Set](https://discourse.ladybug.tools/t/bug-of-dumpvisset-or-incomplete-known-issues/39972) 的 `.svg` 格式成为 MCP 工作流的主要模型可视化方案，使我们能够在不依赖 CAD 界面的情况下完整检查构建成果。

本项目的实现核心仍是 [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation)，这是 Ladybug Tools 团队多年开发的成果。

## 开源许可证

Ladybug Tools MCP 采用 GNU 通用公共许可证第三版（GPL v3），与 Ladybug Tools 项目的开源许可证一致。

## 联系方式

你可以通过以下方式联系我：

- 邮箱：`loftytao@foxmail.com`
- 微信：`LoftyTao`

如果你愿意提供 Codex 或 Claude Code 的使用额度或订阅支持，我也会非常感谢。
