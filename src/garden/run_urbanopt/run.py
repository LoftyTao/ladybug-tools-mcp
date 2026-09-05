"""Garden-managed URBANopt Energy run ledger and SDK command services."""

from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

from dragonfly_energy.config import folders as sdk_folders
from dragonfly_energy.run import base_honeybee_osw as sdk_base_honeybee_osw
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt

from garden.background import submit_daemon
from garden.dragonfly_des.artifacts import (
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    resolve_des_artifact_path,
)
from garden.ladybug_tools_config import (
    REQUIRED_RUNTIME_VERSIONS,
    get_ladybug_tools_config,
    iter_urbanopt_sdk_output_paths,
    urbanopt_runtime_env,
    write_urbanopt_bundle_config,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.run_ledger import (
    RunLedger,
    make_run_target,
    normalize_run_id,
    project_run,
    serialized_run_start,
)
from garden.run_ledger import run_id_from_target_or_value
from garden.run_energy.config import resolve_garden_weather_epw
from garden.urbanopt_cli import (
    has_urbanopt_cli_bundle,
    run_urbanopt_energy_with_cli_bundle,
)
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

URBANOPT_ARTIFACT_DOMAIN = "urbanopt"
URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE = "urbanopt_project_folder"
URBANOPT_RUN_TARGET_TYPE = "urbanopt_run"
URBANOPT_RUN_DOMAIN = "urbanopt"
URBANOPT_RUN_RECIPE = "run_energy"
URBANOPT_RUN_ROOT = Path("runs") / "urbanopt"
URBANOPT_RUN_INDEX = URBANOPT_RUN_ROOT / "index.json"
CONFIG_NEXT_TOOL = "LB_get_runtime_config"
DEFAULT_URBANOPT_NETWORK_POLICY = {
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

_URBANOPT_RUN_LEDGER = RunLedger(
    lock="file",
    atomic=True,
    recover_trailing_json=True,
    sort_by_created_at=True,
)


@serialized_run_start
def prepare_project(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    weather_target: dict[str, Any] | None = None,
    cpu_count: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Prepare a Garden-bounded URBANopt Energy project from a feature GeoJSON."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    project_dir = feature_geojson.parent
    model_target = _model_target_from_targets(
        manifest,
        feature_geojson_target,
    )
    epw_path = (
        resolve_garden_weather_epw(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        if weather_target is not None
        else None
    )
    preflight = _preflight_urbanopt_runtime()
    if preflight["runtime_status"] == "blocked":
        return _operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="prepare_project",
            preflight=preflight,
        )
    _prime_urbanopt_sdk_version_cache(preflight)

    runtime = preflight.get("runtime")
    _prepare_run_folder(
        garden_root=garden_root_path,
        project_dir=project_dir,
        recipe=None,
        model_target=model_target,
    )
    _clear_urbanopt_run_outputs(garden_root_path, project_dir)
    sdk_base_honeybee_osw(
        str(project_dir),
        epw_file=str(epw_path) if epw_path is not None else None,
        skip_report=False,
    )
    write_urbanopt_bundle_config(project_dir, runtime)
    scenario_csv = Path(
        sdk_prepare_urbanopt_folder(
            str(feature_geojson),
            cpu_count=cpu_count,
            verbose=verbose,
        )
    ).expanduser().resolve()
    write_urbanopt_bundle_config(project_dir, runtime)
    scenario_csv = _bounded_existing_path(garden_root_path, scenario_csv, suffix=".csv")
    project_dir = _bounded_existing_directory(garden_root_path, scenario_csv.parent)
    project_target = _artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(project_dir.name)}_urbanopt_project",
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        path=project_dir,
    )
    if model_target is not None:
        project_target["model_target"] = model_target
    scenario_target = _des_artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(scenario_csv.stem)}_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=scenario_csv,
    )
    if model_target is not None:
        scenario_target["model_target"] = model_target
    _register_artifacts(
        manifest=manifest,
        garden_root=garden_root_path,
        targets=[project_target, scenario_target],
    )
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        artifact_path=project_target["path"],
        absolute_path=str(project_dir),
        source={
            "feature_geojson_target": feature_geojson_target,
            "model_target": model_target,
        },
    )
    summary_view = {
        "garden_target": manifest.target(),
        "prepared": True,
        "runtime_status": "ready",
        "feature_geojson_target": feature_geojson_target,
        "project_folder_target": project_target,
        "scenario_csv_target": scenario_target,
        "preflight": preflight,
    }
    if model_target is not None:
        summary_view["model_target"] = model_target
    if weather_target is not None:
        summary_view["weather_target"] = weather_target
    return {
        "target": project_target,
        "project_folder_target": project_target,
        "scenario_csv_target": scenario_target,
        "runtime_status": "ready",
        "summary_view": summary_view,
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message="Prepared URBANopt Energy project folder.",
        ),
    }


