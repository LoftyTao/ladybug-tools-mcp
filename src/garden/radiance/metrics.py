"""Radiance metric report and honeybee-radiance-postprocess result services."""

from __future__ import annotations

import csv
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from fnmatch import fnmatch
from pathlib import Path
from statistics import mean, median
from typing import Any

from garden.libraries.properties import save_garden_properties_library_object
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.run import (
    _materialize_schedule_values,
    _read_index,
    _reconcile_running_record,
    _run_id_from_target_or_value,
)
from garden.radiance.visual import (
    _validate_run_target_garden,
    list_radiance_grid_results,
    list_radiance_hdr_images,
)
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report


def _import_postprocess() -> dict[str, Any]:
    """Import honeybee_radiance_postprocess while silencing any CuPy banner on stdio."""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        from honeybee_radiance_postprocess.ies.lm import dynamic_schedule_direct_illuminance
        from honeybee_radiance_postprocess.leed.leed import leed_states_schedule
        from honeybee_radiance_postprocess.results.annual_daylight import AnnualDaylight
        from honeybee_radiance_postprocess.results.annual_irradiance import AnnualIrradiance
        from honeybee_radiance_postprocess.results.results import Results
        from honeybee_radiance_postprocess.dynamic import DynamicSchedule

    return {
        "AnnualDaylight": AnnualDaylight,
        "AnnualIrradiance": AnnualIrradiance,
        "Results": Results,
        "DynamicSchedule": DynamicSchedule,
        "lm_states_schedule": dynamic_schedule_direct_illuminance,
        "leed_states_schedule": leed_states_schedule,
    }


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
    "ga": {".ga"},
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
    folder_names_by_metric = {
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
        for metric in (metrics or list(folder_names_by_metric))
    ]
    metric_summaries: dict[str, Any] = {}
    warnings: list[str] = []
    for metric in requested:
        folder_names = folder_names_by_metric.get(metric, (metric,))
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
    ga_folder = _existing_output_root(root, record, "ga")
    if ga_folder is None:
        metrics_root = _existing_output_root(root, record, "metrics")
        ga_folder = metrics_root / "ga" if metrics_root is not None else None
    ga_summary = (
        _metric_folder_summary(ga_folder, metric="ga", include_values=include_values)
        if ga_folder is not None and ga_folder.is_dir()
        else None
    )
    ga_available = bool(ga_summary and ga_summary["sensor_count"])
    warnings: list[str] = []
    if not ga_available:
        warnings.append(
            "Glare autonomy (GA) output was not found in the completed run."
        )
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
                "ga_available": ga_available,
                "ga": ga_summary,
                "available_result_files": [
                    to_posix_relative(path, root)
                    for path in sorted(result_root.rglob("*"))
                    if path.is_file()
                ][:50],
            },
            "report": make_report(
                status="blocked",
                message=message,
                warnings=warnings,
            ),
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
        "ga": ga_summary,
        "ga_available": ga_available,
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
            "ga_available": ga_available,
            "ga": ga_summary,
            "body_returned": False,
        },
        "report": make_report(
            status="ok",
            message="Radiance DGP/glare summary returned.",
            warnings=warnings,
        ),
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


def _numeric_stats(values: list[float], *, include_values: bool) -> dict[str, Any]:
    if not values:
        stats: dict[str, Any] = {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "p10": None,
            "p90": None,
        }
    else:
        ordered = sorted(values)
        n = len(ordered)
        stats = {
            "count": n,
            "min": float(ordered[0]),
            "max": float(ordered[-1]),
            "mean": float(mean(ordered)),
            "median": float(median(ordered)),
            "p10": float(ordered[max(0, min(n - 1, int(0.1 * (n - 1))))]),
            "p90": float(ordered[max(0, min(n - 1, int(0.9 * (n - 1))))]),
        }
    if include_values:
        stats["values"] = [float(v) for v in values]
    return stats


