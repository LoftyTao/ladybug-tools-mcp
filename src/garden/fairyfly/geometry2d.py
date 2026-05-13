"""Ladybug Geometry 2D helpers for Fairyfly authoring."""

from __future__ import annotations

from typing import Iterable

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.line import LineSegment3D
from ladybug_geometry.geometry3d.pointvector import Point3D


def _point2d(value: Iterable[float]) -> Point2D:
    coords = list(value)
    if len(coords) < 2:
        raise ValueError("2D points must include x and y coordinates.")
    return Point2D(float(coords[0]), float(coords[1]))


def _point3d_from_2d(point: Point2D) -> Point3D:
    return Point3D(point.x, point.y, 0)


def polygon2d_from_vertices(
    vertices_2d: list[list[float]],
    *,
    tolerance: float | None = None,
) -> Polygon2D:
    """Create a cleaned Polygon2D from public 2D vertex input."""
    polygon = Polygon2D(tuple(_point2d(vertex) for vertex in vertices_2d))
    if tolerance is not None:
        polygon = polygon.remove_duplicate_vertices(tolerance)
        polygon = polygon.remove_colinear_vertices(tolerance)
    if len(polygon.vertices) < 3:
        raise ValueError("A Fairyfly Shape polygon needs at least three vertices.")
    if polygon.is_self_intersecting:
        raise ValueError(
            "Self-intersecting Fairyfly Shape polygons are not supported by this "
            "tool yet. Split the polygon before adding it to the model."
        )
    return polygon


def face3d_from_vertices_2d(
    vertices_2d: list[list[float]],
    *,
    holes_2d: list[list[list[float]]] | None = None,
    tolerance: float | None = None,
) -> Face3D:
    """Create a z=0 Face3D from 2D polygon input."""
    polygon = polygon2d_from_vertices(vertices_2d, tolerance=tolerance)
    boundary = tuple(_point3d_from_2d(point) for point in polygon.vertices)
    holes = None
    if holes_2d:
        holes = tuple(
            tuple(_point3d_from_2d(point) for point in hole.vertices)
            for hole in (
                polygon2d_from_vertices(hole_vertices, tolerance=tolerance)
                for hole_vertices in holes_2d
            )
        )
    return Face3D(boundary, holes=holes)


def line_segments3d_from_segments_2d(
    line_segments_2d: list[list[list[float]]],
) -> tuple[LineSegment3D, ...]:
    """Create z=0 LineSegment3D objects from public 2D segment input."""
    segments: list[LineSegment3D] = []
    for segment in line_segments_2d:
        if len(segment) != 2:
            raise ValueError("Each Fairyfly boundary segment must have two points.")
        segment_2d = LineSegment2D.from_end_points(
            _point2d(segment[0]),
            _point2d(segment[1]),
        )
        segments.append(LineSegment3D.from_line_segment2d(segment_2d))
    if not segments:
        raise ValueError("Fairyfly boundaries need at least one line segment.")
    return tuple(segments)
