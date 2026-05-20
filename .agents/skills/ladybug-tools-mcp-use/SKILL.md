---
name: ladybug-tools-mcp-use
description: Use when operating Ladybug Tools MCP through FastMCP Code Mode, including the exact trigger phrase `Ladybug Tools MCP，测试开始` for user-led subagent testing, verified Garden-mode paths, base-model confirmation, or failure-diagnosis guidance.
---

# Ladybug Tools MCP Use

Use Code Mode for multi-tool workflows.
Use only Code Mode for Ladybug Tools MCP workflows. The only outer MCP tools are `search`, `get_schema`, and `execute`; call domain tools only inside `execute` via `await call_tool(...)`.
Do not use the removed top-level Tool Search / Call Tool entrypoints, and do not call domain tools as outer MCP tools.
Use Garden mode and do not request full large payloads by default.

## Onboarding and Intent Triggers

- If the user says the exact trigger phrase `Ladybug Tools MCP，测试开始`, enter user-led subagent testing mode. Spawn the project-scoped `ladybug_mcp_tester` custom agent, which uses `gpt-5.4-mini`, and pass it the user's testing task. Do not spawn this testing subagent for any other wording or by Agent initiative.
- If the user greets Ladybug Tools MCP with `你好！Ladybug Tools!`, `Hi, Ladybug Tools!`, or a similarly broad start, answer with the friendly fixed-structure `Bug Flyzzzzzzzzz!` welcome in the onboarding reference and ask for one of the three numbered top-level directions.
- Match the user's trigger language for onboarding replies. A mixed-language greeting like `Hi，Ladybug Tools！` counts as English. Do not default to Chinese unless the user used Chinese or the language is unclear.
- Keep `direction_label` values internal. Do not show `direction_label:` lines in the user-facing welcome; save the chosen label internally and continue into the Garden gate.
- Any option selection routes to the same Garden gate. After option 1, 2, or 3, ask whether the user already has a Garden to continue with or wants to create one; do not start modeling, resource creation, or Grasshopper collaboration before this gate.
- In the Garden gate, call `list_gardens` when possible and show the five most recent Gardens from `matches[:5]`. If more than ten Gardens exist, suggest cleanup and offer to help, but do not delete or clean anything without explicit confirmation.
- After Garden creation or selection, use the saved direction label to offer a short next-step menu: modeling/object creation for `natural_language_modeling`, reusable resources for `reusable_resource_preparation`, and Grasshopper component-link plus model-edit guidance for `platform_collaboration`.
- If the user directly asks for natural-language modeling, reusable simulation resources, or Rhino / Grasshopper collaboration, save the matching top-level direction label internally and still enter the Garden gate before downstream authoring tools.
- Use Garden as the user-facing product concept for persistent project context. Use `list_gardens`, `create_garden`, and `get_garden` for the Garden gate; do not invent `workspace_*` tools or call the Garden a workspace in onboarding copy.
- If a stable `garden_root`, Garden target, or current Flowerpot context already exists, ask whether to continue with that Garden instead of restarting the welcome flow.

## Core Rules

