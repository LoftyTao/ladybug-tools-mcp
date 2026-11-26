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
- [代理客户端配置指南](#代理客户端配置指南)
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

将模型、气象文件、模拟运行与可视化结果统一存放在 Garden 中，可为各类工具提供稳定的项目上下文与可预期的文件结构。

### Flowerpot

Flowerpot 是 Ladybug Tools MCP 与其他交互界面交换信息的中间层。
例如，本项目为 Ladybug Tools 开发的 Flowerpot 组件主要承担生态内的数据交接，帮助用户完成必要的手动操作。

本项目希望用户将更多精力用于与代理交互，因此没有为 Ladybug Tools MCP 另行构建独立的平台界面。
建议使用已有的 Ladybug Tools 基础设施，并通过 Flowerpot 传递数据与信息。

## 快速开始

### Windows x86_64 一体化离线安装包

Windows x86_64 推荐使用 [GitHub Releases](https://github.com/LoftyTao/ladybug-tools-mcp/releases) 提供的**一体化离线安装包**（`lbt-mcp-<ver>-win-x64-setup.exe`，例如 `lbt-mcp-1.2.3-win-x64-setup.exe`）。
安装器采用当前用户安装方式（无需管理员权限），内置 Python `3.12`、`lbt-mcp` 及其依赖、Radiance `5.4 (2023-11-05)`、OpenStudio SDK `3.11.0`、未修改的 EnergyPlus `25.2.0`、Ironbug `1.26.1`（配合自包含 `IronbugBridge.exe`，无需额外安装 `.NET` 运行时）、LBT Measures、`pyHygroThermFEM-Fairyfly` + `gmsh`（THERM）、`lbt-rune-viewer`（三维预览器）以及开源许可证与声明文件。安装包随附可通过 `lbt-mcp flowerpot install` 安装的 Flowerpot 组件文件。

#### 可选 URBANopt 离线扩展包

街区尺度 Dragonfly URBANopt 工作流使用独立的**可选 URBANopt 离线扩展包**（`lbt-mcp-<ver>-win-x64-urbanopt.lbtpack`，例如 `lbt-mcp-1.2.3-win-x64-urbanopt.lbtpack`），内含 URBANopt CLI `1.4.0-rc1`、`OpenStudio/Ruby` 与运行时 Gems。

- 将 `lbt-mcp-<ver>-win-x64-urbanopt.lbtpack` 放在 `lbt-mcp-<ver>-win-x64-setup.exe` 同级目录，安装器会自动识别并供勾选安装；
- 也可在安装后随时通过 `lbt-mcp pack install` / `lbt-mcp pack remove` 进行安装或卸载。

#### 默认目录与非 ASCII / 含空格路径处理

- **默认 `<LBT_MCP_HOME>`**：当 Windows 用户配置目录路径为纯 ASCII 且不含空格时，默认为 `%LOCALAPPDATA%\lbt-mcp`。
- **自动回退**：当 `%LOCALAPPDATA%` 或用户目录包含空格或非 ASCII 字符（如中文用户名）时，安装器会自动默认选择 `C:\lbt-mcp`，因为 Radiance、OpenStudio、EnergyPlus 等模拟引擎要求运行时路径为无空格纯 ASCII。
- **自定义路径**：若手动选择含空格或非 ASCII 字符的安装目录，安装器会弹出警告，`lbt-mcp doctor` 也会给出提示。
- **Garden 工作区**：默认位于 `%USERPROFILE%\Gardens`，始终独立于 `<LBT_MCP_HOME>` 之外，升级或卸载时都会保留用户模型、气象文件、模拟运行和 Git 版本历史；`LADYBUG_TOOLS_GARDENS_ROOT` 支持空格与中文路径。
- **零全局环境污染**：安装器不会修改 Windows 全局 `PATH`、`RAYPATH` 或 `~/.env_uo.bat`。运行时路径保存在 `<LBT_MCP_HOME>\config\runtime.json`，并直接同步到内置虚拟环境的 Ladybug Tools SDK `config.json` 中。

#### 安装目录结构

```text
<LBT_MCP_HOME>\                         # 默认：%LOCALAPPDATA%\lbt-mcp（路径含空格/非ASCII时自动为 C:\lbt-mcp）
├── bin\
│   └── lbt-mcp.exe                     # 原生 Rust stdio 启动器与 CLI 入口
├── app\
│   ├── current.json                    # 当前活动版本指针
│   ├── current\                        # 当前活动版本目录
│   │   ├── venv\                       # 可重定位 Python 3.12 虚拟环境
│   │   ├── skills\
│   │   │   └── ladybug-tools\          # 内置 Agent Skill
│   │   └── grasshopper\                # 打包的 Flowerpot .ghuser 用户对象
│   └── releases\<ver>\                 # 按版本号存放的发布载荷
├── config\
│   ├── runtime.json                    # 内置与自定义的模拟引擎路径配置
│   ├── installation.json               # 安装记录（schema_version: 1）
│   └── packs\                          # 已安装的 .lbtpack 清单回执
├── runtimes\
│   ├── python\3.12.16\                 # 便携版 Python 3.12 运行时
│   ├── openstudio\3.11.0\              # OpenStudio SDK 3.11.0（bin/、CSharp/openstudio/ 与未修改的 EnergyPlus 25.2.0）
│   ├── radiance\5.4\                   # Radiance 5.4 (2023-11-05) radbin + radlib
│   ├── ironbug\1.26.1\                 # Ironbug 1.26.1 程序集
│   ├── lbt_home\resources\measures\    # LBT Measures 与 honeybee-openstudio-gem
│   └── urbanopt-cli-1.4.0\             # 仅在安装 URBANopt 扩展包后出现
├── LICENSE                             # GNU AGPL-3.0-only
└── licenses\                           # THIRD_PARTY_NOTICES.md、CORRESPONDING_SOURCE.md、SOURCE_MANIFEST.json、components\

%USERPROFILE%\
├── .ladybug-tools-mcp\installation.json # 供 Rhino/Grasshopper Flowerpot 读取的用户指针记录（schema_version: 1）
└── Gardens\                             # 默认 Gardens 根目录（位于 <LBT_MCP_HOME> 外，卸载时保留）
```

### CLI 诊断、运行时、扩展包与 Flowerpot 命令

通过 `<LBT_MCP_HOME>\bin\lbt-mcp.exe`（或在 Python 环境中使用 `lbt-mcp`）执行服务启动、状态查询、诊断检查、运行时同步、扩展包和 Flowerpot 管理：

```text
lbt-mcp serve                                          # 启动 stdio MCP 服务（缺省子命令时的默认行为）
lbt-mcp status [--home <dir>] [--state <file>]         # 查看当前 <LBT_MCP_HOME>、版本、启动器与 Gardens 路径
lbt-mcp doctor [--home <dir>] [--smoke]                # 校验安装记录、ASCII/空格路径安全性、SDK config.json 同步、许可证与 Rune/THERM；--smoke 执行引擎子进程探针
lbt-mcp runtime list|sync|set|reset                    # 查看、同步到 SDK config.json、覆盖或重置模拟引擎路径
lbt-mcp pack install <file.lbtpack> [--home <dir>]     # 校验 SHA-256 并安装离线 .lbtpack 扩展包
lbt-mcp pack list [--home <dir>]                       # 列出已安装的扩展包
lbt-mcp pack remove <name> [--home <dir>]              # 卸载扩展包自有文件并重新同步 SDK 配置
lbt-mcp flowerpot install [--grasshopper-dir <dir>]    # 安装可选 Rhino 8 / Grasshopper Flowerpot 组件
lbt-mcp flowerpot uninstall [--state <file>]           # 卸载未修改的 Flowerpot 组件
```

### Flowerpot 与平台范围

Windows 上的 Rhino 8 用户可在安装 Ladybug Tools MCP 后运行 `lbt-mcp flowerpot install`。重启 Grasshopper 后，可搜索 `FP` 或在 `Flowerpot` 分类中找到七个组件（`FP Create Garden`、`FP Garden List`、`FP Honeybee Link`、`FP Dragonfly Link`、`FP Energy Properties Input`、`FP Radiance Properties Input`、`FP Detail HVAC`）。Rhino、Ladybug Tools for Grasshopper 和 Ironbug 依具体工作流另行安装。[组件说明](src/grasshopper_components/README.md)介绍了各组件的用途。

Garden 版本管理需要 `PATH` 中可用的 Git。DES/Modelica 依赖 GeoJSON Modelica Translator、ThermalNetwork 和 Modelica Buildings Library。OpenDSS 需要已初始化的 URBANopt Python 环境。RNM 和 REopt 需要兼容的本地服务。

Windows x86_64 是主要的一体化离线验收平台；Linux x86_64 和 macOS Apple Silicon 通过同一 CI 流程基于 PyPI / 源码构建包运行基础 MCP 与单元/契约检查。Flowerpot 仅保留 Windows Rhino/Grasshopper 边界；Fairyfly/THERM 已内置跨平台 `pyHygroThermFEM-Fairyfly` C++20 求解器与无头 Gmsh Q4 网格划分器，可在 Windows、Linux 与 macOS 上直接运行稳态、瞬态及热湿耦合模拟（无需额外安装外部 LBNL THERM）。详见 [Release Notes](https://github.com/LoftyTao/ladybug-tools-mcp/releases) 与 [distribution workflow](https://github.com/LoftyTao/ladybug-tools-mcp/actions/workflows/distribution.yml)。

### 模拟运行环境

Windows 离线安装包已内置下表所示的模拟运行时（URBANopt 通过可选 `.lbtpack` 扩展包提供）。若使用源码或 PyPI 环境，可通过 `LB_Get_Runtime_Config` 或 `lbt-mcp doctor --smoke` 检查已安装引擎。

Ladybug Tools MCP | Python | Radiance | OpenStudio SDK | EnergyPlus | Ironbug | URBANopt CLI | THERM | 3D Viewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1.2.3` | 3.12 | [5.4 (2023-11-05)](https://github.com/LBNL-ETA/Radiance/releases/tag/rad5R4) | [3.11.0](https://github.com/NREL/OpenStudio/releases/tag/v3.11.0) | 25.2.0 | [1.26.1](https://github.com/MingboPeng/Ironbug/releases/tag/v1.26.1) | [1.4.0-rc1](https://github.com/urbanopt/urbanopt-cli/releases/tag/v1.4.0.rc1)（可选扩展包） | 内置 `pyHygroThermFEM-Fairyfly` + `gmsh` | 内置 `lbt-rune-viewer` |

### PyPI 与源码开发

在 Linux、macOS 或自定义 Python 3.12 环境中，可通过 [uv](https://docs.astral.sh/uv/getting-started/installation/) 从 PyPI 安装：

```text
uv venv --python 3.12
uv pip install --prerelease allow lbt-mcp==1.2.3
```

修改本项目时可配置源码开发环境：

```text
git clone https://github.com/LoftyTao/ladybug-tools-mcp.git
cd ladybug-tools-mcp
uv venv --python 3.12
uv pip install --prerelease allow -e .
```

源码构建 wheel 支持 `LBT_MCP_REQUIRE_HYGROTHERM_NATIVE=1`、`LBT_MCP_REQUIRE_IRONBUG_BRIDGE=1` 与 `LBT_MCP_REQUIRE_RUNE_VIEWER=1`；Windows 离线安装包及对应源码包通过 `scripts/distribution/build_windows_bundle.py` 和 `scripts/distribution/build_corresponding_source.py` 生成。

## 代理客户端配置指南

请按各代理客户端的配置格式手动添加 MCP 服务：

- **命令（`command`）**：`<LBT_MCP_HOME>\bin\lbt-mcp.exe`
- **参数（`args`）**：`["serve"]`
- **环境变量（`env`）**：
  - `LADYBUG_TOOLS_GARDENS_ROOT`：Garden 根目录（默认 `%USERPROFILE%\Gardens`，位于 `<LBT_MCP_HOME>` 之外）
  - `LADYBUG_TOOLS_MCP_HOME`（可选）：显式指定 `<LBT_MCP_HOME>`（直接调用 `<LBT_MCP_HOME>\bin\lbt-mcp.exe` 时启动器会自动根据上级目录识别）

> **提示**：运行 `<LBT_MCP_HOME>\bin\lbt-mcp.exe status` 可查看本机展开后的绝对路径。多数 MCP 客户端不会自动展开 `%LOCALAPPDATA%` 或 `%USERPROFILE%`，请将 `<LBT_MCP_HOME>`（如 `C:\lbt-mcp` 或 `C:\Users\<user>\AppData\Local\lbt-mcp`）和 `<GARDENS_ROOT>`（如 `C:\Users\<user>\Gardens`）替换为实际绝对路径（JSON 字符串中需写作 `\\`，TOML 中可使用单引号字面量 `'...'`）。

### Codex（`~/.codex/config.toml`）

将以下内容合并到 `$CODEX_HOME/config.toml`（默认 `~/.codex/config.toml`）：

```toml
[mcp_servers.lbt-mcp]
command = '<LBT_MCP_HOME>\bin\lbt-mcp.exe'
args = ["serve"]
startup_timeout_sec = 60
required = true

[mcp_servers.lbt-mcp.env]
LADYBUG_TOOLS_GARDENS_ROOT = '<GARDENS_ROOT>'
# 可选：
# LADYBUG_TOOLS_MCP_HOME = '<LBT_MCP_HOME>'
```

### Claude Code（`.mcp.json` / `claude mcp add-json`）

项目级 `.mcp.json`：

```json
{
  "mcpServers": {
    "lbt-mcp": {
      "type": "stdio",
      "command": "<LBT_MCP_HOME>\\bin\\lbt-mcp.exe",
      "args": ["serve"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>"
      }
    }
  }
}
```

或通过命令行注册到用户级配置（仅传入内层服务对象，切勿覆盖 `~/.claude.json`）：

```text
claude mcp add-json --scope user lbt-mcp '{"type":"stdio","command":"<LBT_MCP_HOME>\\bin\\lbt-mcp.exe","args":["serve"],"env":{"LADYBUG_TOOLS_GARDENS_ROOT":"<GARDENS_ROOT>"}}'
```

### Cursor（`~/.cursor/mcp.json`）

合并到用户级 `~/.cursor/mcp.json` 或项目级 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "lbt-mcp": {
      "command": "<LBT_MCP_HOME>\\bin\\lbt-mcp.exe",
      "args": ["serve"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>"
      }
    }
  }
}
```

### VS Code（`.vscode/mcp.json`）

合并到项目级 `.vscode/mcp.json`（或在 VS Code 中执行 `MCP: Open User Configuration`；不要写入编辑器 `settings.json`）：

```json
{
  "servers": {
    "lbt-mcp": {
      "type": "stdio",
      "command": "<LBT_MCP_HOME>\\bin\\lbt-mcp.exe",
      "args": ["serve"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>"
      }
    }
  }
}
```

### Gemini CLI（`~/.gemini/settings.json`）

合并到用户级 `~/.gemini/settings.json` 或项目级 `.gemini/settings.json`：

```json
{
  "mcpServers": {
    "lbt-mcp": {
      "command": "<LBT_MCP_HOME>\\bin\\lbt-mcp.exe",
      "args": ["serve"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>"
      }
    }
  }
}
```

### OpenCode / OpenCode 2（`opencode.json`）

合并到 `opencode.json`（或 `~/.config/opencode/opencode.json`）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lbt-mcp": {
      "type": "local",
      "command": ["<LBT_MCP_HOME>\\bin\\lbt-mcp.exe", "serve"],
      "environment": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>"
      },
      "timeout": 120000
    }
  }
}
```

OpenCode 等客户端的 Skill 路径指向实际存放目录。

### 通用 stdio MCP 客户端与内置 Agent Skill 路径

对于其他标准 stdio MCP 客户端，可按以下结构合并（直接调用 `<LBT_MCP_HOME>\bin\lbt-mcp.exe` 时 `LADYBUG_TOOLS_MCP_HOME` 可省略）：

```json
{
  "mcpServers": {
    "lbt-mcp": {
      "command": "<LBT_MCP_HOME>\\bin\\lbt-mcp.exe",
      "args": ["serve"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<GARDENS_ROOT>",
        "LADYBUG_TOOLS_MCP_HOME": "<LBT_MCP_HOME>"
      }
    }
  }
}
```

`lbt-mcp serve` 通过 MCP 资源 `skill://ladybug-tools/SKILL.md` 提供内置的 `ladybug-tools` Agent Skill。支持从磁盘加载 Skill 的客户端可使用 Windows 离线安装包提供的目录。

