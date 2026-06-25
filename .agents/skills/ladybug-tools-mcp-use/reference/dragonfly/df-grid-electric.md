# Dragonfly Electric Grid Workflow

Status: Agent-verified for Grid authoring, Grid-target URBANopt feature export, URBANopt Energy handoff, VisualizationSet handoff, and blocked/failed runtime ledgers. Use this reference for Dragonfly Electric Grid authoring and runtime-gated RNM/OpenDSS/REopt attempts. Do not describe RNM/OpenDSS/REopt numeric completion as Agent-verified until retained runtime evidence exists.

OKF source: `docs/llm-wiki/tools/dragonfly-grid-tools.md`.

## Preconditions

- Create or select a Garden.
- Keep all Dragonfly Grid targets, feature GeoJSON artifacts, scenario CSV artifacts, run ledgers, and result artifacts in the same Garden.
- Use `df_grid_search_opendss` to find catalog identifiers before creating transformers or electrical connectors.
- Use exact catalog identifiers from `df_grid_search_opendss` matches. Do not guess values such as `default`.
- Use a real short Garden root under `D:\`, such as `D:\df_mcp_ax7`, and a short `folder_name` for URBANopt-backed handoff artifacts because the Dragonfly Energy URBANopt writer rejects long export folders. Do not use mapped/cache drives for this validation lane.
- Use `df_des_export_urbanopt_model` to produce the `dragonfly_des` feature GeoJSON target, then `df_urbanopt_prepare_project` to produce the scenario CSV target before runtime tools. Pass `electrical_network_target`, `road_network_target`, and `ground_pv_targets` to `df_des_export_urbanopt_model` when the downstream Grid run needs those features. Do not use ordinary `df_export_model_file(file_type="geojson")` output as the Grid runtime prerequisite.
- RNM and REopt are URBANopt post-processing paths, but in URBANopt CLI 1.2.0 they are API-backed unless a compatible local service/runtime is configured. Run and poll URBANopt Energy through the local 1.2.0 bundle first. Under the MCP confirmed no-network policy, expect `df_grid_start_rnm` and `df_grid_start_reopt` to return `runtime_status="blocked"` before online API submission and report `summary_view.runtime_diagnostics.external_api_blocker`.
- OpenDSS should use the local URBANopt CLI 1.2.0 bundle plus an offline-initialized runtime pack, not an online download. Before calling `df_grid_start_opendss`, inspect `config_get_runtime_config.summary_view.engines.urbanopt.network_policy.mode`, `opendss_python_deps.initialized`, `opendss_python_deps.offline_runtime_pack.ready`, and `opendss_python_deps.offline_runtime_pack.missing_required_paths`. Continue only when the policy is `offline_required`, both readiness flags are `true`, and the missing list is empty. If `df_grid_start_opendss` still returns blocked, report `summary_view.runtime_diagnostics.opendss_python_deps` from that result first, then fall back to `config_get_runtime_config` if the run result lacks diagnostics. Do not run `uo install_python` during validation. When ready, MCP follows the Grasshopper `DF Run OpenDSS` branch shape inside the adapter: RNM results trigger `--rnm`; otherwise the project `electrical_database.json` is passed as OpenDSS equipment when present.

## Tool Order

1. Search catalog identifiers with `df_grid_search_opendss`.
2. Create `df_grid_substation`.
3. Create `df_grid_transformer` with a `transformer_properties_identifier`.
4. Create `df_grid_electrical_connector` with a `power_line_identifier`.
5. Create `df_grid_electrical_network` from the Substation, Transformer, and ElectricalConnector targets.
6. Optionally create `df_grid_road_network` for RNM and `df_grid_ground_photovoltaics` / `df_grid_financial_parameters` for REopt handoff.
7. Preview with `df_grid_network_to_visualization_set`, then use shared `visualization_*` exporters.
8. Export prerequisites with `df_des_export_urbanopt_model`, including Grid targets when applicable, then call `df_urbanopt_prepare_project` to get the scenario CSV target.
9. Start and poll `df_urbanopt_start_simulation` / `df_urbanopt_poll_simulation`; preserve the run ledger and list outputs.
10. Start runtime-gated runs only with feature GeoJSON and scenario CSV targets: `df_grid_start_rnm`, `df_grid_start_opendss`, or `df_grid_start_reopt`.
11. Read OpenDSS CSV outputs only when they are registered as `dragonfly_grid_opendss_result_csv` artifacts.

## Code Mode Skeleton

```python
catalog = await call_tool("df_grid_search_opendss", {
    "keywords": ["OH1"],
    "catalogs": ["transformer_properties"],
    "limit": 1,
})
power_lines = await call_tool("df_grid_search_opendss", {
    "catalogs": ["power_lines"],
    "limit": 1,
})
substation = await call_tool("df_grid_substation", {
    "garden_root": garden_root,
    "identifier": "Substation_A",
    "footprint_points": [[0, 0], [4, 0], [4, 3], [0, 3]],
})
transformer = await call_tool("df_grid_transformer", {
    "garden_root": garden_root,
    "identifier": "Transformer_A",
    "footprint_points": [[10, 0], [12, 0], [12, 2], [10, 2]],
    "transformer_properties_identifier": catalog["matches"][0]["identifier"],
})
connector = await call_tool("df_grid_electrical_connector", {
    "garden_root": garden_root,
    "identifier": "Connector_A",
    "polyline_points": [[4, 1], [10, 1]],
    "power_line_identifier": power_lines["matches"][0]["identifier"],
})
network = await call_tool("df_grid_electrical_network", {
    "garden_root": garden_root,
    "identifier": "Network_A",
    "substation_target": substation["target"],
    "transformer_targets": [transformer["target"]],
    "connector_targets": [connector["target"]],
})
roads = await call_tool("df_grid_road_network", {
    "garden_root": garden_root,
    "identifier": "Roads_A",
    "substation_target": substation["target"],
    "road_segments": [{
        "identifier": "Main_Road",
        "polyline_points": [[-12, 3], [0, 3], [14, 3]],
    }],
})
preview = await call_tool("df_grid_network_to_visualization_set", {
    "garden_root": garden_root,
    "network_target": network["target"],
})
exported = await call_tool("df_des_export_urbanopt_model", {
    "garden_root": garden_root,
    "location": location,
    "folder_name": "r",
    "electrical_network_target": network["target"],
    "road_network_target": roads["target"],
})
{
    "network": network["summary_view"],
    "preview": preview["visualization_set_target"],
    "feature_geojson_target": exported["feature_geojson_target"],
}
```

## Stop Conditions

- Stop on `runtime_status="blocked"` from `df_grid_start_rnm`, `df_grid_start_opendss`, or `df_grid_start_reopt`; return the `run_target`, blocked reason, and any `summary_view.runtime_diagnostics` included in the run result. Use `config_get_runtime_config` when the blocked result does not already include enough runtime detail.
- For RNM/REopt blocked results, include `summary_view.runtime_diagnostics.external_api_blocker.online_api_endpoints`, `online_api_blocked`, and `required_local_runtime` in the user-facing summary.
- Do not run RNM-US or REopt online API paths as part of no-network validation. If a separate manual probe reaches `rnm.urbanopt.net` or `developer.nrel.gov`, record it as external-service evidence only, not MCP local completion.
- Treat OpenDSS as a local URBANopt CLI 1.2.0 bundle path requiring an offline runtime pack. If `config_get_runtime_config.summary_view.engines.urbanopt.opendss_python_deps.initialized` or `offline_runtime_pack.ready` is not `true`, or if `offline_runtime_pack.missing_required_paths` lists `python_path`, `pip_path`, or `ditto_path`, report the dependency-initialization blocker and stop; do not download dependencies or call `uo install_python` from the Agent run.
- When debugging Grid runs after `df_urbanopt_prepare_project`, keep the URBANopt runner split intact: project `Gemfile` in `runner.conf.gemfile_path`, installed CLI gem bundle in `runner.conf.bundle_install_path`.
- Do not call `df_urbanopt_*` tools as substitutes for Grid execution. URBANopt Energy and Electric Grid are separate workflow families.
- Do not invent `df_urbanopt_export_model`, `df_grid_run_opendss`, `df_grid_run_rnm`, or `df_grid_run_reopt`; the current public start tools are `df_grid_start_*`.
- Do not treat Honeybee Energy ElectricLoadCenter or Ironbug electrical source objects as Dragonfly Electric Grid network objects.