- Prefer explicit Garden root, object names, and target actions.
- When using Code Mode, keep intermediate SDK dicts and targets inside the `execute` block and return only final target, summary, receipt, or compact diagnostics.
- For create/edit/simulate workflows, do the dependent chain in one `execute` block whenever possible. Use local variables for tool results and return one compact final dictionary; do not make one `execute` call per MCP tool unless you are debugging a specific failing step.
- For common Ladybug Tools create/edit/simulate workflows, use `execute` as the first outer tool and call likely domain tools by name inside it. Use `search`/`get_schema` only after a tool name or parameter shape is actually unknown.
- For large create/edit/simulate requests, split work into the staged energy workflow: Stage A model/rooms, Stage B subfaces/shades, Stage C Energy properties/HVAC, Stage D weather/run, and Stage E outputs. Each stage resumes from Garden state, returns a compact stage summary, and stops after the requested stage is complete.
- For Stage C or any request that asks to validate a Honeybee model or return a validation flag, call `validate_honeybee_model`; use `validate_honeybee_model`, not `get_base_honeybee_model`, because `get_base_honeybee_model` only confirms the Garden base Honeybee model target/summary.
- If a long `execute` block fails after some write calls have already succeeded, do not replay the whole script. Garden writes are persistent; resume with a smaller repair block, search existing targets if needed, and continue from the failed step.
- Public tool arguments use one canonical lowercase `snake_case` name. Use `garden_root`, `model_target`, `host_target`, `object_type`, and `return_object_dict`; do not use historical names such as `_garden_root`, `garden_root_`, `_target`, or `object_type_`.
- `create_garden` is the common Garden-root exception: it takes the folder path as `root_dir` and returns the reusable top-level `garden_root` string. Do not call `create_garden` with `garden_root`.
- For blank-project workflows, the first `execute` block must call `create_garden` before any tool that takes `garden_root`; creating the folder yourself is not enough because Garden tools require `garden.json`.
- For workflows that start from an existing Garden path, set `garden_root` to that literal path before the first read or write call.
- Write tools persist Garden changes and return persistence receipts; do not search for `save_garden` or `save_base_honeybee_model` after successful create/edit calls unless the user explicitly asks for a separate save operation.
- Deterministic-pass/candidate: after completing a user-prompt-level workflow that changed Garden authoring truth (`garden.json`, `models/`, or `libraries/`), call `create_garden_version` once with a compact subject and structured summary. Do not call it after every low-level write; save one version for the completed user request.
- Deterministic-pass/candidate: for undo, go-back, or restore requests, call `list_garden_versions`, choose by subject/summary, then call `restore_garden_version`. Do not request Git diffs or file bodies; inspect the restored model with Search, Validate, or Visualize tools if needed.
- For reusable Energy/Radiance library objects, prefer direct Garden-saving create tools with `garden_root` and `return_object_dict=false` when available; for schedules that do not need time-series inspection, also set `include_data=false`. Use `save_garden_properties_library_object` only when the user already has a full `object_dict` to store.
- `create_honeybee_model` takes `identifier`; do not use `model_name`. It does not take `return_object_dict` or `display_name`; it already returns compact targets unless `include_body=true` is explicitly requested for a debug/export need.
- Honeybee and Dragonfly model create tools use the boolean `set_base`, not `set_as_base`.
- Honeybee and Dragonfly base model slots are separate. Use `get_base_honeybee_model` for Honeybee and `get_base_dragonfly_model` for Dragonfly; the generic model-slot tools are not public.
- Deterministic-pass: for DOE INP or DesignBuilder dsbXML model file export, call `export_model_file` with `garden_root`, `export_format`, and the exact Honeybee Model or Dragonfly Model `model_target`. Get the base target first with `get_base_honeybee_model` or `get_base_dragonfly_model` when the user wants the current base model; do not pass a generic model family field.
- Agent-verified: for Dragonfly authoring, call `create_dragonfly_model`, then `create_dragonfly_room2d`, then `create_dragonfly_story`, then `create_dragonfly_building` in order, then use `edit_dragonfly_model`, `edit_dragonfly_story`, `edit_dragonfly_building`, `edit_dragonfly_room2d`, `search_dragonfly_model_objects`, `get_dragonfly_model_summary`, `validate_dragonfly_model`, `dragonfly_model_to_visualization_set`, and optionally `dragonfly_model_to_honeybee`. Dragonfly Energy ProgramType/ConstructionSet application is available through `apply_dragonfly_energy_properties` for Room2D, Story, and Building targets. Dragonfly Radiance ModifierSet and grid-parameter application is available through `apply_dragonfly_radiance_properties`; grid parameters support Room2D and Building targets, not Story targets. Keep the chain in one Code Mode `execute` block when possible. The retained OpenAI Agents SDK 40-task cross run passed in one `execute` after tool-surface fixes; do not add generic model-slot tools or recovery wrappers to smooth removed paths.
- For Web View demo mode, call `start_web_view_mode` once at the start of the relevant Garden workflow; do not invent `set_dragonfly_web_view_demo_mode`, `open_browser`, `refresh_viewer`, or a Dragonfly-specific preview tool. After Web View Mode is active, significant Dragonfly edits, properties, conversions, and VisualizationSet outputs automatically create local session previews under `tmp/web_view/previews/`; do not call `visualization_set_to_vtkjs` after every edit just to refresh the panel.
- For Dragonfly property tools, the canonical target field is `host_target`. Use exact library identifiers such as `Generic Office Program`, `Default Generic Construction Set`, and `Generic_Interior_Visible_Modifier_Set` when no project-specific library search is needed. If applying a grid parameter, include a modest grid size such as `grid_dimension=0.7`.
- For Dragonfly Story adjacency, use a Story target with `story_target` or a Story identifier with `story_identifier`; do not pass a Building target as a generic `target`, and do not invent adjacency add tools.
- Deterministic-pass with scaffolded Agent cross-suite: for Dragonfly UWG Alternative Weather workflows, use `get_dragonfly_uwg_properties_summary`, `apply_dragonfly_uwg_properties`, `create_uwg_simulation_parameter`, `dragonfly_model_to_uwg`, `start_uwg_run`, `get_uwg_run`, `list_uwg_runs`, and `list_uwg_run_outputs`. Prefer `start_uwg_run` plus polling for Agents; use the returned morphed `weather_file` target with existing Energy tools only when the user asks for downstream Energy simulation. Do not call or invent `run_urbanopt`; URBANopt Energy, Electric Grid, and District Thermal remain separate backlog directions. Fully natural UWG discovery still needs a later retained run.
- Agent-verified with scaffolded Code Mode: Fairyfly authoring and THERM runtime are Windows-only and depend on the `fairyfly` / `fairyfly_therm` packages plus THERM runtime availability. For Fairyfly or two-dimensional heat-transfer authoring, use `create_fairyfly_model`, `create_fairyfly_solid_material`, `add_fairyfly_shape_to_model`, `add_fairyfly_boundary_to_model`, `validate_fairyfly_model`, `fairyfly_model_to_visualization_set`, `visualization_set_to_vtkjs`, and `get_base_fairyfly_model` / `set_base_fairyfly_model`. `create_fairyfly_solid_material` returns an inline `object_dict`, not a Garden target. For THERM execution, use `write_fairyfly_model_to_thmz`, `start_fairyfly_therm_run`, `get_fairyfly_therm_run`, `read_fairyfly_therm_result`, `read_fairyfly_u_factor_result`, and `fairyfly_therm_result_to_visualization_set`; if THERM is unavailable, respect the returned `blocked` status instead of inventing results.
- `create_honeybee_room` writes the room into the Garden base Honeybee model and auto-attaches to the selected model. Do not pass `host_target`, and do not pass returned room targets into `edit_honeybee_model.add_objects`; use later edit/search tools directly against the returned target.
- For simple box rooms, `create_honeybee_room` takes `identifier`, `x_dim`, `y_dim`, `height`, and optional `origin`; do not use `room_name`, `width`, `depth`, `origin_x`, `origin_y`, or `origin_z`.
- For `edit_honeybee_room`, pass `search_honeybee_model_objects` `matches[i].target` or a returned `create_honeybee_room.target` as the value for the parameter named `target`; not `room_target`, not a room identifier, not the full search response, and not `matches[i]` itself.
- For parameterized windows, prefer `create_honeybee_apertures_by_parameters` with `generation_mode="by_ratio"` and top-level `ratio`, or `generation_mode="by_width_height"` with top-level `aperture_width` and `aperture_height`. Do not hand-write a large `parameters` object unless recovering from a schema mismatch.
- Parameterized aperture and shade creation returns `targets[]`; the top-level `target` is the first created object for simple follow-up handoff.
- For one-room facade Agent stages, avoid Grasshopper-style or invented helpers. `create_honeybee_apertures_by_parameters` and `create_honeybee_shades_by_parameters` do not take `run_after`, `run_checks`, or other boolean "execute after" flags. Do not call `add_honeybee_shade_by_boundaries`, `attach_radiance_sensor_grid`, `list_radiance_grid_runs`, `get_honeybee_model_summary`, `get_garden_properties_library`, or `search_energy_program_types`; use the canonical create/search/validate/run tools already listed in this Skill.
- For facade aperture/shade setup, search once for the target exterior Face, create one aperture by ratio, use the returned aperture `target` for one simplified overhang/louver shade, then validate once. If that block partially succeeds, resume from persisted typed targets instead of recreating apertures or shades in a loop.
- For construction sets, prefer `create_window_construction` with simple `u_factor / shgc / vt` and `create_construction_set` with Honeybee generic defaults or Garden targets. In an existing Garden, call `create_window_construction` with `garden_root` and `return_object_dict=false` so it returns a reusable Garden target; use that target for `create_construction_set.aperture_set`, not `save_to_library` and not a handwritten `WindowConstruction` dict. For a low-U window override, pass the returned window construction target directly as `create_construction_set.aperture_set`; do not create an intermediate `ApertureConstructionSet` unless you need multiple aperture slots. Do not pass hand-written `thickness / conductivity` material dicts directly to `create_opaque_construction`; use `create_opaque_material` first or a library identifier.
- For EPW weather, use `search_epw_map` without `garden_root`, then `download_epw` with the same `garden_root` and selected `epw_map_target`; there is no `download_weather_file` tool or separate weather folder path.
- `search_epw_map` takes a plain `query` string. For hot-humid China facade studies, `query="Sanya"` is known to return OneBuilding weather data; avoid over-specific suffixes such as `"Sanya China TMY3"` if they return no matches. If the selected weather search returns no matches, try one clearly named second query such as `"Miami"` and then stop with the saved failure/status instead of looping.
- For EPW weather charts or original EPW vs UWG morphed EPW comparisons, use `read_weather_file_data` to save SDK EPW fields as `ladybug_data_collection` targets, then pass those targets into `data_collection_monthly_chart_to_visualization_set`; do not parse EPW text by hand.
- For shade-attached photovoltaic setup, call `create_pv_properties` with a canonical `mounting_type`: `FixedOpenRack`, `FixedRoofMounted`, `OneAxis`, `OneAxisBacktracking`, or `TwoAxis`. Use `FixedRoofMounted`, not `FixedRoofMount`; do not invent `FlushMount`.
- For energy simulation in Agent workflows, prefer `start_energy_run` and poll `get_energy_run`; avoid blocking `run_energy` unless the user explicitly asks to wait for local completion.
- For post-run ERR diagnostics, call `read_energy_errors`; do not invent `read_energy_run_err` or pass ad hoc weather fields such as `weather_file_target` into `start_energy_run`.
- For a known completed energy run, use `start_energy_run` with `run_id` and `reload_old=true` to reload the completed ledger, then call `get_energy_run`, `list_energy_run_outputs`, and `read_energy_eui`; this must not start a new background run.
- Focused Agent-verified but still high-cost: for Radiance point-in-time grid/view workflows, use one setup checkpoint and one run/postprocess pass. Attach one SensorGrid or View, create one single-timestep sky and one parameter set, then call the matching `start_radiance_*_run` and `get_radiance_run(wait_seconds=60, poll_interval=2)`. Do not rebuild geometry, grids, views, skies, or parameters after they exist; search compact Radiance artifacts and resume from targets.
- Code Mode `execute` blocks are isolated. Variables from one `execute` call are not available in later calls. Do not use `import`, `os`, `pathlib`, `asyncio`, `asyncio.gather`, or parallel calls inside `execute`; call tools sequentially and use literal path strings from the prompt.
- In Code Mode `execute`, avoid compact Python iterator tricks over tool-result lists, especially `next(...)` with generator expressions. Use explicit `for` loops, assign a target variable, and return a compact diagnostic if no match is found; failed Agent runs have otherwise produced list/iterator errors and repeated searches.
- In Code Mode, do not instantiate `Garden` or SDK objects directly; use `await call_tool(...)` with MCP tool names.
- `execute` code is Python. Use `True`, `False`, and `None`, not JSON `true`, `false`, or `null`.
- Use `get_schema` only when `search` descriptions are insufficient; request brief schema first, and detailed schema only for the exact blocked tool.
- In Code Mode, `search` and `get_schema` are outer tools, not domain tools. Do not call `await call_tool("search", ...)` or `await call_tool("get_schema", ...)` inside `execute`.
- In Code Mode, do not use `print()` inside `execute`; stdout can corrupt stdio MCP transport. Return compact JSON-compatible data instead.
- Do not serialize tool results with `json.dumps` inside `execute`; return a dict directly.
- When the user says vague words like `模型`、`房间`、`墙`、`窗`, first narrow the request to the object level with Code Mode `search`/`get_schema` and `search_honeybee_model_objects`.
- When confirming a create/edit/remove result, verify with a follow-up read/search call instead of trusting the write call alone.
- When recovering from a partial write, use `search_honeybee_model_objects.children_scope` with the room/face/aperture/door target to inspect existing child objects before retrying writes such as aperture or shade creation. `children_scope` must be a typed target dict, not `true` and not `parent_target`.
- There is no `get_honeybee_model_summary` public tool. For Honeybee counts, room energy assignments, child object counts, and compact object evidence, use `search_honeybee_model_objects`; for validity use `validate_honeybee_model`.
- `search_honeybee_model_objects` matches for rooms, faces, apertures, and doors include compact `child_counts`; use those counts before making separate full-model room/face/aperture/shade inventory searches.
- For subface/shade stages, search rooms once, search exterior wall faces with `children_scope`, create apertures from returned face targets, then create shades from returned aperture/face targets; do not relist the whole model after each individual write.
- When confirming only Honeybee base model presence or retrieving the compact Honeybee base model target, call `get_base_honeybee_model`.
- When confirming an existing Garden manifest, call `get_garden`; do not use filesystem probes or Python imports inside Code Mode.
- Keep Flowerpot as an opaque dict and do not unpack internal fields manually.
- When the user is validating failure behavior, do not auto-recover by default.
- In Code Mode, do not call original domain tools as outer MCP tools. Use them only inside `execute` via `await call_tool(tool_name, arguments)`.
- Tool names returned by Code Mode `search` are strings for `execute`/`call_tool`, not callable outer tools. The outer callable tools remain only `search`, `get_schema`, and `execute`.
- Every `call_tool` invocation must include a non-empty JSON `arguments` object that uses the tool's exact required parameter names. If a required-argument validation error appears, rebuild the full arguments object from the latest search result, tool schema, or prompt instead of retrying the failed shape.
- When writing Windows paths inside JSON examples, escape backslashes or generate the arguments object with a JSON serializer.
- For multi-step write workflows, prefer one concrete tool call at a time. After a successful search, immediately call the next MCP tool with the target from that search instead of ending with a plan sentence.
- Avoid parallel write calls against the same Garden/model. The server serializes in-process Honeybee model writes, but Agents should still wait for each write result, then search or validate before the next dependent write.
- For downstream `target` / `host_target`, pass the nested typed target dict such as `matches[i].target` or a write tool's returned `target`. Do not pass full tool responses, `matches[i]`, or identifier-only dictionaries.
- Do not describe unverified tool paths as recommended. If a path is only a candidate or currently fails in natural-language runs, say so explicitly.