def _find_grid_result_folders(
    garden_root: Path,
    record: dict[str, Any],
    *,
    output_name: str | None = None,
) -> list[tuple[str, Path]]:
    outputs = record.get("outputs") or []
    candidates: list[tuple[str, Path]] = []
    preferred = (
        output_name,
        "results",
        "cumulative-sun-hours",
        "direct-sun-hours",
        "average-irradiance",
        "cumulative-radiation",
        "peak-irradiance",
        "tcp",
        "csp",
        "hsp",
        "condition",
        "temperature",
        "pmv",
        "utci",
    )
    by_name = {
        str(item.get("name")): item
        for item in outputs
        if isinstance(item, dict) and item.get("name") and item.get("path")
    }
    ordered_names: list[str] = [n for n in preferred if n and n in by_name]
    for name in by_name:
        if name not in ordered_names:
            ordered_names.append(name)

    for name in ordered_names:
        if output_name and name != output_name:
            continue
        raw_path = by_name[name]["path"]
        p = (garden_root / str(raw_path)).resolve()
        try:
            p.relative_to(garden_root)
        except ValueError:
            continue
        if p.is_dir():
            candidates.append((name, p))
    return candidates


def summarize_radiance_grid_results(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    output_name: str | None = None,
    grid_filter: str = "*",
    save_report: bool = True,
    include_values: bool = False,
) -> dict[str, Any]:
    """Summarize numeric grid outputs for point-in-time-grid, radiation, sun hours, DF, sky-view, or comfort grids."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)

    folders = _find_grid_result_folders(root, record, output_name=output_name)
    grid_summaries: dict[str, Any] = {}
    selected_output: str | None = None
    for out_name, folder in folders:
        files = sorted(
            item
            for item in folder.rglob("*")
            if item.is_file()
            and item.name not in {"grids_info.json", "vis_metadata.json"}
            and item.suffix.lower() in {".res", ".ill", ".txt", ".csv", ".da", ".cda", ".udi", ".ase", ".ga"}
        )
        if not files:
            continue
        selected_output = out_name
        all_vals: list[float] = []
        for file_path in files:
            grid_name = file_path.stem
            if grid_filter and grid_filter != "*" and not fnmatch(grid_name, grid_filter):
                continue
            vals = _read_numbers(file_path)
            if not vals:
                continue
            all_vals.extend(vals)
            grid_summaries[grid_name] = {
                "file": to_posix_relative(file_path, root),
                "output_name": out_name,
                **_numeric_stats(vals, include_values=include_values),
            }
        if grid_summaries:
            break

    overall = _numeric_stats(
        [
            val
            for item in grid_summaries.values()
            for val in (item.get("values") or [])
        ]
        if include_values
        else [],
        include_values=False,
    )
    if grid_summaries and not include_values:
        # Compute aggregate min/max/mean directly across matching files without keeping all values in memory.
        all_nums: list[float] = []
        for item in grid_summaries.values():
            f = (root / item["file"]).resolve()
            all_nums.extend(_read_numbers(f))
        overall = _numeric_stats(all_nums, include_values=False)

    payload = {
        "target_type": "radiance_grid_summary_report",
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "output_name": selected_output,
        "overall": overall,
        "grids": grid_summaries,
    }
    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "output_name": selected_output,
            "grid_count": len(grid_summaries),
            "overall": overall,
            "grids": grid_summaries,
            "body_returned": False,
        },
        "report": make_report(
            status="ok" if grid_summaries else "blocked",
            message=(
                f"Summarized {len(grid_summaries)} numeric grid result file(s)."
                if grid_summaries
                else "No numeric grid result files were found."
            ),
        ),
    }
    if save_report and grid_summaries:
        target, receipt = _save_report(
            garden_root=root,
            identifier=f"{record.get('run_id')}_grid_summary",
            payload=payload,
            target_type="radiance_grid_summary_report",
        )
        result["target"] = target
        result["persistence_receipt"] = receipt
        result["summary_view"]["target"] = target
    return result


def _load_dynamic_schedule_arg(
    pp: dict[str, Any],
    *,
    garden_root: Path,
    dynamic_schedule: Any,
) -> Any:
    if dynamic_schedule is None:
        return None
    DynamicSchedule = pp["DynamicSchedule"]
    if isinstance(dynamic_schedule, dict):
        if dynamic_schedule.get("target_type") and dynamic_schedule.get("path"):
            p = (garden_root / str(dynamic_schedule["path"])).resolve()
            p.relative_to(garden_root)
            return DynamicSchedule.from_json(str(p))
        return DynamicSchedule.from_dict(dynamic_schedule)
    if isinstance(dynamic_schedule, str):
        p = Path(dynamic_schedule).expanduser()
        if not p.is_absolute():
            p = (garden_root / p).resolve()
        p.relative_to(garden_root)
        return DynamicSchedule.from_json(str(p))
    raise ValueError("dynamic_schedule must be a target, file path, or DynamicSchedule dict.")


def _resolve_results_folder_for_annual(root: Path, record: dict[str, Any]) -> Path:
    for out_name in ("results", "annual-daylight", "annual-irradiance"):
        p = _existing_output_root(root, record, out_name)
        if p is not None and (p / "grids_info.json").is_file():
            return p
    return _results_root(root, record)


def run_annual_postprocess(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    grid_filter: str = "*",
    thresholds: dict[str, Any] | None = None,
    threshold: float = 300.0,
    min_threshold: float = 100.0,
    max_threshold: float = 3000.0,
    target_time: float = 50.0,
    ase_threshold: float = 1000.0,
    ase_occ_hours: int = 250,
    uniformity_threshold: float = 0.5,
    schedule: Any = None,
    dynamic_schedule: Any = None,
    hoys: list[float] | None = None,
    res_type: str = "total",
    mode: str = "auto",
    save_report: bool = True,
    include_values: bool = False,
) -> dict[str, Any]:
    """Run post-hoc honeybee_radiance_postprocess analytics (DA/cDA/UDI/sDA/ASE/uniformity or annual irradiance)."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    results_folder = _resolve_results_folder_for_annual(root, record)

    t_cfg = dict(thresholds or {})
    da_thresh = float(t_cfg.get("threshold", t_cfg.get("da_threshold", threshold)))
    udi_min = float(t_cfg.get("min_threshold", t_cfg.get("udi_min", min_threshold)))
    udi_max = float(t_cfg.get("max_threshold", t_cfg.get("udi_max", max_threshold)))
    sda_time = float(t_cfg.get("target_time", t_cfg.get("sda_target_time", target_time)))
    ase_dir_t = float(t_cfg.get("ase_threshold", ase_threshold))
    ase_hrs = int(t_cfg.get("ase_occ_hours", ase_occ_hours))
    uni_t = float(t_cfg.get("uniformity_threshold", uniformity_threshold))

    pp = _import_postprocess()
    occ_schedule = _materialize_schedule_values(garden_root_path=root, schedule=schedule)
    states = _load_dynamic_schedule_arg(pp, garden_root=root, dynamic_schedule=dynamic_schedule)

    recipe_name = str(record.get("recipe") or "")
    use_irradiance = mode == "irradiance" or (mode == "auto" and "irradiance" in recipe_name)

    grids_out: dict[str, Any] = {}
    if use_irradiance:
        irr = pp["AnnualIrradiance"](str(results_folder), schedule=occ_schedule)
        avg_arrays, peak_arrays, cum_arrays, grids_info = irr.annual_metrics(
            hoys=hoys or [],
            states=states,
            grids_filter=grid_filter,
        )
        for cum, peak, avg, ginfo in zip(cum_arrays, peak_arrays, avg_arrays, grids_info):
            gid = str(ginfo.get("full_id") or ginfo.get("name"))
            grids_out[gid] = {
                "sensor_count": int(len(cum)),
                "cumulative": _numeric_stats([float(v) for v in cum.tolist()], include_values=include_values),
                "peak": _numeric_stats([float(v) for v in peak.tolist()], include_values=include_values),
                "average": _numeric_stats([float(v) for v in avg.tolist()], include_values=include_values),
            }
    else:
        ad = pp["AnnualDaylight"](str(results_folder), schedule=occ_schedule)
        da_list, cda_list, udi_list, udi_lo_list, udi_hi_list, grids_info = ad.annual_metrics(
            threshold=da_thresh,
            min_t=udi_min,
            max_t=udi_max,
            states=states,
            grids_filter=grid_filter,
        )
        sda_vals, _ = ad.spatial_daylight_autonomy(
            threshold=da_thresh,
            target_time=sda_time,
            states=states,
            grids_filter=grid_filter,
        )
        ase_vals, ase_hours_list, _ = ad.annual_sunlight_exposure(
            direct_threshold=ase_dir_t,
            occ_hours=ase_hrs,
            states=states,
            grids_filter=grid_filter,
        )
        try:
            uni_pcts, _, _ = ad.annual_uniformity_ratio(
                threshold=uni_t,
                states=states,
                grids_filter=grid_filter,
            )
        except Exception:
            uni_pcts = [None] * len(grids_info)

        hoy_avg_list = hoy_peak_list = hoy_cum_list = hoy_peak_hoys = None
        if hoys:
            hoy_avg_list, _ = ad.average_values(
                hoys=hoys, states=states, grids_filter=grid_filter, res_type=res_type
            )
            hoy_peak_list, hoy_peak_hoys, _ = ad.peak_values(
                hoys=hoys, states=states, grids_filter=grid_filter, res_type=res_type
            )
            hoy_cum_list, _ = ad.cumulative_values(
                hoys=hoys, states=states, grids_filter=grid_filter, res_type=res_type
            )

        for idx, ginfo in enumerate(grids_info):
            gid = str(ginfo.get("full_id") or ginfo.get("name"))
            entry: dict[str, Any] = {
                "sensor_count": int(len(da_list[idx])),
                "sda": round(float(sda_vals[idx]), 4),
                "ase": round(float(ase_vals[idx]), 4),
                "uniformity_passing_percent": (
                    round(float(uni_pcts[idx]), 4) if uni_pcts[idx] is not None else None
                ),
                "da": _numeric_stats([float(v) for v in da_list[idx].tolist()], include_values=include_values),
                "cda": _numeric_stats([float(v) for v in cda_list[idx].tolist()], include_values=include_values),
                "udi": _numeric_stats([float(v) for v in udi_list[idx].tolist()], include_values=include_values),
                "udi_lower": _numeric_stats([float(v) for v in udi_lo_list[idx].tolist()], include_values=include_values),
                "udi_upper": _numeric_stats([float(v) for v in udi_hi_list[idx].tolist()], include_values=include_values),
                "ase_hours": _numeric_stats([float(v) for v in ase_hours_list[idx].tolist()], include_values=include_values),
            }
            if hoy_avg_list is not None and hoy_peak_list is not None and hoy_cum_list is not None:
                entry["hoy_filtered"] = {
                    "hoy_count": len(hoys or []),
                    "average": _numeric_stats([float(v) for v in hoy_avg_list[idx].tolist()], include_values=include_values),
                    "peak": _numeric_stats([float(v) for v in hoy_peak_list[idx].tolist()], include_values=include_values),
                    "peak_hoy": (
                        float(hoy_peak_hoys[idx])
                        if hoy_peak_hoys is not None and hoy_peak_hoys[idx] is not None
                        else None
                    ),
                    "cumulative": _numeric_stats([float(v) for v in hoy_cum_list[idx].tolist()], include_values=include_values),
                }
            grids_out[gid] = entry

    payload = {
        "target_type": "radiance_annual_postprocess_report",
        "run_id": record.get("run_id"),
        "recipe": recipe_name,
        "mode": "irradiance" if use_irradiance else "daylight",
        "parameters": {
            "threshold": da_thresh,
            "min_threshold": udi_min,
            "max_threshold": udi_max,
            "target_time": sda_time,
            "ase_threshold": ase_dir_t,
            "ase_occ_hours": ase_hrs,
            "uniformity_threshold": uni_t,
            "hoys_count": len(hoys) if hoys else None,
        },
        "grids": grids_out,
    }
    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": recipe_name,
            "mode": payload["mode"],
            "grid_count": len(grids_out),
            "parameters": payload["parameters"],
            "grids": grids_out,
            "body_returned": False,
        },
        "report": make_report(
            status="ok",
            message=f"Computed post-hoc annual postprocess metrics for {len(grids_out)} grid(s).",
        ),
    }
    if save_report:
        target, receipt = _save_report(
            garden_root=root,
            identifier=f"{record.get('run_id')}_annual_postprocess",
            payload=payload,
            target_type="radiance_annual_postprocess_report",
        )
        result["target"] = target
        result["persistence_receipt"] = receipt
        result["summary_view"]["target"] = target
    return result


