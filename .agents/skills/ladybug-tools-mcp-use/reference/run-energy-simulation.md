# Run Energy Simulation 与 EPW 气象文件

Use this path when the user needs to find or download EPW weather data and run a Honeybee Energy annual-energy-use simulation from a Garden model.

## 当前证据分级

### 已验证内容

Deterministic MCP tests cover:

- `search_tools` can find `search_epw_map`, `download_epw`, `search_weather_files`, `start_energy_run`, `run_energy`, `list_energy_runs`, `get_energy_run`, `list_energy_run_outputs`, `read_energy_eui`, and `read_energy_errors`.
- `search_epw_map` returns bounded candidates with an `epw_map_weather` target and does not return the full EPW map dataset.
- `download_epw` requires `garden_root`, stores weather under `imports/weather/<identifier>/`, registers the `weather_file` target in `garden.json`, and returns Garden-relative EPW/DDY paths.
- `search_weather_files` only searches `weather_file` targets already registered in the Garden manifest; it does not search SDK/global folders.
- `search_weather_files` normalizes identifiers, station text, EPW paths, and alias metadata so city-like queries such as `Shanghai weather` can reuse a registered target when that target carries the city token or alias.
- `start_energy_run` consumes a Garden-managed `weather_file` target, writes a `running` record to `runs/energy/index.json`, returns immediately with an `energy_run` target and `poll_next`, and schedules `run_energy` as background work.
- `run_energy` remains available for deterministic direct-MCP verification and blocking clients. It writes `runs/energy/index.json`, captures recipe stdout/stderr into `recipe_stdio.log`, returns an `energy_run` target, and does not return large output payloads.
- `create_energy_output_request` creates compact `energy_output_request` targets for requested EnergyPlus outputs, custom output variables, SQL output, summary reports, and later `DataCollection` reads.
- `start_energy_run` and `run_energy` accept `output_request_target`; prefer this over having an Agent copy or invent a large `SimulationParameter` dictionary.
- Deterministic-pass: `start_energy_run` and `run_energy` accept advanced `additional_idf_path`, `additional_idf_text`, and Garden-local `measures_path` arguments, mapping to the `annual-energy-use` recipe inputs `additional-idf` and `measures`. Use these only when the user explicitly provides or asks to use additional EnergyPlus IDF objects, EMS snippets, or OpenStudio measures; this is not a default Agent path.
- `read_energy_result_data` reads completed SQL outputs as compact Ladybug `DataCollection` summaries. It can list available SQL outputs when output selection and filters are omitted, filter outputs with `output_query`, `unit`, `data_type`, or `object_type`, and persist returned collections as `ladybug_data_collection` targets for the generic visualize tools when `save_data_collections=true`.
- `read_energy_result_data.summary_view.result_context` links returned DataCollections back to the run ledger, SQL artifact, selected output metadata, filter inputs, and the `energy_output_request` / custom outputs when available. Use this context to explain where a result came from instead of guessing from the output name alone.
- `data_collection_hourly_plot_to_visualization_set` and `data_collection_monthly_chart_to_visualization_set` consume saved Energy result `ladybug_data_collection` targets and return compact `visualization_set_target` outputs for HTML/SVG export.
- `energy_result_hourly_plot_to_html` and `energy_result_monthly_chart_to_html` remain compatibility/debug direct-to-HTML paths; do not use them as the default Agent chart path.
- A direct MCP custom full flow has been verified with a custom box room, custom ScheduleDay/ScheduleRuleset setpoint schedules saved to the Garden Properties Library, custom PSZ template HVAC saved to the Garden Properties Library, room edit by targets, real Boston TMY3 EPW/DDY from EPW Map, actual OpenStudio/EnergyPlus execution, and `read_energy_eui`.
- Invalid EPW/DDY preflight saves a failed run ledger instead of launching a long recipe.

OpenAI Agents smoke passed on 2026-04-25 in `tests/agent_integration/test_agent_energy_run_smoke.py`:

