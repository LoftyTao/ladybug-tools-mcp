---
name: ladybug-tools-mcp-use
description: Use when operating Ladybug Tools MCP through FastMCP Code Mode, including verified Garden-mode paths, base-model confirmation, or failure-diagnosis guidance.
---

# Ladybug Tools MCP Use

Use Code Mode for multi-tool workflows.
FastMCP Code Mode is still MCP: use the active Agent MCP connection and the host application's MCP tool calls. For normal Ladybug Tools workflows, the MCP tools exposed to the Agent are `search`, `get_schema`, and `execute`; call domain tools inside `execute` via `await call_tool(...)`. Model-visible FastMCP App entries such as `web_view_start_mode` may also appear for host UI panels.
Do not bypass the active Agent MCP connection with a shell CLI, local `Client(create_mcp())`, direct Python service imports, or a repo-launched server unless you are writing/running deterministic MCP server tests.
Do not use the removed top-level Tool Search / Call Tool entrypoints, and do not call domain tools as standalone MCP tools outside Code Mode.
Use Garden mode and do not request full large payloads by default.

## Onboarding and Intent Triggers

- Do not spawn a project-scoped dedicated Ladybug Tools MCP tester agent. The former `ladybug_mcp_tester` custom agent has been retired; use the normal active MCP connection, deterministic tests, bounded Codex subagent case testing, or explicit external Agent SDK harnesses when validation is needed.
- If the user greets Ladybug Tools MCP with `你好！Ladybug Tools!`, `Hi, Ladybug Tools!`, or a similarly broad start, answer with the friendly fixed-structure `Bug Flyzzzzzzzzz!` welcome in the onboarding reference and ask for one of the three numbered top-level directions.
- Match the user's trigger language for onboarding replies. A mixed-language greeting like `Hi，Ladybug Tools！` counts as English. Do not default to Chinese unless the user used Chinese or the language is unclear.
- Keep `direction_label` values internal. Do not show `direction_label:` lines in the user-facing welcome; save the chosen label internally and continue into the Garden gate.
- Any option selection routes to the same Garden gate. After option 1, 2, or 3, ask whether the user already has a Garden to continue with or wants to create one; do not start modeling, resource creation, or Grasshopper collaboration before this gate.
- In the Garden gate, call `garden_list` when possible and show the five most recent Gardens from `matches[:5]`. If more than ten Gardens exist, suggest cleanup and offer to help, but do not delete or clean anything without explicit confirmation.
- After Garden creation or selection, use the saved direction label to offer a short next-step menu: modeling/object creation for `natural_language_modeling`, reusable resources for `reusable_resource_preparation`, and Grasshopper component-link plus model-edit guidance for `platform_collaboration`.
- If the user directly asks for natural-language modeling, reusable simulation resources, or Rhino / Grasshopper collaboration, save the matching top-level direction label internally and still enter the Garden gate before downstream authoring tools.
- Use Garden as the user-facing product concept for persistent project context. Use `garden_list`, `garden_create`, and `garden_get` for the Garden gate; do not invent `workspace_*` tools or call the Garden a workspace in onboarding copy.
- If a stable `garden_root`, Garden target, or current Flowerpot context already exists, ask whether to continue with that Garden instead of restarting the welcome flow.

## Core Rules

