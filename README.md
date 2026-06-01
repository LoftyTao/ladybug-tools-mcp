# Ladybug Tools MCP

![Ladybug Tools MCP Header](resources/GitHub-Obsidian-header-flowerpot-garden.png)

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文（ZH）</a>
</p>

## Overview

Ladybug Tools MCP is an MCP service built with FastMCP for agent applications. Through natural-language conversation, users can use the core capabilities of Ladybug Tools for common workflows including modeling, editing, querying, simulation, and data visualization, and can do so without depending on a CAD interface.

Please note that this project does not have any funding support, so it may remain in a long-term experimental stage. Please use it carefully.

There is a fairly large demo GIF here, so it may take a moment to load.

![Opencode Honeybee Modeling Flow](resources/remotion/snapshots/videos/opencode-honeybee-modeling-vtkjs-flow-en/opencode-honeybee-modeling-vtkjs-flow-en-latest.gif)

This project has been built entirely by Codex, including the source code and all demo images. GPT 5.4 and GPT 5.5 were used for project development, MiniMax 2.7 was used for focused and partial tool-call testing, and GPT 5.4 Mini was used for complete cross-functional workflow testing. The overall cost is roughly 5 billion tokens per month.

## Version 1.1.0 Highlights

Ladybug Tools MCP `v1.1.0` focuses on two project-level changes:

- Ironbug is now represented through a repository-local, pure Python API layer instead of relying on the earlier C# console path for authoring and validation.
- Web View Mode now uses the FastMCP Apps protocol for the primary vtk.js preview surface. Hosts with MCP Apps UI support can render the preview directly in a sandboxed app panel. FastMCP's current [Apps documentation](https://gofastmcp.com/apps/quickstart) shows this host-rendered path with examples such as Claude Desktop and Goose; clients that do not advertise the Apps UI extension can still use the returned local `127.0.0.1` fallback URL.

## Contents

