"""Ladybug DataCollection visualization services."""

from __future__ import annotations

import html
from pathlib import Path
from statistics import mean
from typing import Any

import ladybug_vtk._extend_visualization_set  # noqa: F401
from ladybug.hourlyplot import HourlyPlot
from ladybug.monthlychart import MonthlyChart
from ladybug_display.extension.hourlyplot import hourly_plot_to_vis_set
from ladybug_display.extension.monthlychart import monthly_chart_to_vis_set

from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.data_collection import collection_from_dict, load_data_collection
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.visualize.artifacts import _register_artifact, _resolve_output_dir
from garden.visualize.artifacts import save_visualization_set

DATA_COLLECTION_MONTHLY_CHART_HTML_ARTIFACT_TYPE = "data_collection_monthly_chart_html"

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


def _resolve_collection_input(
    *,
    data_collection: dict[str, Any] | None = None,
    data_collection_target: dict[str, Any] | None = None,
    garden_root: str | None = None,
    field_name: str,
) -> tuple[Any, dict[str, Any]]:
    has_dict = data_collection is not None
    has_target = data_collection_target is not None
    if has_dict == has_target:
        raise ValueError(
            f"{field_name} requires exactly one of data_collection or data_collection_target."
        )
    if has_dict:
        if not isinstance(data_collection, dict):
            raise ValueError(f"{field_name}.data_collection must be a dictionary.")
        return collection_from_dict(data_collection), {
            "target_type": "data_collection_dict",
            "data_collection_type": data_collection.get("type"),
        }
    if not garden_root:
        raise ValueError(
            f"{field_name}.data_collection_target requires garden_root to load the Garden artifact."
        )
    collection = load_data_collection(
        garden_root=garden_root,
        data_collection_target=data_collection_target or {},
    )
    return collection, dict(data_collection_target or {})


def _header_value(header: Any, attr: str) -> Any:
    value = getattr(header, attr, None)
    if attr == "data_type" and value is not None:
        return getattr(value, "name", str(value))
    return value


def _collection_name(collection: Any, fallback: str) -> str:
    if hasattr(collection, "ToString"):
        try:
            value = str(collection.ToString()).strip()
            if value:
                return value
        except Exception:
            pass
    return fallback


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


def _transform_collection(collection: Any, time_interval: str) -> Any:
    interval = time_interval.strip().lower()
    if interval not in _MONTHLY_CHART_TIME_INTERVALS:
        allowed = ", ".join(sorted(_MONTHLY_CHART_TIME_INTERVALS))
        raise ValueError(f"Unsupported time_interval: {time_interval}. Allowed: {allowed}.")
    if interval == "as_is":
        return collection.duplicate() if hasattr(collection, "duplicate") else collection

    current = _collection_time_interval(collection)
    if interval == current:
        return collection.duplicate() if hasattr(collection, "duplicate") else collection
    method_by_interval = {
        "daily": "average_daily",
        "monthly": "average_monthly",
        "monthly_per_hour": "average_monthly_per_hour",
        "total_daily": "total_daily",
        "total_monthly": "total_monthly",
        "total_monthly_per_hour": "total_monthly_per_hour",
    }
    method_name = method_by_interval.get(interval)
    if method_name is None or not hasattr(collection, method_name):
        raise ValueError(f"Cannot transform {current} DataCollection to {interval}.")
    return getattr(collection, method_name)()


def _collection_summary(
    collection: Any,
    *,
    label: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    values = list(getattr(collection, "values", []) or [])
    header = getattr(collection, "header", None)
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    return {
        "label": label,
        "name": _collection_name(collection, label),
        "source": source,
        "collection_type": type(collection).__name__,
        "time_interval": _collection_time_interval(collection),
        "data_type": _header_value(header, "data_type") if header is not None else None,
        "unit": _header_value(header, "unit") if header is not None else None,
        "metadata": dict(getattr(header, "metadata", {}) or {}) if header is not None else {},
        "value_count": len(values),
        "minimum": min(numeric_values) if numeric_values else None,
        "maximum": max(numeric_values) if numeric_values else None,
        "mean": mean(numeric_values) if numeric_values else None,
    }


def _visualization_set_summary(visualization_set: dict[str, Any]) -> dict[str, Any]:
    geometry_layers = visualization_set.get("geometry", []) or []
    layer_identifiers = [
        layer.get("identifier")
        for layer in geometry_layers
        if isinstance(layer, dict) and layer.get("identifier")
    ]
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry_layers),
        "geometry_identifiers": layer_identifiers,
    }