@serialized_run_start
def start_simulation(
    *,
    garden_root: str,
    prepared_project_target: dict[str, Any],
    feature_geojson_target: dict[str, Any],
    scenario_csv_target: dict[str, Any],
    run_id: str | None = None,
    cpu_count: int | None = None,
) -> dict[str, Any]:
    """Start an URBANopt Energy run and write a Garden run ledger."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_run_id = _normalize_run_id(run_id)
    existing = _run_record_by_id(garden_root_path, normalized_run_id)
    if existing is not None:
        return _result_from_record(
            garden_root=garden_root_path,
            manifest=manifest,
            record=existing,
            message=f"URBANopt Energy run already exists: {normalized_run_id}",
        )
    project_dir = _resolve_project_folder(garden_root_path, manifest, prepared_project_target)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    if feature_geojson.parent != project_dir or scenario_csv.parent != project_dir:
        raise ValueError("URBANopt feature, scenario and prepared project must share one folder.")
    model_target = _model_target_from_targets(
        manifest,
        feature_geojson_target,
        prepared_project_target,
    )
    target = _run_target(manifest.garden_id, normalized_run_id)
    preflight = _preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status != "blocked":
        _prime_urbanopt_sdk_version_cache(preflight)
        _prepare_run_folder(
            garden_root=garden_root_path,
            project_dir=project_dir,
            recipe=URBANOPT_RUN_RECIPE,
            model_target=model_target,
        )
        _clear_urbanopt_run_outputs(garden_root_path, project_dir)
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        status=status,
        run_dir=project_dir,
        prepared_project_target=prepared_project_target,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        model_target=model_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
    )
    _upsert_record(garden_root_path, record)
    if status != "blocked":
        try:
            submit_daemon(
                _run_urbanopt_job,
                name="urbanopt-run",
                garden_root=str(garden_root_path),
                run_id=normalized_run_id,
                project_dir=str(project_dir),
                feature_geojson=str(feature_geojson),
                scenario_csv=str(scenario_csv),
                cpu_count=cpu_count,
                runtime=preflight.get("runtime"),
            )
        except Exception as exc:
            record.update(_failure_fields(str(exc), traceback.format_exc()))
            _upsert_record(garden_root_path, record)
    latest = _run_record_by_id(garden_root_path, normalized_run_id) or record
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=latest,
        message=f"URBANopt Energy run {latest['runtime_status']}: {normalized_run_id}",
    )


def poll_simulation(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read one URBANopt Energy run ledger record."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_id)
    if record is None:
        raise ValueError(f"URBANopt Energy run not found: {resolved_id}")
    return _result_from_record(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"URBANopt Energy run {record['runtime_status']}: {resolved_id}",
    )


def list_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List output files for one URBANopt Energy run ledger record."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_id)
    if record is None:
        raise ValueError(f"URBANopt Energy run not found: {resolved_id}")
    outputs = list(record.get("outputs") or [])
    return {
        "matches": outputs,
        "outputs": outputs,
        "run_target": record["target"],
        "runtime_status": record["runtime_status"],
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_id,
            "recipe": URBANOPT_RUN_RECIPE,
            "runtime_status": record["runtime_status"],
            "count": len(outputs),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(outputs)} output(s) for URBANopt Energy run {resolved_id}.",
        ),
    }


def _run_urbanopt_job(
    *,
    garden_root: str,
    run_id: str,
    project_dir: str,
    feature_geojson: str,
    scenario_csv: str,
    cpu_count: int | None,
    runtime: dict[str, Any] | None = None,
) -> None:
    garden_root_path = _garden_root(garden_root)
    record = _run_record_by_id(garden_root_path, run_id)
    if record is None:
        return
    try:
        if has_urbanopt_cli_bundle(runtime):
            run_urbanopt_energy_with_cli_bundle(
                feature_geojson=feature_geojson,
                scenario_csv=scenario_csv,
                runtime=runtime,
                cpu_count=cpu_count,
            )
            discovered = []
        else:
            with urbanopt_runtime_env(runtime):
                outputs = sdk_run_urbanopt(feature_geojson, scenario_csv, cpu_count=cpu_count)
            discovered = _outputs_from_sdk_result(garden_root_path, outputs)
        if not discovered:
            discovered = _discover_outputs(garden_root_path, Path(project_dir))
        if not discovered:
            raise RuntimeError("URBANopt run finished without discoverable outputs.")
        failed_job_error = _failed_job_error(garden_root_path, Path(project_dir))
        if failed_job_error:
            failure = _failure_fields(failed_job_error, failed_job_error)
            failure["outputs"] = discovered
            record.update(failure)
            _upsert_record(garden_root_path, record)
            return
        record.update(
            {
                "status": "completed",
                "runtime_status": "completed",
                "completed_at": utc_now_iso(),
                "outputs": discovered,
            }
        )
    except Exception as exc:
        record.update(_failure_fields(str(exc), traceback.format_exc()))
    _upsert_record(garden_root_path, record)


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _prepare_run_folder(
    *,
    garden_root: Path,
    project_dir: Path,
    recipe: str | None,
    model_target: dict[str, Any] | None,
) -> None:
    _URBANOPT_RUN_LEDGER.prepare_folder(
        garden_root / URBANOPT_RUN_INDEX,
        to_posix_relative(project_dir, garden_root),
        recipe=recipe,
        model_target=model_target,
    )


def _clear_urbanopt_run_outputs(garden_root: Path, project_dir: Path) -> None:
    garden_root = garden_root.expanduser().resolve()
    project_dir = project_dir.expanduser().resolve()
    try:
        project_dir.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("URBANopt project folder must stay inside the Garden.") from exc
    for name in ("run", "osm"):
        path = (project_dir / name).resolve()
        path.relative_to(project_dir)
        if path.is_dir():
            shutil.rmtree(path)


def _model_target_from_targets(
    manifest: GardenManifest,
    *targets: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for target in targets:
        if not isinstance(target, dict):
            continue
        model_target = target.get("model_target")
        if isinstance(model_target, dict):
            return model_target
    for target in targets:
        if not isinstance(target, dict):
            continue
        path = target.get("path")
        if not isinstance(path, str):
            continue
        for artifact in manifest.artifacts:
            if artifact.get("path") != path:
                continue
            model_target = artifact.get("model_target")
            if isinstance(model_target, dict):
                return model_target
    return None


def _resolve_feature_geojson(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        suffix=".geojson",
    )


def _resolve_scenario_csv(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        suffix=".csv",
    )


def _resolve_project_folder(
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
) -> Path:
    if not isinstance(target, dict):
        raise ValueError("Expected an URBANopt project folder target dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("URBANopt project target must have target_type 'artifact'.")
    if target.get("domain") != URBANOPT_ARTIFACT_DOMAIN:
        raise ValueError("URBANopt project target must reference domain 'urbanopt'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("URBANopt project target belongs to a different Garden.")
    if target.get("artifact_type") != URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE:
        raise ValueError("Expected URBANopt artifact type 'urbanopt_project_folder'.")
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("URBANopt project target requires a non-empty path.")
    if Path(path_value).is_absolute():
        raise ValueError("URBANopt project target path must be Garden-relative.")
    path = (garden_root / path_value).resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("URBANopt project target path must stay inside the Garden.") from exc
    if not path.is_dir():
        raise ValueError(f"URBANopt project folder not found: {path_value}")
    return path


def _bounded_existing_path(garden_root: Path, value: str | Path, *, suffix: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("URBANopt Energy artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} artifact: {path}")
    if not path.is_file():
        raise ValueError(f"URBANopt Energy artifact not found: {path}")
    return path


def _bounded_existing_directory(garden_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("URBANopt Energy project folders must stay inside the Garden.") from exc
    if not path.is_dir():
        raise ValueError(f"URBANopt Energy project folder not found: {path}")
    return path


def _preflight_urbanopt_runtime() -> dict[str, Any]:
    config = get_ladybug_tools_config()
    urbanopt = config["summary_view"]["engines"].get("urbanopt", {})
    issues = []
    if not urbanopt.get("available"):
        issues.append("URBANopt CLI or Gemfile is not available to dragonfly_energy.")
    if not has_urbanopt_cli_bundle(urbanopt):
        issues.append(
            f"A local URBANopt CLI {REQUIRED_RUNTIME_VERSIONS['urbanopt']} bundle Gemfile is required for MCP local-bundle runtime validation."
        )
    if urbanopt.get("version_status") in {"older", "newer", "unknown"}:
        issues.append("URBANopt runtime version does not match the current DEV requirement.")
    if issues:
        return _blocked_preflight(issues, missing=["urbanopt"], runtime=urbanopt)
    return {"status": "ok", "runtime_status": "ready", "issues": [], "runtime": urbanopt}


def _prime_urbanopt_sdk_version_cache(preflight: dict[str, Any]) -> None:
    runtime = preflight.get("runtime") if isinstance(preflight, dict) else None
    if not isinstance(runtime, dict):
        return
    version = runtime.get("version") or runtime.get("detected_version")
    parsed = _parse_version_tuple(version)
    if parsed is None:
        return
    sdk_folders._urbanopt_version = parsed
    sdk_folders._urbanopt_version_str = ".".join(str(part) for part in parsed)


def _parse_version_tuple(value: Any) -> tuple[int, ...] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parts = value.strip().split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _blocked_preflight(
    issues: list[str],
    *,
    missing: list[str],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": issues,
        "missing": sorted(set(missing)),
        "runtime": runtime,
        "recommended_next_tools": [CONFIG_NEXT_TOOL],
    }
    diagnostics = _runtime_diagnostics_from_preflight(result)
    if diagnostics:
        result["runtime_diagnostics"] = diagnostics
    return result


def _runtime_diagnostics_from_preflight(preflight: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(preflight, dict):
        return {}
    runtime = preflight.get("runtime")
    if not isinstance(runtime, dict):
        return {}
    policy = runtime.get("network_policy")
    if not isinstance(policy, dict):
        policy = DEFAULT_URBANOPT_NETWORK_POLICY
    return {
        "network_policy": dict(policy),
        "urbanopt": runtime,
    }


def _preflight_runtime_diagnostics(preflight: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(preflight, dict):
        return {}
    existing = preflight.get("runtime_diagnostics")
    if isinstance(existing, dict) and existing:
        return existing
    return _runtime_diagnostics_from_preflight(preflight)


def _attach_runtime_diagnostics(
    summary_view: dict[str, Any],
    report_details: dict[str, Any],
    preflight: dict[str, Any] | None,
) -> None:
    diagnostics = _preflight_runtime_diagnostics(preflight)
    if diagnostics:
        summary_view["runtime_diagnostics"] = diagnostics
        report_details["runtime_diagnostics"] = diagnostics


def _operation_blocked_result(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    operation: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    recommended = list(preflight.get("recommended_next_tools") or [CONFIG_NEXT_TOOL])
    summary_view = {
        "garden_target": manifest.target(),
        "operation": operation,
        "runtime_status": "blocked",
        "preflight": preflight,
        "recommended_next_tools": recommended,
    }
    report_details = {
        "garden_root": str(garden_root),
        "recommended_next_tools": recommended,
        "preflight": preflight,
    }
    _attach_runtime_diagnostics(summary_view, report_details, preflight)
    return {
        "runtime_status": "blocked",
        "summary_view": summary_view,
        "report": make_report(
            status="warning",
            message=f"URBANopt Energy operation blocked by missing runtime: {operation}",
            warnings=list(preflight.get("issues") or []),
            details=report_details,
        ),
    }


def _normalize_run_id(value: str | None) -> str:
    return normalize_run_id(
        value,
        value or f"urbanopt_energy_{utc_now_iso()}_{uuid4().hex[:8]}",
    )


def _run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    return make_run_target(
        target_type=URBANOPT_RUN_TARGET_TYPE,
        garden_id=garden_id,
        domain=URBANOPT_RUN_DOMAIN,
        recipe=URBANOPT_RUN_RECIPE,
        run_id=run_id,
    )


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    return run_id_from_target_or_value(
        run_target,
        run_id,
        target_type=URBANOPT_RUN_TARGET_TYPE,
        domain=URBANOPT_RUN_DOMAIN,
        domain_message="run_target must reference domain 'urbanopt'.",
        recipe=URBANOPT_RUN_RECIPE,
        missing_message="Pass run_target or run_id.",
        slug_value=True,
    )


def _record(
    *,
    garden_root: Path,
    run_id: str,
    target: dict[str, Any],
    status: str,
    run_dir: Path,
    preflight: dict[str, Any],
    completed_at: str | None = None,
    error: str | None = None,
    outputs: list[dict[str, Any]] | None = None,
    **targets: Any,
) -> dict[str, Any]:
    started_at = utc_now_iso()
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": URBANOPT_RUN_RECIPE,
        "status": status,
        "runtime_status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(run_dir, garden_root),
        "preflight": preflight,
        "outputs": outputs or [],
    }
    for key, value in targets.items():
        if value is not None:
            record[key] = value
    if completed_at is not None:
        record["completed_at"] = completed_at
    if error:
        record["error"] = error
    return record


def _failure_fields(error: str, traceback_text: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "runtime_status": "failed",
        "completed_at": utc_now_iso(),
        "error": error,
        "traceback": traceback_text,
    }


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    _URBANOPT_RUN_LEDGER.upsert(garden_root / URBANOPT_RUN_INDEX, record)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any] | None:
    return _URBANOPT_RUN_LEDGER.get(garden_root / URBANOPT_RUN_INDEX, run_id)


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "target",
        "recipe",
        "status",
        "runtime_status",
        "created_at",
        "started_at",
        "completed_at",
        "run_folder",
        "prepared_project_target",
        "feature_geojson_target",
        "scenario_csv_target",
        "model_target",
        "preflight",
        "outputs",
        "error",
    )
    return project_run(record, keys)


def _result_from_record(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    target = record["target"]
    runtime_status = record["runtime_status"]
    recommended = list((record.get("preflight") or {}).get("recommended_next_tools") or [])
    if runtime_status in {"blocked", "failed"} and not recommended:
        recommended = [CONFIG_NEXT_TOOL]
    poll_next = {
        "tool": "DF_urbanopt_poll_simulation",
        "arguments": {"garden_root": str(garden_root), "run_target": target},
    }
    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "recipe": record["recipe"],
        "status": runtime_status,
        "runtime_status": runtime_status,
        "run": _public_run(record),
        "outputs": record.get("outputs") or [],
        "poll_next": poll_next,
        "preflight": record.get("preflight"),
        "recommended_next_tools": recommended,
    }
    report_status = "warning" if runtime_status in {"blocked", "failed"} else "ok"
    report_details = {
        "recommended_next_tools": recommended,
        "preflight": record.get("preflight"),
    }
    _attach_runtime_diagnostics(summary_view, report_details, record.get("preflight"))
    return {
        "target": target,
        "run_target": target,
        "runtime_status": runtime_status,
        "poll_next": poll_next,
        "summary_view": summary_view,
        "report": make_report(
            status=report_status,
            message=message,
            warnings=list((record.get("preflight") or {}).get("issues") or []),
            details=report_details,
        ),
    }


def _artifact_target_for_path(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    identifier: str,
    artifact_type: str,
    path: Path,
) -> dict[str, Any]:
    return {
        "target_type": "artifact",
        "domain": URBANOPT_ARTIFACT_DOMAIN,
        "garden_id": manifest.garden_id,
        "artifact_type": artifact_type,
        "identifier": identifier,
        "path": to_posix_relative(path, garden_root),
    }


def _des_artifact_target_for_path(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    identifier: str,
    artifact_type: str,
    path: Path,
) -> dict[str, Any]:
    return {
        "target_type": "artifact",
        "domain": "dragonfly_des",
        "garden_id": manifest.garden_id,
        "artifact_type": artifact_type,
        "identifier": identifier,
        "path": to_posix_relative(path, garden_root),
    }


def _register_artifacts(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    targets: list[dict[str, Any]],
) -> None:
    for target in targets:
        manifest.upsert_artifact(
            target,
            key_fields=("domain", "artifact_type", "identifier"),
        )
    manifest.write(garden_root)


def _output_for_path(garden_root: Path, path: Path, *, name: str | None = None) -> dict[str, Any]:
    suffix = path.suffix.lower().lstrip(".")
    return {
        "name": name or path.name,
        "path": to_posix_relative(path, garden_root),
        "exists": path.exists(),
        "is_directory": path.is_dir(),
        "kind": suffix or ("folder" if path.is_dir() else "file"),
    }


def _outputs_from_sdk_result(garden_root: Path, value: Any) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for output_type, path in iter_urbanopt_sdk_output_paths(value):
        path_obj = Path(path).resolve()
        name = f"{output_type}:{path_obj.name}" if output_type else None
        outputs.append(_output_for_path(garden_root, path_obj, name=name))
    return outputs


def _discover_outputs(garden_root: Path, root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    outputs = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "background_request.json":
            continue
        if path.name.lower() not in URBANOPT_STANDARD_OUTPUT_NAMES:
            continue
        outputs.append(_output_for_path(garden_root, path))
    return outputs


def _failed_job_error(garden_root: Path, root: Path) -> str | None:
    if not root.is_dir():
        return None
    failed_jobs = sorted(root.rglob("failed.job"))
    if not failed_jobs:
        return None
    markers = ", ".join(to_posix_relative(path, garden_root) for path in failed_jobs[:5])
    if len(failed_jobs) > 5:
        markers += f", ... ({len(failed_jobs)} total)"
    return f"URBANopt run wrote failed.job marker(s): {markers}"