def export_daylight_control_schedules(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    grid_filter: str = "*",
    schedule: Any = None,
    dynamic_schedule: Any = None,
    ill_setpoint: float = 300.0,
    min_power_in: float = 0.3,
    min_light_out: float = 0.2,
    off_at_min: bool = False,
    identifier_prefix: str | None = None,
    persist_to_garden: bool = True,
) -> dict[str, Any]:
    """Generate 8760 electric-lighting dimming schedules from annual daylight results and persist for EnergyPlus."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    results_folder = _resolve_results_folder_for_annual(root, record)

    pp = _import_postprocess()
    base_sch = _materialize_schedule_values(garden_root_path=root, schedule=schedule)
    states = _load_dynamic_schedule_arg(pp, garden_root=root, dynamic_schedule=dynamic_schedule)
    ad = pp["AnnualDaylight"](str(results_folder), schedule=base_sch)
    schedules_arrays, grids_info = ad.daylight_control_schedules(
        states=states,
        grids_filter=grid_filter,
        base_schedule=base_sch,
        ill_setpoint=float(ill_setpoint),
        min_power_in=float(min_power_in),
        min_light_out=float(min_light_out),
        off_at_min=bool(off_at_min),
    )

    from honeybee_energy.lib.scheduletypelimits import fractional
    from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval

    prefix = slugify_name(identifier_prefix or f"{record.get('run_id')}_dimming")
    schedule_entries: list[dict[str, Any]] = []
    schedule_targets: list[dict[str, Any]] = []
    sch_dir = root / "artifacts" / "radiance" / "schedules"
    sch_dir.mkdir(parents=True, exist_ok=True)

    for arr, ginfo in zip(schedules_arrays, grids_info):
        grid_name = str(ginfo.get("name") or ginfo.get("full_id") or "grid")
        values = [round(float(v), 6) for v in arr.tolist()]
        sch_id = slugify_name(f"{prefix}_{grid_name}")
        csv_path = sch_dir / f"{sch_id}.csv"
        csv_path.write_text("\n".join(str(v) for v in values) + "\n", encoding="utf-8")
        csv_rel = to_posix_relative(csv_path, root)

        entry: dict[str, Any] = {
            "grid_identifier": grid_name,
            "schedule_identifier": sch_id,
            "value_count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": round(mean(values), 6) if values else None,
            "csv_path": csv_rel,
        }
        if persist_to_garden:
            sch_obj = ScheduleFixedInterval(
                sch_id,
                values,
                schedule_type_limit=fractional,
                timestep=1,
            )
            saved = save_garden_properties_library_object(
                garden_root=str(root),
                domain="honeybee_energy",
                object_family="schedule",
                object_dict=sch_obj.to_dict(),
            )
            entry["target"] = saved["target"]
            entry["persistence_receipt"] = saved["persistence_receipt"]
            schedule_targets.append(saved["target"])
        schedule_entries.append(entry)

    return {
        "target": schedule_targets[0] if schedule_targets else None,
        "schedule_targets": schedule_targets,
        "schedules": schedule_entries,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "ill_setpoint": float(ill_setpoint),
            "min_power_in": float(min_power_in),
            "min_light_out": float(min_light_out),
            "off_at_min": bool(off_at_min),
            "schedule_count": len(schedule_entries),
            "schedule_identifiers": [e["schedule_identifier"] for e in schedule_entries],
            "ready_for": "EnergyPlus ScheduleFixedInterval / EP_Create_Program_Type",
        },
        "report": make_report(
            status="ok",
            message=f"Generated {len(schedule_entries)} 8760 daylight control dimming schedule(s).",
        ),
    }


def generate_radiance_dynamic_schedule(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    mode: str = "sensor_maximum",
    grid_filter: str = "*",
    sensor_index: dict[str, list[int]] | None = None,
    maximum: float = 3000.0,
    shade_transmittance: float | dict[str, float] = 0.05,
    use_states: bool = False,
    res_type: str = "total",
) -> dict[str, Any]:
    """Generate dynamic aperture group blind state schedules (sensor_maximum, ies_lm_83, or leed)."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)
    results_folder = _resolve_results_folder_for_annual(root, record)

    normalized_mode = mode.strip().lower().replace("-", "_")
    pp = _import_postprocess()
    ad = pp["AnnualDaylight"](str(results_folder))

    if normalized_mode == "sensor_maximum":
        eff_index = sensor_index
        if eff_index is None:
            eff_index = {
                str(ginfo["full_id"]): [0]
                for ginfo in ad._filter_grids(grids_filter=grid_filter)
            }
        dyn_sch = ad.dynamic_schedule_from_sensor_maximum(
            eff_index,
            grids_filter=grid_filter,
            maximum=float(maximum),
            res_type=res_type,
        )
        extra_meta: dict[str, Any] = {}
    elif normalized_mode in {"ies_lm_83", "lm_83", "lm", "leed"}:
        fn_key = "leed_states_schedule" if normalized_mode == "leed" else "lm_states_schedule"
        raw_sched, fail_to_comply, shd_trans_dict = pp[fn_key](
            ad,
            grids_filter=grid_filter,
            shade_transmittance=shade_transmittance,
            use_states=use_states,
        )
        if isinstance(raw_sched, pp["DynamicSchedule"]):
            dyn_sch = raw_sched
            dyn_payload = dyn_sch.to_dict()
        elif (
            isinstance(raw_sched, dict)
            and raw_sched
            and all(isinstance(v, dict) and "schedule" in v for v in raw_sched.values())
        ):
            dyn_sch = pp["DynamicSchedule"].from_dict(raw_sched)
            dyn_payload = dyn_sch.to_dict()
        else:
            dyn_payload = {
                "type": "TransmittanceScheduleMap",
                "transmittance_schedules": {
                    str(k): [float(v) for v in vals] for k, vals in (raw_sched or {}).items()
                },
            }
        safe_fail: dict[str, Any] = {}
        if isinstance(fail_to_comply, dict):
            for k, v in fail_to_comply.items():
                if hasattr(v, "tolist"):
                    safe_fail[str(k)] = v.tolist()
                elif isinstance(v, (list, tuple)):
                    safe_fail[str(k)] = [int(x) if isinstance(x, (bool, int)) or type(x).__name__.startswith("int") else float(x) for x in v]
                elif isinstance(v, bool):
                    safe_fail[str(k)] = bool(v)
                else:
                    try:
                        safe_fail[str(k)] = int(v)
                    except Exception:
                        safe_fail[str(k)] = str(v)
        safe_shd = {str(k): float(v) for k, v in (shd_trans_dict or {}).items()}
        extra_meta = {
            "fail_to_comply": safe_fail,
            "shade_transmittance": safe_shd,
            "use_states": bool(use_states),
        }
    else:
        raise ValueError("mode must be sensor_maximum, ies_lm_83, or leed.")

    if normalized_mode == "sensor_maximum":
        dyn_payload = dyn_sch.to_dict()

    out_dir = root / "artifacts" / "radiance" / "dynamic_schedules"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_id = slugify_name(f"{record.get('run_id')}_{normalized_mode}")
    out_path = out_dir / f"{safe_id}.json"
    out_path.write_text(json.dumps(dyn_payload, indent=2) + "\n", encoding="utf-8")
    rel_path = to_posix_relative(out_path, root)
    target = {
        "target_type": "radiance_dynamic_schedule",
        "domain": "honeybee_radiance",
        "garden_id": manifest.garden_id,
        "identifier": safe_id,
        "path": rel_path,
    }
    if dyn_payload.get("type") == "TransmittanceScheduleMap" or isinstance(
        dyn_payload.get("transmittance_schedules"), dict
    ):
        group_ids = [str(k) for k in (dyn_payload.get("transmittance_schedules") or {}).keys()]
    elif isinstance(dyn_payload.get("aperture_group_schedules"), list):
        group_ids = [
            str(item.get("group_identifier") or item.get("identifier"))
            for item in dyn_payload["aperture_group_schedules"]
            if isinstance(item, dict)
        ]
    else:
        group_ids = [
            str(k)
            for k, v in dyn_payload.items()
            if isinstance(v, dict) and "schedule" in v
        ]
    return {
        "target": target,
        "dynamic_schedule_target": target,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type="radiance_dynamic_schedule",
            artifact_path=rel_path,
            absolute_path=str(out_path),
            source={"run_id": record.get("run_id"), "mode": normalized_mode},
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": record.get("run_id"),
            "mode": normalized_mode,
            "group_count": len(group_ids),
            "group_identifiers": group_ids,
            **extra_meta,
        },
        "report": make_report(
            status="ok",
            message=f"Generated Radiance dynamic schedule ({normalized_mode}) with {len(group_ids)} group(s).",
        ),
    }


