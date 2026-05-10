# Ladybug Tools MCP

![Ladybug Tools MCP Header](resources/GitHub-Obsidian-header-flowerpot-garden.png)

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文（ZH）</a>
</p>

## 概述

Ladybug Tools MCP 是由 FastMCP 创建的，为智能体 (Agent) 应用开发的本地模型上下文协议 (MCP) 服务，用户可以通过自然语言对话的方式使用 Ladybug Tools 中的核心功能，包括但不限于建模、编辑、查询、模拟以及数据可视化等常见应用，并且可以无需 CAD 界面的介入。

>你可以理解为建筑环境设计领域的甲方模拟器。

**需要注意，这个项目由于没有任何的资助，因此可能处于长期的实验性阶段，请谨慎的使用。**

这里有个比较大的演示图片，需要等待一下。

![Opencode Honeybee Modeling Flow](resources/remotion/snapshots/videos/opencode-honeybee-modeling-vtkjs-flow/opencode-honeybee-modeling-vtkjs-flow-latest.gif)

这个项目完全由 Codex 进行构建，包括源码和所有的演示图像。编码模型使用  GPT 5.4/5.5 进行项目开发，测试环节使用 Minimax 2.7 做点状和局部面状的工具调用测试，完整的功能交叉测试使用 GPT 5.4 Mini，总体成本大概是每月 50 亿词元。

## 目录

