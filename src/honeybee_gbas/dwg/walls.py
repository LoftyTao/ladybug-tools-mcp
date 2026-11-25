"""Native wall completion, opening clearance and opening rehosting."""

from __future__ import annotations

from itertools import combinations
from math import atan2, cos, hypot, sin, tan

from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Face3D, Plane, Point3D, Vector3D
from shapely import set_precision
from shapely.geometry import LineString, MultiPoint, Polygon, box
from shapely.ops import triangulate, unary_union

from .. import model as hb
from .geometry import OVERLAY_PRECISION_MM, _Surface, _compare, _polygon, coverage, polygons, wall_point, wall_points
from .geometry import sloped_oblique_wall, source_oblique_wall
from .records import Filer, add_native, opening, space, wall, write_inner_rings
from .surfaces import assigned_walls, planar_polygon, wall_boundary


def source_wall(face, room, floor, geometry=None, allow_base=False):
    geometry = geometry or face.geometry
    if abs(face.normal.z) > 1e-4 or geometry.holes:
        return None
    scale = floor["scale"]
    if any(max(item.plane.distance_to_point(point) * scale for point in (*item.boundary, *(point for ring in item.holes or () for point in ring))) > 0.001 for item in (geometry, face.geometry)):
        return None
    bottom = min(point.z for point in geometry.boundary) * scale
    offset = bottom - hb.room_floor_elevation(room) * scale
    if offset < -0.5 or offset <= 0.5 and not allow_base:
        return None
    ux, uy = -face.normal.y, face.normal.x
    length = hypot(ux, uy)
    ux, uy = ux / length, uy / length
    origin = geometry.boundary[0].scale(scale)
    coordinates = [((point.x * scale - origin.x) * ux + (point.y * scale - origin.y) * uy, point.z * scale - bottom) for point in geometry.boundary]
    polygon = set_precision(Polygon(coordinates), OVERLAY_PRECISION_MM)
    if not polygon.is_valid or polygon.interiors or polygon.area <= 1:
        return None
    extent_low, base, extent_high, top = polygon.bounds
    boundary = list(polygon.exterior.coords)[:-1]
    base_positions = [x for x, z in boundary if abs(z) <= 1e-6]
    if len(base_positions) < 2:
        return None
    low, high = min(base_positions), max(base_positions)
    if high - low <= 0.01:
        return None
    first = next((index for index, (x, z) in enumerate(boundary) if abs(x - low) <= 1e-6 and abs(z) <= 1e-6), None)
    last = next((index for index, (x, z) in enumerate(boundary) if abs(x - high) <= 1e-6 and abs(z) <= 1e-6), None)
    if first is None or last is None:
        return None
    chains = []
    for direction in (1, -1):
        chain = [boundary[first]]
        index = first
        while index != last:
            index = (index + direction) % len(boundary)
            chain.append(boundary[index])
        chains.append(chain)
    lower = next((index for index, chain in enumerate(chains) if all(abs(z) <= 1e-6 for x, z in chain)), None)
    if lower is None:
        return None
    upper = chains[1 - lower]
    if len(upper) > 2 and abs(upper[1][0] - low) <= 1e-6:
        upper = upper[1:]
    if len(upper) > 2 and abs(upper[-2][0] - high) <= 1e-6:
        upper = upper[:-1]
    profile = [(x - low, z) for x, z in upper]
    envelope = Polygon([(low, 0), (high, 0), *[(low + x, z) for x, z in reversed(profile)]])
    if abs(base) > 0.5 or polygon.symmetric_difference(envelope).area > max(1.0, polygon.area * 1e-8):
        return None
    dx, dy = floor["offset_mm"]
    row = {"identifier": face.identifier, "source_identifiers": [face.identifier], "story": floor["story"], "source_room": room.identifier, "start_mm": (origin.x + low * ux + dx, origin.y + low * uy + dy, bottom - floor["reference_elevation_mm"]), "end_mm": (origin.x + high * ux + dx, origin.y + high * uy + dy, bottom - floor["reference_elevation_mm"]), "height_mm": top, "thickness_mm": max(1.0, hb.face_thickness_m(face) * 1000), "openings": [], "neighbors": [0, 0, 0, 0], "left_space": floor["room_handle"], "right_space": 0, "source_elevated": True, "profile_status": "source_elevated_native_wall"}
    row["source_elevated"] = offset > 0.5
    if extent_low < low - 1e-6 or extent_high > high + 1e-6 or any(second[0] < first[0] - 1e-6 for first, second in zip(upper, upper[1:])):
        return None
    if any(abs(z - top) > 0.01 for x, z in profile):
        row["profile_mm"] = profile
    source = geometry.scale(scale)
    candidate = Face3D(wall_boundary(row, floor))
    if max(source.plane.distance_to_point(point) for point in candidate.boundary) > 0.001 or planar_polygon(source, source.plane).symmetric_difference(planar_polygon(candidate, source.plane)).area > max(1.0, source.area * 1e-8):
        return None
    return row


def sloped_base_wall(face, room, floor, geometry):
    if abs(face.normal.z) > 1e-4 or geometry.holes:
        return None
    scale = floor["scale"]
    source = geometry.scale(scale)
    if source.area <= 1.0 or max(source.plane.distance_to_point(point) for point in source.boundary) > 0.001:
        return None
    ux, uy = -face.normal.y, face.normal.x
    horizontal = hypot(ux, uy)
    ux, uy = ux / horizontal, uy / horizontal
    points = list(source.boundary)
    for index, first in enumerate(points):
        last = points[(index + 1) % len(points)]
        width = (last.x - first.x) * ux + (last.y - first.y) * uy
        first_index, last_index = index, (index + 1) % len(points)
        if width < 0:
            first, last = last, first
            first_index, last_index = last_index, first_index
            width = -width
        rise = last.z - first.z
        if width <= 0.01 or abs(rise) <= 0.001:
            continue
        length = hypot(width, rise)
        coordinates = [(((point.x - first.x) * ux + (point.y - first.y) * uy) * width / length + (point.z - first.z) * rise / length,
                        -((point.x - first.x) * ux + (point.y - first.y) * uy) * rise / length + (point.z - first.z) * width / length) for point in points]
        if any(along < -0.001 or along > length + 0.001 or height < -0.001 for along, height in coordinates):
            continue
        chains = []
        for direction in (1, -1):
            chain = [first_index]
            position = first_index
            while position != last_index:
                position = (position + direction) % len(points)
                chain.append(position)
            chains.append(chain)
        profile = [coordinates[position] for position in max(chains, key=len)]
        dx, dy = floor["offset_mm"]
        row = {"identifier": face.identifier, "source_identifiers": [face.identifier], "story": floor["story"], "source_room": room.identifier,
               "start_mm": (first.x + dx, first.y + dy, first.z - floor["reference_elevation_mm"]),
               "end_mm": (last.x + dx, last.y + dy, last.z - floor["reference_elevation_mm"]),
               "height_mm": source.max.z - source.min.z, "thickness_mm": max(1.0, hb.face_thickness_m(face) * 1000),
               "profile_mm": profile, "openings": [], "neighbors": [0, 0, 0, 0], "left_space": floor["room_handle"], "right_space": 0,
               "source_elevated": source.min.z - hb.room_floor_elevation(room) * scale > 0.5, "source_sloped_base": True,
               "profile_status": "source_sloped_base_native_polygon"}
        candidate = Face3D(wall_boundary(row, floor))
        if max(source.plane.distance_to_point(point) for point in candidate.boundary) <= 0.001 and planar_polygon(source, source.plane).symmetric_difference(planar_polygon(candidate, source.plane)).area <= max(1.0, source.area * 1e-8):
            return row
    return None


