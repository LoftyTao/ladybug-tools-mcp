# Ladybug Tools MCP

本项目以 Garden 为持久上下文，通过 Flowerpot 在代理工作流与交互式建模界面之间交接 Ladybug Tools 对象。

## Language

**Garden**:
用户持久保存和继续编辑 Ladybug Tools 模型、属性库及关联成果的项目上下文。
_Avoid_: MCP 安装目录、源码仓库

**Flowerpot**:
连接 Garden 与外部交互界面的不透明交接对象；它标识可继续工作的上下文，而不是承载完整模型。
_Avoid_: Flowerpot 字典、模型数据

**Flowerpot integration**:
让指定交互界面通过 Flowerpot 参与 Garden 工作流的可选集成；当前提供 Grasshopper 集成。
_Avoid_: Flowerpot 对象、MCP 本体

**Ironbug authoring model**:
在 Garden 中由代理维护的、可验证并可持久化的 Ironbug 暖通系统图。
_Avoid_: MCP Ironbug 对象、原生 Ironbug 对象

**Ironbug system specification**:
表达完整 Ironbug 暖通系统的可序列化交换规格，可跨运行时传递并重建原生系统。
_Avoid_: Ironbug authoring model、DetailedHVAC 对象

**native Ironbug HVAC system**:
由 Ironbug 自身运行时识别的完整暖通系统对象，可供原生 Ironbug 与相关 Grasshopper 组件消费。
_Avoid_: Ironbug system specification、MCP Ironbug 对象

**Honeybee DetailedHVAC**:
Honeybee Energy 中保存 Ironbug 系统规格及其房间/热区绑定的详细暖通定义。
_Avoid_: detail hvac、native Ironbug HVAC system

**direct Ironbug handoff**:
从 Garden 中的 Ironbug 作者模型到 Grasshopper 原生 Ironbug 暖通系统的单向交接；交换格式不属于用户接口。
_Avoid_: JSON 输出、双向同步

**room binding**:
Ironbug 热区与 Honeybee 房间之间基于稳定标识符建立的对应关系；该关系在交接前由 Garden 确定。
_Avoid_: Grasshopper 房间重映射、交接后绑定

**end-to-end Ironbug compatibility**:
原生 Ironbug 暖通系统可被 Honeybee DetailedHVAC 接受，并能完成目标能耗仿真的兼容状态。
_Avoid_: 可连线、可反序列化

**supported runtime matrix**:
项目已完成端到端兼容验收的一组明确版本组合。
_Avoid_: 最低版本、尽力兼容

**FP Detail HVAC**:
将 Garden 中的 Ironbug 作者模型单向交接为 Grasshopper 原生 Ironbug 暖通系统的 Flowerpot 组件。
_Avoid_: Honeybee DetailedHVAC、JSON 输出组件、FP Detailed HVAC