- `search_tools -> search_epw_map -> download_epw`
  - Recorded metrics: 3 outer tool calls, 2 real MCP calls, 12,963 total tokens, no repeated MCP tools.

OpenAI Agents smoke passed on 2026-04-27 in `tests/agent_integration/test_agent_energy_run_smoke.py`:

- `execute(search_epw_map -> download_epw)` for Garden-managed weather download.
  - Recorded metrics: 1 outer `execute`, 2 inner MCP calls, no repeated MCP tools.
- `search_tools -> start_energy_run -> get_energy_run` on a preflight-failure ledger fixture.
  - Recorded metrics: 3 outer tool calls, 2 real MCP calls, 21,561 total tokens, no repeated MCP tools.
  - The prompt did not call `run_energy`, `search_epw_map`, or `download_epw`.
- `execute(start_energy_run(reload_old=true) -> get_energy_run -> list_energy_run_outputs -> read_energy_eui)` on a completed-run ledger fixture.
  - Recorded metrics: 1 outer `execute`, 4 inner MCP calls, no repeated MCP tools.
  - The prompt did not call `run_energy`, `search_epw_map`, or `download_epw`.
- `execute(read_energy_result_data(save_data_collections=true) -> data_collection_hourly_plot_to_visualization_set -> visualization_set_to_html)` on a completed SQL ledger using a real EnergyPlus SQL sample resource.
  - Recorded metrics: 1 outer `execute`, 3 inner MCP calls, no repeated MCP tools.
  - The prompt did not call `run_energy`, `start_energy_run`, `search_epw_map`, or `download_epw`.
- `execute(read_energy_result_data(output_names=[...], save_data_collections=true) -> data_collection_monthly_chart_to_visualization_set -> visualization_set_to_html)` on a completed annual SQL ledger using a real EnergyPlus SQL sample resource.
  - Recorded metrics: 1 outer `execute`, 3 inner MCP calls, no repeated MCP tools.
  - Two same-unit series used `label`; the generic monthly chart tool wrote these labels into DataCollection metadata for the MonthlyChart legend.
- `execute(read_energy_result_data(output_query="heating energy", unit="kWh", data_type="Energy", save_data_collections=true) -> data_collection_monthly_chart_to_visualization_set -> visualization_set_to_html)` on a completed annual SQL ledger using a real EnergyPlus SQL sample resource.
  - Recorded metrics: 1 outer `execute`, 3 inner MCP calls, no repeated MCP tools.
  - This verifies the natural result-query path without exact EnergyPlus output names in the prompt or arguments.
- `execute(create_honeybee_room -> create_setpoint -> create_ideal_air_system -> search_honeybee_model_objects -> edit_honeybee_room -> validate_honeybee_model -> start_energy_run -> get_energy_run)` on an existing Garden/model with invalid weather preflight.
  - Recorded metrics: 1 outer `execute`, 8 inner MCP calls, no repeated MCP tools.
  - This replaces the old one-shot blocking `run_energy` Agent fixture.
- Supervised external Agent tasks passed on 2026-04-30:
  - `search_epw_map -> download_epw` saved Garden-managed weather in task 17.
  - `start_energy_run -> get_energy_run` completed a fresh OpenStudio/EnergyPlus background run in task 18, producing SQL and EUI outputs.
  - `list_energy_run_outputs -> read_energy_eui` read the completed run in task 19.
  - `read_energy_result_data(save_data_collections=true, include_values=false)` persisted SQL heating/cooling result DataCollections in task 20. The Agent still repeated result reads before closure, so this is verified for function and still active for cost optimization.
- MiniMax-M2.7 Agent smoke passed on 2026-05-10:
  - `execute(start_energy_run(additional_idf_text=EMS...) -> run_energy(measures_path=OpenStudio Results folder) -> list_energy_runs)` with intentionally invalid weather preflight.
  - Recorded metrics: 1 outer `execute`, 3 inner MCP calls, `5,908` total tokens, no repeated MCP tools.
  - This verifies Agent-side argument discovery and ledger recording for advanced inputs; it does not verify successful OpenStudio/EnergyPlus execution with a real measure because weather preflight was intentionally invalid.

