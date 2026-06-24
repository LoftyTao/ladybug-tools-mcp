# URBANopt Energy Workflow

Use this workflow when the user asks for URBANopt-backed Dragonfly Energy runs. For ordinary single-building annual Energy simulation, use Honeybee / EnergyPlus tools.

## Preconditions

- Create or select a Garden.
- Produce a Dragonfly Energy feature GeoJSON target first, usually with `df_des_export_urbanopt_model`.
- Keep the feature GeoJSON and later project/run artifacts inside the same Garden.
- On Windows, keep the Garden path visible to the SDK very short. A short drive alias that maps back into the allowed artifact folder is acceptable for validation; a normal long repository path can trigger `urbanopt_writer_path_too_long`.
- Expect the first real URBANopt run to spend a long time in Ruby/Bundler dependency setup. Poll the run and list outputs before reading simulation results.

## Tool Order

1. Call `df_urbanopt_prepare_project` with `garden_root` and `feature_geojson_target`.
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
- Do not call a generic `run_urbanopt` tool.
- Do not treat this as DES sys-param, Modelica, UWG, or Electric Grid execution.
