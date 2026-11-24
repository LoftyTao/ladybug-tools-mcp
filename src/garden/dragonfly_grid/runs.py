"""Garden-managed Dragonfly Electric Grid run ledgers."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import time
import traceback
from typing import Any

from dragonfly_energy.run import run_default_report as sdk_run_default_report
from dragonfly_energy.run import run_reopt as sdk_run_reopt
from dragonfly_energy.run import run_rnm as sdk_run_rnm

from garden.background import submit_worker_process

from garden.ladybug_tools_config import REQUIRED_RUNTIME_VERSIONS, urbanopt_runtime_env, write_urbanopt_bundle_config
from garden.manifest import GardenManifest, utc_now_iso, write_json_file
from garden.paths import require_garden_root, resolve_existing_garden_path, to_posix_relative
from garden.run_ledger import RunLedger, RunManager
from garden.urbanopt_cli import (
    CONFIG_NEXT_TOOL,
    DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY,
    blocked_preflight,
    has_urbanopt_cli_bundle,
    has_urbanopt_opendss_python_deps,
    output_for_path,
    outputs_from_sdk_result,
    run_urbanopt_default_report_with_cli_bundle,
    run_urbanopt_opendss_with_cli_bundle,
    run_urbanopt_reopt_with_cli_bundle,
    run_urbanopt_rnm_with_cli_bundle,
    urbanopt_engine_config,
)
from ladybug_tools_mcp.contracts import make_report

from .authoring import OPENDSS_RESULT_ARTIFACT_TYPE

GRID_RUN_TARGET_TYPE = "dragonfly_grid_run"
GRID_RUN_DOMAIN = "dragonfly_grid"
GRID_RUN_ROOT = Path("runs") / "dragonfly_grid"
GRID_RUN_RECIPES = {"rnm", "opendss", "reopt"}
LOCAL_GRID_RUNTIME_BLOCKER = (
    f"URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} is available for local-bundle Energy/OpenStudio execution, "
    "but this RNM/REopt path requires a compatible local service/runtime configuration "
    "rather than online API submission."
)
DEFAULT_GRID_NETWORK_POLICY = DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY
GRID_EXTERNAL_API_BLOCKERS = {
    "rnm": {
        "recipe": "rnm",
        "api_backed": True,
        "online_api_blocked": True,
        "online_api_endpoints": ["https://rnm.urbanopt.net/api/v2/"],
        "local_service_required": True,
        "local_service_configured": False,
        "required_local_runtime": "Compatible local RNM service/runtime configured and reachable.",
    },
    "reopt": {
        "recipe": "reopt",
        "api_backed": True,
        "online_api_blocked": True,
        "online_api_endpoints": ["https://developer.nrel.gov/api/reopt/v3/"],
        "local_service_required": True,
        "local_service_configured": False,
        "required_local_runtime": "Compatible local REopt API/service configured and reachable.",
    },
}

_GRID_RUNS = RunManager(
    domain=GRID_RUN_DOMAIN,
    target_type=GRID_RUN_TARGET_TYPE,
    runs_dir=GRID_RUN_ROOT,
    default_recipe="rnm",
    allowed_recipes=GRID_RUN_RECIPES,
    per_recipe_index=True,
    use_uuid_fallback=True,
    not_found_label="Dragonfly Grid",
    public_fields=(
        "run_id",
        "target",
        "recipe",
        "status",
        "runtime_status",
        "created_at",
        "started_at",
        "completed_at",
        "run_folder",
        "worker_pid",
        "feature_geojson_target",
        "scenario_csv_target",
        "preflight",
        "outputs",
        "error",
    ),
    ledger=RunLedger(lock="file", atomic=True, recover_trailing_json=True, empty_is_empty=True),
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _worker_environment(
    garden_root: Path,
    run_dir: Path,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    temp_dir = (garden_root / "tmp" / run_dir.name).resolve()
    temp_dir.relative_to(garden_root)
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    if extra:
        env.update(extra)
    return env


def _record_worker_pid(root: Path, recipe: str, run_id: str, proc: Any) -> None:
    worker_pid = getattr(proc, "pid", None)
    if worker_pid is None:
        return
    current = _GRID_RUNS.get(root, run_id, recipe=recipe)
    if current is not None and current.get("worker_pid") is None:
        current["worker_pid"] = worker_pid
        _GRID_RUNS.upsert(root, current, recipe=recipe)


def poll_grid_run(
    *,
    garden_root: str,
    recipe: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one Dragonfly Electric Grid run ledger record."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_id = _GRID_RUNS.resolve_run_id(run_target, run_id, recipe=recipe)
    record = _GRID_RUNS.require(root, resolved_id, recipe=recipe)
    return _result_from_record(root, manifest, record)


def _wait_for_grid_run(
    garden_root: str,
    recipe: str,
    result: dict[str, Any],
    wait_seconds: float | None,
    poll_interval: float,
) -> dict[str, Any]:
    requested_wait = max(float(wait_seconds or 0), 0.0)
    if not requested_wait:
        return result
    applied_wait = min(requested_wait, 240.0)
    interval = max(float(poll_interval or 2.0), 0.2)
    deadline = time.monotonic() + applied_wait
    while result.get("runtime_status") in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
        result = poll_grid_run(
            garden_root=garden_root,
            recipe=recipe,
            run_target=result.get("run_target"),
        )
    summary_view = result.setdefault("summary_view", {})
    summary_view["wait_seconds_requested"] = wait_seconds
    summary_view["wait_seconds_applied"] = applied_wait
    return result


def start_rnm(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    underground_ratio: float = 0.9,
    lv_only: bool = True,
    nodes_per_building: int = 1,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start or block an RNM post-processing run."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    runtime = urbanopt_engine_config() or None
    normalized_run_id = _GRID_RUNS.normalize_run_id(run_id, prefix="rnm")
    use_localhost = _grid_local_service_ready("rnm", runtime)
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="rnm",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={
            "operation": "run_rnm",
            "underground_ratio": underground_ratio,
            "lv_only": lv_only,
            "nodes_per_building": nodes_per_building,
            "use_localhost": use_localhost,
        },
        preflight=_preflight_rnm_runtime(runtime),
    )
    if record["status"] == "running":
        run_dir = _GRID_RUNS.run_dir(root, normalized_run_id, recipe="rnm")
        try:
            proc = submit_worker_process(
                garden_root=root,
                run_dir=run_dir,
                worker_module="garden.dragonfly_grid.runs:_run_rnm_job",
                request=_json_safe(
                    {
                        "garden_root": str(root),
                        "run_id": normalized_run_id,
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "runtime": runtime,
                        "underground_ratio": underground_ratio,
                        "lv_only": lv_only,
                        "nodes_per_building": nodes_per_building,
                        "use_localhost": use_localhost,
                    }
                ),
                cwd=root,
                environment=_worker_environment(root, run_dir),
            )
            _record_worker_pid(root, "rnm", normalized_run_id, proc)
        except Exception as exc:
            _complete_with_error(root, "rnm", normalized_run_id, str(exc))
    latest = _GRID_RUNS.get(root, normalized_run_id, recipe="rnm") or record
    result = _result_from_record(root, manifest, latest)
    return _wait_for_grid_run(garden_root, "rnm", result, wait_seconds, poll_interval)


def start_opendss(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    autosize: bool = False,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start or block an OpenDSS simulation run."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    runtime = urbanopt_engine_config() or None
    normalized_run_id = _GRID_RUNS.normalize_run_id(run_id, prefix="opendss")
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="opendss",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={"operation": "run_opendss", "autosize": autosize},
        preflight=_preflight_opendss_runtime(runtime),
    )
    if record["status"] == "running":
        run_dir = _GRID_RUNS.run_dir(root, normalized_run_id, recipe="opendss")
        try:
            proc = submit_worker_process(
                garden_root=root,
                run_dir=run_dir,
                worker_module="garden.dragonfly_grid.runs:_run_opendss_job",
                request=_json_safe(
                    {
                        "garden_root": str(root),
                        "run_id": normalized_run_id,
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "runtime": runtime,
                        "autosize": autosize,
                    }
                ),
                cwd=root,
                environment=_worker_environment(root, run_dir),
            )
            _record_worker_pid(root, "opendss", normalized_run_id, proc)
        except Exception as exc:
            _complete_with_error(root, "opendss", normalized_run_id, str(exc))
    latest = _GRID_RUNS.get(root, normalized_run_id, recipe="opendss") or record
    result = _result_from_record(root, manifest, latest)
    return _wait_for_grid_run(garden_root, "opendss", result, wait_seconds, poll_interval)


def start_reopt(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    urdb_label: str,
    financial_parameters_target: dict[str, Any] | None = None,
    financial_parameters: dict[str, Any] | None = None,
    reopt_parameter_target: dict[str, Any] | None = None,
    reopt_parameter: dict[str, Any] | None = None,
    run_id: str | None = None,
    developer_key: str | None = None,
    wait_seconds: float | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Start or block a REopt post-processing run with financial and DER parameter support."""
    from garden.dragonfly_grid.authoring import _object_to_dict, load_grid_object

    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")

    resolved_fp: dict[str, Any] | None = None
    if financial_parameters_target is not None:
        fp_obj = load_grid_object(
            garden_root=root,
            target=financial_parameters_target,
            expected_kind="financial_parameters",
        )
        resolved_fp = _object_to_dict(fp_obj)
    elif isinstance(financial_parameters, dict):
        resolved_fp = dict(financial_parameters)

    resolved_reopt: dict[str, Any] | None = None
    if reopt_parameter_target is not None:
        rp_obj = load_grid_object(
            garden_root=root,
            target=reopt_parameter_target,
            expected_kind="reopt_parameter",
        )
        resolved_reopt = _object_to_dict(rp_obj)
    elif isinstance(reopt_parameter, dict):
        resolved_reopt = dict(reopt_parameter)

    runtime = urbanopt_engine_config() or None
    normalized_run_id = _GRID_RUNS.normalize_run_id(run_id, prefix="reopt")
    use_localhost = _grid_local_service_ready("reopt", runtime)
    record = _start_record(
        garden_root=root,
        manifest=manifest,
        recipe="reopt",
        run_id=normalized_run_id,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        request={
            "operation": "run_reopt",
            "urdb_label": urdb_label,
            "use_localhost": use_localhost,
            "has_financial_parameters": resolved_fp is not None,
            "has_reopt_parameter": resolved_reopt is not None,
        },
        preflight=_preflight_reopt_runtime(runtime),
    )
    if record["status"] == "running":
        run_dir = _GRID_RUNS.run_dir(root, normalized_run_id, recipe="reopt")
        extra_env = (
            {"LBT_MCP_REOPT_DEVELOPER_KEY": developer_key}
            if developer_key
            else None
        )
        try:
            proc = submit_worker_process(
                garden_root=root,
                run_dir=run_dir,
                worker_module="garden.dragonfly_grid.runs:_run_reopt_job",
                request=_json_safe(
                    {
                        "garden_root": str(root),
                        "run_id": normalized_run_id,
                        "feature_geojson": str(feature_geojson),
                        "scenario_csv": str(scenario_csv),
                        "runtime": runtime,
                        "urdb_label": urdb_label,
                        "use_localhost": use_localhost,
                        "financial_parameter": resolved_fp,
                        "reopt_parameter": resolved_reopt,
                    }
                ),
                cwd=root,
                environment=_worker_environment(root, run_dir, extra=extra_env),
            )
            _record_worker_pid(root, "reopt", normalized_run_id, proc)
        except Exception as exc:
            _complete_with_error(root, "reopt", normalized_run_id, str(exc))
    latest = _GRID_RUNS.get(root, normalized_run_id, recipe="reopt") or record
    result = _result_from_record(root, manifest, latest)
    return _wait_for_grid_run(garden_root, "reopt", result, wait_seconds, poll_interval)