Manual OpenAI Agents Code Mode smoke passed on 2026-04-26:

- `search -> execute(start_energy_run -> get_energy_run)` on invalid EPW/DDY preflight.
  - Recorded metrics: 2 outer tool calls, 2 inner MCP calls (`start_energy_run`, `get_energy_run`), 9,264 total tokens, no repeated MCP tools.

### 候选/未稳定内容

- The blocking Agent-side `run_energy -> list_energy_runs -> get_energy_run -> list_energy_run_outputs` path is not recommended. Recorded MiniMax/OpenAI Agents attempts either produced `arguments:null` with legacy `call_tool` or held a long `execute` request open until timeout/interruption.
- The `start_energy_run -> get_energy_run` preflight-failure path has been verified with OpenAI Agents in both Code Mode and legacy `search_tools/call_tool` smoke shapes.
- The completed-run output path has been verified with OpenAI Agents through a reloadable completed ledger fixture. This verifies result discovery and reading, not fresh EnergyPlus execution.
- A supervised fresh completed-run success path now exists: task 18 completed a new background recipe, task 19 read outputs/EUI, and task 20 saved SQL result DataCollections. Treat it as functionally verified but cost-heavy until more tasks reduce repeated search/result reads.
- The one-shot low-intelligence Agent full workflow from blank Garden to custom edit to actual simulation is not yet a stable recommended path. A recorded failed run used about 533k total tokens, made 23 outer tool calls, repeated `run_energy`, and did not reliably reach `read_energy_eui`. Treat this as a prompt/tool-description optimization input; prefer staged Agent workflows until it is re-verified.
- 2026-04-26 MiniMax v9 reached actual annual-energy-use launch through blocking `run_energy`, but the Agent harness timed out before final output. This proves the engine path can be reached and also confirms that blocking `run_energy` is not a stable Agent default.
- 2026-04-26 MiniMax v16 reached `start_energy_run -> get_energy_run` in the focused custom model-edit-simulate path and returned a final `running` run ledger. This verifies the natural Agent path can close to simulation start, but v17 failed before weather/run, so treat the one-shot large path as candidate rather than stable.
- 2026-04-26 staged MiniMax validation reached `search_epw_map -> download_epw -> start_energy_run -> get_energy_run` from an already-edited Garden and returned a final run summary. This staged run is a stable assumption for simulation-start handoff, but not evidence that the full one-shot create/edit/simulate prompt is stable.
- 2026-04-26 Garden-only weather rerun reached `search_epw_map -> download_epw(garden_root) -> search_weather_files -> start_energy_run -> get_energy_run` with Lhasa weather in a real MiniMax segment. It is now verified that weather files can stay inside Garden management through the Agent path.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch C Task 12 verified natural city weather switching and reuse: Shanghai-area and Beijing weather were downloaded as Garden `weather_file` targets, `search_weather_files` could rediscover the downloaded Shanghai file by internal station identifier such as `lang_gang` / `584760`, and a Beijing `start_energy_run -> get_energy_run` short launch reached `running`. A follow-up deterministic regression added normalized city/alias matching so `Shanghai weather` can rediscover a registered target with a Shanghai alias.
- 2026-05-01 Codex `ladybug_mcp_tester` natural broad Batch C Task 13 verified a fresh annual run to completion in a natural prompt chain, then `start_energy_run(reload_old=true) -> get_energy_run -> list_energy_run_outputs -> read_energy_eui` reused the completed ledger without starting a duplicate simulation. The retained run `task13_annual_office_baseline` produced 7 outputs and EUI total `401.979` in about 24 seconds.
- Broad weather choice decisions, such as selecting the best source for a climate study, are not yet a stable MCP decision workflow.
- More Energy recipes should reuse the same `energy_run` target, ledger, output index, and result-reader pattern when added.

## Shortest Agent Path: Download EPW

