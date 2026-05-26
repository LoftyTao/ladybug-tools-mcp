# Onboarding and Intent Triggers

## Purpose

Use this reference when the user greets Ladybug Tools MCP, asks to start with broad guidance, or gives a top-level intent before a stable Garden context is known.

This is an Agent-facing routing layer. It does not add a new MCP launch tool and does not replace the formal FastMCP Code Mode MCP path. Its job is to keep first contact stable: choose a top-level direction, then enter the Garden gate before downstream modeling, reusable-resource, or collaboration workflows.

## Vocabulary

- `workspace_id` in older upstream onboarding notes maps to the current Garden context in this MCP.
- Garden is the primary product concept for persistent project context. The stable context value is usually `garden_root`, a Garden target, or a known current Flowerpot context that can resolve to a Garden.
- The current public tools are `garden_list`, `garden_create`, and `garden_get`, not `workspace_list`, `workspace_create`, or `workspace_get`.

## Entry Signals

Use the full welcome template when the user says:

- `你好！Ladybug Tools!`
- `Hi, Ladybug Tools!`
- `Hi，Ladybug Tools！`
- `我想通过 Ladybug Tools MCP 做点事情，但你先带我走流程。`
- Any similarly broad greeting where no stable Garden context or top-level direction is known.

Use a shorter routing response when the user already says one of the three top-level directions but no stable Garden context is known.

## Language Matching

Match the user's trigger language for all onboarding replies:

- If the trigger is English, reply in English.
- If the trigger is another language, reply in that language.
- A mixed-language greeting like `Hi，Ladybug Tools！` counts as English because the user's greeting word is English.
- Do not default to Chinese unless the user used Chinese or the language is unclear.
- Keep stable protocol labels such as `direction_label`, `natural_language_modeling`, `reusable_resource_preparation`, `platform_collaboration`, `garden_root`, and tool names in English.

## Top-Level Direction Labels

Store one of these labels in the conversation state before handing off to the Garden flow:

- `natural_language_modeling`: natural-language modeling through simulation.
- `reusable_resource_preparation`: reusable simulation resources, such as schedules, constructions, loads, HVAC, Radiance modifiers, or library objects.
- `platform_collaboration`: collaborative editing with another interface such as Rhino / Grasshopper through Flowerpot.

## Shortest Old Tool Path

When the host exposes old FastMCP tools, first confirm that Garden discovery is available through Tool Search:

```text
search query="garden_list garden_create garden_get create choose existing recent Garden"
```

The expected MCP tools are:

- `garden_list`
- `garden_create`
- `garden_get`

If using Code Mode, do the same check through the outer `search` tool only when the tool names are unknown. Do not call `search` or `get_schema` inside `execute`.

## Fixed-Structure Welcome Template

For the fixed greeting trigger, answer with this structure. The title and numbering stay stable; translate the human-facing sentences and option labels to match the user's trigger language. Do not show `direction_label:` lines in the user-facing welcome. Save the chosen label internally after the user picks an option.

Keep the tone helpful and light. This is a welcome, not a routing table.

Chinese trigger example:

```text
Bug Flyzzzzzzzzz!
欢迎使用 Ladybug Tools MCP！花园 (Garden) 是使用 MCP 的前提，用于存储所有资源文件。
您可以从以下三个选项作为您的主要使用意图，以便我更好地协助您：

1. 通过自然语言对话的方式进行模型创建到模拟流程
2. 通过自然语言对话的方式准备可复用的模拟资源
3. 通过 Flowerpot 将 MCP 连接到 Grasshopper 或其他界面进行协作
```

English trigger example:

```text
Bug Flyzzzzzzzzz!
Welcome to Ladybug Tools MCP! A Garden is required before using the MCP, and it stores all resource files.
Please choose one of the three options below as your main intent so I can help you more effectively:

1. Create and simulate models through a natural-language conversation
2. Prepare reusable simulation resources through a natural-language conversation
3. Connect the MCP to Grasshopper or another interface through Flowerpot
```

