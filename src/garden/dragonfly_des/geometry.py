"""Geometry adapters for Dragonfly DES authoring tools."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from ladybug_geometry.geometry3d.pointvector import Point3D


def _numeric_sequence(value: Any, *, length: int, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a coordinate list.")
    if len(value) != length:
        raise ValueError(f"{field_name} must be a Point{length}D coordinate list.")
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain numeric coordinates.") from exc


def _point2d(value: Any, *, field_name: str) -> Point2D:
    x, y = _numeric_sequence(value, length=2, field_name=field_name)
    return Point2D(x, y)


def _point3d(value: Any, *, field_name: str) -> Point3D:
    x, y, z = _numeric_sequence(value, length=3, field_name=field_name)
    return Point3D(x, y, z)


def connector_geometry_from_points(points: list[list[float]]) -> LineSegment2D | Polyline2D:
    """Create a ThermalConnector LineSegment2D or Polyline2D from 2D points."""
    if len(points) < 2:
        raise ValueError("connector polyline_points must include at least two 2D points.")
    vertices = [
        _point2d(point, field_name=f"connector polyline_points[{index}]")
        for index, point in enumerate(points)
    ]
    if len(vertices) == 2:
        return LineSegment2D.from_end_points(vertices[0], vertices[1])
    return Polyline2D(tuple(vertices))


def ghe_geometry_from_points(points: list[list[float]]) -> Polygon2D:
    """Create a GroundHeatExchanger Polygon2D footprint from 2D points."""
    if len(points) < 3:
        raise ValueError("ground heat exchanger footprint_points must include at least three 2D points.")
    vertices = [
        _point2d(point, field_name=f"ground heat exchanger footprint_points[{index}]")
        for index, point in enumerate(points)
    ]
    return Polygon2D(tuple(vertices))


def ghe_borehole_positions_from_points(points: list[list[float]] | None) -> list[Point3D] | None:
    """Create SDK-required Point3D borehole positions from coordinate lists."""
    if points is None:
        return None
    return [
        _point3d(point, field_name=f"ground heat exchanger borehole_positions[{index}]")
        for index, point in enumerate(points)
    ]