- [概述](#概述)
- [用户群体](#用户群体)
- [基本概念](#基本概念)
- [快速开始](#快速开始)
- [初次使用](#初次使用)
- [工作流程示例](#工作流程示例)
- [主要工具](#主要工具)
- [如何贡献](#如何贡献)
- [待办事项](#待办事项)
- [致谢](#致谢)
- [开源协议](#开源协议)
- [联系方式](#联系方式)

## 用户群体

Ladybug Tools MCP 的开发初衷主要是为了快速的让设计或技术概念成型，例如教授在建筑技术课程中讲述“什么是特朗勃墙”时，学生可以在台下打开 Codex 的语音模式，Codex 则能在教授讲述完毕时就自动的将这些概念转变为视觉可查看的模型和文件，并且伴有图形流程。

所以，开发主要面向的用户群体是学生与老师，接着才是建筑从业者和资深工程师们，他们可能会让智能体接管一部分繁琐的工作，但绝大多数工作去自主选择。对于不了解三维软件应用的用户来说，也可以通过 Ladybug Tools MCP 来感受 Ladybug Tools 的生态魅力。

## 基本概念

Ladybug Tools MCP 不同于 Rhino / Grasshopper 中使用的 Ladybug Tools ，为了使用好它您需要了解本项目的几个核心概念，例如模型上下文协议、智能体、技能、词元、花园以及花盆等。
### 模型上下文协议

**[模型上下文协议 (MCP,Model Context Protocol)](https://modelcontextprotocol.io/docs/getting-started/intro)** 是用于将外部系统连接到智能体应用的开源标准。对于绝大多数用户而言，Ladybug Tools 是为人类交互所在 Rhino / Grasshopper 创建的用户界面。而 Ladybug Tools MCP 是智能体可通过自然语言调用的工具箱。Ladybug Tools MCP 将 Ladybug Tools Core SDK 的核心能力封装成了一套标准化的工具以及使用说明，通过 MCP 的方式供智能体应用调用。

### 智能体

**[智能体 (Agent)](https://openai.github.io/openai-agents-python/agents/)** 是一个具有指令和工具集的大语言模型(LLMs)，Ladybug Tools MCP 通常以工具的形式在智能体应用中进行调用。

### 智能体技能

[智能体技能 (Skills)](https://agentskills.io/home) 是提示词工程的一种落地实践，通过 Markdown 格式将专业知识和工作流程总结成“说明书”展示给智能体，让智能体能够遵循这些技能来执行您的意图。

### 词元

**词元 (Tokens)** 是智能体应用中计算成本的一个单位，不同性能、速度的大语言模型的词元定价均不一致，但是我建议您选择您能力范围内最好且性价比最高的模型来体验 Ladybug Tools MCP。

对于 Ladybug Tools 的实践应用来说，通常至少要具备 258K 的背景上下文窗口，和一个足够用量的 Coding Plan 订阅。由于成本原因，我不能对广泛的订阅模型进行测试，但对于 GPT Plus 用户而言，应该能够在 Codex 中每 5 小时执行 3~4 个复杂模型的创建和编辑工作。

### 花园

**花园 (Garden)** 是存储和管理 Ladybug Tools MCP 所有生成内容的本地路径，主要产物内容通过 Git 进行管理。

>**花园是虫子们栖息和自由活动的地方，不会受到人类的打扰**

由于智能体应用在实际工作中容易干出超出预期的事情，我们做了很多的工作将它的注意力被约束在花园中，这是数月开发实践的主要成功经验之一。
### 花盆

**花盆 (Flowerpot)** 是 Ladybug Tools MCP 与其他非智能体界面进行信息传输的**中间层**，例如 我们为 Ladybug Tools 开发的 **Flowerpot** 组件只是利用生态的中转插件，意在让用户执行必要的手动工作。

>**通过花盆将花园的局部生态移植到任何地方。**

由于我们希望用户拥有足够多的注意力在智能体上进行交互，而非重新投入到手工业制造的环节当中，所以我们并没有为 Ladybug Tools MCP 创建各种平台的交互界面，而是推荐您自行搭建或善用各种 Ladybug Tools 的基础设施，然后通过**花盆**进行数据和信息的传递。

## 快速开始

### 先决条件

在开始使用 Ladybug Tools 之前，我们需要对一些系统前置项内容进行配置，一般至少要包含如下内容：

- Python 3.12
- Ladybug Tools 1.10*
- Git
- uv
- 任意智能体应用，例如 [Codex](https://chatgpt.com/codex) , [Cluade Code](https://code.claude.com/docs/en/desktop-quickstart) , [Open Code](https://opencode.ai/) 以及 [OpenClaw](https://openclaw.ai/) 等。

如果您并不了解什么是智能体应用，那么我非常乐意推荐您使用 [Codex](https://chatgpt.com/codex)。

注意: Ladybug Tools 是一个完整的生态，并且还在积极、持续的更新，因此这个先决条件会随动，实际情况您需要参考 [Ladybug Tools 兼容性矩阵](https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix)。
### 安装指南

如果你完全不知道什么是 MCP，也没有很好的能力去做手动构建，那请放心的把这个工作交给 [Codex](https://chatgpt.com/codex)或者其他智能体应用吧！

以 Codex 为例，你只需要：

- 安装 Codex。
- 打开一个本地工作区。
- 把本项目链接发送给 Codex。
- 对它说：
 ```
 帮我把这个项目的 MCP 安装并配置到这个项目工作区中。
 ```
- 刷一会短视频，累了回来看看的时候，一切都会准备就绪。

#### Codex 插件安装

这个仓库也已经附带了一个本地 Codex 插件包。Codex 不是只读取 `.codex-plugin/plugin.json` 就直接安装插件，而是通过 marketplace 文件发现插件；本仓库已经把这两部分都准备好了：

- `.agents/plugins/marketplace.json`
- `plugins/ladybug-tools-mcp/.codex-plugin/plugin.json`

在 Codex 中安装这个插件的步骤如下：

1. 先将本仓库克隆到本地。
2. 将仓库根目录注册为本地 Codex marketplace：

```bash
codex plugin marketplace add <absolute-repo-path>
```

3. 在 Codex App 里打开 Plugins 侧栏，找到 `Ladybug Tools MCP`，然后安装或启用它。
4. 安装完成后，或后续插件文件有改动时，重启一次 Codex，让它重新载入本地已安装副本。

Codex 会把本地插件安装到 `~/.codex/plugins/cache/<marketplace-name>/<plugin-name>/local/`，并把插件开关状态记录在 `~/.codex/config.toml` 中。更完整的打包与安装规则，可以参考官方 [Codex 插件构建文档](https://developers.openai.com/codex/plugins/build)。

#### 使用 Codex 插件

安装完成后，请在 Codex 里新开一个线程。随后你可以用这两种方式使用插件：

1. 在输入框中键入 `@`，选择 `Ladybug Tools MCP`，然后直接描述任务。
2. 直接描述任务，让 Codex 自动选择合适的已安装插件。

如果你希望明确指定就用这个插件，就使用 `@Ladybug Tools MCP`。例如：

```text
@Ladybug Tools MCP Create a new Garden for this project and build a simple Honeybee room with south-facing windows.
```

```text
@Ladybug Tools MCP Search EPW data for Shanghai, download the weather file into my Garden, and start an energy simulation.
```

根据官方 Codex 插件文档，插件安装完成后，应当新开线程，然后要么直接描述目标，要么通过 `@` 显式调用某个插件。参考：[Plugins – Codex](https://developers.openai.com/codex/plugins)。

接下来的内容是给智能体应用看的：

#### 本地安装命令

请在目标工作区中执行以下命令。`<repo-url>` 替换为本项目仓库地址，`<repo-dir>` 替换为克隆后的目录名。

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

随后在所有系统中执行：

```bash
git clone <repo-url>
cd <repo-dir>
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
uv pip install -e .
uv run python -c "import ladybug_tools_mcp; print(ladybug_tools_mcp.__version__)"
```

#### MCP 配置示例

请将 `<absolute-repo-path>` 替换为本项目在本机的绝对路径，将 `<python-command>` 替换为本项目虚拟环境中的 Python。

Windows:

```text
<absolute-repo-path>\\.venv\\Scripts\\python.exe
```

macOS / Linux:

```text
<absolute-repo-path>/.venv/bin/python
```

Codex 使用 TOML 配置：

```toml
[mcp_servers.ladybug-tools-mcp]
command = "<python-command>"
args = ["-m", "ladybug_tools_mcp.server"]
cwd = "<absolute-repo-path>"
```

Cursor、OpenCode 或其他使用 `mcpServers` 的智能体应用，可以使用 JSON 配置：

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

Claude Code 推荐通过 CLI 添加本地 stdio MCP：

```text
claude mcp add ladybug-tools-mcp -- "<python-command>" -m ladybug_tools_mcp.server
```

如果需要项目级共享配置，可以使用：

```text
claude mcp add ladybug-tools-mcp --scope project -- "<python-command>" -m ladybug_tools_mcp.server
```

Claude Code 项目级 `.mcp.json` 文件也使用 `mcpServers` 结构：

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

OpenClaw 的 MCP 客户端注册表使用 `mcp.servers`：

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

配置完成后，重启智能体应用，并确认 MCP 是否已经连接。

#### Grasshopper 组件路径

如果用户需要使用 `src/grasshopper_components/` 中的 GHPython 组件，安装配置时还需要让 Grasshopper 能够找到本项目源码。

优先设置环境变量：

Windows PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("LADYBUG_TOOLS_MCP_ROOT", "<absolute-repo-path>", "User")
```

macOS / Linux:

```bash
export LADYBUG_TOOLS_MCP_ROOT="<absolute-repo-path>"
```

如果需要把组件脚本复制到其他机器或独立交付，请同时检查并修改每个 `FP *.py` 文件顶部的 `_DEVELOPMENT_SRC_ROOT`。Windows 指向：

```text
<absolute-repo-path>\src
```

macOS / Linux 指向：

```text
<absolute-repo-path>/src
```

这些组件会在启动时把该路径加入 `sys.path`，用于加载 `flowerpot.runtime` 和项目内的 Grasshopper 协同代码。

## 初次使用

如果您安装的是 `Ladybug Tools MCP` Codex 插件，那么最直接的首次使用方式就是通过 `@` 显式调用这个插件。

### 在 Codex 中使用 `@Ladybug Tools MCP`

- 在 Codex 中新开一个线程。
- 输入 `@`，然后选择 `Ladybug Tools MCP`。
- 直接描述任务，或者让它先帮您创建 / 继续一个 Garden。

例如：

```text
@Ladybug Tools MCP Create a new Garden for this project and build a simple Honeybee room with south-facing windows.
```

```text
@Ladybug Tools MCP Continue my existing Garden and search EPW data for Shanghai, then download the weather file.
```

如果您不是走 Codex 插件这条路径，也仍然可以在 Ladybug Tools MCP 启用后，通过 `/` 触发 `ladybug-tools-mcp-use` 技能，再输入 `你好，Ladybug Tools！` 来激活我们提供的三种主要使用意图的引导流程；在引导结束之后，您就可以开始进行对应的任务构建。

![Welcome Flow](resources/remotion/snapshots/videos/opencode-onboarding-flows/welcome-fixed-3-options-latest.gif)

一般情况下，智能体应用会根据我们 Skills 的引导流程要求输出引导模板，但实际效果取决于智能体应用的指令集和大语言模型的基础能力，我强烈建议您使用能力范围内最好的模型以更好的使用我们的工具。

## 工作流程示例

您一开始使用时有可能会不知所措，这是正常的，不要放弃！

在我们的交叉测试集中，我们成功的让智能体应用完成了以下覆盖的内容，这些内容的稳定性和词元消耗已经趋于稳定，我认为您的学习可以从这里开始。

### 从空白项目开始建一个小模型

  - 创建一个新的 Garden。
  - 创建 Honeybee Model。
  - 创建一到两个 Room。
  - 给外墙添加窗、门和遮阳。
  - 检查模型是否有缺面、错连、边界条件错误等问题。

### 在已有模型上继续编辑

  - 找到指定房间、墙面、窗或门。
  - 修改窗的位置、尺寸和构造。
  - 添加低传热窗、厚重墙体、房间人员和设备负荷。
  - 给房间设置程序、温控和简单空调系统。
  - 编辑完成后重新检查模型。

### 建筑性能模拟流程

  - 搜索并下载指定城市的 EPW Weather File。
  - 把天气文件保存在 Garden 中。
  - 启动 Energy 模拟。
  - 读取 EUI、错误信息和部分小时结果。
  - 把结果导出成月度图、小时图或 HTML 页面。

### 准备可复用的 Energy 资源

  - 创建 Schedule、Program Type、Construction Set、Setpoint 和 HVAC Template。
  - 保存到 Garden Properties Library。
  - 在后续模型中搜索并复用这些资源。
  - 对资料不完整的来源，只记录能够确定的内容，不编造材料层或窗参数。

### 做基础 Radiance 工作

  - 创建天空、WEA、Sky Matrix、Sensor Grid 和 View。
  - 给模型对象分配 Radiance Modifier。
  - 启动网格或视角模拟。
  - 读取 HDR、Falsecolor、GIF 或年度采光指标。
  - 把结果转换成可查看的 Visualization Set。

### 连接 Grasshopper 和智能体

  - 在 Grasshopper 里用 Flowerpot 组件交出当前模型或项目上下文。
  - 智能体在 Garden 中继续建模、编辑、保存和校验。
  - Grasshopper 侧继续负责人工选择、预览和必要的手动操作。
  - 适合“界面里做几何，智能体做整理和长链路调用”的工作方式。

### 保留和恢复项目状态

  - 在重要操作前创建 Garden Version。
  - 尝试修改模型或模拟资源。
  - 如果结果不满意，可以恢复到之前的版本。
  - 恢复后继续导出 HTML / SVG 等检查结果。

## 主要工具

Ladybug Tools MCP 不适合做少量工具式的 MCP 服务，这是由于我们的应用广度决定的，所以我简单列举了一下 MCP 目前支持和比较稳定的工具情况。对于详细的工具清单，您可以随时向您的 智能体应用提问。

### 项目与环境

- 查询 Ladybug Tools 本地运行环境配置
- 创建、查找、读取和清理 Garden
- 保存、读取和切换 Garden Base Model
- 创建、列出、检查和恢复 Garden Version
- 搜索 Garden 中的模型、对象、文件和产物

### Flowerpot 协同

- 创建 Flowerpot 平台交接记录
- 读取当前 Flowerpot 上下文
- 获取和清理 Flowerpot
- 支持 Grasshopper 组件把模型、资源和交互上下文交给 Garden

### 模型创建

- 组建 Honeybee Model
- 创建 Rooms、Faces、Doors、Apertures、Shades
- 通过参数批量创建 Apertures 和 Shades
- 将创建结果保存为 Garden 中可继续调用的 Target

### 模型编辑

- 搜索和定位 Honeybee Model 中的对象
- 校验 Honeybee Model
- 变更对象的几何形状 (Ladybug Geometry)
- 变更对象的边界条件 (Boundary Condition)
- 变更对象的类型 (Face Type)
- 移动、旋转、缩放和镜像对象
- 删除 Rooms、Faces、Doors、Apertures、Shades
- 关联模型对象并整理相邻关系

### 属性资源

**Energy**

- 创建 Program Type and Loads
- 创建 People、Lighting、Equipment、Infiltration、Setpoint、Ventilation、Service Hot Water
- 创建 Schedule Day、Schedule Rule、Schedule Ruleset
- 创建 Construction Set、Construction and Material
- 创建 Ideal Air System
- 搜索 HVAC Template
- 创建 Ventilation Control and AFN
- 创建 Daylighting Control
- 创建 PV Properties and Electric Load Center

**Radiance**

- 创建 Modifier Set and Modifier
- 创建 Glass、Metal、Mirror、Opaque、Trans Modifier
- 创建 Sensor Grids
- 创建 View
- 创建 Wea and Sky
- 创建 Sky Matrix and Radiance Parameters
- 创建 Dynamic Group
- 创建 Shade State、SubFace State and State Geometry
- 创建 Luminaire and Lamp

**Garden Library**

- 保存 Energy and Radiance 属性资源到 Garden Properties Library
- 搜索和读取 Garden Properties Library 对象
- 标准化 Garden Properties Library 存储结构

### 模拟

**Energy**

- 搜索和下载 EPW Weather File
- 创建 Energy Output Request
- 启动、轮询、列出和读取 Energy Run
- 读取 ERR、EUI 和结果数据
- 导出 Energy 小时图和月度图 HTML

**Radiance**

- 启动 Grid、View and Matrix Radiance Run
- 轮询、列出和读取 Radiance Run
- 列出 Grid Result、HDR Image and Artifact
- 汇总 Annual Daylight Metrics
- 汇总 Glare Metrics
- 生成 Falsecolor and GIF
- 将 Radiance 结果转换为 Visualization Set

### 可视化和导出

可视化能力是 Ladybug Tools MCP 脱离 CAD 平台运行的主要能力，我非常强烈的建议您了解他们。

- 将 Honeybee Model、Room、Face 转换为 Visualization Set
- 将 DataCollection 转换为图表、文件和 Visualization Set
- 组合多个 Visualization Set
- 创建和编辑 2D Legend Parameters
- 导出 HTML , VTK.JS 和 SVG 可视化产物

## 如何贡献

由于这个项目高度通过智能体进行构建，因此我并不排斥您使用智能体应用的方式来进行贡献，但有几条原则需要遵循，以防我们的项目获得不受控制的膨胀。

- [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation) 是这个项目所有 MCP 工具的核心，如果您期望添加的工具并不在 SDK 的服务范围，那么就不应该是这个项目去进行后续开发。相反，这个时候更应该去为 Ladybug Tools 这个项目做贡献。
- 所有的新工具开发都一定要先经过 Github Issue 的开放性讨论，并由**人类主导**讨论内容和构建开发计划。
- 只写解决当前问题的代码，如果您对当前项目做了 AI 代码审查，但这些问题您并没有在正常的使用场景中实际遇到过，那么我们就不该处理这些问题。
- 工具宁缺毋滥，如无必要，勿增实体。
- 如果上述问题都能遵循，我会很乐意您加入到这个社区自治的维护者行列。
## 待办事项

这些内容都是后续开发的主要方向，在没有广泛的用户呼声期望我们如何去做之前，这个项目会从这些方向进行展开。

- [ ] Dragonfly Model 的创建与编辑工具
- [ ] 添加 UrbanOpt 支持
- [ ] 更多的 Visualization Set 前后处理支持
- [ ] 支持 Ironbug 以完成真正的自定义空调系统定制
- [ ] 与 Agent 直接协同的 Web View 与 Model Editor 工具
- [ ] 可以将所有流程和步骤可视化的演示模式（就像 REAEME 中提供的视频那样）
- [ ] 云服务支持 (我认为这可以是 Pollination 的拓展)
- [ ] ......

绝大多数的事项已经在测试环境中被证明有效，会在不久之后面世，尽请期待。
## 致谢

需要感谢 [Ladybug Tools 社区](https://discourse.ladybug.tools/)与 [Ladybug Tools 团队](https://www.ladybug.tools/about.html#team)的支持：

- **Mostapha** 为这个项目[调整了 Pydantic 兼容的优先级](https://discourse.ladybug.tools/t/upgrade-to-pydantic-2-0/36437/9)，这极大的降低了我们项目的开发难度。
- **Chris** 让 [Visualization Set](https://discourse.ladybug.tools/t/bug-of-dumpvisset-or-incomplete-known-issues/39972) 的 .svg 格式成为了 MCP 最主要的模型可视化方案，这使得我们能完全脱离 CAD 界面来检查任何构建的内容。

除此之外，这个项目的实现核心是 [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation)，这是多年以来 Ladybug Tools 团队的开发产物。

## 开源协议

Ladybug Tools MCP 使用 GNU General Public License Version 3 (GPL v3) 发布，和 Ladybug Tools 项目的开源协议保持一致。
## 联系方式

您可以通过以下方式联系到我：

Email : loftytao@foxmail.com
Wechat : LoftyTao

如果能获得一些 Codex 或 Claude Code 的 Tokens，或者相关的订阅方案支持，那就再好不过了，我也很希望得到这类帮助。