def complete_elevated_walls(drawing, codes, model, report):
    from .records import opening_block, opening_profile, wall_opening_bounds

    scale = hb.unit_scale(model.units)
    rooms = {row["identifier"]: row for row in report["rooms"]}
    floors = {row["story"]: row for row in report["floors"]}
    source_faces = {face.identifier: face for room in model.rooms for face in room.faces}
    source_ids = {}
    for room in model.rooms:
        for face in room.faces:
            for kind, children in (("Window", face.apertures), ("Door", face.doors)):
                for item in children:
                    key = (kind, tuple(sorted(tuple(round(value * scale, 2) for value in point) for point in item.geometry.boundary)))
                    source_ids.setdefault(key, []).append(item.identifier)
    additions = []
    removed = set()
    for room in model.rooms:
        native_room = rooms[room.identifier]
        floor = {**floors[native_room["story"]], "scale": scale, "room_handle": native_room["handle"]}
        sources = [_Surface(face.identifier, "Wall", face.geometry.scale(scale)) for face in room.faces if str(face.type) == "Wall"]
        valid = []
        for row in report["walls"]:
            if row.get("virtual_plan") or native_room["handle"] not in (row["left_space"], row["right_space"]):
                continue
            geometry = _Surface(str(row["handle"]), "Wall", Face3D(wall_boundary(row, floors[row["story"]])))
            if _compare(sources, [geometry], 0.05, 1.0)["extra_area_m2"] <= 1e-6:
                valid.append(([tuple(point) for point in geometry.geometry.boundary], []))
        for face in room.faces:
            if str(face.type) != "Wall":
                continue
            row = source_wall(face, room, floor)
            if row is None:
                continue
            comparison = coverage(face.geometry, valid, scale, tolerance=1e-8, check_extra=False)
            if comparison["source_area_m2"] - comparison["missing_area_m2"] > 1e-6:
                continue
            adjacent = getattr(face.boundary_condition, "boundary_condition_objects", ())
            other = source_faces.get(adjacent[0]) if adjacent else None
            if other is not None and rooms[other.parent.identifier]["story"] == row["story"]:
                row["right_space"] = rooms[other.parent.identifier]["handle"]
            entity = add_native(drawing, codes["SWR_WALL"], "建-墙-砖", row, wall, [(1000, face.identifier), (1000, "Wall"), (1000, "SourceElevated")])
            report["walls"].append(row)
            native_room["walls"].append(entity.handle)
            if row["right_space"]:
                rooms[other.parent.identifier]["walls"].append(entity.handle)
            report["wall_profile_geometry"].append({"handle": entity.handle, "identifier": face.identifier, "source_identifiers": [face.identifier], "status": "native_profile" if row.get("profile_mm") else "rectangular", "source_elevated": True, **({"profile_mm": row["profile_mm"]} if row.get("profile_mm") else {})})
            additions.append({"identifier": face.identifier, "source_room": room.identifier, "handle": entity.handle, "source_base_mm": row["start_mm"][2] + floor["reference_elevation_mm"]})
            valid.append(([tuple(point) for point in wall_boundary(row, floor)], []))
            start, end = row["start_mm"], row["end_mm"]
            segment = hb.WallSegment(Point3D((start[0] - floor["offset_mm"][0]) / scale, (start[1] - floor["offset_mm"][1]) / scale, 0), Point3D((end[0] - floor["offset_mm"][0]) / scale, (end[1] - floor["offset_mm"][1]) / scale, 0), row["thickness_mm"] / 1000, row["height_mm"] / scale, hb.is_exterior(face), room.identifier, face.identifier, face.normal)
            for kind, children in (("Window", face.apertures), ("Door", face.doors)):
                for item in children:
                    source = wall_opening_bounds(hb.opening_rect(item, kind, model.units))
                    piece = opening_profile(source, segment, scale, 0, hypot(end[0] - start[0], end[1] - start[1]), min(point.z for point in item.geometry.boundary) * scale, max(point.z for point in item.geometry.boundary) * scale, True)
                    if piece is None:
                        continue
                    key = (kind, tuple(sorted(tuple(round(value * scale, 2) for value in point) for point in item.geometry.boundary)))
                    identifiers = source_ids[key]
                    removed.update(child["handle"] for child in report["openings"] if set(identifiers).intersection(child["source_identifiers"]))
                    symbol = "DOOR" if kind == "Door" else "WIN"
                    width, height = piece["high"] - piece["low"], piece["top"] - piece["bottom"]
                    along = (piece["low"] + piece["high"]) / 2
                    length = segment.length * scale
                    x, y = start[0] + along * (end[0] - start[0]) / length, start[1] + along * (end[1] - start[1]) / length
                    child = {"identifier": item.identifier, "source_identifiers": identifiers, "kind": kind, "story": row["story"], "mark": f"{'M' if kind == 'Door' else 'C'}{len(report['openings']) + 1:03d}", "position_mm": (x, y, piece["bottom"] - floor["reference_elevation_mm"]), "width_mm": width, "height_mm": height, "angle_rad": atan2(end[1] - start[1], end[0] - start[0]), "wall": entity.handle, "block_2d": drawing.blocks[f"$ARCHSYS${symbol}2D"][0], "block_3d": opening_block(drawing, symbol, piece["profile"], row["thickness_mm"], atan2(end[1] - start[1], end[0] - start[0])), "clipping_blockers": [], "profile_mm": piece["profile"], "geometry_policy": "source_elevated_native_host"}
                    created = add_native(drawing, codes["SWR_OPENING"], "建-门窗", child, opening, [(1000, item.identifier), (1000, kind)])
                    row["openings"].append(created.handle)
                    report["openings"].append(child)
                    report["reference_openings"] = [reference for reference in report["reference_openings"] if not set(identifiers).intersection(reference.get("source_identifiers", [reference["identifier"]]))]
    if removed:
        report["openings"] = [row for row in report["openings"] if row["handle"] not in removed]
        drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
        for row in report["walls"]:
            row["openings"] = [handle for handle in row["openings"] if handle not in removed]
    from .records import connect_walls

    for story in {row["story"] for row in report["walls"]}:
        connect_walls([row for row in report["walls"] if row["story"] == story])
    report["elevated_walls"] = additions
    report["counts"]["native_elevated_walls"] = len(additions)


def elevated_inclined_wall(face, room, floor):
    return (face.normal.z > 1e-4 and face.identifier not in floor.get("shared_wall_ids", ())
            and (face.geometry.min.z - hb.room_floor_elevation(room)) * floor["scale"] > 1.0)


def source_native_wall(face, room, floor, geometry=None):
    if elevated_inclined_wall(face, room, floor):
        return None
    if abs(face.normal.z) > 1e-8:
        row = source_oblique_wall(face, room, floor, geometry) or sloped_oblique_wall(face, room, floor, geometry)
        if row is not None:
            return row
    return source_wall(face, room, floor, geometry, allow_base=True) or sloped_base_wall(face, room, floor, geometry or face.geometry)


def source_native_wall_reconstruction_rows(face, room, floor):
    row = source_native_wall(face, room, floor)
    if row is not None:
        row["source_reconstruction_method"] = "whole_source_native_wall"
        return [row]
    scale = floor["scale"]
    source = face.geometry.scale(scale)
    normal = face.normal
    horizontal = hypot(normal.x, normal.y)
    if source.holes or horizontal <= 1e-4 or max(source.plane.distance_to_point(point) for point in source.boundary) > 0.001:
        return []
    ux, uy = -normal.y / horizontal, normal.x / horizontal
    origin = source.boundary[0]
    def along(point):
        return (point.x - origin.x) * ux + (point.y - origin.y) * uy
    positions = sorted({along(point) for point in source.boundary})
    ranges = [(min(along(point.scale(scale)) for point in item.geometry.boundary), max(along(point.scale(scale)) for point in item.geometry.boundary)) for item in (*face.apertures, *face.doors)]
    middle = (positions[0] + positions[-1]) / 2
    candidates = {*positions[1:-1], *((low + high) / 2 for low, high in zip(positions, positions[1:]))}
    cuts = sorted(candidates, key=lambda value: (sum(low + 0.001 < value < high - 0.001 for low, high in ranges), abs(value - middle), value))
    expected = planar_polygon(source, source.plane)
    for cut in cuts:
        if min(cut - positions[0], positions[-1] - cut) <= 0.01:
            continue
        plane = Plane(n=Vector3D(ux, uy, 0), o=Point3D(origin.x + cut * ux, origin.y + cut * uy, origin.z))
        pieces = source.split_with_plane(plane, 0.001)
        if not pieces:
            continue
        rows = [source_native_wall(face, room, floor, piece.scale(1 / scale)) for piece in pieces]
        if any(row is None for row in rows):
            continue
        shapes = [planar_polygon(piece, source.plane) for piece in pieces]
        observed = unary_union(shapes)
        if expected.symmetric_difference(observed).area > 1.0 or sum(shape.area for shape in shapes) - observed.area > 1.0:
            continue
        for row in rows:
            row.update(source_reconstruction_method="whole_source_sdk_vertical_partition", source_reconstruction_cut_mm=cut)
        return rows
    return []