- Prefer explicit Garden root, object names, and target actions.
- When using Code Mode, keep intermediate SDK dicts and targets inside the `execute` block and return only final target, summary, receipt, or compact diagnostics.
- For create/edit/simulate workflows, do the dependent chain in one `execute` block whenever possible. Use local variables for tool results and return one compact final dictionary; do not make one `execute` call per MCP tool unless you are debugging a specific failing step.
- For common Ladybug Tools create/edit/simulate workflows, use `execute` as the first outer tool and call likely domain tools by name inside it. Use `search`/`get_schema` only after a tool name or parameter shape is actually unknown.
- For large create/edit/simulate requests, split work into the staged energy workflow: Stage A model/rooms, Stage B subfaces/shades, Stage C Energy properties/HVAC, Stage D weather/run, and Stage E outputs. Each stage resumes from Garden state, returns a compact stage summary, and stops after the requested stage is complete.
- For Stage C or any request that asks to validate a Honeybee model or return a validation flag, call `honeybee_validate_model`; use `honeybee_validate_model`, not `garden_get_base_honeybee_model`, because `garden_get_base_honeybee_model` only confirms the Garden base Honeybee model target/summary.
- If a long `execute` block fails after some write calls have already succeeded, do not replay the whole script. Garden writes are persistent; resume with a smaller repair block, search existing targets if needed, and continue from the failed step.
- Public tool arguments use one canonical lowercase `snake_case` name. Use `garden_root`, `model_target`, `host_target`, `object_type`, and `return_object_dict`; do not use historical names such as `_garden_root`, `garden_root_`, `_target`, or `object_type_`.
- Tool names are callable by their runtime public names after Code Mode `search` or `get_schema` exposes them. Domain names now include FastMCP namespace prefixes such as `honeybee_create_room`, `energyplus_start_simulation`, `radiance_create_sensor_grid`, and `detailed_hvac_zone_equipment_ptac`; do not call the old un-namespaced wrapper names.
- Keep Honeybee Energy HVAC template/simple HVAC separate from Ironbug DetailedHVAC. Use the Energy references for `hvac-template` workflows such as template HVAC, Ideal Air, simple ventilation/fans, and reusable HVAC resources; use the Ironbug references for `detailed-hvac` workflows such as source-backed components, loops, branches, and DetailedHVAC application.
- `garden_create` is the common Garden-root exception: it takes the folder path as `root_dir` and returns the reusable top-level `garden_root` string. Do not call `garden_create` with `garden_root`.
- For blank-project workflows, the first `execute` block must call `garden_create` before any tool that takes `garden_root`; creating the folder yourself is not enough because Garden tools require `garden.json`.
- For workflows that start from an existing Garden path, set `garden_root` to that literal path before the first read or write call.
- Write tools persist Garden changes and return persistence receipts; do not search for `save_garden` or `garden_save_base_honeybee_model` after successful create/edit calls unless the user explicitly asks for a separate save operation.
- For versioned Garden workflows, after completing a user-prompt-level workflow that changed Garden authoring truth (`garden.json`, `models/`, or `libraries/`), call `garden_create_version` once with a compact subject and structured summary. Do not call it after every low-level write; save one version for the completed user request.
- For undo, go-back, or restore requests, call `garden_list_versions`, choose by subject/summary, then call `garden_restore_version`. Do not request Git diffs or file bodies; inspect the restored model with Search, Validate, or Visualize tools if needed.
- For reusable Energy/Radiance library objects, prefer direct Garden-saving create tools with `garden_root` and `return_object_dict=false` when available; for schedules that do not need time-series inspection, also set `include_data=false`. Use `library_save_garden_properties_object` only when the user already has a full `object_dict` to store.
- `honeybee_create_model` takes `identifier`; do not use `model_name`. It does not take `return_object_dict` or `display_name`; it already returns compact targets unless `include_body=true` is explicitly requested for a debug/export need.
- Honeybee and Dragonfly model create tools use the boolean `set_base`, not `set_as_base`.
- Honeybee and Dragonfly base model slots are separate. Use `garden_get_base_honeybee_model` for Honeybee and `garden_get_base_dragonfly_model` for Dragonfly; the generic model-slot tools are not public.
- Deterministic-pass: for DOE INP or DesignBuilder dsbXML model file export, call `garden_export_model_file` with `garden_root`, `export_format`, and the exact Honeybee Model or Dragonfly Model `model_target`. Get the base target first with `garden_get_base_honeybee_model` or `garden_get_base_dragonfly_model` when the user wants the current base model; do not pass a generic model family field.
- Agent-verified: for Dragonfly authoring, call `dragonfly_create_model`, then `dragonfly_create_room2d`, then `dragonfly_create_story`, then `dragonfly_create_building` in order, then use `dragonfly_edit_model`, `dragonfly_edit_story`, `dragonfly_edit_building`, `dragonfly_edit_room2d`, `dragonfly_search_model_objects`, `dragonfly_get_model_summary`, `dragonfly_validate_model`, `dragonfly_model_to_visualization_set`, and optionally `dragonfly_model_to_honeybee`. Dragonfly Energy ProgramType/ConstructionSet application is available through `dragonfly_apply_energy_properties` for Room2D, Story, and Building targets. Dragonfly Radiance ModifierSet and grid-parameter application is available through `dragonfly_apply_radiance_properties`; grid parameters support Room2D and Building targets, not Story targets. Keep the chain in one Code Mode `execute` block when possible. Do not add generic model-slot tools or recovery wrappers to smooth removed paths.
- For Web View demo mode, call `web_view_start_mode` once at the start of the relevant Garden workflow so the host can open the FastMCP App preview panel; do not invent `set_dragonfly_web_view_demo_mode`, `open_browser`, `refresh_viewer`, or a Dragonfly-specific preview tool. After Web View Mode is active, significant Dragonfly edits, properties, conversions, and VisualizationSet outputs automatically create session previews under `tmp/web_view/previews/`; do not call `visualization_set_to_vtkjs` after every edit just to refresh the panel.
- For Dragonfly property tools, the canonical target field is `host_target`. Use exact library identifiers such as `Generic Office Program`, `Default Generic Construction Set`, and `Generic_Interior_Visible_Modifier_Set` when no project-specific library search is needed. If applying a grid parameter, include a modest grid size such as `grid_dimension=0.7`.
- For Dragonfly Story adjacency, use a Story target with `story_target` or a Story identifier with `story_identifier`; do not pass a Building target as a generic `target`, and do not invent adjacency add tools.
- Deterministic-pass with scaffolded Agent cross-suite: for Dragonfly UWG Alternative Weather workflows, use `uwg_get_dragonfly_properties_summary`, `uwg_apply_dragonfly_properties`, `uwg_create_simulation_parameter`, `uwg_dragonfly_model_to_uwg`, `uwg_start_simulation`, `uwg_poll_simulation`, `uwg_list_runs`, and `uwg_list_run_outputs`. Prefer `uwg_start_simulation` plus polling for Agents; use the returned morphed `weather_file` target with existing Energy tools only when the user asks for downstream Energy simulation. Do not call or invent `run_urbanopt`; URBANopt Energy, Electric Grid, and District Thermal remain separate backlog directions.
- Agent-verified with scaffolded Code Mode: Fairyfly authoring and THERM runtime are Windows-only and depend on the `fairyfly` / `fairyfly_therm` packages plus THERM runtime availability. For Fairyfly or two-dimensional heat-transfer authoring, use `therm_create_model`, `therm_create_solid_material`, `therm_add_shape_to_model`, `therm_add_boundary_to_model`, `therm_validate_model`, `therm_model_to_visualization_set`, `visualization_set_to_vtkjs`, and `therm_get_base_model` / `therm_set_base_model`. `therm_create_solid_material` returns an inline `object_dict`, not a Garden target. For THERM execution, use `therm_write_model_to_thmz`, `therm_start_simulation`, `therm_poll_simulation`, `therm_read_result`, `therm_read_u_factor`, and `therm_result_to_visualization_set`; if THERM is unavailable, respect the returned `blocked` status instead of inventing results.
- Agent-verified with scaffolded Code Mode: for Ironbug-Core `.ibjson` authoring and inspection, use `detailed_hvac_create_model`, `detailed_hvac_validate_model`, `detailed_hvac_search_model_objects`, and `validate_ironbug_energy_readiness` inside one `execute` block. Pass `created["target"]` as `ironbug_model_target`, inspect search results from `matches`, read readiness from `ready`, and read the first blocking code from `blocking_issues[0]["code"]`. Do not call or invent `read_ironbug_model` or `run_ironbug_energy`.
- Deterministic-pass / historical Agent smoke for Ironbug custom HVAC water-loop assembly: treat the request as one compact authoring task before any Energy run. Create or choose a Garden, create an Ironbug model, create precise components, then use semantic loop tools such as `detailed_hvac_plant_loop_chilled_water`, `detailed_hvac_plant_loop_hot_water`, and `detailed_hvac_plant_loop_condenser_water` with direct branch component targets and setpoints. Do not call or invent `create_ironbug_plant_loop`, `add_ironbug_plant_loop`, `set_ironbug_plant_loop_components`, `create_ironbug_plant_loop_branches`, `create_ironbug_exist_plant_loop`, or explicit PlantEquipmentOperation tools; those are not public MCP paths. Current HVAC-matrix acceptance must not use `IB_LoadProfilePlant` as demand; district-cooling, boiler, and chiller/condenser rows need real terminal, coil, air-terminal, or zone-equipment demand tied to `IB_ThermalZone` and Honeybee/Dragonfly Rooms before retention. Use the target returned by `detailed_hvac_create_model` for validation/search/apply inputs, do not hand-build Ironbug targets, and do not guess `.ibjson` paths. For the persisted `.ibjson` path in the final answer, use the returned target `path`, which lives under `models/ironbug/`. Inside `execute`, explicitly `return` the compact final dictionary after validation, compact search, and any required Energy readback.
- Plant-loop branch shape applies to every PlantLoop component family, not only coils: a flat branch list is one serial branch; separate room terminals, loads, exchangers, tanks, chillers, boilers, or heat-rejection components that should operate in parallel must be nested as one inner list per parallel branch.
- Deterministic-contract-pass: for comprehensive Ironbug graphs such as FCU + DOAS, VAV, VRF, air-loop, terminal, coil, and mixed air/hydronic systems, do not use `detailed_hvac_add_hvac_component_fallback`. Use the precise source-backed `create_ironbug_*` files plus relationship tools. Comprehensive create wrappers expose only reviewed explicit parameters, concrete descriptions, literal tags, and a literal `source_class` service call; they do not expose generic `custom_attributes`, `ib_properties`, `children`, or MCP-local `SOURCE_*` metadata constants. If a needed Ironbug source member is missing, treat that as a missing MCP tool/schema task for the owning file, not as permission to smuggle the value through a generic payload.
- Natural Ironbug custom-HVAC templates: Example System 1 should use exact source-backed component ids, then semantic chilled-water and condenser-water loop tools. For current district-cooling, boiler hot-water, or chiller/condenser Energy acceptance, do not use `IB_LoadProfilePlant` as demand; build a room-serving path with a distinct terminal or coil family, connect it to `IB_ThermalZone` and the selected Honeybee/Dragonfly Room, then create the semantic loop with direct supply/demand component targets and a loop setpoint. Plant-only pump/source/load-profile graphs are debug-only and do not satisfy custom-HVAC Energy acceptance. Example System 3 source-backed plant-core assembly should use semantic chilled-water and condenser-water loop tools for the primary, secondary, and condenser loops, then add terminal-integrated demand before Energy retention. Do not invent source class names such as `IB_Chiller_Electric_Ideal_Empirical`, `IB_CoolingTower_SingleSpeed`, or `IB_LoadProfile_Plant`.
- Before any Ironbug custom HVAC Energy case, confirm the served Rooms or Room2Ds are simulation-ready: Honeybee Rooms need ProgramType and thermostat Setpoint, and Dragonfly Story/Building native HVAC paths need conditioned Room2Ds unless `conditioned_only=false` is intentional. Use `reference/ironbug/ironbug-room-energy-preconditions.md` before loading a one-case HVAC skill.
- `honeybee_create_room` writes the room into the Garden base Honeybee model and auto-attaches to the selected model. Do not pass `host_target`, and do not pass returned room targets into `honeybee_edit_model.add_objects`; use later edit/search tools directly against the returned target.
- For simple box rooms, `honeybee_create_room` takes `identifier`, `x_dim`, `y_dim`, `height`, and optional `origin`; do not use `room_name`, `width`, `depth`, `origin_x`, `origin_y`, or `origin_z`.
- For `honeybee_edit_room`, pass `honeybee_search_model_objects` `matches[i].target` or a returned `honeybee_create_room.target` as the value for the parameter named `target`; not `room_target`, not a room identifier, not the full search response, and not `matches[i]` itself.
- For parameterized windows, prefer `honeybee_create_apertures_by_parameters` with `generation_mode="by_ratio"` and top-level `ratio`, or `generation_mode="by_width_height"` with top-level `aperture_width` and `aperture_height`. Do not hand-write a large `parameters` object unless recovering from a schema mismatch.
- Parameterized aperture and shade creation returns `targets[]`; the top-level `target` is the first created object for simple follow-up handoff.
- For one-room facade Agent stages, avoid Grasshopper-style or invented helpers. `honeybee_create_apertures_by_parameters` and `honeybee_create_shades_by_parameters` do not take `run_after`, `run_checks`, or other boolean "execute after" flags. Do not call `add_honeybee_shade_by_boundaries`, `attach_radiance_sensor_grid`, `list_radiance_grid_runs`, `get_honeybee_model_summary`, `get_garden_properties_library`, or `search_energy_program_types`; use the canonical create/search/validate/run tools already listed in this Skill.
- For facade aperture/shade setup, search once for the target exterior Face, create one aperture by ratio, use the returned aperture `target` for one simplified overhang/louver shade, then validate once. If that block partially succeeds, resume from persisted typed targets instead of recreating apertures or shades in a loop.
- For construction sets, prefer `energy_create_window_construction` with simple `u_factor / shgc / vt` and `energy_create_construction_set` with Honeybee generic defaults or Garden targets. In an existing Garden, call `energy_create_window_construction` with `garden_root` and `return_object_dict=false` so it returns a reusable Garden target; use that target for `energy_create_construction_set.aperture_set`, not `save_to_library` and not a handwritten `WindowConstruction` dict. For a low-U window override, pass the returned window construction target directly as `energy_create_construction_set.aperture_set`; do not create an intermediate `ApertureConstructionSet` unless you need multiple aperture slots. Do not pass hand-written `thickness / conductivity` material dicts directly to `energy_create_opaque_construction`; use `energy_create_opaque_material` first or a library identifier.
- For EPW weather, use `energyplus_search_epw_map` without `garden_root`, then `energyplus_download_epw` with the same `garden_root` and selected `epw_map_target`; there is no `download_weather_file` tool or separate weather folder path.
- `energyplus_search_epw_map` takes a plain `query` string. For hot-humid China facade studies, `query="Sanya"` is known to return OneBuilding weather data; avoid over-specific suffixes such as `"Sanya China TMY3"` if they return no matches. If the selected weather search returns no matches, try one clearly named second query such as `"Miami"` and then stop with the saved failure/status instead of looping.
- For EPW weather charts or original EPW vs UWG morphed EPW comparisons, use `energyplus_read_weather_file_data` to save SDK EPW fields as `ladybug_data_collection` targets, then pass those targets into `visualization_data_collection_monthly_chart_to_visualization_set`; do not parse EPW text by hand.
- For shade-attached photovoltaic setup, call `energy_create_pv_properties` with a canonical `mounting_type`: `FixedOpenRack`, `FixedRoofMounted`, `OneAxis`, `OneAxisBacktracking`, or `TwoAxis`. Use `FixedRoofMounted`, not `FixedRoofMount`; do not invent `FlushMount`.
- For energy simulation in Agent workflows, prefer `energyplus_start_simulation` and poll `energyplus_poll_simulation`; avoid blocking `energyplus_run_simulation_wait` unless the user explicitly asks to wait for local completion.
- For post-run ERR diagnostics, call `energyplus_read_errors`; do not invent `read_energy_run_err` or pass ad hoc weather fields such as `weather_file_target` into `energyplus_start_simulation`.
- For a known completed energy run, use `energyplus_start_simulation` with `run_id` and `reload_old=true` to reload the completed ledger, then call `energyplus_poll_simulation`, `energyplus_list_run_outputs`, and `energyplus_read_eui`; this must not start a new background run.
- Focused Agent-verified: for Radiance point-in-time grid/view workflows, use one setup checkpoint and one run/postprocess pass. Attach one SensorGrid or View, create one single-timestep sky and one parameter set, then call the matching `start_radiance_*_run` and `radiance_poll_simulation(wait_seconds=60, poll_interval=2)`. Do not rebuild geometry, grids, views, skies, or parameters after they exist; search compact Radiance artifacts and resume from targets.
- Code Mode `execute` blocks are isolated. Variables from one `execute` call are not available in later calls. Do not use `import`, `os`, `pathlib`, `asyncio`, `asyncio.gather`, or parallel calls inside `execute`; call tools sequentially and use literal path strings from the prompt.
- In Code Mode `execute`, avoid compact Python iterator tricks over tool-result lists, especially `next(...)` with generator expressions. Use explicit `for` loops, assign a target variable, and return a compact diagnostic if no match is found; failed Agent runs have otherwise produced list/iterator errors and repeated searches.
- In Code Mode, do not instantiate `Garden` or SDK objects directly; use `await call_tool(...)` with MCP tool names.
- `execute` code is Python. Use `True`, `False`, and `None`, not JSON `true`, `false`, or `null`.
- Use `get_schema` only when `search` descriptions are insufficient; request brief schema first, and detailed schema only for the exact blocked tool.
- In Code Mode, `search` and `get_schema` are MCP tools exposed by the Code Mode surface, not domain tools. Do not call `await call_tool("search", ...)` or `await call_tool("get_schema", ...)` inside `execute`.
- In Code Mode, do not use `print()` inside `execute`; stdout can corrupt stdio MCP transport. Return compact JSON-compatible data instead.
- Do not serialize tool results with `json.dumps` inside `execute`; return a dict directly.
- When the user says vague words like `模型`、`房间`、`墙`、`窗`, first narrow the request to the object level with Code Mode `search`/`get_schema` and `honeybee_search_model_objects`.
- When confirming a create/edit/remove result, verify with a follow-up read/search call instead of trusting the write call alone.
- When recovering from a partial write, use `honeybee_search_model_objects.children_scope` with the room/face/aperture/door target to inspect existing child objects before retrying writes such as aperture or shade creation. `children_scope` must be a typed target dict, not `true` and not `parent_target`.
- There is no `get_honeybee_model_summary` public tool. For Honeybee counts, room energy assignments, child object counts, and compact object evidence, use `honeybee_search_model_objects`; for validity use `honeybee_validate_model`.
- `honeybee_search_model_objects` matches for rooms, faces, apertures, and doors include compact `child_counts`; use those counts before making separate full-model room/face/aperture/shade inventory searches.
- For subface/shade stages, search rooms once, search exterior wall faces with `children_scope`, create apertures from returned face targets, then create shades from returned aperture/face targets; do not relist the whole model after each individual write.
- When confirming only Honeybee base model presence or retrieving the compact Honeybee base model target, call `garden_get_base_honeybee_model`.
- When confirming an existing Garden manifest, call `garden_get`; do not use filesystem probes or Python imports inside Code Mode.
- Keep Flowerpot as an opaque dict and do not unpack internal fields manually.
- When the user is validating failure behavior, do not auto-recover by default.
- In Code Mode, do not call original domain tools as outer MCP tools. Use them only inside `execute` via `await call_tool(tool_name, arguments)`.
- Tool names returned by Code Mode `search` are strings for `execute`/`call_tool`, not standalone MCP tool calls. Use the connected MCP session's Code Mode tools to discover and execute them.
- Every `call_tool` invocation must include a non-empty JSON `arguments` object that uses the tool's exact required parameter names. If a required-argument validation error appears, rebuild the full arguments object from the latest search result, tool schema, or prompt instead of retrying the failed shape.
- When writing Windows paths inside JSON examples, escape backslashes or generate the arguments object with a JSON serializer.
- For multi-step write workflows, prefer one concrete tool call at a time. After a successful search, immediately call the next MCP tool with the target from that search instead of ending with a plan sentence.
- Avoid parallel write calls against the same Garden/model. The server serializes in-process Honeybee model writes, but Agents should still wait for each write result, then search or validate before the next dependent write.
- For downstream `target` / `host_target`, pass the nested typed target dict such as `matches[i].target` or a write tool's returned `target`. Do not pass full tool responses, `matches[i]`, or identifier-only dictionaries.
- Do not describe unverified tool paths as recommended. If a path is only a candidate or currently fails in natural-language runs, say so explicitly.

