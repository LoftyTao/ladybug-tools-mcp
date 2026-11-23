"""Garden-managed URBANopt Energy run ledger and SDK command services."""

from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from typing import Any

from dragonfly_energy.run import base_honeybee_osw as sdk_base_honeybee_osw
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt

from garden.background import submit_daemon
from garden.dragonfly_des.export import (
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    resolve_des_artifact_path,
)
from garden.ladybug_tools_config import urbanopt_runtime_env, write_urbanopt_bundle_config
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_energy.config import resolve_garden_weather_epw
from garden.run_ledger import RunManager, serialized_run_start
from garden.urbanopt_cli import (
    CONFIG_NEXT_TOOL,
    DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY,
    attach_runtime_diagnostics,
    discover_urbanopt_outputs,
    failed_urbanopt_job_error,
    has_urbanopt_cli_bundle,
    operation_blocked_result,
    outputs_from_sdk_result,
    preflight_urbanopt_runtime,
    prime_urbanopt_sdk_version_cache,
    run_urbanopt_energy_with_cli_bundle,
)
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

URBANOPT_ARTIFACT_DOMAIN = "urbanopt"
URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE = "urbanopt_project_folder"
URBANOPT_RUN_TARGET_TYPE = "urbanopt_run"
URBANOPT_RUN_DOMAIN = "urbanopt"
URBANOPT_RUN_RECIPE = "run_energy"
URBANOPT_RUN_ROOT = Path("runs") / "urbanopt"
URBANOPT_RUN_INDEX = URBANOPT_RUN_ROOT / "index.json"
DEFAULT_URBANOPT_NETWORK_POLICY = DEFAULT_LOCAL_RUNTIME_NETWORK_POLICY

_URBANOPT_RUNS = RunManager(
    domain=URBANOPT_RUN_DOMAIN,
    target_type=URBANOPT_RUN_TARGET_TYPE,
    runs_dir=URBANOPT_RUN_ROOT,
    default_recipe=URBANOPT_RUN_RECIPE,
    allowed_recipes={URBANOPT_RUN_RECIPE},
    run_id_prefix="urbanopt_energy",
    use_uuid_fallback=True,
    slug_lookup=True,
    domain_message="run_target must reference domain 'urbanopt'.",
    missing_message="Pass run_target or run_id.",
    not_found_label="URBANopt Energy",
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
        "prepared_project_target",
        "feature_geojson_target",
        "scenario_csv_target",
        "model_target",
        "preflight",
        "outputs",
        "error",
    ),
)
_URBANOPT_RUN_LEDGER = _URBANOPT_RUNS.ledger


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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    project_dir = feature_geojson.parent
    model_target = _model_target_from_targets(manifest, feature_geojson_target)
    epw_path = (
        resolve_garden_weather_epw(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        if weather_target is not None
        else None
    )
    preflight = preflight_urbanopt_runtime()
    if preflight["runtime_status"] == "blocked":
        return operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="prepare_project",
            preflight=preflight,
            label="URBANopt Energy",
        )
    prime_urbanopt_sdk_version_cache(preflight)

    runtime = preflight.get("runtime")
    _URBANOPT_RUNS.prepare_folder(
        garden_root_path,
        to_posix_relative(project_dir, garden_root_path),
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
    scenario_csv = resolve_existing_garden_path(
        garden_root_path, scenario_csv, kind="file", suffix=".csv", label="URBANopt Energy artifact"
    )
    project_dir = resolve_existing_garden_path(
        garden_root_path, scenario_csv.parent, kind="directory", label="URBANopt Energy project folder"
    )
    project_target = _artifact_target(
        manifest=manifest,
        garden_root=garden_root_path,
        domain=URBANOPT_ARTIFACT_DOMAIN,
        identifier=f"{slugify_name(project_dir.name)}_urbanopt_project",
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        path=project_dir,
        model_target=model_target,
    )
    scenario_target = _artifact_target(
        manifest=manifest,
        garden_root=garden_root_path,
        domain="dragonfly_des",
        identifier=f"{slugify_name(scenario_csv.stem)}_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=scenario_csv,
        model_target=model_target,
    )
    for target in (project_target, scenario_target):
        manifest.upsert_artifact(target, key_fields=("domain", "artifact_type", "identifier"))
    manifest.write(garden_root_path)

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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_run_id = _URBANOPT_RUNS.normalize_run_id(run_id)
    existing = _URBANOPT_RUNS.get(garden_root_path, normalized_run_id)
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
    target = _URBANOPT_RUNS.make_target(manifest.garden_id, normalized_run_id)
    preflight = preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status != "blocked":
        prime_urbanopt_sdk_version_cache(preflight)
        _URBANOPT_RUNS.prepare_folder(
            garden_root_path,
            to_posix_relative(project_dir, garden_root_path),
            recipe=URBANOPT_RUN_RECIPE,
            model_target=model_target,
        )
        _clear_urbanopt_run_outputs(garden_root_path, project_dir)
    started_at = utc_now_iso()
    record: dict[str, Any] = {
        "run_id": normalized_run_id,
        "target": target,
        "recipe": URBANOPT_RUN_RECIPE,
        "status": status,
        "runtime_status": status,
        "created_at": started_at,
        "started_at": started_at,
        "run_folder": to_posix_relative(project_dir, garden_root_path),
        "prepared_project_target": prepared_project_target,
        "feature_geojson_target": feature_geojson_target,
        "scenario_csv_target": scenario_csv_target,
        "preflight": preflight,
        "outputs": [],
    }
    if model_target is not None:
        record["model_target"] = model_target
    if status == "blocked":
        record["completed_at"] = utc_now_iso()
        if preflight["issues"]:
            record["error"] = "; ".join(preflight["issues"])
    _URBANOPT_RUNS.upsert(garden_root_path, record)
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
            record.update(_URBANOPT_RUNS.failure_fields(str(exc), traceback.format_exc()))
            _URBANOPT_RUNS.upsert(garden_root_path, record)
    latest = _URBANOPT_RUNS.get(garden_root_path, normalized_run_id) or record
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _URBANOPT_RUNS.resolve_run_id(run_target, run_id, recipe=URBANOPT_RUN_RECIPE)
    record = _URBANOPT_RUNS.require(garden_root_path, resolved_id)
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_id = _URBANOPT_RUNS.resolve_run_id(run_target, run_id, recipe=URBANOPT_RUN_RECIPE)
    record = _URBANOPT_RUNS.require(garden_root_path, resolved_id)
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
    garden_root_path = require_garden_root(garden_root)
    record = _URBANOPT_RUNS.get(garden_root_path, run_id)
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
            discovered = outputs_from_sdk_result(garden_root_path, outputs)
        if not discovered:
            discovered = discover_urbanopt_outputs(garden_root_path, Path(project_dir))
        if not discovered:
            raise RuntimeError("URBANopt run finished without discoverable outputs.")
        failed_job_error = failed_urbanopt_job_error(garden_root_path, Path(project_dir))
        if failed_job_error:
            failure = _URBANOPT_RUNS.failure_fields(failed_job_error, failed_job_error)
            failure["outputs"] = discovered
            record.update(failure)
            _URBANOPT_RUNS.upsert(garden_root_path, record)
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
        record.update(_URBANOPT_RUNS.failure_fields(str(exc), traceback.format_exc()))
    _URBANOPT_RUNS.upsert(garden_root_path, record)


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
        if isinstance(target, dict) and isinstance(target.get("model_target"), dict):
            return target["model_target"]
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("path"), str):
            continue
        for artifact in manifest.artifacts:
            if artifact.get("path") == target["path"] and isinstance(artifact.get("model_target"), dict):
                return artifact["model_target"]
    return None