def source_native_wall_parts(face, room, floor, shape):
    scale = floor["scale"]
    geometry = face.geometry
    plane = geometry.plane
    normal = face.normal
    horizontal = hypot(normal.x, normal.y)
    if horizontal <= 1e-4 or max(plane.distance_to_point(point) * scale for point in (*geometry.boundary, *(point for ring in geometry.holes or () for point in ring))) > 0.001:
        return []
    origin = geometry.boundary[0].scale(scale)
    ux, uy = -normal.y / horizontal, normal.x / horizontal
    shift_x, shift_y = -normal.x * normal.z / horizontal ** 2, -normal.y * normal.z / horizontal ** 2
    def local(x, y):
        point = plane.xy_to_xyz(Point2D(x, y)).scale(scale)
        return (point.x - origin.x) * ux + (point.y - origin.y) * uy, point.z - origin.z
    def surface(shape):
        def point(x, z):
            return Point3D((origin.x + x * ux + z * shift_x) / scale, (origin.y + x * uy + z * shift_y) / scale, (origin.z + z) / scale)
        return Face3D(tuple(point(x, z) for x, z in list(shape.exterior.coords)[:-1]), plane=plane, holes=tuple(tuple(point(x, z) for x, z in list(ring.coords)[:-1]) for ring in shape.interiors) or None)
    result = []
    for part in polygons(shape):
        projected = set_precision(Polygon([local(x, y) for x, y in list(part.exterior.coords)[:-1]], [[local(x, y) for x, y in list(ring.coords)[:-1]] for ring in part.interiors]), OVERLAY_PRECISION_MM)
        source = surface(projected)
        whole = source_native_wall(face, room, floor, source)
        if whole is not None:
            result.append(whole)
            continue
        variants = []
        if not projected.interiors:
            source_mm = source.scale(scale)
            low_z, high_z = projected.bounds[1], projected.bounds[3]
            levels = sorted({z for x, z in projected.exterior.coords} | {min(point.z * scale - origin.z for point in item.geometry.boundary) for item in (*face.apertures, *face.doors) if low_z < min(point.z * scale - origin.z for point in item.geometry.boundary) < high_z})
            for base in levels[1:-1]:
                split = source_mm.split_with_plane(Plane(o=Point3D(0, 0, origin.z + base)), 0.001)
                pieces = [piece for piece in split or () if piece.min.z >= origin.z + base - 0.001 and piece.area > 1.0]
                rows = [source_native_wall(face, room, floor, piece.scale(1 / scale)) for piece in pieces]
                if rows and all(row is not None for row in rows):
                    for row in rows:
                        row.update(source_partition=True, source_partition_method="sdk_horizontal_source_partition")
                    shapes = [Polygon([((point.x - origin.x) * ux + (point.y - origin.y) * uy, point.z - origin.z) for point in piece.boundary]) for piece in pieces]
                    variants.append((rows, unary_union(shapes)))
                    break
        cuts = sorted({x for ring in (projected.exterior, *projected.interiors) for x, z in ring.coords})
        caps = {}
        low_z, high_z = projected.bounds[1] - 1, projected.bounds[3] + 1
        for low, high in zip(cuts, cuts[1:]):
            if high - low <= 0.01:
                continue
            for cell in polygons(projected.intersection(box(low, low_z, high, high_z))):
                if cell.area <= 1.0:
                    continue
                first = cell.intersection(LineString([(low, low_z), (low, high_z)]))
                last = cell.intersection(LineString([(high, low_z), (high, high_z)]))
                if first.is_empty or last.is_empty:
                    continue
                base = max(first.bounds[1], last.bounds[1])
                for cap in polygons(cell.intersection(box(low, base, high, high_z))):
                    if cap.area > 1.0:
                        caps.setdefault(base, []).append(cap)
        rows = []
        shapes = []
        for pieces in caps.values():
            for cap in polygons(unary_union(pieces)):
                row = source_native_wall(face, room, floor, surface(cap))
                if row is not None:
                    row.update(source_partition=True, source_partition_method="exact_horizontal_base_top_profile_caps")
                    rows.append(row)
                    shapes.append(cap)
        remainder = projected.difference(unary_union(shapes))
        for low, high in zip(cuts, cuts[1:]):
            if high - low <= 0.01:
                continue
            for cell in polygons(remainder.intersection(box(low, low_z, high, high_z))):
                if cell.area <= 1.0:
                    continue
                row = source_native_wall(face, room, floor, surface(cell))
                if row is not None:
                    row.update(source_partition=True, source_partition_method="exact_native_sloped_base_polygon")
                    rows.append(row)
                    shapes.append(cell)
        variants.append((rows, unary_union(shapes)))
        children = [Polygon([local(*plane.xyz_to_xy(point)) for point in item.geometry.boundary]).intersection(projected) for item in (*face.apertures, *face.doors)]
        def score(variant):
            rows, observed = variant
            residual = projected.difference(observed)
            openings = [child.intersection(residual) for child in children]
            opaque = residual.difference(unary_union(children))
            panel_parts = sum(1 + len(piece.interiors) * 2 for piece in polygons(opaque)) + sum(len(polygons(piece)) for piece in openings)
            return sum(piece.area > 1.0 for piece in openings), panel_parts, sum(piece.area for piece in openings), residual.area, len(rows)
        result.extend(min(variants, key=score)[0])
    return result


def remove_native_walls(drawing, report, handles):
    removed = set(handles)
    removed.update(row["handle"] for row in report["openings"] if row["wall"] in handles)
    drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
    report["walls"] = [row for row in report["walls"] if row["handle"] not in handles]
    report["openings"] = [row for row in report["openings"] if row["handle"] not in removed]
    report["wall_profile_geometry"] = [row for row in report["wall_profile_geometry"] if row["handle"] not in handles]
    report["elevated_walls"] = [row for row in report["elevated_walls"] if row["handle"] not in handles]
    for room in report["rooms"]:
        room["walls"] = [handle for handle in room["walls"] if handle not in handles]


def source_wall_reconstruction(face, room, floor, model, report, semantics, protected=None):
    scale = floor["scale"]
    plane = face.geometry.plane
    source = planar_polygon(face.geometry, plane, scale)
    floors = {row["story"]: row for row in report["floors"]}
    rows = []
    for row in report["walls"]:
        if row.get("virtual_plan") or row["story"] != floor["story"]:
            continue
        geometry = Face3D(wall_boundary(row, floors[row["story"]], scale))
        if abs(geometry.normal.dot(face.normal)) < 0.99999999 or any(plane.distance_to_point(point) * scale > 0.001 for point in geometry.boundary):
            continue
        candidate = planar_polygon(geometry, plane, scale)
        if candidate.intersection(source).area * scale ** 2 <= 1.0:
            continue
        if floor["room_handle"] not in (row["left_space"], row["right_space"]) or semantics.get(row["identifier"]) != semantics.get(face.identifier) or candidate.difference(source).area * scale ** 2 > 1.0:
            return None, []
        rows.append(row)
    if not rows:
        return None, []
    replacements = source_native_wall_reconstruction_rows(face, room, floor)
    if not replacements:
        return None, []
    others = {handle for row in rows for handle in (row["left_space"], row["right_space"]) if handle and handle != floor["room_handle"]}
    if len(others) > 1:
        return None, []
    for handle in others:
        owner = next(item for item in report["rooms"] if item["handle"] == handle)
        other = next(item for item in model.rooms if item.identifier == owner["identifier"])
        matching = [item for item in other.faces if str(item.type) == "Wall" and semantics.get(item.identifier) == semantics.get(face.identifier) and abs(item.normal.dot(face.normal)) > 0.99999999 and all(plane.distance_to_point(point) * scale <= 0.001 for point in item.geometry.boundary)]
        extra = source.difference(unary_union([planar_polygon(item.geometry, plane, scale) for item in matching])).area * scale ** 2
        if extra > 1.0:
            if protected is not None:
                protected.append({"identifier": face.identifier, "source_room": room.identifier, "protected_source_room": other.identifier, "shared_handles": [row["handle"] for row in rows], "whole_source_area_m2": source.area * (scale / 1000) ** 2, "protected_side_expansion_area_m2": extra / 1e6, "reason": "distinct_shared_side_top_profiles"})
            return None, []
    identifiers = list(dict.fromkeys([face.identifier, *(identifier for row in rows for identifier in row.get("source_identifiers", [row["identifier"]]))]))
    handles = [row["handle"] for row in rows]
    for handle in {floor["room_handle"], *others}:
        owner = next(item for item in report["rooms"] if item["handle"] == handle)
        if len(set(owner["walls"]).difference(handles)) + len(replacements) > 255:
            return None, []
    for replacement in replacements:
        vacant = "right_space" if replacement["left_space"] else "left_space"
        replacement[vacant] = next(iter(others), 0)
        replacement["source_identifiers"] = identifiers
        replacement["source_reconstruction"] = True
    return replacements, handles


