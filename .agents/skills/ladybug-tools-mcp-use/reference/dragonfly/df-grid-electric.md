# Dragonfly Electric Grid Workflow

Status: deterministic-contract-pass. Use this reference for Dragonfly Electric Grid authoring and runtime-gated RNM/OpenDSS/REopt attempts. Do not describe Grid runtime completion as Agent-verified until retained Agent evidence exists.

OKF evidence source: `docs/llm-wiki/tools/dragonfly-grid-tools.md`.

## Preconditions

- Create or select a Garden.
- Keep all Dragonfly Grid targets, feature GeoJSON artifacts, scenario CSV artifacts, run ledgers, and result artifacts in the same Garden.
- Use `df_grid_search_opendss` to find catalog identifiers before creating transformers or electrical connectors.
- Use `df_des_export_urbanopt_model` or another supported Dragonfly Energy export path to produce feature GeoJSON and scenario CSV targets before runtime tools.

## Tool Order

1. Search catalog identifiers with `df_grid_search_opendss`.
2. Create `df_grid_substation`.
3. Create `df_grid_transformer` with a `transformer_properties_identifier`.
4. Create `df_grid_electrical_connector` with a `power_line_identifier`.
5. Create `df_grid_electrical_network` from the Substation, Transformer, and ElectricalConnector targets.
6. Optionally create `df_grid_road_network` for RNM and `df_grid_ground_photovoltaics` / `df_grid_financial_parameters` for REopt handoff.
7. Start runtime-gated runs only with feature GeoJSON and scenario CSV targets: `df_grid_start_rnm`, `df_grid_start_opendss`, or `df_grid_start_reopt`.
8. Read OpenDSS CSV outputs only when they are registered as `dragonfly_grid_opendss_result_csv` artifacts.
9. Preview with `df_grid_network_to_visualization_set` or `df_grid_results_to_visualization_set`, then use shared `visualization_*` exporters.

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
preview = await call_tool("df_grid_network_to_visualization_set", {
    "garden_root": garden_root,
    "network_target": network["target"],
})
{
    "network": network["summary_view"],
    "preview": preview["visualization_set_target"],
}
```

## Stop Conditions

- Stop on `runtime_status="blocked"` from `df_grid_start_rnm`, `df_grid_start_opendss`, or `df_grid_start_reopt`; return the `run_target`, blocked reason, and `config_get_runtime_config` guidance.
- Do not call `df_urbanopt_*` tools as substitutes for Grid execution. URBANopt Energy and Electric Grid are separate workflow families.
- Do not invent `df_urbanopt_export_model`, `df_grid_run_opendss`, `df_grid_run_rnm`, or `df_grid_run_reopt`; the current public start tools are `df_grid_start_*`.
- Do not treat Honeybee Energy ElectricLoadCenter or Ironbug electrical source objects as Dragonfly Electric Grid network objects.