- [Overview](#overview)
- [User Groups](#user-groups)
- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [FastMCP App Preview Mode Beta](#fastmcp-app-preview-mode-beta)
- [First Use](#first-use)
- [Workflow Examples](#workflow-examples)
- [Main Tools](#main-tools)
- [How to Contribute](#how-to-contribute)
- [Todo](#todo)
- [Acknowledgements](#acknowledgements)
- [Open Source License](#open-source-license)
- [Contact](#contact)

## User Groups

The original purpose of Ladybug Tools MCP is to turn design or technical concepts into concrete outputs quickly. For example, when a professor explains “What is a Trombe wall?” in a building technology course, a student can open Codex voice mode during the lecture, and by the time the explanation is finished, Codex can already transform the concept into inspectable models and files, together with graphical workflow output.

For that reason, the main target users are students and teachers, followed by building professionals and senior engineers. They may want an agent to take over some tedious work, while still keeping the final choice for most tasks in their own hands. For users who do not know much about 3D software workflows, Ladybug Tools MCP can also serve as a way to experience the Ladybug Tools ecosystem.

## Core Concepts

Ladybug Tools MCP is different from Ladybug Tools as used inside Rhino / Grasshopper. To use it well, it helps to understand several core concepts of this project, including MCP, agents, skills, tokens, Garden, and Flowerpot.

### Model Context Protocol

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) is an open standard used to connect external systems to agent applications. For most users, Ladybug Tools provides a user interface for human interaction inside Rhino / Grasshopper. Ladybug Tools MCP, by contrast, is a toolbox that an agent can call through natural language. It packages the core capabilities of the Ladybug Tools Core SDK into a standardized set of tools and usage guidance, and exposes them through MCP so that agent applications can call them.

### Agent

An [Agent](https://openai.github.io/openai-agents-python/agents/) is a large language model with instructions and tools. Ladybug Tools MCP is usually called as a toolset from inside an agent application.

### Agent Skills

[Skills](https://agentskills.io/home) are a practical way to turn prompt engineering into reusable operating guidance. By summarizing domain knowledge and workflows in Markdown, they provide an “instruction manual” that helps an agent follow your intent more reliably.

### Tokens

Tokens are the unit used to calculate cost in agent applications. Models differ in performance, speed, and token pricing, but I still recommend using the best and most cost-effective model you can reasonably access if you want a good Ladybug Tools MCP experience.

For practical Ladybug Tools use, a context window of at least 258K is usually needed, together with a sufficiently large Coding Plan subscription. Because of cost, I cannot test broadly across many subscription models, but for GPT Plus users, it should generally be possible to complete three to four complex model creation and editing tasks every five hours inside Codex.

### Garden

A Garden is the local path used to store and manage everything generated by Ladybug Tools MCP. The main outputs inside it are tracked through Git.

Because agent applications can easily do things beyond expectation in real work, a large part of this project has been about constraining the agent’s attention inside the Garden. This has been one of the main successful lessons from several months of development practice.

### Flowerpot

Flowerpot is the intermediary layer used by Ladybug Tools MCP to exchange information with other non-agent interfaces. For example, the Flowerpot components we developed for Ladybug Tools mainly act as relay plugins inside the ecosystem, with the goal of helping users complete the necessary manual work.

Because we want users to keep as much attention as possible on the interaction with the agent, instead of returning to manual production steps, we have not tried to build separate platform UIs for Ladybug Tools MCP. Instead, we recommend that you make good use of existing Ladybug Tools infrastructure and then pass data and information through Flowerpot.

## Quick Start

### Prerequisites

Before using Ladybug Tools MCP, some system prerequisites usually need to be configured. At minimum, that often includes:

- Python 3.12
- Ladybug Tools runtime matching the current `v1.1.0` matrix below
- Git
- uv
- Any agent application, such as [Codex](https://chatgpt.com/codex), [Claude Code](https://code.claude.com/docs/en/desktop-quickstart), [Open Code](https://opencode.ai/), or [OpenClaw](https://openclaw.ai/)

If you are not familiar with agent applications, I am very happy to recommend [Codex](https://chatgpt.com/codex).

Please note that Ladybug Tools is a complete ecosystem and is still being actively updated, so these prerequisites can move over time. The table below records the Ladybug Tools MCP `v1.1.0` source-release runtime expectation as of 2026-06-01. It follows the style of the upstream [Ladybug Tools compatibility matrix](https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix), removes Rhino, and adds the THERM runtime that this project can report through `get_ladybug_tools_config`. Ironbug authoring now runs through the project-local Python layer, so Ironbug.Console is no longer a required runtime for normal MCP workflows.

| Ladybug Tools MCP | Python | Radiance | OpenStudio SDK | EnergyPlus | OpenStudio App | URBANopt CLI | THERM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `v1.1.0` | 3.12 | 5.4 (2023-11-05) | 3.10.0 | 25.1.0 | 1.10.0 | 1.2.0 | 8.1.30 beta |

This project does not install these external runtimes for you. Choose the workflows you need, install the corresponding runtimes manually, and use `get_ladybug_tools_config` to inspect what the local SDK configuration can read. When a runtime cannot be found, the Config tool returns documentation links and install hints instead of trying to download or configure it.

### Installation Guide

If you do not really know what MCP is and do not want to do the setup manually, you can hand this job over to [Codex](https://chatgpt.com/codex) or another agent application.

Using Codex as an example, you only need to:

- Install Codex.
- Open a local workspace.
- Send this project link to Codex.
- Say:

```text
Help me install and configure the MCP from this project into this workspace.
```

#### Local Installation Commands

Run the following commands in the target workspace. Replace `<repo-url>` with the repository URL of this project and `<repo-dir>` with the cloned folder name.

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

Then run the following on all systems:

```bash
git clone <repo-url>
cd <repo-dir>
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
uv pip install -e .
uv run python -c "import ladybug_tools_mcp; print(ladybug_tools_mcp.__version__)"
```

`requirements.txt` is pinned for a reproducible user install. Maintainers who intentionally want the floating development dependency set can install `requirements-dev.txt` instead.

#### MCP Configuration Examples

Replace `<absolute-repo-path>` with the absolute path of this repository on your machine, and replace `<python-command>` with the Python executable inside this project’s virtual environment.

Windows:

```text
<absolute-repo-path>\.venv\Scripts\python.exe
```

macOS / Linux:

```text
<absolute-repo-path>/.venv/bin/python
```

Codex uses TOML:

```toml
[mcp_servers.ladybug-tools-mcp]
command = "<python-command>"
args = ["-m", "ladybug_tools_mcp.server"]
cwd = "<absolute-repo-path>"
```

Cursor, OpenCode, or other agent applications that use `mcpServers` can use JSON:

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

Claude Code is recommended to add the local stdio MCP through the CLI:

```text
claude mcp add ladybug-tools-mcp -- "<python-command>" -m ladybug_tools_mcp.server
```

If you need project-level shared configuration, you can use:

```text
claude mcp add ladybug-tools-mcp --scope project -- "<python-command>" -m ladybug_tools_mcp.server
```

Claude Code project-level `.mcp.json` files also use the `mcpServers` structure:

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

OpenClaw uses `mcp.servers` in its MCP client registry:

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

After configuration is finished, restart the agent application and confirm that the MCP server is connected.

#### Grasshopper Component Path

If you need to use the GHPython components in `src/grasshopper_components/`, Grasshopper also needs to be able to find the project source.

It is recommended to set an environment variable first:

Windows PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("LADYBUG_TOOLS_MCP_ROOT", "<absolute-repo-path>", "User")
```

macOS / Linux:

```bash
export LADYBUG_TOOLS_MCP_ROOT="<absolute-repo-path>"
```

If you need to copy the component scripts to another machine or deliver them independently, also check and modify `_DEVELOPMENT_SRC_ROOT` near the top of each `FP *.py` file. On Windows it should point to:

```text
<absolute-repo-path>\src
```

On macOS / Linux it should point to:

```text
<absolute-repo-path>/src
```

These components add that path into `sys.path` at startup so they can load `flowerpot.runtime` and the Grasshopper collaboration code inside the project.

## FastMCP App Preview Mode Beta

Web View Mode is an experimental FastMCP App preview mode for live modeling sessions. It lets a host application render the current Garden preview through vtk.js while an agent creates or edits Honeybee, Dragonfly, Fairyfly, or VisualizationSet outputs.

FastMCP Apps let a tool return a UI resource, which the host renders in a sandboxed iframe when the host supports the MCP Apps UI extension. The official [FastMCP Apps quickstart](https://gofastmcp.com/apps/quickstart) uses host-rendered examples such as Claude Desktop and Goose, and also provides `fastmcp dev apps` for local browser preview during development. Host support still varies. When a client does not advertise the Apps UI extension, Ladybug Tools MCP returns a local fallback URL that serves the same Garden-backed preview from `127.0.0.1`.

### Enable

Ask the agent to enable Web View Mode before modeling or editing:

```text
Enable Web View Mode for this Garden, then create or edit the Honeybee model.
```

In MCP terms, the agent calls:

```text
start_web_view_mode(garden_root, name="...")
```

Starting the mode creates a Garden-local Web View session and returns the FastMCP App metadata for the host. If the host cannot render the App iframe, the result also includes a local `viewer.url`, usually:

```text
http://127.0.0.1:3127
```

The MCP service does not force-open a system browser. Hosts with MCP Apps support should render the returned `ui://web_view/ladybug-tools/vtkjs-preview.html` resource. Hosts without that support, including current Codex runs that report `client_supports_ui_extension=false`, should open the returned fallback URL when a visible preview is needed.

### Close

Ask the agent to stop Web View Mode, or call:

```text
stop_web_view_mode(garden_root)
```

This disables future automatic previews and stops the matching local fallback viewer if one was started. Preview history under `tmp/web_view/` is preserved.

### Difference From Ordinary Mode

In ordinary mode, modeling tools write Garden files and return compact targets, summaries, and receipts. No viewer server is started, and no automatic preview file is exported after every edit.

In Web View Mode, significant Honeybee, Dragonfly, Fairyfly, and VisualizationSet operations automatically export session-managed `.vtkjs` previews under:

```text
<garden>/tmp/web_view/previews/
```

The App polls Garden session state and reloads the latest `.vtkjs` package without a manual refresh. These automatic previews are local session state, not formal user-requested Garden artifacts. If you need a durable reusable artifact, still ask the agent to export a VisualizationSet with `visualization_set_to_vtkjs`.

The fallback viewer intentionally uses an explicit local port. If the requested port is already occupied, startup fails clearly instead of silently choosing another port or leaving the browser pointed at an older Garden.

## First Use

After the MCP server is configured in your agent application, start a new thread and ask it to use Ladybug Tools MCP. In Codex, the most direct path is to configure the server in `~/.codex/config.toml` with the TOML example above, restart Codex, then describe the Garden or modeling task directly.

If your host supports skills, invoke the `ladybug-tools-mcp-use` skill with `/`, then input `HI , Ladybug Tools !` to activate the onboarding flow for the three main usage intents that we provide. After the onboarding is complete, you can start building according to your intent.

![Welcome Flow](resources/remotion/snapshots/videos/opencode-onboarding-flows/welcome-fixed-3-options-en-latest.gif)

In general, the agent application will output the onboarding template according to the guidance in our skills, but the actual result still depends on the host application’s instructions and the base capability of the language model. I strongly recommend that you use the best model available within your means in order to use our tools more effectively.

## Workflow Examples

It is normal to feel a bit lost when you first start using it, so please do not give up.

In our cross-testing set, we have successfully made agent applications complete the following kinds of work. The stability and token cost of these workflows have become relatively steady, and I believe they are a good place to begin learning.

### Build a small model from a blank project

- Create a new Garden.
- Create a Honeybee Model.
- Create one or two Rooms.
- Add windows, doors, and shades to exterior walls.
- Check whether the model has missing faces, broken adjacencies, or boundary-condition issues.

### Continue editing an existing model

- Find the specified room, wall, window, or door.
- Modify the location, dimensions, and construction of windows.
- Add low-U-value windows, heavy wall constructions, occupant loads, and equipment loads.
- Assign program types, setpoints, and a simple HVAC system to rooms.
- Re-check the model after editing.

### Building performance simulation workflow

- Search for and download the EPW weather file for a specified city.
- Save the weather file into the Garden.
- Start an Energy simulation.
- Read EUI, error information, and some hourly results.
- Export the results as monthly charts, hourly charts, or HTML pages.

### Prepare reusable Energy resources

- Create schedules, program types, construction sets, setpoints, and HVAC templates.
- Save them into the Garden Properties Library.
- Search for and reuse these resources in later models.
- For incomplete sources, record only what can be determined and do not invent material layers or window parameters.

### Author custom HVAC with Ironbug

- Create Ironbug DetailedHVAC objects for coils, fans, pumps, boilers, chillers, terminals, plant loops, air loops, setpoint managers, and output requests.
- Assemble source-backed custom HVAC systems such as PTAC, PTHP, FCU, DOAS, VAV, VRF, boiler reheat, chiller plant, and condenser-water loop cases.
- Link Ironbug ThermalZone objects to Honeybee or Dragonfly rooms, then apply the DetailedHVAC model before running the standard Energy simulation workflow.
- Use the Ironbug workflow when an HVAC Template is too coarse and you need object-level loop topology, child components, and OpenStudio / EnergyPlus-facing equipment intent.

### Do basic Radiance work

- Create skies, WEA files, sky matrices, sensor grids, and views.
- Assign Radiance modifiers to model objects.
- Start grid or view simulations.
- Read HDR, falsecolor, GIF, or annual daylight metrics.
- Convert the results into inspectable visualization sets.

### Connect Grasshopper and the agent

- Use Flowerpot components in Grasshopper to hand over the current model or project context.
- Let the agent continue modeling, editing, saving, and validating in the Garden.
- Let the Grasshopper side continue to handle manual selection, preview, and the necessary manual operations.
- This is suitable for a workflow where geometry is handled in the interface and organization plus long-chain tool use is handled by the agent.

### Preserve and restore project state

- Create a Garden Version before important operations.
- Try modifying the model or simulation resources.
- If the result is unsatisfactory, restore to the earlier version.
- After restoration, continue exporting HTML / SVG and other inspection outputs.

## Main Tools

Ladybug Tools MCP is not suitable for being a tiny MCP service with only a handful of tools. Because of the breadth of the application domain, I will only briefly list the currently supported and relatively stable tool areas here. For a detailed tool list, you can always ask your agent application.

### Project and environment

- Query the local Ladybug Tools runtime configuration
- Create, search, read, and clean Gardens
- Save, read, and switch the Garden Base Model
- Create, list, inspect, and restore Garden Versions
- Search models, objects, files, and artifacts inside the Garden

### Flowerpot collaboration

- Create Flowerpot platform handoff records
- Read the current Flowerpot context
- Retrieve and clean Flowerpots
- Support Grasshopper components in handing models, resources, and interaction context over to the Garden

### Model creation

- Assemble Honeybee Models
- Create Rooms, Faces, Doors, Apertures, and Shades
- Batch-create Apertures and Shades from parameters
- Save creation results as Targets that can continue to be called inside the Garden

### Model editing

- Search for and locate objects inside a Honeybee Model
- Validate Honeybee Models
- Change object geometry (Ladybug Geometry)
- Change object boundary conditions (Boundary Condition)
- Change object types (Face Type)
- Move, rotate, scale, and mirror objects
- Delete Rooms, Faces, Doors, Apertures, and Shades
- Relate model objects and organize adjacency relationships

### Property resources

**Energy**

- Create Program Type and Loads
- Create People, Lighting, Equipment, Infiltration, Setpoint, Ventilation, and Service Hot Water
- Create Schedule Day, Schedule Rule, and Schedule Ruleset
- Create Construction Set, Construction, and Material
- Create Ideal Air System
- Search HVAC Template
- Create Ventilation Control and AFN
- Create Daylighting Control
- Create PV Properties and Electric Load Center

**Ironbug DetailedHVAC**

- Create DetailedHVAC component objects for fans, pumps, coils, boilers, chillers, heat exchangers, setpoint managers, availability managers, terminals, zone equipment, and plant equipment
- Create semantic hot-water, chilled-water, and condenser-water loops from source-backed supply and demand components
- Create AirLoop, PlantLoop, ThermalZone, OutdoorAirSystem, Existing Object, Node Probe, EMS, and output-variable records
- Search, validate, and assemble Ironbug models saved in the Garden
- Prepare custom HVAC systems for the Energy workflow after Room energy properties and setpoints are in place

**Radiance**

- Create Modifier Set and Modifier
- Create Glass, Metal, Mirror, Opaque, and Trans Modifier
- Create Sensor Grids
- Create Views
- Create WEA and Sky
- Create Sky Matrix and Radiance Parameters
- Create Dynamic Groups
- Create Shade State, SubFace State, and State Geometry
- Create Luminaires and Lamps

**Garden Library**

- Save Energy and Radiance property resources into the Garden Properties Library
- Search and read Garden Properties Library objects
- Standardize the Garden Properties Library storage structure

### Simulation

**Energy**

- Search for and download EPW weather files
- Create Energy Output Requests
- Start, poll, list, and read Energy Runs
- Read ERR, EUI, and result data
- Export Energy hourly charts and monthly chart HTML

**Radiance**

- Start Grid, View, and Matrix Radiance Runs
- Poll, list, and read Radiance Runs
- List Grid Results, HDR Images, and Artifacts
- Summarize Annual Daylight Metrics
- Summarize Glare Metrics
- Generate Falsecolor and GIF
- Convert Radiance results into Visualization Sets

### Visualization and export

Visualization is one of the main capabilities that lets Ladybug Tools MCP operate away from CAD platforms, and I strongly recommend that you get familiar with it.

- Convert Honeybee Models, Rooms, and Faces into Visualization Sets
- Convert DataCollections into charts, files, and Visualization Sets
- Compose multiple Visualization Sets
- Create and edit 2D Legend Parameters
- Export HTML, vtk.js, and SVG visualization artifacts

## How to Contribute

Because this project is built to a very large extent through agent-assisted development, I do not reject contributions made with agent applications. However, there are several principles that need to be followed so that the project does not grow in an uncontrolled way.

- [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation) is the core of all MCP tools in this project. If the tool you want to add is not within the scope of the SDK, then this project should not be the place for the follow-up implementation. In that case, it is more appropriate to contribute directly to the Ladybug Tools project itself.
- All new tool development should first go through an open GitHub Issue discussion, and the discussion content and development plan should be led by humans.
- Only write code that solves the current problem. If an AI code review points out issues that you have not actually encountered in normal usage scenarios, then we should not handle those issues.
- Better to have too few tools than too many; do not add entities unless they are truly necessary.
- If these principles can be followed, I would be very happy for you to join this community-driven maintainer group.

## Todo

These are the main directions for later development. Before there is a broad user signal telling us otherwise, the project will continue to expand in these directions.

- [ ] Dragonfly Model creation and editing tools
- [ ] Add UrbanOpt support
- [ ] More Visualization Set pre-processing and post-processing support
- [ ] Expand retained Ironbug Energy acceptance cases for more custom HVAC topologies
- [ ] Web View and Model Editor tools for direct agent collaboration
- [ ] A demo mode that can visualize all processes and steps
- [ ] Cloud service support
- [ ] ...

Most of these items have already been proven effective in the test environment and will appear in the near future.

## Acknowledgements

Special thanks to the [Ladybug Tools community](https://discourse.ladybug.tools/) and the [Ladybug Tools team](https://www.ladybug.tools/about.html#team):

- **Mostapha** [raised the priority of Pydantic compatibility](https://discourse.ladybug.tools/t/upgrade-to-pydantic-2-0/36437/9), which greatly reduced the development difficulty of this project.
- **Chris** helped make the `.svg` format of [Visualization Set](https://discourse.ladybug.tools/t/bug-of-dumpvisset-or-incomplete-known-issues/39972) the main model visualization scheme for the MCP workflow, which made it possible for us to fully inspect built content without relying on a CAD interface.

Beyond that, the implementation core of this project remains the [Ladybug Tools Core SDK](https://discourse.ladybug.tools/pub/ladybug-tools-core-sdk-documentation), which is the result of many years of development by the Ladybug Tools team.

## Open Source License

Ladybug Tools MCP is released under the GNU General Public License Version 3 (GPL v3), consistent with the open source license used by the Ladybug Tools project.

## Contact

You can contact me through the following methods:

- Email: `loftytao@foxmail.com`
- WeChat: `LoftyTao`

If someone can offer some Codex or Claude Code tokens, or even a subscription plan, that would be even better. I would really appreciate that kind of support.
