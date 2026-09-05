"""MCP-local URBANopt CLI adapter for the required bundled runtime."""

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
    REQUIRED_RUNTIME_VERSIONS,
    urbanopt_cli_gem_bundle_path,
    urbanopt_cli_runtime_gemfile_path,
    urbanopt_runtime_env,
)

REMOTE_SERVICE_ENV_KEYS = {
    "ALL_PROXY",
    "FTP_PROXY",
    "GEM_DEVELOPER_KEY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NREL_API_KEY",
    "NREL_DEVELOPER_KEY",
    "NO_PROXY",
    "REOPT_API_KEY",
}


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
    use_localhost: bool = False,
) -> Path:
    """Run RNM with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    _update_rnm_inputs(
        feature_geojson=Path(feature_geojson),
        underground_ratio=underground_ratio,
        lv_only=lv_only,
        nodes_per_building=nodes_per_building,
    )
    if use_localhost:
        _run_rnm_localhost(
            project_dir=project_dir,
            runtime=runtime,
            feature_geojson=Path(feature_geojson),
            scenario_csv=Path(scenario_csv),
        )
    else:
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
    use_localhost: bool = False,
) -> tuple[Path, Path]:
    """Run REopt scenario post-processing with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    assumptions_file = _write_reopt_assumptions_file(
        project_dir=project_dir,
        runtime=runtime,
        urdb_label=urdb_label,
    )
    env_extra = {"GEM_DEVELOPER_KEY": developer_key} if developer_key and not use_localhost else None
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
        use_reopt_localhost_adapter=use_localhost,
    )
    run_folder = project_dir / "run" / Path(scenario_csv).stem
    return run_folder / "scenario_optimization.csv", run_folder / "scenario_optimization.json"


