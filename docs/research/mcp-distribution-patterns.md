# Ladybug Tools MCP 分发方案评估

评估日期：2026-09-19。本文记录实施前的仓库状态与评估，实际实现和验收结果见[分发验收记录](../distribution-acceptance.md)。依据为官方协议、产品文档、项目源码及本机已安装包的元数据。下文的“标准路径”指官方支持的机制，不代表对实际市场占比的统计。

## 整体判断

PyPI wheel、uv 管理 Python 环境、本地 stdio 接入以及预生成 Grasshopper 用户对象，都是有官方机制支持的分发组合。统一终端向导适合本项目的跨客户端、跨建模环境需求；它应集中负责配置和附加资产部署，环境与依赖管理交给 uv。当前草案对首次安装已有明确目标，但还需要补齐维护、兼容性与发布验收。

| 方案部分 | 判断与依据 |
| --- | --- |
| PyPI wheel + uv + stdio | 适合作为通用基础。MCP 定义客户端启动本地 stdio 子进程；Registry 可描述 PyPI/std​io 包，uv 提供隔离工具环境。[MCP stdio](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/stdio.mdx)、[Registry 包类型](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx)、[uv 工具环境](https://docs.astral.sh/uv/concepts/tools/) |
| Python 终端配置向导 | 是项目自行维护的便利入口。它可以组合标准安装操作，但不是 MCP 协议要求每个服务提供的功能；应保持可独立使用的 MCP 命令入口。此项为架构建议。 |
| 随包 Skills 与宿主安装 | MCP 资源与宿主原生技能是两种交付行为。Codex 文档说明了本地技能目录，并提供将 Skills 与 MCP 配置组装为插件的方式。[技能发现](https://developers.openai.com/zh-Hans/docs/build-skills)、[插件打包](https://developers.openai.com/zh-Hans/plugins/build/plugins) |
| Flowerpot 预生成 .ghuser | 符合 Grasshopper 用户对象机制。官方 API 提供保存用户对象和复制到对应用户目录的方法。[SaveToFile](https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_Kernel_GH_UserObject_SaveToFile.htm)、[CopyFileToAppropriateFolder](https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_Kernel_GH_ComponentServer_CopyFileToAppropriateFolder.htm) |
| MCPB、宿主插件、Registry | 可作为补充入口。MCPB 的 uv 类型由实现该格式的宿主管理；Registry 只存元数据，不托管实际包。不能仅由支持 MCP 推断某个客户端支持这些安装方式。[MCPB 清单](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)、[Registry 说明](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx) |

## 发布前应补齐的内容

### 1. 明确临时启动环境与持久运行环境

uv 官方将 uvx 的缓存环境视为可丢弃环境；uv tool install 创建持久工具环境。已安装工具还可能被 uvx 复用，显式隔离运行可避开这种复用。[uv 工具环境](https://docs.astral.sh/uv/concepts/tools/)

建议：向导通过独立的启动环境运行，持久安装由 uv 管理；Flowerpot 连接持久环境中的 Python，不引用 uvx 缓存或开发仓库。再次运行安装器时，不应在正在使用的目标环境内直接执行自我替换。Garden 与这两类环境都分开。GUI 客户端和 Rhino 启动进程的 PATH 也应验证，不能仅以终端里能找到命令作为成功依据。

### 2. “固定 MCP 版本”与“完整环境可复现”分别验证

当前 [pyproject.toml](../../pyproject.toml) 没有运行依赖声明，命令入口只有 Ironbug Console；[requirements.txt](../../requirements.txt) 固定了直接依赖，但不是完整传递依赖锁。包元数据需要声明依赖和命令入口，依赖约束还需在最终用户安装流程中实际生效。[Python 包元数据](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

uv 的项目锁文件可以导出为其他安装流程使用的格式；不能仅把 uv.lock 放进仓库就认为公开 wheel 的消费者会自动使用它。[锁文件导出](https://docs.astral.sh/uv/concepts/projects/sync/#exporting-the-lockfile)

本机只读元数据检查显示，VTK 9.7.0、NumPy 2.1.0 和 OpenStudio 3.11.0 当前安装的 wheel 标签均为 cp312-cp312-win_amd64。这只能证明当前 Windows/Python 3.12 组合；不能证明 macOS ARM64 或其他 Linux 组合可用。轮子兼容性本身由 Python、ABI 和平台标签表达。[平台兼容标签](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/)

建议：首发支持表写明操作系统、架构、Python 和可用功能；分别测试基础 MCP/预览与按需模拟依赖。支持平台上应验证预编译依赖的可获得性，避免把编译工具链要求转嫁给用户。安装器本身跨平台与完整 SDK 组合通过验收应分别陈述。

### 3. 把重复安装、升级和卸载定义清楚

草案已有配置备份和保留 Garden 的要求，还应明确：重复安装如何识别已有版本；哪些配置和复制文件由安装器管理；用户修改过的 Skills 如何处理；安装中断后如何重试；卸载如何只移除本项目的注册项和未被用户修改的文件。

建议保留一份简短安装记录，记录所选版本、配置位置和复制资产的校验值。Python 环境的管理使用 uv 原生命令。安装过程中先准备并检查运行环境，再更新宿主配置和组件关联；失败时保留原配置。MCP、Skills 和 Flowerpot 资产使用同一发行版本。Garden 数据不随程序卸载。

### 4. Flowerpot 的产物构建与旧画布兼容需要独立验收

当前 [组件目录](../../src/grasshopper_components/README.md) 只有六个源脚本，缺少可直接部署的 .ghuser 产物；[runtime.py](../../src/flowerpot/runtime.py) 和 [worker.py](../../src/flowerpot/worker.py) 仍包含开发仓库和 Windows .venv 路径假设。分发工作需要先生成并验收端口、标识、分类正确的用户对象，再配置其连接到持久运行环境。

官方 API 的 ReadFromFile 只说明读取用户对象文件；另有显式的 IGH_UpgradeObject 升级接口。由此只能推断：不能从“替换了 .ghuser 文件”推出“现有 .gh 画布中的实例已经升级”。这不是对所有用户对象升级行为的实验结论。[ReadFromFile](https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_Kernel_GH_UserObject_ReadFromFile.htm)、[IGH_UpgradeObject](https://developer.rhino3d.com/api/grasshopper/html/T_Grasshopper_Kernel_IGH_UpgradeObject.htm)

建议分别验证新组件搜索/拖入，以及旧画布在运行环境升级后继续工作；若某次变更需要替换旧组件，应给出明确范围和操作方式。首版依现有 Windows/Rhino 8 矩阵声明支持，其他平台以实际验收扩展。

Yak 是 Rhino/Grasshopper 插件的原生包管理入口，其文档定义了 .yak 清单和 .gha/.ghpy 的放置规则；它与 .ghuser 用户目录安装不应混为一谈。当前六个脚本可以先交付预生成用户对象，是否另加 Yak 发布应依据后续插件形态决定。[Yak](https://developer.rhino3d.com/guides/yak/what-is-yak/)、[包结构](https://developer.rhino3d.com/en/guides/yak/the-anatomy-of-a-package/)

### 5. 在 Agent 体验测试下面增加确定性的回归基线

建议把测试分成三层：无需模型的包安装和 MCP 协议/工具检查；OpenCode2 免费模型的自然语言快速检查；Codex 的完整用户流程验收。第一层直接校验已安装产物的实际行为，覆盖启动、资源、Garden、一个小模型和预览；另外两层检查 Agent 是否能正确使用它们。

OpenCode2 支持非交互运行和 JSON 记录，适合作为外层体验测试入口。[OpenCode V2 CLI](https://opencode.ai/v2/docs/cli/commands/)。免费服务可用性、客户端 beta 版本和模型行为会给测试引入额外变量，因此结果需区分模型/服务问题与 MCP 回归；不能以模型回复“成功”作为产物验收。

终端向导还应能通过参数完成无人值守测试，避免 CI 需要模拟按键。测试使用没有源码 checkout、可编辑安装或开发者全局依赖兜底的环境，并包含已有配置、中文/空格路径和失败重试场景。

安装交互与 MCP 服务运行应使用明确不同的命令模式。客户端启动 stdio 服务时不能进入向导或输出安装提示，stdout 只承载 MCP 消息，诊断日志写入 stderr；这应由协议检查覆盖。[MCP stdio 规范](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/stdio.mdx)

### 6. 把发布过程与被测试的产物对应起来

建议发布流程构建 wheel 后直接测试该 wheel，并发布同一产物。除服务能启动外，还应检查 Skills、天气资源和 Flowerpot 组件确实进入包，组件资产与当前源码版本一致。明确 PyPI 项目发布权限和版本号规则，后续通过 CI 发布时使用 PyPI Trusted Publishing，避免维护长期上传令牌。[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)

宿主插件可作为复用同一 Python 服务的另一个入口，但要按目标宿主和发布渠道验证。OpenAI 的公开插件提交文档当前要求远程 HTTPS MCP 端点；本地/私有插件与公开商店提交并非同一交付流程，不宜把公开上架作为本地 MCP 首次分发的前提。[OpenAI 插件打包与提交说明](https://developers.openai.com/zh-Hans/plugins/build/plugins)

### 7. 说明现有网络边界

[Web View 页面](../../src/web_view/url_fallback.py) 从 unpkg.com 加载 vtk.js；localhost 描述页面服务位置，并不表示预览完全离线。保留当前方式符合已确认范围，但安装和诊断说明应区分首次包下载失败、MCP 启动失败和 CDN 资源加载失败。此次评估不将离线预览改造加入首发范围。

## 建议的实施顺序

先打通独立 wheel 的安装和确定性基础检查；再完成持久环境与终端配置向导；随后交付预生成的 Flowerpot 用户对象及兼容性检查；最后以三平台安装检查、OpenCode2 快速体验和 Windows/Codex/Rhino 完整验收验证同一发行物。MCPB、宿主插件和 Registry 登记作为按需增加的入口，复用同一已验证版本。

这些是对现有草案的评估与补强建议，尚不代表完成实现、发布或跨平台验收。