```text
<LBT_MCP_HOME>\app\current\skills\ladybug-tools
```

## Web View 预览模式

Web View 模式通过原生 GPU 加速的 Rune 三维预览器（`lbt-rune-viewer`）直接连接 Garden，提供实时建模渲染、模型检查与双向空间批注体验。
当代理创建、编辑或校验 Honeybee / Dragonfly 模型时，`lbt-rune-viewer` 会以原生 wgpu 渲染建筑几何，支持 CAD 视角控制、剖切、按属性着色和三维对象点选。

### 开启

建模或编辑前，让代理开启 Web View 模式：

```text
请为这个 Garden 开启 Web View 模式，然后创建或编辑 Honeybee 模型。
```

代理通过 MCP 代码模式调用：

```text
GD_Web_View_Start_Mode(garden_root, name="...", open_window=True)
```

开启后，服务会在 `<garden>/tmp/web_view/` 下初始化原子协议文件（`session.json`、`present.json`、`interaction_state.json`），自动基于 Garden 的基础 Honeybee 或 Dragonfly 模型初始化 `present.json`（Dragonfly 会按需转换到 `tmp/web_view/models/`），并在 `open_window=True` 且存在图形显示环境时拉起 `lbt-rune-viewer` 桌面窗口（无头或仅协议同步场景可传 `open_window=False`）。

