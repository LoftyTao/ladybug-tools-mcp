"""Floor, wall section and opening clipping geometry for native DWG export."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import hypot, isfinite
from numbers import Real

from ladybug_geometry.geometry3d import Point3D

from . import model as hb
from .model import WallSegment


@dataclass(frozen=True)
class LevelLayout:
    story: str
    identifier: str
    floor_number: int
    series: str
    source_elevation_mm: float
    reference_elevation_mm: float
    height_mm: float
    height_source: str
    offset_mm: tuple[float, float]
    frame_bounds_mm: tuple[float, float, float, float]
    alignment_mm: tuple[float, float]
    room_identifiers: tuple[str, ...]
    warnings: tuple[str, ...]


def plan_levels(model, gap_mm: float = 5000.0, tolerance_mm: float = 0.5, include_orphan_shades: bool = True) -> list[LevelLayout]:
    if not isfinite(gap_mm) or gap_mm <= 0:
        raise ValueError("Floor level layout requires a finite positive millimeter gap")
    if not isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError("Floor level layout requires a finite positive millimeter tolerance")
    scale = hb.unit_scale(model.units)
    buckets: dict[tuple[str, float], list] = {}
    for room in model.rooms:
        story = room.story or "Unassigned"
        elevation = round(hb.room_floor_elevation(room) * scale / tolerance_mm) * tolerance_mm
        buckets.setdefault((story, elevation), []).append(room)
    if not buckets:
        return []
    stories = sorted(
        {story for story, _ in buckets},
        key=lambda story: (min(elevation for name, elevation in buckets if name == story), story),
    )
    all_points = []
    for room in model.rooms:
        boundaries = hb.room_plan_boundaries(room)
        if boundaries:
            all_points.extend(point for boundary in boundaries for point in boundary.boundary)
        else:
            all_points.extend(hb.room_floor_boundary(room))
    if not all_points:
        raise ValueError("Floor level layout requires room floor boundaries")
    all_points.extend(point for shade in model.shades if include_orphan_shades or hb.owner_room(shade) is not None for point in shade.geometry.boundary)
    if include_orphan_shades:
        all_points.extend(point for mesh in model.shade_meshes for point in mesh.geometry.vertices)
    all_thicknesses = [hb.face_thickness_m(face) * 1000 for room in model.rooms for face in room.faces]
    all_margin = max(1000.0, max(all_thicknesses, default=0.0) + 1000.0)
    global_low_x = min(point.x for point in all_points) * scale - all_margin
    global_low_y = min(point.y for point in all_points) * scale - all_margin
    global_high_x = max(point.x for point in all_points) * scale + all_margin
    global_high_y = max(point.y for point in all_points) * scale + all_margin
    if not all(isfinite(value) for value in (global_low_x, global_low_y, global_high_x, global_high_y)) or global_high_x <= global_low_x or global_high_y <= global_low_y:
        raise ValueError("Floor level layout requires finite positive bounds")
    groups = []
    for story in stories:
        elevations = sorted(elevation for name, elevation in buckets if name == story)
        groups.append([(elevation, buckets[(story, elevation)]) for elevation in elevations])
    cursor = 0.0
    result = []
    reference = min(elevation for elevation, _ in groups[0])
    for floor_number, story in enumerate(stories, 1):
        story_groups = groups[floor_number - 1]
        primary = min(story_groups, key=lambda item: item[0])[0]
        series_index = 0
        next_story = min(
            (min(elevation for name, elevation in buckets if name == other) for other in stories[floor_number:]),
            default=None,
        )
        for elevation, rooms in story_groups:
            room_top = max(hb.room_elevation_bounds(room)[1] for room in rooms) * scale
            extent = room_top - reference
            if not isfinite(extent) or extent <= 0:
                raise ValueError(f"Floor level layout requires a positive height: {story}")
            height = extent
            source = "room_geometry_with_native_reference"
            if not isfinite(height) or height <= 0:
                raise ValueError(f"Floor level layout requires a positive height: {story}")
            warnings = []
            if next_story is not None and room_top > next_story + tolerance_mm:
                warnings.append("room_geometry_extends_above_next_story")
            if elevation == primary:
                series = ""
                if next_story is not None and room_top > next_story:
                    height = next_story - reference
                    source = "next_story_with_overlapping_room_geometry"
            else:
                series = chr(ord("A") + series_index)
                series_index += 1
            identifier = story if not series else f"{story}:{series}"
            width = global_high_x - global_low_x
            dx = cursor
            cursor += width + gap_mm
            result.append(LevelLayout(
                story, identifier, floor_number, series, elevation, reference, height, source,
                (dx, 0.0), (global_low_x + dx, global_low_y, global_high_x + dx, global_high_y),
                (global_low_x + dx, global_low_y), tuple(room.identifier for room in rooms), tuple(warnings),
            ))
        primary_rooms = next(rooms for elevation, rooms in story_groups if elevation == primary)
        primary_top = max(hb.room_elevation_bounds(room)[1] for room in primary_rooms) * scale
        reference = min(primary_top, next_story) if next_story is not None else primary_top
    return result


def plan_native_levels(model, gap_mm: float = 5000.0, tolerance_mm: float = 0.5, include_orphan_shades: bool = True) -> list[LevelLayout]:
    levels = plan_levels(model, gap_mm, tolerance_mm, include_orphan_shades)
    if not any(level.series for level in levels) or len({level.source_elevation_mm for level in levels}) != len(levels):
        return levels
    levels.sort(key=lambda level: level.source_elevation_mm)
    rooms = {room.identifier: room for room in model.rooms}
    scale = hb.unit_scale(model.units)
    result = []
    for index, level in enumerate(levels):
        top = levels[index + 1].source_elevation_mm if index + 1 < len(levels) else max(hb.room_elevation_bounds(rooms[identifier])[1] * scale for identifier in level.room_identifiers)
        result.append(replace(level, floor_number=index + 1, series="", reference_elevation_mm=level.source_elevation_mm, height_mm=top - level.source_elevation_mm, height_source="source_elevation_sequence", warnings=(*level.warnings, "native_primary_source_elevation")))
    return result


@dataclass(frozen=True)
class AxisConnector(WallSegment):
    adjoining_face_identifier: str


def floor_section(model, story: str | None = None, axis: str = "centerline", cut_height_mm: float = 1200.0, shared_wall_thickness_mm: float | None = None, adapt_cut_height: bool = False) -> list:

    if not isfinite(cut_height_mm) or cut_height_mm <= 0:
        raise ValueError("Section cut height requires a positive millimeter value")
    if not isinstance(adapt_cut_height, bool):
        raise TypeError("Section height adaptation requires a boolean value")
    shared_thickness_m = _shared_wall_thickness_m(shared_wall_thickness_mm)
    scale = hb.unit_scale(model.units)
    tolerance = 0.1 / scale
    precision = 1e-6 / scale
    sections = []
    source_elevations = {} if shared_thickness_m is not None else None
    for room in model.rooms:
        if story and (room.story or "Unassigned") != story:
            continue
        elevation = hb.room_floor_elevation(room)
        if source_elevations is not None:
            source_elevations[room.identifier] = elevation
        cut = elevation + room_section_height_mm(room, scale, cut_height_mm, adapt_cut_height) / scale
        for face in room.faces:
            if str(face.type).lower() != "wall":
                continue
            for start, end in _face_section(face.geometry, cut, precision):
                sections.append(WallSegment(
                    start=Point3D(start.x, start.y, 0.0),
                    end=Point3D(end.x, end.y, 0.0),
                    thickness_m=hb.face_thickness_m(face),
                    height=hb.face_height(face),
                    exterior=hb.is_exterior(face),
                    room_identifier=room.identifier,
                    face_identifier=face.identifier,
                    normal=face.normal,
                ))
    source_thicknesses = {segment.face_identifier: segment.thickness_m for segment in sections} if shared_thickness_m is not None else None
    return wall_axes(_deduplicate_sections(
        sections, tolerance, infer_shared=axis == "centerline" or shared_thickness_m is not None,
        shared_thickness_m=shared_thickness_m, source_elevations=source_elevations,
    ), scale, axis, source_elevations=source_elevations, shared_thickness_m=shared_thickness_m, source_thicknesses=source_thicknesses)


def room_section_height_mm(room, scale: float, requested_mm: float, adapt_cut_height: bool = False) -> float:

    if not adapt_cut_height:
        return requested_mm
    available_mm = (hb.room_elevation_bounds(room)[1] - hb.room_floor_elevation(room)) * scale
    if isfinite(available_mm) and available_mm > 0 and available_mm + 1e-6 < requested_mm:
        return available_mm / 2.0
    return requested_mm


def _shared_wall_thickness_m(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("Shared wall thickness requires a numeric millimeter value")
    try:
        millimeters = float(value)
    except OverflowError as error:
        raise ValueError("Shared wall thickness requires a finite positive millimeter value") from error
    meters = millimeters / 1000.0
    if not isfinite(millimeters) or millimeters <= 0 or meters == 0:
        raise ValueError("Shared wall thickness requires a finite positive millimeter value")
    return meters


def _face_section(geometry, elevation: float, precision: float) -> list[tuple[Point3D, Point3D]]:
    direction_x = -geometry.normal.y
    direction_y = geometry.normal.x
    direction_length = hypot(direction_x, direction_y)
    if direction_length <= 1e-12:
        return []
    direction_x /= direction_length
    direction_y /= direction_length
    intersections = []
    for loop in (geometry.boundary, *(geometry.holes or ())):
        for start, end in zip(loop, (*loop[1:], loop[0])):
            start_delta = start.z - elevation
            end_delta = end.z - elevation
            start_on = abs(start_delta) <= precision
            end_on = abs(end_delta) <= precision
            if start_on:
                intersections.append(Point3D(start.x, start.y, elevation))
            if end_on:
                intersections.append(Point3D(end.x, end.y, elevation))
            if not start_on and not end_on and start_delta * end_delta < 0:
                parameter = -start_delta / (end_delta - start_delta)
                intersections.append(Point3D(
                    start.x + parameter * (end.x - start.x),
                    start.y + parameter * (end.y - start.y),
                    elevation,
                ))
    intersections.sort(key=lambda point: point.x * direction_x + point.y * direction_y)
    points = []
    for point in intersections:
        if not points or point.distance_to_point(points[-1]) > precision:
            points.append(point)
    result = []
    for start, end in zip(points, points[1:]):
        midpoint = Point3D((start.x + end.x) / 2, (start.y + end.y) / 2, elevation)
        local = geometry.plane.xyz_to_xy(midpoint)
        if geometry.boundary_polygon2d.point_relationship(local, precision) < 0:
            continue
        if any(hole.point_relationship(local, precision) > 0 for hole in geometry.hole_polygon2d or ()):
            continue
        if result and result[-1][1].distance_to_point(start) <= precision:
            result[-1] = (result[-1][0], end)
        else:
            result.append((start, end))
    return result


def _collinear(first, second, tolerance: float) -> bool:
    dx = first.end.x - first.start.x
    dy = first.end.y - first.start.y
    length = hypot(dx, dy)
    if length <= tolerance:
        return False
    return all(
        abs((point.x - first.start.x) * dy - (point.y - first.start.y) * dx) <= tolerance * length
        for point in (second.start, second.end)
    )


def _same_elevation(first, second, tolerance: float, source_elevations=None) -> bool:
    if abs(first.start.z - second.start.z) > tolerance:
        return False
    return source_elevations is None or abs(source_elevations[first.room_identifier] - source_elevations[second.room_identifier]) <= tolerance


def _deduplicate_sections(sections, tolerance: float, infer_shared: bool = False, shared_thickness_m: float | None = None, source_elevations=None) -> list:
    groups = []
    for segment in sections:
        if segment.length <= tolerance:
            continue
        for group in groups:
            if _same_elevation(group[0], segment, tolerance, source_elevations) and _collinear(group[0], segment, tolerance):
                group.append(segment)
                break
        else:
            groups.append([segment])
    result = []
    for group in groups:
        if len(group) == 1:
            result.append(group[0])
            continue
        reference = group[0]
        length = reference.length
        ux = (reference.end.x - reference.start.x) / length
        uy = (reference.end.y - reference.start.y) / length
        ranges = []
        cuts = []
        for segment in group:
            values = sorted(
                (point.x - reference.start.x) * ux + (point.y - reference.start.y) * uy
                for point in (segment.start, segment.end)
            )
            ranges.append(values)
            cuts.extend(values)
        unique = []
        for value in sorted(cuts):
            if not unique or value - unique[-1] > tolerance:
                unique.append(value)
        pieces = []
        for low, high in zip(unique, unique[1:]):
            midpoint = (low + high) / 2
            candidates = [
                index for index, (start, end) in enumerate(ranges)
                if start <= midpoint <= end
            ]
            if not candidates:
                continue
            index = max(candidates, key=lambda item: (
                group[item].exterior, group[item].height, group[item].thickness_m, -item
            ))
            shared = infer_shared and any(
                group[first].room_identifier != group[second].room_identifier
                and group[first].normal.dot(group[second].normal) < -0.9999
                and (shared_thickness_m is None or _collinear(group[first], group[second], tolerance))
                for position, first in enumerate(candidates)
                for second in candidates[position + 1:]
            )
            exterior = group[index].exterior and not shared
            thickness = shared_thickness_m if shared and shared_thickness_m is not None else group[index].thickness_m
            if pieces and pieces[-1][0] == index and pieces[-1][3] == exterior and pieces[-1][4] == thickness and abs(pieces[-1][2] - low) <= tolerance:
                pieces[-1] = (index, pieces[-1][1], high, exterior, thickness)
            else:
                pieces.append((index, low, high, exterior, thickness))
        for index, low, high, exterior, thickness in pieces:
            result.append(replace(
                group[index],
                start=Point3D(reference.start.x + ux * low, reference.start.y + uy * low, reference.start.z),
                end=Point3D(reference.start.x + ux * high, reference.start.y + uy * high, reference.end.z),
                exterior=exterior,
                thickness_m=thickness,
            ))
    return result


def wall_axes(segments, scale: float, axis: str = "centerline", source_elevations=None, shared_thickness_m: float | None = None, source_thicknesses=None) -> list:
    if axis not in {"centerline", "surface"}:
        raise ValueError("Wall axis requires centerline or surface")
    source = list(segments)
    if axis == "surface":
        return source
    tolerance = 0.1 / scale
    shifted = []
    for segment in source:
        distance = segment.thickness_m * 1000.0 / scale / 2.0 if segment.exterior else 0.0
        horizontal_squared = segment.normal.x ** 2 + segment.normal.y ** 2
        factor = distance / horizontal_squared if horizontal_squared > 1e-24 else 0.0
        dx = segment.normal.x * factor
        dy = segment.normal.y * factor
        shifted.append(replace(
            segment,
            start=Point3D(segment.start.x + dx, segment.start.y + dy, segment.start.z),
            end=Point3D(segment.end.x + dx, segment.end.y + dy, segment.end.z),
        ))
    endpoints = []
    for index, segment in enumerate(source):
        endpoints.extend(((index, "start", segment.start), (index, "end", segment.end)))
    for index, attribute, point in endpoints:
        incident = []
        for other_index, other in enumerate(source):
            if other_index == index:
                continue
            if not _same_elevation(source[index], other, tolerance, source_elevations):
                continue
            if point_on_segment(point, other.start, other.end, tolerance):
                incident.append(other_index)
        if not incident:
            continue
        candidates = []
        current = shifted[index]
        for other_index in incident:
            other = shifted[other_index]
            intersection = line_intersection(current.start, current.end, other.start, other.end)
            if intersection is None:
                continue
            limit = max(
                source[index].thickness_m,
                source[other_index].thickness_m,
            ) * 1000.0 / scale * 10.0 + tolerance
            distance = hypot(intersection.x - point.x, intersection.y - point.y)
            if distance <= limit:
                direction_x = source[index].end.x - source[index].start.x
                direction_y = source[index].end.y - source[index].start.y
                projection = (intersection.x - point.x) * direction_x + (intersection.y - point.y) * direction_y
                candidates.append((other.exterior, projection, intersection))
        if candidates:
            sign = 1 if attribute == "start" else -1
            candidate = min(candidates, key=lambda item: (item[1] * sign, not item[0]))[2]
            shifted[index] = replace(current, **{attribute: candidate})
    connectors = []
    for index, attribute, point in endpoints:
        current = shifted[index]
        endpoint = getattr(current, attribute)
        if any(
            index != other_index and _same_elevation(current, other, tolerance, source_elevations)
            and point_on_segment(endpoint, other.start, other.end, tolerance)
            for other_index, other in enumerate(shifted)
        ) or any(
            _same_elevation(current, item, tolerance, source_elevations)
            and point_on_segment(endpoint, item.start, item.end, tolerance)
            for item in connectors
        ):
            continue
        candidates = []
        for other_index, other in enumerate(source):
            if other_index == index or not _same_elevation(source[index], other, tolerance, source_elevations):
                continue
            if not point_on_segment(point, other.start, other.end, tolerance):
                continue
            if not _collinear(source[index], other, tolerance):
                continue
            target = _closest_point(endpoint, shifted[other_index].start, shifted[other_index].end)
            distance = hypot(target.x - endpoint.x, target.y - endpoint.y)
            limit = max(source[index].thickness_m, other.thickness_m) * 1000.0 / scale * 10.0 + tolerance
            if tolerance < distance <= limit:
                candidates.append((distance, other_index, target))
        if candidates:
            _, other_index, target = min(candidates, key=lambda item: (item[0], item[1]))
            thickness = source_thicknesses.get(current.face_identifier, current.thickness_m) if shared_thickness_m is not None and source_thicknesses is not None else current.thickness_m
            connectors.append(AxisConnector(
                start=endpoint,
                end=target,
                thickness_m=thickness,
                height=current.height,
                exterior=current.exterior,
                room_identifier=current.room_identifier,
                face_identifier=current.face_identifier,
                normal=current.normal,
                adjoining_face_identifier=source[other_index].face_identifier,
            ))
    if shared_thickness_m is not None:
        shifted = _preserve_single_side_thickness(source, shifted, shared_thickness_m, tolerance, source_elevations, source_thicknesses)
    return _deduplicate_sections(shifted, tolerance, source_elevations=source_elevations) + connectors


def _preserve_single_side_thickness(source, shifted, shared_thickness_m: float, tolerance: float, source_elevations=None, source_thicknesses=None) -> list:
    result = []
    for original, current in zip(source, shifted):
        source_thickness = source_thicknesses.get(original.face_identifier, original.thickness_m) if source_thicknesses is not None else original.thickness_m
        if original.exterior or original.thickness_m != shared_thickness_m or original.thickness_m == source_thickness:
            result.append(current)
            continue
        others = [
            other for other in source
            if other is not original
            and _same_elevation(original, other, tolerance, source_elevations)
            and _collinear(original, other, tolerance)
        ]
        dx, dy = current.end.x - current.start.x, current.end.y - current.start.y
        size = hypot(dx, dy)
        if size <= tolerance:
            result.append(current)
            continue
        ux, uy = dx / size, dy / size
        ranges = []
        cuts = [0.0, size]
        for other in [original, *others]:
            low, high = sorted((point.x - current.start.x) * ux + (point.y - current.start.y) * uy for point in (other.start, other.end))
            low, high = max(0.0, low), min(size, high)
            if high - low > tolerance:
                ranges.append((low, high, other))
                cuts.extend((low, high))
        unique = []
        for value in sorted(cuts):
            if not unique or value - unique[-1] > tolerance:
                unique.append(value)
        for low, high in zip(unique, unique[1:]):
            midpoint = (low + high) / 2.0
            selected = next((other for start, end, other in ranges if start <= midpoint <= end), None)
            if selected is None:
                selected = replace(current, thickness_m=source_thickness)
            result.append(replace(
                selected,
                start=Point3D(current.start.x + ux * low, current.start.y + uy * low, current.start.z),
                end=Point3D(current.start.x + ux * high, current.start.y + uy * high, current.end.z),
                exterior=current.exterior,
            ))
    return result


def _closest_point(point: Point3D, start: Point3D, end: Point3D) -> Point3D:
    dx = end.x - start.x
    dy = end.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return start
    parameter = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_squared
    parameter = max(0.0, min(1.0, parameter))
    return Point3D(start.x + parameter * dx, start.y + parameter * dy, point.z)


def point_on_segment(point: Point3D, start: Point3D, end: Point3D, tolerance: float) -> bool:
    dx = end.x - start.x
    dy = end.y - start.y
    length = hypot(dx, dy)
    if length <= tolerance:
        return hypot(point.x - start.x, point.y - start.y) <= tolerance
    cross = abs((point.x - start.x) * dy - (point.y - start.y) * dx)
    if cross > tolerance * length:
        return False
    projection = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length
    return -tolerance <= projection <= length + tolerance


def line_intersection(a: Point3D, b: Point3D, c: Point3D, d: Point3D) -> Point3D | None:
    ux = b.x - a.x
    uy = b.y - a.y
    vx = d.x - c.x
    vy = d.y - c.y
    determinant = ux * vy - uy * vx
    if abs(determinant) <= hypot(ux, uy) * hypot(vx, vy) * 1e-10:
        return None
    parameter = ((c.x - a.x) * vy - (c.y - a.y) * vx) / determinant
    return Point3D(a.x + parameter * ux, a.y + parameter * uy, a.z)
