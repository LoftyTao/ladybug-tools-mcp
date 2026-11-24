"""Energy simulation result reading and visualization services."""

from __future__ import annotations

import html
from pathlib import Path
import sqlite3
from statistics import mean
from typing import Any

from honeybee.model import Model
from honeybee_energy.result.match import match_faces_to_data, match_rooms_to_data
from honeybee_energy.result.osw import OSW
from honeybee_energy.result.rdd import RDD
from honeybee_energy.result.zsz import ZSZ
import ladybug_vtk._extend_visualization_set  # noqa: F401
from ladybug.hourlyplot import HourlyPlot
from ladybug.monthlychart import MonthlyChart
from ladybug.sql import SQLiteResult
from ladybug_display.extension.hourlyplot import hourly_plot_to_vis_set
from ladybug_display.extension.monthlychart import monthly_chart_to_vis_set

from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report
from garden.data_collection import save_data_collection
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.run_energy.annual import (
    _absolute_output_path,
    _outputs_map,
    _run_id_from_target_or_value,
    _run_record_by_id,
)
from garden.run_energy.output_requests import read_energy_output_request

HOURLY_PLOT_HTML_ARTIFACT_TYPE = "energy_result_hourly_plot_html"
MONTHLY_CHART_HTML_ARTIFACT_TYPE = "energy_result_monthly_chart_html"

