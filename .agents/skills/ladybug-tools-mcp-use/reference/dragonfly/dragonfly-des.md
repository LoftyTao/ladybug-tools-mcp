---
type: reference
status: active
audience:
  - agents
  - mcp-users
tags:
  - dragonfly
  - des
  - district-energy
  - urbanopt
  - modelica
---

# Dragonfly DES Workflow

Use this path for Dragonfly DES tool discovery, minimal Dragonfly authoring, export behavior, and run ledgers.

## Preconditions

- Start from a Garden created or selected with `garden_create` / `garden_get`.
- Use a Garden `base_dragonfly_model` or an explicit Dragonfly Model target.
- Create or select DES loop targets before export. Fifth-generation and GHE loops need connector and parameter targets created by the DES authoring tools.
- Only pass `des_loop_target` to export when the loop topology is valid for Dragonfly Energy. ThermalConnectors must form a closed loop; a single open connector is accepted as an object but fails export. First export without a DES loop or author a closed connected loop.
- For `df_des_create_horizontal_pipe_parameter`, use `diameter_ratio` between 11 and 17.
- For DES export and URBANopt Energy runs, use a Garden `weather_file` target with an EPW path.
- Check runtime configuration before any URBANopt, GMT/uo_des, Docker, or OpenModelica execution.
- For sys-param and Modelica work, inspect `config_get_runtime_config.summary_view.engines.des_gmt`. Continue only when `available=true`; missing `uo_des.exe`, `thermalnetwork.exe`, `geojson_modelica_translator`, `ThermalNetwork`, or Modelica Buildings Library resources are local dependency blockers.
- Do not run `dragonfly_energy install all-des` from an Agent validation run. Grasshopper can use that installer when the user chooses it, but MCP validation must stay fully offline, report the missing `des_gmt` dependencies, and stop.
- Keep URBANopt export Gardens on a short filesystem path on Windows. Dragonfly Energy asserts that the export simulation folder path must be shorter than 60 characters; the MCP service uses compact root-level export folders and preserves short caller path aliases for the SDK writer.

## Usual MCP Route

Inside one Code Mode `execute` block when dependencies are already known:

1. Create the Garden and Dragonfly Model if the prompt starts blank.
2. Create DES connector/parameter/loop targets with `df_des_thermal_connector` and the `df_des_create_*` authoring tools.
3. Export URBANopt artifacts with `df_des_export_urbanopt_model`.
4. Export DES artifacts with `df_des_export_model` when a weather target is available.
5. Prepare or start URBANopt with `df_des_prepare_urbanopt_project` using the same `weather_target` when available, then `df_des_start_urbanopt_simulation` and `df_des_poll_urbanopt_simulation`.
6. After URBANopt outputs are ready, call `df_des_assign_building_loads`, then `df_des_start_sys_param` and `df_des_poll_sys_param`.
7. For Modelica work, use `df_des_write_modelica_project`, optionally `df_des_start_modelica_simulation`, and `df_des_poll_modelica_simulation`.

Return compact targets, summaries, runtime status, reports, and persistence receipts. Do not request or return full GeoJSON, HBJSON, scenario CSV, system-parameter JSON, or Modelica file bodies by default.

## Result Handling

- If URBANopt/GMT/Docker/OpenModelica are present but the user only asked for a smoke test or setup check, do not launch a real simulation without explicit permission.
- If `df_des_start_sys_param`, `df_des_write_modelica_project`, or `df_des_start_modelica_simulation` returns `runtime_status="blocked"`, report `summary_view.runtime_diagnostics` first. It should include `network_policy.mode="offline_required"`, `online_install_allowed=false`, `online_api_allowed=false`, and the relevant `des_gmt` or `modelica_runtime` missing dependency details.
- Do not treat successful URBANopt Energy completion as proof that DES sys-param or Modelica is ready.
- Poll ledgers and output paths for Modelica; do not invent numeric Modelica result readers or summaries.
- If a required Garden artifact target is missing, go back to the export or authoring step that creates it instead of fabricating a target dict.
- Treat `failed.job` markers as a failed URBANopt run even when OSM or IDF files exist.
- `df_des_prepare_urbanopt_project` writes the base Honeybee OSW and project-local URBANopt CLI bundle config; do not run Bundler setup manually from Code Mode.
- `df_des_assign_building_loads` is a scenario-results binding stage after URBANopt Energy outputs exist. Pass the MCP-required feature and scenario targets, but do not invent a separate feature-patching step or expect it to run DES sys-param.
- There is not yet a public DES object search/recovery tool. Keep returned DES targets in the same `execute` block, or deliberately recreate them after a partial failure.
- `df_des_export_model` needs DES-ready Dragonfly Building loads. A minimal Dragonfly Model made only from Room2D/Story/Building is not enough for full DES export.
