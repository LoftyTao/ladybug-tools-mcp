"""Garden-managed URBANopt Energy run ledger and SDK command services."""

from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

from dragonfly_energy.config import folders as sdk_folders
from dragonfly_energy.run import prepare_urbanopt_folder as sdk_prepare_urbanopt_folder
from dragonfly_energy.run import run_urbanopt as sdk_run_urbanopt

from garden.dragonfly_des.artifacts import (
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    resolve_des_artifact_path,
)
from garden.ladybug_tools_config import get_ladybug_tools_config
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

URBANOPT_ARTIFACT_DOMAIN = "urbanopt"
URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE = "urbanopt_project_folder"
URBANOPT_RUN_TARGET_TYPE = "urbanopt_run"
URBANOPT_RUN_DOMAIN = "urbanopt"
URBANOPT_RUN_RECIPE = "run_energy"
URBANOPT_RUN_ROOT = Path("runs") / "urbanopt"
URBANOPT_RUN_INDEX = URBANOPT_RUN_ROOT / "index.json"
CONFIG_NEXT_TOOL = "config_get_runtime_config"

_index_lock = threading.Lock()


def prepare_project(
    *,
    garden_root: str,
    feature_geojson_target: dict[str, Any],
    cpu_count: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Prepare a Garden-bounded URBANopt Energy project from a feature GeoJSON."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    preflight = _preflight_urbanopt_runtime()
    if preflight["runtime_status"] == "blocked":
        return _operation_blocked_result(
            garden_root=garden_root_path,
            manifest=manifest,
            operation="prepare_project",
            preflight=preflight,
        )
    _prime_urbanopt_sdk_version_cache(preflight)

    scenario_csv = Path(
        sdk_prepare_urbanopt_folder(
            str(feature_geojson),
            cpu_count=cpu_count,
            verbose=verbose,
        )
    ).expanduser().resolve()
    scenario_csv = _bounded_existing_path(garden_root_path, scenario_csv, suffix=".csv")
    project_dir = _bounded_existing_directory(garden_root_path, scenario_csv.parent)
    project_target = _artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(project_dir.name)}_urbanopt_project",
        artifact_type=URBANOPT_PROJECT_FOLDER_ARTIFACT_TYPE,
        path=project_dir,
    )
    scenario_target = _des_artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{slugify_name(scenario_csv.stem)}_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=scenario_csv,
    )
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
        source={"feature_geojson_target": feature_geojson_target},
    )
    return {
        "target": project_target,
        "project_folder_target": project_target,
        "scenario_csv_target": scenario_target,
        "runtime_status": "ready",
        "summary_view": {
            "garden_target": manifest.target(),
            "prepared": True,
            "runtime_status": "ready",
            "feature_geojson_target": feature_geojson_target,
            "project_folder_target": project_target,
            "scenario_csv_target": scenario_target,
            "preflight": preflight,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message="Prepared URBANopt Energy project folder.",
        ),
    }


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
    project_dir = _resolve_project_folder(garden_root_path, manifest, prepared_project_target)
    feature_geojson = _resolve_feature_geojson(garden_root_path, manifest, feature_geojson_target)
    scenario_csv = _resolve_scenario_csv(garden_root_path, manifest, scenario_csv_target)
    normalized_run_id = _normalize_run_id(run_id)
    target = _run_target(manifest.garden_id, normalized_run_id)
    run_dir = garden_root_path / URBANOPT_RUN_ROOT / normalized_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_background_request(
        run_dir,
        {
            "operation": "run_urbanopt",
            "prepared_project_target": prepared_project_target,
            "feature_geojson_target": feature_geojson_target,
            "scenario_csv_target": scenario_csv_target,
            "cpu_count": cpu_count,
        },
    )
    preflight = _preflight_urbanopt_runtime()
    status = "blocked" if preflight["runtime_status"] == "blocked" else "running"
    if status != "blocked":
        _prime_urbanopt_sdk_version_cache(preflight)
    record = _record(
        garden_root=garden_root_path,
        run_id=normalized_run_id,
        target=target,
        status=status,
        run_dir=run_dir,
        prepared_project_target=prepared_project_target,
        feature_geojson_target=feature_geojson_target,
        scenario_csv_target=scenario_csv_target,
        preflight=preflight,
        completed_at=utc_now_iso() if status == "blocked" else None,
        error="; ".join(preflight["issues"]) if status == "blocked" else None,
    )
    _upsert_record(garden_root_path, record)
    if status != "blocked":
        _BACKGROUND_EXECUTOR.submit(
            _run_urbanopt_job,
            garden_root=str(garden_root_path),
            run_id=normalized_run_id,
            project_dir=str(project_dir),
            feature_geojson=str(feature_geojson),
            scenario_csv=str(scenario_csv),
            cpu_count=cpu_count,
        )
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
    if not outputs:
        run_folder = record.get("run_folder")
        if isinstance(run_folder, str):
            outputs = _discover_outputs(garden_root_path, garden_root_path / run_folder)
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