Use this as a weather-management stage. Do not mix broad weather-download discovery with simulation-start discovery in one `search_tools` query; mixed queries have caused Agents to repeatedly call `search_epw_map` with invalid arguments.

1. `search_tools`
   - Query: `search epw map download weather file`
2. `call_tool` -> `search_epw_map`
   - Use `query`, `source`, `host`, and optional coordinates to find a bounded candidate list.
   - Use `matches[i].target` for the selected station.
3. `call_tool` -> `download_epw`
   - Always pass the same `garden_root` as the model/simulation Garden.
   - Prefer `epw_map_target` from `search_epw_map`.
   - Only use `query / source / host` directly when the query resolves to exactly one candidate. Human station text like `Boston Logan TMY3` is accepted; if the source token is present and otherwise ambiguous, `download_epw` can prefer the exact source match and then prefer the DOE host when that breaks a two-host tie.
4. Keep the returned `weather_file` target for `start_energy_run`.

## Shortest Agent Path: Start Energy In Code Mode

Use Code Mode for Agent workflows. Keep all intermediate targets inside the `execute` code block.

1. `search`
   - Query: `start annual energy simulation energy use intensity eui`
2. Obtain weather:
   - Use `download_epw.target` or `search_weather_files.matches[i].target`.
   - For reuse, call `search_weather_files(garden_root, query=<city/station/source text>)` before downloading another EPW.
   - Do not look for `download_epw.value`; the weather target is returned as `target`.
3. `execute` -> `await call_tool("start_energy_run", arguments)`
   - Required:
     - `garden_root`
   - Preferred:
     - `weather_target`
   - Optional:
      - `model_target`; omit it to use the Garden base model.
      - `run_id`; provide a stable value when later reads need predictable addressing.
      - `units`: use `si` or `ip`; do not pass energy units such as `kWh`.
      - `additional_idf_path`: Garden-relative path to an existing `.idf` file for advanced EnergyPlus objects.
      - `additional_idf_text`: small inline EnergyPlus IDF text, such as complete EMS objects. Do not pass it together with `additional_idf_path`.
      - `measures_path`: Garden-relative path to an existing OpenStudio measures folder.
4. Poll with `get_energy_run` using `start_energy_run.target` or `run_id`.
5. When status is `completed`, call `list_energy_run_outputs`, then `read_energy_eui` if the EUI output exists.
6. When status is `failed`, call `list_energy_run_outputs` and `read_energy_errors` for bounded diagnostics.
7. When status remains `running`, return the `energy_run` target and tell the user the run is still in progress; do not retry `start_energy_run` for the same run.

## Shortest Agent Path: Read Completed Energy Outputs

Use this path when a Garden already has a completed `energy_run` ledger and the user wants result summaries such as EUI.

1. `search_tools`
   - Query: `completed annual energy simulation outputs eui read energy use intensity`
2. Optional `call_tool` -> `start_energy_run`
   - Use this only when the user says to reload or resume a known completed run.
   - Required:
     - `garden_root`
     - `run_id`
     - `reload_old=true`
   - If the run ledger is already `completed`, this returns the completed `energy_run` target without starting a new background run.
3. `call_tool` -> `get_energy_run`
   - Pass `garden_root` and either `run_id` or the `run_target`.
4. `call_tool` -> `list_energy_run_outputs`
   - Confirm the `eui` output exists before reading it.
5. `call_tool` -> `read_energy_eui`
   - Return the compact EUI JSON summary.

## Shortest Agent Path: Read And Visualize SQL DataCollections

Use this path when the run already has a completed SQL output and the user asks for hourly loads, HVAC demand, unmet hours, surface temperatures, or a custom EnergyPlus output variable. Prefer the generic `visualize` target path for new charts; the Energy-owned direct HTML tools remain available for compatibility.

1. `search_tools`
   - Query: `request hourly custom output datacollection sql results visualization`