Internal mapping:

```text
1 -> natural_language_modeling
2 -> reusable_resource_preparation
3 -> platform_collaboration
```

After the user chooses a direction, handoff to `02-Garden 创建与选择`. The Garden gate must create or choose a Garden before moving to route `29`, `30`, or `31`.

## Option Selection Response

Any option selection routes to the same Garden gate:

- Option 1 saves `natural_language_modeling` internally, then goes to Garden creation or selection.
- Option 2 saves `reusable_resource_preparation` internally, then goes to Garden creation or selection.
- Option 3 saves `platform_collaboration` internally, then goes to Garden creation or selection.

Do not start modeling, resource creation, or Grasshopper collaboration immediately after the user chooses one of the three options. The next user-facing step is to create or choose a Garden.

The first Garden-gate reply should be a short binary choice: create a new Garden or continue an existing one. Do not jump straight into asking for a Garden name before the user has picked one of those two directions.

When the user chooses the existing-Garden path, call `garden_list` without `root_dir` when no stable Garden root has already been established, so discovery uses the system's default Gardens root. If the user has named a specific parent folder, pass that folder as `root_dir`. Show the five most recent Gardens from `matches[:5]`. The service sorts `matches` by recent `created_at` / `updated_at` values and includes `summary_view.count`. In onboarding, only read from the default Gardens root or the user-specified query root; do not search test folders or cache folders as reusable Garden sources.

When the user chooses the new-Garden path, ask for the new Garden name and then call `garden_create`.

If more than ten Gardens exist, suggest cleanup and offer to help. Do not delete or clean anything without explicit user confirmation. For cleanup, first clarify whether the user wants to inspect old Gardens, archive them outside MCP, or run `garden_cleanup_workspace` on selected non-authoring scopes. Do not make the user type a path when recent Garden matches are available.

Chinese trigger example:

```text
好的，我将为您创建花园 (Garden)，再开始之前，我需要确定您的意图：

1. 创建一个全新的花园作为新的开始
2. 使用已有的花园延续以往的工作内容
```

English trigger example:

```text
Great. I will help you set up the Garden first. Before we begin, I need to confirm which path you want:

1. Create a brand-new Garden as a fresh start
2. Use an existing Garden to continue previous work
```

## New-Garden Branch Response

When the user chooses the new-Garden path, respond with a short fixed template in the user's trigger language, then ask for the Garden name. Do not start modeling or resource creation yet.

Chinese trigger example:

```text
好的，我们将从一个新的花园 (Garden) 开始。请告诉我您希望这个 Garden 使用的名称，我会为您创建它。
通常情况下，Garden 会被存放在 `D:\Desktop\Codex\rec-ladybug-tools-mcp\gardens` 下；如果您不希望存放在这里，也可以直接告诉我您希望使用的保存位置，我会按您的要求创建。
```

English trigger example:

```text
Great. We will start with a brand-new Garden. Please tell me the name you want to use for this Garden, and I will create it for you.
By default, the Garden will be stored under `D:\Desktop\Codex\rec-ladybug-tools-mcp\gardens`. If you do not want to use that location, you can simply tell me where you want it to be saved instead, and I will create it there for you.
```

## Existing-Garden Branch Response

When the user chooses the existing-Garden path, respond with a short fixed template in the user's trigger language, then call `garden_list` and show the five most recent Gardens from `matches[:5]`. Read only from the default save location or the user-specified save location; do not read reusable Gardens from test folders or cache folders. If none fits, offer to switch to the new-Garden path.

Chinese trigger example:

```text
好的，我将先为您查找已有的花园 (Garden)。我会先列出最近使用的 5 个 Garden 供您选择；如果没有合适的，我们再创建一个新的。
这些可复用的 Garden 将只从默认保存位置 `D:\Desktop\Codex\rec-ladybug-tools-mcp\gardens` 或您指定的保存位置中读取，不会从测试目录或缓存目录中读取。

1. XXX
2. XXX
3. XXX
4. XXX
5. XXX
```

