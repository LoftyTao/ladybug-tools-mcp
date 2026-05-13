"""Fairyfly THERM result parsing services."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import fmean
from typing import Any

from fairyfly_therm.result import THMZResult

from garden.fairyfly.targets import (
    FAIRYFLY_THMZ_TARGET_TYPE,
    make_fairyfly_therm_result_target,
    make_fairyfly_u_factor_result_target,
    normalize_fairyfly_therm_run_target,
)
from garden.fairyfly.therm import FAIRYFLY_THERM_INDEX
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

FAIRYFLY_THERM_RESULT_ARTIFACT_TYPE = "fairyfly_therm_result"
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


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "value_count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "value_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": fmean(values),
    }


def _read_run_index(garden_root: Path) -> list[dict[str, Any]]:
    path = garden_root / FAIRYFLY_THERM_INDEX
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("runs", []))


def _run_record(garden_root: Path, run_id: str) -> dict[str, Any]:
    for record in _read_run_index(garden_root):
        if record.get("run_id") == run_id:
            return record
    raise ValueError(f"Fairyfly THERM run was not found: {run_id}")


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


def _normalize_data_type(data_type: str) -> tuple[str, str]:
    key = data_type.strip().lower().replace("-", "_").replace(" ", "_")
    attr = _DATA_TYPE_ATTRS.get(key)
    if attr is None:
        raise ValueError("data_type must be temperature or heat_flux.")
    return _DATA_TYPE_NAMES[attr], attr


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str | None:
    if run_target is not None:
        return str(normalize_fairyfly_therm_run_target(run_target)["run_id"])
    if run_id:
        return str(run_id)
    return None


def _thmz_path_from_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    thmz_target: dict[str, Any],
) -> tuple[Path, str, dict[str, Any]]:
    if thmz_target.get("target_type") != FAIRYFLY_THMZ_TARGET_TYPE:
        raise ValueError("thmz_target must have target_type 'fairyfly_thmz'.")
    garden_id = thmz_target.get("garden_id")
    if garden_id and garden_id != manifest.garden_id:
        raise ValueError("thmz_target belongs to a different Garden.")
    path_value = thmz_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("thmz_target requires a Garden-relative path.")
    path = (garden_root / path_value).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError(f"THERM THMZ file was not found: {path_value}")
    run_id = str(thmz_target.get("run_id") or path.stem)
    return path, run_id, dict(thmz_target)


def _thmz_path_from_run(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    run_id: str,
) -> tuple[Path, dict[str, Any] | None]:
    record = _run_record(garden_root, run_id)
    thmz_target = record.get("thmz_target")
    path_value = None
    if isinstance(thmz_target, dict):
        path_value = thmz_target.get("path")
    if path_value is None:
        path_value = record.get("thmz_path")
    if not isinstance(path_value, str) or not path_value:
        path_value = f"runs/fairyfly_therm/{run_id}/model.thmz"
    path = (garden_root / path_value).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError(f"THERM THMZ file was not found for run: {run_id}")
    if isinstance(thmz_target, dict):
        return path, thmz_target
    return path, None


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
            garden_root=garden_root,
            manifest=manifest,
            thmz_target=thmz_target,
        )
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    if not resolved_run_id:
        raise ValueError("Provide thmz_target, run_target, or run_id.")
    path, resolved_thmz_target = _thmz_path_from_run(
        garden_root=garden_root,
        manifest=manifest,
        run_id=resolved_run_id,
    )
    return path, resolved_run_id, resolved_thmz_target


def _numeric_values(values: Any) -> list[float]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        values = list(values)
    numeric: list[float] = []
    for value in values:
        if value is None:
            continue
        numeric.append(float(value))
    return numeric


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
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    relative_path = to_posix_relative(path, garden_root)
    source = {
        "run_id": run_id,
        "data_type": data_type,
        "thmz_path": payload.get("thmz_path"),
    }
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
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_data_type, attr = _normalize_data_type(data_type)
    thmz_path, resolved_run_id, resolved_thmz_target = _resolve_thmz_path(
        garden_root=garden_root_path,
        manifest=manifest,
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
    )
    result = THMZResult(str(thmz_path))
    values = _numeric_values(getattr(result, attr))
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
    response = {
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


def _serialize_u_factor(value: Any) -> dict[str, Any]:
    return {field: getattr(value, field, None) for field in _U_FACTOR_FIELDS}


def read_fairyfly_u_factor_result(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read U-Factor result summaries from a THERM THMZ file."""
    garden_root_path = _garden_root(garden_root)
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
        _serialize_u_factor(item) for item in (result.u_factors or [])
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