2. Optional pre-run setup: `call_tool` -> `create_energy_output_request`
   - Use before a fresh run when the requested output was not already requested.
   - Pass `custom_outputs` for exact EnergyPlus output variable names.
   - Pass the returned `target` as `output_request_target` into `start_energy_run` or `run_energy`.
3. `call_tool` -> `read_energy_result_data`
   - Required:
     - `garden_root`
     - `run_id` or `run_target`
   - Optional:
     - omit `output_name` to list available SQL outputs.
     - pass exact `output_name` to read compact `DataCollection` summaries.
     - pass `output_names` to read several exact outputs in one call for a multi-series chart.
     - pass `output_query` plus optional `unit`, `data_type`, or `object_type` when the user gives a result concept rather than an exact EnergyPlus output name.
     - for a natural heating/cooling request, `output_query="heating cooling"` or `"heating or cooling"` matches outputs containing either heating or cooling; still prefer exact `output_names` when the Agent already knows the names.
     - keep `include_values=false` unless the user explicitly needs raw values.
     - set `save_data_collections=true` when the next step is a chart; use `data_collection_targets[]` rather than copying values.
   - Read `summary_view.result_context` and per-collection `output_parameter` when you need to report the run, SQL artifact, reporting frequency, unit, data type, or whether the output came from `custom_outputs`.
4. `call_tool` -> `data_collection_hourly_plot_to_visualization_set`
   - Required:
     - `garden_root`
     - `data_collection_target`
   - Preferred:
     - `return_visualization_set=false`
   - Returns a compact `visualization_set_target`.
5. `call_tool` -> `visualization_set_to_html` or `visualization_set_to_svg`
   - Pass the `visualization_set_target`; do not pass full HTML, SQL, values, or a full VisualizationSet through the conversation.

## Shortest Agent Path: Monthly Chart For Multiple Series

Use this path when the user wants a chart comparing multiple same-unit Energy result series, or wants hourly SQL results displayed as hourly, daily, monthly average, or monthly-per-hour patterns. Prefer reading each SQL output into a `ladybug_data_collection` target and then using the generic DataCollection monthly chart tool.

1. `search_tools`
   - Query: `monthly chart energy result datacollection target visualization set legend`
2. `call_tool` -> `read_energy_result_data`
   - Pass `output_names` with all desired exact EnergyPlus output names.
   - Set `include_values=false`.
   - Set `save_data_collections=true`.
   - Use the returned `data_collection_targets[]` as the chart series sources.
3. `call_tool` -> `data_collection_monthly_chart_to_visualization_set`
   - Required:
     - `garden_root`
     - `series`
   - Each `series` item requires:
     - `data_collection_target`
   - Each `series` item may include:
     - `label`
   - Use `label` for the chart legend name. The tool writes it into `DataCollection.header.metadata["type"]` because Ladybug MonthlyChart uses DataCollection metadata for legend naming.
   - Use one `time_interval` for the whole chart: `as_is`, `hourly`, `daily`, `monthly`, `monthly_per_hour`, `total_daily`, `total_monthly`, or `total_monthly_per_hour`.
   - Use `monthly` for monthly average lines and `monthly_per_hour` for monthly average by hour patterns.
   - Set `return_visualization_set=false` so the result contains `visualization_set_target`, not a full `VisualizationSet` dict.
   - All series in one MonthlyChart must have the same interval after conversion.
4. `call_tool` -> `visualization_set_to_html` or `visualization_set_to_svg`
   - Pass the `visualization_set_target`.
   - Do not use Energy-owned direct chart tools unless you specifically need the compatibility/debug one-call path.

## Blocking Direct-MCP Path

Use `run_energy` only for deterministic direct-MCP tests, debugging, or clients that can safely hold a long tool call open. Do not use it as the ordinary low-intelligence Agent path.

`run_energy` now captures Python stdout/stderr, logging handlers, and process-level stdout/stderr file descriptors into `recipe_stdio.log` so OpenStudio/EnergyPlus output does not corrupt stdio JSON-RPC. This hardens blocking direct-MCP use but does not make blocking `run_energy` the Agent default.

## Minimal Examples