_MONTHLY_CHART_TIME_INTERVALS = {
    "as_is",
    "hourly",
    "daily",
    "monthly",
    "monthly_per_hour",
    "total_daily",
    "total_monthly",
    "total_monthly_per_hour",
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _sql_result(
    *,
    garden_root: Path,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> tuple[str, Path, Any, dict[str, Any]]:
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root, resolved_run_id)
    sql_path = _absolute_output_path(garden_root, record, "sql")
    return resolved_run_id, sql_path, SQLiteResult(str(sql_path)), record


def _header_value(header: Any, attr: str) -> Any:
    value = getattr(header, attr, None)
    if attr == "data_type" and value is not None:
        return getattr(value, "name", str(value))
    return value


def _value_name(value: Any) -> Any:
    if value is None:
        return None
    return getattr(value, "name", str(value))


def _normalize_output_info(
    info: dict[str, Any] | None,
    *,
    output_name: str,
) -> dict[str, Any]:
    info = dict(info or {})
    return {
        "output_name": str(info.get("output_name") or output_name),
        "object_type": _value_name(info.get("object_type")),
        "unit": _value_name(info.get("unit", info.get("units"))),
        "data_type": _value_name(info.get("data_type")),
    }


def _available_output_infos(
    *,
    available_outputs: list[Any],
    available_outputs_info: list[Any],
) -> list[dict[str, Any]]:
    infos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in available_outputs_info:
        if not isinstance(item, dict):
            continue
        output_name = str(item.get("output_name") or "")
        if not output_name:
            continue
        infos.append(_normalize_output_info(item, output_name=output_name))
        seen.add(output_name)
    for output_name in available_outputs:
        name = str(output_name)
        if name not in seen:
            infos.append(_normalize_output_info(None, output_name=name))
    return infos


def _matches_text(value: Any, expected: str | None, *, substring: bool) -> bool:
    if expected is None:
        return True
    actual = str(value or "").lower()
    expected_value = expected.strip().lower()
    if not expected_value:
        return True
    if substring:
        normalized = (
            expected_value.replace("/", " ")
            .replace(",", " ")
            .replace(" and ", " ")
            .replace(" or ", " ")
        )
        tokens = [token for token in normalized.split() if token]
        if set(tokens) == {"heating", "cooling"}:
            return "heating" in actual or "cooling" in actual
    return expected_value in actual if substring else actual == expected_value


def _matches_output_filters(
    info: dict[str, Any],
    *,
    output_query: str | None,
    unit: str | None,
    data_type: str | None,
    object_type: str | None,
) -> bool:
    return (
        _matches_text(info.get("output_name"), output_query, substring=True)
        and _matches_text(info.get("unit"), unit, substring=False)
        and _matches_text(info.get("data_type"), data_type, substring=False)
        and _matches_text(info.get("object_type"), object_type, substring=True)
    )


def _output_request_summary(
    *,
    garden_root: Path,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    target = record.get("output_request_target")
    if not isinstance(target, dict):
        return None
    payload = read_energy_output_request(
        garden_root=garden_root,
        output_request_target=target,
    )
    simulation_output = dict(payload.get("simulation_output") or {})
    outputs = list(simulation_output.get("outputs", []) or [])
    summary_reports = list(simulation_output.get("summary_reports", []) or [])
    return {
        "target": payload.get("target") or target,
        "identifier": payload.get("identifier") or target.get("identifier"),
        "path": target.get("path"),
        "presets": list(payload.get("presets", []) or []),
        "custom_outputs": list(payload.get("custom_outputs", []) or []),
        "reporting_frequency": simulation_output.get("reporting_frequency"),
        "include_sqlite": simulation_output.get("include_sqlite", True),
        "include_html": simulation_output.get("include_html", True),
        "summary_reports": summary_reports,
        "output_count": len(outputs),
        "outputs_preview": outputs[:20],
        "custom_output_count": len(payload.get("custom_outputs", []) or []),
    }


def _run_context(record: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "run_id",
        "recipe",
        "status",
        "created_at",
        "completed_at",
        "run_folder",
        "units",
        "workers",
        "model_target",
        "weather_target",
        "sim_par_path",
        "output_request_target",
    ]
    return {key: record.get(key) for key in keys if key in record}


def _requested_by(
    output_name: str,
    output_request: dict[str, Any] | None,
) -> str | None:
    if output_request is None:
        return None
    if output_name in set(output_request.get("custom_outputs") or []):
        return "custom_output"
    if output_name in set(output_request.get("outputs_preview") or []):
        return "output_request"
    return None


def _output_parameter(
    *,
    output_name: str,
    output_info: dict[str, Any],
    output_request: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "name": output_name,
        "reporting_frequency": (
            output_request.get("reporting_frequency")
            if output_request is not None
            else None
        ),
        "unit": output_info.get("unit"),
        "data_type": output_info.get("data_type"),
        "object_type": output_info.get("object_type"),
        "requested_by": _requested_by(output_name, output_request),
    }


def _data_collection_name(collection: Any, default_name: str) -> str:
    if hasattr(collection, "ToString"):
        try:
            value = str(collection.ToString()).strip()
            if value and "\n" not in value:
                return value
        except Exception:
            pass
    return default_name


def _data_collection_identifier(
    *,
    run_id: str,
    output_name: str,
    collection_index: int,
) -> str:
    return f"{run_id}_{output_name}_{collection_index}"


def _collection_summary(
    collection: Any,
    *,
    output_name: str,
    include_values: bool,
    max_values: int,
    output_parameter: dict[str, Any] | None = None,
    result_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = list(getattr(collection, "values", []) or [])
    header = getattr(collection, "header", None)
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    summary: dict[str, Any] = {
        "name": _data_collection_name(collection, output_name),
        "output_name": output_name,
        "collection_type": type(collection).__name__,
        "data_type": _header_value(header, "data_type") if header is not None else None,
        "unit": _header_value(header, "unit") if header is not None else None,
        "metadata": (
            dict(getattr(header, "metadata", {}) or {}) if header is not None else {}
        ),
        "value_count": len(values),
        "minimum": min(numeric_values) if numeric_values else None,
        "maximum": max(numeric_values) if numeric_values else None,
        "mean": mean(numeric_values) if numeric_values else None,
    }
    if output_parameter is not None:
        summary["output_parameter"] = output_parameter
    if result_context is not None:
        summary["result_context"] = result_context
    analysis_period = (
        getattr(header, "analysis_period", None) if header is not None else None
    )
    time_interval = _collection_time_interval(collection)
    summary["time_interval"] = time_interval
    summary["time_interval_guidance"] = _time_interval_guidance(
        time_interval,
        data_type=summary.get("data_type"),
    )
    if analysis_period is not None:
        timestep = getattr(analysis_period, "timestep", None)
        summary["analysis_period"] = {
            "timestep": timestep,
            "is_annual": getattr(analysis_period, "is_annual", None),
        }
        if isinstance(timestep, (int, float)) and timestep > 0:
            summary["analysis_period"]["effective_interval_minutes"] = 60 / timestep
        if isinstance(timestep, (int, float)) and timestep > 1:
            summary["time_interval_guidance"] = (
                f"{summary['time_interval_guidance']} analysis_period.timestep="
                f"{timestep} means sub-hourly timestep values."
            )
    if include_values:
        visible_values = values[:max_values]
        summary["values"] = visible_values
        summary["values_truncated"] = len(values) > len(visible_values)
    return summary


def _data_collections(
    sql: Any, output_name: str, run_period_index: int | None
) -> list[Any]:
    if run_period_index is None:
        return list(sql.data_collections_by_output_name(output_name))
    return list(
        sql.data_collections_by_output_name_run_period(output_name, run_period_index)
    )


def _available_output_name_message(sql: Any, *, limit: int = 12) -> str:
    names = [str(name) for name in (getattr(sql, "available_outputs", []) or []) if name]
    if not names:
        return "Call EP_Read_Result_Data without output_name to inspect available SQL outputs."
    preview = "; ".join(names[:limit])
    suffix = "" if len(names) <= limit else f"; ... ({len(names)} total)"
    return f"Available output names include: {preview}{suffix}."


def _collection_time_interval(collection: Any) -> str:
    name = type(collection).__name__.lower()
    if "monthlyperhour" in name:
        return "monthly_per_hour"
    if "monthly" in name:
        return "monthly"
    if "daily" in name:
        return "daily"
    if "hourly" in name:
        return "hourly"
    return name or "unknown"


def _time_interval_guidance(time_interval: str, *, data_type: str | None = None) -> str:
    interval = str(time_interval or "").strip().lower()
    is_energy = str(data_type or "").strip().lower() == "energy"
    if interval == "monthly":
        if is_energy:
            return (
                "monthly means a monthly average for this Energy DataCollection; "
                "use total_monthly when the user asks for monthly total energy or load."
            )
        return "monthly means a monthly average; use total_monthly for monthly totals."
    if interval == "total_monthly":
        return "total_monthly means a monthly total for each series."
    if interval == "hourly":
        return (
            "hourly reflects the DataCollection interval; check analysis_period.timestep "
            "to distinguish one value per hour from sub-hourly timestep values."
        )
    return f"{interval or 'unknown'} DataCollection interval."


def _result_data_next_step_guidance(
    collections_by_output: list[dict[str, Any]],
) -> str | None:
    truncated = [item for item in collections_by_output if item["collections_truncated"]]
    if not truncated:
        return None
    outputs = ", ".join(str(item["output_name"]) for item in truncated[:5])
    return (
        "collections_truncated=true for one or more outputs. Reuse the existing "
        "collection_count, returned_collection_count, and collections_truncated "
        "fields; increase max_collections or narrow filters before charting all "
        f"zones. Truncated outputs include: {outputs}."
    )


def _transform_collection(collection: Any, time_interval: str) -> Any:
    interval = time_interval.strip().lower()
    if interval not in _MONTHLY_CHART_TIME_INTERVALS:
        allowed = ", ".join(sorted(_MONTHLY_CHART_TIME_INTERVALS))
        raise ValueError(
            f"Unsupported time_interval: {time_interval}. Allowed: {allowed}."
        )
    if interval == "as_is":
        return (
            collection.duplicate() if hasattr(collection, "duplicate") else collection
        )

    current = _collection_time_interval(collection)
    if interval == current:
        return (
            collection.duplicate() if hasattr(collection, "duplicate") else collection
        )
    method_by_interval = {
        "daily": "average_daily",
        "monthly": "average_monthly",
        "monthly_per_hour": "average_monthly_per_hour",
        "total_daily": "total_daily",
        "total_monthly": "total_monthly",
        "total_monthly_per_hour": "total_monthly_per_hour",
    }
    method_name = method_by_interval.get(interval)
    if method_name is None:
        raise ValueError(f"Cannot transform {current} DataCollection to {interval}.")
    if not hasattr(collection, method_name):
        raise ValueError(f"{type(collection).__name__} does not support {method_name}.")
    return getattr(collection, method_name)()


def read_energy_result_data(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    output_name: str | None = None,
    output_names: list[str] | None = None,
    output_query: str | None = None,
    unit: str | None = None,
    data_type: str | None = None,
    object_type: str | None = None,
    run_period_index: int | None = None,
    include_values: bool = False,
    max_values: int = 24,
    max_collections: int = 10,
    max_outputs: int = 25,
    save_data_collections: bool = False,
    match_to: str = "none",
    model_target: dict[str, Any] | None = None,
    invert_multiplier: bool = False,
    space_based: bool = False,
    zone_correct_mult: bool = True,
) -> dict[str, Any]:
    """Read EnergyPlus SQL output into compact Ladybug DataCollection summaries."""
    if max_values < 0:
        raise ValueError("max_values must be zero or greater.")
    if max_collections <= 0:
        raise ValueError("max_collections must be positive.")
    if max_outputs <= 0:
        raise ValueError("max_outputs must be positive.")
    match_mode = str(match_to or "none").strip().lower().replace("-", "_")
    if match_mode not in {"none", "rooms", "faces", "auto"}:
        raise ValueError("match_to must be one of: none, rooms, faces, auto.")
    if output_name is not None and output_names is not None:
        raise ValueError("Provide only one of output_name or output_names.")
    exact_output_names = (
        [output_name]
        if output_name is not None
        else [str(name) for name in (output_names or [])]
    )
    if output_names is not None and not exact_output_names:
        raise ValueError("output_names must include at least one output name.")
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id, sql_path, sql, record = _sql_result(
        garden_root=garden_root_path,
        run_target=run_target,
        run_id=run_id,
    )
    available_outputs = list(getattr(sql, "available_outputs", []) or [])
    available_outputs_info = _available_output_infos(
        available_outputs=available_outputs,
        available_outputs_info=list(getattr(sql, "available_outputs_info", []) or []),
    )
    output_info_by_name = {
        str(item["output_name"]): item for item in available_outputs_info
    }
    filters = {
        "output_query": output_query,
        "unit": unit,
        "data_type": data_type,
        "object_type": object_type,
    }
    has_filters = any(value is not None for value in filters.values())
    if exact_output_names:
        requested_output_names = exact_output_names
    elif has_filters:
        requested_output_names = [
            item["output_name"]
            for item in available_outputs_info
            if _matches_output_filters(
                item,
                output_query=output_query,
                unit=unit,
                data_type=data_type,
                object_type=object_type,
            )
        ][:max_outputs]
        if not requested_output_names:
            raise ValueError("No Energy SQL outputs matched the requested filters.")
    else:
        requested_output_names = []
    output_request = _output_request_summary(
        garden_root=garden_root_path,
        record=record,
    )
    selected_outputs = []
    for name in requested_output_names:
        info = _normalize_output_info(output_info_by_name.get(name), output_name=name)
        info["requested_by"] = _requested_by(name, output_request)
        selected_outputs.append(info)
    result_context = {
        "run": _run_context(record),
        "sql": {
            "path": to_posix_relative(sql_path, garden_root_path),
            "size_bytes": sql_path.stat().st_size if sql_path.is_file() else None,
        },
        "output_request": output_request,
        "filters": filters,
        "selected_outputs": selected_outputs,
    }
    if not requested_output_names:
        return {
            "data_collections": [],
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": resolved_run_id,
                "sql_path": to_posix_relative(sql_path, garden_root_path),
                "result_context": result_context,
                "available_output_count": len(available_outputs),
                "available_outputs_preview": available_outputs[:50],
            },
            "available_outputs": available_outputs,
            "available_outputs_info": available_outputs_info[:100],
            "report": make_report(
                status="ok",
                message=f"Energy SQL output inventory returned for run {resolved_run_id}.",
            ),
        }

    summaries: list[dict[str, Any]] = []
    data_collection_targets: list[dict[str, Any]] = []
    data_collection_receipts: list[dict[str, Any]] = []
    total_collection_count = 0
    collections_by_output: list[dict[str, Any]] = []
    all_collections_by_output: dict[str, list[Any]] = {}
    for current_output_name in requested_output_names:
        collections = _data_collections(sql, current_output_name, run_period_index)
        all_collections_by_output[current_output_name] = collections
        visible_collections = collections[:max_collections]
        total_collection_count += len(collections)
        collections_by_output.append(
            {
                "output_name": current_output_name,
                "collection_count": len(collections),
                "returned_collection_count": len(visible_collections),
                "collections_truncated": len(collections) > len(visible_collections),
            }
        )
        for collection_index, collection in enumerate(visible_collections):
            output_info = _normalize_output_info(
                output_info_by_name.get(current_output_name),
                output_name=current_output_name,
            )
            parameter = _output_parameter(
                output_name=current_output_name,
                output_info=output_info,
                output_request=output_request,
            )
            summary = _collection_summary(
                collection,
                output_name=current_output_name,
                include_values=include_values,
                max_values=max_values,
                output_parameter=parameter,
                result_context={
                    "run_id": resolved_run_id,
                    "sql_path": to_posix_relative(sql_path, garden_root_path),
                    "run_period_index": run_period_index,
                    "collection_index": collection_index,
                    "output_request_identifier": (
                        output_request.get("identifier")
                        if output_request is not None
                        else None
                    ),
                },
            )
            if save_data_collections:
                saved = save_data_collection(
                    garden_root=garden_root_path,
                    data_collection=collection,
                    identifier=_data_collection_identifier(
                        run_id=resolved_run_id,
                        output_name=current_output_name,
                        collection_index=collection_index,
                    ),
                    source={
                        "producer": "read_energy_result_data",
                        "run_id": resolved_run_id,
                        "sql_path": to_posix_relative(sql_path, garden_root_path),
                        "output_name": current_output_name,
                        "run_period_index": run_period_index,
                        "collection_index": collection_index,
                        "output_request_identifier": (
                            output_request.get("identifier")
                            if output_request is not None
                            else None
                        ),
                        "output_parameter": parameter,
                    },
                )
                summary["target"] = saved["target"]
                summary["data_collection_target"] = saved["target"]
                summary["data_target"] = saved["target"]
                summary["data_persistence_receipt"] = saved["persistence_receipt"]
                data_collection_targets.append(saved["target"])
                data_collection_receipts.append(saved["persistence_receipt"])
            summaries.append(summary)

    response: dict[str, Any] = {
        "data_collections": summaries,
        "data_collection_targets": data_collection_targets,
        "data_collection_persistence_receipts": data_collection_receipts,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "sql_path": to_posix_relative(sql_path, garden_root_path),
            "output_name": output_name,
            "output_names": requested_output_names,
            "run_period_index": run_period_index,
            "result_context": result_context,
            "collection_count": total_collection_count,
            "returned_collection_count": len(summaries),
            "collections_truncated": any(
                item["collections_truncated"] for item in collections_by_output
            ),
            "collections_by_output": collections_by_output,
            "next_step_guidance": _result_data_next_step_guidance(
                collections_by_output
            ),
            "saved_data_collection_count": len(data_collection_targets),
            "first_data_collection_target": (
                data_collection_targets[0] if data_collection_targets else None
            ),
            "data_collection_targets": data_collection_targets,
        },
        "report": make_report(
            status="ok",
            message=(
                f"Energy DataCollection summaries returned for run {resolved_run_id}."
            ),
        ),
    }
    if match_mode != "none":
        matched_payload = _attach_geometry_matches(
            garden_root_path=garden_root_path,
            record=record,
            run_id=resolved_run_id,
            sql_path=sql_path,
            collections_by_output=all_collections_by_output,
            match_mode=match_mode,
            model_target=model_target,
            invert_multiplier=invert_multiplier,
            space_based=space_based,
            zone_correct_mult=zone_correct_mult,
            include_values=include_values,
            max_values=max_values,
            max_collections=max_collections,
            save_data_collections=save_data_collections,
        )
        response["geometry_matches"] = matched_payload
        response["summary_view"]["geometry_matches"] = {
            "match_mode": matched_payload["match_mode"],
            "model_identifier": matched_payload.get("model_identifier"),
            "matched_room_count": matched_payload["matched_room_count"],
            "matched_face_count": matched_payload["matched_face_count"],
            "matched_data_collection_targets": matched_payload[
                "matched_data_collection_targets"
            ],
        }
    return response


def _inject_html_legend(
    html_path: Path,
    *,
    title: str,
    labels: list[str],
) -> None:
    if not labels:
        return
    colors = [
        "#2f6fbb",
        "#d55e00",
        "#009e73",
        "#cc79a7",
        "#f0ad00",
        "#56b4e9",
        "#6f4bb2",
        "#7a7a7a",
    ]
    items = "\n".join(
        (
            '<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<span style="width:12px;height:12px;background:{colors[index % len(colors)]};'
            'display:inline-block;border-radius:2px;"></span>'
            f"<span>{html.escape(label)}</span></div>"
        )
        for index, label in enumerate(labels)
    )
    overlay = (
        '<div id="lbt-mcp-series-legend" style="position:fixed;right:16px;top:16px;'
        "z-index:9999;background:rgba(255,255,255,0.92);border:1px solid #c9c9c9;"
        "border-radius:4px;padding:10px 12px;font-family:Arial,sans-serif;"
        'font-size:12px;line-height:1.35;color:#222;max-width:280px;">'
        f'<div style="font-weight:600;margin-bottom:6px;">{html.escape(title)}</div>'
        f"{items}</div>"
    )
    text = html_path.read_text(encoding="utf-8", errors="replace")
    if "</body>" in text:
        text = text.replace("</body>", overlay + "\n</body>", 1)
    else:
        text += "\n" + overlay
    html_path.write_text(text, encoding="utf-8")


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
    return manifest.upsert_artifact(record)


def energy_result_hourly_plot_to_html(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    output_name: str,
    collection_index: int = 0,
    name: str = "energy_result_hourly_plot",
    output_subdir: str = "artifacts/energy/results/html",
) -> dict[str, Any]:
    """Export one Energy SQL DataCollection as an HourlyPlot HTML artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id, sql_path, sql, _record = _sql_result(
        garden_root=garden_root_path,
        run_target=run_target,
        run_id=run_id,
    )
    collections = _data_collections(sql, output_name, None)
    if not collections:
        raise ValueError(
            f"No DataCollections found for output: {output_name}. "
            f"{_available_output_name_message(sql)}"
        )
    if collection_index < 0 or collection_index >= len(collections):
        raise ValueError(
            "collection_index is outside the returned DataCollection range."
        )
    collection = collections[collection_index]
    collection_summary = _collection_summary(
        collection,
        output_name=output_name,
        include_values=True,
        max_values=24,
    )
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify_name(name)
    html_path = output_dir / f"{safe_name}.html"
    try:
        hourly_plot = HourlyPlot(collection)
        vis_set = hourly_plot_to_vis_set(hourly_plot)
        exported = Path(
            vis_set.to_html(
                output_folder=str(output_dir),
                file_name=safe_name,
                open=False,
            )
        ).resolve()
        html_path = exported
    except Exception as exc:
        raise ValueError(f"Ladybug HourlyPlot export failed: {exc}") from exc

    html_path.relative_to(garden_root_path)
    artifact_path = to_posix_relative(html_path, garden_root_path)
    source = {
        "run_id": resolved_run_id,
        "sql_path": to_posix_relative(sql_path, garden_root_path),
        "output_name": output_name,
        "collection_index": collection_index,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=HOURLY_PLOT_HTML_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)
    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=HOURLY_PLOT_HTML_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(html_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": html_path.is_file(),
            "data_collection": collection_summary,
        },
        "report": make_report(
            status="ok",
            message="Energy result hourly plot HTML artifact exported.",
        ),
    }


def _monthly_chart_series(
    *,
    sql: Any,
    series: list[dict[str, Any]],
    time_interval: str,
) -> tuple[list[Any], list[dict[str, Any]]]:
    if not series:
        raise ValueError("series must include at least one output_name.")
    collections: list[Any] = []
    summaries: list[dict[str, Any]] = []
    intervals: set[str] = set()
    for index, item in enumerate(series):
        if not isinstance(item, dict):
            raise ValueError("Each series item must be a dictionary.")
        output_name = str(item.get("output_name") or "").strip()
        if not output_name:
            raise ValueError("Each series item requires output_name.")
        collection_index = int(item.get("collection_index", 0))
        candidates = _data_collections(sql, output_name, item.get("run_period_index"))
        if collection_index < 0 or collection_index >= len(candidates):
            raise ValueError(
                f"collection_index {collection_index} is outside the DataCollection "
                f"range for output {output_name}. {_available_output_name_message(sql)}"
            )
        collection = _transform_collection(candidates[collection_index], time_interval)
        label = str(item.get("label") or _data_collection_name(collection, output_name))
        if hasattr(collection, "header"):
            original_type = collection.header.metadata.get("type")
            if original_type:
                collection.header.metadata["output_type"] = original_type
            collection.header.metadata["type"] = label
            collection.header.metadata["label"] = label
            collection.header.metadata["legend_name"] = label
        interval = _collection_time_interval(collection)
        intervals.add(interval)
        summary = _collection_summary(
            collection,
            output_name=output_name,
            include_values=False,
            max_values=0,
        )
        summary.update(
            {
                "series_index": index,
                "label": label,
                "collection_index": collection_index,
                "time_interval": interval,
                "time_interval_guidance": _time_interval_guidance(
                    interval,
                    data_type=summary.get("data_type"),
                ),
            }
        )
        collections.append(collection)
        summaries.append(summary)
    if len(intervals) > 1:
        raise ValueError(
            "Monthly chart series must all use the same time interval. "
            f"Got: {', '.join(sorted(intervals))}."
        )
    return collections, summaries


def energy_result_monthly_chart_to_html(
    *,
    garden_root: str,
    series: list[dict[str, Any]],
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    time_interval: str = "as_is",
    chart_title: str | None = None,
    y_axis_title: str | None = None,
    stack: bool = False,
    percentile: float = 34,
    time_marks: bool = False,
    name: str = "energy_result_monthly_chart",
    output_subdir: str = "artifacts/energy/results/html",
) -> dict[str, Any]:
    """Export SQL result DataCollections as a monthly chart HTML artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id, sql_path, sql, _record = _sql_result(
        garden_root=garden_root_path,
        run_target=run_target,
        run_id=run_id,
    )
    collections, series_summaries = _monthly_chart_series(
        sql=sql,
        series=series,
        time_interval=time_interval,
    )
    output_dir = (garden_root_path / output_subdir).resolve()
    output_dir.relative_to(garden_root_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify_name(name)
    chart = MonthlyChart(
        collections,
        stack=stack,
        percentile=percentile,
    )
    vis_set = monthly_chart_to_vis_set(
        chart,
        time_marks=time_marks,
        global_title=chart_title,
        y_axis_title=y_axis_title,
    )
    html_path = Path(
        vis_set.to_html(
            output_folder=str(output_dir),
            file_name=safe_name,
            open=False,
        )
    ).resolve()
    html_path.relative_to(garden_root_path)
    labels = [summary["label"] for summary in series_summaries]
    _inject_html_legend(
        html_path,
        title=chart_title or "Series",
        labels=labels,
    )
    artifact_path = to_posix_relative(html_path, garden_root_path)
    source = {
        "run_id": resolved_run_id,
        "sql_path": to_posix_relative(sql_path, garden_root_path),
        "series": [
            {
                "output_name": summary["output_name"],
                "collection_index": summary["collection_index"],
                "label": summary["label"],
                "time_interval": summary["time_interval"],
            }
            for summary in series_summaries
        ],
        "time_interval": time_interval,
        "chart_title": chart_title,
        "y_axis_title": y_axis_title,
        "stack": stack,
        "percentile": percentile,
        "time_marks": time_marks,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=MONTHLY_CHART_HTML_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)
    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=MONTHLY_CHART_HTML_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(html_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": html_path.is_file(),
            "run_id": resolved_run_id,
            "sql_path": to_posix_relative(sql_path, garden_root_path),
            "time_interval": time_interval,
            "time_interval_guidance": _time_interval_guidance(
                time_interval,
                data_type=(
                    series_summaries[0].get("data_type") if series_summaries else None
                ),
            ),
            "chart_title": chart_title,
            "series": series_summaries,
        },
        "report": make_report(
            status="ok",
            message="Energy result monthly chart HTML artifact exported.",
        ),
    }


def _sizing_matches(value: str, query: str | None) -> bool:
    return query is None or query.strip().lower() in value.lower()


def _sizing_blocker(run_id: str, reason: str) -> dict[str, Any]:
    return {
        "summary_view": {"run_id": run_id, "sizing_count": 0},
        "energy_blocker": {
            "reason": reason,
            "recommended_next_tools": ["GD_Poll_Run"],
        },
        "report": make_report(status="blocked", message=reason),
    }


def read_energy_sizing(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    zone: str | None = None,
    component: str | None = None,
    sizing_category: str | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Read compact zone and component sizing from a completed Energy run."""
    if max_results <= 0:
        raise ValueError("max_results must be positive.")
    category = (
        sizing_category.strip().lower().replace("-", "_").replace(" ", "_")
        if sizing_category
        else None
    )
    if category not in {None, "zone", "component", "heating", "cooling", "zone_heating", "zone_cooling"}:
        raise ValueError(
            "sizing_category must be zone, component, heating, or cooling."
        )
    root = _garden_root(garden_root)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    if record.get("status") != "completed":
        return _sizing_blocker(resolved_run_id, "Sizing results require a completed Energy run.")
    try:
        _, sql_path, sql, _ = _sql_result(
            garden_root=root, run_target=run_target, run_id=run_id
        )
    except (FileNotFoundError, ValueError) as exc:
        return _sizing_blocker(resolved_run_id, f"Sizing SQL is unavailable: {exc}")
    zones = []
    if category in {None, "zone", "heating", "zone_heating", "cooling", "zone_cooling"}:
        zone_sizes = (
            sql.zone_heating_sizes
            if category in {"heating", "zone_heating"}
            else sql.zone_cooling_sizes
            if category in {"cooling", "zone_cooling"}
            else [*sql.zone_heating_sizes, *sql.zone_cooling_sizes]
        )
        for item in zone_sizes:
            data = item.to_dict()
            if _sizing_matches(str(data.get("zone_name", "")), zone):
                zones.append(data)
    components = []
    if category in {None, "component"}:
        for item in sql.component_sizes:
            data = item.to_dict()
            if _sizing_matches(str(data.get("component_name", "")), component):
                components.append(data)
    total = len(zones) + len(components)
    if not total:
        return _sizing_blocker(resolved_run_id, "No sizing results matched the requested filters.")
    return {
        "run_target": record.get("target") or run_target,
        "summary_view": {
            "run_id": resolved_run_id,
            "sql_path": str(sql_path.relative_to(root)).replace("\\", "/"),
            "zone_result_count": len(zones),
            "component_result_count": len(components),
            "result_count": total,
            "filters": {"zone": zone, "component": component, "sizing_category": category},
        },
        "zone_sizing": zones[:max_results],
        "component_sizing": components[:max_results],
        "results_truncated": total > max_results,
        "report": make_report(status="ok", message=f"Read EnergyPlus sizing for run {resolved_run_id}."),
    }


def _resolve_run_output_file(
    garden_root: Path,
    record: dict[str, Any],
    output_name: str,
    fallback_rel_paths: tuple[str, ...] = (),
) -> Path:
    try:
        return _absolute_output_path(garden_root, record, output_name)
    except ValueError:
        pass
    if output_name == "osw" and record.get("workflow_path"):
        candidate = (garden_root / str(record["workflow_path"])).resolve()
        try:
            candidate.relative_to(garden_root)
            if candidate.is_file():
                return candidate
        except ValueError:
            pass
    run_folder = record.get("run_folder")
    if isinstance(run_folder, str) and run_folder:
        run_dir = (garden_root / run_folder).resolve()
        for rel in fallback_rel_paths:
            candidate = (run_dir / rel).resolve()
            try:
                candidate.relative_to(garden_root)
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
    raise ValueError(f"Energy run has no {output_name} output.")


def _resolve_honeybee_model_for_run(
    garden_root: Path,
    record: dict[str, Any],
    model_target: dict[str, Any] | None = None,
) -> Model:
    if model_target is not None:
        _manifest, resolved = resolve_model_target(garden_root, model_target)
        return load_honeybee_model(garden_root, resolved)
    rec_target = record.get("model_target")
    if isinstance(rec_target, dict) and rec_target.get("path"):
        candidate = (garden_root / str(rec_target["path"])).resolve()
        try:
            candidate.relative_to(garden_root)
            if candidate.is_file():
                return Model.from_hbjson(str(candidate), cleanup_irrational=False)
        except ValueError:
            pass
    rec_path = record.get("model_path")
    if isinstance(rec_path, str) and rec_path:
        candidate = (garden_root / rec_path).resolve()
        try:
            candidate.relative_to(garden_root)
            if candidate.is_file():
                return Model.from_hbjson(str(candidate), cleanup_irrational=False)
        except ValueError:
            pass
    _manifest, resolved = resolve_model_target(garden_root, None)
    return load_honeybee_model(garden_root, resolved)


def _attach_geometry_matches(
    *,
    garden_root_path: Path,
    record: dict[str, Any],
    run_id: str,
    sql_path: Path,
    collections_by_output: dict[str, list[Any]],
    match_mode: str,
    model_target: dict[str, Any] | None,
    invert_multiplier: bool,
    space_based: bool,
    zone_correct_mult: bool,
    include_values: bool,
    max_values: int,
    max_collections: int,
    save_data_collections: bool,
) -> dict[str, Any]:
    model = _resolve_honeybee_model_for_run(garden_root_path, record, model_target)
    matched_rooms: list[dict[str, Any]] = []
    matched_faces: list[dict[str, Any]] = []
    saved_targets: list[dict[str, Any]] = []
    sql_rel = to_posix_relative(sql_path, garden_root_path)

    for output_name, collections in collections_by_output.items():
        if not collections:
            continue
        first_meta = dict(getattr(getattr(collections[0], "header", None), "metadata", {}) or {})
        effective_mode = match_mode
        if effective_mode == "auto":
            if "Surface" in first_meta:
                effective_mode = "faces"
            else:
                effective_mode = "rooms"

        if effective_mode == "rooms":
            room_tuples = match_rooms_to_data(
                collections,
                model.rooms,
                invert_multiplier=invert_multiplier,
                space_based=space_based,
                zone_correct_mult=zone_correct_mult,
            )
            for idx, (room, coll, multiplier) in enumerate(room_tuples[:max_collections]):
                values = [
                    float(v)
                    for v in (getattr(coll, "values", []) or [])
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                header = getattr(coll, "header", None)
                entry: dict[str, Any] = {
                    "room_identifier": room.identifier,
                    "room_display_name": room.display_name,
                    "zone": room.zone,
                    "story": room.story,
                    "floor_area": room.floor_area,
                    "room_multiplier": room.multiplier,
                    "effective_multiplier": multiplier,
                    "output_name": output_name,
                    "unit": _header_value(header, "unit") if header else None,
                    "value_count": len(values),
                    "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                    "mean": mean(values) if values else None,
                    "total": sum(values) if values else None,
                }
                if include_values:
                    raw = list(getattr(coll, "values", []) or [])
                    entry["values"] = raw[:max_values]
                    entry["values_truncated"] = len(raw) > len(entry["values"])
                if save_data_collections:
                    saved = save_data_collection(
                        garden_root=garden_root_path,
                        data_collection=coll,
                        identifier=f"{run_id}_{output_name}_room_{room.identifier}_{idx}",
                        source={
                            "producer": "match_rooms_to_data",
                            "run_id": run_id,
                            "sql_path": sql_rel,
                            "output_name": output_name,
                            "room_identifier": room.identifier,
                            "effective_multiplier": multiplier,
                        },
                    )
                    entry["data_collection_target"] = saved["target"]
                    saved_targets.append(saved["target"])
                matched_rooms.append(entry)
        elif effective_mode == "faces":
            top_faces = [*model.faces, *model.orphaned_apertures, *model.orphaned_doors]
            face_tuples = match_faces_to_data(collections, top_faces)
            for idx, (face_obj, coll) in enumerate(face_tuples[:max_collections]):
                values = [
                    float(v)
                    for v in (getattr(coll, "values", []) or [])
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                header = getattr(coll, "header", None)
                parent = getattr(face_obj, "parent", None)
                entry = {
                    "face_identifier": face_obj.identifier,
                    "face_display_name": face_obj.display_name,
                    "object_type": type(face_obj).__name__,
                    "face_type": getattr(getattr(face_obj, "type", None), "name", None),
                    "boundary_condition": getattr(
                        getattr(face_obj, "boundary_condition", None), "name", None
                    ),
                    "area": getattr(face_obj, "area", None),
                    "parent_identifier": getattr(parent, "identifier", None),
                    "output_name": output_name,
                    "unit": _header_value(header, "unit") if header else None,
                    "value_count": len(values),
                    "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                    "mean": mean(values) if values else None,
                    "total": sum(values) if values else None,
                }
                if include_values:
                    raw = list(getattr(coll, "values", []) or [])
                    entry["values"] = raw[:max_values]
                    entry["values_truncated"] = len(raw) > len(entry["values"])
                if save_data_collections:
                    saved = save_data_collection(
                        garden_root=garden_root_path,
                        data_collection=coll,
                        identifier=f"{run_id}_{output_name}_face_{face_obj.identifier}_{idx}",
                        source={
                            "producer": "match_faces_to_data",
                            "run_id": run_id,
                            "sql_path": sql_rel,
                            "output_name": output_name,
                            "face_identifier": face_obj.identifier,
                        },
                    )
                    entry["data_collection_target"] = saved["target"]
                    saved_targets.append(saved["target"])
                matched_faces.append(entry)

    return {
        "match_mode": match_mode,
        "model_identifier": model.identifier,
        "matched_room_count": len(matched_rooms),
        "matched_face_count": len(matched_faces),
        "matched_rooms": matched_rooms,
        "matched_faces": matched_faces,
        "matched_data_collection_targets": saved_targets,
    }


def match_energy_results_to_rooms(
    *,
    garden_root: str,
    output_name: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    model_target: dict[str, Any] | None = None,
    run_period_index: int | None = None,
    invert_multiplier: bool = False,
    space_based: bool = False,
    zone_correct_mult: bool = True,
    include_values: bool = False,
    max_values: int = 24,
    max_collections: int = 50,
    save_data_collections: bool = False,
) -> dict[str, Any]:
    """Match EnergyPlus zone/system SQL DataCollections to Honeybee Model Rooms."""
    return read_energy_result_data(
        garden_root=garden_root,
        run_target=run_target,
        run_id=run_id,
        output_name=output_name,
        run_period_index=run_period_index,
        include_values=include_values,
        max_values=max_values,
        max_collections=max_collections,
        save_data_collections=save_data_collections,
        match_to="rooms",
        model_target=model_target,
        invert_multiplier=invert_multiplier,
        space_based=space_based,
        zone_correct_mult=zone_correct_mult,
    )


def match_energy_results_to_faces(
    *,
    garden_root: str,
    output_name: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    model_target: dict[str, Any] | None = None,
    run_period_index: int | None = None,
    include_values: bool = False,
    max_values: int = 24,
    max_collections: int = 50,
    save_data_collections: bool = False,
) -> dict[str, Any]:
    """Match EnergyPlus surface SQL DataCollections to Honeybee Model Faces/Apertures/Doors."""
    return read_energy_result_data(
        garden_root=garden_root,
        run_target=run_target,
        run_id=run_id,
        output_name=output_name,
        run_period_index=run_period_index,
        include_values=include_values,
        max_values=max_values,
        max_collections=max_collections,
        save_data_collections=save_data_collections,
        match_to="faces",
        model_target=model_target,
    )


def _list_sql_tabular_tables(sql_path: Path) -> list[dict[str, str]]:
    conn = sqlite3.connect(str(sql_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT ReportName, TableName "
            "FROM TabularDataWithStrings "
            "ORDER BY ReportName, TableName"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return [
        {"report_name": str(rep or ""), "table_name": str(tbl or "")}
        for rep, tbl in rows
        if tbl
    ]


def read_energy_tabular_data(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    table_name: str | None = None,
    report_name: str | None = None,
    table_query: str | None = None,
    j_to_kwh: bool = True,
    max_results: int = 50,
) -> dict[str, Any]:
    """List SQL tabular summary tables or read one table via SQLiteResult.tabular_data_by_name."""
    if max_results <= 0:
        raise ValueError("max_results must be positive.")
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id, sql_path, sql, record = _sql_result(
        garden_root=root,
        run_target=run_target,
        run_id=run_id,
    )
    sql_rel = to_posix_relative(sql_path, root)
    all_tables = _list_sql_tabular_tables(sql_path)

    if not table_name:
        filtered = all_tables
        if report_name:
            rep_q = report_name.strip().lower()
            filtered = [item for item in filtered if rep_q in item["report_name"].lower()]
        if table_query:
            tbl_q = table_query.strip().lower()
            filtered = [
                item
                for item in filtered
                if tbl_q in item["table_name"].lower() or tbl_q in item["report_name"].lower()
            ]
        visible = filtered[:max_results]
        return {
            "run_target": record.get("target") or run_target,
            "run_id": resolved_run_id,
            "tables": visible,
            "total_table_count": len(all_tables),
            "matching_table_count": len(filtered),
            "returned_table_count": len(visible),
            "truncated": len(filtered) > len(visible),
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": resolved_run_id,
                "sql_path": sql_rel,
                "total_table_count": len(all_tables),
                "matching_table_count": len(filtered),
                "returned_table_count": len(visible),
                "tables": visible,
            },
            "report": make_report(
                status="ok",
                message=f"Listed {len(visible)} SQL tabular table(s) for run {resolved_run_id}.",
            ),
        }

    resolved_table = table_name.strip()
    resolved_report = report_name.strip() if report_name else None
    exact_matches = [
        item for item in all_tables if item["table_name"].lower() == resolved_table.lower()
    ]
    if exact_matches:
        resolved_table = exact_matches[0]["table_name"]
        if resolved_report is not None:
            rep_matches = [
                item for item in exact_matches if item["report_name"].lower() == resolved_report.lower()
            ]
            if rep_matches:
                resolved_report = rep_matches[0]["report_name"]

    table_dict = sql.tabular_data_by_name(
        resolved_table,
        j_to_kwh=j_to_kwh,
        report_name=resolved_report,
    )
    columns = list(sql.tabular_column_names(resolved_table, report_name=resolved_report))
    items = list(table_dict.items())
    visible_items = items[:max_results]
    rows = {str(key): list(vals) for key, vals in visible_items}
    records = [
        {
            "row_name": str(key),
            "values": list(vals),
            "by_column": (
                {columns[idx]: vals[idx] for idx in range(min(len(columns), len(vals)))}
                if columns
                else {}
            ),
        }
        for key, vals in visible_items
    ]
    return {
        "run_target": record.get("target") or run_target,
        "run_id": resolved_run_id,
        "table_name": resolved_table,
        "report_name": resolved_report,
        "j_to_kwh": bool(j_to_kwh),
        "columns": columns,
        "rows": rows,
        "records": records,
        "row_count": len(items),
        "returned_row_count": len(visible_items),
        "truncated": len(items) > len(visible_items),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "sql_path": sql_rel,
            "table_name": resolved_table,
            "report_name": resolved_report,
            "columns": columns,
            "row_count": len(items),
            "returned_row_count": len(visible_items),
            "truncated": len(items) > len(visible_items),
            "rows": rows,
        },
        "report": make_report(
            status="ok",
            message=(
                f"Read SQL table {resolved_table!r} ({len(visible_items)} of {len(items)} row(s))."
            ),
        ),
    }


def read_energy_zsz(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    zone: str | None = None,
    include_values: bool = False,
    max_values: int = 24,
    max_results: int = 50,
) -> dict[str, Any]:
    """Parse EnergyPlus epluszsz.csv sizing profiles via honeybee_energy.result.zsz.ZSZ."""
    if max_values < 0:
        raise ValueError("max_values must be zero or greater.")
    if max_results <= 0:
        raise ValueError("max_results must be positive.")
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    zsz_path = _resolve_run_output_file(
        root,
        record,
        "zsz",
        ("openstudio/run/epluszsz.csv", "epluszsz.csv"),
    )
    zsz = ZSZ(str(zsz_path))
    zsz_rel = to_posix_relative(zsz_path, root)

    def _summarize_group(collections: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        filtered = [
            coll
            for coll in collections
            if _sizing_matches(str(coll.header.metadata.get("Zone", "")), zone)
        ]
        items: list[dict[str, Any]] = []
        for coll in filtered[:max_results]:
            vals = [float(v) for v in coll.values]
            entry: dict[str, Any] = {
                "zone_name": coll.header.metadata.get("Zone"),
                "type": coll.header.metadata.get("type"),
                "unit": coll.header.unit,
                "value_count": len(vals),
                "peak": max(vals) if vals else None,
                "minimum": min(vals) if vals else None,
                "mean": mean(vals) if vals else None,
            }
            if include_values:
                entry["values"] = vals[:max_values]
                entry["values_truncated"] = len(vals) > len(entry["values"])
            items.append(entry)

        coincident_peak = None
        peak_step_index = None
        non_coincident_sum = None
        if filtered:
            step_count = min(len(coll.values) for coll in filtered)
            if step_count > 0:
                totals = [
                    sum(float(coll.values[i]) for coll in filtered)
                    for i in range(step_count)
                ]
                coincident_peak = max(totals)
                peak_step_index = totals.index(coincident_peak)
            non_coincident_sum = sum(max(float(v) for v in coll.values) for coll in filtered if coll.values)
        return items, {
            "zone_count": len(filtered),
            "unit": filtered[0].header.unit if filtered else None,
            "coincident_peak": coincident_peak,
            "peak_step_index": peak_step_index,
            "non_coincident_sum": non_coincident_sum,
            "max_zone_peak": max((item["peak"] for item in items if item["peak"] is not None), default=None),
        }

    cool_loads, cool_load_stats = _summarize_group(list(zsz.cooling_load_data))
    heat_loads, heat_load_stats = _summarize_group(list(zsz.heating_load_data))
    cool_flows, cool_flow_stats = _summarize_group(list(zsz.cooling_flow_data))
    heat_flows, heat_flow_stats = _summarize_group(list(zsz.heating_flow_data))

    return {
        "run_target": record.get("target") or run_target,
        "run_id": resolved_run_id,
        "zsz_path": zsz_rel,
        "timestep": zsz.timestep,
        "coincident_peaks": {
            "cooling_load": cool_load_stats,
            "heating_load": heat_load_stats,
            "cooling_flow": cool_flow_stats,
            "heating_flow": heat_flow_stats,
        },
        "cooling_loads": cool_loads,
        "heating_loads": heat_loads,
        "cooling_flows": cool_flows,
        "heating_flows": heat_flows,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "zsz_path": zsz_rel,
            "timestep": zsz.timestep,
            "coincident_peaks": {
                "cooling_load": cool_load_stats,
                "heating_load": heat_load_stats,
            },
            "cooling_zone_count": cool_load_stats["zone_count"],
            "heating_zone_count": heat_load_stats["zone_count"],
        },
        "report": make_report(
            status="ok",
            message=f"Read EnergyPlus ZSZ sizing profiles for run {resolved_run_id}.",
        ),
    }


def read_energy_rdd(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    query: str | None = None,
    keywords: list[str] | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Discover available EnergyPlus output variable names from eplusout.rdd via RDD."""
    if max_results <= 0:
        raise ValueError("max_results must be positive.")
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    rdd_path = _resolve_run_output_file(
        root,
        record,
        "rdd",
        ("openstudio/run/eplusout.rdd", "eplusout.rdd"),
    )
    rdd = RDD(str(rdd_path))
    all_names = list(rdd.output_names)
    if keywords:
        matched = list(rdd.filter_outputs_by_keywords([str(k) for k in keywords if str(k).strip()]))
    elif query and query.strip():
        tokens = [token.lower() for token in query.strip().split() if token]
        matched = [
            name for name in all_names if all(token in name.lower() for token in tokens)
        ]
    else:
        matched = all_names
    visible = matched[:max_results]
    rdd_rel = to_posix_relative(rdd_path, root)
    return {
        "run_target": record.get("target") or run_target,
        "run_id": resolved_run_id,
        "rdd_path": rdd_rel,
        "total_output_count": len(all_names),
        "matching_output_count": len(matched),
        "returned_output_count": len(visible),
        "output_names": visible,
        "truncated": len(matched) > len(visible),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "rdd_path": rdd_rel,
            "query": query,
            "keywords": keywords,
            "total_output_count": len(all_names),
            "matching_output_count": len(matched),
            "returned_output_count": len(visible),
            "output_names": visible,
            "truncated": len(matched) > len(visible),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Read {len(visible)} of {len(matched)} matching RDD output name(s) "
                f"for run {resolved_run_id}."
            ),
        ),
    }


