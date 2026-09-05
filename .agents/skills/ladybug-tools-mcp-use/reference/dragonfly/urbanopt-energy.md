# URBANopt Energy Workflow

Use this workflow when the user asks for URBANopt-backed Dragonfly Energy runs. For ordinary single-building annual Energy simulation, use Honeybee / EnergyPlus tools.

## Preconditions

- Create or select a Garden.
- Produce a Dragonfly Energy feature GeoJSON target first, usually with `DF_des_export_urbanopt_model`.
- Prefer a Garden `weather_file` target when running a real URBANopt Energy simulation. Local Ladybug Tools weather copied into the Garden is acceptable when remote EPW lookup is not needed.
- Keep the feature GeoJSON and later project/run artifacts inside the same Garden.
- Keep the selected Garden root short enough for the native URBANopt writer on Windows; a long path can trigger `urbanopt_writer_path_too_long`. If diagnostics select a Windows URBANopt bundle, let the runtime adapter handle the Windows-side path.
- URBANopt validation must use the local URBANopt CLI 1.4.0 bundle and an existing Garden weather target. Do not run Bundler installation, online weather download, online API submission, or dependency installers from the Agent path.
- For default URBANopt export folders, use the model display name; pass `folder_name` only when the user requests an explicit project directory name. Preserve native project and scenario subdirectories.
- Be precise about evidence labels: `local-bundle runtime pass` requires project `.bundle`/runner config, bundled command evidence, checked `run/**/*.log` plus `run/**/*.osw` simulation evidence files with at least one expected local bundle-path echo, clean Energy outputs, and `online_fetch_markers=[]`; process-tree TCP sampling with `external_connection_count=0` is optional `no_external_tcp_capture`; only call it a `fully offline pass` when the retained run was executed on a disconnected host or under an explicit firewall-deny capture.
- Apply the URBANopt-family local runtime matrix before runtime-heavy calls: Energy/OpenStudio can complete through the local CLI bundle plus local Garden project/weather artifacts; RNM/REopt online API blocked paths stay blocked until local services are configured; OpenDSS local runtime pack only means no `uo install_python`; DES/GMT local dependency only and Modelica local runtime only must be reported as blockers when local executables/libraries are missing.
- Do not report an Agent pass if the result still asks to rerun, retry, continue, poll, install, download, configure localhost services, provide a local runtime pack, or rerun under firewall/disconnected-host proof. Finish the action or report blocked/failed.
- Continue only when `LB_get_runtime_config.summary_view.engines.urbanopt.cli_runtime_gemfile.exists=true` and `LB_get_runtime_config.summary_view.engines.urbanopt.openstudio_runtime_gemfile.exists=true`; use the returned CLI Gemfile for URBANopt commands and the installed OpenStudio runtime Gemfile/root for building calculations. An SDK-only `urbanopt_gemfile_path` is a blocked MCP validation path.
- If URBANopt runtime preflight blocks, report `summary_view.runtime_diagnostics` first. It should include `network_policy.mode="local_runtime_required"`, `full_network_isolation_required=false`, `online_install_allowed=false`, `online_api_allowed=false`, and the local `urbanopt` runtime record.
- A real local URBANopt run can still be slow because OpenStudio/EnergyPlus is doing work. Poll the run and list outputs before reading simulation results.

## Tool Order

1. Call `DF_urbanopt_prepare_project` with `garden_root`, `feature_geojson_target`, and `weather_target` when an EPW is available.
2. Pass `DF_urbanopt_prepare_project.target` as `prepared_project_target`.
3. Pass `DF_urbanopt_prepare_project.scenario_csv_target` as `scenario_csv_target`.
4. Start with `DF_urbanopt_start_simulation`.
5. Poll with `DF_urbanopt_poll_simulation`.
6. List outputs with `DF_urbanopt_list_run_outputs` before diagnostics or DES follow-up.

## Code Mode Skeleton

```python
prepared = await call_tool("DF_urbanopt_prepare_project", {
    "garden_root": garden_root,
    "feature_geojson_target": feature_geojson_target,
    "weather_target": weather_target,
})
started = await call_tool("DF_urbanopt_start_simulation", {
    "garden_root": garden_root,
    "prepared_project_target": prepared["target"],
    "feature_geojson_target": feature_geojson_target,
    "scenario_csv_target": prepared["scenario_csv_target"],
})
polled = await call_tool("DF_urbanopt_poll_simulation", {
    "garden_root": garden_root,
    "run_target": started["run_target"],
})
outputs = await call_tool("DF_urbanopt_list_run_outputs", {
    "garden_root": garden_root,
    "run_target": started["run_target"],
})
output_files = outputs.get("outputs", outputs.get("matches", []))
{
    "prepared": prepared["summary_view"],
    "run": polled["summary_view"],
    "run_folder": polled["summary_view"]["run"]["run_folder"],
    "outputs": output_files,
}
```

## Result Handling

- Poll with `DF_urbanopt_poll_simulation` and list outputs with `DF_urbanopt_list_run_outputs` before result parsing.
- Only read SQL/HTML/ERR/IDF-style outputs after `DF_urbanopt_list_run_outputs` reports them.
- Use `run_folder` from the start or poll result and each output record's `path` from the output listing; do not derive paths from `run_id` or scenario names.
- If a rerun marks an earlier record `superseded`, use only the current run's returned outputs.
- Treat `failed.job` markers as a failed URBANopt run even when OSM or IDF files exist.
- `DF_urbanopt_prepare_project` writes the base Honeybee OSW with default feature reports enabled and project-local URBANopt CLI bundle config; do not call `base_honeybee_osw` or Bundler setup yourself from Code Mode.
- For SDK-prepared URBANopt projects, expect `runner.conf.gemfile_path` to point to the copied OpenStudio-runtime `Gemfile`, while `runner.conf.bundle_install_path` and the project `.bundle/config` point to the installed OpenStudio runtime root. Project preparation copies that runtime `Gemfile`, `Gemfile.lock`, and gemspec. CLI commands use the installed `gems/Gemfile`; do not substitute its CLI bundle for the building runtime.
- Use the Windows-visible URBANopt bundle paths and environment reported by the MCP adapter; do not hardcode a drive-letter Gemfile, call `bundle.bat` yourself, or rely on a bare global `uo` command. Do not set `BUNDLE_FROZEN` or process-level `BUNDLE_PATH` for Windows Garden runs.
- URBANopt CLI subprocesses are sanitized for local-bundle runtime validation: proxy variables and REopt/NREL API key variables are stripped before launch so inherited shell settings do not turn the Energy path into an online submission path.
- Grasshopper `DF Run URBANopt` supports optional measures, mapper measures, default feature reports, and emissions-year settings. The current MCP `DF_urbanopt_prepare_project` schema does not expose those optional knobs yet, so do not promise or fabricate them during Agent runs.
- Do not call a generic `run_urbanopt` tool.
- Do not treat this as DES sys-param, Modelica, UWG, or Electric Grid execution.