def _set_visualization_set_name(vis_set: Any, name: str | None) -> None:
    if name:
        vis_set.identifier = slugify_name(name)
        vis_set.display_name = name


def _apply_label_metadata(collection: Any, label: str) -> None:
    if not hasattr(collection, "header"):
        return
    original_type = collection.header.metadata.get("type")
    if original_type:
        collection.header.metadata["output_type"] = original_type
    collection.header.metadata["type"] = label
    collection.header.metadata["label"] = label
    collection.header.metadata["legend_name"] = label


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
            "<div style=\"display:flex;align-items:center;gap:6px;margin:2px 0;\">"
            f"<span style=\"width:12px;height:12px;background:{colors[index % len(colors)]};"
            "display:inline-block;border-radius:2px;\"></span>"
            f"<span>{html.escape(label)}</span></div>"
        )
        for index, label in enumerate(labels)
    )
    overlay = (
        "<div id=\"lbt-mcp-series-legend\" style=\"position:fixed;right:16px;top:16px;"
        "z-index:9999;background:rgba(255,255,255,0.92);border:1px solid #c9c9c9;"
        "border-radius:4px;padding:10px 12px;font-family:Arial,sans-serif;"
        "font-size:12px;line-height:1.35;color:#222;max-width:280px;\">"
        f"<div style=\"font-weight:600;margin-bottom:6px;\">{html.escape(title)}</div>"
        f"{items}</div>"
    )
    text = html_path.read_text(encoding="utf-8", errors="replace")
    if "</body>" in text:
        text = text.replace("</body>", overlay + "\n</body>", 1)
    else:
        text += "\n" + overlay
    html_path.write_text(text, encoding="utf-8")


