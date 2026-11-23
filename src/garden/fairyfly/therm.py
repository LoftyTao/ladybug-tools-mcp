"""Fairyfly THERM targets, writing, run ledger, and result parsing services."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import fmean
from typing import Any

from fairyfly_therm.result import THMZResult
from fairyfly_therm.run import run_thmz
from fairyfly_therm.writer import model_to_thmz

from garden.fairyfly.availability import therm_engine_config
from garden.fairyfly.model import load_fairyfly_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.run_ledger import RunLedger, RunManager
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

FAIRYFLY_THERM_RECIPE = "therm"
FAIRYFLY_THMZ_TARGET_TYPE = "fairyfly_thmz"
FAIRYFLY_THERM_RUN_TARGET_TYPE = "fairyfly_therm_run"
FAIRYFLY_THERM_RESULT_TARGET_TYPE = "fairyfly_therm_result"
FAIRYFLY_THERM_DOMAIN = "fairyfly"
FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE = "fairyfly_therm_result"

FAIRYFLY_THERM_RUNS_DIR = Path("runs") / "fairyfly_therm"
FAIRYFLY_THERM_INDEX = FAIRYFLY_THERM_RUNS_DIR / "index.json"
RESULTS_DIR = Path("artifacts") / "fairyfly" / "results"

_DATA_TYPE_ATTRS = {
    "temperature": "temperatures",
    "temperatures": "temperatures",
    "heat_flux": "heat_flux_magnitudes",
    "heat_flux_magnitude": "heat_flux_magnitudes",
    "heat_flux_magnitudes": "heat_flux_magnitudes",
}
_DATA_TYPE_NAMES = {
    "temperatures": "temperature",
    "heat_flux_magnitudes": "heat_flux",
}
_U_FACTOR_FIELDS = (
    "name",
    "delta_temperature",
    "heat_flux",
    "total_u_factor",
    "total_length",
    "projected_x_u_factor",
    "projected_x_length",
    "projected_y_u_factor",
    "projected_y_length",
    "projected_in_glass_plane_u_factor",
    "projected_in_glass_plane_length",
    "custom_rotation_u_factor",
    "custom_rotation_length",
)

_THERM_RUNS = RunManager(
    domain=FAIRYFLY_THERM_DOMAIN,
    target_type=FAIRYFLY_THERM_RUN_TARGET_TYPE,
    runs_dir=FAIRYFLY_THERM_RUNS_DIR,
    default_recipe=FAIRYFLY_THERM_RECIPE,
    allowed_recipes={FAIRYFLY_THERM_RECIPE},
    run_id_prefix="fairyfly_therm",
    missing_message="Provide run_target or run_id.",
    not_found_label="Fairyfly THERM",
    public_fields=(
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
    ),
    ledger=RunLedger(atomic=True, recover_trailing_json=True, sort_by_created_at=True),
)


def make_fairyfly_thmz_target(garden_id: str, run_id: str, path: str) -> dict[str, Any]:
    """Build a Fairyfly THERM THMZ artifact target."""
    return {
        "target_type": FAIRYFLY_THMZ_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "path": path,
    }


def make_fairyfly_therm_run_target(garden_id: str, run_id: str) -> dict[str, Any]:
    """Build a Fairyfly THERM run target."""
    return _THERM_RUNS.make_target(garden_id, run_id)


def make_fairyfly_therm_result_target(
    garden_id: str,
    run_id: str,
    data_type: str,
    path: str,
) -> dict[str, Any]:
    """Build a Fairyfly THERM result target."""
    return {
        "target_type": FAIRYFLY_THERM_RESULT_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": FAIRYFLY_THERM_DOMAIN,
        "recipe": FAIRYFLY_THERM_RECIPE,
        "run_id": run_id,
        "data_type": data_type,
        "path": path,
    }


def make_fairyfly_u_factor_result_target(garden_id: str, run_id: str, path: str) -> dict[str, Any]:
    """Build the U-Factor specialization of a Fairyfly THERM result target."""
    return make_fairyfly_therm_result_target(
        garden_id=garden_id,
        run_id=run_id,
        data_type="u_factors",
        path=path,
    )


def normalize_fairyfly_therm_run_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Fairyfly THERM run target."""
    if not isinstance(value, dict):
        raise ValueError("Fairyfly THERM run target must be a dictionary.")
    if value.get("target_type") != FAIRYFLY_THERM_RUN_TARGET_TYPE:
        raise ValueError("run_target must have target_type 'fairyfly_therm_run'.")
    if value.get("domain") != FAIRYFLY_THERM_DOMAIN:
        raise ValueError("run_target must reference domain 'fairyfly'.")
    if value.get("recipe") != FAIRYFLY_THERM_RECIPE:
        raise ValueError("run_target must reference recipe 'therm'.")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_target requires run_id.")
    return dict(value)


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    return manifest.upsert_artifact(
        {
            "artifact_type": artifact_type,
            "name": name,
            "path": path,
            "source": source,
            "created_at": utc_now_iso(),
        }
    )


