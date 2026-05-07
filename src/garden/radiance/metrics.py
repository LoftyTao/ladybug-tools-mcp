"""Radiance metric report services."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.run import (
    _read_index,
    _reconcile_running_record,
    _run_id_from_target_or_value,
)
from garden.radiance.visual import _validate_run_target_garden


def _garden_root(root: str) -> Path:
    path = Path(root).expanduser().resolve()
    if not (path / "garden.json").is_file():
        raise ValueError(f"Garden root does not contain garden.json: {root}")
    return path


def _run_record(
    garden_root: Path,
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    resolved_run_id = _run_id_from_target_or_value(
        run_target=run_target,
        run_id=run_id,
    )
    for record in _read_index(garden_root):
        if record.get("run_id") == resolved_run_id:
            return _reconcile_running_record(garden_root_path=garden_root, record=record)
    raise ValueError(f"Radiance run was not found: {resolved_run_id}")


def _require_completed(record: dict[str, Any]) -> None:
    if record.get("status") != "completed":
        raise ValueError("Radiance metric summaries require a completed Radiance run.")


def _output_path(record: dict[str, Any], output_name: str) -> str | None:
    outputs = record.get("outputs") or {}
    if isinstance(outputs, dict):
        value = outputs.get(output_name)
        return str(value) if value else None
    for item in outputs:
        if isinstance(item, dict) and item.get("name") == output_name:
            value = item.get("path")
            return str(value) if value else None
    return None


def _existing_output_root(
    garden_root: Path,
    record: dict[str, Any],
    output_name: str,
) -> Path | None:
    result_path = _output_path(record, output_name)
    if not result_path:
        return None
    path = (garden_root / result_path).resolve()
    path.relative_to(garden_root)
    return path if path.is_dir() else None


def _results_root(garden_root: Path, record: dict[str, Any]) -> Path:
    path = _existing_output_root(garden_root, record, "results")
    if path is None:
        raise ValueError("Radiance run has no results output.")
    if not path.is_dir():
        raise ValueError("Radiance results folder is missing.")
    return path


def _read_numbers(path: Path) -> list[float]:
    values: list[float] = []
    for token in path.read_text(encoding="utf-8").replace(",", " ").split():
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


_METRIC_SUFFIXES = {
    "ase": {".ase"},
    "cda": {".cda"},
    "da": {".da"},
    "sda": {".sda", ".res", ".txt"},
    "udi": {".udi"},
    "udi_lower": {".udi"},
    "udi_upper": {".udi"},
}


def _metric_folder_summary(
    folder: Path,
    *,
    metric: str,
    include_values: bool,
) -> dict[str, Any]:
    allowed_suffixes = _METRIC_SUFFIXES.get(metric)
    files = [
        item
        for item in folder.iterdir()
        if item.is_file()
        and item.name not in {"grids_info.json", "vis_metadata.json"}
        and (allowed_suffixes is None or item.suffix.lower() in allowed_suffixes)
    ]
    values: list[float] = []
    for file_path in files:
        values.extend(_read_numbers(file_path))
    summary: dict[str, Any] = {
        "grid_count": len(files),
        "sensor_count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": mean(values) if values else None,
        "source_files": [file_path.name for file_path in files],
    }
    if include_values:
        summary["values"] = values
    return summary


def _save_report(
    *,
    garden_root: Path,
    identifier: str,
    payload: dict[str, Any],
    target_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    safe_id = slugify_name(identifier)
    path = garden_root / "artifacts" / "radiance" / "metric_reports" / f"{safe_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    target = {
        "target_type": target_type,
        "identifier": safe_id,
        "path": to_posix_relative(path, garden_root),
    }
    return target, {"path": to_posix_relative(path, garden_root), "saved": True}


def summarize_annual_daylight_metrics(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    grid_identifier: str | None = None,
    metrics: list[str] | None = None,
    save_report: bool = True,
    include_values: bool = False,
) -> dict[str, Any]:
    """Summarize completed annual daylight result folders into a compact report."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    result_root = _results_root(root, record)
    metrics_root = _existing_output_root(root, record, "metrics")
    folder_aliases = {
        "da": ("da",),
        "cda": ("cda",),
        "udi": ("udi",),
        "udi_lower": ("udi_lower", "udi-lower"),
        "udi_upper": ("udi_upper", "udi-upper"),
        "ase": ("ase", "ASE"),
        "sda": ("sda", "sDA"),
    }
    requested = [
        metric.strip().lower().replace("-", "_")
        for metric in (metrics or list(folder_aliases))
    ]
    metric_summaries: dict[str, Any] = {}
    warnings: list[str] = []
    for metric in requested:
        folder_names = folder_aliases.get(metric, (metric,))
        folder = next(
            (
                candidate
                for root_candidate in (metrics_root, result_root)
                if root_candidate is not None
                for folder_name in folder_names
                for candidate in [root_candidate / folder_name]
                if candidate.is_dir()
            ),
            None,
        )
        if folder is None:
            warnings.append(
                f"Metric {metric} was not found in completed annual daylight results."
            )
            continue
        metric_summaries[metric] = _metric_folder_summary(
            folder,
            metric=metric,
            include_values=include_values,
        )
    payload = {
        "target_type": "radiance_metric_report",
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "grid_identifier": grid_identifier,
        "metrics": metric_summaries,
        "warnings": warnings,
        "provenance": {"results_path": to_posix_relative(result_root, root)},
    }
    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "metrics": metric_summaries,
            "warnings": warnings,
            "body_returned": False,
        },
        "report": make_report(
            status="ok" if metric_summaries else "blocked",
            message=(
                "Annual daylight metric summary returned."
                if metric_summaries
                else "No requested annual daylight metrics were found."
            ),
            warnings=warnings,
        ),
    }
    if save_report:
        target, receipt = _save_report(
            garden_root=root,
            identifier=f"{record.get('run_id')}_annual_daylight_metrics",
            payload=payload,
            target_type="radiance_metric_report",
        )
        result["target"] = target
        result["radiance_metric_report_target"] = target
        result["persistence_receipt"] = receipt
        result["summary_view"]["target"] = target
    return result