## Reading Order

Read only the most relevant reference file(s) for the current task.

- Welcome, Garden context, and intent routing:
  - `reference/onboarding-intent-triggers.md`
- Natural-language object discovery and search narrowing:
  - `reference/search-honeybee-model-objects-natural-language.md`
- Garden creation:
  - `reference/create-garden.md`
- Create Honeybee model and confirm Honeybee base model:
  - `reference/create-honeybee-model-and-confirm-base-model.md`
- Create Dragonfly model, Room2D, Story, Building, validate, display, UWG Alternative Weather, and convert:
  - `reference/dragonfly-authoring.md`
- Create Fairyfly model, material, shape, boundary, validate, THERM run/results, and VisualizationSet export (Agent-verified with scaffolded Code Mode):
  - `reference/fairyfly-authoring.md`
- Create Honeybee room:
  - `reference/create-honeybee-room.md`
- Create Honeybee apertures/windows by parameters:
  - `reference/create-honeybee-apertures-by-parameters.md`
- Create Honeybee interior doors on shared room walls:
  - `reference/create-honeybee-interior-door.md`
- Expand an existing live Honeybee model with rooms, adjacency, windows, and doors:
  - `reference/live-honeybee-model-expansion.md`
- Create Honeybee shades/louvers by parameters:
  - `reference/create-honeybee-shades-by-parameters.md`
