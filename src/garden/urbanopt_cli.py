"""MCP-local URBANopt CLI adapter for the required bundled runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from dragonfly_energy.config import folders as dragonfly_energy_folders
from dragonfly_energy.reopt import REoptParameter

from garden.ladybug_tools_config import (
    REQUIRED_RUNTIME_VERSIONS,
    get_ladybug_tools_config,
    iter_urbanopt_sdk_output_paths,
    urbanopt_cli_gem_bundle_path,
    urbanopt_cli_runtime_gemfile_path,
    urbanopt_runtime_env,
)
from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from ladybug_tools_mcp.contracts import make_report

CONFIG_NEXT_TOOL = "LB_Get_Runtime_Config"
DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY = {
    "mode": "local_runtime_required",
    "full_network_isolation_required": False,
    "online_install_allowed": False,
    "online_api_allowed": False,
    "local_bundle_required": True,
}
URBANOPT_STANDARD_OUTPUT_NAMES = {
    "in.osm",
    "in.idf",
    "eplusout.sql",
    "epluszsz.csv",
    "eplusout.rdd",
    "eplustbl.htm",
    "eplustbl.html",
    "eplusout.err",
    "finished.job",
    "failed.job",
}

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
    _run_bundle_command(
        project_dir=project_dir,
        runtime=runtime,
        exec_args=["uo", "run", "-f", str(feature_geojson), "-s", str(scenario_csv)],
        log_name="run_simulation",
        prepare_temp_dir=True,
    )


def run_urbanopt_default_report_with_cli_bundle(
    *,
    feature_geojson: str,
    scenario_csv: str,
    runtime: dict[str, Any] | None,
) -> tuple[Path, Path]:
    """Generate URBANopt default reports with the CLI bundle Gemfile."""
    project_dir = _check_project_files(feature_geojson, scenario_csv)
    _run_bundle_command(
        project_dir=project_dir,
        runtime=runtime,
        exec_args=["uo", "process", "--default", "-f", str(feature_geojson), "-s", str(scenario_csv)],
        log_name="run_default_report",
        prepare_temp_dir=True,
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
        _run_bundle_command(
            project_dir=project_dir,
            runtime=runtime,
            exec_args=["ruby", "-e", script, str(scenario_csv), str(feature_geojson)],
            log_name="run_rnm_localhost",
        )
    else:
        _run_bundle_command(
            project_dir=project_dir,
            runtime=runtime,
            exec_args=["uo", "rnm", "--feature", str(feature_geojson), "--scenario", str(scenario_csv)],
            log_name="run_rnm",
            prepare_temp_dir=True,
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
    _run_bundle_command(
        project_dir=project_dir,
        runtime=runtime,
        exec_args=[
            "uo",
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
        prepare_temp_dir=True,
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
    args = ["uo", "opendss", "--scenario", str(scenario_csv), "--feature", str(feature_geojson)]
    if _opendss_rnm_results_path(project_dir, Path(scenario_csv)).is_file():
        args.append("--rnm")
    elif (project_dir / "electrical_database.json").is_file():
        args.extend(["--equipment", str(project_dir / "electrical_database.json")])
    if autosize:
        args.append("--upgrade")
    _run_bundle_command(
        project_dir=project_dir,
        runtime=runtime,
        exec_args=args,
        log_name="run_opendss",
        apply_opendss_shim=True,
        prepare_temp_dir=True,
    )
    return project_dir


def _opendss_rnm_results_path(project_dir: Path, scenario_csv: Path) -> Path:
    scenario_name = scenario_csv.stem
    scenario_path = project_dir / "run" / scenario_name / "rnm-us" / "results" / "GeoJSON" / "Distribution_system.json"
    if scenario_path.is_file() or scenario_name == "honeybee_scenario":
        return scenario_path
    return project_dir / "run" / "honeybee_scenario" / "rnm-us" / "results" / "GeoJSON" / "Distribution_system.json"


def has_urbanopt_cli_bundle(runtime: dict[str, Any] | None) -> bool:
    """Return True when a runtime includes an existing CLI Gemfile."""
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    return bool(gemfile and gemfile.is_file())


def has_urbanopt_opendss_python_deps(runtime: dict[str, Any] | None) -> bool:
    """Return True when URBANopt CLI OpenDSS Python deps are initialized."""
    deps = runtime.get("opendss_python_deps") if isinstance(runtime, dict) else None
    if isinstance(deps, dict):
        pack = deps.get("offline_runtime_pack")
        if isinstance(pack, dict):
            return deps.get("initialized") is True and pack.get("ready") is True
        if deps.get("initialized") is True:
            return _opendss_python_config_ready(_opendss_python_config(runtime))
    return _opendss_python_config_ready(_opendss_python_config(runtime))


def _opendss_python_config_ready(config: Path | None) -> bool:
    if config is None or not config.is_file():
        return False
    try:
        loaded = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(loaded, dict) and all(
        isinstance(loaded.get(k), str) and Path(loaded[k]).is_file()
        for k in ("python_path", "pip_path", "ditto_path")
    )


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
    command = [
        sys.executable,
        "-m",
        "dragonfly_energy",
        "translate",
        "hb-models-to-osm",
        str(hb_json_dir),
        "--output-folder",
        str(project_dir / "osm"),
    ]
    sim_par_json = project_dir / "simulation_parameter.json"
    if sim_par_json.is_file():
        command.extend(["--sim-par-json", str(sim_par_json)])
    workflow_osw = project_dir / "mappers" / "honeybee_workflow.osw"
    if workflow_osw.is_file():
        weather_file = json.loads(workflow_osw.read_text(encoding="utf-8")).get("weather_file")
        if isinstance(weather_file, str) and weather_file:
            command.extend(["--epw-file", weather_file])
    runner_conf = project_dir / "runner.conf"
    if runner_conf.is_file():
        runner_cpu = json.loads(runner_conf.read_text(encoding="utf-8")).get("num_parallel")
        if isinstance(runner_cpu, int):
            cpu_count = runner_cpu
    if cpu_count is not None:
        command.extend(["--cpu-count", str(cpu_count)])
    env = os.environ.copy()
    env["PYTHONHOME"] = ""
    temp_dir = project_dir / "tmp"
    temp_dir.mkdir(exist_ok=True)
    env.update(TEMP=str(temp_dir), TMP=str(temp_dir))
    completed = subprocess.run(command, cwd=str(project_dir), env=env, capture_output=True, text=True)
    _write_process_log(project_dir, "translate_hbjson_to_osm", command, completed)
    if completed.returncode != 0:
        raise RuntimeError(_process_error("Failed to translate HBJSON files to OSM.", completed))


def _run_bundle_command(
    *,
    project_dir: Path,
    runtime: dict[str, Any] | None,
    exec_args: list[str],
    log_name: str,
    env_extra: dict[str, str | None] | None = None,
    use_reopt_localhost_adapter: bool = False,
    apply_opendss_shim: bool = False,
    prepare_temp_dir: bool = False,
) -> None:
    gemfile = urbanopt_cli_runtime_gemfile_path(runtime)
    if gemfile is None or not gemfile.is_file():
        raise RuntimeError("URBANopt CLI bundle Gemfile is unavailable.")
    command = [_bundle_executable(runtime), "exec", *exec_args]
    with urbanopt_runtime_env(runtime):
        env = os.environ.copy()
        env["PYTHONHOME"] = ""
        if prepare_temp_dir:
            temp_dir = project_dir / "tmp"
            temp_dir.mkdir(exist_ok=True)
            env.update(TEMP=str(temp_dir), TMP=str(temp_dir))
        env.update(
            {
                "BUNDLE_GEMFILE": str(gemfile),
                "BUNDLE_RETRY": "0",
                "BUNDLE_DISABLE_VERSION_CHECK": "true",
            }
        )
        if urbanopt_cli_gem_bundle_path(runtime) is not None:
            runtime_file = (runtime or {}).get("openstudio_runtime_gemfile", {}).get("path")
            if runtime_file:
                env["UO_BUNDLE_INSTALL_PATH"] = str(Path(runtime_file).parent)
        env.pop("BUNDLE_PATH", None)
        env.pop("BUNDLE_FROZEN", None)
        if apply_opendss_shim:
            _apply_urbanopt_python_deps_shim(env=env, project_dir=project_dir, runtime=runtime)
        if use_reopt_localhost_adapter:
            _apply_reopt_localhost_patch(env=env, project_dir=project_dir)
        if env_extra:
            for key, value in env_extra.items():
                if value is not None:
                    env[key] = value
        for key in list(env):
            if key.upper() in REMOTE_SERVICE_ENV_KEYS:
                env.pop(key, None)
        completed = subprocess.run(command, cwd=str(project_dir), env=env, capture_output=True, text=True)
    _write_process_log(project_dir, log_name, command, completed)
    if completed.returncode != 0:
        raise RuntimeError(_process_error(f"URBANopt CLI command failed: {log_name}.", completed))


def _apply_reopt_localhost_patch(*, env: dict[str, str], project_dir: Path) -> None:
    patch_dir = project_dir / ".mcp_urbanopt_reopt"
    patch_dir.mkdir(parents=True, exist_ok=True)
    (patch_dir / "mcp_reopt_localhost_patch.rb").write_text(
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
    env["RUBYLIB"] = f"{patch_dir}{os.pathsep}{env['RUBYLIB']}" if env.get("RUBYLIB") else str(patch_dir)
    env["RUBYOPT"] = f"-rmcp_reopt_localhost_patch {env['RUBYOPT']}" if env.get("RUBYOPT") else "-rmcp_reopt_localhost_patch"


def _apply_urbanopt_python_deps_shim(*, env: dict[str, str], project_dir: Path, runtime: dict[str, Any] | None) -> None:
    deps = runtime.get("opendss_python_deps") if isinstance(runtime, dict) else None
    if not isinstance(deps, dict):
        return
    pack = deps.get("offline_runtime_pack")
    if not isinstance(pack, dict) or pack.get("source") != "explicit_python_config":
        return
    cfg_path_val = (pack.get("python_config") or {}).get("path")
    python_config = Path(cfg_path_val) if isinstance(cfg_path_val, str) and cfg_path_val else None
    if python_config is None or not python_config.is_file():
        return
    shim_dir = project_dir / ".mcp_urbanopt_python_deps" / "example_files" / "python_deps"
    shim_dir.mkdir(parents=True, exist_ok=True)
    (shim_dir / "python_config.json").write_text(python_config.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    deps_file_val = (deps.get("dependencies_file") or {}).get("path")
    if isinstance(deps_file_val, str) and Path(deps_file_val).is_file():
        (shim_dir / "dependencies.json").write_text(Path(deps_file_val).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    example_files = str(shim_dir.parent)
    env["RUBYLIB"] = f"{example_files}{os.pathsep}{env['RUBYLIB']}" if env.get("RUBYLIB") else example_files


def _find_bundle_example_file(runtime: dict[str, Any] | None, rel_glob: str, rel_fallback: str) -> Path | None:
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    if bundle_path is None:
        return None
    example_root = bundle_path / "gems"
    for candidate in sorted(example_root.glob(rel_glob)):
        if candidate.is_file():
            return candidate
    fallback = example_root / f"urbanopt-cli-{REQUIRED_RUNTIME_VERSIONS['urbanopt']}" / rel_fallback
    return fallback if fallback.is_file() else None


def _opendss_python_config(runtime: dict[str, Any] | None) -> Path | None:
    return _find_bundle_example_file(
        runtime,
        "urbanopt-cli-*/example_files/python_deps/python_config.json",
        "example_files/python_deps/python_config.json",
    )


def _update_rnm_inputs(*, feature_geojson: Path, underground_ratio: float, lv_only: bool, nodes_per_building: int) -> None:
    geo_dict = json.loads(feature_geojson.read_text(encoding="utf-8"))
    project = geo_dict.setdefault("project", {})
    project["underground_cables_ratio"] = underground_ratio
    project["only_lv_consumers"] = lv_only
    project["max_number_of_lv_nodes_per_building"] = nodes_per_building
    feature_geojson.write_text(json.dumps(geo_dict, indent=4), encoding="utf-8", newline="\n")


def _write_reopt_assumptions_file(*, project_dir: Path, runtime: dict[str, Any] | None, urdb_label: str) -> Path:
    template = _find_bundle_example_file(
        runtime,
        "urbanopt-cli-*/example_files/reopt/multiPV_assumptions.json",
        "example_files/reopt/multiPV_assumptions.json",
    )
    if template is not None:
        assumptions = json.loads(template.read_text(encoding="utf-8"))
    else:
        assumptions_path = getattr(dragonfly_energy_folders, "reopt_assumptions_path", None)
        if not assumptions_path:
            raise RuntimeError("No REopt assumptions template is configured in dragonfly_energy.")
        parameters = REoptParameter()
        parameters.pv_parameter.max_kw = 1000000000
        parameters.storage_parameter.max_kw = 1000000
        parameters.generator_parameter.max_kw = 1000000000
        assumptions = parameters.to_assumptions_dict(assumptions_path, urdb_label)

    if isinstance(assumptions.get("Scenario"), dict) and isinstance(assumptions["Scenario"].get("Site"), dict):
        scenario = assumptions["Scenario"]
        assumptions = dict(scenario["Site"])
        if "time_steps_per_hour" in scenario:
            settings = assumptions.setdefault("Settings", {})
            if isinstance(settings, dict):
                settings.setdefault("time_steps_per_hour", scenario["time_steps_per_hour"])
    if "Storage" in assumptions and "ElectricStorage" not in assumptions:
        assumptions["ElectricStorage"] = assumptions.pop("Storage")

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

    reopt_folder = project_dir / "reopt"
    reopt_folder.mkdir(exist_ok=True)
    assumptions_file = reopt_folder / "reopt_assumptions.json"
    assumptions_file.write_text(json.dumps(assumptions, indent=4), encoding="utf-8", newline="\n")
    return assumptions_file


def _bundle_executable(runtime: dict[str, Any] | None) -> str:
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    executable_name = "bundle.bat" if os.name == "nt" else "bundle"
    if bundle_path is not None:
        candidate = bundle_path / "bin" / executable_name
        if candidate.is_file():
            return str(candidate)
    return executable_name


def _write_process_log(project_dir: Path, name: str, command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
    payload = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    (project_dir / f"mcp_urbanopt_{name}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _process_error(message: str, completed: subprocess.CompletedProcess[str]) -> str:
    parts = [message, f"returncode={completed.returncode}"]
    if (stdout := (completed.stdout or "").strip()):
        parts.append(f"stdout={stdout[-2000:]}")
    if (stderr := (completed.stderr or "").strip()):
        parts.append(f"stderr={stderr[-2000:]}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Shared preflight, runtime diagnostics, and URBANopt output discovery helpers
# ---------------------------------------------------------------------------


def urbanopt_engine_config() -> dict[str, Any]:
    """Return the URBANopt engine dictionary from the cached config diagnostic."""
    try:
        config = get_ladybug_tools_config()
    except Exception:
        return {}
    engines = config.get("summary_view", {}).get("engines", {})
    urbanopt = engines.get("urbanopt") if isinstance(engines, dict) else None
    return urbanopt if isinstance(urbanopt, dict) else {}


def blocked_preflight(
    issues: list[str],
    *,
    missing: list[str],
    runtime: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
    recommended_next_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Build a standard runtime preflight blocked payload."""
    result: dict[str, Any] = {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": issues,
        "missing": sorted(set(missing)),
        "recommended_next_tools": list(recommended_next_tools or [CONFIG_NEXT_TOOL]),
    }
    if runtime is not None:
        result["runtime"] = runtime
    if diagnostics:
        result["runtime_diagnostics"] = diagnostics
    elif isinstance(runtime, dict):
        policy = runtime.get("network_policy")
        result["runtime_diagnostics"] = {
            "network_policy": dict(policy) if isinstance(policy, dict) else dict(DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY),
            "urbanopt": runtime,
        }
    return result