def merge_coincident_walls(drawing, report, semantics):
    floors = {row["story"]: row for row in report["floors"]}
    removed = {}
    records = []
    walls = [row for row in report["walls"] if not row.get("virtual_plan") and row["height_mm"] > 0]
    for index, row in enumerate(walls):
        if row["handle"] in removed:
            continue
        geometry = Face3D(wall_boundary(row, floors[row["story"]]))
        shape = planar_polygon(geometry, geometry.plane)
        start, end = row["start_mm"], row["end_mm"]
        for other in walls[index + 1:]:
            if other["handle"] in removed or row["story"] != other["story"] or semantics.get(row["identifier"]) != semantics.get(other["identifier"]):
                continue
            candidate = Face3D(wall_boundary(other, floors[other["story"]]))
            if abs(geometry.normal.dot(candidate.normal)) < 0.999999 or any(geometry.plane.distance_to_point(point) > 0.01 for point in candidate.boundary):
                continue
            difference = shape.symmetric_difference(planar_polygon(candidate, geometry.plane)).area
            if difference > max(1.0, shape.area * 1e-9):
                continue
            direction = (end[0] - start[0]) * (other["end_mm"][0] - other["start_mm"][0]) + (end[1] - start[1]) * (other["end_mm"][1] - other["start_mm"][1])
            fields = ("left_space", "right_space") if direction > 0 else ("right_space", "left_space")
            if any(row[first] and other[second] and row[first] != other[second] for first, second in zip(("left_space", "right_space"), fields)):
                continue
            for first, second in zip(("left_space", "right_space"), fields):
                row[first] = row[first] or other[second]
            row["source_identifiers"] = list(dict.fromkeys([*row.get("source_identifiers", [row["identifier"]]), *other.get("source_identifiers", [other["identifier"]])]))
            row["openings"] = list(dict.fromkeys([*row["openings"], *other["openings"]]))
            removed[other["handle"]] = row["handle"]
            records.append({"handle": row["handle"], "reused_handle": other["handle"], "story": row["story"], "source_identifiers": row["source_identifiers"], "difference_mm2": difference})
    if removed:
        report["walls"] = [row for row in report["walls"] if row["handle"] not in removed]
        drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
        for room in report["rooms"]:
            room["walls"] = list(dict.fromkeys(removed.get(handle, handle) for handle in room["walls"]))
        for opening_row in report["openings"]:
            opening_row["wall"] = removed.get(opening_row["wall"], opening_row["wall"])
        report["wall_profile_geometry"] = [row for row in report["wall_profile_geometry"] if row["handle"] not in removed]
        source_ids = {row["handle"]: row.get("source_identifiers", [row["identifier"]]) for row in report["walls"]}
        for row in report["wall_profile_geometry"]:
            row["source_identifiers"] = source_ids[row["handle"]]
        report["elevated_walls"] = [row for row in report["elevated_walls"] if row["handle"] not in removed]
    return records


def refresh_room_space_references(drawing, report):
    rooms = {row["identifier"]: row for row in report["rooms"]}
    for entity in drawing.entities:
        tags = [value for code, value in entity.xdata if code == 1000]
        if len(tags) < 2 or tags[1] != "Room":
            continue
        row = rooms.get(tags[0])
        if row is None:
            continue
        references = []
        def body(writer, row=row, references=references):
            references.clear()
            space(Filer(writer, references), row, drawing)
        entity.body = body
        entity.references = references