def _find_dgp_files(results_root: Path) -> list[Path]:
    return sorted(
        path
        for path in results_root.rglob("*")
        if path.is_file()
        and (
            path.suffix.lower() == ".dgp"
            or (
                path.suffix.lower() in {".ill", ".txt", ".res"}
                and "dgp" in path.name.lower()
            )
        )
    )


def summarize_radiance_glare_metrics(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    view_identifier: str | None = None,
    dgp_threshold: float = 0.4,
    save_report: bool = True,
    include_values: bool = False,
) -> dict[str, Any]:
    """Summarize DGP result files, blocking image-only glare claims."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    result_root = _results_root(root, record)
    dgp_files = _find_dgp_files(result_root)
    values: list[float] = []
    for file_path in dgp_files:
        values.extend(_read_numbers(file_path))
    if not values:
        message = (
            "No DGP result data found. HDR, GIF, and falsecolor outputs are "
            "qualitative glare-risk evidence only."
        )
        return {
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": record.get("run_id"),
                "recipe": record.get("recipe"),
                "view_identifier": view_identifier,
                "dgp_available": False,
                "available_result_files": [
                    to_posix_relative(path, root)
                    for path in sorted(result_root.rglob("*"))
                    if path.is_file()
                ][:50],
            },
            "report": make_report(status="blocked", message=message),
        }
    exceedance_count = sum(1 for value in values if value > dgp_threshold)
    dgp: dict[str, Any] = {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
        "threshold": dgp_threshold,
        "exceedance_count": exceedance_count,
        "exceedance_fraction": exceedance_count / len(values),
        "source_files": [to_posix_relative(path, root) for path in dgp_files],
    }
    if include_values:
        dgp["values"] = values
    payload = {
        "target_type": "radiance_glare_report",
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "view_identifier": view_identifier,
        "dgp": dgp,
        "provenance": {"results_path": to_posix_relative(result_root, root)},
    }
    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "view_identifier": view_identifier,
            "dgp_available": True,
            "dgp": dgp,
            "body_returned": False,
        },
        "report": make_report(status="ok", message="Radiance DGP/glare summary returned."),
    }
    if save_report:
        target, receipt = _save_report(
            garden_root=root,
            identifier=f"{record.get('run_id')}_glare_metrics",
            payload=payload,
            target_type="radiance_glare_report",
        )
        result["target"] = target
        result["radiance_glare_report_target"] = target
        result["persistence_receipt"] = receipt
        result["summary_view"]["target"] = target
    return result