- B-stage room -> exterior face -> aperture -> shade short path:
  - `reference/subface-shade-stage-short-path.md`
- Staged Energy create/edit/simulate workflow:
  - `reference/staged-energy-agent-workflow.md`
- Source-backed hot-humid Honeybee light/thermal facade case with Sanya weather, simplified shade, EnergyPlus, and point-in-time Radiance:
  - `reference/source-backed-light-thermal-facade.md`
- Ventilation, zone fan, PV, run, and result visualization workflow:
  - `reference/ventilation-pv-agent-workflow.md`
- Create Honeybee Energy schedules:
  - `reference/create-schedule-ruleset.md`
- Search Honeybee Energy standards library identifiers:
  - `reference/search-energy-library-objects.md`
- Search Honeybee Radiance standards library identifiers:
  - `reference/search-radiance-library-objects.md`
- Create project-specific Honeybee Radiance modifiers:
  - `reference/create-radiance-modifiers.md`
- Create project-specific Honeybee Radiance luminaires from IES files:
  - `reference/create-radiance-luminaires.md`
- Create and apply Honeybee Radiance dynamic states:
  - `reference/create-radiance-dynamic-states.md`
- Create Radiance WEA and SkyMatrix targets:
  - `reference/create-radiance-sky-wea.md`