def _run_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
    report_status: str = "ok",
) -> dict[str, Any]:
    target = record["target"]
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
            "tool": "FF_Poll_Simulation",
            "arguments": {"garden_root": str(garden_root), "run_target": target},
        },
    }
    return {
        "target": target,
        "run_target": target,
        "fairyfly_therm_run_target": target,
        "run_id": record["run_id"],
        "status": record["status"],
        "summary_view": summary,
        "report": make_report(
            status=report_status,
            message=message,
            warnings=list(record.get("warnings", [])),
        ),
    }


def write_fairyfly_model_to_thmz(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Write a Garden-backed Fairyfly model to a THERM THMZ artifact."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    normalized_run_id = _THERM_RUNS.normalize_run_id(run_id)
    run_dir = _THERM_RUNS.run_dir(garden_root_path, normalized_run_id)
    safe_name = slugify_name(name) if name else "model"
    thmz_path = run_dir / f"{safe_name}.thmz"
    model_to_thmz(model, str(thmz_path))
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    target = make_fairyfly_thmz_target(
        garden_id=manifest.garden_id,
        run_id=normalized_run_id,
        path=thmz_relative_path,
    )
    model_path = resolved_model_target.get("path")
    source = {
        "run_id": normalized_run_id,
        "model_target": resolved_model_target,
        "model_path": model_path,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type="fairyfly_thmz",
        name=f"{normalized_run_id}_{safe_name}",
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
            "run_id": normalized_run_id,
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
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_run_id = _THERM_RUNS.normalize_run_id(run_id)
    run_dir = _THERM_RUNS.run_dir(garden_root_path, normalized_run_id)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    target = make_fairyfly_therm_run_target(manifest.garden_id, normalized_run_id)
    model_path = resolved_model_target.get("path")
    engine = therm_engine_config()
    started_at = utc_now_iso()

    if not engine.get("available"):
        disabled_reason = str(engine.get("disabled_reason") or "therm_unavailable")
        record = {
            "run_id": normalized_run_id,
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
        _THERM_RUNS.upsert(garden_root_path, record)
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
            run_id=normalized_run_id,
            path=thmz_relative_path,
        )
    record = {
        "run_id": normalized_run_id,
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
    _THERM_RUNS.upsert(garden_root_path, record)
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _THERM_RUNS.resolve_run_id(run_target, run_id)
    record = _THERM_RUNS.public_run(_THERM_RUNS.require(garden_root_path, resolved_run_id))
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
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    records = [_THERM_RUNS.public_run(record) for record in _THERM_RUNS.list(garden_root_path)]
    if status:
        records = [record for record in records if record.get("status") == status]
    return {
        "matches": records,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(records),
            "status": status or "all",
        },
        "report": make_report(status="ok", message=f"Found {len(records)} Fairyfly THERM run(s)."),
    }


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"value_count": 0, "minimum": None, "maximum": None, "mean": None}
    return {
        "value_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": fmean(values),
    }


def _normalize_data_type(data_type: str) -> tuple[str, str]:
    key = data_type.strip().lower().replace("-", "_").replace(" ", "_")
    attr = _DATA_TYPE_ATTRS.get(key)
    if attr is None:
        raise ValueError("data_type must be temperature or heat_flux.")
    return _DATA_TYPE_NAMES[attr], attr


def _thmz_path_from_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any],
) -> tuple[Path, str, dict[str, Any]]:
    if thmz_target.get("target_type") != FAIRYFLY_THMZ_TARGET_TYPE:
        raise ValueError("thmz_target must have target_type 'fairyfly_thmz'.")
    if thmz_target.get("garden_id") != manifest.garden_id:
        raise ValueError("thmz_target belongs to a different Garden.")
    path_value = thmz_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("thmz_target requires a Garden-relative path.")
    path = resolve_existing_garden_path(garden_root, path_value, kind="file", label="THERM THMZ file")
    run_id = str(thmz_target.get("run_id") or path.stem)
    return path, run_id, dict(thmz_target)