### 视角控制、读取上下文与截图

- `GD_Web_View_Present`：控制三维视口的显示模式（`view_type`）、着色方式（`color_by`）、高亮对象（`highlight_targets`）、隔离模式（`isolation_mode`）、校验问题叠加（`validation_issues`）、相机视角（`camera`）、剖切面（`section`）与空间标注（`callouts`）。
- `GD_Web_View_Get_Context`：从 `interaction_state.json` 读取用户在视口中选中的对象、三维空间批注、当前视角和待处理意图，并可原子地将已处理的批注标记为已解决。
- `GD_Web_View_Capture`：按“实时 `lbt-rune-viewer` 截图握手 -> 无头 `lbt-rune-viewer --snap` -> 离屏 VTK 兜底”三级链路将当前视角截图保存到 `<garden>/tmp/web_view/captures/`。

### 关闭

让代理停止 Web View 模式，或调用：

```text
GD_Web_View_Stop_Mode(garden_root)
```

这会停止后续自动推送到 `present.json`，并关闭由当前会话启动的 `lbt-rune-viewer` 窗口进程。
`tmp/web_view/` 中的协议历史会保留。

### 与普通模式的区别

普通模式下，建模工具将文件写入 Garden，并返回精简的目标引用、摘要和回执，不会启动 `lbt-rune-viewer`，也不会在编辑后自动写入 `tmp/web_view/present.json`。

