"""Geometry adapters for Dragonfly Electric Grid authoring tools."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry2d.polyline import Polyline2D


def _point2d(value: Any, *, field_name: str) -> Point2D:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ValueError(f"{field_name} must be a Point2D coordinate list.")
    try:
        x, y = (float(value[0]), float(value[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain numeric coordinates.") from exc
    return Point2D(x, y)


def polygon_from_points(points: list[list[float]], *, field_name: str) -> Polygon2D:
    """Create a Polygon2D footprint from 2D points."""
    if len(points) < 3:
        raise ValueError(f"{field_name} must include at least three 2D points.")
    return Polygon2D(
        tuple(
            _point2d(point, field_name=f"{field_name}[{index}]")
            for index, point in enumerate(points)
        )
    )


def polyline_from_points(points: list[list[float]], *, field_name: str) -> LineSegment2D | Polyline2D:
    """Create a LineSegment2D or Polyline2D from 2D points."""
    if len(points) < 2:
        raise ValueError(f"{field_name} must include at least two 2D points.")
    vertices = [
        _point2d(point, field_name=f"{field_name}[{index}]")
        for index, point in enumerate(points)
    ]
    if len(vertices) == 2:
        return LineSegment2D.from_end_points(vertices[0], vertices[1])
    return Polyline2D(tuple(vertices))

