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
- For DES export, use a Garden `weather_file` target with an EPW path.
- Check runtime configuration before any URBANopt, GMT/uo_des, Docker, or OpenModelica execution.
- Keep URBANopt export Gardens on a short filesystem path on Windows. Dragonfly Energy asserts that the export simulation folder path must be shorter than 60 characters; the MCP service uses compact root-level export folders and preserves short caller path aliases for the SDK writer.

## Usual MCP Route

Inside one Code Mode `execute` block when dependencies are already known:

1. Create the Garden and Dragonfly Model if the prompt starts blank.
2. Create DES connector/parameter/loop targets with `df_des_thermal_connector` and the `df_des_create_*` authoring tools.
3. Export URBANopt artifacts with `df_des_export_urbanopt_model`.
4. Export DES artifacts with `df_des_export_model` when a weather target is available.
5. Prepare or start URBANopt with `df_des_prepare_urbanopt_project`, `df_des_start_urbanopt_simulation`, then `df_des_poll_urbanopt_simulation`.
6. After URBANopt outputs are ready, call `df_des_assign_building_loads`, then `df_des_start_sys_param` and `df_des_poll_sys_param`.
7. For Modelica work, use `df_des_write_modelica_project`, optionally `df_des_start_modelica_simulation`, and `df_des_poll_modelica_simulation`.

Return compact targets, summaries, runtime status, reports, and persistence receipts. Do not request or return full GeoJSON, HBJSON, scenario CSV, system-parameter JSON, or Modelica file bodies by default.

## Result Handling

- If URBANopt/GMT/Docker/OpenModelica are present but the user only asked for a smoke test or setup check, do not launch a real simulation without explicit permission.
- Poll ledgers and output paths for Modelica; do not invent numeric Modelica result readers or summaries.
- If a required Garden artifact target is missing, go back to the export or authoring step that creates it instead of fabricating a target dict.
- There is not yet a public DES object search/recovery tool. Keep returned DES targets in the same `execute` block, or deliberately recreate them after a partial failure.
- `df_des_export_model` needs DES-ready Dragonfly Building loads. A minimal Dragonfly Model made only from Room2D/Story/Building is not enough for full DES export.
