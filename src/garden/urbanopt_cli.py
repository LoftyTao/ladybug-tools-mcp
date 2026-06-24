"""MCP-local URBANopt CLI adapter for bundled URBANopt 1.2 runtimes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dragonfly_energy.config import folders as dragonfly_energy_folders
from dragonfly_energy.reopt import REoptParameter

from garden.ladybug_tools_config import (
    urbanopt_cli_gem_bundle_path,
    urbanopt_cli_runtime_gemfile_path,
    urbanopt_runtime_env,
)


def run_urbanopt_energy_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
    cpu_count: int | None = None,
) -> None:
    """Run URBANopt Energy with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    _translate_hbjson_to_osm(project_dir, cpu_count=cpu_count)
    _run_uo(
        project_dir=project_dir,
        runtime=runtime,
        args=["run", "-f", str(feature_geojson), "-s", str(scenario_csv)],
        log_name="run_simulation",
    )


def run_urbanopt_default_report_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
) -> tuple[Path, Path]:
    """Generate URBANopt default reports with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    _run_uo(
        project_dir=project_dir,
        runtime=runtime,
        args=["process", "--default", "-f", str(feature_geojson), "-s", str(scenario_csv)],
        log_name="run_default_report",
    )
    run_folder = project_dir / "run" / Path(scenario_csv).stem
    return run_folder / "default_scenario_report.csv", run_folder / "default_scenario_report.json"


def run_urbanopt_rnm_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
    underground_ratio: float = 0.9,
    lv_only: bool = True,
    nodes_per_building: int = 1,
) -> Path:
    """Run RNM with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    _update_rnm_inputs(
        feature_geojson=Path(feature_geojson),
        underground_ratio=underground_ratio,
        lv_only=lv_only,
        nodes_per_building=nodes_per_building,
    )
    _run_uo(
        project_dir=project_dir,
        runtime=runtime,
        args=["rnm", "--feature", str(feature_geojson), "--scenario", str(scenario_csv)],
        log_name="run_rnm",
    )
    return project_dir / "run" / Path(scenario_csv).stem / "rnm-us" / "results"


