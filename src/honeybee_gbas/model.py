"""Honeybee model geometry and source metadata helpers for native DWG export."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, replace
from math import isfinite, sqrt
from typing import Iterable

from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from honeybee.units import conversion_factor_to_meters
from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
from shapely.geometry import Polygon
from shapely.ops import unary_union


EXTERIOR_CONDITIONS = {"Outdoors", "Ground"}


@dataclass(frozen=True)
class WallSegment:
    start: Point3D
    end: Point3D
    thickness_m: float
    height: float
    exterior: bool
    room_identifier: str
    face_identifier: str
    normal: Vector3D

    @property
    def length(self) -> float:
        return self.start.distance_to_point(self.end)

    @property
    def midpoint(self) -> Point3D:
        return Point3D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
            (self.start.z + self.end.z) / 2,
        )


@dataclass(frozen=True)
class OpeningRect:
    identifier: str
    kind: str
    story: str
    room_identifier: str
    host_identifier: str
    operable: bool
    width: float
    height: float
    sill: float
    start: Point3D
    end: Point3D
    center: Point3D
    normal: Vector3D
    host_thickness_m: float
    host_exterior: bool
    construction: str = ""
    u_factor: float = 0.0
    shgc: float = 0.0
    host_type: str = "Wall"
    boundary: tuple[Point3D, ...] = ()
    vertical_height: float = 0.0


def owner_room(component):
    current = component
    while current is not None:
        if isinstance(current, Room):
            return current
        current = getattr(current, "parent", None)
    return None


def unit_scale(units: str) -> float:
    return conversion_factor_to_meters(units) * 1000.0


def story_names(model: Model) -> list[str]:
    elevations: dict[str, float] = {}
    for room in model.rooms:
        story = room.story or "Unassigned"
        elevation = room_floor_elevation(room)
        if story not in elevations or elevation < elevations[story]:
            elevations[story] = elevation
    return [name for name, _ in sorted(elevations.items(), key=lambda item: (item[1], item[0]))]


def room_elevation_bounds(room: Room) -> tuple[float, float]:
    elevations = [point.z for face in room.faces for point in face.geometry.vertices]
    if not elevations:
        raise ValueError("Room elevation bounds require enclosure faces")
    return min(elevations), max(elevations)


def room_floor_elevation(room: Room) -> float:
    faces = room.horizontal_floor_boundaries()
    air = [face for face in room.faces if str(face.type) == "AirBoundary" and face.normal.z < -0.9999]
    if air:
        return min([face.geometry.min.z for face in air] + [face.min.z for face in faces])
    if faces:
        return min(face.min.z for face in faces)
    return room_elevation_bounds(room)[0]


def room_floor_area(room: Room) -> float:
    return float(room.floor_area)


def room_plan_boundaries(room: Room) -> tuple[Face3D, ...]:
    if any(str(face.type) == "AirBoundary" and face.normal.z < -0.9999 for face in room.faces):
        return (room.horizontal_boundary(),)
    boundaries = room.horizontal_floor_boundaries()
    if boundaries:
        return tuple(boundaries)
    return ()


def room_height(room: Room) -> float:
    lower, upper = room_elevation_bounds(room)
    return float(upper - lower)


def room_floor_face(room: Room) -> Face3D | None:
    faces = room.horizontal_floor_boundaries()
    if not faces:
        return None
    return max(faces, key=lambda face: face.area)


def room_floor_boundary(room: Room) -> tuple[Point3D, ...]:
    face = room_floor_face(room)
    if face is not None:
        return tuple(face.boundary)
    if room.faces:
        return tuple(min(room.faces, key=lambda item: item.geometry.min.z).geometry.boundary)
    return tuple()


def face_thickness_m(face: Face) -> float:
    try:
        return float(face.properties.energy.construction.thickness)
    except Exception:
        return 0.0


def face_height(face: Face) -> float:
    return float(face.max.z - face.min.z)


def is_exterior(face: Face) -> bool:
    return str(face.boundary_condition) in EXTERIOR_CONDITIONS


class _ThermalHost:
    def __init__(self, opening, altitude: float):
        self.opening = opening
        self.altitude = altitude

    def __getattr__(self, name):
        return getattr(self.opening, name)


def thermal_properties(opening):
    properties = opening.properties.energy
    altitude = opening.altitude
    for canonical in (-90.0, 0.0, 90.0):
        if altitude != canonical and abs(altitude - canonical) < 1e-9:
            return properties.duplicate(_ThermalHost(opening, canonical))
    return properties


def wall_bottom_edge(face: Face) -> tuple[Point3D, Point3D] | None:
    boundary = face.geometry.boundary
    if len(boundary) < 2:
        return None
    lowest = min(point.z for point in boundary)
    best: tuple[float, Point3D, Point3D] | None = None
    for index, point in enumerate(boundary):
        nxt = boundary[(index + 1) % len(boundary)]
        if abs(point.z - lowest) > 1e-6 or abs(nxt.z - lowest) > 1e-6:
            continue
        length = point.distance_to_point(nxt)
        if best is None or length > best[0]:
            best = (length, point, nxt)
    if best is None:
        return None
    return best[1], best[2]


def segment_key(start: Point3D, end: Point3D) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    first = (round(start.x, 3), round(start.y, 3), round(start.z, 3))
    second = (round(end.x, 3), round(end.y, 3), round(end.z, 3))
    return tuple(sorted((first, second)))


def wall_segments(model: Model, story: str | None = None) -> list[WallSegment]:
    segments: dict[tuple, WallSegment] = {}
    for room in model.rooms:
        if story and (room.story or "Unassigned") != story:
            continue
        for face in room.faces:
            if str(face.type).lower() != "wall":
                continue
            edge = wall_bottom_edge(face)
            if edge is None:
                continue
            segment = WallSegment(
                start=edge[0],
                end=edge[1],
                thickness_m=face_thickness_m(face),
                height=face_height(face),
                exterior=is_exterior(face),
                room_identifier=room.identifier,
                face_identifier=face.identifier,
                normal=face.normal,
            )
            key = segment_key(edge[0], edge[1])
            existing = segments.get(key)
            if existing is None:
                segments[key] = segment
            else:
                segments[key] = replace(
                    existing,
                    thickness_m=max(existing.thickness_m, segment.thickness_m),
                    height=max(existing.height, segment.height),
                    exterior=existing.exterior or segment.exterior,
                )
    return list(segments.values())


def opening_rect(opening, kind: str, units: str = "Meters") -> OpeningRect:
    geometry = opening.geometry
    bottom = None
    top = None
    try:
        bottom, top, _ = geometry.extract_rectangle(1e-3)
    except (TypeError, ValueError):
        bottom = None
        top = None
    if bottom is None or top is None:
        boundary = geometry.boundary
        low = min(point.z for point in boundary)
        pairs = [
            (boundary[index], boundary[(index + 1) % len(boundary)])
            for index in range(len(boundary))
            if abs(boundary[index].z - low) <= 1e-6
            and abs(boundary[(index + 1) % len(boundary)].z - low) <= 1e-6
        ]
        if pairs:
            start, end = max(pairs, key=lambda item: item[0].distance_to_point(item[1]))
        else:
            start, end = boundary[0], boundary[1]
        polygon = geometry.boundary_polygon2d
        width = float(polygon.max.x - polygon.min.x)
        height = float(polygon.max.y - polygon.min.y)
        sill = float(low)
        center = Point3D(
            (start.x + end.x) / 2,
            (start.y + end.y) / 2,
            (start.z + end.z) / 2,
        )
    else:
        start = bottom.p1
        end = bottom.p2
        width = float(bottom.length)
        height = float(bottom.distance_to_point(top.p1))
        sill = float(min(bottom.p1.z, bottom.p2.z))
        center = Point3D(
            (bottom.p1.x + bottom.p2.x) / 2,
            (bottom.p1.y + bottom.p2.y) / 2,
            (bottom.p1.z + bottom.p2.z) / 2,
        )
    face = opening.parent
    room = face.parent if face is not None else None
    floors = room.horizontal_floor_boundaries() if room is not None else ()
    floor_z = min(item.min.z for item in floors) if floors else room_elevation_bounds(room)[0] if room is not None else sill
    sill = sill - floor_z
    construction = ""
    u_factor = 0.0
    shgc = 0.0
    try:
        construction = opening.properties.energy.construction.identifier
        properties = thermal_properties(opening)
        u_factor = float(properties.u_factor(units))
        shgc = float(properties.shgc(units))
    except Exception:
        pass
    return OpeningRect(
        identifier=opening.identifier,
        kind=kind,
        story=(room.story or "Unassigned") if room is not None else "Components",
        room_identifier=room.identifier if room is not None else "",
        host_identifier=face.identifier if face is not None else "",
        operable=bool(getattr(opening, "is_operable", False)),
        width=width,
        height=height,
        sill=sill,
        start=start,
        end=end,
        center=center,
        normal=geometry.normal,
        host_thickness_m=face_thickness_m(face) if face is not None else 0.0,
        host_exterior=is_exterior(face) if face is not None else False,
        construction=construction,
        u_factor=u_factor,
        shgc=shgc,
        host_type=str(face.type) if face is not None else "",
        boundary=tuple(geometry.boundary),
        vertical_height=float(geometry.max.z - geometry.min.z),
    )


def openings(model: Model, story: str | None = None, unique: bool = False) -> list[OpeningRect]:
    result: list[OpeningRect] = []
    seen = set()
    for room in model.rooms:
        if story and (room.story or "Unassigned") != story:
            continue
        for face in room.faces:
            for aperture in face.apertures:
                if unique and aperture.identifier in seen:
                    continue
                result.append(opening_rect(aperture, "Window", model.units))
                seen.add(aperture.identifier)
                if unique and str(aperture.boundary_condition) == "Surface":
                    seen.add(aperture.boundary_condition.boundary_condition_objects[0])
            for door in face.doors:
                if unique and door.identifier in seen:
                    continue
                result.append(opening_rect(door, "Door", model.units))
                seen.add(door.identifier)
                if unique and str(door.boundary_condition) == "Surface":
                    seen.add(door.boundary_condition.boundary_condition_objects[0])
    return result


def room_names(model: Model) -> dict[str, str]:
    identifiers = [room.identifier for room in model.rooms]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Room names require unique source identities")
    namespace = _room_namespace(model)
    identities = {identifier: identifier[len(namespace):] for identifier in identifiers}
    names = {}
    for room in model.rooms:
        name = room.display_name
        names[room.identifier] = name if name and name.strip() and name != room.identifier else identities[room.identifier]
    counts = Counter(names.values())
    reserved = {name for name, count in counts.items() if count == 1}
    numbers = Counter()
    for identifier in sorted(identifiers):
        name = names[identifier]
        if counts[name] > 1:
            numbers[name] += 1
            candidate = f"{name} [{numbers[name]}]"
            while candidate in reserved:
                numbers[name] += 1
                candidate = f"{name} [{numbers[name]}]"
            names[identifier] = candidate
            reserved.add(candidate)
    return names


def _room_namespace(model: Model) -> str:
    if not model.rooms:
        return ""
    identifier = model.identifier
    candidates = []
    if any(character.isalpha() for character in identifier):
        candidates.extend(identifier + separator for separator in ("-", "_", "."))
    for match in re.finditer(r"[-_.]+", identifier):
        parts = re.split(r"[-_.]+", identifier[:match.start()])
        if len(parts) >= 2 and all(part.isalpha() for part in parts):
            candidates.append(identifier[:match.end()])
    for prefix in sorted(candidates, key=lambda value: (-len(value), value)):
        if all(room.identifier.startswith(prefix) and len(room.identifier) > len(prefix) for room in model.rooms):
            return prefix
    return ""


def room_code(identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Calculation room codes require a source identifier")
    return "H" + hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:12]


def room_codes(identifiers: Iterable[str]) -> dict[str, str]:
    result = {}
    symbols = set()
    for identifier in identifiers:
        code = room_code(identifier)
        symbol = ("Rm-" + code).upper()
        if identifier in result or symbol in symbols:
            raise ValueError("Calculation room codes require unique source identities and DOE-2 symbols")
        result[identifier] = code
        symbols.add(symbol)
    return result


def source_room_codes(manifest: dict) -> dict[str, str]:
    result = {}
    for row in manifest.get("rooms", []):
        code = row.get("native_code", row["identifier"])
        if code in result:
            raise ValueError("Native room mapping requires unique calculation codes")
        result[code] = row["identifier"]
    return result


def inspect_model(model) -> dict:
    issues = []
    faces = [face for room in model.rooms for face in room.faces]
    wall_faces = [face for face in faces if str(face.type) == "Wall"]
    opening_faces = [opening for face in faces for opening in (*face.apertures, *face.doors)]
    orphaned = {
        "faces": len(model.orphaned_faces),
        "apertures": len(model.orphaned_apertures),
        "doors": len(model.orphaned_doors),
        "shades": len(model.orphaned_shades),
    }
    scale = unit_scale(model.units)
    for shade in model.shades:
        issues.append(_issue("shade_geometry", shade.identifier, "reference_3d_and_shading_assignment"))
    for mesh in model.shade_meshes:
        issues.append(_issue("shade_mesh", mesh.identifier, "reference_3d_and_shading_assignment"))
    for face in wall_faces:
        if abs(face.normal.z) > 1e-4:
            issues.append(_issue("inclined_wall", face.identifier, "plan_projection"))
        if wall_bottom_edge(face) is None:
            issues.append(_issue("wall_bottom_profile", face.identifier, "profile_projection"))
        if not _rectangle_complete(face.geometry, 0.1 / scale):
            issues.append(_issue("wall_profile", face.identifier, "section_intersection"))
    for opening in opening_faces:
        if str(opening.parent.type) != "Wall":
            issues.append(_issue("roof_or_floor_opening", opening.identifier, "roof_plan"))
        elif abs(opening.normal.z) > 1e-4:
            issues.append(_issue("inclined_opening", opening.identifier, "plan_projection"))
        elif not _rectangle_complete(opening.geometry, 0.1 / scale):
            issues.append(_issue("opening_profile", opening.identifier, "profile_geometry"))
    for room in model.rooms:
        floors = room.horizontal_floor_boundaries()
        if len(floors) > 1:
            issues.append(_issue("multiple_floor_regions", room.identifier, "multiple_boundaries"))
        if any(face.has_holes for face in floors):
            issues.append(_issue("floor_holes", room.identifier, "inner_boundaries"))
    if not model.rooms:
        issues.append(_issue("component_collection", model.identifier, "component_plan"))
    elif orphaned["faces"] or orphaned["apertures"] or orphaned["doors"]:
        issues.append(_issue("orphaned_components", model.identifier, "component_plan"))
    counts = Counter(issue["code"] for issue in issues)
    route = "native_plan" if not issues else "plan_adaptation"
    if not model.rooms:
        route = "component_collection"
    return {
        "model": model.identifier,
        "units": model.units,
        "rooms": len(model.rooms),
        "stories": story_names(model),
        "wall_faces": len(wall_faces),
        "wall_segments": len(wall_segments(model)),
        "openings": len(opening_faces),
        "orphaned": orphaned,
        "shades": len(model.shades),
        "shade_meshes": len(model.shade_meshes),
        "route": route,
        "verification": "BESI runtime roundtrip",
        "issue_counts": dict(sorted(counts.items())),
        "issues": issues,
    }


def _issue(code: str, identifier: str, adaptation: str) -> dict:
    return {"code": code, "identifier": identifier, "adaptation": adaptation}


def _rectangle_complete(geometry, tolerance: float) -> bool:
    try:
        result = geometry.extract_rectangle(tolerance)
        return result is not None and not result[2]
    except (TypeError, ValueError, AssertionError):
        return False

LAYER = "日-建筑"


def source_triangles(component, kind, floor, scale: float) -> list:
    geometry = component.geometry.triangulated_mesh3d if kind == "Shade" else component.geometry
    vertices = [(point.x * scale + floor.offset_mm[0], point.y * scale + floor.offset_mm[1],
                 point.z * scale - floor.source_elevation_mm) for point in geometry.vertices]
    if any(not all(isfinite(value) for value in point) for point in vertices):
        raise ValueError("Shade vertices require finite coordinates")
    faces = []
    for indices in geometry.faces:
        if len(indices) == 3:
            faces.append(tuple(vertices[index] for index in indices))
        elif len(indices) == 4:
            faces.extend(tuple(vertices[indices[index]] for index in triangle)
                         for triangle in ((0, 1, 2), (0, 2, 3)))
        else:
            raise ValueError("Shade mesh faces require three or four vertices")
    areas = [_triangle_area(face) for face in faces]
    if any(not isfinite(area) for area in areas):
        raise ValueError("Shade mesh requires finite triangular faces")
    faces = [face for face, area in zip(faces, areas) if area > 1e-6]
    if not faces:
        raise ValueError("Shade mesh requires nondegenerate triangular faces")
    if kind == "Shade":
        source_area = component.geometry.area * scale * scale
        actual_area = sum(_triangle_area(face) for face in faces)
        if not isfinite(source_area) or abs(actual_area - source_area) > max(0.01, source_area * 1e-8):
            raise ValueError("Shade triangulation requires matching source area")
    return faces


def triangles_match(expected, actual, tolerance: float = 0.1) -> bool:
    try:
        reference_groups = _plane_groups(expected)
        actual_groups = _plane_groups(actual)
        aligned = {}
        for key, polygons in actual_groups.items():
            candidates = [reference for reference in reference_groups if max(abs(a - b) for a, b in zip(reference[:3], key[:3])) <= 1e-7 and abs(reference[3] - key[3]) <= tolerance]
            if not candidates:
                return False
            selected = min(candidates, key=lambda reference: (sum((a - b) ** 2 for a, b in zip(reference[:3], key[:3])), abs(reference[3] - key[3])))
            aligned.setdefault(selected, []).extend(polygons)
        if set(reference_groups) != set(aligned):
            return False
        for key, reference in reference_groups.items():
            left, right = unary_union(reference), unary_union(aligned[key])
            if (left.is_empty or right.is_empty or left.hausdorff_distance(right) > tolerance or
                    left.symmetric_difference(right).area > max(tolerance * tolerance, left.area * 1e-10)):
                return False
        return True
    except (ValueError, ArithmeticError):
        return False


def _plane_groups(faces) -> dict:
    groups = {}
    for first, second, third in faces:
        a = tuple(second[index] - first[index] for index in range(3))
        b = tuple(third[index] - first[index] for index in range(3))
        cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        length = sqrt(sum(value * value for value in cross))
        if not isfinite(length) or length <= 1e-6:
            raise ValueError("Shade mesh requires nondegenerate triangles")
        orientation = next(value for value in cross if abs(value / length) > 1e-8)
        sign = 1 if orientation > 0 else -1
        normal = tuple(sign * value / length for value in cross)
        axis = max(range(3), key=lambda index: round(abs(normal[index]), 8))
        distance = sum(normal[index] * first[index] for index in range(3))
        key = (*[round(value, 8) for value in normal], round(distance, 3))
        dimensions = [index for index in range(3) if index != axis]
        polygon = Polygon([(point[dimensions[0]], point[dimensions[1]]) for point in (first, second, third)])
        groups.setdefault(key, []).append(polygon)
    return groups


def _triangle_area(points) -> float:
    first, second, third = points
    a = tuple(second[index] - first[index] for index in range(3))
    b = tuple(third[index] - first[index] for index in range(3))
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    return sqrt(sum(value * value for value in cross)) / 2