- Visualize Sunpath, Sky Dome, and cumulative Radiation Dome context:
  - `reference/visualize-sunpath-sky-dome.md`
- Create Radiance sensor grids and views:
  - `reference/create-radiance-sensor-view.md`
- Run Radiance recipes:
  - `reference/run-radiance-simulation.md`
- Post-cleanup MiMo broad-suite pass paths:
  - `reference/post-cleanup-agent-broad-pass-paths.md`
- Save/search Garden Properties Library objects:
  - `reference/garden-properties-library.md`
- Create source-backed reusable Energy resource packs:
  - `reference/source-backed-energy-resources.md`
- Create Honeybee Energy program type:
  - `reference/create-program-type.md`
- Create Honeybee Energy construction set:
  - `reference/create-construction-set.md`
- Create / attach Honeybee Energy HVAC:
  - `reference/create-hvac.md`
- Run Energy simulation and EPW weather files:
  - `reference/run-energy-simulation.md`
- Evidence-first Energy result diagnosis:
  - `reference/energy-result-diagnosis.md`
- Edit Honeybee model metadata and top-level add/remove:
  - `reference/edit-honeybee-model.md`
- Edit Honeybee face / room:
  - `reference/edit-honeybee-face-and-room.md`
- Edit Honeybee aperture / door / shade:
  - `reference/edit-honeybee-subfaces-and-shade.md`