def preflight_urbanopt_runtime(*, network_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check whether URBANopt CLI and its local runtime bundle are ready."""
    urbanopt = urbanopt_engine_config()
    issues: list[str] = []
    if not urbanopt.get("available"):
        issues.append("URBANopt CLI or Gemfile is not available to dragonfly_energy.")
    if not has_urbanopt_cli_bundle(urbanopt):
        issues.append(
            f"A local URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle Gemfile is required."
        )
    if urbanopt.get("version_status") in {"older", "newer", "unknown"}:
        issues.append("URBANopt runtime version does not match the required version.")
    if issues:
        policy = urbanopt.get("network_policy")
        resolved_policy = (
            dict(policy)
            if isinstance(policy, dict)
            else dict(network_policy or DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY)
        )
        return blocked_preflight(
            issues,
            missing=["urbanopt"],
            runtime=urbanopt,
            diagnostics={"network_policy": resolved_policy, "urbanopt": urbanopt},
        )
    return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": urbanopt}


def prime_urbanopt_sdk_version_cache(preflight: dict[str, Any] | None) -> None:
    """Populate dragonfly_energy's cached CLI version tuple from preflight."""
    runtime = preflight.get("runtime") if isinstance(preflight, dict) else None
    if not isinstance(runtime, dict):
        return
    version = runtime.get("version") or runtime.get("detected_version")
    if not isinstance(version, str) or not version.strip():
        return
    parts = version.strip().split(".")
    if not all(part.isdigit() for part in parts):
        return
    parsed = tuple(int(part) for part in parts)
    dragonfly_energy_folders._urbanopt_version = parsed
    dragonfly_energy_folders._urbanopt_version_str = ".".join(str(part) for part in parsed)


def attach_runtime_diagnostics(
    summary_view: dict[str, Any],
    report_details: dict[str, Any],
    preflight: dict[str, Any] | None,
) -> None:
    """Mirror existing preflight runtime_diagnostics into summary and report."""
    if not isinstance(preflight, dict):
        return
    diagnostics = preflight.get("runtime_diagnostics")
    if not isinstance(diagnostics, dict) or not diagnostics:
        runtime = preflight.get("runtime")
        if not isinstance(runtime, dict):
            return
        policy = runtime.get("network_policy")
        diagnostics = {
            "network_policy": dict(policy) if isinstance(policy, dict) else dict(DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY),
            "urbanopt": runtime,
        }
    if diagnostics:
        summary_view["runtime_diagnostics"] = diagnostics
        report_details["runtime_diagnostics"] = diagnostics


def operation_blocked_result(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    operation: str,
    preflight: dict[str, Any],
    label: str = "URBANopt Energy",
) -> dict[str, Any]:
    """Build a consistent blocked-by-runtime operation response."""
    recommended = list(preflight.get("recommended_next_tools") or [CONFIG_NEXT_TOOL])
    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "operation": operation,
        "runtime_status": "blocked",
        "preflight": preflight,
        "recommended_next_tools": recommended,
    }
    report_details: dict[str, Any] = {
        "garden_root": str(garden_root),
        "recommended_next_tools": recommended,
        "preflight": preflight,
    }
    attach_runtime_diagnostics(summary_view, report_details, preflight)
    return {
        "runtime_status": "blocked",
        "summary_view": summary_view,
        "report": make_report(
            status="warning",
            message=f"{label} operation blocked by missing runtime: {operation}",
            warnings=list(preflight.get("issues") or []),
            details=report_details,
        ),
    }