def run_urbanopt_reopt_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
    urdb_label: str,
    developer_key: str | None = None,
) -> tuple[Path, Path]:
    """Run REopt scenario post-processing with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    assumptions_file = _write_reopt_assumptions_file(
        project_dir=project_dir,
        runtime=runtime,
        urdb_label=urdb_label,
    )
    env_extra = {"GEM_DEVELOPER_KEY": developer_key} if developer_key else None
    _run_uo(
        project_dir=project_dir,
        runtime=runtime,
        args=[
            "process",
            "--reopt-scenario",
            "-f",
            str(feature_geojson),
            "-s",
            str(scenario_csv),
            "--reopt-scenario-assumptions-file",
            str(assumptions_file),
        ],
        log_name="run_reopt",
        env_extra=env_extra,
    )
    run_folder = project_dir / "run" / Path(scenario_csv).stem
    return run_folder / "scenario_optimization.csv", run_folder / "scenario_optimization.json"


def has_urbanopt_cli_bundle(runtime: dict[str, Any] | None) -> bool:
    """Return True when a runtime includes an existing CLI Gemfile."""
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    return bool(gemfile and gemfile.is_file())


def _check_project_files(feature_geojson: str | Path, scenario_csv: str | Path) -> Path:
    feature_path = Path(feature_geojson).expanduser().resolve()
    scenario_path = Path(scenario_csv).expanduser().resolve()
    if not feature_path.is_file():
        raise FileNotFoundError(f"No URBANopt feature GeoJSON was found: {feature_geojson}")
    if not scenario_path.is_file():
        raise FileNotFoundError(f"No URBANopt scenario CSV was found: {scenario_csv}")
    return feature_path.parent


def _translate_hbjson_to_osm(project_dir: Path, *, cpu_count: int | None) -> None:
    hb_json_dir = project_dir / "hb_json"
    if not hb_json_dir.is_dir():
        return
    osm_dir = project_dir / "osm"
    command = [
        sys.executable,
        "-m",
        "dragonfly_energy",
        "translate",
        "hb-models-to-osm",
        str(hb_json_dir),
        "--output-folder",
        str(osm_dir),
    ]
    sim_par_json = project_dir / "simulation_parameter.json"
    if sim_par_json.is_file():
        command.extend(["--sim-par-json", str(sim_par_json)])
    workflow_osw = project_dir / "mappers" / "honeybee_workflow.osw"
    if workflow_osw.is_file():
        with workflow_osw.open("r", encoding="utf-8") as handle:
            osw_dict = json.load(handle)
        weather_file = osw_dict.get("weather_file")
        if isinstance(weather_file, str) and weather_file:
            command.extend(["--epw-file", weather_file])
    runner_conf = project_dir / "runner.conf"
    if runner_conf.is_file():
        with runner_conf.open("r", encoding="utf-8") as handle:
            runner_dict = json.load(handle)
        runner_cpu_count = runner_dict.get("num_parallel")
        if isinstance(runner_cpu_count, int):
            cpu_count = runner_cpu_count
    if cpu_count is not None:
        command.extend(["--cpu-count", str(cpu_count)])
    env = os.environ.copy()
    env["PYTHONHOME"] = ""
    completed = subprocess.run(
        command,
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    _write_process_log(project_dir, "translate_hbjson_to_osm", command, completed)
    if completed.returncode != 0:
        raise RuntimeError(_process_error("Failed to translate HBJSON files to OSM.", completed))


def _run_uo(
    *,
    project_dir: Path,
    runtime: dict[str, Any] | None,
    args: list[str],
    log_name: str,
    env_extra: dict[str, str | None] | None = None,
) -> None:
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    if gemfile is None or not gemfile.is_file():
        raise RuntimeError("URBANopt CLI bundle Gemfile is unavailable.")
    command = [_bundle_executable(runtime), "exec", "uo", *args]
    with urbanopt_runtime_env(runtime):
        env = os.environ.copy()
        env["PYTHONHOME"] = ""
        env["BUNDLE_GEMFILE"] = str(gemfile)
        if env_extra:
            for key, value in env_extra.items():
                if value is not None:
                    env[key] = value
        completed = subprocess.run(
            command,
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
        )
    _write_process_log(project_dir, log_name, command, completed)
    if completed.returncode != 0:
        raise RuntimeError(_process_error(f"URBANopt CLI command failed: {log_name}.", completed))


def _update_rnm_inputs(
    *,
    feature_geojson: Path,
    underground_ratio: float,
    lv_only: bool,
    nodes_per_building: int,
) -> None:
    with feature_geojson.open("r", encoding="utf-8") as handle:
        geo_dict = json.load(handle)
    project = geo_dict.setdefault("project", {})
    project["underground_cables_ratio"] = underground_ratio
    project["only_lv_consumers"] = lv_only
    project["max_number_of_lv_nodes_per_building"] = nodes_per_building
    with feature_geojson.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(geo_dict, handle, indent=4)


def _write_reopt_assumptions_file(
    *,
    project_dir: Path,
    runtime: dict[str, Any] | None,
    urdb_label: str,
) -> Path:
    assumptions_path = getattr(dragonfly_energy_folders, "reopt_assumptions_path", None)
    reopt_folder = project_dir / "reopt"
    reopt_folder.mkdir(exist_ok=True)
    assumptions_file = reopt_folder / "reopt_assumptions.json"
    assumptions = _load_reopt_assumptions(runtime)
    if assumptions is None:
        if not assumptions_path:
            raise RuntimeError("No REopt assumptions template is configured in dragonfly_energy.")
        parameters = REoptParameter()
        parameters.pv_parameter.max_kw = 1000000000
        parameters.storage_parameter.max_kw = 1000000
        parameters.generator_parameter.max_kw = 1000000000
        assumptions = parameters.to_assumptions_dict(assumptions_path, urdb_label)
    assumptions = _normalize_reopt_assumptions(assumptions)
    _apply_reopt_defaults(assumptions, urdb_label=urdb_label)
    with assumptions_file.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(assumptions, handle, indent=4)
    return assumptions_file


def _load_reopt_assumptions(runtime: dict[str, Any] | None) -> dict[str, Any] | None:
    template = _reopt_assumptions_template(runtime)
    if template is None:
        return None
    with template.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _reopt_assumptions_template(runtime: dict[str, Any] | None) -> Path | None:
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    if bundle_path is not None:
        example_root = bundle_path / "gems"
        for candidate in sorted(example_root.glob("urbanopt-cli-*/example_files/reopt/multiPV_assumptions.json")):
            if candidate.is_file():
                return candidate
        fallback = bundle_path / "gems" / "urbanopt-cli-1.2.0" / "example_files" / "reopt" / "multiPV_assumptions.json"
        if fallback.is_file():
            return fallback
    return None


def _normalize_reopt_assumptions(assumptions: dict[str, Any]) -> dict[str, Any]:
    """Return an URBANopt REopt 1.2-compatible assumptions dictionary."""
    if "Scenario" in assumptions and isinstance(assumptions["Scenario"], dict):
        scenario = assumptions["Scenario"]
        site = scenario.get("Site")
        if isinstance(site, dict):
            assumptions = dict(site)
            if "time_steps_per_hour" in scenario:
                settings = assumptions.setdefault("Settings", {})
                if isinstance(settings, dict):
                    settings.setdefault("time_steps_per_hour", scenario["time_steps_per_hour"])
    if "Storage" in assumptions and "ElectricStorage" not in assumptions:
        assumptions["ElectricStorage"] = assumptions.pop("Storage")
    return assumptions


def _apply_reopt_defaults(assumptions: dict[str, Any], *, urdb_label: str) -> None:
    tariff = assumptions.setdefault("ElectricTariff", {})
    if isinstance(tariff, dict):
        tariff["urdb_label"] = urdb_label
    pv = assumptions.get("PV")
    if isinstance(pv, list):
        for system in pv:
            if isinstance(system, dict):
                system["max_kw"] = 1000000000
    elif isinstance(pv, dict):
        pv["max_kw"] = 1000000000
    storage = assumptions.setdefault("ElectricStorage", {})
    if isinstance(storage, dict):
        storage["max_kw"] = 1000000
        storage.setdefault("max_kwh", 1000000)
    generator = assumptions.setdefault("Generator", {})
    if isinstance(generator, dict):
        generator["max_kw"] = 1000000000


def _bundle_executable(runtime: dict[str, Any] | None) -> str:
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    executable_name = "bundle.bat" if os.name == "nt" else "bundle"
    if bundle_path is not None:
        candidate = bundle_path / "bin" / executable_name
        if candidate.is_file():
            return str(candidate)
    return executable_name


def _write_process_log(
    project_dir: Path,
    name: str,
    command: list[str],
    completed: subprocess.CompletedProcess[str],
) -> None:
    payload = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    log_path = project_dir / f"mcp_urbanopt_{name}.json"
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _process_error(message: str, completed: subprocess.CompletedProcess[str]) -> str:
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    parts = [message, f"returncode={completed.returncode}"]
    if stdout:
        parts.append(f"stdout={stdout[-2000:]}")
    if stderr:
        parts.append(f"stderr={stderr[-2000:]}")
    return "\n".join(parts)