- Remove Honeybee aperture:
  - `reference/remove-honeybee-aperture.md`
- Remove Honeybee face:
  - `reference/remove-honeybee-face.md`
- Remove Honeybee door:
  - `reference/remove-honeybee-door.md`
- Remove Honeybee shade:
  - `reference/remove-honeybee-shade.md`
- Operate Honeybee objects with move / rotate / scale / mirror:
  - `reference/operate-honeybee-objects.md`
- Relate Honeybee model adjacency:
  - `reference/relate-honeybee-model.md`
- Clean Garden non-authoring scopes:
  - `reference/cleanup-garden-workspace.md`
- Garden version history, undo, and safe restore:
  - `reference/garden-version-management.md`
- Continue modeling from a Grasshopper Flowerpot:
  - `reference/flowerpot-grasshopper-modeling.md`
- Enable Web View demo mode for Agent-side live previews:
  - `reference/web-view-mode.md`
- Read-only query:
  - `reference/read-only-base-model-query.md`
- Validate Honeybee model:
  - `reference/validate-honeybee-model.md`
- Visualize Honeybee model as a VisualizationSet:
  - `reference/visualize-honeybee-model.md`
- Visualize Honeybee room / face as a VisualizationSet:
  - `reference/visualize-honeybee-room-face.md`
- Compose VisualizationSets:
  - `reference/compose-visualization-sets.md`
- Create / edit 2D legend parameters:
  - `reference/create-edit-2d-legend-parameter.md`
- Visualize Honeybee Room attributes and export SVG:
  - `reference/visualize-honeybee-room-attribute-svg.md`
- Visualize Honeybee Face attributes and export SVG:
  - `reference/visualize-honeybee-face-attribute-svg.md`
- Export VisualizationSet to HTML artifact:
  - `reference/visualization-set-to-html.md`
- Export VisualizationSet to SVG artifact:
  - `reference/visualization-set-to-svg.md`
- Visualize Ladybug DataCollection targets as monthly/hourly charts:
  - `reference/visualize-data-collection-chart.md`
- Failure diagnosis for saving base Honeybee model on an empty Garden:
  - `reference/save-base-honeybee-model-on-empty-garden.md`

## Scope

- `SKILL.md` should stay short and only provide entry rules and navigation.
- Detailed scenarios, validated shortest paths, prompt samples, success criteria, and failure examples belong under `reference/`.
- `reference/` is for Agent-facing usage paths only.
- `docs/llm-wiki/` is for product notes, project state, evidence, token-cost records, and capability evolution; it is not the main Agent entrypoint.
- Only paths verified by real OpenAI Agents runs can be documented as recommended paths in `reference/`.