def _resolve_artifact(root: Path, manifest: GardenManifest, target: dict[str, Any], *, suffix: str) -> Path:
    if not isinstance(target, dict):
        raise ValueError("artifact target must be a dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("target must have target_type 'artifact'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("artifact target belongs to a different Garden.")
    path = target.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("artifact target requires a Garden-relative path.")
    return resolve_existing_garden_path(root, path, kind="file", suffix=suffix, label="artifact target")


def _urbanopt_runtime_ready(runtime: dict[str, Any] | None) -> bool:
    if shutil.which("uo"):
        return True
    if not isinstance(runtime, dict):
        return False
    engines = runtime.get("engines")
    if isinstance(engines, dict):
        urbanopt = engines.get("urbanopt")
        if isinstance(urbanopt, dict) and urbanopt.get("status") == "available":
            return True
    if runtime.get("available") is True or runtime.get("status") == "available":
        return True
    bundle = runtime.get("cli_gem_bundle")
    return isinstance(bundle, dict) and bundle.get("status") == "available"


def _ready_preflight(diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "runtime_status": "ready",
        "issues": [],
        "missing": [],
        "recommended_next_tools": [],
        "runtime_diagnostics": diagnostics,
    }


def _preflight_rnm_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = (urbanopt_engine_config() or None) if runtime is None else runtime
    diagnostics = _grid_external_api_diagnostics("rnm", runtime)
    if _grid_local_service_ready("rnm", runtime):
        return _ready_preflight(diagnostics)
    message = LOCAL_GRID_RUNTIME_BLOCKER if _urbanopt_runtime_ready(runtime) else "URBANopt/RNM runtime is not available."
    return blocked_preflight([message], missing=["rnm"], diagnostics=diagnostics)


def _preflight_opendss_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = (urbanopt_engine_config() or None) if runtime is None else runtime
    deps = _opendss_python_deps(runtime)
    diagnostics = {"opendss_python_deps": deps} if deps else {}
    if not has_urbanopt_cli_bundle(runtime):
        return blocked_preflight(
            [f"URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle is required for local OpenDSS execution."],
            missing=["opendss"],
            diagnostics=diagnostics,
        )
    if not has_urbanopt_opendss_python_deps(runtime):
        return blocked_preflight(
            [
                f"URBANopt CLI OpenDSS Python dependencies are not initialized in the local {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle. "
                "Missing python_config.json under example_files/python_deps; provide an initialized local runtime pack. "
                "MCP local-bundle runtime validation will not run uo install_python or download dependencies."
            ],
            missing=["opendss"],
            diagnostics=diagnostics,
        )
    return _ready_preflight(diagnostics)


def _preflight_reopt_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = (urbanopt_engine_config() or None) if runtime is None else runtime
    diagnostics = _grid_external_api_diagnostics("reopt", runtime)
    if _grid_local_service_ready("reopt", runtime) and has_urbanopt_cli_bundle(runtime):
        return _ready_preflight(diagnostics)
    message = LOCAL_GRID_RUNTIME_BLOCKER if _urbanopt_runtime_ready(runtime) else "URBANopt/REopt runtime is not available."
    return blocked_preflight([message], missing=["reopt"], diagnostics=diagnostics)


def _grid_external_api_diagnostics(recipe: str, runtime: dict[str, Any] | None) -> dict[str, Any]:
    blocker = dict(GRID_EXTERNAL_API_BLOCKERS[recipe])
    local_service = _grid_local_service_config(recipe, runtime)
    blocker["local_service_configured"] = bool(local_service.get("configured"))
    blocker["local_service_ready"] = bool(local_service.get("ready"))
    blocker["mcp_localhost_adapter_ready"] = bool(local_service.get("mcp_adapter_ready"))
    return {
        "network_policy": _grid_network_policy(runtime),
        "local_service": local_service,
        "external_api_blocker": blocker,
    }


def _grid_local_service_ready(recipe: str, runtime: dict[str, Any] | None) -> bool:
    local_service = _grid_local_service_config(recipe, runtime)
    return bool(local_service.get("ready")) and bool(local_service.get("mcp_adapter_ready"))


def _grid_local_service_config(recipe: str, runtime: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(runtime, dict):
        service = runtime.get(f"{recipe}_service")
        if isinstance(service, dict):
            return service
        engines = runtime.get("engines")
        if isinstance(engines, dict):
            urbanopt = engines.get("urbanopt")
            if isinstance(urbanopt, dict) and isinstance(urbanopt.get(f"{recipe}_service"), dict):
                return urbanopt[f"{recipe}_service"]
    return {
        "recipe": recipe,
        "local_service_required": True,
        "configured": False,
        "ready": False,
        "mcp_adapter_ready": False,
        "missing": ["local_service_configuration", "mcp_localhost_adapter"],
        "mcp_local_runtime_required": True,
        "online_api_blocked": True,
    }


def _grid_network_policy(runtime: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(runtime, dict):
        for candidate in (
            runtime.get("network_policy"),
            runtime.get("engines", {}).get("urbanopt", {}).get("network_policy")
            if isinstance(runtime.get("engines"), dict)
            else None,
        ):
            if isinstance(candidate, dict):
                return candidate
    return dict(DEFAULT_GRID_NETWORK_POLICY)


def _opendss_python_deps(runtime: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(runtime, dict):
        return {}
    if isinstance(runtime.get("opendss_python_deps"), dict):
        return runtime["opendss_python_deps"]
    engines = runtime.get("engines")
    if isinstance(engines, dict):
        urbanopt = engines.get("urbanopt")
        if isinstance(urbanopt, dict) and isinstance(urbanopt.get("opendss_python_deps"), dict):
            return urbanopt["opendss_python_deps"]
    return {}


def _start_record(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    recipe: str,
    run_id: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    request: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    target = _GRID_RUNS.make_target(manifest.garden_id, run_id, recipe=recipe)
    run_dir = _GRID_RUNS.run_dir(garden_root, run_id, recipe=recipe)
    status = "blocked" if preflight.get("runtime_status") == "blocked" else "running"
    if status == "blocked":
        write_json_file(
            run_dir / "background_request.json",
            {
                **request,
                "feature_geojson_target": feature_geojson_target,
                "scenario_csv_target": scenario_csv_target,
            },
            ensure_ascii=False,
        )
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": recipe,
        "status": status,
        "runtime_status": status,
        "created_at": utc_now_iso(),
        "started_at": None if status == "blocked" else utc_now_iso(),
        "completed_at": utc_now_iso() if status == "blocked" else None,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "preflight": preflight,
        "outputs": [],
        "error": "; ".join(preflight.get("issues", [])) if status == "blocked" else None,
    }
    _GRID_RUNS.upsert(garden_root, record, recipe=recipe)
    return record


def _complete_with_error(root: Path, recipe: str, run_id: str, message: str) -> None:
    record = _GRID_RUNS.get(root, run_id, recipe=recipe)
    if record is None:
        return
    if record.get("worker_pid") is None:
        record["worker_pid"] = os.getpid()
    record.update(_GRID_RUNS.failure_fields(message))
    _GRID_RUNS.upsert(root, record, recipe=recipe)


def _run_rnm_job(**kwargs: Any) -> None:
    root = Path(kwargs["garden_root"])
    run_id = kwargs["run_id"]
    feature_geojson = Path(kwargs["feature_geojson"])
    try:
        runtime = kwargs.get("runtime")
        write_urbanopt_bundle_config(feature_geojson.parent, runtime)
        if has_urbanopt_cli_bundle(runtime):
            run_urbanopt_default_report_with_cli_bundle(
                feature_geojson=str(feature_geojson),
                scenario_csv=kwargs["scenario_csv"],
                runtime=runtime,
            )
            outputs = run_urbanopt_rnm_with_cli_bundle(
                feature_geojson=str(feature_geojson),
                scenario_csv=kwargs["scenario_csv"],
                runtime=runtime,
                underground_ratio=kwargs["underground_ratio"],
                lv_only=kwargs["lv_only"],
                nodes_per_building=kwargs["nodes_per_building"],
                use_localhost=kwargs["use_localhost"],
            )
        else:
            with urbanopt_runtime_env(runtime):
                sdk_run_default_report(str(feature_geojson), kwargs["scenario_csv"])
                outputs = sdk_run_rnm(
                    str(feature_geojson),
                    kwargs["scenario_csv"],
                    underground_ratio=kwargs["underground_ratio"],
                    lv_only=kwargs["lv_only"],
                    nodes_per_building=kwargs["nodes_per_building"],
                )
        _complete_success(root, "rnm", run_id, outputs, feature_geojson.parent)
    except Exception:  # pragma: no cover - external runtime diagnostics vary
        _complete_with_error(root, "rnm", run_id, traceback.format_exc())


def _run_reopt_job(**kwargs: Any) -> None:
    from garden.urbanopt_cli import _coerce_reopt_parameters

    root = Path(kwargs["garden_root"])
    run_id = kwargs["run_id"]
    feature_geojson = Path(kwargs["feature_geojson"])
    developer_key = kwargs.get("developer_key") or os.environ.get("LBT_MCP_REOPT_DEVELOPER_KEY")
    reopt_param_input = kwargs.get("reopt_parameter")
    financial_param_input = kwargs.get("financial_parameter")
    try:
        runtime = kwargs.get("runtime")
        write_urbanopt_bundle_config(feature_geojson.parent, runtime)
        if has_urbanopt_cli_bundle(runtime):
            run_urbanopt_default_report_with_cli_bundle(
                feature_geojson=str(feature_geojson),
                scenario_csv=kwargs["scenario_csv"],
                runtime=runtime,
            )
            outputs = run_urbanopt_reopt_with_cli_bundle(
                feature_geojson=str(feature_geojson),
                scenario_csv=kwargs["scenario_csv"],
                runtime=runtime,
                urdb_label=kwargs["urdb_label"],
                developer_key=developer_key,
                use_localhost=kwargs.get("use_localhost", False),
                reopt_parameter=reopt_param_input,
                financial_parameter=financial_param_input,
            )
        else:
            reopt_obj, has_custom = _coerce_reopt_parameters(
                reopt_param_input,
                financial_param_input,
            )
            with urbanopt_runtime_env(runtime):
                sdk_run_default_report(str(feature_geojson), kwargs["scenario_csv"])
                outputs = sdk_run_reopt(
                    str(feature_geojson),
                    kwargs["scenario_csv"],
                    kwargs["urdb_label"],
                    reopt_parameters=reopt_obj if has_custom else None,
                    developer_key=developer_key,
                )
        _complete_success(root, "reopt", run_id, outputs, feature_geojson.parent)
    except Exception:  # pragma: no cover - external runtime diagnostics vary
        _complete_with_error(root, "reopt", run_id, traceback.format_exc())


def _run_opendss_job(**kwargs: Any) -> None:
    root = Path(kwargs["garden_root"])
    run_id = kwargs["run_id"]
    feature_geojson = Path(kwargs["feature_geojson"])
    try:
        runtime = kwargs.get("runtime")
        write_urbanopt_bundle_config(feature_geojson.parent, runtime)
        outputs = run_urbanopt_opendss_with_cli_bundle(
            feature_geojson=str(feature_geojson),
            scenario_csv=kwargs["scenario_csv"],
            runtime=runtime,
            autosize=kwargs["autosize"],
        )
        _complete_success(root, "opendss", run_id, outputs, feature_geojson.parent)
    except Exception:  # pragma: no cover - external runtime diagnostics vary
        _complete_with_error(root, "opendss", run_id, traceback.format_exc())


def _complete_success(
    root: Path,
    recipe: str,
    run_id: str,
    sdk_outputs: Any = None,
    project_dir: Path | None = None,
) -> None:
    record = _GRID_RUNS.get(root, run_id, recipe=recipe)
    if record is None:
        return
    if record.get("worker_pid") is None:
        record["worker_pid"] = os.getpid()
    outputs = (
        []
        if recipe == "opendss"
        else outputs_from_sdk_result(root, sdk_outputs, include_is_directory=False, include_kind=True, expand_dirs=True)
    )
    if project_dir is not None:
        seen = {output["path"] for output in outputs}
        for output in _discover_project_outputs(root, project_dir, recipe):
            if output["path"] not in seen:
                outputs.append(output)
                seen.add(output["path"])
    if not outputs:
        record.update(
            {
                **_GRID_RUNS.failure_fields(
                    f"Dragonfly Grid {recipe} run finished without discoverable outputs."
                ),
                "outputs": [],
            }
        )
        _GRID_RUNS.upsert(root, record, recipe=recipe)
        return
    record.update(
        {
            "status": "completed",
            "runtime_status": "completed",
            "completed_at": utc_now_iso(),
            "outputs": outputs,
            "error": None,
        }
    )
    _GRID_RUNS.upsert(root, record, recipe=recipe)


def _discover_project_outputs(root: Path, project_dir: Path, recipe: str) -> list[dict[str, Any]]:
    project_dir = project_dir.expanduser().resolve()
    if recipe == "rnm":
        run_path = project_dir / "run"
        if not run_path.exists():
            return []
        outputs = []
        for item in sorted(p for p in run_path.rglob("*") if p.is_file()):
            rel = item.relative_to(project_dir).as_posix() if item.is_relative_to(project_dir) else item.as_posix()
            if "rnm-us/results" not in rel or item.name == "background_request.json":
                continue
            outputs.append(output_for_path(root, item, include_is_directory=False, include_kind=True))
        return outputs
    if recipe == "reopt":
        return [
            output_for_path(root, path, include_is_directory=False, include_kind=True)
            for path in sorted((project_dir / "run").rglob("scenario_optimization.*"))
            if path.is_file()
        ]
    if recipe == "opendss":
        manifest = GardenManifest.read(root)
        outputs = []
        for base in (project_dir / "opendss", project_dir / "run"):
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.csv")):
                if path.is_file():
                    outputs.append(
                        output_for_path(
                            root,
                            path,
                            include_is_directory=False,
                            include_kind=True,
                            extra={
                                "target_type": "artifact",
                                "domain": GRID_RUN_DOMAIN,
                                "garden_id": manifest.garden_id,
                                "artifact_type": OPENDSS_RESULT_ARTIFACT_TYPE,
                                "identifier": path.stem,
                            },
                        )
                    )
        return outputs
    return []


def _result_from_record(root: Path, manifest: GardenManifest, record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("runtime_status") or record.get("status") or "unknown")
    preflight = record.get("preflight", {})
    runtime_diagnostics = preflight.get("runtime_diagnostics") if isinstance(preflight, dict) else None
    recommended_value = preflight.get("recommended_next_tools") if isinstance(preflight, dict) else None
    recommended = list(recommended_value or ([CONFIG_NEXT_TOOL] if status == "blocked" else []))
    poll_next = {
        "tool": "GD_Poll_Run",
        "arguments": {"garden_root": str(root), "run_target": record["target"]},
        "run_target": record["target"],
        "run_id": record["run_id"],
    }
    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "run": {
            "run_id": record["run_id"],
            "recipe": record["recipe"],
            "status": record.get("status"),
            "runtime_status": status,
            "worker_pid": record.get("worker_pid"),
        },
        "recommended_next_tools": recommended,
        "output_count": len(record.get("outputs", [])),
    }
    report_details: dict[str, Any] = {
        "run_target": record["target"],
        "error": record.get("error"),
        "recommended_next_tools": recommended,
    }
    if status == "blocked":
        report_details["retry_tool"] = "DF_Grid_Start_Simulation"
    if runtime_diagnostics:
        summary_view["runtime_diagnostics"] = runtime_diagnostics
        report_details["runtime_diagnostics"] = runtime_diagnostics
    result: dict[str, Any] = {
        "target": record["target"],
        "run_target": record["target"],
        "runtime_status": status,
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status=status if status in {"blocked", "failed"} else "ok",
            message=f"Dragonfly Grid {record['recipe']} run {status}: {record['run_id']}",
            details=report_details,
        ),
    }
    if record.get("worker_pid") is not None:
        summary_view["worker_pid"] = record["worker_pid"]
        result["worker_pid"] = record["worker_pid"]
    return result