def complete_native_wall_parts(drawing, codes, model, report, semantics=None, floor_mesh_rooms=()):
    from .records import connect_walls, hole_wall_handles

    scale = hb.unit_scale(model.units)
    rooms = {row["identifier"]: row for row in report["rooms"]}
    floors = {row["story"]: row for row in report["floors"]}
    interior = {face.identifier: face for room in model.rooms for face in room.faces
                if str(face.type) == "Wall" and str(face.boundary_condition) == "Surface"}
    shared_wall_ids = set()
    for face in interior.values():
        if face.normal.z <= 1e-4:
            continue
        adjacent_id, adjacent_room = face.boundary_condition.boundary_condition_objects
        other = interior.get(adjacent_id)
        if (other is not None and other.parent.identifier == adjacent_room and other.parent is not face.parent
                and other.boundary_condition.boundary_condition_objects == (face.identifier, face.parent.identifier)
                and rooms[adjacent_room]["story"] == rooms[face.parent.identifier]["story"]
                and (not semantics or semantics.get(face.identifier) == semantics.get(adjacent_id))
                and face.normal.dot(other.normal) < -0.999999
                and face.geometry.is_geometrically_equivalent(other.geometry, 0.001 / scale)):
            shared_wall_ids.add(face.identifier)
    additions = []
    reconstructions = []
    protected = []
    residuals = []
    for room in model.rooms:
        native = rooms[room.identifier]
        floor = {**floors[native["story"]], "scale": scale, "room_handle": native["handle"], "shared_wall_ids": shared_wall_ids}
        faces = sorted((face for face in room.faces if str(face.type) == "Wall"), key=lambda face: (-sum(item.area for item in (*face.apertures, *face.doors)), -face.area, face.identifier))
        for face in faces:
            if str(face.type) != "Wall":
                continue
            plane = face.geometry.plane
            matching = [geometry for geometry in assigned_walls(native, report, scale) if abs(geometry.normal.dot(face.normal)) > 0.9999 and all(plane.distance_to_point(point) * scale <= 0.5 for point in geometry.boundary)]
            source = planar_polygon(face.geometry, plane, scale)
            missing = source.difference(unary_union([planar_polygon(geometry, plane, scale) for geometry in matching]))
            if missing.area * scale ** 2 <= 1.0:
                continue
            replacements, removed = source_wall_reconstruction(face, room, floor, model, report, semantics or {}, protected)
            if replacements is not None:
                remove_native_walls(drawing, report, set(removed))
                rows = replacements
                reconstructions.append({"identifier": face.identifier, "source_room": room.identifier, "replaced_handles": removed, "source_area_m2": face.area * (scale / 1000) ** 2, "native_parts": len(rows), "method": rows[0]["source_reconstruction_method"]})
            else:
                rows = source_native_wall_parts(face, room, floor, missing)
            peer = interior.get(face.boundary_condition.boundary_condition_objects[0]) if face.identifier in interior else None
            whole_panel = (room.identifier in floor_mesh_rooms and peer is not None and face.normal.z > 1e-4
                           and peer.boundary_condition.boundary_condition_objects == (face.identifier, room.identifier)
                           and face.boundary_condition.boundary_condition_objects[-1] == peer.parent.identifier
                           and rooms[peer.parent.identifier]["story"] != native["story"]
                           and not face.sub_faces and replacements is None and (source.area - missing.area) * scale ** 2 <= 1.0
                           and bool(rows) and all(r.get("source_oblique") and r.get("source_partition")
                                                  and not (r["left_space"] and r["right_space"]) for r in rows)
                           and sum(r["native_area_m2"] for r in rows) < missing.area * (scale / 1000) ** 2 - 1e-6)
            if whole_panel:
                rows = []
            children = unary_union([planar_polygon(item.geometry, plane, scale) for item in (*face.apertures, *face.doors)])
            def priority(row):
                shape = planar_polygon(Face3D(wall_boundary(row, floor, scale)), plane, scale)
                return -shape.intersection(children).area, -shape.area
            rows.sort(key=priority)
            emitted = []
            deferred = 0
            for row in rows:
                owners = [item for item in report["rooms"] if item["handle"] in (row["left_space"], row["right_space"])]
                if any(len(item["walls"]) >= 255 for item in owners):
                    deferred += 1
                    continue
                geometry = Face3D(wall_boundary(row, floor, scale))
                shape = planar_polygon(geometry, plane, scale)
                if shape.difference(source if replacements is not None else missing).area * scale ** 2 > max(1.0, shape.area * scale ** 2 * 1e-8):
                    continue
                row.update(source_completion=True, top_shape_method="TDbWall_SetPolyShape_equivalent")
                entity = add_native(drawing, codes["SWR_WALL"], "建-墙-砖", row, wall, [(1000, face.identifier), (1000, "Wall"), (1000, "SourceNativeCompletion")])
                report["walls"].append(row)
                for owner in owners:
                    owner["walls"].append(entity.handle)
                report["wall_profile_geometry"].append({"handle": entity.handle, "identifier": face.identifier, "source_identifiers": row["source_identifiers"], "status": "native_profile" if row.get("profile_mm") else "rectangular", "source_completion": True})
                additions.append({"source_room": room.identifier, "identifier": face.identifier, "handle": entity.handle})
                emitted.append(shape)
            remaining = (source if replacements is not None else missing).difference(unary_union(emitted))
            if remaining.area * scale ** 2 > 1.0:
                deviation = max(plane.distance_to_point(point) * scale for point in face.geometry.boundary)
                shared = any(row["identifier"] == face.identifier and row["source_room"] == room.identifier for row in protected)
                reason = "elevated_inclined_wall_requires_native_roof_projection" if elevated_inclined_wall(face, room, floor) else "source_nonplanarity_exceeds_exact_native_wall_tolerance" if deviation > 0.001 else "native_oblique_horizontal_top_curve_requires_source_plane_completion" if abs(face.normal.z) > 1e-8 else "shared_side_top_profiles_leave_sloped_lower_boundary" if shared else "sloped_lower_boundary_requires_source_plane_panel"
                if whole_panel:
                    reason = "whole_shared_incline_preserves_ceiling_projection"
                residuals.append({"identifier": face.identifier, "source_room": room.identifier, "reason": "native_room_wall_reference_capacity_preserves_source_panels" if deferred else reason, "geometry_reason": reason, "missing_area_m2": remaining.area * (scale / 1000) ** 2, "source_plane_deviation_mm": deviation, "native_partition_parts": len(emitted), "native_parts_deferred_by_capacity": deferred, "coverage_policy": "exact_native_caps_and_explicit_residual_panels"})
    shared = merge_coincident_walls(drawing, report, semantics or {})
    removed = set()
    for row in report["walls"]:
        if not row.get("virtual_plan"):
            continue
        segment = LineString([row["start_mm"][:2], row["end_mm"][:2]])
        for field in ("left_space", "right_space"):
            handle = row[field]
            if not handle:
                continue
            candidates = [LineString([other["start_mm"][:2], other["end_mm"][:2]]).buffer(0.01) for other in report["walls"] if not other.get("virtual_plan") and other["story"] == row["story"] and abs(other["start_mm"][2] - row["start_mm"][2]) <= 0.5 and handle in (other["left_space"], other["right_space"])]
            if segment.difference(unary_union(candidates)).length <= 0.01:
                row[field] = 0
                room = next(room for room in report["rooms"] if room["handle"] == handle)
                room["walls"] = [identity for identity in room["walls"] if identity != row["handle"]]
        if row["left_space"] == row["right_space"] == 0:
            removed.add(row["handle"])
    report["walls"] = [row for row in report["walls"] if row["handle"] not in removed]
    drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
    for row in report["walls"]:
        row["neighbors"] = [0, 0, 0, 0]
    for story in {row["story"] for row in report["walls"]}:
        connect_walls([row for row in report["walls"] if row["story"] == story])
    for room in [*report["rooms"], *report["building_outlines"]]:
        if room.get("inner_properties"):
            walls = [row for row in report["walls"] if row["story"] == room["story"] and (row["handle"] in room["walls"] if room["category"] == 0 else True)]
            write_inner_rings(drawing, codes, room["inner_properties"], room["holes_mm"], [hole_wall_handles(hole, walls) for hole in room["holes_mm"]])
    retained = {row["handle"] for row in report["walls"]}
    report["native_wall_completion"] = {"method": "QQWD_SetPolyShape_equivalent", "walls": [row for row in additions if row["handle"] in retained], "whole_source_reconstructions": reconstructions, "protected_shared_source_profiles": protected, "source_residuals": residuals, "native_partition_policy": "sdk_horizontal_source_partitions_and_exact_native_caps", "native_oblique_protocol": "GetProfileOutline_projected_3D_baseline_and_horizontal_top_curve", "exact_plane_tolerance_mm": 0.001, "room_wall_reference_limit": 255, "shared_native_walls": shared, "removed_plan_helpers": sorted(removed), "host_validation": "pending"}
    report["counts"]["native_elevated_walls"] = sum(bool(row.get("source_elevated")) for row in report["walls"])
    report["counts"]["native_oblique_walls"] = sum(bool(row.get("source_oblique")) for row in report["walls"])


def physical_walls(report, entities=None, bases=None):
    floors = {row["story"]: row for row in report["floors"]}
    result = {}
    for source in report["walls"]:
        native = source if entities is None else entities[source["handle"]]
        if source.get("virtual_plan") or native["height_mm"] <= 0 or native.get("catalog", 2) == 4:
            continue
        floor = floors[source["story"]]
        elevation = floor["reference_elevation_mm"] if bases is None else bases[source["story"]]
        row = {**source, **native}
        for key in ("start_mm", "end_mm"):
            point = native[key]
            row[key] = (point[0] - floor["offset_mm"][0], point[1] - floor["offset_mm"][1], point[2] + elevation)
        row["left_width_mm"] = native.get("left_width_mm", source["thickness_mm"] / 2)
        row["right_width_mm"] = native.get("right_width_mm", source["thickness_mm"] / 2)
        result[source["handle"]] = row
    return result


def plan_wall_conflicts(rows):
    result = []
    for index, first in enumerate(rows):
        a, b = first["start_mm"], first["end_mm"]
        length = hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        for second in rows[index + 1:]:
            if first["story"] != second["story"]:
                continue
            c, d = second["start_mm"], second["end_mm"]
            distance = hypot(d[0] - c[0], d[1] - c[1])
            if abs(ux * (d[1] - c[1]) - uy * (d[0] - c[0])) / distance > 1e-6:
                continue
            deviation = max(abs((point[0] - a[0]) * uy - (point[1] - a[1]) * ux) for point in (c, d))
            if deviation > 0.01:
                continue
            low, high = sorted((point[0] - a[0]) * ux + (point[1] - a[1]) * uy for point in (c, d))
            overlap = min(length, high) - max(0.0, low)
            if overlap > 0.1:
                result.append({"first": first["handle"], "second": second["handle"], "story": first["story"],
                               "overlap_length_mm": overlap, "line_deviation_mm": deviation})
    return result