## Reading Order

Read only the most relevant category overview and reference file(s) for the current task.

- Onboarding, welcome copy, and the beginner Garden gate:
  - `reference/onboarding-intent-triggers.md`
- Garden context, base model confirmation, versioning, cleanup, and Garden failure boundaries:
  - `reference/garden/overview.md`
  - `reference/garden/create-garden.md`
  - `reference/garden/read-only-base-model-query.md`
  - `reference/garden/save-base-honeybee-model-on-empty-garden.md`
- Honeybee core model authoring, object search, edit/remove, relationship, and validation:
  - `reference/honeybee/overview.md`
  - `reference/honeybee/create-honeybee-model-and-confirm-base-model.md`
  - `reference/honeybee/create-honeybee-room.md`
  - `reference/honeybee/search-honeybee-model-objects-natural-language.md`
  - `reference/honeybee/validate-honeybee-model.md`
- Honeybee subfaces, shades, staged facade work, object operation, and removal:
  - `reference/honeybee/create-honeybee-face-and-shade.md`
  - `reference/honeybee/create-honeybee-apertures-by-parameters.md`
  - `reference/honeybee/create-honeybee-interior-door.md`
  - `reference/honeybee/create-honeybee-shades-by-parameters.md`
  - `reference/honeybee/subface-shade-stage-short-path.md`
  - `reference/honeybee/live-honeybee-model-expansion.md`
  - `reference/honeybee/edit-honeybee-model.md`
  - `reference/honeybee/edit-honeybee-face-and-room.md`
  - `reference/honeybee/edit-honeybee-subfaces-and-shade.md`
  - `reference/honeybee/operate-honeybee-objects.md`
  - `reference/honeybee/relate-honeybee-model.md`
  - `reference/honeybee/remove-honeybee-room.md`
  - `reference/honeybee/remove-honeybee-face.md`
  - `reference/honeybee/remove-honeybee-aperture.md`
  - `reference/honeybee/remove-honeybee-door.md`
  - `reference/honeybee/remove-honeybee-shade.md`