def run_urbanopt_opendss_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
    autosize: bool = False,
) -> Path:
    """Run OpenDSS with the CLI bundle Gemfile and initialized Python deps."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    args = ["opendss", "--scenario", str(scenario_csv), "--feature", str(feature_geojson)]
    if _opendss_rnm_results_path(project_dir, Path(scenario_csv)).is_file():
        args.append("--rnm")
    else:
        equipment = project_dir / "electrical_database.json"
        if equipment.is_file():
            args.extend(["--equipment", str(equipment)])
    if autosize:
        args.append("--upgrade")
    _run_uo(
        project_dir=project_dir,
        runtime=runtime,
        args=args,
        log_name="run_opendss",
    )
    return project_dir


def _opendss_rnm_results_path(project_dir: Path, scenario_csv: Path) -> Path:
    """Return the RNM distribution-system GeoJSON expected before OpenDSS."""
    scenario_name = scenario_csv.stem
    scenario_path = (
        project_dir
        / "run"
        / scenario_name
        / "rnm-us"
        / "results"
        / "GeoJSON"
        / "Distribution_system.json"
    )
    if scenario_path.is_file() or scenario_name == "honeybee_scenario":
        return scenario_path
    return (
        project_dir
        / "run"
        / "honeybee_scenario"
        / "rnm-us"
        / "results"
        / "GeoJSON"
        / "Distribution_system.json"
    )


def has_urbanopt_cli_bundle(runtime: dict[str, Any] | None) -> bool:
    """Return True when a runtime includes an existing CLI Gemfile."""
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    return bool(gemfile and gemfile.is_file())


def has_urbanopt_opendss_python_deps(runtime: dict[str, Any] | None) -> bool:
    """Return True when URBANopt CLI OpenDSS Python deps are initialized."""
    if isinstance(runtime, dict):
        deps = runtime.get("opendss_python_deps")
        if isinstance(deps, dict):
            pack = deps.get("offline_runtime_pack")
            if isinstance(pack, dict):
                return deps.get("initialized") is True and pack.get("ready") is True
            if deps.get("initialized") is True:
                return _opendss_python_config_ready(_opendss_python_config(runtime))
    config = _opendss_python_config(runtime)
    return _opendss_python_config_ready(config)


def _opendss_python_config_ready(config: Path | None) -> bool:
    if config is None or not config.is_file():
        return False
    try:
        loaded = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(loaded, dict):
        return False
    for key in ("python_path", "pip_path", "ditto_path"):
        value = loaded.get(key)
        if not isinstance(value, str) or not Path(value).is_file():
            return False
    return True


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
    temp_dir = project_dir / "tmp"
    temp_dir.mkdir(exist_ok=True)
    env.update(TEMP=str(temp_dir), TMP=str(temp_dir))
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
    use_reopt_localhost_adapter: bool = False,
) -> None:
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    if gemfile is None or not gemfile.is_file():
        raise RuntimeError("URBANopt CLI bundle Gemfile is unavailable.")
    command = [_bundle_executable(runtime), "exec", "uo", *args]
    with urbanopt_runtime_env(runtime):
        env = os.environ.copy()
        env["PYTHONHOME"] = ""
        temp_dir = project_dir / "tmp"
        temp_dir.mkdir(exist_ok=True)
        env.update(TEMP=str(temp_dir), TMP=str(temp_dir))
        env.update(_offline_bundler_env(runtime, gemfile))
        env.pop("BUNDLE_PATH", None)
        env.pop("BUNDLE_FROZEN", None)
        if args and args[0] == "opendss":
            _apply_urbanopt_python_deps_shim(
                env=env,
                project_dir=project_dir,
                runtime=runtime,
            )
        if use_reopt_localhost_adapter:
            _apply_reopt_localhost_patch(env=env, project_dir=project_dir)
        if env_extra:
            for key, value in env_extra.items():
                if value is not None:
                    env[key] = value
        _sanitize_remote_service_env(env)
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


def _apply_reopt_localhost_patch(*, env: dict[str, str], project_dir: Path) -> None:
    patch_dir = project_dir / ".mcp_urbanopt_reopt"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_path = patch_dir / "mcp_reopt_localhost_patch.rb"
    patch_path.write_text(
        "\n".join(
            [
                "require 'urbanopt/reopt/reopt_post_processor'",
                "require 'urbanopt/reopt/reopt_lite_api'",
                "",
                "module URBANopt",
                "  module REopt",
                "    class REoptPostProcessor",
                "      unless method_defined?(:mcp_original_initialize)",
                "        alias_method :mcp_original_initialize, :initialize",
                "        def initialize(scenario_report, scenario_reopt_assumptions_file = nil, reopt_feature_assumptions = [], nrel_developer_key = nil, localhost = false, erp_assumptions_file = nil)",
                "          mcp_original_initialize(scenario_report, scenario_reopt_assumptions_file, reopt_feature_assumptions, nrel_developer_key, true, erp_assumptions_file)",
                "        end",
                "      end",
                "    end",
                "",
                "    class REoptLiteAPI",
                "      unless method_defined?(:mcp_original_initialize)",
                "        alias_method :mcp_original_initialize, :initialize",
                "        def initialize(nrel_developer_key = nil, use_localhost = false)",
                "          mcp_original_initialize(nrel_developer_key, true)",
                "          @uri_submit = URI.parse('http://127.0.0.1:8000/v3/job/')",
                "          @uri_submit_outagesimjob = URI.parse('http://127.0.0.1:8000/v3/erp/')",
                "        end",
                "      end",
                "    end",
                "  end",
                "end",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    existing_rubylib = env.get("RUBYLIB")
    env["RUBYLIB"] = (
        str(patch_dir)
        if not existing_rubylib
        else str(patch_dir) + os.pathsep + existing_rubylib
    )
    existing_rubyopt = env.get("RUBYOPT")
    patch_option = "-rmcp_reopt_localhost_patch"
    env["RUBYOPT"] = (
        patch_option
        if not existing_rubyopt
        else patch_option + " " + existing_rubyopt
    )


def _apply_urbanopt_python_deps_shim(
    *,
    env: dict[str, str],
    project_dir: Path,
    runtime: dict[str, Any] | None,
) -> None:
    python_config = _runtime_opendss_python_config(runtime)
    if python_config is None:
        return
    shim_python_deps = project_dir / ".mcp_urbanopt_python_deps" / "example_files" / "python_deps"
    shim_python_deps.mkdir(parents=True, exist_ok=True)
    (shim_python_deps / "python_config.json").write_text(
        python_config.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    dependencies = _runtime_opendss_dependencies_file(runtime)
    if dependencies is not None:
        (shim_python_deps / "dependencies.json").write_text(
            dependencies.read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
    example_files = shim_python_deps.parent
    existing = env.get("RUBYLIB")
    env["RUBYLIB"] = (
        str(example_files)
        if not existing
        else str(example_files) + os.pathsep + existing
    )


def _runtime_opendss_python_config(runtime: dict[str, Any] | None) -> Path | None:
    if not isinstance(runtime, dict):
        return None
    deps = runtime.get("opendss_python_deps")
    if not isinstance(deps, dict):
        return None
    pack = deps.get("offline_runtime_pack")
    if not isinstance(pack, dict) or pack.get("source") != "explicit_python_config":
        return None
    config_record = pack.get("python_config")
    if not isinstance(config_record, dict):
        return None
    path = config_record.get("path")
    if not isinstance(path, str) or not path:
        return None
    config_path = Path(path)
    return config_path if config_path.is_file() else None


def _runtime_opendss_dependencies_file(runtime: dict[str, Any] | None) -> Path | None:
    if not isinstance(runtime, dict):
        return None
    deps = runtime.get("opendss_python_deps")
    if not isinstance(deps, dict):
        return None
    record = deps.get("dependencies_file")
    if not isinstance(record, dict):
        return None
    path = record.get("path")
    if not isinstance(path, str) or not path:
        return None
    dependencies = Path(path)
    return dependencies if dependencies.is_file() else None


def _run_rnm_localhost(
    *,
    project_dir: Path,
    runtime: dict[str, Any] | None,
    feature_geojson: Path,
    scenario_csv: Path,
) -> None:
    script = "\n".join(
        [
            "require 'urbanopt/rnm'",
            "scenario_csv = ARGV.fetch(0)",
            "feature_file = ARGV.fetch(1)",
            "scenario_name = File.basename(scenario_csv, File.extname(scenario_csv)).downcase",
            "run_dir = File.join(File.dirname(feature_file), 'run', scenario_name)",
            "runner = URBANopt::RNM::Runner.new(scenario_name, run_dir, scenario_csv, feature_file, reopt: false, opendss_catalog: true)",
            "runner.create_simulation_files",
            "runner.run(true)",
            "runner.post_process",
        ]
    )
    _run_bundle_ruby(
        project_dir=project_dir,
        runtime=runtime,
        script=script,
        args=[str(scenario_csv), str(feature_geojson)],
        log_name="run_rnm_localhost",
    )


def _run_bundle_ruby(
    *,
    project_dir: Path,
    runtime: dict[str, Any] | None,
    script: str,
    args: list[str],
    log_name: str,
) -> None:
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    if gemfile is None or not gemfile.is_file():
        raise RuntimeError("URBANopt CLI bundle Gemfile is unavailable.")
    command = [_bundle_executable(runtime), "exec", "ruby", "-e", script, *args]
    with urbanopt_runtime_env(runtime):
        env = os.environ.copy()
        env["PYTHONHOME"] = ""
        env.update(_offline_bundler_env(runtime, gemfile))
        env.pop("BUNDLE_PATH", None)
        env.pop("BUNDLE_FROZEN", None)
        _sanitize_remote_service_env(env)
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


def _offline_bundler_env(runtime: dict[str, Any] | None, gemfile: Path) -> dict[str, str]:
    env = {
        "BUNDLE_GEMFILE": str(gemfile),
        "BUNDLE_RETRY": "0",
        "BUNDLE_DISABLE_VERSION_CHECK": "true",
    }
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    if bundle_path is not None:
        runtime_file = (runtime or {}).get("openstudio_runtime_gemfile", {}).get("path")
        if runtime_file:
            env["UO_BUNDLE_INSTALL_PATH"] = str(Path(runtime_file).parent)
    return env


def _sanitize_remote_service_env(env: dict[str, str]) -> None:
    for key in list(env):
        if key.upper() in REMOTE_SERVICE_ENV_KEYS:
            env.pop(key, None)


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
        fallback = bundle_path / "gems" / f"urbanopt-cli-{REQUIRED_RUNTIME_VERSIONS['urbanopt']}" / "example_files" / "reopt" / "multiPV_assumptions.json"
        if fallback.is_file():
            return fallback
    return None


def _opendss_python_config(runtime: dict[str, Any] | None) -> Path | None:
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    if bundle_path is None:
        return None
    example_root = bundle_path / "gems"
    for candidate in sorted(example_root.glob("urbanopt-cli-*/example_files/python_deps/python_config.json")):
        if candidate.is_file():
            return candidate
    fallback = bundle_path / "gems" / f"urbanopt-cli-{REQUIRED_RUNTIME_VERSIONS['urbanopt']}" / "example_files" / "python_deps" / "python_config.json"
    if fallback.is_file():
        return fallback
    return None


def _normalize_reopt_assumptions(assumptions: dict[str, Any]) -> dict[str, Any]:
    """Return an URBANopt REopt-compatible assumptions dictionary."""
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
