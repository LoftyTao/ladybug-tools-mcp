"""Native slab, roof, wall surface, enclosure and shade mesh construction."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from math import cos, radians, sqrt
from types import SimpleNamespace

from honeybee.face import Face
from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
from ladybug_geometry.triangulation import earcut
from shapely import get_parts, line_merge, set_precision
from shapely.errors import GEOSException
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .. import model as hb
from .geometry import OVERLAY_PRECISION_MM, _Surface, _compare, convex_regions, coverage, opening_points, simple_roof_regions, wall_points
from .orientation import vertical_wall_normal
from .records import (
    add_native, attach_room_properties, attach_surface_properties, floor_frame, opening,
    slab, space, wall, write_inner_rings,
)


def dot(first, second):
    return sum(a * b for a, b in zip(first, second))


def cross(first, second):
    return (first[1] * second[2] - first[2] * second[1], first[2] * second[0] - first[0] * second[2], first[0] * second[1] - first[1] * second[0])


def normalized(vector):
    length = math.sqrt(dot(vector, vector))
    if length <= 1e-12:
        raise ValueError("Native surface normals require a positive length")
    return tuple(value / length for value in vector)


def axes(normal):
    normal = normalized(normal)
    first = normalized(cross((0, 1, 0) if abs(normal[0]) < 1 / 64 and abs(normal[1]) < 1 / 64 else (0, 0, 1), normal))
    return first, cross(normal, first), normal


def wcs_points(row):
    first, second, normal = axes(row["normal"])
    return [tuple(first[index] * point[0] + second[index] * point[1] + normal[index] * row["elevation_mm"] for index in range(3)) for point in row["outline_mm"]]


def _condition_roof_triangles(faces, altitude):
    def sides(face):
        return tuple(zip(face, (*face[1:], face[0])))

    neighbors = {edge: i for i, face in enumerate(faces) for edge in sides(face)}
    heights = list(map(altitude, faces))
    pending = deque(neighbors)
    while pending:
        a, b = pending.popleft()
        i, j = neighbors.get((a, b)), neighbors.get((b, a))
        if i is None or j is None:
            continue
        c, = set(faces[i]) - {a, b}
        d, = set(faces[j]) - {a, b}
        first, second = (a, d, c), (b, c, d)
        h, k = altitude(first), altitude(second)
        if min(h, k) <= max(0.0, min(heights[i], heights[j])) + OVERLAY_PRECISION_MM:
            continue
        for face in (faces[i], faces[j]):
            for edge in sides(face):
                del neighbors[edge]
        faces[i], faces[j] = first, second
        heights[i], heights[j] = h, k
        for index in (i, j):
            for edge in sides(faces[index]):
                neighbors[edge] = index
                pending.append(edge)
    return faces


def roof_mesh_indices(ring):
    shape = Polygon(ring)
    if not shape.is_valid or shape.area <= 0 or not shape.exterior.is_ccw:
        raise ValueError("Bound roofs require simple outward material patches")
    if len(ring) == 3 or len(ring) == 4 and shape.equals(shape.convex_hull):
        return [tuple(range(len(ring)))]
    def altitude(face):
        a, b, c = (ring[i] for i in face)
        twice_area = (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])
        return twice_area / max(math.dist(a, b), math.dist(b, c), math.dist(c, a))
    best, best_quality = [], -math.inf
    for offset in dict.fromkeys((0, len(ring)//2, 1, len(ring)//3, len(ring)-1)):
        order = [*range(offset, len(ring)), *range(offset)]
        x0, y0 = ring[offset]
        ids = earcut([v for j in order for v in (ring[j][0]-x0, ring[j][1]-y0)])
        faces = [tuple(order[j] for j in ids[i:i+3]) for i in range(0, len(ids), 3)]
        for i, face in enumerate(faces):
            if altitude(face) >= OVERLAY_PRECISION_MM:
                continue
            adjacent = {edge: (j, tri[k-1]) for j, tri in enumerate(faces) if j != i
                        for k, edge in enumerate(zip(tri, (*tri[1:], tri[0])))}
            swaps = []
            for k, (a, b) in enumerate(zip(face, (*face[1:], face[0]))):
                if (b, a) in adjacent:
                    j, d = adjacent[b, a]
                    c = face[k-1]
                    first, second = (a, d, c), (b, c, d)
                    quality = min(altitude(first), altitude(second))
                    if quality > OVERLAY_PRECISION_MM:
                        swaps.append((quality, j, first, second))
            if swaps:
                _, j, first, second = max(swaps)
                faces[i], faces[j] = first, second
        quality = min((altitude(face) for face in faces), default=-math.inf)
        if quality >= OVERLAY_PRECISION_MM:
            return faces
        if quality > best_quality:
            best, best_quality = faces, quality
    return _condition_roof_triangles(best, altitude)


def write_bound_roof_meshes(drawing, report):
    def exterior_wall(row):
        return row["face_usage"] == 5 and row["kind"] == "Wall" and row.get("boundary_condition") == "Outdoors"

    if not report.get("floor_meshes") and not any(
            r["room_bound"] and (r["face_usage"] == 2 or exterior_wall(r)) for r in report["surfaces"]):
        return
    entities = {e.handle: e for e in drawing.entities}
    hatch_hosts = {r["wall"] for r in report["openings"] if r.get("host_identifier")}
    count = 0
    for row in report["surfaces"]:
        wall = exterior_wall(row)
        if not row["room_bound"] or (row["face_usage"] not in (1, 2) and not wall) or row["handle"] in hatch_hosts:
            continue
        if row["holes_mm"]:
            raise ValueError(f"Bound roof {row['identifier']} requires simple material patches")
        indices = roof_mesh_indices(row["outline_mm"])
        entity = entities[row["handle"]]
        if wall:
            entity.layer = "建-屋顶"
        drawing.set_polyface(entity, [[row["boundary_mm"][i] for i in face] for face in indices])
        row.pop("object_description", None)
        row.update(native_class="POLYLINE_PFACE", dxf_name="POLYLINE", mesh_faces=len(indices))
        count += 1
    report["counts"].update(native_roof_meshes=count, native_slabs=len(report["surfaces"]) - count)


def add_surfaces(drawing, codes, model, floors, report, floor_slabs=True):
    scale = hb.unit_scale(model.units)
    report["surfaces"] = []
    report["roof_openings"] = []
    report["skylights"] = []
    for room in model.rooms:
        floor = floors[room.identifier]
        def convert(point):
            return (point.x * scale + floor.offset_mm[0], point.y * scale + floor.offset_mm[1], point.z * scale - floor.reference_elevation_mm)
        for face in room.faces:
            kind = str(face.type)
            if kind not in {"Floor", "RoofCeiling"}:
                continue
            if kind == "Floor" and not floor_slabs:
                continue
            geometry = face.geometry
            if kind == "RoofCeiling":
                roof = add_parts(drawing, codes, report, room.identifier, face.identifier, kind, floor.identifier, [geometry.boundary], tuple(face.normal), convert, holes=geometry.holes or ())
                for item in face.apertures:
                    add_skylight(drawing, codes, report, room.identifier, face, item, floor.identifier, convert, scale)
                for item in face.doors:
                    add_roof_opening(drawing, codes, report, room.identifier, face, hb.opening_rect(item, "Door", model.units), roof["handle"], floor.identifier, convert, scale)
                continue
            parts = [geometry.boundary]
            if geometry.holes:
                mesh = geometry.triangulated_mesh3d
                parts = [[mesh.vertices[index] for index in triangle] for triangle in mesh.faces]
            add_parts(drawing, codes, report, room.identifier, face.identifier, kind, floor.identifier, parts, tuple(face.normal), convert)
    report["surface_scope"] = "Native source-coordinate floor and roof slabs with room-bound CPrRoof attributes; skylights are separate face slabs attached to their roof faces"


def add_parts(drawing, codes, report, room, identifier, kind, story, parts, normal, convert, host=None, holes=(), bind=True, planar_tolerance_mm=0.01, preserve_floor_normal=False):
    if kind == "Floor" and not preserve_floor_normal:
        normal = (0.0, 0.0, 1.0)
    first, second, normal = axes(normal)
    for index, part in enumerate(parts):
        points = [convert(point) for point in part]
        elevations = [dot(point, normal) for point in points]
        elevation = sum(elevations) / len(elevations)
        maximum_projection = max(abs(value - elevation) for value in elevations)
        if maximum_projection > planar_tolerance_mm:
            raise ValueError(f"Native surfaces require planar source pieces: {identifier}")
        points = [tuple(point[axis] + normal[axis] * (elevation - value) for axis in range(3)) for point, value in zip(points, elevations)]
        outline = [(dot(point, first), dot(point, second)) for point in points]
        if not Polygon(outline).exterior.is_ccw:
            points.reverse()
            outline.reverse()
        hole_rows = []
        for hole in holes:
            hole_points = [convert(point) for point in hole]
            hole_elevations = [dot(point, normal) for point in hole_points]
            if max(hole_elevations) - min(hole_elevations) > 0.01:
                raise ValueError(f"Native surface holes require planar source pieces: {identifier}")
            ring = [(dot(point, first), dot(point, second)) for point in hole_points]
            if Polygon(ring).exterior.is_ccw:
                ring.reverse()
            hole_rows.append(ring)
        row = {"identifier": identifier, "source_room": room, "story": story, "kind": kind, "part": index, "normal": normal, "elevation_mm": elevation, "outline_mm": outline, "boundary_mm": points, "holes_mm": hole_rows, "host_identifier": host, "maximum_projection_mm": maximum_projection}
        usage = {"Floor": 8, "Skylight": 2, "RoofDoor": 3, "Wall": 5, "WallWindow": 6, "WallDoor": 3}.get(kind, 1)
        layer = "建-楼板" if kind == "Floor" else "建-天窗" if kind == "Skylight" else "建-墙-砖" if kind in {"Wall", "WallWindow", "WallDoor"} else "建-屋顶"
        if kind == "Skylight":
            row["object_description"] = "天窗"
        entity = add_native(drawing, codes["SWR_SLAB"], layer, row, slab, [(1000, identifier), (1000, kind), (1000, room), *([(1000, host)] if host else [])])
        board_type = 3 if kind in {"Skylight", "RoofDoor", "WallWindow"} else 0
        native_code = next((candidate.get("native_code", room) for candidate in report.get("rooms", []) if candidate["identifier"] == room), room)
        attach_surface_properties(drawing, entity, native_code if bind else "", usage, board_type)
        row["native_room_code"] = native_code if bind else ""
        row["face_usage"] = usage
        row["board_type"] = board_type
        row["room_bound"] = bind
        report["surfaces"].append(row)
    return row


def skylight_parts(geometry, scale):
    boundary = geometry.boundary
    short_edge = len(boundary) > 3 and any(first.distance_to_point(last) * scale < 10.0 for first, last in zip(boundary, (*boundary[1:], boundary[0])))
    if short_edge:
        mesh = geometry.triangulated_mesh3d
        return tuple(tuple(mesh.vertices[index] for index in triangle) for triangle in mesh.faces)
    return (boundary,)


def add_skylight(drawing, codes, report, room, face, item, story, convert, scale):
    geometry = item.geometry
    parts = skylight_parts(geometry, scale)
    start = len(report["surfaces"])
    row = add_parts(
        drawing, codes, report, room, item.identifier, "Skylight", story,
        parts, tuple(geometry.normal), convert, host=face.identifier,
    )
    for part in report["surfaces"][start:]:
        part["name"] = item.display_name or item.identifier
        part["thickness_mm"] = 0.0
        part["source_thickness_mm"] = hb.face_thickness_m(item) * 1000
        entity = next(entity for entity in drawing.entities if entity.handle == part["handle"])
        drawing.add_appid("_ARCH_SLAB_TEXT")
        part["native_label"] = "天窗"
        entity.application_xdata["_ARCH_SLAB_TEXT"] = ((1000, part["native_label"]),)
        entity.xdata += ((1000, part["name"]),)
        part["calculation_partition"] = "area_preserving_short_edge_triangles" if len(parts) > 1 else "source_boundary"
        record = {
            "identifier": item.identifier,
            "source_identifiers": [item.identifier],
            "kind": "Skylight",
            "host_identifier": face.identifier,
            "surface_handle": part["handle"],
            "opening_handle": None,
            "part": part["part"],
            "area_m2": Polygon(part["outline_mm"]).area / 1e6,
            "calculation_partition": part["calculation_partition"],
        }
        report["roof_openings"].append(record)
        report["skylights"].append(record)
    return row


def add_roof_opening(drawing, codes, report, room, face, item, host_handle, story, convert, scale):
    boundary = [convert(point) for point in item.boundary]
    bottom = min(point[2] for point in boundary)
    start, end = convert(item.start), convert(item.end)
    center = convert(item.center)
    symbol = "DOOR" if item.kind == "Door" else "WIN"
    row = {
        "identifier": item.identifier,
        "source_identifiers": [item.identifier],
        "kind": item.kind,
        "story": story,
        "mark": f"{'M' if item.kind == 'Door' else 'C'}{len(report['openings']) + 1:03d}",
        "position_mm": (center[0], center[1], bottom),
        "width_mm": item.width * scale,
        "height_mm": item.height * scale,
        "angle_rad": math.atan2(end[1] - start[1], end[0] - start[0]),
        "wall": host_handle,
        "block_2d": drawing.blocks[f"$ARCHSYS${symbol}2D"][0],
        "block_3d": drawing.blocks[f"$ARCHSYS${symbol}3D"][0],
        "clipping_blockers": [],
        "host_identifier": face.identifier,
    }
    entity = add_native(drawing, codes["SWR_OPENING"], "建-门窗", row, opening, [(1000, item.identifier), (1000, item.kind), (1000, room)])
    report["openings"].append(row)
    report.setdefault("roof_openings", []).append({"identifier": item.identifier, "host_identifier": face.identifier, "surface_handle": host_handle, "opening_handle": entity.handle, "area_m2": float(item.width * item.height)})
    return row


def close_room_boundaries(drawing, codes, report, room_rows, wall_rows):
    from shapely.ops import unary_union
    added = []
    for room in room_rows:
        outline = room["outline_mm"]
        elevation = room["position_mm"][2]
        existing = [row for row in wall_rows if row["story"] == room["story"] and abs(row["start_mm"][2] - elevation) <= 0.5]
        network = unary_union([LineString([row["start_mm"][:2], row["end_mm"][:2]]).buffer(max(100.0, row["thickness_mm"])) for row in existing])
        for index, (first, last) in enumerate(zip(outline, (*outline[1:], outline[0]))):
            edge = LineString([first, last])
            if edge.length <= 1.0 or edge.difference(network).length <= 1.0:
                continue
            near = sorted(existing, key=lambda row: LineString([row["start_mm"][:2], row["end_mm"][:2]]).distance(edge))
            thickness = near[0]["thickness_mm"] if near else 100.0
            start, end = (last, first)
            row = {"identifier": f"{room['identifier']}:closure:{index}", "story": room["story"], "source_room": room["identifier"], "start_mm": (*start, elevation), "end_mm": (*end, elevation), "height_mm": room["height_mm"], "thickness_mm": thickness, "openings": [], "neighbors": [0, 0, 0, 0], "left_space": room["handle"], "right_space": 0, "profile_status": "room_closure_wall", "closure": True}
            add_native(drawing, codes["SWR_WALL"], "建-墙-砖", row, wall, [(1000, row["identifier"]), (1000, "Wall"), (1000, "RoomClosure")])
            wall_rows.append(row)
            report["walls"].append(row)
            room["walls"].append(row["handle"])
            added.append(row)
    return added


def add_ceiling_surfaces(drawing, codes, model, ceiling_layouts, report):
    scale = hb.unit_scale(model.units)
    report["surfaces"] = []
    report["roof_openings"] = []
    report["skylights"] = []
    for room in model.rooms:
        layout = ceiling_layouts.get(room.identifier)
        if layout is None:
            continue
        def convert(point):
            return (point.x * scale + layout.offset_mm[0], point.y * scale + layout.offset_mm[1], point.z * scale - layout.reference_elevation_mm)
        for face in room.faces:
            if str(face.type) != "RoofCeiling":
                continue
            geometry = face.geometry
            parts = [geometry.boundary]
            if geometry.holes:
                mesh = geometry.triangulated_mesh3d
                parts = [[mesh.vertices[index] for index in triangle] for triangle in mesh.faces]
            for part in parts:
                add_ceiling_part(drawing, codes, report, room.identifier, face.identifier, layout.identifier, part, tuple(face.normal), convert)
            for item in face.apertures:
                add_skylight(drawing, codes, report, room.identifier, face, item, layout.identifier, convert, scale)
    report["surface_scope"] = "Native roof and ceiling slabs in dedicated ceiling storeys; occupied storeys retain BESI-generated room floors and wall enclosures"


def add_ceiling_part(drawing, codes, report, room, identifier, story, part, normal, convert):
    first, second, normal = axes(normal)
    points = [convert(point) for point in part]
    elevations = [dot(point, normal) for point in points]
    if max(elevations) - min(elevations) > 0.01:
        raise ValueError(f"Native ceiling surfaces require planar source pieces: {identifier}")
    row = {"identifier": identifier, "source_room": room, "story": story, "kind": "RoofCeiling", "part": len(report["surfaces"]), "normal": normal, "elevation_mm": sum(elevations) / len(elevations), "outline_mm": [(dot(point, first), dot(point, second)) for point in points], "boundary_mm": points, "host_identifier": None}
    add_native(drawing, codes["SWR_SLAB"], "建-屋顶", row, slab, [(1000, identifier), (1000, "RoofCeiling"), (1000, room)])
    report["surfaces"].append(row)


def add_wall_profiles(model, report, semantics=None):
    scale = hb.unit_scale(model.units)
    faces = {face.identifier: face for room in model.rooms for face in room.faces}
    room_faces = {room.identifier: [face for face in room.faces if str(face.type) == "Wall"] for room in model.rooms}
    floors = {row["story"]: row for row in report["floors"]}
    room_identifiers = {row["handle"]: row["identifier"] for row in report.get("rooms", [])}
    records = []
    for row in report["walls"]:
        if row.get("closure"):
            continue
        source = faces[row["identifier"]]
        floor = floors[row["story"]]
        start, end = row["start_mm"], row["end_mm"]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        shapes = []
        identifiers = []
        for candidate in room_faces[row["source_room"]]:
            if semantics and semantics.get(source.identifier) != semantics.get(candidate.identifier):
                continue
            if abs(candidate.normal.z) > 1e-4 or candidate.geometry.holes:
                continue
            if any(source.geometry.plane.distance_to_point(point) * scale > 0.5 for point in candidate.geometry.boundary):
                continue
            coordinates = [((point.x * scale + floor["offset_mm"][0] - start[0]) * dx / length + (point.y * scale + floor["offset_mm"][1] - start[1]) * dy / length, point.z * scale - floor["reference_elevation_mm"] - start[2]) for point in candidate.geometry.boundary]
            coordinates = [(0.0 if abs(x) <= 0.5 else length if abs(x - length) <= 0.5 else x, z) for x, z in coordinates]
            polygon = Polygon(coordinates)
            if polygon.is_valid and polygon.area > 1e-6 and polygon.intersection(box(0, -1e8, length, 1e8)).area > 1e-6:
                shapes.append(polygon)
                identifiers.append(candidate.identifier)
        shape = unary_union([set_precision(shape, OVERLAY_PRECISION_MM) for shape in shapes])
        shared_rooms = []
        for handle in {row.get("left_space", 0), row.get("right_space", 0)}.intersection(room_identifiers):
            identifier = room_identifiers[handle]
            if identifier == row["source_room"]:
                continue
            other_shapes = []
            other_identifiers = []
            for candidate in room_faces[identifier]:
                if semantics and semantics.get(source.identifier) != semantics.get(candidate.identifier):
                    continue
                if abs(candidate.normal.z) > 1e-4 or candidate.geometry.holes or any(source.geometry.plane.distance_to_point(point) * scale > 0.5 for point in candidate.geometry.boundary):
                    continue
                coordinates = [((point.x * scale + floor["offset_mm"][0] - start[0]) * dx / length + (point.y * scale + floor["offset_mm"][1] - start[1]) * dy / length, point.z * scale - floor["reference_elevation_mm"] - start[2]) for point in candidate.geometry.boundary]
                coordinates = [(0.0 if abs(x) <= 0.5 else length if abs(x - length) <= 0.5 else x, z) for x, z in coordinates]
                polygon = Polygon(coordinates)
                if polygon.is_valid and polygon.area > 1e-6:
                    other_shapes.append(set_precision(polygon, OVERLAY_PRECISION_MM))
                    other_identifiers.append(candidate.identifier)
            common = shape.intersection(unary_union(other_shapes))
            if common.area > 1.0:
                shape = common
                identifiers.extend(other_identifiers)
                shared_rooms.append(identifier)
        clipped = shape.intersection(box(0, -1e8, length, 1e8))
        row["source_identifiers"] = identifiers
        record = {"handle": row["handle"], "identifier": source.identifier, "source_identifiers": identifiers, "status": "rectangular", "shared_profile_rooms": shared_rooms}
        if clipped.is_empty or clipped.geom_type != "Polygon" or source.geometry.holes or abs(source.normal.z) > 1e-4 or clipped.bounds[0] > 0.5 or clipped.bounds[2] < length - 0.5:
            record.update(status="profile_review_required", reason="simple_vertical_profile_required")
        else:
            low, bottom, high, upper = clipped.bounds
            positions = sorted({0.0, length, *(x for x, z in clipped.exterior.coords if 0.001 < x < length - 0.001)})
            top = [(x, clipped.intersection(LineString([(max(low, min(high, x)), -1e8), (max(low, min(high, x)), 1e8)])).bounds[3]) for x in positions]
            envelope = Polygon([(0, 0), (length, 0), *reversed(top)])
            delta = envelope.symmetric_difference(clipped).area
            if abs(bottom) > 0.5 or low > 0.5 or high < length - 0.5 or delta > max(1.0, clipped.area * 1e-6):
                record.update(status="profile_review_required", reason="horizontal_base_and_continuous_top_required", difference_mm2=delta)
            else:
                row["height_mm"] = upper
                row["top_shape_method"] = "TDbWall_SetPolyShape_equivalent"
                if any(abs(z - upper) > 0.01 for x, z in top):
                    row["profile_mm"] = top
                    row["profile_status"] = "native_source_top_profile"
                    record["status"] = "native_profile"
                    record["profile_mm"] = top
        records.append(record)
    report["wall_profile_geometry"] = records


def planar_roof_parts(face):
    if face.apertures:
        plane = face.geometry.plane
        def shape_of(geometry):
            return Polygon([tuple(plane.xyz_to_xy(point)) for point in geometry.boundary], [[tuple(plane.xyz_to_xy(point)) for point in hole] for hole in geometry.holes or ()])
        shape = shape_of(face.geometry)
        openings = unary_union([shape_of(item.geometry) for item in (*face.apertures, *face.doors)])
        opaque = shape.difference(openings)
        pieces = list(opaque.geoms) if opaque.geom_type == "MultiPolygon" else [opaque]
        partition = simple_roof_regions if abs(face.normal.z - 1) <= 1e-12 else convex_regions
        return tuple(tuple(plane.xy_to_xyz(Point2D(x, y)) for x, y in part.exterior.coords[:-1]) for piece in pieces if not piece.is_empty for part in partition(piece))
    geometry = Face3D.from_punched_geometry(face.geometry, [item.geometry for item in face.doors]) if face.doors else face.geometry
    if not geometry.holes:
        return (geometry.boundary,)
    mesh = geometry.triangulated_mesh3d
    plane = geometry.plane
    polygons = [Polygon([tuple(plane.xyz_to_xy(mesh.vertices[index])) for index in triangle]) for triangle in mesh.faces]
    while True:
        merged = False
        for first in range(len(polygons)):
            for second in range(first + 1, len(polygons)):
                union = polygons[first].union(polygons[second])
                if union.geom_type == "Polygon" and union.is_valid and not union.interiors:
                    polygons[first] = union
                    polygons.pop(second)
                    merged = True
                    break
            if merged:
                break
        if not merged:
            break
    return tuple(tuple(plane.xy_to_xyz(Point2D(x, y)) for x, y in polygon.exterior.coords[:-1]) for polygon in polygons)


def shared_floor_ceilings(model, room_floors, explicit_floor_rooms, scale):
    source_faces = {face.identifier: face for room in model.rooms for face in room.faces}
    shared_ceilings = {}
    for room in model.rooms:
        lower = room_floors[room.identifier]
        datum = lower["reference_elevation_mm"] + lower["height_mm"]
        for face in room.faces:
            if str(face.type) != "RoofCeiling" or str(face.boundary_condition) != "Surface" or lower.get("series"):
                continue
            adjacent_id, adjacent_room = face.boundary_condition.boundary_condition_objects
            other = source_faces.get(adjacent_id)
            upper = room_floors.get(adjacent_room)
            if (other is None or other.parent.identifier != adjacent_room or str(other.type) != "Floor"
                    or str(other.boundary_condition) != "Surface" or other.boundary_condition.boundary_condition_objects != (face.identifier, room.identifier)
                    or adjacent_room in explicit_floor_rooms or upper is None or upper.get("series") or upper["floor_number"] != lower["floor_number"] + 1
                    or face.sub_faces or other.sub_faces or face.normal.z < cos(radians(1)) or other.normal.z > -cos(radians(1))):
                continue
            deviation = max(abs(point.z * scale - datum) for item in (face, other) for point in item.geometry.vertices)
            if deviation <= 1.0 and abs(upper["source_elevation_mm"] - datum) <= 0.5 and face.geometry.is_geometrically_equivalent(other.geometry, 1.0 / scale):
                shared_ceilings[face.identifier] = {"source_room": room.identifier, "upper_room": adjacent_room,
                                                    "upper_face": adjacent_id, "maximum_datum_deviation_mm": deviation}
    return shared_ceilings


def partitioned_roof_corners(model, room_floors, scale, whole_roofs=()):
    def outline(face):
        polygon = Polygon([(p.x * scale, p.y * scale) for p in face.geometry.boundary])
        return set_precision(polygon.exterior, OVERLAY_PRECISION_MM)

    cut_roofs = defaultdict(list)
    for room in model.rooms:
        for face in room.faces:
            if (str(face.type) == "RoofCeiling" and str(face.boundary_condition) == "Outdoors"
                    and face.apertures and face.identifier not in whole_roofs and (face.max.z - face.min.z) * scale <= 0.5):
                cut_roofs[room.identifier].append((face, outline(face)))
    corners = {}
    regions = {}
    for room in model.rooms:
        neighbours = {f.boundary_condition.boundary_condition_objects[-1] for f in room.faces
                      if str(f.type) == "Wall" and str(f.boundary_condition) == "Surface"}
        peers = [roof for rid in sorted(neighbours & cut_roofs.keys()) if room_floors[rid]["story"] == room_floors[room.identifier]["story"]
                 for roof in cut_roofs[rid]]
        if not peers:
            continue
        for face in room.faces:
            if str(face.type) != "RoofCeiling" or str(face.boundary_condition) != "Outdoors" or face.sub_faces or face.geometry.holes:
                continue
            if (face.max.z - face.min.z) * scale > 0.5:
                continue
            edge = outline(face)
            for peer, other in peers:
                if (max(face.max.z, peer.max.z) - min(face.min.z, peer.min.z)) * scale > 0.5:
                    continue
                shared = line_merge(edge.intersection(other))
                turns = [Point(v) for line in get_parts(shared) if line.geom_type == "LineString" for v in list(line.simplify(1.0).coords)[1:-1]]
                if not turns:
                    continue
                if peer.identifier not in regions:
                    regions[peer.identifier] = [Polygon([(p.x * scale, p.y * scale) for p in part]) for part in planar_roof_parts(peer)]
                if any(sum(poly.distance(turn) <= 1.0 for poly in regions[peer.identifier]) != 1 for turn in turns):
                    corners.setdefault(face.identifier, []).append(peer.identifier)
    return corners


def spatial_skylight_hosts(model, report, explicit_floor_rooms, scale):
    frames = {f["story"]: f for f in report["floors"]}
    plans = defaultdict(dict)
    for room in report["rooms"]:
        dx, dy = frames[room["story"]]["offset_mm"]
        def ring(points):
            return [(x - dx, y - dy) for x, y in points]
        plans[room["story"]][room["identifier"]] = Polygon(ring(room["outline_mm"]), [ring(h) for h in room["holes_mm"]])
    stories = {r["identifier"]: r["story"] for r in report["rooms"]}
    result = set()
    for room in model.rooms:
        if room.identifier in explicit_floor_rooms:
            continue
        roofs = [f for f in room.faces if str(f.type) == "RoofCeiling"]
        if not any(f.apertures for f in roofs):
            continue
        projections = {f.identifier: Polygon([(p.x * scale, p.y * scale) for p in f.geometry.boundary],
                           [[(p.x * scale, p.y * scale) for p in ring] for ring in f.geometry.holes or ()]) for f in roofs}
        storey = plans[stories[room.identifier]]
        for f in roofs:
            if not f.apertures or f.doors or f.geometry.holes or f.normal.z < 0.5 or str(f.boundary_condition) != "Outdoors":
                continue
            footprint = projections[f.identifier]
            if not footprint.is_valid or footprint.area < 1.0 or footprint.difference(storey[room.identifier]).area > 1.0:
                continue
            others = [p for rid, p in storey.items() if rid != room.identifier]
            others.extend(p for fid, p in projections.items() if fid != f.identifier)
            if all(p.is_valid and footprint.intersection(p).area <= 1.0 for p in others):
                result.add(f.identifier)
    return result


def add_roof_storey(drawing, codes, model, report, bind_roofs=True, explicit_floor_rooms=(), spatial_skylights=False):
    scale = hb.unit_scale(model.units)
    occupied = report["floors"]
    primary = [row for row in occupied if not row.get("series")]
    top = max(primary, key=lambda row: row["floor_number"])
    source_story = top["source_story"]
    anchor = max(hb.room_elevation_bounds(room)[1] for room in model.rooms) * scale
    ground = report["ground_frame"]
    native_base = ground["height_mm"] + sum(row["height_mm"] for row in primary if row["floor_number"] < top["floor_number"])
    height = anchor - native_base
    if height <= 0:
        raise ValueError("The centralized roof requires a positive top-primary frame height")
    top["height_mm"] = height
    top["frame"]["height_mm"] = height
    top["roof_anchor_mm"] = anchor
    floors = {row["story"]: row for row in occupied}
    room_floors = {row["identifier"]: floors[row["story"]] for row in report["rooms"]}
    native_rooms = {row["identifier"]: row for row in report["rooms"]}
    shared_ceilings = shared_floor_ceilings(model, room_floors, explicit_floor_rooms, scale)
    spatial = spatial_skylight_hosts(model, report, explicit_floor_rooms, scale) if spatial_skylights else set()
    automatic = set()
    decisions = []
    for room in model.rooms:
        faces = [face for face in room.faces if str(face.type) == "RoofCeiling"]
        native = native_rooms[room.identifier]
        ceiling = room_floors[room.identifier]["reference_elevation_mm"] + room_floors[room.identifier]["height_mm"]
        room_ceiling = native["position_mm"][2] + room_floors[room.identifier]["reference_elevation_mm"] + native["height_mm"]
        eligible = bool(faces) and abs(ceiling - room_ceiling) <= 0.5 and all(face.normal.z > cos(radians(1.0)) and not face.geometry.holes and not face.doors and str(face.boundary_condition) != "Adiabatic" and (not face.apertures or str(face.boundary_condition) == "Outdoors" and abs(face.normal.z - 1) <= 1e-12) and all(abs(point.z * scale - ceiling) <= 0.5 for point in face.geometry.boundary) for face in faces)
        if room.identifier in explicit_floor_rooms:
            eligible = False
        if eligible:
            source = unary_union([Polygon([(point.x * scale, point.y * scale) for point in face.geometry.boundary]) for face in faces])
            plan = unary_union([Polygon([(point.x * scale, point.y * scale) for point in face.boundary], [[(point.x * scale, point.y * scale) for point in ring] for ring in face.holes or ()]) for face in hb.room_plan_boundaries(room)])
            eligible = source.is_valid and plan.is_valid and source.symmetric_difference(plan).area <= max(1.0, plan.area * 1e-8)
        if eligible:
            automatic.update(face.identifier for face in faces)
        automatic.update(face.identifier for face in faces if face.identifier in shared_ceilings)
        decisions.extend({"identifier": face.identifier, "source_room": room.identifier, "policy": "native_shared_floor" if face.identifier in shared_ceilings else "native_room_ceiling" if face.identifier in automatic else "explicit_source_roof", "native_room_handle": native["handle"], "native_ceiling_elevation_mm": ceiling,
                          "source_gross_area_m2": face.area * (scale / 1000) ** 2,
                          "source_opaque_area_m2": face.punched_geometry.area * (scale / 1000) ** 2,
                          "source_skylight_area_m2": sum(item.area for item in face.apertures) * (scale / 1000) ** 2,
                           "roof_binding": "room_ceiling" if face.identifier in automatic else "native_spatial_roof_clipping"
                                           if face.identifier in spatial or not bind_roofs else "explicit_room"} for face in faces)
    corner_peers = partitioned_roof_corners(model, room_floors, scale, automatic | spatial)
    for row in decisions:
        if row["policy"] == "native_room_ceiling" and row["identifier"] in corner_peers:
            automatic.remove(row["identifier"])
            row.update(policy="explicit_source_roof", adjacent_partitioned_roofs=corner_peers[row["identifier"]],
                       roof_binding="explicit_room" if bind_roofs else "native_spatial_roof_clipping")
    report["roof_selection"] = {"policy": "explicit_roofs_for_source_exceptions", "native_room_ceiling_faces": len(automatic), "explicit_source_roof_faces": sum(row["policy"] == "explicit_source_roof" for row in decisions), "faces": decisions, "host_validation": "pending",
                                "shared_ceiling_faces": shared_ceilings,
                                "roof_geometry": "source_opaque_boundary_with_geometric_holes_and_opening_cutouts",
                                 "skylight_geometry": "closed_polyline_definition_in_the_source_room_storey",
                                 "skylight_roof_assembly": "native_host_attachment_at_room_datum_or_explicit_source_enclosure",
                                "skylight_native_labels": "compact_native_identity_with_full_source_names_in_metadata",
                                "thermal_area_validation": "host_readback_required"}
    def selected(room, face):
        return str(face.type) == "RoofCeiling" and face.identifier not in automatic
    rooms = [room for room in model.rooms if any(selected(room, face) for face in room.faces)]
    source_frame = top["frame"]
    x0 = ground["center_mm"][0] + ground["width_mm"] / 2 + 5000.0
    y0 = source_frame["center_mm"][1] - source_frame["depth_mm"] / 2
    width, depth = source_frame["width_mm"], source_frame["depth_mm"]
    offset = (top["offset_mm"][0] + x0 - source_frame["alignment_mm"][0], top["offset_mm"][1] + y0 - source_frame["alignment_mm"][1])
    frame = {
        "identifier": "Roof", "floor_number": max(row["floor_number"] for row in occupied) + 1,
        "series": "", "center_mm": (x0 + width / 2, y0 + depth / 2),
        "alignment_mm": (x0, y0), "width_mm": width, "depth_mm": depth, "height_mm": 0.0,
    }
    entity = add_native(drawing, codes["SWR_FLOOR_FRAME"], "公-视口", frame, floor_frame, [(1000, "Roof"), (1000, "FloorFrame"), (1000, "centralized_roof")])
    report["roof_frame"] = dict(frame, source_story=source_story)
    report["roof_layout"] = {
        "story": "Roof", "source_story": source_story, "role": "roof", "series": "",
        "floor_number": frame["floor_number"], "source_elevation_mm": anchor,
        "reference_elevation_mm": anchor, "native_elevation_mm": native_base + height,
        "local_elevation_mm": 0.0, "offset_mm": offset, "height_mm": 0.0,
        "frame_bounds_mm": (x0, y0, x0 + width, y0 + depth),
        "room_identifiers": [room.identifier for room in rooms],
        "frame_handle": entity.handle, "frame": frame,
    }
    drawing.add_text("Roof", (x0, y0 + depth + 500.0, 0.0), 350.0, "HB-Labels")

    def convert(point):
        return (point.x * scale + offset[0], point.y * scale + offset[1], point.z * scale - anchor)

    for room in rooms:
        for face in room.faces:
            if not selected(room, face):
                continue
            start = len(report["surfaces"])
            defined = face.identifier in spatial
            parts = (face.geometry.boundary,) if defined else planar_roof_parts(face)
            roof = add_parts(drawing, codes, report, room.identifier, face.identifier, "RoofCeiling", "Roof", parts, tuple(face.normal), convert, bind=bind_roofs and not defined, planar_tolerance_mm=1.0) if parts else None
            for row in report["surfaces"][start:]:
                row.update(source_story=room.story or "Unassigned", source_identifiers=[face.identifier], source_face_identifier=face.identifier, boundary_condition=str(face.boundary_condition), reference_elevation_mm=anchor)
            for item in face.apertures:
                if defined:
                    continue
                start = len(report["surfaces"])
                add_skylight(drawing, codes, report, room.identifier, face, item, "Roof", convert, scale)
                for row in report["surfaces"][start:]:
                    row.update(source_story=room.story or "Unassigned", source_identifiers=[item.identifier], source_face_identifier=face.identifier, reference_elevation_mm=anchor)
            for item in face.doors:
                if roof is None:
                    raise ValueError("Native roof hatches require an opaque source host")
                row = add_roof_opening(drawing, codes, report, room.identifier, face, hb.opening_rect(item, "Door", model.units), roof["handle"], "Roof", convert, scale)
                row.update(source_story=room.story or "Unassigned", source_room=room.identifier, source_face_identifier=face.identifier, reference_elevation_mm=anchor)
    report["surface_scope"] = "Centralized roofs with compact-label skylights and room-bound opaque source pieces; source holes and opening cutouts retain hole-free native pieces; independent room-bound source skylights preserve native window assembly"
    low, high = map(list, drawing.extents)
    points = [(x0, y0, 0.0), (x0 + width, y0 + depth + 1000.0, 0.0)]
    points.extend(point for row in report["surfaces"] for point in row["boundary_mm"])
    for index in range(3):
        low[index] = min(low[index], *(point[index] for point in points))
        high[index] = max(high[index], *(point[index] for point in points))
    drawing.extents = (tuple(low), tuple(high))
    return report["roof_layout"]


def wall_boundary(row, floor, scale=1.0):
    points = wall_points(row)
    return tuple(Point3D((point[0] - floor["offset_mm"][0]) / scale, (point[1] - floor["offset_mm"][1]) / scale, (point[2] + floor["reference_elevation_mm"]) / scale) for point in points)


def assigned_walls(room, report, scale=1.0):
    floors = {row["story"]: row for row in report["floors"]}
    return [Face3D(wall_boundary(row, floors[row["story"]], scale)) for row in report["walls"] if not row.get("virtual_plan") and room["handle"] in (row["left_space"], row["right_space"])]


def prepare_wall_surfaces(drawing, codes, model, report):
    from .records import connect_walls, hole_wall_handles

    scale = hb.unit_scale(model.units)
    rooms = {row["identifier"]: row for row in report["rooms"]}
    floors = {row["story"]: row for row in report["floors"]}
    walls = {row["handle"]: row for row in report["walls"]}
    native_openings = defaultdict(list)
    for row in report["openings"]:
        profile = row.get("profile_mm")
        if not profile:
            continue
        floor = floors[row["story"]]
        host = walls[row["wall"]]
        boundary = [(x - floor["offset_mm"][0], y - floor["offset_mm"][1], z + floor["reference_elevation_mm"]) for x, y, z in opening_points(row, host)]
        for identifier in row["source_identifiers"]:
            native_openings[identifier].append((boundary, []))
    explicit = set()
    preserved = defaultdict(set)
    opening_rows = {row["handle"]: row for row in report["openings"]}
    records = []
    decisions = []
    for room in model.rooms:
        source = [face for face in room.faces if str(face.type) == "Wall"]
        reasons = []
        if any(abs(face.normal.z) > 1e-4 for face in source):
            reasons.append("inclined_source_wall")
        if any(face.geometry.holes for face in source):
            reasons.append("source_wall_inner_rings")
        failed_openings = {item.identifier for face in source for item in (*face.apertures, *face.doors) if not coverage(item.geometry, native_openings[item.identifier], scale, tolerance=1e-8)["passed"]}
        if failed_openings:
            reasons.append("explicit_wall_opening_geometry")
        comparison = _compare([_Surface(face.identifier, "Wall", face.geometry.scale(scale)) for face in source], [_Surface(str(index), "Wall", geometry) for index, geometry in enumerate(assigned_walls(rooms[room.identifier], report))], 0.05, 1.0)
        if comparison["extra_area_m2"] > max(1e-6, comparison["source_area_m2"] * 1e-8):
            reasons.append("source_enclosure_profile")
        if reasons:
            explicit.add(room.identifier)
            for row in report["walls"]:
                if rooms[room.identifier]["handle"] not in (row["left_space"], row["right_space"]):
                    continue
                children = [opening_rows[handle] for handle in row["openings"]]
                candidate = Face3D(wall_boundary(row, floors[row["story"]]))
                support = _compare([_Surface(face.identifier, "Wall", face.geometry.scale(scale)) for face in source], [_Surface(str(row["handle"]), "Wall", candidate)], 0.05, 1.0)
                review = []
                if support["extra_area_m2"] > 1e-6:
                    review.append("source_wall_support_required")
                if abs(row["start_mm"][2] - rooms[room.identifier]["position_mm"][2]) > 0.5:
                    review.append("room_base_alignment_required")
                affected = [item for face in source for item in (*face.apertures, *face.doors) if item.identifier in failed_openings and abs(candidate.normal.dot(item.normal)) > 0.9999 and all(candidate.plane.distance_to_point(point.scale(scale)) <= 1.0 for point in item.geometry.boundary) and planar_polygon(item.geometry.scale(scale), candidate.plane).intersection(planar_polygon(candidate, candidate.plane)).area > 1.0]
                if any(failed_openings.intersection(child["source_identifiers"]) for child in children) or affected:
                    review.append("native_opening_completion_required")
                if not review:
                    preserved[room.identifier].add(row["handle"])
                decisions.append({"handle": row["handle"], "source_room": room.identifier, "mode": "source_completion" if review else "native_wall", "reasons": review, "extra_area_m2": support["extra_area_m2"]})
        records.append({"identifier": room.identifier, "mode": "per_wall_native_with_source_completion" if reasons else "native_wall_profiles_with_source_completion", "reasons": reasons, "initial_missing_area_m2": comparison["missing_area_m2"], "initial_extra_area_m2": comparison["extra_area_m2"], "preserved_native_wall_handles": sorted(preserved[room.identifier])})
    report["wall_adaptation"] = {"schema": "native_source_wall_selection_v2", "selection_scope": "per_wall_per_room", "rooms": records, "walls": decisions, "explicit_rooms": sorted(explicit), "panel_storey": "Roof", "plan_topology_height_mm": -1.0}
    handles = {rooms[identifier]["handle"] for identifier in explicit}
    preserved_handles = {rooms[identifier]["handle"]: values for identifier, values in preserved.items()}
    removed = set()
    for row in report["walls"]:
        for field in ("left_space", "right_space"):
            if row[field] in handles and row["handle"] not in preserved_handles.get(row[field], set()):
                row[field] = 0
        if row["left_space"] == row["right_space"] == 0:
            removed.add(row["handle"])
    report["walls"] = [row for row in report["walls"] if row["handle"] not in removed]
    removed.update(row["handle"] for row in report["openings"] if row["wall"] in removed)
    report["openings"] = [row for row in report["openings"] if row["handle"] not in removed]
    drawing.entities = [entity for entity in drawing.entities if entity.handle not in removed]
    report["wall_profile_geometry"] = [row for row in report["wall_profile_geometry"] if row["handle"] not in removed]
    for row in report["walls"]:
        row["neighbors"] = [0, 0, 0, 0]
    for room in report["rooms"]:
        room["walls"] = [handle for handle in room["walls"] if handle not in removed]
        if room["identifier"] not in explicit:
            continue
        room["walls"] = sorted(preserved[room["identifier"]])
        boundary_walls = [row for row in report["walls"] if row["handle"] in room["walls"]]
        boundary_lines = [LineString([row["start_mm"][:2], row["end_mm"][:2]]) for row in boundary_walls]
        for ring_index, ring in enumerate((room["outline_mm"], *room["holes_mm"])):
            for index, (first, last) in enumerate(zip(ring, (*ring[1:], ring[0]))):
                start, end = (last, first) if ring_index == 0 else (first, last)
                line = LineString([start, end])
                cuts = {0.0, line.length}
                for candidate in boundary_lines:
                    if all(line.distance(Point(point)) <= 0.01 for point in candidate.coords):
                        cuts.update(max(0.0, min(line.length, line.project(Point(point)))) for point in candidate.coords)
                cuts = sorted(cuts)
                for part, (low, high) in enumerate(zip(cuts, cuts[1:])):
                    if high - low <= 0.01 or any(candidate.distance(line.interpolate((low + high) / 2)) <= 0.01 for candidate in boundary_lines):
                        continue
                    first, last = line.interpolate(low), line.interpolate(high)
                    row = {"identifier": f"{room['identifier']}:plan:{ring_index}:{index}:{part}", "story": room["story"], "source_room": room["identifier"], "start_mm": (first.x, first.y, room["position_mm"][2]), "end_mm": (last.x, last.y, room["position_mm"][2]), "height_mm": -1.0, "thickness_mm": 100.0, "openings": [], "neighbors": [0, 0, 0, 0], "left_space": room["handle"], "right_space": 0, "virtual_plan": True}
                    add_native(drawing, codes["SWR_WALL"], "建-墙-砖", row, wall, [(1000, row["identifier"]), (1000, "VirtualPlan")])
                    report["walls"].append(row)
                    room["walls"].append(row["handle"])
        if room.get("inner_properties"):
            walls = [row for row in report["walls"] if row["handle"] in room["walls"]]
            write_inner_rings(drawing, codes, room["inner_properties"], room["holes_mm"], [hole_wall_handles(hole, walls) for hole in room["holes_mm"]])
    for story in {row["story"] for row in report["walls"]}:
        connect_walls([row for row in report["walls"] if row["story"] == story])
    return explicit


def planar_polygon(geometry, plane, scale=1.0):
    polygon = Polygon([tuple(plane.xyz_to_xy(point)) for point in geometry.boundary], [[tuple(plane.xyz_to_xy(point)) for point in hole] for hole in geometry.holes or ()])
    if not polygon.is_valid:
        decoded = polygon.buffer(0)
        if decoded.is_valid and abs(decoded.area - polygon.area) <= max(1e-7 / scale ** 2, abs(polygon.area) * 1e-9):
            polygon = decoded
    try:
        return set_precision(polygon, OVERLAY_PRECISION_MM / scale)
    except GEOSException:
        if polygon.is_valid:
            return polygon
        raise


def polygons(shape):
    if shape.geom_type == "Polygon":
        return [shape] if shape.area > 0 else []
    return [piece for item in getattr(shape, "geoms", ()) for piece in polygons(item)]


def source_parts(shape, plane):
    result = []
    for polygon in polygons(shape):
        def ring(coordinates):
            return tuple(plane.xy_to_xyz(Point2D(x, y)) for x, y in list(coordinates)[:-1])
        geometry = Face3D(ring(polygon.exterior.coords), plane=plane, holes=tuple(ring(hole.coords) for hole in polygon.interiors) or None)
        result.extend(planar_roof_parts(Face("SourcePanel", geometry)))
    return result


def add_wall_surfaces(drawing, codes, model, report):
    scale = hb.unit_scale(model.units)
    floor = report["roof_layout"]
    rooms = {row["identifier"]: row for row in report["rooms"]}
    report["wall_panels"] = []
    residuals = {(row["source_room"], row["identifier"]): row for row in report.get("native_wall_completion", {}).get("source_residuals", [])}
    panel_openings = set()
    pending_doors = {}
    def convert(point):
        return (point.x * scale + floor["offset_mm"][0], point.y * scale + floor["offset_mm"][1], point.z * scale - floor["reference_elevation_mm"])
    def add(room, face, identifier, kind, shape, host=None):
        start = len(report["surfaces"])
        parts = [part for part in source_parts(shape, face.geometry.plane) if Face3D(part).area * scale ** 2 > 1.0]
        if parts:
            add_parts(drawing, codes, report, room.identifier, identifier, kind, floor["story"], parts, tuple(face.normal), convert, host=host, planar_tolerance_mm=1.0)
        for row in report["surfaces"][start:]:
            row.update(source_identifiers=[identifier], source_face_identifier=face.identifier, source_story=room.story or "Unassigned", reference_elevation_mm=floor["reference_elevation_mm"])
            residual = residuals.get((room.identifier, face.identifier))
            if residual is not None:
                row.update(native_wall_fallback_reason=residual["reason"], source_plane_deviation_mm=residual["source_plane_deviation_mm"])
            report["wall_panels"].append(row)
    for room in model.rooms:
        native = assigned_walls(rooms[room.identifier], report, scale)
        for face in room.faces:
            if str(face.type) != "Wall":
                continue
            plane = face.geometry.plane
            source = planar_polygon(face.geometry, plane, scale)
            matching = [geometry for geometry in native if abs(geometry.normal.dot(face.normal)) > 0.9999 and all(plane.distance_to_point(point) * scale <= 1.0 for point in geometry.boundary)]
            covered = unary_union([planar_polygon(geometry, plane, scale) for geometry in matching])
            missing = source.difference(covered)
            if missing.area * scale ** 2 <= max(1.0, source.area * scale ** 2 * 1e-10):
                continue
            children = [*face.apertures, *face.doors]
            opaque = missing.difference(unary_union([planar_polygon(item.geometry, plane, scale) for item in children]))
            add(room, face, face.identifier, "Wall", opaque)
            for item in children:
                opening = planar_polygon(item.geometry, plane, scale).intersection(missing)
                if opening.area * scale ** 2 <= 1.0:
                    continue
                kind = "WallWindow" if item in face.apertures else "WallDoor"
                add(room, face, item.identifier, kind, opening, face.identifier)
                panel_openings.add(item.identifier)
                if kind == "WallDoor":
                    pending_doors[item.identifier] = {"identifier": item.identifier, "source_identifiers": [item.identifier], "kind": "Door", "story": floor["story"], "host_identifier": face.identifier, "reason": "native_door_child_protocol_pending", "geometry_status": "source_plane_panel_preserved"}
    report["reference_openings"] = [row for row in report["reference_openings"] if row["identifier"] not in panel_openings]
    report["reference_openings"].extend(pending_doors.values())
    report["counts"].update(walls=len(report["walls"]), native_openings=len(report["openings"]), reference_openings=len(report["reference_openings"]), native_slabs=len(report["surfaces"]), native_wall_panels=len(report["wall_panels"]), native_panel_openings=len(panel_openings) - len(pending_doors), pending_door_panel_children=len(pending_doors), native_plan_walls=sum(bool(row.get("virtual_plan")) for row in report["walls"]))
    report["counts"]["native_wall_profiles"] = sum(row["status"] == "native_profile" for row in report["wall_profile_geometry"])
    report["wall_adaptation"]["source_panel_openings"] = sorted(panel_openings)
    report["wall_adaptation"]["pending_native_door_children"] = sorted(pending_doors)
    report["adaptation_scope"] = "Per-wall native objects and editable native openings take precedence; source-completion panels cover only residual geometry in the centralized envelope storey"
    if report["wall_panels"]:
        low, high = map(list, drawing.extents)
        points = [point for row in report["wall_panels"] for point in row["boundary_mm"]]
        for axis in range(3):
            low[axis] = min(low[axis], *(point[axis] for point in points))
            high[axis] = max(high[axis], *(point[axis] for point in points))
        drawing.extents = (tuple(low), tuple(high))


def route_envelope_storeys(drawing, codes, report):
    occupied = [row for row in report["floors"] if row.get("role", "occupied") == "occupied"]
    primary = {row["floor_number"]: row for row in occupied if not row.get("series")}
    room_floors = {row["identifier"]: next(floor for floor in occupied if floor["story"] == row["story"]) for row in report["rooms"]}
    numbers = set()
    for row in report["surfaces"]:
        source = room_floors.get(row.get("source_room"))
        if source is None or source["floor_number"] == max(primary) or row["kind"] != "RoofCeiling":
            continue
        ceiling = source["reference_elevation_mm"] + source["height_mm"]
        if row.get("boundary_condition") == "Adiabatic" or abs(row["normal"][2]) < 0.9999 or any(abs(point[2] + row["reference_elevation_mm"] - ceiling) > 1.0 for point in row["boundary_mm"]):
            numbers.add(source["floor_number"])
    shared_levels = {room_floors[entry["source_room"]]["floor_number"] for entry in report.get("roof_selection", {}).get("shared_ceiling_faces", {}).values()}
    direct = {number: primary[number + 1] for number in numbers & shared_levels}
    numbers = sorted(numbers - direct.keys())
    if not numbers and not direct:
        report["envelope_storeys"] = []
        return
    cursor = max(report["roof_layout"]["frame_bounds_mm"][2], *(row["frame"]["center_mm"][0] + row["frame"]["width_mm"] / 2 for row in occupied)) + 5000.0
    helpers = {}
    for number in numbers:
        source = primary[number]
        original = source["frame"]
        width, depth = original["width_mm"], original["depth_mm"]
        x0, y0 = cursor, original["alignment_mm"][1]
        cursor += width + 5000.0
        height = 0.5
        source["height_mm"] -= height
        source["frame"]["height_mm"] = source["height_mm"]
        reference = source["reference_elevation_mm"] + source["height_mm"]
        story = f"Envelope:{source['story']}"
        frame = {"identifier": story, "floor_number": number + sum(value < number for value in numbers) + 1, "series": "", "center_mm": (x0 + width / 2, y0 + depth / 2), "alignment_mm": (x0, y0), "width_mm": width, "depth_mm": depth, "height_mm": height}
        entity = add_native(drawing, codes["SWR_FLOOR_FRAME"], "公-视口", frame, floor_frame, [(1000, story), (1000, "FloorFrame"), (1000, "source_envelope")])
        offset = (source["offset_mm"][0] + x0 - original["alignment_mm"][0], source["offset_mm"][1] + y0 - original["alignment_mm"][1])
        helpers[number] = {"story": story, "source_story": source["source_story"], "role": "envelope", "series": "", "floor_number": frame["floor_number"], "source_elevation_mm": reference, "reference_elevation_mm": reference, "local_elevation_mm": 0.0, "offset_mm": offset, "height_mm": height, "frame_bounds_mm": (x0, y0, x0 + width, y0 + depth), "frame_handle": entity.handle, "frame": frame}
        for outline in list(report["building_outlines"]):
            owner = next((row for row in occupied if row["story"] == outline["story"]), None)
            if owner is None or owner["floor_number"] != number:
                continue
            dx, dy = offset[0] - owner["offset_mm"][0], offset[1] - owner["offset_mm"][1]
            def shift_ring(ring):
                return [(x + dx, y + dy) for x, y in ring]
            row = {**outline, "identifier": f"{story}:{outline['identifier']}", "story": story, "height_mm": height, "position_mm": (outline["position_mm"][0] + dx, outline["position_mm"][1] + dy, 0.0), "outline_mm": shift_ring(outline["outline_mm"]), "holes_mm": [shift_ring(ring) for ring in outline["holes_mm"]], "walls": []}
            entity = add_native(drawing, codes["SWR_SPACE"], row["layer"], row, space, [(1000, row["identifier"]), (1000, "BuildingOutline")])
            inner = attach_room_properties(drawing, codes, entity, row["holes_mm"])
            if inner:
                write_inner_rings(drawing, codes, inner, row["holes_mm"], [[] for _ in row["holes_mm"]])
            report["building_outlines"].append(row)
        drawing.add_text(story, (x0, y0 + depth + 500.0, 0.0), 350.0, "HB-Labels")
    original_layouts = {row["story"]: row for row in report["floors"]}
    original_layouts[report["roof_layout"]["story"]] = report["roof_layout"]
    opening_surfaces = {}
    for row in report["surfaces"]:
        room = room_floors.get(row.get("source_room"))
        target = (helpers.get(room["floor_number"]) or direct.get(room["floor_number"])) if room else None
        if target is None:
            continue
        source = original_layouts[row["story"]]
        shift = (target["offset_mm"][0] - source["offset_mm"][0], target["offset_mm"][1] - source["offset_mm"][1], source["reference_elevation_mm"] - target["reference_elevation_mm"])
        first, second, normal = axes(row["normal"])
        dx, dy = dot(shift, first), dot(shift, second)
        row["elevation_mm"] += dot(shift, normal)
        row["outline_mm"] = [(x + dx, y + dy) for x, y in row["outline_mm"]]
        row["holes_mm"] = [[(x + dx, y + dy) for x, y in hole] for hole in row.get("holes_mm", [])]
        row["boundary_mm"] = [tuple(value + shift[axis] for axis, value in enumerate(point)) for point in row["boundary_mm"]]
        row.update(story=target["story"], reference_elevation_mm=target["reference_elevation_mm"])
        opening_surfaces[row["identifier"]] = (shift, target)
    for row in report["openings"]:
        host = opening_surfaces.get(row.get("host_identifier"))
        if host is None:
            continue
        shift, target = host
        row["position_mm"] = tuple(value + shift[axis] for axis, value in enumerate(row["position_mm"]))
        row["story"] = target["story"]
    for row in occupied:
        original = row["floor_number"]
        row["source_native_floor_number"] = original
        row["floor_number"] = original + sum(number < original for number in numbers)
        row["frame"]["floor_number"] = row["floor_number"]
    report["roof_layout"]["floor_number"] += len(numbers)
    report["roof_layout"]["frame"]["floor_number"] = report["roof_layout"]["floor_number"]
    report["roof_frame"]["floor_number"] = report["roof_layout"]["floor_number"]
    report["floors"].extend(helpers.values())
    target_numbers = {row["story"]: row["floor_number"] for row in report["floors"]}
    for row in report["surfaces"]:
        if row["identifier"] in opening_surfaces:
            row["envelope_native_floor"] = target_numbers[row["story"]]
    report["floors"].sort(key=lambda row: (row["floor_number"], row.get("series", "")))
    report["envelope_storeys"] = list(helpers.values())
    report["counts"]["building_outlines"] = len(report["building_outlines"])
    report["wall_adaptation"]["panel_storey"] = "source_level_envelopes_and_terminal_roof"
    low, high = map(list, drawing.extents)
    for helper in helpers.values():
        high[0] = max(high[0], helper["frame_bounds_mm"][2])
        high[1] = max(high[1], helper["frame_bounds_mm"][3] + 1000)
    points = [point for row in report["surfaces"] for point in row["boundary_mm"]]
    for axis in range(3):
        low[axis] = min(low[axis], *(point[axis] for point in points))
        high[axis] = max(high[axis], *(point[axis] for point in points))
    drawing.extents = (tuple(low), tuple(high))


def add_inclined_floor_carriers(drawing, codes, model, report):
    scale = hb.unit_scale(model.units)
    floor = report["roof_layout"]
    def convert(point):
        return (point.x * scale + floor["offset_mm"][0], point.y * scale + floor["offset_mm"][1],
                point.z * scale - floor["reference_elevation_mm"])
    for room in model.rooms:
        source_base = hb.room_floor_elevation(room) * scale
        for face in room.faces:
            if str(face.type) != "Floor" or face.max.z * scale - source_base <= 1.0:
                continue
            start = len(report["surfaces"])
            add_parts(drawing, codes, report, room.identifier, face.identifier, "Floor", floor["story"],
                      planar_roof_parts(face), tuple(face.normal), convert, planar_tolerance_mm=1.0,
                      preserve_floor_normal=True)
            for row in report["surfaces"][start:]:
                row.update(source_identifiers=[face.identifier], source_face_identifier=face.identifier,
                            source_story=room.story or "Unassigned", reference_elevation_mm=floor["reference_elevation_mm"],
                            native_carrier="inclined_floor", native_carrier_category="挑空楼板", source_kind="Floor",
                            source_floor_profile="inclined" if (face.max.z - face.min.z) * scale > 1.0 else "elevated_horizontal",
                             source_room_floor_base_elevation_mm=source_base)


def explicit_floor_selection(model, report):
    scale = hb.unit_scale(model.units)
    frames = {row["story"]: row for row in report["floors"]}
    levels = {row["identifier"]: frames[row["story"]]["floor_number"] for row in report["rooms"]}
    lowest = min(levels.values())
    result = {}
    for room in model.rooms:
        floors = [face for face in room.faces if str(face.type) == "Floor"]
        if (not floors or any(face.sub_faces for face in floors)
                or any(str(face.type) == "AirBoundary" and face.normal.z < -0.9999 for face in room.faces)):
            continue
        level = levels[room.identifier]
        if max(face.max.z for face in floors) - min(face.min.z for face in floors) > 1.0 / scale:
            result[room.identifier] = "profiled_source_floor"
        elif level == lowest and all(str(face.boundary_condition) == "Outdoors" and face.min.z * scale > 1.0 for face in floors):
            result[room.identifier] = "exposed_lowest_floor_above_ground_datum"
        elif any(str(face.boundary_condition) == "Surface" and face.boundary_condition.boundary_condition_objects[-1] in levels
                 and levels[face.boundary_condition.boundary_condition_objects[-1]] + 1 < level for face in floors):
            result[room.identifier] = "nonconsecutive_source_floor_adjacency"
    return result


def add_profiled_floors(drawing, model, report, selected):
    scale = hb.unit_scale(model.units)
    frames = {f["story"]: f for f in report["floors"]}
    rooms = {row["identifier"]: row for row in report["rooms"]}
    records = []
    low, high = map(list, drawing.extents)
    for room in model.rooms:
        if room.identifier not in selected:
            continue
        owner = rooms[room.identifier]
        frame = frames[owner["story"]]
        dx, dy = frame["offset_mm"]
        base = frame["reference_elevation_mm"]
        owner.update(has_floor=False, explicit_floor_meshes=[], explicit_floor_reason=selected[room.identifier])
        for face in room.faces:
            if str(face.type) != "Floor":
                continue
            mesh = face.geometry.triangulated_mesh3d
            triangles = []
            for indices in mesh.faces:
                a, b, c = (mesh.vertices[i] for i in indices)
                if (b - a).cross(c - a).dot(face.normal) < 0:
                    b, c = c, b
                points = [(p.x * scale + dx, p.y * scale + dy, p.z * scale - base) for p in (a, b, c)]
                triangles.append(points)
                for axis in range(3):
                    low[axis] = min(low[axis], *(p[axis] for p in points))
                    high[axis] = max(high[axis], *(p[axis] for p in points))
            for part, start in enumerate(range(0, len(triangles), 10000)):
                entity = drawing.add_polyface(triangles[start:start + 10000], "建-屋顶",
                                              [(1000, face.identifier), (1000, "Floor"), (1000, room.identifier)])
                attach_surface_properties(drawing, entity, owner["native_code"], 8, 1 if str(face.boundary_condition) == "Adiabatic" else 0)
                owner["explicit_floor_meshes"].append(entity.handle)
                records.append({"handle": entity.handle, "identifier": face.identifier, "kind": "Floor", "source_kind": "Floor",
                                "source_room": room.identifier, "native_room_code": owner["native_code"], "story": frame["story"],
                                "part": part, "layer": entity.layer, "placement": "occupied_room_frame",
                                "normal": tuple(face.normal), "boundary_condition": str(face.boundary_condition),
                                "face_usage": 8, "native_carrier_category": "挑空楼板"})
    report["floor_meshes"] = records
    drawing.extents = (tuple(low), tuple(high))
    report["counts"]["native_floor_meshes"] = len(records)


def promote_inclined_enclosures(drawing, report, angle_tolerance=1.0):
    entities = {entity.handle: entity for entity in drawing.entities}
    promoted = [row for row in report["surfaces"] if row.get("native_carrier") == "inclined_floor"]
    retained = []
    for row in report["wall_panels"]:
        category = {"Wall": "屋顶", "WallWindow": "天窗"}.get(row["kind"])
        if category is None or row.get("boundary_condition") not in {"Outdoors", "Adiabatic"} or vertical_wall_normal(Vector3D(*row["normal"]), angle_tolerance):
            retained.append(row)
            continue
        usage = 1 if row["kind"] == "Wall" else 2
        carrier = "inclined_roof" if usage == 1 else "inclined_skylight"
        if usage == 1 and row["normal"][2] < -sqrt(0.5):
            if row.get("boundary_condition") == "Outdoors":
                retained.append(row)
                continue
            usage, category, carrier = 8, "挑空楼板", "inclined_floor"
        row.update(native_carrier=carrier,
                   native_carrier_category=category, source_kind=row["kind"], face_usage=usage)
        entities[row["handle"]].application_xdata["BECS_FACE_USAGE"] = ((1071, usage),)
        promoted.append(row)
        if usage == 2:
            opening = {"identifier": row["identifier"], "source_identifiers": row["source_identifiers"],
                       "kind": "Skylight", "source_kind": "WallWindow", "host_identifier": row["host_identifier"],
                       "surface_handle": row["handle"], "opening_handle": None, "part": row["part"],
                       "native_carrier": row["native_carrier"]}
            report["skylights"].append(opening)
            report["roof_openings"].append(opening)
    rooms = {row["handle"]: row for row in report["rooms"]}
    helpers = []
    for row in report["walls"]:
        if row.get("virtual_plan"):
            owner = rooms[row["left_space"] or row["right_space"]]
            row.update(height_mm=owner["height_mm"], catalog=4, base_mode=0,
                       topology_representation="native_positive_height_thermal_virtual_wall")
            helpers.append(row["handle"])
    report["wall_panels"] = retained
    report["wall_adaptation"].pop("plan_topology_height_mm", None)
    report["wall_adaptation"].update(plan_topology_height_policy="source_room_height", plan_topology_base_mode=0,
                                     plan_topology_catalog=4)
    report["enclosure_carriers"] = {
        "schema": "native_inclined_enclosure_carriers_v1", "parts": promoted,
        "positive_virtual_topology_walls": helpers,
        "source_identity": "original_wall_and_window_identifiers_geometry_and_constructions",
        "native_classification": "room_bound_roof_and_skylight_with_explicit_source_construction_roles",
        "host_acceptance": "required",
    }
    report["counts"].update(native_wall_panels=len(retained),
                            native_panel_openings=len({row["identifier"] for row in retained if row["kind"] == "WallWindow"}),
                            native_inclined_enclosure_parts=len(promoted),
                            native_inclined_window_parts=sum(row["kind"] == "WallWindow" for row in promoted),
                            native_positive_virtual_topology_walls=len(helpers),
                            native_virtual_walls=sum(row.get("catalog") == 4 for row in report["walls"]),
                            native_skylights=len(report["skylights"]))
    return promoted


def compare_native_enclosures(manifest, geometry):
    expected = manifest.get("enclosure_carriers", {})
    layouts = {row["story"]: row for row in manifest["floors"]}
    layouts[manifest["roof_layout"]["story"]] = manifest["roof_layout"]
    primary = min((row for row in manifest["floors"] if not row.get("series")), key=lambda row: row["floor_number"])
    origin = tuple(primary["offset_mm"][axis] - primary["frame"]["alignment_mm"][axis] for axis in range(2))
    native = defaultdict(list)
    for floor in geometry.get("storeys", []):
        for key in ("wall_details", "floor_details"):
            for row in floor.get(key, []):
                if row.get("handle"):
                    native[row["handle"].upper()].append(row)
    parts = []
    for source in expected.get("parts", []):
        handle = format(source["handle"], "X")
        matches = native[handle]
        actual = matches[0] if len(matches) == 1 else {}
        floor = layouts[source["story"]]
        points = [Point3D(point[0] - floor["offset_mm"][0] + origin[0],
                          point[1] - floor["offset_mm"][1] + origin[1],
                          point[2] + floor["reference_elevation_mm"]) for point in source["boundary_mm"]]
        face = Face3D(tuple(points))
        source_shape = Polygon([tuple(face.plane.xyz_to_xy(point)) for point in points])
        observed = [Point3D(*point) for point in actual.get("boundary_mm", [])]
        shape = Polygon([tuple(face.plane.xyz_to_xy(point)) for point in observed]) if len(observed) >= 3 else Polygon()
        difference = source_shape.symmetric_difference(shape).area / 1e6 if shape.is_valid else None
        plane_distance = max((face.plane.distance_to_point(point) for point in observed), default=None)
        glazed = source["native_carrier"] == "inclined_skylight"
        children = actual.get("openings", [])
        opening = children[0] if len(children) == 1 else {}
        expected_area = source_shape.area / 1e6
        actual_area = opening.get("area_m2") if glazed else actual.get("main_area_m2")
        simplified = not matches and not glazed and expected_area <= 1e-4
        if simplified:
            actual_area = 0.0
        construction = opening.get("construction_id") if glazed else actual.get("construction_id")
        area_difference = actual_area - expected_area if actual_area is not None else None
        owner_matched = str(opening.get("handle") or "").upper() == handle and str(opening.get("owner_handle") or "").upper() == handle if glazed else not children
        native_room = source["native_room_code"]
        room_matched = native_room in (actual.get("left_room"), actual.get("right_room"))
        passed = simplified or (actual.get("native_class") == "SEFloor" and room_matched and owner_matched
                  and difference is not None and difference <= max(1e-6, expected_area * 1e-6)
                  and plane_distance is not None and plane_distance <= 1.0
                  and area_difference is not None and abs(area_difference) <= max(1e-6, expected_area * 1e-6)
                  and construction == source.get("construction_id"))
        parts.append({"handle": handle, "identifier": source["identifier"], "source_kind": source["kind"],
                      "native_carrier": source["native_carrier"], "native_class": actual.get("native_class"),
                      "source_area_m2": expected_area, "native_thermal_area_m2": actual_area,
                      "area_difference_m2": area_difference, "symmetric_difference_m2": difference,
                      "maximum_plane_distance_mm": plane_distance, "expected_construction_id": source.get("construction_id"),
                      "native_construction_id": construction, "native_owner_matched": owner_matched,
                      "room_matched": room_matched, "native_tiny_opaque_part_simplified": simplified, "passed": passed})
    helpers = []
    for identity in expected.get("positive_virtual_topology_walls", []):
        matches = native[format(identity, "X")]
        row = matches[0] if len(matches) == 1 else {}
        flags = int(row.get("flags_hex", "0"), 16)
        passed = row.get("native_class") == "SEWall" and bool(flags & 0x40) and not flags & 0x100
        helpers.append({"handle": format(identity, "X"), "native_flags_hex": row.get("flags_hex"), "passed": passed})
    simplified_area = sum(row["source_area_m2"] for row in parts if row["native_tiny_opaque_part_simplified"])
    return {"passed": geometry.get("assembled") is True and simplified_area <= 1e-4 and all(row["passed"] for row in (*parts, *helpers)),
             "scope": "thermal_native_geometry_area_construction_room_and_full_window_owner_after_initialization",
             "parts": parts, "positive_virtual_topology_walls": helpers,
             "native_tiny_opaque_simplification_area_m2": simplified_area,
             "maximum_native_tiny_opaque_simplification_area_m2": 1e-4,
             "tiny_part_policy": "retained_source_CAD_geometry; native_thermal_assembly_simplification; opaque_only_and_model_total_bounded",
            "native_classification_difference": "source_wall_and_window_parts_use_native_roof_and_skylight_categories"}


def add_shade_meshes(drawing, model, report):
    floors = {row["story"]: row for row in report["floors"]}
    room_floors = {row["identifier"]: floors[row["story"]] for row in report["rooms"]}
    components = [(item, "Shade") for item in model.shades]
    components.extend((item, "ShadeMesh") for item in model.shade_meshes)
    scale = hb.unit_scale(model.units)
    records = []
    points = []
    for component, kind in components:
        owner = hb.owner_room(component)
        floor = room_floors[owner.identifier] if owner is not None else report["site_layout"]
        source_frame = SimpleNamespace(offset_mm=floor["offset_mm"], source_elevation_mm=floor["reference_elevation_mm"])
        indoor = bool(getattr(component, "is_indoor", False))
        layer = "HB-Indoor-Shade" if indoor else hb.LAYER
        if layer not in drawing.layers:
            drawing.layers[layer] = (drawing.allocate(), 41, True)
        triangles = hb.source_triangles(component, kind, source_frame, scale)
        handles = []
        for part, start in enumerate(range(0, len(triangles), 10000)):
            entity = drawing.add_polyface(triangles[start:start + 10000], layer, [(1000, component.identifier), (1000, kind), (1000, "IndoorShade" if indoor else "EnvironmentShade"), (1071, part)])
            handles.append(entity.handle)
        parent = getattr(component, "parent", None)
        records.append({"identifier": component.identifier, "kind": kind, "source_parent": getattr(parent, "identifier", None), "source_room": owner.identifier if owner is not None else None, "is_indoor": indoor, "story": floor["story"], "routing": "room_storey" if owner is not None else "site", "handle": handles[0], "handles": handles, "layer": layer, "native_class": "AcDbPolyFaceMesh", "face_count": len(triangles), "area_m2": sum(hb._triangle_area(face) for face in triangles) / 1e6, "geometry_status": "native_polyface_written", "calculation_status": "indoor_shading_semantics_pending" if indoor else "environment_assembly_pending"})
        points.extend(point for triangle in triangles for point in triangle)
    report["shading"] = {"schema": "native_shade_meshes_v2", "storey_policy": "orphan_to_site_attached_to_owner_room_storey", "source_shades": len(model.shades), "source_shade_meshes": len(model.shade_meshes), "native_shades": len(records), "native_meshes": sum(len(row["handles"]) for row in records), "site_shades": sum(row["routing"] == "site" for row in records), "room_storey_shades": sum(row["routing"] == "room_storey" for row in records), "environment_shades": sum(not row["is_indoor"] for row in records), "indoor_shades": sum(row["is_indoor"] for row in records), "status": "native_geometry_written_host_pending" if records else "no_source_shading_objects", "representation": "editable_3d_polyface_per_source_component", "environment_layer": hb.LAYER, "records": records}
    report["counts"].update(native_shades=len(records), native_shade_meshes=report["shading"]["native_meshes"])
    if points:
        low, high = map(list, drawing.extents)
        for axis in range(3):
            low[axis] = min(low[axis], *(point[axis] for point in points))
            high[axis] = max(high[axis], *(point[axis] for point in points))
        drawing.extents = (tuple(low), tuple(high))


def compare_shade_meshes(model, report, polyfaces, bases):
    components = {item.identifier: (item, "Shade") for item in model.shades}
    components.update((item.identifier, (item, "ShadeMesh")) for item in model.shade_meshes)
    floors = {row["story"]: row for row in report["floors"]}
    if report.get("site_layout"):
        floors[report["site_layout"]["story"]] = report["site_layout"]
    room_stories = {row["identifier"]: row["story"] for row in report["rooms"]}
    records = []
    for row in report.get("shading", {}).get("records", []):
        source = components.get(row["identifier"])
        matched = source is not None
        owner = hb.owner_room(source[0]) if source is not None else None
        expected_story = room_stories.get(owner.identifier) if owner is not None else "Site"
        matched = matched and row["story"] == expected_story and row.get("routing") == ("room_storey" if owner is not None else "site") and row.get("source_room") == (owner.identifier if owner is not None else None)
        observed = []
        floor = floors[row["story"]]
        frame = SimpleNamespace(offset_mm=(0.0, 0.0), source_elevation_mm=0.0)
        expected = hb.source_triangles(*source, frame, hb.unit_scale(model.units)) if matched else []
        for part, handle in enumerate(row["handles"]):
            mesh = polyfaces.get(handle, {})
            matched = matched and all(tag in mesh.get("xdata", []) for tag in ((1000, row["identifier"]), (1000, row["kind"]), (1000, "IndoorShade" if row["is_indoor"] else "EnvironmentShade"), (1071, part)))
            matched = matched and mesh.get("layer") == row["layer"] and mesh.get("layer_visible") is True
            observed.extend(tuple((point[0] - floor["offset_mm"][0], point[1] - floor["offset_mm"][1], point[2] + bases[row["story"]]) for point in triangle) for triangle in mesh.get("triangles_mm", []))
        matched = bool(matched and observed and hb.triangles_match(expected, observed, 0.01))
        records.append({"identifier": row["identifier"], "kind": row["kind"], "passed": matched, "source_triangles": len(expected), "native_triangles": len(observed), "source_story": expected_story, "source_room": owner.identifier if owner is not None else None, "is_indoor": row["is_indoor"], "calculation_status": row["calculation_status"]})
    identifiers = [row["identifier"] for row in records]
    complete = len(identifiers) == len(set(identifiers)) and set(identifiers) == set(components)
    return {"scope": "SDK shade geometry versus independently decoded native polyface vertices, indices, source identities and absolute placement", "source_objects": len(components), "complete": complete, "passed": complete and all(row["passed"] for row in records), "records": records, "host_validation": "pending"}


def compare_assembled_shades(model, manifest, native_report):
    floors = {row["story"]: row for row in manifest["floors"]}
    if manifest.get("site_layout"):
        floors[manifest["site_layout"]["story"]] = manifest["site_layout"]
    records = [row for row in manifest.get("shading", {}).get("records", []) if not row["is_indoor"]]
    handles = {format(handle, "X"): row for row in records for handle in row["handles"]}
    components = {item.identifier: (item, "Shade") for item in model.shades if not item.is_indoor}
    components.update((item.identifier, (item, "ShadeMesh")) for item in model.shade_meshes)
    assembly = native_report.get("result") or native_report.get("assembly") or {}
    observed = {}
    issues = []
    native_count = 0
    observed_floors = list(assembly.get("floors", []))
    if assembly.get("site_shading"):
        observed_floors.append(assembly["site_shading"])
    for floor in observed_floors:
        count = floor.get("shade_objects", 0)
        meshes, identities = floor.get("shade_faces", []), floor.get("shade_handles", [])
        native_count += count
        if len(meshes) != count or len(identities) != count:
            issues.append({"code": "shade_list_coverage_required", "story": floor["story"]})
        expected = floors.get(floor["story"])
        for identity, mesh in zip(identities, meshes):
            identity = str(identity or "").upper()
            source = handles.get(identity)
            if source is None or expected is None or source["story"] != floor["story"] or identity in observed:
                issues.append({"code": "shade_source_mapping_required", "handle": identity, "story": floor["story"]})
                continue
            triangles = []
            for face in mesh:
                if len(face) != 4:
                    issues.append({"code": "shade_face_geometry_required", "handle": identity})
                    continue
                points = [tuple(point[axis] * 1000 + (expected["frame"]["alignment_mm"][axis] - expected["offset_mm"][axis] if axis < 2 else 0.0) for axis in range(3)) for point in face]
                for indices in ((0, 1, 2), (0, 2, 3)):
                    triangle = tuple(points[index] for index in indices)
                    if hb._triangle_area(triangle) > 1e-6:
                        triangles.append(triangle)
            observed[identity] = triangles
    result = []
    frame = SimpleNamespace(offset_mm=(0.0, 0.0), source_elevation_mm=0.0)
    for identifier, component in components.items():
        row = next((row for row in records if row["identifier"] == identifier), {})
        source_handles = [format(handle, "X") for handle in row.get("handles", [])]
        expected = hb.source_triangles(*component, frame, hb.unit_scale(model.units))
        triangles = [triangle for handle in source_handles for triangle in observed.get(handle, [])]
        passed = bool(source_handles and all(handle in observed for handle in source_handles) and hb.triangles_match(expected, triangles, 0.1))
        result.append({"identifier": identifier, "passed": passed, "handles": source_handles, "source_triangles": len(expected), "native_triangles": len(triangles)})
    complete = len(records) == len(components) and {row["identifier"] for row in records} == set(components) and set(observed) == set(handles) and native_count == len(handles)
    passed = native_report.get("status") in {"completed", "review_required"} and assembly.get("assembled") is True and complete and not issues and all(row["passed"] for row in result)
    return {"scope": "BESI assembled exterior shading meshes, persisted source handles and absolute source geometry", "passed": bool(passed), "complete": complete, "source_objects": len(components), "native_meshes": native_count, "records": result, "issues": issues, "indoor_geometry_objects": manifest.get("shading", {}).get("indoor_shades", 0), "calculation_coefficients": "pending"}
