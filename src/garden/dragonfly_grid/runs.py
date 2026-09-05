"""Garden-managed Dragonfly Electric Grid run ledgers."""

from __future__ import annotations

import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

from dragonfly_energy.run import run_default_report as sdk_run_default_report
from dragonfly_energy.run import run_reopt as sdk_run_reopt
from dragonfly_energy.run import run_rnm as sdk_run_rnm

from garden.ladybug_tools_config import (
    REQUIRED_RUNTIME_VERSIONS,
    get_ladybug_tools_config,
    iter_urbanopt_sdk_output_paths,
    urbanopt_runtime_env,
    write_urbanopt_bundle_config,
)
from garden.manifest import GardenManifest, utc_now_iso, write_json_file
from garden.paths import to_posix_relative
from garden.run_ledger import RunLedger, make_run_target, normalize_run_id
from garden.urbanopt_cli import (
    has_urbanopt_cli_bundle,
    has_urbanopt_opendss_python_deps,
    run_urbanopt_default_report_with_cli_bundle,
    run_urbanopt_opendss_with_cli_bundle,
    run_urbanopt_reopt_with_cli_bundle,
    run_urbanopt_rnm_with_cli_bundle,
)
from garden.dragonfly_grid.results import OPENDSS_RESULT_ARTIFACT_TYPE
from ladybug_tools_mcp.contracts.report import make_report

GRID_RUN_TARGET_TYPE = "dragonfly_grid_run"
GRID_RUN_DOMAIN = "dragonfly_grid"
GRID_RUN_ROOT = Path("runs") / "dragonfly_grid"
GRID_RUN_RECIPES = {"rnm", "opendss", "reopt"}
CONFIG_NEXT_TOOL = "LB_get_runtime_config"
LOCAL_GRID_RUNTIME_BLOCKER = (
    f"URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} is available for local-bundle Energy/OpenStudio execution, "
    "but this RNM/REopt path resolves to an online API unless a compatible "
    "local service or runtime is configured. MCP requires local-service runtime "
    "evidence and blocks online API submission."
)
DEFAULT_GRID_NETWORK_POLICY = {
    "mode": "local_runtime_required",
    "full_network_isolation_required": False,
    "online_install_allowed": False,
    "online_api_allowed": False,
    "local_bundle_required": True,
}
GRID_EXTERNAL_API_BLOCKERS = {
    "rnm": {
        "recipe": "rnm",
        "api_backed": True,
        "online_api_blocked": True,
        "online_api_endpoints": ["https://rnm.urbanopt.net/api/v2/"],
        "local_service_required": True,
        "local_service_configured": False,
        "required_local_runtime": (
            "Compatible local RNM service/runtime explicitly configured and "
            "covered by local-service runtime tests."
        ),
    },
    "reopt": {
        "recipe": "reopt",
        "api_backed": True,
        "online_api_blocked": True,
        "online_api_endpoints": ["https://developer.nrel.gov/api/reopt/v3/"],
        "local_service_required": True,
        "local_service_configured": False,
        "required_local_runtime": (
            "Compatible local REopt API/service explicitly configured and "
            "covered by local-service runtime tests."
        ),
    },
}

_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dragonfly-grid")
_GRID_RUN_LEDGER = RunLedger(lock="thread")


