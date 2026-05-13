"""Fairyfly THERM writing and run ledger services."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import get_ident
from typing import Any

from fairyfly_therm.run import run_thmz
from fairyfly_therm.writer import model_to_thmz

from garden.fairyfly.availability import therm_engine_config
from garden.fairyfly.model_io import load_fairyfly_model, resolve_model_target
from garden.fairyfly.targets import (
    FAIRYFLY_THERM_RECIPE,
    make_fairyfly_therm_run_target,
    make_fairyfly_thmz_target,
    normalize_fairyfly_therm_run_target,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

FAIRYFLY_THERM_RUNS_DIR = Path("runs") / "fairyfly_therm"
FAIRYFLY_THERM_INDEX = FAIRYFLY_THERM_RUNS_DIR / "index.json"


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _run_index_path(garden_root: Path) -> Path:
    return garden_root / FAIRYFLY_THERM_INDEX


def _decode_index_payload(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if exc.msg != "Extra data":
            raise
        payload, _ = json.JSONDecoder().raw_decode(raw)
        if not isinstance(payload, dict):
            raise
        return payload


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    path = _run_index_path(garden_root)
    if not path.is_file():
        return []
    return list(_decode_index_payload(path.read_text(encoding="utf-8")).get("runs", []))


def _write_index(garden_root: Path, records: list[dict[str, Any]]) -> None:
    path = _run_index_path(garden_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{get_ident()}.tmp")
    try:
        tmp_path.write_text(
            json.dumps({"runs": records}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    records = [
        item for item in _read_index(garden_root) if item.get("run_id") != record["run_id"]
    ]
    records.append(record)
    records.sort(key=lambda item: str(item.get("created_at", "")))
    _write_index(garden_root, records)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    for record in _read_index(garden_root):
        if record.get("run_id") == run_id:
            return record
    raise ValueError(f"Fairyfly THERM run was not found: {run_id}")


def _normalize_run_id(value: str | None) -> str:
    if value:
        return slugify_name(value)
    timestamp = utc_now_iso().replace(":", "").replace("-", "").replace("Z", "").lower()
    return f"fairyfly_therm_{timestamp}"


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    if run_target is not None:
        return str(normalize_fairyfly_therm_run_target(run_target)["run_id"])
    if run_id:
        return str(run_id)
    raise ValueError("Provide run_target or run_id.")


def _run_dir(garden_root: Path, run_id: str) -> Path:
    run_dir = (garden_root / FAIRYFLY_THERM_RUNS_DIR / run_id).resolve()
    run_dir.relative_to(garden_root)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "target",
        "recipe",
        "status",
        "created_at",
        "completed_at",
        "model_target",
        "model_path",
        "run_folder",
        "thmz_target",
        "thmz_path",
        "engine",
        "disabled_reason",
        "warnings",
    )
    return {key: record.get(key) for key in keys if key in record}


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact_type
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(record)
    return record


def _run_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
    report_status: str = "ok",
) -> dict[str, Any]:
    target = record["target"]
    poll_arguments = {"garden_root": str(garden_root), "run_target": target}
    summary = {
        "garden_target": manifest.target(),
        "target": target,
        "run_id": record["run_id"],
        "status": record["status"],
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_folder": record.get("run_folder"),
        "thmz_target": record.get("thmz_target"),
        "engine": record.get("engine"),
        "disabled_reason": record.get("disabled_reason"),
        "poll_next": {
            "tool": "get_fairyfly_therm_run",
            "arguments": poll_arguments,
        },
    }
    warnings = list(record.get("warnings", []))
    return {
        "target": target,
        "run_target": target,
        "fairyfly_therm_run_target": target,
        "run_id": record["run_id"],
        "status": record["status"],
        "summary_view": summary,
        "report": make_report(status=report_status, message=message, warnings=warnings),
    }


def write_fairyfly_model_to_thmz(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Write a Garden-backed Fairyfly model to a THERM THMZ artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    run_id = _normalize_run_id(run_id)
    run_dir = _run_dir(garden_root_path, run_id)
    safe_name = slugify_name(name) if name else "model"
    thmz_path = run_dir / f"{safe_name}.thmz"
    model_to_thmz(model, str(thmz_path))
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    target = make_fairyfly_thmz_target(
        garden_id=manifest.garden_id,
        run_id=run_id,
        path=thmz_relative_path,
    )
    model_path = resolved_model_target.get("path")
    source = {
        "run_id": run_id,
        "model_target": resolved_model_target,
        "model_path": model_path,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type="fairyfly_thmz",
        name=f"{run_id}_{safe_name}",
        path=thmz_relative_path,
        source=source,
    )
    manifest.write(garden_root_path)
    return {
        "target": target,
        "thmz_target": target,
        "model_target": resolved_model_target,
        "artifact": artifact,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type="fairyfly_thmz",
            artifact_path=thmz_relative_path,
            absolute_path=str(thmz_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": "written",
            "path": thmz_relative_path,
            "model_target": resolved_model_target,
            "model_path": model_path,
            "artifact": artifact,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly model written to THERM THMZ: {thmz_relative_path}",
        ),
    }


def start_fairyfly_therm_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    silent: bool = True,
) -> dict[str, Any]:
    """Start a Fairyfly THERM run and persist the Garden run ledger."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    run_id = _normalize_run_id(run_id)
    run_dir = _run_dir(garden_root_path, run_id)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    target = make_fairyfly_therm_run_target(manifest.garden_id, run_id)
    model_path = resolved_model_target.get("path")
    engine = therm_engine_config()
    started_at = utc_now_iso()

    if not engine.get("available"):
        disabled_reason = str(engine.get("disabled_reason") or "therm_unavailable")
        record = {
            "run_id": run_id,
            "target": target,
            "recipe": FAIRYFLY_THERM_RECIPE,
            "status": "blocked",
            "created_at": started_at,
            "completed_at": utc_now_iso(),
            "model_target": resolved_model_target,
            "model_path": model_path,
            "run_folder": run_folder,
            "engine": engine,
            "disabled_reason": disabled_reason,
            "warnings": [f"THERM runtime unavailable: {disabled_reason}"],
        }
        _upsert_record(garden_root_path, record)
        return _run_response(
            garden_root=garden_root_path,
            manifest=manifest,
            record=record,
            message="Fairyfly THERM run blocked because THERM is unavailable.",
            report_status="blocked",
        )

    warnings: list[str] = []
    status = "completed"
    thmz_path = run_dir / "model.thmz"
    try:
        model = load_fairyfly_model(garden_root_path, resolved_model_target)
        model_to_thmz(model, str(thmz_path))
        run_thmz(str(thmz_path), silent=silent)
    except Exception as exc:  # pragma: no cover - exercised by real THERM runtime
        status = "failed"
        warnings.append(str(exc))

    thmz_target = None
    thmz_relative_path = None
    if thmz_path.is_file():
        thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
        thmz_target = make_fairyfly_thmz_target(
            garden_id=manifest.garden_id,
            run_id=run_id,
            path=thmz_relative_path,
        )
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "status": status,
        "created_at": started_at,
        "completed_at": utc_now_iso(),
        "model_target": resolved_model_target,
        "model_path": model_path,
        "run_folder": run_folder,
        "thmz_target": thmz_target,
        "thmz_path": thmz_relative_path,
        "engine": engine,
        "warnings": warnings,
    }
    _upsert_record(garden_root_path, record)
    return _run_response(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=(
            "Fairyfly THERM run completed."
            if status == "completed"
            else "Fairyfly THERM run failed; run record was saved."
        ),
        report_status="ok" if status == "completed" else "error",
    )


def get_fairyfly_therm_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Get one Fairyfly THERM run record."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(
        run_target=run_target,
        run_id=run_id,
    )
    record = _public_run(_run_record_by_id(garden_root_path, resolved_run_id))
    return _run_response(
        garden_root=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Fairyfly THERM run returned: {resolved_run_id}",
        report_status="ok" if record.get("status") != "blocked" else "blocked",
    )


def list_fairyfly_therm_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List Fairyfly THERM runs registered in a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    records = [_public_run(record) for record in _read_index(garden_root_path)]
    if status:
        records = [record for record in records if record.get("status") == status]
    return {
        "matches": records,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(records),
            "status": status or "all",
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(records)} Fairyfly THERM run(s).",
        ),
    }
