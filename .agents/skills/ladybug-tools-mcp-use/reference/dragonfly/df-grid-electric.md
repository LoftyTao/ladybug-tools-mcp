# Dragonfly Electric Grid Workflow

Status: Agent-verified for Grid authoring, Grid-target URBANopt feature export, URBANopt Energy handoff, VisualizationSet handoff, and blocked/failed runtime ledgers. Use this reference for Dragonfly Electric Grid authoring and runtime-gated RNM/OpenDSS/REopt attempts. Do not describe RNM/OpenDSS/REopt numeric completion as Agent-verified until retained runtime evidence exists.

## Preconditions

- Create or select a Garden.
- Keep all Dragonfly Grid targets, feature GeoJSON artifacts, scenario CSV artifacts, run ledgers, and result artifacts in the same Garden.
- Use `DF_grid_search_opendss` to find catalog identifiers before creating transformers or electrical connectors.
- Use exact catalog identifiers from `DF_grid_search_opendss` matches. Do not guess values such as `default`.
- Keep the selected Garden root and any explicit URBANopt `folder_name` within the native writer's Windows path limit. Omit `folder_name` unless the user requests a custom project directory; the default uses the model display name.
- Use `DF_des_export_urbanopt_model` to produce the `dragonfly_des` feature GeoJSON target, then `DF_urbanopt_prepare_project` to produce the scenario CSV target before runtime tools. Pass `electrical_network_target`, `road_network_target`, and `ground_pv_targets` to `DF_des_export_urbanopt_model` when the downstream Grid run needs those features. Do not use ordinary `DF_export_model_file(file_type="geojson")` output as the Grid runtime prerequisite.
- RNM and REopt are URBANopt post-processing paths that may require a compatible local service/runtime. Before treating them as eligible, inspect `LB_get_runtime_config.summary_view.engines.urbanopt.rnm_service` / `reopt_service`: `configured` may come from `LADYBUG_MCP_RNM_USE_LOCALHOST` or `LADYBUG_MCP_REOPT_USE_LOCALHOST`, but it is not enough. Require `mcp_adapter_ready=true`, `local_service_reachable=true`, and `ready=true` before running either path. Also inspect the returned `urbanopt_source_evidence` fields.
- Run and poll URBANopt Energy through the current local 1.4.0 bundle first. For `DF_grid_start_rnm` and `DF_grid_start_reopt`, continue only when the returned local-service diagnostics are ready; otherwise return the blocked result with `summary_view.runtime_diagnostics.external_api_blocker` plus `summary_view.runtime_diagnostics.local_service`.
- OpenDSS should use the current local URBANopt CLI 1.4.0 bundle plus a pre-provisioned local runtime pack, not an online download. Before calling `DF_grid_start_opendss`, inspect `LB_get_runtime_config.summary_view.engines.urbanopt.network_policy.mode`, `opendss_python_deps.initialized`, `opendss_python_deps.offline_runtime_pack.ready`, `opendss_python_deps.offline_runtime_pack.missing_required_paths`, `opendss_python_deps.dependencies_require_network`, and `opendss_python_deps.dependency_network_sources`. Continue only when the policy is `local_runtime_required`, both readiness flags are `true`, and the missing list is empty. A pack outside the URBANopt installation can be exposed with `LADYBUG_MCP_URBANOPT_PYTHON_CONFIG=<path-to-python_config.json>`; MCP projects it into a Garden-local Ruby load-path shim before calling `uo opendss`. If dependency network sources are present, report them as a reason the pack must be pre-provisioned locally; do not treat them as local `.bundle` proof, which is judged from retained simulation logs and OSW files. If `DF_grid_start_opendss` still returns blocked, report `summary_view.runtime_diagnostics.opendss_python_deps` from that result first, then fall back to `LB_get_runtime_config` if the run result lacks diagnostics. Do not run `uo install_python` during validation. When ready, MCP follows the Grasshopper `DF Run OpenDSS` branch shape inside the adapter: RNM results trigger `--rnm`; otherwise the project `electrical_database.json` is passed as OpenDSS equipment when present.

## Tool Order

1. Search catalog identifiers with `DF_grid_search_opendss`.
2. Create `DF_grid_substation`.
3. Create `DF_grid_transformer` with a `transformer_properties_identifier`.
4. Create `DF_grid_electrical_connector` with a `power_line_identifier`.
5. Create `DF_grid_electrical_network` from the Substation, Transformer, and ElectricalConnector targets.
6. Optionally create `DF_grid_road_network` for RNM and `DF_grid_ground_photovoltaics` / `DF_grid_financial_parameters` for REopt handoff.
7. Preview with `DF_grid_network_to_visualization_set`, then use shared `LB_*` exporters.
8. Export prerequisites with `DF_des_export_urbanopt_model`, including Grid targets when applicable, then call `DF_urbanopt_prepare_project` to get the scenario CSV target.
9. Start and poll `DF_urbanopt_start_simulation` / `DF_urbanopt_poll_simulation`; preserve the run ledger and list outputs.
10. Start runtime-gated runs only with feature GeoJSON and scenario CSV targets: `DF_grid_start_rnm`, `DF_grid_start_opendss`, or `DF_grid_start_reopt`.
11. Read OpenDSS CSV outputs only when they are registered as `dragonfly_grid_opendss_result_csv` artifacts.

