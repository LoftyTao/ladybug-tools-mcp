---
name: ladybug-tools-mcp-use
description: Use when operating Ladybug Tools MCP through FastMCP Code Mode, including verified Garden-mode paths, base-model confirmation, or failure-diagnosis guidance.
---

# Ladybug Tools MCP Use

Use Code Mode for multi-tool workflows.
FastMCP Code Mode is still MCP: use the active Agent MCP connection and the host application's MCP tool calls. For normal Ladybug Tools workflows, the MCP tools exposed to the Agent are `search`, `get_schema`, and `execute`; call domain tools inside `execute` via `await call_tool(...)`.
Do not bypass the active Agent MCP connection with a shell CLI, local `Client(create_mcp())`, direct Python service imports, or a repo-launched server.
Do not use the removed top-level Tool Search / Call Tool entrypoints, and do not call domain tools as standalone MCP tools outside Code Mode.
Use Garden mode and do not request full large payloads by default.

## Onboarding and Intent Triggers

- If the user greets Ladybug Tools MCP with `你好！Ladybug Tools!`, `Hi, Ladybug Tools!`, or a similarly broad start, answer with the friendly fixed-structure `Bug Flyzzzzzzzzz!` welcome in the onboarding reference and ask for one of the three numbered top-level directions.
- Match the user's trigger language for onboarding replies. A mixed-language greeting like `Hi，Ladybug Tools！` counts as English. Do not default to Chinese unless the user used Chinese or the language is unclear.
- Keep `direction_label` values internal. Do not show `direction_label:` lines in the user-facing welcome; save the chosen label internally and continue into the Garden gate.
- Any option selection routes to the same Garden gate. After option 1, 2, or 3, ask whether the user already has a Garden to continue with or wants to create one; do not start modeling, resource creation, or Grasshopper collaboration before this gate.
- In the Garden gate, call `GD_list` when possible and show the five most recent Gardens from `matches[:5]`. If more than ten Gardens exist, suggest cleanup and offer to help, but do not delete or clean anything without explicit confirmation.
- After Garden creation or selection, use the saved direction label to offer a short next-step menu: modeling/object creation for `natural_language_modeling`, reusable resources for `reusable_resource_preparation`, and Grasshopper component-link plus model-edit guidance for `platform_collaboration`.
- If the user directly asks for natural-language modeling, reusable simulation resources, or Rhino / Grasshopper collaboration, save the matching top-level direction label internally and still enter the Garden gate before downstream authoring tools.
- Use Garden as the user-facing product concept for persistent project context. Use `GD_list`, `GD_create`, and `GD_get` for the Garden gate; do not invent `workspace_*` tools or call the Garden a workspace in onboarding copy.
- If a stable `garden_root`, Garden target, or current Flowerpot context already exists, ask whether to continue with that Garden instead of restarting the welcome flow.

## Core Rules