English trigger example:

```text
Great. I will first look up your existing Gardens. I will show the five most recently used Gardens for you to choose from; if none fits, we can create a new one instead.
These reusable Gardens will be read only from the default save location `D:\Desktop\Codex\rec-ladybug-tools-mcp\gardens` or another save location you specify, not from test folders or cache folders.

1. XXX
2. XXX
3. XXX
4. XXX
5. XXX
```

## Short Routing Template

If the user already says "我要自然语言建模", "I want natural-language modeling", "我要做可复用资源", "I need reusable simulation resources", "我要跟其他界面协作", or "I want to collaborate with Grasshopper", skip the repeated welcome text and respond briefly in the user's trigger language.

Chinese trigger example:

```text
收到，我们先走 Garden 这一步：如果你已有 Garden，我会继续使用；如果没有，我会先帮你创建一个。
```

English trigger example:

```text
Got it. First we will handle the Garden step: if you already have a Garden, I will continue with it; otherwise I will help create one.
```

Save the chosen label internally, but do not display it unless the user explicitly asks for debug or protocol details.

Then handoff to `02-Garden 创建与选择`.

## After Garden Creation Or Selection

After Garden creation or selection, use the saved direction label to offer a small next-step menu. Keep it short, concrete, and in the user's trigger language. Do not show the internal label unless the user asks for debug/protocol details.

natural_language_modeling next prompts:

- Distinguish an empty Garden from a Garden that already has a Honeybee base model.
- For an empty Garden, first create an empty Honeybee model. By default, use the Garden name as the model name, but remind the user that it can be changed.
- For an existing Garden, checking the current model state is an implicit and mandatory step before suggesting edits. Read the compact current-model summary first, and validate when the user is about to edit the existing model.

Empty-Garden Chinese example:

```text
Garden 已经准备好了。当前这是一个空的 Garden，里面还没有可继续编辑的 Honeybee Model。
接下来我会先为您创建一个空的 Honeybee Model，默认名称会与 Garden 名称保持一致；如果您想更改这个名称，也可以现在告诉我。

创建完模型后，我们通常可以从这些意图开始：

1. 创建一个或多个房间
2. 描述房间的形状、尺寸、层高、朝向或楼层关系
3. 为房间添加窗、门或遮阳
4. 继续补充您已经知道的技术细节

如果您暂时不确定怎么说，也可以直接用自然语言告诉我您想要几个房间、它们大致是什么形状，以及每个房间的大概尺寸。
```

Empty-Garden English example:

```text
The Garden is ready. This is currently an empty Garden, so there is no Honeybee model to continue editing yet.
Next, I will first create an empty Honeybee model for you. By default, its name will match the Garden name, but you can change that name now if you want to.

After the model is created, we can usually start from one of these intents:

1. Create one or more rooms
2. Describe room shape, size, height, orientation, or floor relationships
3. Add windows, doors, or shades to the rooms
4. Continue with any technical details you already know

If you are not sure how to describe it yet, you can simply tell me how many rooms you want, what shapes they roughly have, and the approximate size of each room.
```

Existing-Garden Chinese example:

```text
Garden 已经准备好了。我会先隐式检查当前 Garden 中模型的基本状态，然后再继续引导您编辑。

当前模型状态会以简要形式返回，例如：
- 模型名称：XXX
- 房间数量：XXX
- 窗数量：XXX
- 门数量：XXX
- 遮阳数量：XXX
- 验证状态：有效 / 需要修正

在确认完当前状态后，我们更适合直接编辑现有模型，例如：

1. 新增或修改一个或多个房间
2. 调整现有窗、门或遮阳
3. 检查并修正当前模型问题
4. 继续补充您已经知道的技术细节

如果您已经知道想改什么，也可以直接告诉我目标对象和修改意图。
```