def start_rnm(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    underground_ratio: float = 0.9,
    lv_only: bool = True,
    nodes_per_building: int = 1,
) -> dict[str, Any]:
    """Start or block an RNM post-processing run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    runtime = _urbanopt_runtime_config()
    normalized_run_id = _normalize_run_id(run_id, "rnm")
    preflight = _preflight_rnm_runtime(runtime)
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
        preflight=preflight,
    )
    if record["status"] == "running":
        _BACKGROUND_EXECUTOR.submit(
            _run_rnm_job,
            garden_root=str(root),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            runtime=runtime,
            underground_ratio=underground_ratio,
            lv_only=lv_only,
            nodes_per_building=nodes_per_building,
            use_localhost=use_localhost,
        )
    latest = _run_record_by_id(root, "rnm", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def start_opendss(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    autosize: bool = False,
) -> dict[str, Any]:
    """Start or block an OpenDSS simulation run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    runtime = _urbanopt_runtime_config()
    normalized_run_id = _normalize_run_id(run_id, "opendss")
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
        _BACKGROUND_EXECUTOR.submit(
            _run_opendss_job,
            garden_root=str(root),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            runtime=runtime,
            autosize=autosize,
        )
    latest = _run_record_by_id(root, "opendss", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def start_reopt(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    urdb_label: str,
    run_id: str | None = None,
    developer_key: str | None = None,
) -> dict[str, Any]:
    """Start or block a REopt post-processing run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    feature_geojson = _resolve_artifact(root, manifest, feature_geojson_target, suffix=".geojson")
    scenario_csv = _resolve_artifact(root, manifest, scenario_csv_target, suffix=".csv")
    runtime = _urbanopt_runtime_config()
    normalized_run_id = _normalize_run_id(run_id, "reopt")
    preflight = _preflight_reopt_runtime(runtime)
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
        },
        preflight=preflight,
    )
    if record["status"] == "running":
        _BACKGROUND_EXECUTOR.submit(
            _run_reopt_job,
            garden_root=str(root),
            run_id=normalized_run_id,
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            runtime=runtime,
            urdb_label=urdb_label,
            developer_key=developer_key,
            use_localhost=use_localhost,
        )
    latest = _run_record_by_id(root, "reopt", normalized_run_id) or record
    return _result_from_record(root, manifest, latest)


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


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
    resolved = (root / path).resolve()
    resolved.relative_to(root.resolve())
    if suffix and resolved.suffix.lower() != suffix:
        raise ValueError(f"artifact path must end with {suffix}.")
    if not resolved.exists():
        raise ValueError(f"artifact target file was not found: {path}")
    return resolved


def _urbanopt_runtime_config() -> dict[str, Any] | None:
    try:
        config = get_ladybug_tools_config()
    except Exception:
        return None
    summary = config.get("summary_view") if isinstance(config, dict) else None
    if not isinstance(summary, dict):
        return None
    engines = summary.get("engines")
    if isinstance(engines, dict):
        urbanopt = engines.get("urbanopt")
        if isinstance(urbanopt, dict):
            return urbanopt
    return summary


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
    if runtime.get("available") is True:
        return True
    if runtime.get("status") == "available":
        return True
    bundle = runtime.get("cli_gem_bundle")
    if isinstance(bundle, dict) and bundle.get("status") == "available":
        return True
    return False


def _preflight_rnm_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = _urbanopt_runtime_config() if runtime is None else runtime
    diagnostics = _grid_external_api_diagnostics("rnm", runtime)
    if _grid_local_service_ready("rnm", runtime):
        return {
            "status": "ok",
            "runtime_status": "ready",
            "issues": [],
            "missing": [],
            "recommended_next_tools": [],
            "runtime_diagnostics": diagnostics,
        }
    if _urbanopt_runtime_ready(runtime):
        return _blocked_preflight(
            "rnm",
            LOCAL_GRID_RUNTIME_BLOCKER,
            runtime_diagnostics=diagnostics,
        )
    return _blocked_preflight(
        "rnm",
        "URBANopt/RNM runtime is not available.",
        runtime_diagnostics=diagnostics,
    )


def _preflight_opendss_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = _urbanopt_runtime_config() if runtime is None else runtime
    diagnostics = _opendss_runtime_diagnostics(runtime)
    if not has_urbanopt_cli_bundle(runtime):
        return _blocked_preflight(
            "opendss",
            f"URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle is required for local OpenDSS execution.",
            runtime_diagnostics=diagnostics,
        )
    if not has_urbanopt_opendss_python_deps(runtime):
        return _blocked_preflight(
            "opendss",
            f"URBANopt CLI OpenDSS Python dependencies are not initialized in the local {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle. "
            "Missing python_config.json under example_files/python_deps; provide an initialized local runtime pack. "
            "MCP local-bundle runtime validation will not run uo install_python or download dependencies.",
            runtime_diagnostics=diagnostics,
        )
    return {
        "status": "ok",
        "runtime_status": "ready",
        "issues": [],
        "missing": [],
        "recommended_next_tools": [],
        "runtime_diagnostics": diagnostics,
    }


def _preflight_reopt_runtime(runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = _urbanopt_runtime_config() if runtime is None else runtime
    diagnostics = _grid_external_api_diagnostics("reopt", runtime)
    if _grid_local_service_ready("reopt", runtime) and has_urbanopt_cli_bundle(runtime):
        return {
            "status": "ok",
            "runtime_status": "ready",
            "issues": [],
            "missing": [],
            "recommended_next_tools": [],
            "runtime_diagnostics": diagnostics,
        }
    if _urbanopt_runtime_ready(runtime):
        return _blocked_preflight(
            "reopt",
            LOCAL_GRID_RUNTIME_BLOCKER,
            runtime_diagnostics=diagnostics,
        )
    return _blocked_preflight(
        "reopt",
        "URBANopt/REopt runtime is not available.",
        runtime_diagnostics=diagnostics,
    )


def _blocked_preflight(
    name: str,
    message: str,
    *,
    runtime_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": [message],
        "missing": [name],
        "recommended_next_tools": [CONFIG_NEXT_TOOL],
    }
    if runtime_diagnostics:
        result["runtime_diagnostics"] = runtime_diagnostics
    return result


def _opendss_runtime_diagnostics(runtime: dict[str, Any] | None) -> dict[str, Any]:
    deps = _opendss_python_deps(runtime)
    return {"opendss_python_deps": deps} if deps else {}


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
            if isinstance(urbanopt, dict):
                service = urbanopt.get(f"{recipe}_service")
                if isinstance(service, dict):
                    return service
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
    deps = runtime.get("opendss_python_deps")
    if isinstance(deps, dict):
        return deps
    engines = runtime.get("engines")
    if isinstance(engines, dict):
        urbanopt = engines.get("urbanopt")
        if isinstance(urbanopt, dict):
            deps = urbanopt.get("opendss_python_deps")
            if isinstance(deps, dict):
                return deps
    return {}


def _normalize_run_id(run_id: str | None, prefix: str) -> str:
    return normalize_run_id(run_id, run_id or f"{prefix}_{uuid4().hex[:8]}")


def _run_target(garden_id: str, run_id: str, recipe: str) -> dict[str, Any]:
    if recipe not in GRID_RUN_RECIPES:
        raise ValueError(f"Unsupported Dragonfly Grid recipe: {recipe}.")
    return make_run_target(
        target_type=GRID_RUN_TARGET_TYPE,
        garden_id=garden_id,
        domain=GRID_RUN_DOMAIN,
        recipe=recipe,
        run_id=run_id,
    )


def _run_dir(root: Path, recipe: str, run_id: str) -> Path:
    return root / GRID_RUN_ROOT / recipe / run_id


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
    target = _run_target(manifest.garden_id, run_id, recipe)
    run_dir = _run_dir(garden_root, recipe, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json_file(
        run_dir / "background_request.json",
        {
            **request,
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
        },
        ensure_ascii=False,
    )
    status = "blocked" if preflight.get("runtime_status") == "blocked" else "running"
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
    _upsert_record(garden_root, recipe, record)
    return record


def _index_path(root: Path, recipe: str) -> Path:
    return root / GRID_RUN_ROOT / recipe / "index.json"


def _upsert_record(root: Path, recipe: str, record: dict[str, Any]) -> None:
    _GRID_RUN_LEDGER.upsert(_index_path(root, recipe), record)


def _run_record_by_id(root: Path, recipe: str, run_id: str) -> dict[str, Any] | None:
    return _GRID_RUN_LEDGER.get(_index_path(root, recipe), run_id)


def _complete_with_error(root: Path, recipe: str, run_id: str, message: str) -> None:
    record = _run_record_by_id(root, recipe, run_id)
    if record is None:
        return
    record.update(
        {
            "status": "failed",
            "runtime_status": "failed",
            "completed_at": utc_now_iso(),
            "error": message,
        }
    )
    _upsert_record(root, recipe, record)


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
            outputs = run_urbanopt_reopt_with_cli_bundle(
                feature_geojson=str(feature_geojson),
                scenario_csv=kwargs["scenario_csv"],
                runtime=runtime,
                urdb_label=kwargs["urdb_label"],
                developer_key=kwargs["developer_key"],
                use_localhost=kwargs.get("use_localhost", False),
            )
        else:
            with urbanopt_runtime_env(runtime):
                sdk_run_default_report(str(feature_geojson), kwargs["scenario_csv"])
                outputs = sdk_run_reopt(
                    str(feature_geojson),
                    kwargs["scenario_csv"],
                    kwargs["urdb_label"],
                    developer_key=kwargs["developer_key"],
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
    record = _run_record_by_id(root, recipe, run_id)
    if record is None:
        return
    outputs = [] if recipe == "opendss" else _outputs_from_sdk_result(root, sdk_outputs)
    if project_dir is not None:
        seen = {output["path"] for output in outputs}
        for output in _discover_project_outputs(root, project_dir, recipe):
            if output["path"] not in seen:
                outputs.append(output)
                seen.add(output["path"])
    if not outputs:
        record.update(
            {
                "status": "failed",
                "runtime_status": "failed",
                "completed_at": utc_now_iso(),
                "outputs": [],
                "error": f"Dragonfly Grid {recipe} run finished without discoverable outputs.",
            }
        )
        _upsert_record(root, recipe, record)
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
    _upsert_record(root, recipe, record)


def _outputs_from_sdk_result(root: Path, value: Any) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for output_type, path_value in iter_urbanopt_sdk_output_paths(value):
        path = Path(path_value).expanduser().resolve()
        if path.is_dir():
            outputs.extend(_scan_output_files(root, path))
            continue
        if not path.exists():
            continue
        name = f"{output_type}:{path.name}" if output_type else f"{path.suffix.lower().lstrip('.') or 'file'}:{path.name}"
        outputs.append(_output_for_path(root, path, name=name))
    return outputs


def _discover_project_outputs(root: Path, project_dir: Path, recipe: str) -> list[dict[str, Any]]:
    project_dir = project_dir.expanduser().resolve()
    if recipe == "rnm":
        return _scan_output_files(project_dir, project_dir / "run", root=root, pattern="rnm-us/results")
    if recipe == "reopt":
        outputs = []
        for path in sorted((project_dir / "run").rglob("scenario_optimization.*")):
            if path.is_file():
                outputs.append(_output_for_path(root, path))
        return outputs
    if recipe == "opendss":
        outputs = []
        for base in (project_dir / "opendss", project_dir / "run"):
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.csv")):
                if path.is_file():
                    outputs.append(_output_for_path(root, path, artifact_type=OPENDSS_RESULT_ARTIFACT_TYPE))
        return outputs
    return []


def _output_for_path(
    root: Path,
    path: Path,
    *,
    name: str | None = None,
    artifact_type: str | None = None,
) -> dict[str, Any]:
    output = {
        "name": name or path.name,
        "path": to_posix_relative(path, root),
        "exists": path.exists(),
        "kind": path.suffix.lower().lstrip(".") or "file",
    }
    if artifact_type is not None:
        manifest = GardenManifest.read(root)
        output.update(
            {
                "target_type": "artifact",
                "domain": GRID_RUN_DOMAIN,
                "garden_id": manifest.garden_id,
                "artifact_type": artifact_type,
                "identifier": path.stem,
            }
        )
    return output


def _scan_output_files(
    base_root: Path,
    path: Path,
    *,
    root: Path | None = None,
    pattern: str | None = None,
) -> list[dict[str, Any]]:
    result_root = root or base_root
    if not path.exists():
        return []
    outputs = []
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        rel = item.relative_to(base_root).as_posix() if item.is_relative_to(base_root) else item.as_posix()
        if pattern and pattern not in rel:
            continue
        if item.name == "background_request.json":
            continue
        outputs.append(_output_for_path(result_root, item))
    return outputs


def _result_from_record(root: Path, manifest: GardenManifest, record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("runtime_status") or record.get("status") or "unknown")
    preflight = record.get("preflight", {})
    runtime_diagnostics = (
        preflight.get("runtime_diagnostics") if isinstance(preflight, dict) else None
    )
    recommended_value = (
        preflight.get("recommended_next_tools") if isinstance(preflight, dict) else None
    )
    recommended = list(
        recommended_value or ([CONFIG_NEXT_TOOL] if status == "blocked" else [])
    )
    poll_next = {
        "tool": f"DF_grid_start_{record['recipe']}" if status == "blocked" else None,
        "run_target": record["target"],
        "run_id": record["run_id"],
    }
    summary_view = {
        "garden_target": manifest.target(),
        "run": {
            "run_id": record["run_id"],
            "recipe": record["recipe"],
            "status": record.get("status"),
            "runtime_status": status,
        },
        "recommended_next_tools": recommended,
        "output_count": len(record.get("outputs", [])),
    }
    report_details = {
        "run_target": record["target"],
        "error": record.get("error"),
        "recommended_next_tools": recommended,
    }
    if runtime_diagnostics:
        summary_view["runtime_diagnostics"] = runtime_diagnostics
        report_details["runtime_diagnostics"] = runtime_diagnostics
    return {
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