- The maintained development and local MCP environment is Windows. Use the user's or selected Garden root verbatim, Windows paths, PowerShell commands, and `.venv/Scripts/python.exe`.
- Prefer explicit Garden root, object names, and target actions.
- When using Code Mode, keep intermediate SDK dicts and targets inside the `execute` block and return only final target, summary, receipt, or compact diagnostics.
- For create/edit/simulate workflows, do the dependent chain in one `execute` block whenever possible. Use local variables for tool results and return one compact final dictionary; do not make one `execute` call per MCP tool unless you are debugging a specific failing step.
- For common Ladybug Tools create/edit/simulate workflows, use `execute` as the first outer tool and call likely domain tools by name inside it. Use `search`/`get_schema` only after a tool name or parameter shape is actually unknown.
- For large create/edit/simulate requests, split work into the staged energy workflow: Stage A model/rooms, Stage B subfaces/shades, Stage C Energy properties/HVAC, Stage D weather/run, and Stage E outputs. Each stage resumes from Garden state, returns a compact stage summary, and stops after the requested stage is complete.
- For Stage C or any request that asks to validate a Honeybee model or return a validation flag, call `HB_validate_model`; use `HB_validate_model`, not `GD_get_base_honeybee_model`, because `GD_get_base_honeybee_model` only confirms the Garden base Honeybee model target/summary.
- If a long `execute` block fails after some write calls have already succeeded, do not replay the whole script. Garden writes are persistent; resume with a smaller repair block, search existing targets if needed, and continue from the failed step.
- Public tool arguments use one canonical lowercase `snake_case` name. Use `garden_root`, `model_target`, `host_target`, `object_type`, and `return_object_dict`; do not use historical names such as `_garden_root`, `garden_root_`, `_target`, or `object_type_`.
- Use the complete, case-sensitive tool name returned by Code Mode `search` or `get_schema`; the uppercase ecosystem prefix is part of the public name, for example `HB_create_room`, `EP_start_simulation`, `RAD_create_sensor_grid`, and `IB_zone_equipment_ptac`. After reconnecting or deploying a rename, rediscover the current directory before calling it.
- Keep Honeybee Energy HVAC template/simple HVAC separate from Ironbug DetailedHVAC. Use the Energy references for `hvac-template` workflows such as template HVAC, Ideal Air, simple ventilation/fans, and reusable HVAC resources; use the Ironbug references for `detailed-hvac` workflows such as source-backed components, loops, branches, and DetailedHVAC application.
- `GD_create` is the common Garden-root exception: it takes the folder path as `root_dir` and returns the reusable top-level `garden_root` string. Do not call `GD_create` with `garden_root`.
- `GD_create` initializes Garden-local `.git/` when Git is available on `PATH`; if `summary_view.version_control.git_available=false`, treat creation as successful and defer version tools. After Git becomes available, the first Garden version tool initializes the repository.
- For blank-project workflows, the first `execute` block must call `GD_create` before any tool that takes `garden_root`; creating the folder yourself is not enough because Garden tools require `garden.json`.
- For workflows that start from an existing Garden path, set `garden_root` to that literal path before the first read or write call.
- Write tools persist Garden changes and return persistence receipts; do not search for `save_garden` or `GD_save_base_honeybee_model` after successful create/edit calls unless the user explicitly asks for a separate save operation.
- For Energy, Radiance, and URBANopt runs, use the returned `run_folder` and output record `path` values; treat `run_id` as a ledger key and do not derive filesystem paths from it.
- Garden authoring writes also return a unified `operation_result`; inspect its status, revisions, affected targets, receipt, and report before continuing. Reuse `result["operation_result"]["operation_target"]["operation_id"]` only for the same immutable retry, and pass the latest known revision as `expected_revision` when available.
- For versioned Garden workflows, after completing a user-prompt-level workflow that changed Garden authoring truth (`garden.json`, `models/`, or `libraries/`), call `GD_create_version` once with a compact subject and structured summary. Do not call it after every low-level write; save one version for the completed user request.
- For undo, go-back, or restore requests, call `GD_list_versions`, choose by subject/summary, then call `GD_restore_version`. Do not request Git diffs or file bodies; inspect the restored model with Search, Validate, or Visualize tools if needed.
- For reusable Energy/Radiance library objects, prefer direct Garden-saving create tools with `garden_root` and `return_object_dict=false` when available; for schedules that do not need time-series inspection, also set `include_data=false`. Use `GD_library_save_garden_properties_object` only when the user already has a full `object_dict` to store.
- `HB_create_model` takes `identifier`; do not use `model_name`. It does not take `return_object_dict` or `display_name`; it already returns compact targets unless `include_body=true` is explicitly requested for a debug/export need.
- Honeybee and Dragonfly model create tools use the boolean `set_base`, not `set_as_base`.
- Honeybee and Dragonfly base model slots are separate. Use `GD_get_base_honeybee_model` for Honeybee and `GD_get_base_dragonfly_model` for Dragonfly. The generic model-slot tools are not public.
- Deterministic-contract-pass: use `DF_*`, `DF_des_*`, `DF_grid_*`, `DF_uwg_*`, `DF_urbanopt_*`, `GD_get_base_dragonfly_model`, `GD_set_base_dragonfly_model`, `GD_save_base_dragonfly_model`, `IB_apply_to_dragonfly_model`, and `IB_apply_to_dragonfly_energy_properties` through Code Mode `execute` like other domain tools.
- Deterministic-pass: for DOE INP or DesignBuilder dsbXML model file export, call `GD_export_model_file` with `garden_root`, `export_format`, and the exact Honeybee or Dragonfly Model `model_target`. Get the base target first with `GD_get_base_honeybee_model` or `GD_get_base_dragonfly_model` when the user wants the current base model; do not pass a generic model family field.
- Dragonfly authoring uses `DF_model`, `DF_room2d`, `DF_story`, `DF_building`, Dragonfly edit/search/validate/visualization tools, and optional Dragonfly-to-Honeybee conversion. Keep returned Dragonfly targets in the same `execute` block when possible.
- For local Web View mode, call `GD_web_view_start_mode` once at the start of the relevant Garden workflow, open its returned `viewer.url` in the local sidebar, then continue ordinary model tools. The viewer silently polls every 1.5 seconds and preserves the camera across scene replacement; do not invent `open_browser` or `refresh_viewer`, and do not call `LB_set_to_vtkjs` after every edit just to refresh the viewer.
- For Dragonfly property tools, the canonical target field is `host_target`. Use exact library identifiers such as `Generic Office Program`, `Default Generic Construction Set`, and `Generic_Interior_Visible_Modifier_Set` when no project-specific library search is needed. If applying a grid parameter, include a modest grid size such as `grid_dimension=0.7`.
- For Dragonfly Story adjacency, use a Story target with `story_target` or a Story identifier with `story_identifier`; do not pass a Building target as a generic `target`, and do not invent adjacency add tools.
- Dragonfly UWG Alternative Weather, URBANopt Energy, and Electric Grid tools are normal public routes. For UWG and URBANopt regression tests, prefer an existing Garden-managed weather target or import a verified local EPW before remote map lookup; do not assume a Windows Ladybug Tools install exists. For URBANopt-backed Energy runs, use `DF_urbanopt_prepare_project` with `weather_target` when an EPW is available, then `DF_urbanopt_start_simulation`, `DF_urbanopt_poll_simulation`, and `DF_urbanopt_list_run_outputs`. For Electric Grid authoring and runtime-gated RNM/OpenDSS/REopt attempts, use the `DF_grid_*` route and stop on blocked runtime ledgers.
- Candidate/pending fresh natural Windows MCP acceptance: For every Fairyfly or two-dimensional heat-transfer request, first use Code Mode outer `search` to confirm that the Fairyfly/THERM tool family is registered; only then create or select a Garden.
- If discovery finds no Fairyfly tools, stop immediately, report the Windows/runtime platform boundary, do not create an empty Garden, and do not claim completion.
- Fairyfly authoring and THERM runtime are Windows-only and depend on the `fairyfly` / `fairyfly_therm` packages plus THERM runtime availability.
- Use `FF_create_model`, `FF_create_solid_material`, `FF_add_shape_to_model`, `FF_add_boundary_to_model`, `FF_validate_model`, `FF_model_to_visualization_set`, `LB_set_to_vtkjs`, and `FF_get_base_model` / `FF_set_base_model`.
- `FF_create_solid_material` returns an inline `object_dict`, not a Garden target.
- For THERM execution, use `FF_write_model_to_thmz`, `FF_start_simulation`, `FF_poll_simulation`, `FF_read_result`, `FF_read_u_factor`, and `FF_result_to_visualization_set`; if THERM is unavailable, respect the returned `blocked` status instead of inventing results.
- Agent-verified with scaffolded Code Mode: for Ironbug-Core `.ibjson` authoring and inspection, use `IB_create_model`, `IB_validate_model`, `IB_search_model_objects`, and `validate_ironbug_energy_readiness` inside one `execute` block. Pass `created["target"]` as `ironbug_model_target`, inspect search results from `matches`, read readiness from `ready`, and read the first blocking code from `blocking_issues[0]["code"]`. Do not call or invent `read_ironbug_model` or `run_ironbug_energy`.
- Deterministic-pass / historical Agent smoke for Ironbug custom HVAC water-loop assembly: treat the request as one compact authoring task before any Energy run. Create or choose a Garden, create an Ironbug model, create precise components, then use semantic loop tools such as `IB_plant_loop_chilled_water`, `IB_plant_loop_hot_water`, and `IB_plant_loop_condenser_water` with direct branch component targets and setpoints. Do not call or invent `create_ironbug_plant_loop`, `add_ironbug_plant_loop`, `set_ironbug_plant_loop_components`, `create_ironbug_plant_loop_branches`, `create_ironbug_exist_plant_loop`, or explicit PlantEquipmentOperation tools; those are not public MCP paths. Current HVAC-matrix acceptance must not use `IB_LoadProfilePlant` as demand; district-cooling, boiler, and chiller/condenser rows need real terminal, coil, air-terminal, or zone-equipment demand tied to `IB_ThermalZone` and Honeybee/Dragonfly Rooms before retention. Use the target returned by `IB_create_model` for validation/search/apply inputs, do not hand-build Ironbug targets, and do not guess `.ibjson` paths. For the persisted `.ibjson` path in the final answer, use the returned target `path`, which lives under `models/ironbug/`. Inside `execute`, explicitly `return` the compact final dictionary after validation, compact search, and any required Energy readback.
- Plant-loop branch shape applies to every PlantLoop component family, not only coils: a flat branch list is one serial branch; separate room terminals, loads, exchangers, tanks, chillers, boilers, or heat-rejection components that should operate in parallel must be nested as one inner list per parallel branch.
- Deterministic-contract-pass: for comprehensive Ironbug graphs such as FCU + DOAS, VAV, VRF, air-loop, terminal, coil, and mixed air/hydronic systems, do not use `IB_add_hvac_component_fallback`. Use the precise source-backed `create_ironbug_*` files plus relationship tools. Comprehensive create wrappers expose only reviewed explicit parameters, concrete descriptions, literal tags, and a literal `source_class` service call; they do not expose generic `custom_attributes`, `ib_properties`, `children`, or MCP-local `SOURCE_*` metadata constants. If a needed Ironbug source member is missing, treat that as a missing MCP tool/schema task for the owning file, not as permission to smuggle the value through a generic payload.
- Natural Ironbug custom-HVAC templates: Example System 1 should use exact source-backed component ids, then semantic chilled-water and condenser-water loop tools. For current district-cooling, boiler hot-water, or chiller/condenser Energy acceptance, do not use `IB_LoadProfilePlant` as demand; build a room-serving path with a distinct terminal or coil family, connect it to `IB_ThermalZone` and the selected Honeybee/Dragonfly Room, then create the semantic loop with direct supply/demand component targets and a loop setpoint. Plant-only pump/source/load-profile graphs are debug-only and do not satisfy custom-HVAC Energy acceptance. Example System 3 source-backed plant-core assembly should use semantic chilled-water and condenser-water loop tools for the primary, secondary, and condenser loops, then add terminal-integrated demand before Energy retention. Do not invent source class names such as `IB_Chiller_Electric_Ideal_Empirical`, `IB_CoolingTower_SingleSpeed`, or `IB_LoadProfile_Plant`.
- Before any Ironbug custom HVAC Energy case, confirm the served Rooms or Room2Ds are simulation-ready: Honeybee Rooms need ProgramType and thermostat Setpoint, and Dragonfly Story/Building native HVAC paths need conditioned Room2Ds unless `conditioned_only=false` is intentional. Use `reference/ironbug/ironbug-room-energy-preconditions.md` before loading a one-case HVAC skill.
- `HB_create_room` writes the room into the Garden base Honeybee model and auto-attaches to the selected model. Do not pass `host_target`, and do not pass returned room targets into `HB_edit_model.add_objects`; use later edit/search tools directly against the returned target.
- For simple box rooms, `HB_create_room` takes `identifier`, `x_dim`, `y_dim`, `height`, and optional `origin`; do not use `room_name`, `width`, `depth`, `origin_x`, `origin_y`, or `origin_z`.
- For `HB_edit_room`, pass `HB_search_model_objects` `matches[i].target` or a returned `HB_create_room.target` as the value for the parameter named `target`; not `room_target`, not a room identifier, not the full search response, and not `matches[i]` itself.
- For parameterized windows, prefer `HB_create_apertures_by_parameters` with `generation_mode="by_ratio"` and top-level `ratio`, or `generation_mode="by_width_height"` with top-level `aperture_width` and `aperture_height`. Do not hand-write a large `parameters` object unless recovering from a schema mismatch.
- Parameterized aperture and shade creation returns `targets[]`; the top-level `target` is the first created object for simple follow-up handoff.
- For one-room facade Agent stages, avoid Grasshopper-style or invented helpers. `HB_create_apertures_by_parameters` and `HB_create_shades_by_parameters` do not take `run_after`, `run_checks`, or other boolean "execute after" flags. Do not call `add_honeybee_shade_by_boundaries`, `attach_radiance_sensor_grid`, `list_radiance_grid_runs`, `get_honeybee_model_summary`, `get_garden_properties_library`, or `search_energy_program_types`; use the canonical create/search/validate/run tools already listed in this Skill.
- For a bounded Room -> exterior Wall Face -> ratio Aperture -> horizontal louver Shade stage, follow `reference/honeybee/subface-shade-stage-short-path.md` and use its checkpoint tool; use the low-level create/search path there for other facade edits.
- For construction sets, prefer `EP_create_window_construction` with simple `u_factor / shgc / vt` and `EP_create_construction_set` with Honeybee generic defaults or Garden targets. In an existing Garden, call `EP_create_window_construction` with `garden_root` and `return_object_dict=false` so it returns a reusable Garden target; use that target for `EP_create_construction_set.aperture_set`, not `save_to_library` and not a handwritten `WindowConstruction` dict. For a low-U window override, pass the returned window construction target directly as `EP_create_construction_set.aperture_set`; do not create an intermediate `ApertureConstructionSet` unless you need multiple aperture slots. Do not pass hand-written `thickness / conductivity` material dicts directly to `EP_create_opaque_construction`; use `EP_create_opaque_material` first or a library identifier.
- For bundled EPW weather, read `weather://catalog` and call `EP_import_local_weather` with the current `garden_root` and `source_path="weather://files/<station>"`; for remote or missing stations, call `LB_weather_download` with a specific query and exact directory filters when known. Keep the returned `weather_file` target.
- For `LB_weather_download`, use `format="zip"` when DDY/STAT is needed and confirm with `EP_search_weather_files(require_ddy=True)`; the tool handles epwapi-first lookup and epwfile fallback. Stop on a blocked result instead of constructing remote URLs or credentials.
- For EPW weather charts or original EPW vs UWG morphed EPW comparisons, use `EP_read_weather_file_data` to save SDK EPW fields as `ladybug_data_collection` targets, then pass those targets into `LB_data_collection_monthly_chart_to_visualization_set`; do not parse EPW text by hand.
- For shade-attached photovoltaic setup, call `EP_create_pv_properties` with a canonical `mounting_type`: `FixedOpenRack`, `FixedRoofMounted`, `OneAxis`, `OneAxisBacktracking`, or `TwoAxis`. Use `FixedRoofMounted`, not `FixedRoofMount`; do not invent `FlushMount`.
- For energy simulation in Agent workflows, prefer `EP_start_simulation` and poll `EP_poll_simulation`; avoid blocking `EP_run_simulation_wait` unless the user explicitly asks to wait for local completion.
- For post-run ERR diagnostics, call `EP_read_errors`; do not invent `read_energy_run_err` or pass ad hoc weather fields such as `weather_file_target` into `EP_start_simulation`.
- For a known completed energy run, use `EP_start_simulation` with `run_id` and `reload_old=true` to reload the completed ledger, then call `EP_poll_simulation`, `EP_list_run_outputs`, and `EP_read_eui`; this must not start a new background run.
- Focused Agent-verified: for Radiance point-in-time grid/view workflows, use one setup checkpoint and one run/postprocess pass. Attach one SensorGrid or View, create one single-timestep sky and one parameter set, then call the matching `start_radiance_*_run` and `RAD_poll_simulation(wait_seconds=60, poll_interval=2)`. Do not rebuild geometry, grids, views, skies, or parameters after they exist; search compact Radiance artifacts and resume from targets.
- Code Mode `execute` blocks are isolated. Variables from one `execute` call are not available in later calls. Do not use `import`, `os`, `pathlib`, `asyncio`, `asyncio.gather`, or parallel calls inside `execute`; call tools sequentially and use literal path strings from the prompt.
- In Code Mode `execute`, avoid compact Python iterator tricks over tool-result lists, especially `next(...)` with generator expressions. Use explicit `for` loops, assign a target variable, and return a compact diagnostic if no match is found; failed Agent runs have otherwise produced list/iterator errors and repeated searches.
- In Code Mode, do not instantiate `Garden` or SDK objects directly; use `await call_tool(...)` with MCP tool names.
- `execute` code is Python. Use `True`, `False`, and `None`, not JSON `true`, `false`, or `null`.
- Use `get_schema` only when `search` descriptions are insufficient; request brief schema first, and detailed schema only for the exact blocked tool.
- In Code Mode, `search` and `get_schema` are MCP tools exposed by the Code Mode surface, not domain tools. Do not call `await call_tool("search", ...)` or `await call_tool("get_schema", ...)` inside `execute`.
- In Code Mode, do not use `print()` inside `execute`; stdout can corrupt stdio MCP transport. Return compact JSON-compatible data instead.
- Do not serialize tool results with `json.dumps` inside `execute`; return a dict directly.
- When the user says vague words like `模型`、`房间`、`墙`、`窗`, first narrow the request to the object level with Code Mode `search`/`get_schema` and `HB_search_model_objects`.
- When confirming a create/edit/remove result, verify with a follow-up read/search call instead of trusting the write call alone.
- When recovering from a partial write, use `HB_search_model_objects.children_scope` with the room/face/aperture/door target to inspect existing child objects before retrying writes such as aperture or shade creation. `children_scope` must be a typed target dict, not `true` and not `parent_target`.
- There is no `get_honeybee_model_summary` public tool. For Honeybee counts, room energy assignments, child object counts, and compact object evidence, use `HB_search_model_objects`; for validity use `HB_validate_model`.
- `HB_search_model_objects` matches for rooms, faces, apertures, and doors include compact `child_counts`; use those counts before making separate full-model room/face/aperture/shade inventory searches.
- When confirming only Honeybee base model presence or retrieving the compact Honeybee base model target, call `GD_get_base_honeybee_model`.
- When confirming an existing Garden manifest, call `GD_get`; do not use filesystem probes or Python imports inside Code Mode.
- Keep Flowerpot as an opaque dict and do not unpack internal fields manually.
- When the user is validating failure behavior, do not auto-recover by default.
- In Code Mode, do not call original domain tools as outer MCP tools. Use them only inside `execute` via `await call_tool(tool_name, arguments)`.
- Tool names returned by Code Mode `search` are strings for `execute`/`call_tool`, not standalone MCP tool calls. Use the connected MCP session's Code Mode tools to discover and execute them.
- Every `call_tool` invocation must include a non-empty JSON `arguments` object that uses the tool's exact required parameter names. If a required-argument validation error appears, rebuild the full arguments object from the latest search result, tool schema, or prompt instead of retrying the failed shape.
- Use Windows paths in Code Mode arguments when a path is required. Prefer forward slashes so Python strings and JSON remain unambiguous; use exact runtime paths returned by diagnostics for external engines.
- For multi-step write workflows, prefer one concrete tool call at a time. After a successful search, immediately call the next MCP tool with the target from that search instead of ending with a plan sentence.
- Avoid parallel write calls against the same Garden/model.
- Agents should execute all dependent writes sequentially: wait for each write result, then search or validate before the next dependent write.
- If `operation_result.runtime_status="conflict"` and `readiness_status="reload_required"`, reread current Garden/model state, refresh `expected_revision`, and retry the intended write; never overwrite newer state.
- Do not rely on a process-local model lock.
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
  - `reference/honeybee/create-honeybee-apertures-by-guide-surface.md`
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
  - `reference/dragonfly/df-uwg-weather.md`
  - `reference/dragonfly/dragonfly-des.md`
  - `reference/dragonfly/urbanopt-energy.md`
  - `reference/dragonfly/df-grid-electric.md`
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
  - `reference/radiance/daylight-compliance-recipes.md`
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
- Tool naming, disclosure, or Skill reference maintenance:
  - `reference/platform/tool-naming.md`

## Scope

- `SKILL.md` should stay short and only provide entry rules and navigation.
- Detailed scenarios, validated shortest paths, prompt samples, success criteria, and failure examples belong under `reference/`.
- `reference/` is for Agent-facing usage paths only.
- Only paths verified by a completed direct MCP interaction can be documented as recommended paths in `reference/`.
