"""Legend parameter services for VisualizationSet workflows."""

from __future__ import annotations

from typing import Any

from ladybug.color import Color
from ladybug.legend import LegendParameters

from ladybug_tools_mcp.contracts.report import make_report


ORIENTATIONS = {"vertical", "horizontal"}


def create_2d_legend_parameter(
    *,
    title: str | None = None,
    segment_count: int | None = None,
    decimal_count: int | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    position_2d: dict[str, Any] | None = None,
    dimensions_2d: dict[str, Any] | None = None,
    orientation: str = "vertical",
    color_set: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a serializable Ladybug LegendParameters dict for 2D legends."""
    legend = LegendParameters(
        min=minimum,
        max=maximum,
        segment_count=segment_count,
        title=title,
    )
    _apply_legend_updates(
        legend,
        title=None,
        segment_count=None,
        decimal_count=decimal_count,
        minimum=None,
        maximum=None,
        position_2d=position_2d,
        dimensions_2d=dimensions_2d,
        orientation=orientation,
        color_set=color_set,
    )
    legend_dict = legend.to_dict()
    return {
        "object_dict": legend_dict,
        "summary_view": _legend_summary(legend_dict),
        "report": make_report(
            status="ok",
            message="2D legend parameter created.",
        ),
    }


def edit_2d_legend_parameter(
    *,
    legend_parameter: dict[str, Any],
    title: str | None = None,
    segment_count: int | None = None,
    decimal_count: int | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    position_2d: dict[str, Any] | None = None,
    dimensions_2d: dict[str, Any] | None = None,
    orientation: str | None = None,
    color_set: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Edit a serializable Ladybug LegendParameters dict for 2D legends."""
    legend = legend_parameter_from_dict(legend_parameter)
    _apply_legend_updates(
        legend,
        title=title,
        segment_count=segment_count,
        decimal_count=decimal_count,
        minimum=minimum,
        maximum=maximum,
        position_2d=position_2d,
        dimensions_2d=dimensions_2d,
        orientation=orientation,
        color_set=color_set,
    )
    legend_dict = legend.to_dict()
    return {
        "object_dict": legend_dict,
        "summary_view": _legend_summary(legend_dict),
        "report": make_report(
            status="ok",
            message="2D legend parameter edited.",
        ),
    }


def legend_parameter_from_dict(data: dict[str, Any] | None) -> LegendParameters | None:
    """Build a LegendParameters object from a serialized dict."""
    if data is None:
        return None
    if data.get("type") != "LegendParameters":
        raise ValueError("Only LegendParameters dicts are supported for 2D legend parameters.")
    return LegendParameters.from_dict(data)


def _apply_legend_updates(
    legend: LegendParameters,
    *,
    title: str | None,
    segment_count: int | None,
    decimal_count: int | None,
    minimum: float | None,
    maximum: float | None,
    position_2d: dict[str, Any] | None,
    dimensions_2d: dict[str, Any] | None,
    orientation: str | None,
    color_set: str | dict[str, Any] | None,
) -> None:
    if title is not None:
        legend.title = title
    if segment_count is not None:
        legend.segment_count = segment_count
    if decimal_count is not None:
        legend.decimal_count = decimal_count
    if minimum is not None:
        legend.min = minimum
    if maximum is not None:
        legend.max = maximum
    if orientation is not None:
        normalized = orientation.strip().lower()
        if normalized not in ORIENTATIONS:
            allowed = ", ".join(sorted(ORIENTATIONS))
            raise ValueError(f"Unsupported legend orientation: {orientation}. Allowed values: {allowed}.")
        legend.vertical = normalized == "vertical"
    if position_2d:
        if "origin_x" in position_2d:
            legend.origin_x = str(position_2d["origin_x"])
        if "origin_y" in position_2d:
            legend.origin_y = str(position_2d["origin_y"])
    if dimensions_2d:
        if "segment_height" in dimensions_2d:
            legend.segment_height_2d = str(dimensions_2d["segment_height"])
        if "segment_width" in dimensions_2d:
            legend.segment_width_2d = str(dimensions_2d["segment_width"])
        if "text_height" in dimensions_2d:
            legend.text_height_2d = str(dimensions_2d["text_height"])
    if color_set is not None:
        _apply_color_set(legend, color_set)


def _apply_color_set(legend: LegendParameters, color_set: str | dict[str, Any]) -> None:
    if isinstance(color_set, str):
        legend.colors_by_set(color_set)
        return
    if not isinstance(color_set, dict):
        raise ValueError("color_set must be a colorset name or a dictionary.")
    if color_set.get("name"):
        legend.colors_by_set(str(color_set["name"]))
        return
    colors = color_set.get("colors")
    if not isinstance(colors, list) or not colors:
        raise ValueError("color_set dict must include a name or a non-empty colors list.")
    legend.colors = [Color.from_dict(_normalize_color_dict(item)) for item in colors]


def _normalize_color_dict(color: dict[str, Any]) -> dict[str, Any]:
    data = dict(color)
    data.setdefault("type", "Color")
    return data


def _legend_summary(legend_dict: dict[str, Any]) -> dict[str, Any]:
    properties_2d = legend_dict.get("properties_2d") or {}
    return {
        "type": legend_dict.get("type"),
        "title": legend_dict.get("title", ""),
        "segment_count": legend_dict.get("segment_count"),
        "decimal_count": legend_dict.get("decimal_count"),
        "minimum": legend_dict.get("min"),
        "maximum": legend_dict.get("max"),
        "orientation": "vertical" if legend_dict.get("vertical", True) else "horizontal",
        "origin_x": properties_2d.get("origin_x"),
        "origin_y": properties_2d.get("origin_y"),
        "segment_height": properties_2d.get("segment_height"),
        "segment_width": properties_2d.get("segment_width"),
        "text_height": properties_2d.get("text_height"),
        "color_count": len(legend_dict.get("colors", [])),
    }