def separate_plan_wall_axes(report):
    rows = {row["handle"]: row for row in report["walls"]}
    conflicts = plan_wall_conflicts(report["walls"])
    graph = {}
    geometry = {}
    for pair in conflicts:
        first, second = (rows[pair[key]] for key in ("first", "second"))
        if not first.get("virtual_plan") and not second.get("virtual_plan"):
            for row in (first, second):
                if row["handle"] not in geometry:
                    geometry[row["handle"]] = Face3D(tuple(Point3D(*point) for point in wall_points(row)))
            a, b = geometry[first["handle"]], geometry[second["handle"]]
            if abs(a.normal.dot(b.normal)) > 0.99999999 and max(a.plane.distance_to_point(point) for point in b.boundary) <= 0.01:
                overlap = planar_polygon(a, a.plane).intersection(planar_polygon(b, a.plane)).area
                if overlap > 1.0:
                    raise ValueError(f"Native plan adaptation requires disjoint physical wall surfaces: {first['identifier']} / {second['identifier']}")
        graph.setdefault(first["handle"], set()).add(second["handle"])
        graph.setdefault(second["handle"], set()).add(first["handle"])
    colors = {}
    order = sorted(graph, key=lambda handle: (not bool(rows[handle].get("virtual_plan")), rows[handle]["start_mm"][2],
                                              -len(graph[handle]), rows[handle]["identifier"], handle))
    for handle in order:
        taken = {colors[other] for other in graph[handle] if other in colors}
        colors[handle] = next(value for value in range(len(taken) + 1) if value not in taken)
    step, limit = 0.05, 0.25
    if max(colors.values(), default=0) * step > limit:
        raise ValueError("Native plan separation requires axis displacement within 0.25 millimeters")
    repairs = []
    for handle, color in colors.items():
        if color == 0:
            continue
        row = rows[handle]
        start, end = row["start_mm"], row["end_mm"]
        length = hypot(end[0] - start[0], end[1] - start[1])
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        if ux < -1e-7 or abs(ux) <= 1e-7 and uy < 0:
            ux, uy = -ux, -uy
        shift = -uy * color * step, ux * color * step, 0.0
        for field in ("start_mm", "end_mm"):
            row[field] = tuple(value + shift[axis] for axis, value in enumerate(row[field]))
        repairs.append({"handle": handle, "identifier": row["identifier"], "shift_mm": shift,
                        "maximum_displacement_mm": color * step, "source_start_mm": start, "source_end_mm": end})
    remaining = plan_wall_conflicts(report["walls"])
    report["native_plan_compatibility"] = {"schema": "native_plan_wall_axes_v1", "source_conflicts": len(conflicts),
                                           "step_mm": step, "displacement_limit_mm": limit, "records": repairs,
                                           "remaining_conflicts": remaining, "physical_overlap_policy": "exact_geometry_review_required"}
    if remaining:
        raise ValueError("Native plan separation requires unique projected wall axes")
    return repairs


def isolate_profile_corners(report):
    profiles = {row["handle"] for row in report["walls"] if row.get("profile_mm")}
    oblique = {row["handle"] for row in report["walls"] if abs(row.get("oblique_angle", 0.0)) > 1e-8}
    repairs = []
    for row in report["walls"]:
        previous = list(row["neighbors"])
        row["neighbors"] = [0 if row["handle"] in profiles and handle in oblique or row["handle"] in oblique and handle in profiles else handle for handle in previous]
        if previous != row["neighbors"]:
            repairs.append({"handle": row["handle"], "identifier": row["identifier"], "source_neighbors": previous, "neighbors": list(row["neighbors"])})
    report["native_profile_compatibility"] = {"schema": "native_profile_corner_independence_v1", "profile_walls": sorted(profiles),
                                               "records": repairs, "policy": "isolate_oblique_profile_branch_dependencies_and_preserve_vertical_wall_corners"}
    return repairs


def stabilize_opening_baselines(drawing, report):
    from .records import opening_block

    walls = {row["handle"]: row for row in report["walls"]}
    repairs = []
    for row in report["openings"]:
        host = walls.get(row["wall"])
        if host is None or not row.get("profile_mm"):
            continue
        first, last = host["start_mm"], host["end_mm"]
        rise = last[2] - first[2]
        if abs(rise) <= 1e-8:
            continue
        length = hypot(last[0] - first[0], last[1] - first[1])
        along = ((row["position_mm"][0] - first[0]) * (last[0] - first[0]) + (row["position_mm"][1] - first[1]) * (last[1] - first[1])) / length
        elevation = first[2] + rise * along / length
        previous = row["position_mm"]
        shift = previous[2] - elevation
        if abs(shift) <= 0.001:
            continue
        row["position_mm"] = previous[0], previous[1], elevation
        vertical_height = row["height_mm"] * cos(host.get("oblique_angle", 0.0))
        row["profile_mm"] = [(u, v + shift * 1200 / vertical_height) for u, v in row["profile_mm"]]
        row["block_3d"] = opening_block(drawing, "DOOR" if row["kind"] == "Door" else "WIN", row["profile_mm"], host["thickness_mm"], row["angle_rad"])
        row["source_sill_position_mm"] = previous
        row["native_baseline_origin"] = "three_dimensional_wall_baseline_with_source_sill_in_block_profile"
        repairs.append({"handle": row["handle"], "wall": row["wall"], "source_position_mm": previous, "position_mm": row["position_mm"], "profile_elevation_offset_mm": shift})
    report["native_opening_baseline_compatibility"] = {"schema": "native_opening_baseline_origins_v1", "records": repairs,
                                                       "policy": "stable_native_baseline_projection_with_exact_source_profile_placement"}
    return repairs


def footprint(row, low=0.0, high=None):
    start, end = row["start_mm"], row["end_mm"]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    high = length if high is None else high
    return Polygon([(start[0] + x * ux - y * uy, start[1] + x * uy + y * ux) for x, y in ((low, row["left_width_mm"]), (high, row["left_width_mm"]), (high, -row["right_width_mm"]), (low, -row["right_width_mm"]))])


def wall_support(row):
    start, end = row["start_mm"], row["end_mm"]
    length = hypot(end[0] - start[0], end[1] - start[1])
    if abs(end[2] - start[2]) > 1e-8 or row.get("oblique_angle"):
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        return Polygon([((point[0] - start[0]) * ux + (point[1] - start[1]) * uy, point[2]) for point in wall_points(row)])
    profile = row.get("profile_mm") or [(0.0, row["height_mm"]), (length, row["height_mm"])]
    shape = Polygon([(0.0, start[2]), (length, start[2]), *[(x, start[2] + z) for x, z in reversed(profile)]])
    if not shape.is_valid:
        decoded = shape.buffer(0)
        if decoded.is_valid and abs(decoded.area - shape.area) <= max(1.0, abs(shape.area) * 1e-9):
            shape = decoded
    return shape


def profile_overhang(row):
    start, end = row["start_mm"], row["end_mm"]
    if abs(end[2] - start[2]) > 1e-8:
        return True
    if row.get("oblique_angle"):
        return False
    length = hypot(end[0] - start[0], end[1] - start[1])
    profile = row.get("profile_mm", ())
    return any(x < -1e-6 or x > length + 1e-6 for x, z in profile) or any(last[0] < first[0] - 1e-6 for first, last in zip(profile, profile[1:]))


def support_triangles(row):
    if "_clearance_support_triangles" not in row:
        shape = wall_support(row)
        base = row["start_mm"][2]
        geometry = Face3D(tuple(Point3D(x, z - base, 0) for x, z in list(shape.exterior.coords)[:-1]))
        mesh = geometry.triangulated_mesh3d
        row["_clearance_support_triangles"] = [tuple((mesh.vertices[index].x, mesh.vertices[index].y) for index in part) for part in mesh.faces]
    return row["_clearance_support_triangles"]


def projected_shape(shape, host, plane):
    return unary_union([Polygon([tuple(plane.xyz_to_xy(Point3D(*wall_point(host, x, z)))) for x, z in list(part.exterior.coords)[:-1]], [[tuple(plane.xyz_to_xy(Point3D(*wall_point(host, x, z)))) for x, z in list(ring.coords)[:-1]] for ring in part.interiors]) for part in polygons(shape)])