## Code Mode Skeleton

```python
catalog = await call_tool("DF_grid_search_opendss", {
    "keywords": ["OH1"],
    "catalogs": ["transformer_properties"],
    "limit": 1,
})
power_lines = await call_tool("DF_grid_search_opendss", {
    "catalogs": ["power_lines"],
    "limit": 1,
})
substation = await call_tool("DF_grid_substation", {
    "garden_root": garden_root,
    "identifier": "Substation_A",
    "footprint_points": [[0, 0], [4, 0], [4, 3], [0, 3]],
})
transformer = await call_tool("DF_grid_transformer", {
    "garden_root": garden_root,
    "identifier": "Transformer_A",
    "footprint_points": [[10, 0], [12, 0], [12, 2], [10, 2]],
    "transformer_properties_identifier": catalog["matches"][0]["identifier"],
})
connector = await call_tool("DF_grid_electrical_connector", {
    "garden_root": garden_root,
    "identifier": "Connector_A",
    "polyline_points": [[4, 1], [10, 1]],
    "power_line_identifier": power_lines["matches"][0]["identifier"],
})
network = await call_tool("DF_grid_electrical_network", {
    "garden_root": garden_root,
    "identifier": "Network_A",
    "substation_target": substation["target"],
    "transformer_targets": [transformer["target"]],
    "connector_targets": [connector["target"]],
})
roads = await call_tool("DF_grid_road_network", {
    "garden_root": garden_root,
    "identifier": "Roads_A",
    "substation_target": substation["target"],
    "road_segments": [{
        "identifier": "Main_Road",
        "polyline_points": [[-12, 3], [0, 3], [14, 3]],
    }],
})
preview = await call_tool("DF_grid_network_to_visualization_set", {
    "garden_root": garden_root,
    "network_target": network["target"],
})
exported = await call_tool("DF_des_export_urbanopt_model", {
    "garden_root": garden_root,
    "location": location,
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

- Stop on `runtime_status="blocked"` from `DF_grid_start_rnm`, `DF_grid_start_opendss`, or `DF_grid_start_reopt`; return the `run_target`, blocked reason, and any `summary_view.runtime_diagnostics` included in the run result. Use `LB_get_runtime_config` when the blocked result does not already include enough runtime detail.
- For RNM/REopt blocked results, include `summary_view.runtime_diagnostics.external_api_blocker.online_api_endpoints`, `online_api_blocked`, `local_service_configured`, `local_service_ready`, `required_local_runtime`, `summary_view.runtime_diagnostics.local_service.mcp_adapter_ready`, `summary_view.runtime_diagnostics.local_service.local_service_reachable`, and any `urbanopt_source_evidence` fields returned by `LB_get_runtime_config`.
- Do not run RNM-US or REopt online API paths as part of local-runtime validation. If a separate manual probe reaches `rnm.urbanopt.net` or `developer.nrel.gov`, record it as external-service evidence only, not MCP local completion.
- Treat OpenDSS as the current local URBANopt CLI 1.4.0 bundle path requiring a local runtime pack. If `LB_get_runtime_config.summary_view.engines.urbanopt.opendss_python_deps.initialized` or `offline_runtime_pack.ready` is not `true`, or if `offline_runtime_pack.missing_required_paths` lists `python_path`, `pip_path`, or `ditto_path`, report the dependency-initialization blocker and stop; include `dependencies_require_network` and `dependency_network_sources` when present, then ask for a pre-provisioned local pack exposed through `LADYBUG_MCP_URBANOPT_PYTHON_CONFIG` instead of downloading dependencies or calling `uo install_python` from the Agent run.
- When debugging Grid runs after `DF_urbanopt_prepare_project`, keep the URBANopt runner split intact: project `Gemfile` in `runner.conf.gemfile_path`, installed CLI gem bundle in `runner.conf.bundle_install_path`.
- Do not call `DF_urbanopt_*` tools as substitutes for Grid execution. URBANopt Energy and Electric Grid are separate workflow families.
- Do not invent `DF_urbanopt_export_model`, `DF_grid_run_opendss`, `DF_grid_run_rnm`, or `DF_grid_run_reopt`; the current public start tools are `DF_grid_start_*`.
- Do not treat Honeybee Energy ElectricLoadCenter or Ironbug electrical source objects as Dragonfly Electric Grid network objects.