def _resolve_feature_geojson(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        suffix=".geojson",
    )


def _resolve_scenario_csv(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
    return resolve_des_artifact_path(
        garden_root=garden_root,
        manifest=manifest,
        target=target,
        expected_artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        suffix=".csv",
    )


def _resolve_project_folder(garden_root: Path, manifest: GardenManifest, target: dict[str, Any]) -> Path:
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
    return resolve_existing_garden_path(
        garden_root,
        path_value,
        kind="directory",
        label="URBANopt project folder",
    )


def _artifact_target(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    domain: str,
    identifier: str,
    artifact_type: str,
    path: Path,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": "artifact",
        "domain": domain,
        "garden_id": manifest.garden_id,
        "artifact_type": artifact_type,
        "identifier": identifier,
        "path": to_posix_relative(path, garden_root),
    }
    if model_target is not None:
        target["model_target"] = model_target
    return target


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
        "tool": "DF_URBANopt_Poll_Simulation",
        "arguments": {"garden_root": str(garden_root), "run_target": target},
    }
    summary_view = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "recipe": record["recipe"],
        "status": runtime_status,
        "runtime_status": runtime_status,
        "run": _URBANOPT_RUNS.public_run(record),
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
    attach_runtime_diagnostics(summary_view, report_details, record.get("preflight"))
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


__all__ = [
    "DEFAULT_URBANOPT_NETWORK_POLICY",
    "URBANOPT_ARTIFACT_DOMAIN",
    "URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE",
    "URBANOPT_RUN_DOMAIN",
    "URBANOPT_RUN_INDEX",
    "URBANOPT_RUN_RECIPE",
    "URBANOPT_RUN_ROOT",
    "URBANOPT_RUN_TARGET_TYPE",
    "_URBANOPT_RUN_LEDGER",
    "list_run_outputs",
    "poll_simulation",
    "prepare_project",
    "start_simulation",
]