def oblique_obstacle(host, other, support):
    first, last = host["start_mm"], host["end_mm"]
    start, end = other["start_mm"], other["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    distance = hypot(end[0] - start[0], end[1] - start[1])
    ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
    vx, vy = (end[0] - start[0]) / distance, (end[1] - start[1]) / distance
    host_slope, other_slope = -tan(host.get("oblique_angle", 0.0)), -tan(other.get("oblique_angle", 0.0))
    dot, cross = ux * vx + uy * vy, ux * vy - uy * vx
    if abs(cross) < 1e-7 and abs(host_slope - other_slope * dot) < 1e-7:
        return Polygon()
    host_bounds = Polygon([(point[0], point[1]) for point in wall_points(host)]).bounds
    other_bounds = Polygon([(point[0], point[1]) for point in wall_points(other)]).bounds
    margin = max(host["left_width_mm"], host["right_width_mm"]) + max(other["left_width_mm"], other["right_width_mm"])
    if any(host_bounds[axis] > other_bounds[axis + 2] + margin or other_bounds[axis] > host_bounds[axis + 2] + margin for axis in (0, 1)):
        return Polygon()
    along = (dot, cross, host_slope * cross)
    perpendicular = (-cross, dot, host_slope * dot - other_slope)
    origin_along = (first[0] - start[0]) * vx + (first[1] - start[1]) * vy
    origin_perpendicular = -(first[0] - start[0]) * vy + (first[1] - start[1]) * vx - other_slope * (first[2] - start[2])
    base = start[2] - first[2]
    profile = other.get("profile_mm") if not other.get("oblique_angle") else None
    profile = profile or [(0.0, other["height_mm"]), (distance, other["height_mm"])]
    def vector_cross(a, b):
        return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]
    def vector_dot(a, b):
        return sum(x * y for x, y in zip(a, b))
    sections = []
    widths = [(perpendicular, other["left_width_mm"] - origin_perpendicular), (tuple(-value for value in perpendicular), other["right_width_mm"] + origin_perpendicular), ((0.0, 1.0, 0.0), host["left_width_mm"]), ((0.0, -1.0, 0.0), host["right_width_mm"])]
    if profile_overhang(other):
        for triangle in support_triangles(other):
            direction = 1 if Polygon(triangle).exterior.is_ccw else -1
            constraints = list(widths)
            for first_point, last_point in zip(triangle, (*triangle[1:], triangle[0])):
                dx, dz = (last_point[0] - first_point[0]) * direction, (last_point[1] - first_point[1]) * direction
                constraints.append(((dz * along[0], dz * along[1], dz * along[2] - dx), dz * (first_point[0] - origin_along) - dx * (first_point[1] + base)))
            sections.append(constraints)
    else:
        for (low, z1), (high, z2) in zip(profile, profile[1:]):
            if high - low <= 1e-7:
                continue
            slope = (z2 - z1) / (high - low)
            sections.append([*widths, (along, high - origin_along), (tuple(-value for value in along), origin_along - low), ((0.0, 0.0, -1.0), -base), ((-slope * along[0], -slope * along[1], 1 - slope * along[2]), base + z1 + slope * (origin_along - low))])
    pieces = []
    for constraints in sections:
        points = []
        for (a, aa), (b, bb), (c, cc) in combinations(constraints, 3):
            bc, ca, ab = vector_cross(b, c), vector_cross(c, a), vector_cross(a, b)
            determinant = vector_dot(a, bc)
            if abs(determinant) <= 1e-10:
                continue
            point = tuple((aa * bc[axis] + bb * ca[axis] + cc * ab[axis]) / determinant for axis in range(3))
            if all(vector_dot(normal, point) <= bound + 1e-6 for normal, bound in constraints):
                points.append((point[0], first[2] + point[2]))
        if points:
            shape = MultiPoint(points).convex_hull.intersection(support)
            pieces.extend(part for part in polygons(shape) if part.area > 0.01)
    return unary_union(pieces)