def _resolve_thmz_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any] | None,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> tuple[Path, str, dict[str, Any] | None]:
    if thmz_target is not None:
        return _thmz_path_from_target(
            garden_root=garden_root, manifest=manifest, thmz_target=thmz_target
        )
    if run_target is None and not run_id:
        raise ValueError("Provide thmz_target, run_target, or run_id.")
    resolved_run_id = _THERM_RUNS.resolve_run_id(run_target, run_id)
    record = _THERM_RUNS.require(garden_root, resolved_run_id)
    thmz_ref = record.get("thmz_target")
    if not isinstance(thmz_ref, dict):
        raise ValueError("Fairyfly run record requires a thmz_target.")
    path, _, resolved_target = _thmz_path_from_target(
        garden_root=garden_root, manifest=manifest, thmz_target=thmz_ref
    )
    return path, resolved_run_id, resolved_target


def _numeric_values(values: Any) -> list[float]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        values = list(values)
    return [float(value) for value in values if value is not None]


def _write_result_payload(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_id: str,
    data_type: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    output_dir = (garden_root / RESULTS_DIR).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{run_id}_{data_type}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    relative_path = to_posix_relative(path, garden_root)
    source = {"run_id": run_id, "data_type": data_type, "thmz_path": payload.get("thmz_path")}
    artifact = _register_artifact(
        manifest,
        artifact_type=FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE,
        name=f"{run_id}_{data_type}",
        path=relative_path,
        source=source,
    )
    manifest.write(garden_root)
    target = make_fairyfly_therm_result_target(
        garden_id=manifest.garden_id,
        run_id=run_id,
        data_type=data_type,
        path=relative_path,
    )
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE,
        artifact_path=relative_path,
        absolute_path=str(path),
        source=source,
    )
    return target, artifact, receipt


def read_fairyfly_therm_result(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    data_type: str = "temperature",
    include_values: bool = False,
) -> dict[str, Any]:
    """Read temperature or heat-flux magnitude results from a THERM THMZ file."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_data_type, attr = _normalize_data_type(data_type)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    values = _numeric_values(getattr(THMZResult(str(thmz_path)), attr))
    stats = _stats(values)
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    if not values:
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "no_results",
                "run_id": resolved_run_id,
                "data_type": normalized_data_type,
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
                **stats,
            },
            "report": make_report(
                status="warning",
                message=(
                    "THERM result values were not found in the THMZ. "
                    "Run THERM first and then read the completed result."
                ),
                warnings=["THERM mesh/results are missing from the THMZ."],
            ),
        }

    payload = {
        "run_id": resolved_run_id,
        "data_type": normalized_data_type,
        "thmz_path": thmz_relative_path,
        "statistics": stats,
        "values": values,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type=normalized_data_type,
        payload=payload,
    )
    response: dict[str, Any] = {
        "target": target,
        "therm_result_target": target,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": normalized_data_type,
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
            "therm_result_target": target,
            **stats,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly THERM {normalized_data_type} result returned.",
        ),
    }
    if include_values:
        response["values"] = values
    return response


def read_fairyfly_u_factor_result(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read U-Factor result summaries from a THERM THMZ file."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    result = THMZResult(str(thmz_path))
    u_factors = [
        {field: getattr(item, field, None) for field in _U_FACTOR_FIELDS}
        for item in (result.u_factors or [])
    ]
    thmz_relative_path = to_posix_relative(thmz_path, garden_root_path)
    if not u_factors:
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "status": "no_results",
                "run_id": resolved_run_id,
                "data_type": "u_factors",
                "result_count": 0,
                "thmz_target": resolved_thmz_target,
                "thmz_path": thmz_relative_path,
            },
            "report": make_report(
                status="warning",
                message=(
                    "THERM U-Factor results were not found in the THMZ. "
                    "Confirm U-Factor tags and run THERM before reading results."
                ),
                warnings=["THERM U-Factor results are missing from the THMZ."],
            ),
        }

    payload = {
        "run_id": resolved_run_id,
        "data_type": "u_factors",
        "thmz_path": thmz_relative_path,
        "result_count": len(u_factors),
        "u_factors": u_factors,
    }
    target, artifact, receipt = _write_result_payload(
        garden_root=garden_root_path,
        manifest=manifest,
        run_id=resolved_run_id,
        data_type="u_factors",
        payload=payload,
    )
    target = make_fairyfly_u_factor_result_target(
        garden_id=manifest.garden_id,
        run_id=resolved_run_id,
        path=target["path"],
    )
    return {
        "target": target,
        "u_factor_result_target": target,
        "u_factors": u_factors,
        "artifact": artifact,
        "artifact_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ok",
            "run_id": resolved_run_id,
            "data_type": "u_factors",
            "result_count": len(u_factors),
            "u_factor_result_target": target,
            "thmz_target": resolved_thmz_target,
            "thmz_path": thmz_relative_path,
        },
        "report": make_report(
            status="ok",
            message=f"Fairyfly THERM U-Factor result returned for {resolved_run_id}.",
        ),
    }