Web View 模式下，代码模式中的 Honeybee 建模/编辑、`HB_Validate_Model` 校验以及 Dragonfly 建模操作会在每个执行块结束时合并刷新一次 `<garden>/tmp/web_view/present.json`；`lbt-rune-viewer` 检测到同路径模型内容变化后会自动原地重载并保留您当前的相机视角。
这些会话文件属于本地预览状态，不属于用户明确要求导出的正式成果。
如果需要长期保存和重复使用的成果（如 `html`、`svg`、`png`、`vtkjs`、`vtk`、`vtp`、`vsf`、`pkl`），仍应让代理通过 `LB_Export_Visualization_Set` 显式导出可视化集。

## 首次使用

按照[代理客户端配置指南](#代理客户端配置指南)完成配置（将 `command` 设为 `<LBT_MCP_HOME>\bin\lbt-mcp.exe`、参数设为 `["serve"]`）后，重启客户端并新建会话，直接描述您的 Garden 或建模需求即可。

在可承受的范围内选择能力较强、上下文窗口较大的模型，有助于多步骤建模与模拟工作流更稳定地执行。

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
- 只编写解决当前问题的代码，避免不必要的复杂性与过度抽象。
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

Ladybug Tools MCP 采用 GNU Affero 通用公共许可证第三版（**`AGPL-3.0-only`**，见 [LICENSE](LICENSE)），与 Ladybug Tools Core SDK 保持一致。

第三方组件许可证、署名与随附二进制声明见 [licenses/THIRD_PARTY_NOTICES.md](licenses/THIRD_PARTY_NOTICES.md)，AGPL 与 LGPL 组件（`lbt-mcp`、LBT Core SDKs、`gmsh`、`GEOS`、`Ironbug 1.26.1`）的对应源码获取说明见 [licenses/CORRESPONDING_SOURCE.md](licenses/CORRESPONDING_SOURCE.md)：

- **Radiance**：“This product includes Radiance software (http://radsite.lbl.gov/) developed by the Lawrence Berkeley National Laboratory (http://www.lbl.gov/).”
- **EnergyPlus**：在随附 OpenStudio 运行时内未修改地分发 **EnergyPlus version 25.2.0**；本项目未获得美国能源部（DOE）或劳伦斯伯克利国家实验室（LBNL）的背书。
- **OpenStudio(R)**：依据 BSD-3-Clause 许可证随附 **OpenStudio(R)** 3.11.0 运行时组件（保留未修改的 EnergyPlus 子目录，裁剪的非运行时目录详见 [licenses/THIRD_PARTY_NOTICES.md](licenses/THIRD_PARTY_NOTICES.md)）；本项目未获得 NREL 或 Alliance for Sustainable Energy 的背书。

## 联系方式

你可以通过以下方式联系我：

- 邮箱：`loftytao@foxmail.com`
- 微信：`LoftyTao`

如果你愿意提供 Codex 或 Claude Code 的使用额度或订阅支持，我也会非常感谢。