```json
{
  "name": "search_epw_map",
  "arguments": {
    "query": "Boston",
    "source": "TMY3",
    "host": "doe",
    "max_results": 3
  }
}
```

```json
{
  "name": "download_epw",
  "arguments": {
    "garden_root": "<exact garden root>",
    "epw_map_target": "<search_epw_map.matches[0].target>"
  }
}
```

```json
{
  "name": "start_energy_run",
  "arguments": {
    "garden_root": "<exact garden root>",
    "weather_target": "<download_epw.target>",
    "output_request_target": "<create_energy_output_request.target>",
    "run_id": "baseline_annual_energy",
    "units": "si",
    "workers": 1
  }
}
```

```json
{
  "name": "list_energy_run_outputs",
  "arguments": {
    "garden_root": "<exact garden root>",
    "run_target": "<start_energy_run.target>"
  }
}
```

```json
{
  "name": "read_energy_result_data",
  "arguments": {
    "garden_root": "<exact garden root>",
    "run_id": "baseline_annual_energy",
    "output_names": [
      "Zone Ideal Loads Supply Air Total Heating Energy",
      "Zone Ideal Loads Supply Air Total Cooling Energy"
    ],
    "include_values": false,
    "save_data_collections": true
  }
}
```

```json
{
  "name": "data_collection_monthly_chart_to_visualization_set",
  "arguments": {
    "garden_root": "<exact garden root>",
    "series": [
      {
        "data_collection_target": "<read_energy_result_data.data_collection_targets[0]>",
        "label": "Heating Load"
      },
      {
        "data_collection_target": "<read_energy_result_data.data_collection_targets[1]>",
        "label": "Cooling Load"
      }
    ],
    "time_interval": "monthly",
    "chart_title": "Monthly HVAC Loads",
    "return_visualization_set": false
  }
}
```

```json
{
  "name": "visualization_set_to_html",
  "arguments": {
    "garden_root": "<exact garden root>",
    "visualization_set_target": "<data_collection_monthly_chart_to_visualization_set.visualization_set_target>",
    "name": "monthly_hvac_loads"
  }
}
```

Legacy direct Energy-owned chart path:

```json
{
  "name": "energy_result_monthly_chart_to_html",
  "arguments": {
    "garden_root": "<exact garden root>",
    "run_id": "baseline_annual_energy",
    "series": [
      {
        "output_name": "Zone Ideal Loads Supply Air Total Cooling Energy",
        "label": "Cooling Load"
      }
    ],
    "time_interval": "monthly",
    "chart_title": "Monthly HVAC Loads"
  }
}
```

## Expected Output

- `search_epw_map.matches[i].target`: an `epw_map_weather` target ready for `download_epw.epw_map_target`.
- `download_epw.target`: a Garden-managed `weather_file` target with Garden-relative `epw_path` and usually `ddy_path`.
- `start_energy_run.target`: an `energy_run` target.
- `start_energy_run.summary_view.poll_next`: compact next-call guidance for `get_energy_run`.
- `get_energy_run.summary_view.run.status`: `running`, `completed`, or `failed`.
- `list_energy_run_outputs.matches`: output names, Garden-relative paths, and existence flags.
- `read_energy_errors.text`: bounded ERR text with `summary_view.truncated`.
- `create_energy_output_request.target`: an `energy_output_request` target saved under `runs/energy/output_requests/`.
- `read_energy_result_data.data_collections`: compact summaries with output name, unit, metadata, value count, min/max/mean, optional bounded values, `output_parameter`, and compact per-collection `result_context`.
- `read_energy_result_data.data_collection_targets`: compact `ladybug_data_collection` targets when `save_data_collections=true`.
- `read_energy_result_data.summary_view.result_context`: compact provenance for the run ledger, SQL artifact, selected output metadata, filters, and output request.
- `data_collection_*_to_visualization_set.visualization_set_target`: compact `visualization_set` target when `garden_root` is provided and `return_visualization_set=false`.
- `energy_result_hourly_plot_to_html.artifact_receipt`: Garden artifact metadata for an HTML result visualization.
- `energy_result_monthly_chart_to_html.summary_view.series`: compact series summaries, including label, time interval, value count, unit, and source output name.
- Energy run ledgers are written through a locked atomic replace path. If an older or interrupted ledger file contains one valid JSON object followed by stale trailing bytes, run readers recover the first valid object instead of surfacing `JSONDecodeError: Extra data`.