class _BackgroundExecutor:
    """Submit URBANopt SDK work without blocking the MCP tool response."""

    def submit(self, fn, **kwargs):
        thread = Thread(target=fn, kwargs=kwargs, name="urbanopt-run", daemon=True)
        thread.start()
        return thread


_BACKGROUND_EXECUTOR = _BackgroundExecutor()


def _run_urbanopt_job(
    *,
    garden_root: str,
    run_id: str,
    project_dir: str,
    feature_geojson: str,
    scenario_csv: str,
    cpu_count: int | None,
) -> None:
    garden_root_path = _garden_root(garden_root)
    record = _run_record_by_id(garden_root_path, run_id)
    if record is None:
        return
    try:
        outputs = sdk_run_urbanopt(feature_geojson, scenario_csv, cpu_count=cpu_count)
        discovered = _outputs_from_sdk_result(garden_root_path, outputs)
        if not discovered:
            discovered = _discover_outputs(garden_root_path, Path(project_dir))
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
    return {
        "status": "blocked",
        "runtime_status": "blocked",
        "issues": issues,
        "missing": sorted(set(missing)),
        "runtime": runtime,
        "recommended_next_tools": [CONFIG_NEXT_TOOL],
    }


def _operation_blocked_result(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    operation: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    recommended = list(preflight.get("recommended_next_tools") or [CONFIG_NEXT_TOOL])
    return {
        "runtime_status": "blocked",
        "summary_view": {
            "garden_target": manifest.target(),
            "operation": operation,
            "runtime_status": "blocked",
            "preflight": preflight,
            "recommended_next_tools": recommended,
        },
        "report": make_report(
            status="warning",
            message=f"URBANopt Energy operation blocked by missing runtime: {operation}",
            warnings=list(preflight.get("issues") or []),
            details={
                "garden_root": str(garden_root),
                "recommended_next_tools": recommended,
                "preflight": preflight,
            },
        ),
    }


def _normalize_run_id(value: str | None) -> str:
    if value:
        return slugify_name(value)
    return slugify_name(f"urbanopt_energy_{utc_now_iso()}_{uuid4().hex[:8]}")


def _run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    return {
        "target_type": URBANOPT_RUN_TARGET_TYPE,
        "domain": URBANOPT_RUN_DOMAIN,
        "garden_id": garden_id,
        "recipe": URBANOPT_RUN_RECIPE,
        "run_id": run_id,
    }


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    if run_target is not None:
        if run_target.get("target_type") != URBANOPT_RUN_TARGET_TYPE:
            raise ValueError("run_target must be an urbanopt_run target.")
        if run_target.get("domain") != URBANOPT_RUN_DOMAIN:
            raise ValueError("run_target must reference domain 'urbanopt'.")
        if run_target.get("recipe") != URBANOPT_RUN_RECIPE:
            raise ValueError(f"run_target must reference recipe '{URBANOPT_RUN_RECIPE}'.")
        value = run_target.get("run_id")
        if not value:
            raise ValueError("run_target requires run_id.")
        return str(value)
    if run_id:
        return slugify_name(run_id)
    raise ValueError("Pass run_target or run_id.")


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


def _write_background_request(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "background_request.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    path = garden_root / URBANOPT_RUN_INDEX
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return list(json.loads(text).get("runs", []))


def _write_index(garden_root: Path, records: list[dict[str, Any]]) -> None:
    path = garden_root / URBANOPT_RUN_INDEX
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"runs": records}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    with _index_lock:
        records = [
            item for item in _read_index(garden_root) if item.get("run_id") != record["run_id"]
        ]
        records.append(record)
        _write_index(garden_root, records)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any] | None:
    for record in _read_index(garden_root):
        if record.get("run_id") == run_id:
            return record
    return None


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
        "preflight",
        "outputs",
        "error",
    )
    return {key: record.get(key) for key in keys if key in record}


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
        "tool": "urbanopt_poll_simulation",
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
            details={
                "recommended_next_tools": recommended,
                "preflight": record.get("preflight"),
            },
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
        manifest.artifacts = [
            item
            for item in manifest.artifacts
            if not (
                item.get("domain") == target["domain"]
                and item.get("artifact_type") == target["artifact_type"]
                and item.get("identifier") == target["identifier"]
            )
        ]
        manifest.artifacts.append(target)
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
    if isinstance(value, dict):
        for output_type, paths in value.items():
            if isinstance(paths, (list, tuple)):
                for path in paths:
                    path_obj = Path(path).resolve()
                    outputs.append(
                        _output_for_path(
                            garden_root,
                            path_obj,
                            name=f"{output_type}:{path_obj.name}",
                        )
                    )
            elif paths:
                outputs.append(
                    _output_for_path(garden_root, Path(paths).resolve(), name=str(output_type))
                )
    elif isinstance(value, (list, tuple)):
        for path in value:
            outputs.append(_output_for_path(garden_root, Path(path).resolve()))
    elif value:
        outputs.append(_output_for_path(garden_root, Path(value).resolve()))
    return outputs


def _discover_outputs(garden_root: Path, root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    outputs = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "background_request.json":
            continue
        outputs.append(_output_for_path(garden_root, path))
    return outputs