Existing-Garden English example:

```text
The Garden is ready. I will first do an implicit check of the current model state in this Garden before guiding you into edits.

The current model status should be returned in a short form, for example:
- Model name: XXX
- Room count: XXX
- Window count: XXX
- Door count: XXX
- Shade count: XXX
- Validation status: valid / needs fixes

After confirming the current state, it is usually better to move straight into editing the existing model, for example:

1. Add or modify one or more rooms
2. Adjust existing windows, doors, or shades
3. Check and fix current model issues
4. Continue with any technical details you already know

If you already know what you want to change, you can also tell me the target object and the edit you want directly.
```

Chinese example:

```text
Garden 准备好了。我们可以从一个小模型开始：创建 Honeybee 模型、创建房间、加窗或遮阳，然后再验证模型。你想先从哪一步开始？
```

English example:

```text
The Garden is ready. We can start with a small model: create a Honeybee model, create rooms, add windows or shades, then validate it. Which step should we start with?
```

reusable_resource_preparation next prompts:

- Save reusable resources as local Garden-managed resources first; they do not need to be attached to a model immediately.
- Create a schedule.
- Create a construction set, construction, or material.
- Create a program, people, ventilation, equipment, infiltration, setpoint, lighting, SHW, or related Energy resource.
- Create a modifier set or modifier.

Chinese example:

```text
Garden 已经准备好了。
名称：XXX
保存位置：XXX

接下来我们可以先准备这些可复用资源。它们会先作为本地资源保存在这个 Garden 中，不需要马上绑定到某个模型。

1. 创建 Schedule
2. 创建 Construction Set、Construction 或 Material 等内容
3. 创建 Program、People、Ventilation、Equipment、Infiltration、Setpoint、Lighting、SHW 等内容
4. 创建 Modifier Set 或 Modifier

如果您还没有明确目标，可以先从 Schedule（时间表）或 Construction Set（构造集）开始。
```

English example:

```text
The Garden is ready.
Name: XXX
Save location: XXX

We can prepare reusable resources next. They should first be managed as local resources in this Garden, and they do not need to be attached to a model immediately.

1. Create a Schedule
2. Create a Construction Set, Construction, or Material
3. Create a Program, People, Ventilation, Equipment, Infiltration, Setpoint, Lighting, SHW, or another related Energy resource
4. Create a Modifier Set or Modifier

If you do not have a clear target yet, it is usually best to start with a Schedule or a Construction Set.
```

platform_collaboration next prompts:

- Grasshopper is the only supported external interface for this route right now.
- Present the current Grasshopper component set in the onboarding reply: `FP Garden List`, `FP Create Garden`, `FP Honeybee Link`, `FP Energy Properties Input`, and `FP Radiance Properties Input`.
- Explain the recommended connection pattern: use `FP Garden List` to continue an existing Garden or `FP Create Garden` to start a new one, then pass the returned Flowerpot into `FP Honeybee Link`; use the two Properties Input components only as library readers on the same Flowerpot.
- Explain the MCP collaboration pattern: Grasshopper handles visible graph editing and geometry interaction, while MCP handles natural-language edits, resource authoring, validation, and compact result summaries against the same Garden or active Flowerpot context.
- After the collaboration link is understood, focus MCP suggestions on tasks such as modify HVAC, create a program and apply it to rooms, edit windows/shades, validate the model, or export a simple preview.

Chinese example:

```text
Garden 已经准备好了。
名称：XXX
保存位置：XXX

当前外部界面协作先支持 Grasshopper。为了和 MCP 配合，您可以先了解这 5 个组件：

1. FP Garden List：列出已有 Garden，并输出可继续使用的 Flowerpot
2. FP Create Garden：创建一个新的 Garden，并输出 Flowerpot
3. FP Honeybee Link：把 Honeybee Model 写入 Garden，或从 Garden 跟随当前模型
4. FP Energy Properties Input：读取这个 Garden 中已有的 Energy 资源
5. FP Radiance Properties Input：读取这个 Garden 中已有的 Radiance 资源

推荐连线方式如下：

- 如果您要继续已有 Garden，先用 FP Garden List 找到它，再把输出的 Flowerpot 接到 FP Honeybee Link
- 如果您要从新 Garden 开始，先用 FP Create Garden 创建它，再把输出的 Flowerpot 接到 FP Honeybee Link
- 两个 Properties Input 组件都应连接同一个 Flowerpot，它们负责读取资源，不负责直接把资源应用到模型

与 MCP 的协作方式如下：

- Grasshopper 更适合做组件连线、几何草模、参数滑块调试，以及需要即时图形反馈的操作
- MCP 更适合做自然语言驱动的模型编辑、可复用资源创建、模型检查验证，以及结果整理

如果您希望我先给建议，通常推荐把几何和交互式搭建留在 Grasshopper，把 Program / HVAC / Construction / Modifier、窗和遮阳的批量调整，以及模型验证交给 MCP。

您想先让我带您连组件，还是已经连好了，直接开始编辑当前模型？
```

English example:

```text
The Garden is ready.
Name: XXX
Save location: XXX

Grasshopper is the only supported external collaboration interface right now. To work with MCP, start from these five components:

1. FP Garden List: list existing Gardens and output a reusable Flowerpot
2. FP Create Garden: create a new Garden and output a Flowerpot
3. FP Honeybee Link: write a Honeybee Model into the Garden, or follow the current model from the Garden
4. FP Energy Properties Input: read existing Energy resources from this Garden
5. FP Radiance Properties Input: read existing Radiance resources from this Garden

Recommended wiring:

- To continue an existing Garden, use FP Garden List first and pass its Flowerpot into FP Honeybee Link
- To start from a new Garden, use FP Create Garden first and pass its Flowerpot into FP Honeybee Link
- Both Properties Input components should use the same Flowerpot; they read resources but do not apply them directly to the model

Recommended collaboration pattern:

- Grasshopper is better for graph wiring, geometry sketching, slider-based tuning, and operations that need immediate visual feedback
- MCP is better for natural-language model edits, reusable resource authoring, model validation, and compact result summaries

If you want a default split, keep geometry and interactive setup in Grasshopper, and use MCP for Program / HVAC / Construction / Modifier work, batch window or shade adjustments, and model validation.

Should I guide you through the component wiring first, or is your link already ready and you want to edit the current model directly?
```

## Existing Workspace Context

If the thread already has a stable `garden_root`, Garden target, or current Flowerpot context, do not force the welcome flow again. Ask whether to continue with the current Garden in the user's trigger language.

Chinese trigger example:

```text
我看到当前已经有一个 Garden 上下文。要继续使用这个 Garden，还是切换/创建另一个？
```

English trigger example:

```text
I see an existing Garden context. Should we keep using this Garden, or switch/create another one?
```

If the user confirms the current Garden, continue from that context and route by the saved direction label.

## Boundaries

- The Garden gate is mandatory for the three top-level authoring flows. Do not jump directly into route `29`, `30`, or `31` before the Garden is created or selected.
- The gate does not make Garden mandatory for every read-only, payload-only, debug, or documentation question.
- If the user refuses to continue, end the Ladybug Tools MCP flow and do not jump into modeling, resource generation, or collaboration skills.
- If the user only gives vague small talk and will not choose a top-level direction, keep clarifying the top-level entrance. Do not infer a downstream scenario.
- Flowerpot remains an opaque dict; do not ask users to unpack internal Flowerpot fields.
- Only describe a concrete downstream tool sequence as recommended when a real Agent or equivalent external run has verified it. Otherwise describe it as a candidate direction.