## Notes

- Do not ask Agents to copy full EPW contents, SQL files, HTML reports, ZSZ archives, or model HBJSON through the conversation.
- Do not search global SDK weather folders or invent a separate weather folder. Weather downloads and reuse go through the Garden: `search_epw_map -> download_epw(garden_root=...) -> weather_target -> start_energy_run`.
- Do not call a public `get_energy_simulation_config`; it is intentionally service-layer behavior.
- If `start_energy_run.report.status` is `error`, still inspect the ledger with `get_energy_run` before deciding the run disappeared.
- If `get_energy_run` returns `running`, wait or return the `energy_run` target; do not start a duplicate run.
- If EPW/DDY preflight fails, fix or replace the weather target instead of retrying the same invalid files.
- For custom result outputs, do not handwrite `SimulationParameter` JSON unless the user specifically provides one. Use `create_energy_output_request` and pass its `target` as `output_request_target`.
- `read_energy_result_data` needs a completed SQL output. If `list_energy_run_outputs` has no existing `sql` output, create a new output request with `include_sqlite=true` and run the simulation again.
- For Code Mode, keep search, weather download, model edits, and `start_energy_run` in one `execute` block whenever they depend on one another. Variables do not persist across separate `execute` calls, and repeated weather/library searches were a major token sink in failed MiniMax natural runs.
- For compact exact-code Agent smoke prompts, prefer non-streamed model responses. MiniMax streamed ChatCompletions can expose partial `execute.code` function-call arguments before the final tool call is assembled, causing a syntax-error retry even when the second call succeeds.
- The server can recover direct tool proxy calls inside `execute`, such as `await search_epw_map(...)`, when the exact tool name is known. Keep `await call_tool("tool_name", arguments)` as the general default, but direct proxies are useful for short exact-code prompts where long nested `call_tool(...)` strings were causing function-call argument truncation.
- Service-side Code Mode now suppresses `print()` output from execute blocks so an Agent debug print does not corrupt stdio MCP transport. Still return compact dicts instead of printing because printed diagnostics are discarded.
- 2026-04-26 staged metrics D rerun closed `search_epw_map -> download_epw -> start_energy_run -> get_energy_run`, but MiniMax first tried `download_epw.station_id` and `start_energy_run.units="kWh"`. Prefer passing `search_epw_map.matches[i].target` to `download_epw.epw_map_target`, then pass `download_epw.target` or `weather_target` directly to `start_energy_run`.
- 2026-04-26 Garden-only D rerun still exposed point drift: MiniMax tried `units_system="SI"` once and invented `search_garden_assets` once before recovering. Keep `units` exactly `si` or `ip`, and use `search_weather_files` for Garden weather reuse.
- 2026-05-01 Codex `ladybug_mcp_tester` 20-Task Batch C verified Energy resources and target-only construction/HVAC handoff in Task 9 and Task 10. Task 11 started a real Boston Logan TMY3 annual-energy-use run; the main process later reloaded the completed run with `get_energy_run`, found 7 outputs, read EUI total `406.036`, listed SQL outputs, persisted `Electricity:Facility` as a `ladybug_data_collection`, exported JSON/CSV with `data_collection_to_file(name=...)`, generated monthly/hourly VisualizationSets, and exported HTML/SVG with `visualization_set_to_html/svg(name=...)`.
- The same Batch C confirmed why blocking `run_energy` remains a poor Agent default: Task 12 held the Agent open for a long real simulation and only completed after the controller had interrupted the subagent. Use `start_energy_run` plus later result reads for Agent workflows.
