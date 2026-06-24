# URBANopt Energy Workflow

Use this workflow when the user asks for URBANopt-backed Dragonfly Energy runs. For ordinary single-building annual Energy simulation, use Honeybee / EnergyPlus tools.

## Preconditions

- Create or select a Garden.
- Produce a Dragonfly Energy feature GeoJSON target first, usually with `df_des_export_urbanopt_model`.
- Prefer a Garden `weather_file` target when running a real URBANopt Energy simulation. Local Ladybug Tools weather copied into the Garden is acceptable when remote EPW lookup is not needed.
- Keep the feature GeoJSON and later project/run artifacts inside the same Garden.
- On Windows, keep the Garden path visible to the SDK very short. For Dragonfly URBANopt runtime validation, use a real short Garden under `D:\`, such as `D:\df_mcp_ax7`; do not use mapped/cache drives or a deep repository path. A normal long repository path can trigger `urbanopt_writer_path_too_long`.
- Expect the first real URBANopt run to spend a long time in Ruby/Bundler dependency setup. Poll the run and list outputs before reading simulation results.

## Tool Order

1. Call `df_urbanopt_prepare_project` with `garden_root`, `feature_geojson_target`, and `weather_target` when an EPW is available.
2. Pass `df_urbanopt_prepare_project.target` as `prepared_project_target`.
3. Pass `df_urbanopt_prepare_project.scenario_csv_target` as `scenario_csv_target`.
4. Start with `df_urbanopt_start_simulation`.
5. Poll with `df_urbanopt_poll_simulation`.
6. List outputs with `df_urbanopt_list_run_outputs` before diagnostics or DES follow-up.

## Code Mode Skeleton

```python
prepared = await call_tool("df_urbanopt_prepare_project", {
    "garden_root": garden_root,
    "feature_geojson_target": feature_geojson_target,
    "weather_target": weather_target,
})
started = await call_tool("df_urbanopt_start_simulation", {
    "garden_root": garden_root,
    "prepared_project_target": prepared["target"],
    "feature_geojson_target": feature_geojson_target,
    "scenario_csv_target": prepared["scenario_csv_target"],
})
polled = await call_tool("df_urbanopt_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["run_target"],
})
outputs = await call_tool("df_urbanopt_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": started["run_target"],
})
{
    "prepared": prepared["summary_view"],
    "run": polled["summary_view"],
    "outputs": outputs["summary_view"],
}
```

## Result Handling

- Poll with `df_urbanopt_poll_simulation` and list outputs with `df_urbanopt_list_run_outputs` before result parsing.
- Only read SQL/HTML/ERR/IDF-style outputs after `df_urbanopt_list_run_outputs` reports them.
- Treat `failed.job` markers as a failed URBANopt run even when OSM or IDF files exist.
- `df_urbanopt_prepare_project` writes the base Honeybee OSW with default feature reports enabled and project-local URBANopt CLI bundle config; do not call `base_honeybee_osw` or Bundler setup yourself from Code Mode.
- For SDK-prepared URBANopt projects, expect `runner.conf.gemfile_path` to point to the copied project `Gemfile` and `runner.conf.bundle_install_path` to point to the installed URBANopt CLI gem bundle. Do not replace this with the global CLI Gemfile path in Agent-side debugging.
- URBANopt CLI 1.2.0 uses `C:\URBANopt-cli-1.2.0\gems\Gemfile` with bundled `bundle.bat exec uo`; do not rely on a bare global `uo` command when debugging Windows runtime behavior.
- Grasshopper `DF Run URBANopt` supports optional measures, mapper measures, default feature reports, and emissions-year settings. The current MCP `df_urbanopt_prepare_project` schema does not expose those optional knobs yet, so do not promise or fabricate them during Agent runs.
- Do not call a generic `run_urbanopt` tool.
- Do not treat this as DES sys-param, Modelica, UWG, or Electric Grid execution.