- Dragonfly core model authoring, properties, validation, UWG Alternative Weather, visualization, and conversion:
  - `reference/dragonfly/overview.md`
  - `reference/dragonfly/dragonfly-authoring.md`
- Fairyfly 2D heat-transfer authoring, THERM runs, result reads, and visualization:
  - `reference/fairyfly/overview.md`
  - `reference/fairyfly/fairyfly-authoring.md`
- Energy resources, weather, staged workflows, simulation, result reads, and diagnostics:
  - `reference/energy/overview.md`
  - `reference/energy/search-energy-library-objects.md`
  - `reference/energy/garden-properties-library.md`
  - `reference/energy/create-program-type.md`
  - `reference/energy/create-schedule-ruleset.md`
  - `reference/energy/create-construction-set.md`
  - `reference/energy/create-hvac.md`
  - `reference/energy/source-backed-energy-resources.md`
  - `reference/energy/staged-energy-agent-workflow.md`
  - `reference/energy/source-backed-light-thermal-facade.md`
  - `reference/energy/ventilation-pv-agent-workflow.md`
  - `reference/energy/run-energy-simulation.md`
  - `reference/energy/energy-result-diagnosis.md`
- Radiance modifiers, luminaires, dynamic states, sky/WEA, sensors, views, runs, and sky context:
  - `reference/radiance/overview.md`
  - `reference/radiance/search-radiance-library-objects.md`
  - `reference/radiance/create-radiance-modifiers.md`
  - `reference/radiance/create-radiance-luminaires.md`
  - `reference/radiance/create-radiance-dynamic-states.md`
  - `reference/radiance/create-radiance-sky-wea.md`
  - `reference/radiance/create-radiance-sensor-view.md`
  - `reference/radiance/run-radiance-simulation.md`
  - `reference/radiance/visualize-sunpath-sky-dome.md`