def read_energy_osw(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    max_stdout_chars: int = 2000,
) -> dict[str, Any]:
    """Parse OpenStudio Workflow (.osw) execution logs and measure step outcomes via OSW."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(root, resolved_run_id)
    osw_path = _resolve_run_output_file(
        root,
        record,
        "osw",
        ("openstudio/out.osw", "out.osw", "openstudio/workflow.osw", "workflow.osw"),
    )
    osw = OSW(str(osw_path))
    data = dict(osw.file_dict or {})
    steps_summary: list[dict[str, Any]] = []
    for index, step in enumerate(list(data.get("steps") or [])):
        if not isinstance(step, dict):
            continue
        res = step.get("result") if isinstance(step.get("result"), dict) else {}
        stdout_raw = str(res.get("stdout") or "")
        steps_summary.append(
            {
                "step_index": index,
                "measure_dir_name": step.get("measure_dir_name"),
                "arguments": step.get("arguments") or {},
                "completed_at": res.get("completed_at"),
                "started_at": res.get("started_at"),
                "step_result": res.get("step_result"),
                "warning_count": len(res.get("step_warnings") or []),
                "error_count": len(res.get("step_errors") or []),
                "step_warnings": list(res.get("step_warnings") or []),
                "step_errors": list(res.get("step_errors") or []),
                "stdout_preview": stdout_raw[:max_stdout_chars],
                "stdout_truncated": len(stdout_raw) > max_stdout_chars,
            }
        )
    osw_rel = to_posix_relative(osw_path, root)
    return {
        "run_target": record.get("target") or run_target,
        "run_id": resolved_run_id,
        "osw_path": osw_rel,
        "completed_status": data.get("completed_status"),
        "started_at": data.get("started_at"),
        "completed_at": data.get("completed_at"),
        "seed_file": data.get("seed_file"),
        "weather_file": data.get("weather_file"),
        "measure_paths": list(data.get("measure_paths") or []),
        "step_count": len(steps_summary),
        "steps": steps_summary,
        "warnings": list(osw.warnings),
        "errors": list(osw.errors),
        "error_tracebacks": list(osw.error_tracebacks),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "osw_path": osw_rel,
            "completed_status": data.get("completed_status"),
            "step_count": len(steps_summary),
            "warning_count": len(osw.warnings),
            "error_count": len(osw.errors),
            "steps": steps_summary,
            "errors": list(osw.errors),
            "warnings": list(osw.warnings),
        },
        "report": make_report(
            status="ok",
            message=f"Read OpenStudio OSW workflow for run {resolved_run_id}.",
            warnings=list(osw.warnings),
        ),
    }
