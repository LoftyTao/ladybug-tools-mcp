"""Legend parameter services for VisualizationSet workflows."""

from __future__ import annotations

from typing import Any

from ladybug.color import Color, ColorRange, Colorset
from ladybug.legend import (
    Legend3DParameters,
    LegendParameters,
    LegendParametersCategorized,
)

from ladybug_tools_mcp.contracts import make_report


ORIENTATIONS = {"vertical", "horizontal"}


def list_colorset_names() -> list[str]:
    """Return sorted Ladybug Colorset palette names."""
    return sorted(
        name
        for name in dir(Colorset)
        if not name.startswith("_") and name != "ToString" and callable(getattr(Colorset, name, None))
    )


def resolve_colorset(name: str) -> list[Color]:
    """Resolve a Ladybug Colorset palette by name (case/separator insensitive)."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("color_set name must be a non-empty string.")
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    available = {item.lower(): item for item in list_colorset_names()}
    attr_name = available.get(normalized)
    if attr_name is None:
        allowed = ", ".join(sorted(available.values()))
        raise ValueError(f"Unsupported Colorset {name!r}. Available colorsets: {allowed}.")
    return list(getattr(Colorset, attr_name)())


def legend_3d_parameter_from_dict(data: dict[str, Any] | None) -> Legend3DParameters | None:
    """Build a Legend3DParameters object from a full or inline dictionary."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Legend3DParameters input must be a dictionary.")
    payload = dict(data)
    explicit_type = payload.get("type")
    if explicit_type is not None and explicit_type != "Legend3DParameters":
        raise ValueError("Expected Legend3DParameters dictionary.")
    payload["type"] = "Legend3DParameters"
    if isinstance(payload.get("base_plane"), dict):
        base_plane = dict(payload["base_plane"])
        base_plane.setdefault("type", "Plane")
        payload["base_plane"] = base_plane
    return Legend3DParameters.from_dict(payload)


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
    properties_3d: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a serializable Ladybug LegendParameters dict for 2D/3D legends."""
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
        properties_3d=properties_3d,
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
    properties_3d: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Edit a serializable Ladybug LegendParameters or LegendParametersCategorized dict."""
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
        properties_3d=properties_3d,
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


def legend_parameter_from_dict(
    data: dict[str, Any] | None,
) -> LegendParameters | LegendParametersCategorized | None:
    """Build a LegendParameters or LegendParametersCategorized object from a serialized dict."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("legend_parameter must be a dictionary.")
    legend_type = data.get("type")
    if legend_type == "LegendParameters":
        return LegendParameters.from_dict(data)
    if legend_type == "LegendParametersCategorized":
        payload = dict(data)
        if "colors" not in payload or not payload["colors"]:
            color_set = payload.pop("color_set", None)
            if color_set is not None:
                domain = payload.get("domain") or []
                colors = _resolve_colors_for_count(color_set, len(domain) + 1)
                payload["colors"] = [col.to_dict() for col in colors]
        else:
            payload["colors"] = [_normalize_color_dict(c) for c in payload["colors"]]
        return LegendParametersCategorized.from_dict(payload)
    if legend_type == "Legend3DParameters":
        legend = LegendParameters()
        legend.properties_3d = legend_3d_parameter_from_dict(data)
        return legend
    raise ValueError(
        "legend_parameter.type must be 'LegendParameters', 'LegendParametersCategorized', "
        "or 'Legend3DParameters'."
    )


def _apply_legend_updates(
    legend: LegendParameters | LegendParametersCategorized,
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
    properties_3d: dict[str, Any] | None = None,
) -> None:
    is_categorized = isinstance(legend, LegendParametersCategorized)
    if title is not None:
        legend.title = title
    if segment_count is not None and not is_categorized:
        legend.segment_count = segment_count
    if decimal_count is not None:
        legend.decimal_count = decimal_count
    if minimum is not None and not is_categorized:
        legend.min = minimum
    if maximum is not None and not is_categorized:
        legend.max = maximum
    if orientation is not None:
        normalized = orientation.strip().lower()
        if normalized not in ORIENTATIONS:
            allowed = ", ".join(sorted(ORIENTATIONS))
            raise ValueError(
                f"Unsupported legend orientation: {orientation}. Allowed values: {allowed}."
            )
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
    if properties_3d is not None:
        legend.properties_3d = legend_3d_parameter_from_dict(properties_3d)
    if color_set is not None:
        _apply_color_set(legend, color_set)


def _resolve_colors_for_count(color_set: str | dict[str, Any], count: int | None = None) -> list[Color]:
    if isinstance(color_set, str):
        colors = resolve_colorset(color_set)
    elif isinstance(color_set, dict):
        if color_set.get("name"):
            colors = resolve_colorset(str(color_set["name"]))
        else:
            raw_colors = color_set.get("colors")
            if not isinstance(raw_colors, list) or not raw_colors:
                raise ValueError("color_set dict must include a name or a non-empty colors list.")
            colors = [Color.from_dict(_normalize_color_dict(item)) for item in raw_colors]
    else:
        raise ValueError("color_set must be a colorset name or a dictionary.")

    if count is None or len(colors) == count:
        return colors
    if count <= 1:
        return [colors[0]]
    color_range = ColorRange(colors, (0.0, float(count - 1)))
    return [color_range.color(float(index)) for index in range(count)]


def _apply_color_set(
    legend: LegendParameters | LegendParametersCategorized,
    color_set: str | dict[str, Any],
) -> None:
    if isinstance(legend, LegendParametersCategorized):
        legend.colors = _resolve_colors_for_count(color_set, len(legend.domain) + 1)
        return
    if isinstance(color_set, str):
        colors = resolve_colorset(color_set)
        legend.colors = colors
        if legend.user_data is None:
            legend.user_data = {"color_set": color_set}
        else:
            legend.user_data["color_set"] = color_set
        return
    if not isinstance(color_set, dict):
        raise ValueError("color_set must be a colorset name or a dictionary.")
    if color_set.get("name"):
        name = str(color_set["name"])
        legend.colors = resolve_colorset(name)
        if legend.user_data is None:
            legend.user_data = {"color_set": name}
        else:
            legend.user_data["color_set"] = name
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
    properties_3d = legend_dict.get("properties_3d") or {}
    return {
        "type": legend_dict.get("type"),
        "title": legend_dict.get("title", ""),
        "segment_count": legend_dict.get("segment_count"),
        "decimal_count": legend_dict.get("decimal_count"),
        "minimum": legend_dict.get("min"),
        "maximum": legend_dict.get("max"),
        "domain": legend_dict.get("domain"),
        "category_names": legend_dict.get("category_names"),
        "orientation": "vertical" if legend_dict.get("vertical", True) else "horizontal",
        "origin_x": properties_2d.get("origin_x"),
        "origin_y": properties_2d.get("origin_y"),
        "segment_height": properties_2d.get("segment_height"),
        "segment_width": properties_2d.get("segment_width"),
        "text_height": properties_2d.get("text_height"),
        "properties_3d": properties_3d or None,
        "color_count": len(legend_dict.get("colors", [])),
    }


__all__ = [
    "ORIENTATIONS",
    "create_2d_legend_parameter",
    "edit_2d_legend_parameter",
    "legend_3d_parameter_from_dict",
    "legend_parameter_from_dict",
    "list_colorset_names",
    "resolve_colorset",
]