- VisualizationSet, legend, HTML/SVG export, Honeybee previews, and charts:
  - `reference/visualization/overview.md`
  - `reference/visualization/visualize-honeybee-model.md`
  - `reference/visualization/visualize-honeybee-room-face.md`
  - `reference/visualization/visualize-honeybee-room-attribute-svg.md`
  - `reference/visualization/visualize-honeybee-face-attribute-svg.md`
  - `reference/visualization/compose-visualization-sets.md`
  - `reference/visualization/create-edit-2d-legend-parameter.md`
  - `reference/visualization/visualization-set-to-html.md`
  - `reference/visualization/visualization-set-to-svg.md`
  - `reference/visualization/visualize-data-collection-chart.md`
- Platform strategy: Flowerpot, Grasshopper handoff, and Web View Mode:
  - `reference/platform/overview.md`
  - `reference/platform/flowerpot-grasshopper-modeling.md`
  - `reference/platform/web-view-mode.md`
- Ironbug custom HVAC, Room energy preflight, plant concept mapping, case skills, and family workflow:
  - `reference/ironbug/overview.md`
  - `reference/ironbug/ironbug-room-energy-preconditions.md`
  - `reference/ironbug/ironbug-core-ibjson.md`
  - `reference/ironbug/ironbug-energyplus-plant-concepts.md`
  - `reference/ironbug/ironbug-loop-topology-placement.md`
  - `reference/ironbug/ironbug-ems-operation-strategy.md`
  - `reference/ironbug/ironbug-ems-storage-dispatch.md`
  - `reference/ironbug/custom-hvac-cases/index.md`
  - `reference/ironbug/ironbug-custom-hvac-agent-workflows.md`
- Tool disclosure, namespace, or Skill reference maintenance:
  - `reference/platform/tool-disclosure-namespace-transition.md`

## Scope

- `SKILL.md` should stay short and only provide entry rules and navigation.
- Detailed scenarios, validated shortest paths, prompt samples, success criteria, and failure examples belong under `reference/`.
- `reference/` is for Agent-facing usage paths only.
- `docs/llm-wiki/` is for product notes, project state, evidence, cost records, and capability evolution; it is not the main Agent entrypoint.
- Only paths verified by real OpenAI Agents runs can be documented as recommended paths in `reference/`.
- After a deterministic pass, a short candidate reference may be written before the Agent run. Keep it labeled `deterministic-contract-pass` or `candidate` until the focused Skill-assisted Agent test passes.