def obstacles(host, walls):
    first, last = host["start_mm"], host["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
    shape = footprint(host)
    support = wall_support(host)
    bounds = shape.bounds
    result = []
    for other in walls.values():
        if other["handle"] == host["handle"]:
            continue
        if host.get("oblique_angle") or other.get("oblique_angle") or profile_overhang(host) or profile_overhang(other):
            projected = oblique_obstacle(host, other, support)
            if not projected.is_empty:
                result.append({"wall": other["handle"], "identifier": other["identifier"], "shape": projected})
            continue
        start, end = other["start_mm"], other["end_mm"]
        distance = hypot(end[0] - start[0], end[1] - start[1])
        vx, vy = (end[0] - start[0]) / distance, (end[1] - start[1]) / distance
        if abs(ux * vy - uy * vx) < 1e-7:
            continue
        margin = max(other["left_width_mm"], other["right_width_mm"])
        if max(start[0], end[0]) + margin < bounds[0] or min(start[0], end[0]) - margin > bounds[2] or max(start[1], end[1]) + margin < bounds[1] or min(start[1], end[1]) - margin > bounds[3]:
            continue
        profile = other.get("profile_mm") or [(0.0, other["height_mm"]), (distance, other["height_mm"])]
        pieces = []
        for (low, z1), (high, z2) in zip(profile, profile[1:]):
            if high - low <= 1e-7:
                continue
            overlap = shape.intersection(footprint(other, low, high))
            for part in polygons(overlap):
                if part.area <= 0.01:
                    continue
                points = []
                for x, y in list(part.exterior.coords)[:-1]:
                    along = (x - start[0]) * vx + (y - start[1]) * vy
                    top = start[2] + z1 + (z2 - z1) * (along - low) / (high - low)
                    local = (x - first[0]) * ux + (y - first[1]) * uy
                    points.extend(((local, start[2]), (local, top)))
                projected = MultiPoint(points).convex_hull.intersection(support)
                pieces.extend(part for part in polygons(projected) if part.area > 0.01)
        if pieces:
            result.append({"wall": other["handle"], "identifier": other["identifier"], "shape": unary_union(pieces)})
    return result


def hole_free(shape):
    for part in polygons(shape):
        if part.area <= 0.01:
            continue
        if part.interiors:
            for triangle in triangulate(part):
                yield from hole_free(triangle.intersection(part))
        else:
            yield part


def rehost_wall_openings(drawing, codes, model, report):
    from .records import opening_block

    walls = physical_walls(report)
    rows = {row["handle"]: row for row in report["walls"]}
    rooms = {row["identifier"]: row for row in report["rooms"]}
    floors = {row["story"]: row for row in report["floors"]}
    source_items = {item.identifier: item for room in model.rooms for face in room.faces for item in (*face.apertures, *face.doors)}
    removed = {row["handle"] for row in report["openings"] if row["wall"] in walls}
    drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
    report["openings"] = [row for row in report["openings"] if row["handle"] not in removed]
    for row in report["walls"]:
        row["openings"] = [handle for handle in row["openings"] if handle not in removed]
    scale = hb.unit_scale(model.units)
    groups = {}
    for item in hb.openings(model):
        if item.host_type != "Wall":
            continue
        key = (item.kind, tuple(sorted(tuple(round(value * scale, 2) for value in point) for point in item.boundary)))
        groups.setdefault(key, []).append(item)
    records = []
    for items in groups.values():
        item = items[0]
        source = source_items[item.identifier].geometry.scale(scale)
        plane = source.plane
        shape = _polygon(_Surface(item.identifier, "Opening", source), plane)
        handles = {rooms[entry.room_identifier]["handle"] for entry in items}
        candidates = []
        for host in walls.values():
            if not handles.intersection((host["left_space"], host["right_space"])):
                continue
            start, end = host["start_mm"], host["end_mm"]
            length = hypot(end[0] - start[0], end[1] - start[1])
            ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
            if abs(ux * item.normal.x + uy * item.normal.y) > 1e-4 or max(plane.distance_to_point(Point3D(*point)) for point in wall_points(host)) > 0.5:
                continue
            support = projected_shape(wall_support(host), host, plane)
            if support.is_valid and shape.intersection(support).area > 1.0:
                candidates.append((item.host_identifier not in host.get("source_identifiers", []), host["source_room"] != item.room_identifier, host["handle"], support))
        covered = Polygon()
        emitted = []
        for _, _, handle, support in sorted(candidates, key=lambda value: value[:3]):
            host = walls[handle]
            start, end = host["start_mm"], host["end_mm"]
            angle = atan2(end[1] - start[1], end[0] - start[0])
            ux, uy = cos(angle), sin(angle)
            vertical_scale = cos(host.get("oblique_angle", 0.0))
            intersection = shape.intersection(support).difference(covered)
            floor = floors[host["story"]]
            for part in hole_free(intersection):
                points = [plane.xy_to_xyz(Point2D(x, y)) for x, y in list(part.exterior.coords)[:-1]]
                coordinates = [((point.x - start[0]) * ux + (point.y - start[1]) * uy, point.z) for point in points]
                low, high = min(x for x, z in coordinates), max(x for x, z in coordinates)
                bottom, top = min(z for x, z in coordinates), max(z for x, z in coordinates)
                if high - low <= 0.01 or top - bottom <= 0.01:
                    continue
                along = (low + high) / 2
                profile = [((x - along) * 1200 / (high - low), (z - bottom) * 1200 / (top - bottom)) for x, z in coordinates]
                symbol = "DOOR" if item.kind == "Door" else "WIN"
                row = {"identifier": item.identifier, "source_identifiers": [entry.identifier for entry in items], "kind": item.kind, "story": host["story"], "mark": f"{'M' if item.kind == 'Door' else 'C'}{len(report['openings']) + 1:03d}", "position_mm": (start[0] + along * ux + floor["offset_mm"][0], start[1] + along * uy + floor["offset_mm"][1], bottom - floor["reference_elevation_mm"]), "width_mm": high - low, "height_mm": (top - bottom) / vertical_scale, "angle_rad": angle, "wall": handle, "block_2d": drawing.blocks[f"$ARCHSYS${symbol}2D"][0], "block_3d": opening_block(drawing, symbol, profile, host["left_width_mm"] + host["right_width_mm"], angle), "profile_mm": profile, "clipping_blockers": [], "geometry_policy": "source_oblique_native_wall_partition" if host.get("oblique_angle") else "source_native_wall_partition"}
                entity = add_native(drawing, codes["SWR_OPENING"], "建-门窗", row, opening, [(1000, item.identifier), (1000, item.kind)])
                report["openings"].append(row)
                rows[handle]["openings"].append(entity.handle)
                emitted.append(entity.handle)
            covered = unary_union([covered, shape.intersection(support)])
        if emitted:
            identifiers = {entry.identifier for entry in items}
            report["reference_openings"] = [row for row in report["reference_openings"] if not identifiers.intersection(row.get("source_identifiers", [row["identifier"]]))]
        records.append({"source_identifiers": [entry.identifier for entry in items], "opening_handles": emitted, "uncovered_source_area_m2": shape.difference(covered).area / 1e6})
    report["native_opening_hosts"] = {"policy": "source_polygon_partition_on_final_native_wall_geometry", "records": records, "host_validation": "pending"}


def apply_opening_clearance(drawing, codes, model, report):
    from .records import opening_block

    floors = {row["story"]: row for row in report["floors"]}
    walls = physical_walls(report)
    cache = {}
    records = []
    removed = set()
    additions = []
    hosts = {row["handle"]: row for row in report["walls"]}
    for row in list(report["openings"]):
        host = walls.get(row["wall"])
        if host is None or not row.get("profile_mm"):
            continue
        if host["handle"] not in cache:
            cache[host["handle"]] = obstacles(host, walls)
        masks = cache[host["handle"]]
        start, end = host["start_mm"], host["end_mm"]
        angle = atan2(end[1] - start[1], end[0] - start[0])
        ux, uy = cos(angle), sin(angle)
        vertical_scale = cos(host.get("oblique_angle", 0.0))
        floor = floors[row["story"]]
        x, y, z = row["position_mm"]
        center = (x - floor["offset_mm"][0] - start[0]) * ux + (y - floor["offset_mm"][1] - start[1]) * uy
        shape = Polygon([(center + u * row["width_mm"] / 1200 * cos(row["angle_rad"] - angle), z + v * row["height_mm"] * vertical_scale / 1200 + floor["reference_elevation_mm"]) for u, v in row["profile_mm"]])
        relevant = [mask for mask in masks if mask["shape"].intersection(shape).area > 1.0]
        clipped = shape.difference(unary_union([mask["shape"] for mask in relevant])) if relevant else shape
        if relevant and clipped.minimum_clearance <= OVERLAY_PRECISION_MM:
            clipped = set_precision(clipped, OVERLAY_PRECISION_MM).simplify(0.0)
        loss = shape.area - clipped.area
        records.append({"source_identifiers": list(row["source_identifiers"]), "host": host["handle"], "source_part_area_m2": shape.area / vertical_scale / 1e6, "effective_part_area_m2": clipped.area / vertical_scale / 1e6, "trimmed_area_m2": loss / vertical_scale / 1e6, "blocking_walls": [mask["wall"] for mask in relevant], "policy": "native_wall_volume_clearance"})
        row["wall_clearance_checked"] = True
        if loss <= 1.0:
            continue
        pieces = list(hole_free(clipped))
        if not pieces:
            removed.add(row["handle"])
        template = dict(row)
        for index, part in enumerate(pieces):
            child = row if index == 0 else {key: value for key, value in template.items() if key != "handle"}
            low, bottom, high, top = part.bounds
            along = (low + high) / 2
            child.update(position_mm=(start[0] + along * ux + floor["offset_mm"][0], start[1] + along * uy + floor["offset_mm"][1], bottom - floor["reference_elevation_mm"]), width_mm=high - low, height_mm=(top - bottom) / vertical_scale, angle_rad=angle, profile_mm=[((a - along) * 1200 / (high - low), (b - bottom) * 1200 / (top - bottom)) for a, b in list(part.exterior.coords)[:-1]], geometry_policy="native_wall_volume_clearance", clipping_blockers=[{"wall": mask["wall"], "identifier": mask["identifier"]} for mask in relevant])
            symbol = "DOOR" if child["kind"] == "Door" else "WIN"
            child["block_3d"] = opening_block(drawing, symbol, child["profile_mm"], host["left_width_mm"] + host["right_width_mm"], angle)
            if index:
                child["mark"] = f"{'M' if child['kind'] == 'Door' else 'C'}{len(report['openings']) + len(additions) + 1:03d}"
                entity = add_native(drawing, codes["SWR_OPENING"], "建-门窗", child, opening, [(1000, child["identifier"]), (1000, child["kind"])])
                hosts[host["handle"]]["openings"].append(entity.handle)
                additions.append(child)
    if removed:
        drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
        report["openings"] = [row for row in report["openings"] if row["handle"] not in removed]
        for row in report["walls"]:
            row["openings"] = [handle for handle in row["openings"] if handle not in removed]
    report["openings"].extend(additions)
    for record in report["native_opening_hosts"]["records"]:
        record["source_partition_handles"] = record["opening_handles"]
        identifiers = set(record["source_identifiers"])
        record["opening_handles"] = [row["handle"] for row in report["openings"] if identifiers.intersection(row["source_identifiers"])]
    report["opening_clearance"] = {"policy": "native_wall_volume_clearance", "records": records, "trimmed_parts": sum(row["trimmed_area_m2"] > 1e-6 for row in records), "trimmed_part_area_m2": sum(row["trimmed_area_m2"] for row in records), "host_validation": "pending"}


def effective_source_shape(item, report, walls, cache):
    scale = hb.unit_scale(report["source_units"])
    geometry = item.geometry.scale(scale)
    plane = geometry.plane
    source = _polygon(_Surface(item.identifier, "Opening", geometry), plane)
    room = next(row for row in report["rooms"] if row["identifier"] == item.parent.parent.identifier)
    blocked = []
    for handle, host in walls.items():
        if room["handle"] not in (host["left_space"], host["right_space"]):
            continue
        if any(plane.distance_to_point(Point3D(*point)) > 0.5 for point in wall_points(host)):
            continue
        support = projected_shape(wall_support(host), host, plane)
        if source.intersection(support).area <= 0.01:
            continue
        if handle not in cache:
            cache[handle] = obstacles(host, walls)
        for mask in cache[handle]:
            blocked.append(projected_shape(mask["shape"], host, plane))
    return source.difference(unary_union(blocked)) if blocked else source
