"""Garden-backed Ladybug WindRose statistics and visualization services."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from statistics import mean
from typing import Any

from ladybug.datatype.speed import Speed
from ladybug.windrose import WindRose
from ladybug_display.extension.windrose import wind_rose_to_vis_set

from ladybug_tools_mcp.contracts.report import make_report
from garden.analysis_period import analysis_period_from_input, analysis_period_summary
from garden.manifest import GardenManifest
from garden.visualize.artifacts import save_visualization_set
from garden.visualize.datacollection import _resolve_collection_input
from garden.paths import slugify_name


DEFAULT_DIRECTION_COUNT = 36
DEFAULT_CALM_THRESHOLD = 1e-10


def _number(value: Any, *, field_name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if not isfinite(number):
        raise ValueError(f"{field_name} must be finite.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field_name} must be greater than or equal to {minimum}.")
    return number


def _validated_values(collection: Any, *, field_name: str) -> list[float]:
    values = list(getattr(collection, "values", ()) or ())
    if not values:
        raise ValueError(f"{field_name} must contain at least one value.")
    normalized: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool):
            raise ValueError(f"{field_name}.values[{index}] must be numeric.")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name}.values[{index}] must be numeric.") from exc
        if not isfinite(number):
            raise ValueError(f"{field_name}.values[{index}] must be finite.")
        normalized.append(number)
    return normalized


def _load_collection(
    *,
    data_collection: dict[str, Any] | None,
    data_collection_target: dict[str, Any] | None,
    garden_root: str,
    field_name: str,
) -> tuple[Any, dict[str, Any]]:
    collection, source = _resolve_collection_input(
        data_collection=data_collection,
        data_collection_target=data_collection_target,
        garden_root=garden_root,
        field_name=field_name,
    )
    _validated_values(collection, field_name=field_name)
    return collection, source


def _is_speed_collection(collection: Any) -> bool:
    header = getattr(collection, "header", None)
    return isinstance(getattr(header, "data_type", None), Speed)


def _analysis_summary(values: list[float]) -> dict[str, Any]:
    return {
        "value_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": mean(values),
    }


def _direction_bins(
    *,
    windrose: WindRose,
    total_count: int,
    active_count: int,
) -> list[dict[str, Any]]:
    sector_count = len(windrose.angles) - 1
    sector_width = 360.0 / sector_count
    bins: list[dict[str, Any]] = []
    for index, bin_values in enumerate(windrose.histogram_data):
        center = index * sector_width
        start = (center - sector_width / 2.0) % 360.0
        end = (center + sector_width / 2.0) % 360.0
        numeric_values = [float(value) for value in bin_values]
        count = len(numeric_values)
        bins.append(
            {
                "index": index,
                "center_degrees": center,
                "start_degrees": start,
                "end_degrees": end,
                "count": count,
                "sample_count": count,
                "frequency": count / total_count if total_count else 0.0,
                "frequency_percent": (
                    count / total_count * 100.0 if total_count else 0.0
                ),
                "active_frequency": (
                    count / active_count if active_count else 0.0
                ),
                "active_frequency_percent": (
                    count / active_count * 100.0 if active_count else 0.0
                ),
                "analysis_minimum": min(numeric_values) if numeric_values else None,
                "analysis_maximum": max(numeric_values) if numeric_values else None,
                "analysis_mean": mean(numeric_values) if numeric_values else None,
            }
        )
    return bins


def _visualization_summary(visualization_set: dict[str, Any]) -> dict[str, Any]:
    geometry = visualization_set.get("geometry", []) or []
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry),
        "geometry_identifiers": [
            item.get("identifier")
            for item in geometry
            if isinstance(item, dict) and item.get("identifier")
        ],
    }


def windrose_to_visualization_set(
    *,
    garden_root: str,
    direction_data_collection: dict[str, Any] | None = None,
    direction_data_collection_target: dict[str, Any] | None = None,
    analysis_data_collection: dict[str, Any] | None = None,
    analysis_data_collection_target: dict[str, Any] | None = None,
    direction_count: int = DEFAULT_DIRECTION_COUNT,
    calm_threshold: float = DEFAULT_CALM_THRESHOLD,
    analysis_period: dict[str, Any] | str | None = None,
    north: float = 0.0,
    show_zeros: bool = False,
    frequency_labels: bool = True,
    name: str = "wind_rose",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a WindRose VisualizationSet and compact directional statistics."""
    if isinstance(direction_count, bool) or not isinstance(direction_count, int):
        raise ValueError("direction_count must be an integer.")
    if direction_count < 3:
        raise ValueError("direction_count must be at least 3 for a wind rose plot.")
    calm_threshold = _number(
        calm_threshold,
        field_name="calm_threshold",
        minimum=0.0,
    )
    north = _number(north, field_name="north") % 360.0
    if not isinstance(show_zeros, bool):
        raise ValueError("show_zeros must be a boolean.")
    if not isinstance(frequency_labels, bool):
        raise ValueError("frequency_labels must be a boolean.")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    direction_collection, direction_source = _load_collection(
        data_collection=direction_data_collection,
        data_collection_target=direction_data_collection_target,
        garden_root=str(garden_root_path),
        field_name="direction_data_collection",
    )
    analysis_collection, analysis_source = _load_collection(
        data_collection=analysis_data_collection,
        data_collection_target=analysis_data_collection_target,
        garden_root=str(garden_root_path),
        field_name="analysis_data_collection",
    )
    parsed_analysis_period = analysis_period_from_input(
        analysis_period,
        field_name="analysis_period",
    )
    if parsed_analysis_period is not None and not parsed_analysis_period.is_annual:
        try:
            direction_collection = direction_collection.filter_by_analysis_period(
                parsed_analysis_period
            )
            analysis_collection = analysis_collection.filter_by_analysis_period(
                parsed_analysis_period
            )
        except (AssertionError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not filter WindRose data by analysis_period: {exc}") from exc
    direction_values = _validated_values(
        direction_collection,
        field_name="direction_data_collection",
    )
    analysis_values = _validated_values(
        analysis_collection,
        field_name="analysis_data_collection",
    )
    if len(direction_values) != len(analysis_values):
        raise ValueError(
            "direction_data_collection and analysis_data_collection must have the same value count."
        )

    is_speed_data = _is_speed_collection(analysis_collection)
    calm_values = (
        [value <= calm_threshold for value in analysis_values]
        if is_speed_data
        else [False] * len(analysis_values)
    )
    calm_count = sum(calm_values)
    active_count = len(analysis_values) - calm_count
    analysis_for_windrose = analysis_collection
    if is_speed_data and calm_count:
        analysis_for_windrose = analysis_collection.duplicate()
        analysis_for_windrose.values = [
            0 if is_calm else value
            for value, is_calm in zip(analysis_values, calm_values)
        ]

    try:
        windrose = WindRose(
            direction_collection,
            analysis_for_windrose,
            direction_count=direction_count,
        )
        windrose.north = north
        windrose.show_zeros = show_zeros
        visualization = wind_rose_to_vis_set(
            windrose,
            frequency_labels=frequency_labels,
        )
    except (AssertionError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not create WindRose: {exc}") from exc

    safe_name = slugify_name(name)
    visualization.identifier = safe_name
    visualization.display_name = name
    visualization_set = visualization.to_dict()
    bins = _direction_bins(
        windrose=windrose,
        total_count=len(analysis_values),
        active_count=active_count,
    )
    source = {
        "producer": "LB_windrose_to_visualization_set",
        "direction_data_collection": direction_source,
        "analysis_data_collection": analysis_source,
        "direction_count": direction_count,
        "calm_threshold": calm_threshold,
        "analysis_period": (
            analysis_period_summary(parsed_analysis_period)
            if parsed_analysis_period is not None
            else None
        ),
        "north": north,
        "show_zeros": show_zeros,
        "frequency_labels": frequency_labels,
    }
    statistics = {
        "direction_count": direction_count,
        "north": north,
        "direction_bins": bins,
        "prevailing_direction": list(windrose.prevailing_direction),
        "analysis_period": analysis_period_summary(windrose.analysis_period),
        "value_count": len(analysis_values),
        "active_count": active_count,
        "calm_count": calm_count if is_speed_data else None,
        "calm_frequency": (
            calm_count / len(analysis_values) if is_speed_data else None
        ),
        "calm_frequency_percent": (
            calm_count / len(analysis_values) * 100.0
            if is_speed_data
            else None
        ),
        "calm_threshold": calm_threshold if is_speed_data else None,
        "calm_threshold_applied": is_speed_data,
        "analysis_data": _analysis_summary(analysis_values),
        "direction_data": _analysis_summary(direction_values),
    }
    summary_view = {
        **_visualization_summary(visualization_set),
        "garden_target": manifest.target(),
        "source": source,
        "windrose": statistics,
        "body_returned": return_visualization_set,
    }
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="WindRose statistics and VisualizationSet created.",
        ),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=safe_name,
            source=source,
        )
        result.update(
            {
                "target": saved["target"],
                "visualization_set_target": saved["visualization_set_target"],
                "persistence_receipt": saved["persistence_receipt"],
            }
        )
        summary_view.update(
            {
                "visualization_set_target": saved["visualization_set_target"],
                "body_returned": False,
            }
        )
        result.pop("visualization_set", None)
    return result


wind_rose_to_visualization_set = windrose_to_visualization_set


__all__ = ["windrose_to_visualization_set", "wind_rose_to_visualization_set"]