def output_for_path(
    garden_root: Path,
    path: Path,
    *,
    name: str | None = None,
    include_is_directory: bool = True,
    include_kind: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Garden-relative output entry for run ledgers."""
    output: dict[str, Any] = {
        "name": name or path.name,
        "path": to_posix_relative(path, garden_root),
        "exists": path.exists(),
    }
    if include_is_directory:
        output["is_directory"] = path.is_dir()
    if include_kind:
        suffix = path.suffix.lower().lstrip(".")
        output["kind"] = suffix or ("folder" if path.is_dir() else "file")
    if extra:
        output.update(extra)
    return output


def outputs_from_sdk_result(
    garden_root: Path,
    value: Any,
    *,
    include_is_directory: bool = True,
    include_kind: bool = True,
    expand_dirs: bool = False,
) -> list[dict[str, Any]]:
    """Collect Garden-relative outputs from an SDK run return value."""
    outputs: list[dict[str, Any]] = []
    for output_type, path_value in iter_urbanopt_sdk_output_paths(value):
        path_obj = Path(path_value).expanduser().resolve()
        if expand_dirs and path_obj.is_dir():
            for item in sorted(p for p in path_obj.rglob("*") if p.is_file()):
                if item.name != "background_request.json":
                    outputs.append(
                        output_for_path(
                            garden_root,
                            item,
                            include_is_directory=include_is_directory,
                            include_kind=include_kind,
                        )
                    )
            continue
        if expand_dirs and not path_obj.exists():
            continue
        name = (
            f"{output_type}:{path_obj.name}"
            if output_type
            else (f"{path_obj.suffix.lower().lstrip('.') or 'file'}:{path_obj.name}" if expand_dirs else None)
        )
        outputs.append(
            output_for_path(
                garden_root,
                path_obj,
                name=name,
                include_is_directory=include_is_directory,
                include_kind=include_kind,
            )
        )
    return outputs


def discover_urbanopt_outputs(
    garden_root: Path,
    root: Path,
    *,
    include_kind: bool = True,
) -> list[dict[str, Any]]:
    """Scan a project folder for standard EnergyPlus/URBANopt simulation outputs."""
    if not root.is_dir():
        return []
    outputs = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "background_request.json":
            continue
        if path.name.lower() not in URBANOPT_STANDARD_OUTPUT_NAMES:
            continue
        outputs.append(
            output_for_path(
                garden_root,
                path,
                include_is_directory=True,
                include_kind=include_kind,
            )
        )
    return outputs


def failed_urbanopt_job_error(garden_root: Path, root: Path) -> str | None:
    """Return a diagnostic message when any ``failed.job`` marker exists."""
    if not root.is_dir():
        return None
    failed_jobs = sorted(root.rglob("failed.job"))
    if not failed_jobs:
        return None
    markers = ", ".join(to_posix_relative(path, garden_root) for path in failed_jobs[:5])
    if len(failed_jobs) > 5:
        markers += f", ... ({len(failed_jobs)} total)"
    return f"URBANopt run wrote failed.job marker(s): {markers}"