def _monthly_chart_series(
    series: list[dict[str, Any]],
    *,
    time_interval: str,
    garden_root: str | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    if not series:
        raise ValueError("series must include at least one DataCollection.")
    collections: list[Any] = []
    summaries: list[dict[str, Any]] = []
    intervals: set[str] = set()
    for index, item in enumerate(series):
        if not isinstance(item, dict):
            raise ValueError("Each series item must be a dictionary.")
        collection_input, source = _resolve_collection_input(
            data_collection=item.get("data_collection"),
            data_collection_target=item.get("data_collection_target"),
            garden_root=garden_root,
            field_name=f"series[{index}]",
        )
        collection = _transform_collection(collection_input, time_interval)
        label = str(
            item.get("label")
            or _collection_name(collection, f"Series {index + 1}")
        )
        _apply_label_metadata(collection, label)
        interval = _collection_time_interval(collection)
        intervals.add(interval)
        source["series_index"] = index
        collections.append(collection)
        summaries.append(_collection_summary(collection, label=label, source=source))
    if len(intervals) > 1:
        raise ValueError(
            "Monthly chart series must all use the same time interval. "
            f"Got: {', '.join(sorted(intervals))}."
        )
    return collections, summaries


def data_collection_hourly_plot_to_visualization_set(
    *,
    data_collection: dict[str, Any] | None = None,
    data_collection_target: dict[str, Any] | None = None,
    garden_root: str | None = None,
    name: str = "data_collection_hourly_plot",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate one hourly Ladybug DataCollection into a VisualizationSet."""
    collection, source = _resolve_collection_input(
        data_collection=data_collection,
        data_collection_target=data_collection_target,
        garden_root=garden_root,
        field_name="data_collection_hourly_plot_to_visualization_set",
    )
    if _collection_time_interval(collection) != "hourly":
        raise ValueError("HourlyPlot requires an hourly DataCollection.")
    vis_set = hourly_plot_to_vis_set(HourlyPlot(collection))
    _set_visualization_set_name(vis_set, name)
    vis_set_dict = vis_set.to_dict()
    summary = _collection_summary(
        collection,
        label=_collection_name(collection, name),
        source=source,
    )
    result = {
        "visualization_set": vis_set_dict,
        "summary_view": {
            "visualization_set": _visualization_set_summary(vis_set_dict),
            "data_collection": summary,
        },
        "report": make_report(
            status="ok",
            message="DataCollection hourly plot VisualizationSet created.",
        ),
    }
    if garden_root:
        saved = save_visualization_set(
            garden_root=garden_root,
            visualization_set=vis_set_dict,
            name=name,
            source={
                "producer": "data_collection_hourly_plot_to_visualization_set",
                "data_collection": summary,
            },
        )
        result["target"] = saved["target"]
        result["visualization_set_target"] = saved["target"]
        result["visualization_set_persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["visualization_set_target"] = saved["target"]
    if not return_visualization_set:
        result.pop("visualization_set", None)
    return result


def data_collection_monthly_chart_to_visualization_set(
    *,
    series: list[dict[str, Any]],
    garden_root: str | None = None,
    time_interval: str = "as_is",
    chart_title: str | None = None,
    y_axis_title: str | None = None,
    stack: bool = False,
    percentile: float = 34,
    time_marks: bool = False,
    name: str = "data_collection_monthly_chart",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate Ladybug DataCollections into a MonthlyChart VisualizationSet."""
    collections, series_summaries = _monthly_chart_series(
        series,
        time_interval=time_interval,
        garden_root=garden_root,
    )
    chart = MonthlyChart(collections, stack=stack, percentile=percentile)
    vis_set = monthly_chart_to_vis_set(
        chart,
        time_marks=time_marks,
        global_title=chart_title,
        y_axis_title=y_axis_title,
    )
    _set_visualization_set_name(vis_set, name)
    vis_set_dict = vis_set.to_dict()
    result = {
        "visualization_set": vis_set_dict,
        "summary_view": {
            "visualization_set": _visualization_set_summary(vis_set_dict),
            "time_interval": time_interval,
            "chart_title": chart_title,
            "series": series_summaries,
        },
        "report": make_report(
            status="ok",
            message="DataCollection monthly chart VisualizationSet created.",
        ),
    }
    if garden_root:
        saved = save_visualization_set(
            garden_root=garden_root,
            visualization_set=vis_set_dict,
            name=name,
            source={
                "producer": "data_collection_monthly_chart_to_visualization_set",
                "series": series_summaries,
                "time_interval": time_interval,
                "chart_title": chart_title,
            },
        )
        result["target"] = saved["target"]
        result["visualization_set_target"] = saved["target"]
        result["visualization_set_persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["visualization_set_target"] = saved["target"]
    if not return_visualization_set:
        result.pop("visualization_set", None)
    return result


def data_collection_monthly_chart_to_html(
    *,
    garden_root: str,
    series: list[dict[str, Any]],
    time_interval: str = "as_is",
    chart_title: str | None = None,
    y_axis_title: str | None = None,
    stack: bool = False,
    percentile: float = 34,
    time_marks: bool = False,
    name: str = "data_collection_monthly_chart",
    output_subdir: str = "artifacts/visualization/datacollections/html",
) -> dict[str, Any]:
    """Export Ladybug DataCollections as a MonthlyChart HTML artifact."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    collections, series_summaries = _monthly_chart_series(
        series,
        time_interval=time_interval,
        garden_root=str(garden_root_path),
    )
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    safe_name = slugify_name(name)
    chart = MonthlyChart(collections, stack=stack, percentile=percentile)
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
    _inject_html_legend(html_path, title=chart_title or "Series", labels=labels)

    artifact_path = to_posix_relative(html_path, garden_root_path)
    source = {
        "series": series_summaries,
        "time_interval": time_interval,
        "chart_title": chart_title,
        "y_axis_title": y_axis_title,
        "stack": stack,
        "percentile": percentile,
        "time_marks": time_marks,
    }
    artifact = _register_artifact(
        manifest,
        artifact_type=DATA_COLLECTION_MONTHLY_CHART_HTML_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)
    return {
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=DATA_COLLECTION_MONTHLY_CHART_HTML_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(html_path),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact": artifact,
            "exists": html_path.is_file(),
            "time_interval": time_interval,
            "chart_title": chart_title,
            "series": series_summaries,
        },
        "report": make_report(
            status="ok",
            message="DataCollection monthly chart HTML artifact exported.",
        ),
    }