def summarize_comfort_map_metrics(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    save_report: bool = True,
    include_values: bool = False,
) -> dict[str, Any]:
    """Summarize TCP, HSP, CSP, and thermal condition outputs from completed comfort-map runs."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)

    metrics_found: dict[str, Any] = {}
    for metric_name in ("tcp", "hsp", "csp", "temperature", "condition", "pmv", "utci", "degrees-from-neutral"):
        folder = _existing_output_root(root, record, metric_name)
        if folder is None or not folder.is_dir():
            continue
        files = sorted(
            item
            for item in folder.rglob("*")
            if item.is_file() and item.suffix.lower() in {".csv", ".res", ".txt"}
            and item.name not in {"grids_info.json", "vis_metadata.json"}
        )
        if not files:
            continue
        per_grid: dict[str, Any] = {}
        combined: list[float] = []
        for file_path in files:
            vals = _read_numbers(file_path)
            if not vals:
                continue
            combined.extend(vals)
            per_grid[file_path.stem] = _numeric_stats(vals, include_values=include_values)
        if per_grid:
            metrics_found[metric_name.replace("-", "_")] = {
                "overall": _numeric_stats(combined, include_values=False),
                "grids": per_grid,
            }

    payload = {
        "target_type": "radiance_comfort_report",
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "metrics": metrics_found,
    }
    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "metrics": metrics_found,
            "body_returned": False,
        },
        "report": make_report(
            status="ok" if metrics_found else "blocked",
            message=(
                f"Summarized comfort-map outputs ({', '.join(metrics_found)})."
                if metrics_found
                else "No comfort-map output CSV/result files were found."
            ),
        ),
    }
    if save_report and metrics_found:
        target, receipt = _save_report(
            garden_root=root,
            identifier=f"{record.get('run_id')}_comfort_map",
            payload=payload,
            target_type="radiance_comfort_report",
        )
        result["target"] = target
        result["persistence_receipt"] = receipt
        result["summary_view"]["target"] = target
    return result


def list_radiance_run_all_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List raw outputs, grid result folders, and HDR images for a completed Radiance run."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    record = _run_record(root, run_target=run_target, run_id=run_id)
    _validate_run_target_garden(record, manifest)
    _require_completed(record)

    grid_results = list_radiance_grid_results(
        garden_root=garden_root,
        run_target=run_target,
        run_id=run_id,
    )
    hdr_images: list[dict[str, Any]] = []
    if record.get("recipe") == "point-in-time-view":
        hdr_res = list_radiance_hdr_images(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
        )
        hdr_images = hdr_res.get("hdr_images") or []
    outputs = list(record.get("outputs") or [])
    return {
        "outputs": outputs,
        "grid_results": grid_results.get("grids") or [],
        "hdr_images": hdr_images,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": record.get("run_id"),
            "recipe": record.get("recipe"),
            "output_count": len(outputs),
            "grid_folder_count": len(grid_results.get("grids") or []),
            "hdr_image_count": len(hdr_images),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Listed {len(outputs)} output(s), {len(grid_results.get('grids') or [])} "
                f"grid folder(s), and {len(hdr_images)} HDR image(s)."
            ),
        ),
    }
