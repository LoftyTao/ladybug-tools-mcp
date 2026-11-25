"""Independent binary readback, source coverage, quality and export gates."""

from __future__ import annotations

import struct
from collections import Counter, defaultdict
from math import cos, fsum, hypot, sin, sqrt, tan, ulp

from ladybug_geometry.geometry3d import Face3D, Point3D
from shapely import set_precision
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .. import model as hb
from .binary import BitReader, inspect_container
from .geometry import _Surface, _compare, area_metrics, coverage, opening_boundary_profile, opening_points, wall_points
from .metadata import compare_boundary_conditions, source_boundary
from .surfaces import axes, compare_shade_meshes, dot, wcs_points
from .walls import effective_source_shape, physical_walls, plan_wall_conflicts


def require(condition, message):
    if not condition:
        raise ValueError(message)


def classes(data, section):
    offset, size = section
    reader = BitReader(data[offset + 20:offset + size - 18])
    result = {}
    while reader.limit - reader.position > 7:
        number = reader.bs()
        flags = reader.bs()
        application, cpp, name = reader.text(), reader.text(), reader.text()
        proxy, category = reader.b(), reader.bs()
        require(number == 500 + len(result) and category in (498, 499), "Class definitions require sequential identities and native categories")
        result[number] = {"cpp": cpp, "name": name, "application": application, "entity": category == 498, "proxy": proxy, "flags": flags}
    return result


def extended_tags(data):
    reader = BitReader(data)
    result = []
    while reader.position < reader.limit:
        code = reader.rc() + 1000
        if code == 1000:
            size = reader.rc()
            require(int.from_bytes(reader.raw(2), "big") == 39, "Native extended strings require the declared GBK codepage")
            payload = reader.raw(size)
            require(payload.endswith(b"\0"), "Extended strings require their stored terminator")
            value = payload[:-1].decode("gbk")
        elif code in (1010, 1011, 1012, 1013):
            value = tuple(reader.rd() for _ in range(3))
        elif code in (1040, 1041, 1042):
            value = reader.rd()
        elif code == 1005:
            value = int.from_bytes(reader.raw(8), "big")
        elif code == 1071:
            value = struct.unpack("<i", reader.raw(4))[0]
        elif code == 1070:
            value = struct.unpack("<h", reader.raw(2))[0]
        else:
            raise ValueError("Native extended fields require a supported type")
        result.append((code, value))
    return result


def common(record, entity, applications=None):
    reader = BitReader(record["body"], limit=record["data_bits"])
    require(reader.bs() == record["type_code"] and reader.rl() == record["data_bits"], "Object stream headers require consistent type and size fields")
    require(reader.handle() == (0, record["handle"]), "Object identities require an absolute owning handle")
    tags = []
    while True:
        size = reader.bs()
        if size == 0:
            break
        app = reader.handle()
        require(app[0] == 5 and app[1] > 0, "Extended data requires a registered application handle")
        values = extended_tags(reader.raw(size))
        tags.extend(values)
        if applications is not None:
            applications[app[1]] = values
    if entity:
        require(reader.b() == 0 and reader.bb() == 0 and reader.bl() == 0 and reader.b() == 0, "Native entities require explicit model ownership and links")
        reader.bs()
        require(reader.bd() == 1 and reader.bb() == 0 and reader.bb() == 0 and reader.bs() == 0, "Native entity formatting requires declared defaults")
        reader.rc()
    else:
        require(reader.bl() == 0, "Native database objects require the declared reactor count")
    handles = BitReader(record["body"], position=record["data_bits"])
    references = []
    while handles.limit - handles.position >= 8:
        references.append(handles.handle())
    return reader, references, tags


class NativeReader:
    def __init__(self, reader, references):
        self.r = reader
        self.references = iter(references)

    def ref(self, hard=False):
        code, value = next(self.references)
        require(code == (5 if hard else 4), "Native references require the declared pointer semantics")
        return value

    def base(self):
        require(self.r.rc() == 251, "The native base requires its supported BESI serialization version")
        require(self.r.bd() == 100 and self.r.bd() == 0, "The native base requires its declared scale and elevation")
        self.r.rc()
        self.object_description = self.r.text()
        self.r.text()
        return self.r.rc()

    def poly(self, closed=True):
        require(self.r.rc() == int(closed), "Native polygons require their declared closure flag")
        count = self.r.bs()
        require((3 if closed else 2) <= count <= 65535, "Native polygons require a bounded vertex count")
        points = []
        for _ in range(count):
            point = tuple(self.r.rd() for _ in range(2))
            require(self.r.bd() == 0, "The native polygon codec requires straight segments")
            points.append(point)
        return points


def decode_native(name, reader, references):
    f = NativeReader(reader, references)
    mode = f.base()
    version = reader.rc()
    result = {"version": version, "base_mode": mode, "object_description": f.object_description}
    if name == "SWR_WALL":
        require(version == 6, "The wall codec requires the analyzed legacy native layout")
        result.update(start_mm=reader.point(), end_mm=reader.point())
        reader.bd()
        result["flags"] = reader.bl()
        result.update(left_width_mm=reader.bd(), right_width_mm=reader.bd(), height_mm=reader.bd())
        result["columns"] = [f.ref(), f.ref()]
        result["neighbors"] = [f.ref() for _ in range(4)]
        result["catalog"] = reader.rc()
        result["profile_mm"] = f.poly(False) if result["flags"] & 0x10 else []
        result["openings"] = [f.ref() for _ in range(reader.bs())]
        result["material"] = reader.rc()
        require(reader.rc() == 0, "The wall codec requires the declared curtain-data count")
        for _ in range(5):
            reader.bd()
        result["layers"] = [f.ref(True) for _ in range(4)]
        result.update(left_space=f.ref(), right_space=f.ref())
        result["oblique_angle"] = reader.bd()
    elif name == "SWR_SPACE":
        require(version == 4, "The room codec requires the analyzed native polygon layout")
        result.update(position_mm=reader.point(), identifier=reader.text(), name=reader.text())
        result["statistics"] = [reader.bd() for _ in range(8)]
        result["height_mm"] = result["statistics"][6]
        result["outline_mm"] = f.poly()
        result["flags"] = reader.bs()
        result["category"] = reader.rc()
        reader.rc()
        reader.rc()
        result["style"] = f.ref(True)
        for _ in range(3):
            reader.bd()
        result["walls"] = [f.ref() for _ in range(reader.rc())]
    elif name == "SWR_OPENING":
        require(version == 3, "The opening codec requires the analyzed legacy native layout")
        result.update(position_mm=reader.point(), width_mm=reader.bd())
        reader.bd()
        result.update(height_mm=reader.bd(), angle_rad=reader.bd())
        reader.rc()
        result["category"] = reader.rc()
        reader.bd()
        result["mark"] = reader.text()
        result.update(block_2d=f.ref(True), block_3d=f.ref(True))
        reader.point()
        result["wall"] = f.ref()
        require(reader.bl() == 0, "The opening codec requires the declared simple-opening flags")
        result["styles_and_layers"] = [f.ref(True) for _ in range(5)]
        for _ in range(4):
            reader.bd()
        require(reader.bs() == 0, "The opening codec requires the declared profile count")
        reader.rc()
    elif name == "SWR_FLOOR_FRAME":
        require(version == 1, "The floor codec requires its analyzed native version")
        result.update(center_mm=tuple(reader.rd() for _ in range(2)), alignment_mm=tuple(reader.rd() for _ in range(2)), width_mm=reader.bd(), depth_mm=reader.bd(), height_mm=reader.bd(), label=reader.text())
    elif name == "SWR_SLAB":
        require(version == 3, "Native surfaces require the analyzed slab version")
        result.update(thickness_mm=reader.bd(), flags=reader.bl(), elevation_mm=reader.bd(), outline_mm=f.poly())
        hole_count = reader.bs()
        require(0 <= hole_count <= 65535, "Native surfaces require a bounded hole count")
        result["holes_mm"] = [f.poly() for _ in range(hole_count)]
        result["normal"] = reader.point()
        reader.rc()
        result["layers"] = [f.ref(True) for _ in range(3)]
    else:
        raise ValueError("The native entity requires a registered native codec")
    require(reader.position == reader.limit, "Native data requires exact field-stream consumption")
    require(next(f.references, None) is None, "Native handles require exact reference-stream consumption")
    return result


def properties(reader, references, include_types=False):
    require(reader.rc() == 1, "Native property objects require their supported version")
    refs = iter(references)
    result = {}
    typed = []
    for _ in range(reader.bs()):
        typ, name = reader.rc(), reader.text()
        if typ == 0:
            value = reader.bl()
            if value >= 0x80000000:
                value -= 0x100000000
        elif typ == 1:
            value = reader.bd()
        elif typ == 2:
            value = reader.text()
        elif typ == 3:
            value = reader.point()
        elif typ == 6:
            value = [next(refs)[1] for _ in range(reader.bs())]
        else:
            raise ValueError("Native properties require a supported native field type")
        result[name] = value
        typed.append([name, typ, value])
    require(reader.position == reader.limit and next(refs, None) is None, "Native properties require exact stream consumption")
    return (result, typed) if include_types else result


def ring_area(points):
    return abs(signed_ring_area(points))


def signed_ring_area(points):
    x, y = points[0]
    return fsum((a[0] - x) * (b[1] - y) - (a[1] - y) * (b[0] - x) for a, b in zip(points, (*points[1:], points[0]))) / 2


def close(first, second, tolerance=1e-6):
    if isinstance(first, (list, tuple)):
        return len(first) == len(second) and all(close(a, b, tolerance) for a, b in zip(first, second))
    return abs(first - second) <= tolerance


def surface_polygons(native):
    if native["type"] == "POLYLINE_PFACE":
        return [(ring, []) for ring in native["polygons_mm"]]
    return [(wcs_points(native), [wcs_points(dict(native, outline_mm=ring)) for ring in native["holes_mm"]])]


def check_roof_mesh(source, mesh, room_code):
    usage = source["face_usage"]
    props = mesh["property_records"]
    require((usage in (1, 2) or usage == 5 and source["kind"] == "Wall" and source["boundary_condition"] == "Outdoors")
            and mesh["application_xdata"].get("BECS_FACE_USAGE") == [(1071, usage)]
            and (1000, source["identifier"]) in mesh["application_xdata"].get("HB_BESI", ())
            and bool(room_code) and props.get("BECS_ROOF_SPACE_CODE") == [(280, 1), (301, room_code)]
            and props.get("BECS_ROOF_BORDTYPE") == [(280, 1), (301, str(source["board_type"]))],
            "Bound roof meshes require exact source, usage, board and room identities")
    first, second, normal = axes(source["normal"])
    shapes = []
    for ring in mesh["polygons_mm"]:
        require(all(abs(dot(p, normal) - source["elevation_mm"]) <= 1e-5 for p in ring),
                "Bound roof mesh faces require their source plane")
        shape = Polygon([(dot(p, first), dot(p, second)) for p in ring])
        require(shape.is_valid and shape.area > 0 and shape.exterior.is_ccw,
                "Bound roof mesh faces require outward winding and positive area")
        shapes.append(shape)
    actual = unary_union(shapes)
    target = Polygon(source["outline_mm"], source["holes_mm"])
    limit = max(1e-5, target.area * 1e-10)
    require(target.symmetric_difference(actual).area <= limit and abs(sum(p.area for p in shapes) - actual.area) <= limit,
            "Bound roof meshes require complete disjoint source patches")


def mesh_outer_boundary(mesh):
    edges = Counter()
    for ring in mesh["polygons_mm"]:
        pts = list(map(tuple, ring))
        edges.update(zip(pts, pts[1:] + pts[:1]))
    exterior = edges - Counter({(b, a): count for (a, b), count in edges.items()})
    links = dict(exterior.keys())
    require(bool(links) and len(links) == sum(exterior.values()), "A bound material patch requires an unbranched perimeter")
    start = next(iter(links))
    ring, vertex = [], start
    while vertex in links:
        ring.append(vertex)
        vertex = links.pop(vertex)
    require(vertex == start and not links and len(ring) > 2, "A bound material patch requires one complete outer boundary")
    return ring


def inspect_native(data, expected=None, include_geometry=False):
    result = inspect_container(data)
    definitions = classes(data, result["sections"][1])
    objects = {row["handle"]: row for row in result["objects"]}
    decoded = {}
    dictionaries = {}
    prop_objects = {}
    xrecords = {}
    blocks = {}
    polylines = {}
    lines = {}
    polyfaces = {}
    mesh_vertices = {}
    mesh_records = {}
    sequence_ends = {}
    layers = {}
    appids = {}
    reference_count = 0
    counts = Counter()
    standard_entities = {1, 4, 5, 6, 0x0D, 0x0E, 0x13, 0x1D, 0x4D}
    for handle, record in objects.items():
        typ = record["type_code"]
        definition = definitions.get(typ)
        name = definition["name"] if definition else hex(typ)
        entity = definition["entity"] if definition else typ in standard_entities
        applications = {}
        reader, refs, tags = common(record, entity, applications)
        count = 5 if entity else 3 if typ == 0x4F else 2
        require(len(refs) >= count, "Database objects require their complete common references")
        for code, identity in refs:
            require(code in (2, 3, 4, 5) and (identity == 0 or identity in objects), "All stored references require existing drawing objects")
            reference_count += int(identity != 0)
        if name in {"SWR_WALL", "SWR_SPACE", "SWR_OPENING", "SWR_FLOOR_FRAME", "SWR_SLAB"}:
            row = decode_native(name, reader, refs[count:])
            row.update(handle=handle, type=name, dictionary=refs[1][1], layer_handle=refs[4][1], xdata=tags, application_xdata=applications)
            if name == "SWR_SLAB":
                row["face_usage"] = next((value for code, value in tags if code == 1071), None)
            decoded[handle] = row
            counts[name] += 1
        elif name == "SWR_PROPOBJ":
            values, typed = properties(reader, refs[count:], include_types=True)
            prop_objects[handle] = {"values": values, "properties": typed, "dictionary": refs[1][1]}
        elif typ == 0x31:
            blocks[handle] = {"name": reader.text(), "xdata": tags}
        elif typ == 0x43:
            appids[handle] = reader.text()
        elif typ == 0x33:
            name = reader.text()
            require(reader.b() == 0 and reader.bs() == 0 and reader.b() == 0, "Native layers require local table definitions")
            flags, color = reader.bs(), reader.bs()
            require(reader.position == reader.limit, "Native layers require complete field streams")
            layers[handle] = {"name": name, "flags": flags, "color": color, "visible": flags & 2 == 0}
        elif typ == 0x1D:
            vertex_count, face_count = reader.bs(), reader.bs()
            require(vertex_count >= 3 and face_count > 0 and reader.position == reader.limit and len(refs) == 8, "Polyface meshes require complete bounded counts and child references")
            require([code for code, value in refs[5:]] == [4, 4, 3], "Polyface child references require declared ownership semantics")
            polyfaces[handle] = {"vertex_count": vertex_count, "face_count": face_count, "first_vertex": refs[5][1], "last_vertex": refs[6][1], "seqend": refs[7][1], "owner": refs[0][1], "layer_handle": refs[4][1], "xdata": tags, "dictionary": refs[1][1], "application_xdata": applications}
            counts["POLYLINE_PFACE"] += 1
        elif typ == 0x0D:
            require(reader.rc() == 192, "Polyface vertices require their spatial mesh flags")
            mesh_vertices[handle] = {"point_mm": reader.point(), "owner": refs[0][1], "next": refs[3][1]}
            require(reader.position == reader.limit and len(refs) == 5, "Polyface vertices require complete field and reference streams")
        elif typ == 0x0E:
            mesh_records[handle] = {"indices": [reader.bs() for _ in range(4)], "owner": refs[0][1], "next": refs[3][1]}
            require(reader.position == reader.limit and len(refs) == 5, "Polyface face records require complete index and reference streams")
        elif typ == 6:
            sequence_ends[handle] = refs[0][1]
            require(reader.position == reader.limit and len(refs) == 5, "Polyface sequence ends require an empty field stream and their owner")
        elif typ == 0x13:
            zero = reader.b()
            start, end = [], []
            for _ in range(2 if zero else 3):
                start.append(reader.rd())
                end.append(reader.dd(start[-1]))
            if zero:
                start.append(0.0)
                end.append(0.0)
            require(reader.b() == 1 and reader.b() == 1 and reader.position == reader.limit, "Native lines require default thickness, extrusion and complete field consumption")
            lines[handle] = {"start_mm": start, "end_mm": end, "xdata": tags}
        elif typ == 0x4D:
            flags = reader.bs()
            require(flags & ~521 == 0, "Native polylines require supported closure, elevation and plane fields")
            elevation = reader.bd() if flags & 8 else 0.0
            normal = reader.point() if flags & 1 else (0.0, 0.0, 1.0)
            size = reader.bl()
            require(2 <= size <= 20000, "Native polylines require bounded vertex counts")
            points = [(reader.rd(), reader.rd())]
            for _ in range(size - 1):
                previous = points[-1]
                points.append((reader.dd(previous[0]), reader.dd(previous[1])))
            require(reader.position == reader.limit, "Native polylines require exact stream consumption")
            polylines[handle] = {"points": points, "normal": normal, "elevation_mm": elevation, "closed": bool(flags & 512), "owner": refs[0][1],
                                 "dictionary": refs[1][1], "layer_handle": refs[4][1], "application_xdata": applications}
        elif typ == 0x2A or typ == 500:
            size = reader.bl()
            reader.bs()
            reader.rc()
            names = [reader.text() for _ in range(size)]
            dictionaries[handle] = dict(zip(names, (value for code, value in refs[count:count + size])))
        elif typ == 0x4F:
            payload = BitReader(reader.raw(reader.bl()))
            fields = []
            while payload.position < payload.limit:
                code = payload.rs()
                if code == 280:
                    value = payload.rc()
                elif code in (1, 301, 302):
                    length = payload.rs()
                    require(payload.rc() == 39, "Native XRECORD text requires the declared GBK codepage")
                    encoded = payload.raw(length)
                    require(encoded.endswith(b"\0"), "Native XRECORD strings require a stored terminator")
                    value = encoded[:-1].decode("gbk")
                else:
                    raise ValueError("Native XRECORD data requires a supported field")
                fields.append((code, value))
            require(reader.bs() == 1 and reader.position == reader.limit, "XRECORD data requires exact payload consumption")
            xrecords[handle] = fields
    for mesh in (*polylines.values(), *polyfaces.values()):
        require(mesh["layer_handle"] in layers, "Drawing geometry requires a decoded layer")
        mesh.update(layer=layers[mesh["layer_handle"]]["name"], layer_visible=layers[mesh["layer_handle"]]["visible"])
        mesh["application_xdata"] = {appids[identity]: values for identity, values in mesh["application_xdata"].items()}
        mesh["property_records"] = {name: xrecords[identity] for name, identity in dictionaries.get(mesh["dictionary"], {}).items() if identity in xrecords}
    for handle, mesh in polyfaces.items():
        vertices = []
        faces = []
        children = set()
        child = mesh["first_vertex"]
        while child != mesh["seqend"]:
            require(child not in children and child in objects, "Polyface vertex chains require bounded unique children")
            children.add(child)
            vertex = mesh_vertices.get(child)
            record = vertex or mesh_records.get(child)
            require(record is not None and record["owner"] == handle, "Polyface children require reciprocal mesh ownership")
            if vertex:
                require(not faces, "Polyface spatial vertices require precedence over face records")
                vertices.append(vertex["point_mm"])
            else:
                faces.append(record["indices"])
            if child == mesh["last_vertex"]:
                child = mesh["seqend"]
            else:
                child = record["next"]
        require(sequence_ends.get(mesh["seqend"]) == handle and len(vertices) == mesh["vertex_count"] and len(faces) == mesh["face_count"], "Polyface meshes require complete owned vertex, face and sequence-end lists")
        require(all(all(1 <= index <= len(vertices) for index in face[:3]) and 0 <= face[3] <= len(vertices) for face in faces),
                "Polyface faces require valid one-based vertex indices")
        polygons = [tuple(vertices[i - 1] for i in face if i) for face in faces]
        mesh.update(vertices_mm=vertices, faces=faces, polygons_mm=polygons,
                    triangles_mm=[(p[0], p[i], p[i+1]) for p in polygons for i in range(1, len(p)-1)])
    require(len(mesh_vertices) == sum(row["vertex_count"] for row in polyfaces.values()) and len(mesh_records) == sum(row["face_count"] for row in polyfaces.values()) and len(sequence_ends) == len(polyfaces), "Polyface children require complete parent ownership coverage")
    for row in decoded.values():
        require(row["layer_handle"] in layers, "Native entities require a decoded drawing layer")
        row.update(layer=layers[row["layer_handle"]]["name"], layer_visible=layers[row["layer_handle"]]["visible"])
        row["application_xdata"] = {appids[handle]: values for handle, values in row["application_xdata"].items()}
        row["property_records"] = {name: xrecords[handle] for name, handle in dictionaries.get(row["dictionary"], {}).items() if handle in xrecords}
    for row in (item for item in decoded.values() if item["type"] == "SWR_FLOOR_FRAME"):
        dictionary = dictionaries.get(row["dictionary"], {})
        prop = dictionary.get("SRootEntity")
        row["series"] = prop_objects[prop]["values"].get("Floor_Series", "") if prop in prop_objects else ""
    rooms = {identity: row for identity, row in decoded.items() if row["type"] == "SWR_SPACE" and row["category"] == 0}
    walls = {identity: row for identity, row in decoded.items() if row["type"] == "SWR_WALL"}
    windows = {identity: row for identity, row in decoded.items() if row["type"] == "SWR_OPENING"}
    slabs = {identity: row for identity, row in decoded.items() if row["type"] == "SWR_SLAB"}
    roof_meshes = {h: m for h, m in polyfaces.items() if m["application_xdata"].get("BECS_FACE_USAGE") in ([(1071, 1)], [(1071, 2)], [(1071, 5)])}
    for handle, mesh in roof_meshes.items():
        props = mesh["property_records"]
        code = props.get("BECS_ROOF_SPACE_CODE", [])
        board = props.get("BECS_ROOF_BORDTYPE", [])
        require(len(code) == len(board) == 2 and code[0] == board[0] == (280, 1) and code[1][0] == board[1][0] == 301
                and code[1][1] in {r["identifier"] for r in rooms.values()}, "Bound roof meshes require a recognized room code")
        mesh.update(handle=handle, type="POLYLINE_PFACE", source_room=code[1][1], board_type=int(board[1][1]),
                    face_usage=mesh["application_xdata"]["BECS_FACE_USAGE"][0][1])
        decoded[handle] = mesh
    skylights = {identity: row for identity, row in (slabs | roof_meshes).items() if row["face_usage"] == 2}
    for row in slabs.values():
        require(signed_ring_area(row["outline_mm"]) > 0, f"Native surface {row['handle']:X} requires a right-handed outer ring relative to its explicit normal")
        require(all(signed_ring_area(hole) < 0 for hole in row["holes_mm"]), f"Native surface {row['handle']:X} requires oppositely oriented inner rings")
        dictionary = dictionaries.get(row["dictionary"], {})
        if "BECS_ROOF_SPACE_CODE" not in dictionary:
            row["source_room"] = ""
            row["board_type"] = 0
            continue
        row["source_room"] = xrecords[dictionary["BECS_ROOF_SPACE_CODE"]][1][1]
        row["board_type"] = int(xrecords[dictionary["BECS_ROOF_BORDTYPE"]][1][1])
        require(row["source_room"] == "" or row["source_room"] in {space["identifier"] for space in rooms.values()}, "Native surfaces require a recognized source-room association or the unbound roof path")
    inner_count = 0
    for row in (item for item in decoded.values() if item["type"] == "SWR_SPACE"):
        dictionary = dictionaries[row["dictionary"]]
        require(xrecords[dictionary["BECS_ROOM_HEIGHT_BY_STOREY"]] == [(280, 1), (301, "0")], "Native rooms require explicit independent-height settings")
        holes = []
        if "SwrInnerSpace" in dictionary:
            parent = prop_objects[dictionary["SwrInnerSpace"]]
            for index in range(parent["values"]["NumSpc"]):
                child = prop_objects[dictionaries[parent["dictionary"]][f"InnerSpc{index}"]]["values"]
                holes.append([child[f"P{number}"][:2] for number in range(child["NumPts"])])
        row["holes_mm"] = holes
        row["area_m2"] = (ring_area(row["outline_mm"]) - sum(ring_area(hole) for hole in holes)) / 1e6
        require(row["area_m2"] > 0 and row["height_mm"] > 0, "Native spaces require positive polygon areas and heights")
        inner_count += len(holes)
    for identity, row in walls.items():
        require(abs(row["height_mm"]) > 0 and (row["catalog"] == 4 or row["left_width_mm"] + row["right_width_mm"] > 0), "Native walls require physical or virtual heights and physical thicknesses or a thermal virtual catalog")
        require(row["base_mode"] in (0, 1), "Native walls require a declared physical or topology base mode")
        for room in (row["left_space"], row["right_space"]):
            require(room == 0 or room in rooms and identity in rooms[room]["walls"], "Wall sides and native rooms require reciprocal references")
        for neighbor in row["neighbors"]:
            require(neighbor == 0 or neighbor in walls and identity in walls[neighbor]["neighbors"], "Wall endpoint relations require reciprocal native links")
        for window in row["openings"]:
            require(window in windows and windows[window]["wall"] == identity, "Wall and opening references require reciprocal links")
    for identity, row in windows.items():
        require(row["width_mm"] > 0 and row["height_mm"] > 0, "Native openings require positive sizes")
        if row["wall"] in walls:
            require(identity in walls[row["wall"]]["openings"], "Native openings require reciprocal wall references")
        else:
            require(row["wall"] in slabs, "Native openings require a native wall or surface host")
    if expected:
        floor_meshes = expected.get("floor_meshes", [])
        mesh_sources = [r for r in expected.get("surfaces", ()) if r.get("native_class") == "POLYLINE_PFACE"]
        require(len(roof_meshes) == len(mesh_sources) == expected["counts"].get("native_roof_meshes", 0)
                and set(roof_meshes) == {s["handle"] for s in mesh_sources}, "Bound roof meshes require complete native handle coverage")
        room_codes = {r["identifier"]: rooms[r["handle"]]["identifier"] for r in expected["rooms"]}
        for source in mesh_sources:
            check_roof_mesh(source, roof_meshes[source["handle"]], room_codes[source["source_room"]])
        require(len(polyfaces) == expected.get("counts", {}).get("native_shade_meshes", 0) + len(floor_meshes) + len(roof_meshes), "Native mesh counts require complete floor, roof and shade coverage")
        owners = {handle: row for row in expected["rooms"] for handle in row.get("explicit_floor_meshes", [])}
        require(set(owners) == {row["handle"] for row in floor_meshes} and len(owners) == len(floor_meshes),
                "Native floor meshes require distinct room-owned identities")
        mesh_frames = [floor for floor in expected["floors"] if floor.get("role") == "physical_floors"]
        if mesh_frames:
            require(len(mesh_frames) == 1 and bool(floor_meshes), "Physical floor geometry requires one dedicated frame")
            frame, = mesh_frames
            require(all(s["story"] == frame["story"] for s in floor_meshes)
                    and all(s["story"] != frame["story"] for s in (*expected["rooms"], *expected["surfaces"], *expected["building_outlines"]))
                    and frame["floor_number"] > expected["roof_layout"]["floor_number"],
                    "Physical floors require a separate frame from room ceilings and roofs")
            physical = decoded[frame["frame_handle"]]
            roof = decoded[expected["roof_layout"]["frame_handle"]]
            def limits(f):
                x, y = f["center_mm"]
                return x - f["width_mm"] / 2, y - f["depth_mm"] / 2, x + f["width_mm"] / 2, y + f["depth_mm"] / 2
            x0, y0, x1, y1 = limits(physical)
            require(x0 > limits(roof)[2] and all(x0 <= x <= x1 and y0 <= y <= y1 for handle in owners
                    for triangle in polyfaces[handle]["triangles_mm"] for x, y, _ in triangle),
                    "Physical floor vertices require their own native frame bounds")
        for source in floor_meshes:
            mesh = polyfaces[source["handle"]]
            owner = owners[source["handle"]]
            resident = source.get("placement") == "occupied_room_frame"
            expected_layer = "建-屋顶" if resident or "layer" not in source else "建-楼板"
            if resident:
                frame = next(f for f in expected["floors"] if f["story"] == owner["story"])
                physical = decoded[frame["frame_handle"]]
                cx, cy = physical["center_mm"]
                require(frame.get("role", "occupied") == "occupied" and source["story"] == owner["story"]
                        and all(abs(x-cx) <= physical["width_mm"]/2 and abs(y-cy) <= physical["depth_mm"]/2
                                for tri in mesh["triangles_mm"] for x,y,z in tri),
                        "Source floor vertices must lie in their occupied storey")
            require(mesh["application_xdata"].get("BECS_FACE_USAGE") == [(1071, 8)] and mesh["layer"] == expected_layer
                    and source.get("layer", expected_layer) == expected_layer
                    and (1000, source["identifier"]) in mesh["xdata"], "Native physical floor meshes require their floor role and source identity")
            props = mesh["property_records"]
            require(source["source_room"] == owner["identifier"] and props.get("BECS_ROOF_SPACE_CODE") == [(280, 1), (301, owner["native_code"])]
                    and props.get("BECS_ROOF_BORDTYPE") == [(280, 1), (301, "1" if source["boundary_condition"] == "Adiabatic" else "0")],
                    "Native physical floor meshes require source room and boundary bindings")
        groups = ((expected["walls"], "SWR_WALL", ("start_mm", "end_mm", "height_mm", "neighbors", "left_space", "right_space", "openings")), (expected["rooms"] + expected["building_outlines"], "SWR_SPACE", ("position_mm", "height_mm", "outline_mm", "area_m2", "walls")), (expected["openings"], "SWR_OPENING", ("position_mm", "width_mm", "height_mm", "angle_rad", "wall", "block_2d", "block_3d")), ([floor["frame"] for floor in expected["floors"]] + ([expected["roof_frame"]] if expected.get("roof_frame") else []) + ([{key: value for key, value in expected["ground_frame"].items() if key != "label"}] if expected.get("ground_frame") else []), "SWR_FLOOR_FRAME", ("center_mm", "alignment_mm", "width_mm", "depth_mm", "height_mm", "series")))
        groups += (([s for s in expected.get("surfaces", []) if s.get("native_class") != "POLYLINE_PFACE"], "SWR_SLAB", ("normal", "elevation_mm", "outline_mm", "holes_mm")),)
        for rows, name, fields in groups:
            require(counts[name] == len(rows), "Native class counts require complete source coverage")
            for source in rows:
                row = decoded[source["handle"]]
                for key in fields:
                    require(source[key] == row[key] if isinstance(source[key], str) else close(source[key], row[key]), f"Native readback requires matching source field {key} for {source['handle']:X}")
                if name == "SWR_SPACE":
                    if source.get("explicit_floor_meshes"):
                        require(bool(row["flags"] & 8), "Profiled floors require virtual planar floor support")
                    require(source.get("native_code", source["identifier"]) == row["identifier"] and source["name"] == row["name"], "Native room calculation codes and names require lossless readback")
                    if row["category"] == 0:
                        require((1000, source["identifier"]) in row["xdata"], "Native room source identifiers require persistent extended data")
                    require(len(source["holes_mm"]) == len(row["holes_mm"]), "Native inner rings require complete property storage")
                elif name == "SWR_FLOOR_FRAME":
                    require(row["label"] == str(source["floor_number"]), "Native floor labels require the declared frame sequence")
                elif name in {"SWR_WALL", "SWR_OPENING", "SWR_SLAB"}:
                    require((1000, source["identifier"]) in row["xdata"], "Native entity source identifiers require persistent extended data")
                    if name == "SWR_WALL":
                        require(row["catalog"] == source.get("catalog", 2) and row["material"] == source.get("material", 40) and row["base_mode"] == source.get("base_mode", int(bool(source.get("virtual_plan")))), "Native wall catalogs, material and base modes require independent source-matched readback")
                        require(close(source.get("profile_mm", []), row["profile_mm"]), "Native wall profiles require source-matched local coordinates")
                        require(close(source.get("oblique_angle", 0.0), row["oblique_angle"]), "Native wall oblique angles require source-matched readback")
                    elif name == "SWR_OPENING" and source.get("profile_mm"):
                        block = blocks[row["block_3d"]]
                        require(block["xdata"][:2] == [(1040, 1200.0), (1040, 1200.0)], "Opening outline blocks require native design dimensions")
                        boundary = dict(block["xdata"]).get(1005)
                        require(boundary in polylines, "Opening outline blocks require a persistent boundary handle")
                        profile = polylines[boundary]
                        require(profile["closed"] and profile["owner"] == row["block_3d"] and any(close(profile["normal"], (0.0, direction, 0.0)) for direction in (-1.0, 1.0)), "Native opening outlines require a closed block-owned XZ plane curve")
                        require(close(opening_boundary_profile(row, profile), source["profile_mm"]), "Native opening boundary curves require orientation-matched source-shaped profiles")
                    elif name == "SWR_SLAB":
                        require(row["face_usage"] == source.get("face_usage") and row["board_type"] == source.get("board_type", 0), "Native surface usage and boundary categories require independent source-matched readback")
                        require(row["object_description"] == source.get("object_description", "") and close(row["thickness_mm"], source.get("thickness_mm", 0.0)), "Native surface descriptions and material thickness require source-matched readback")
    result = {"status": "offline_readback_passed", "scope": "directory, section and object CRCs; class definitions; exact native field/handle streams; source identifiers; room polygons and inner-ring properties; floor series; reciprocal wall/room/opening references", "format": result["version"], "objects": len(objects), "object_map_pages": result["map_pages"], "references_resolved": reference_count, "class_counts": dict(counts), "rooms": len(rooms), "native_inner_rings": inner_count, "native_skylights": len(skylights), "floor_series": {format(identity, "X"): row["series"] for identity, row in decoded.items() if row["type"] == "SWR_FLOOR_FRAME" and row["series"]}, "room_area_m2": sum(row["area_m2"] for row in rooms.values()), "rooms_with_wall_references": sum(bool(row["walls"]) for row in rooms.values()), "wall_endpoint_links": sum(bool(value) for row in walls.values() for value in row["neighbors"]), "wall_side_room_links": sum(bool(value) for row in walls.values() for value in (row["left_space"], row["right_space"])), "host_status": "pending"}
    result["native_roof_meshes"] = len(roof_meshes)
    result["surface_orientation"] = {"status": "passed", "checked_surfaces": len(slabs) + (len(roof_meshes) if expected else 0), "checked_inner_rings": sum(len(row["holes_mm"]) for row in slabs.values())}
    if expected and mesh_frames:
        result["physical_floor_frame"] = {"status": "isolated_from_roof", "story": mesh_frames[0]["story"], "meshes": len(owners)}
    elif expected and floor_meshes and all(s.get("placement") == "occupied_room_frame" for s in floor_meshes):
        result["physical_floor_frame"] = {"status": "in_source_room_storey", "meshes": len(owners)}
    sky_definitions = [row for row in polylines.values() if row["layer"] == "建-门窗-天窗" and "_LOUVER_LBL_" in row["application_xdata"] and row["closed"]]
    surface_sources = {row["xdata"][0][1] for row in skylights.values() if row["xdata"]}
    result["native_skylight_definitions"] = len(sky_definitions)
    result["native_skylights"] += sum(bool(tags) and tags[0][1] not in surface_sources for row in sky_definitions
                                      for tags in [row["application_xdata"].get("HB_BESI")])
    plan_reviews = [{"handle": format(identity, "X"), "category": row["category"], "layer": row["layer"]}
                    for identity, row in decoded.items() if row["type"] == "SWR_SPACE"
                    and not (row["layer"] == "建-房间" and row["layer_visible"] and row["flags"] & 0x400
                             if row["category"] == 0 else row["layer"] == "建-建筑区域" and not row["layer_visible"])]
    result["plan_display"] = {"passed": not plan_reviews, "visible_source_room_outlines": sum(row["layer_visible"] and bool(row["flags"] & 0x400) for row in rooms.values()),
                              "calculation_regions": counts["SWR_SPACE"] - len(rooms), "reviews": plan_reviews}
    if expected and expected.get("source_energy"):
        energy = expected["source_energy"]
        require(energy["project_root"] in prop_objects, "Source energy mappings require a serialized native project root")
        for binding in energy["entity_bindings"]:
            entity = decoded.get(binding["handle"]) or polyfaces.get(binding["handle"]) or polylines[binding["handle"]]
            record = entity["property_records"].get(binding["property"], [])
            value = next((value for code, value in record if code == (302 if binding["property"] == "THSWARE_STRUCTLIB_XREC" else 301)), None)
            require(value == str(binding["construction_id"]), "Source constructions require exact native entity bindings")
        result["source_energy"] = {"entity_bindings": len(energy["entity_bindings"]), "project_root_present": True}
    if include_geometry:
        result["geometry"] = {"entities": decoded, "blocks": blocks, "polylines": polylines, "lines": lines, "polyfaces": polyfaces, "properties": prop_objects, "dictionaries": dictionaries}
    return result


def compare_building_outlines(manifest, entities, plans):
    floors = {row["story"]: row for row in manifest["floors"]}
    grouped = defaultdict(list)
    for row in manifest["building_outlines"]:
        grouped[row["story"]].append(row)
    records = []
    precision = manifest["building_outline_precision_mm"]
    for story in sorted(set(floors) | set(grouped)):
        floor = floors.get(story)
        if floor and floor.get("role") == "physical_floors" and not grouped[story] and not plans.get(story):
            continue
        stories = [story]
        if floor and floor.get("role") == "envelope":
            stories = [row["story"] for row in floors.values()
                       if row.get("role", "occupied") == "occupied" and row["floor_number"] == floor["floor_number"] - 1]
        source = unary_union([shape for name in stories for shape in plans.get(name, [])])
        source_boundary = unary_union([set_precision(shape, precision) for name in stories for shape in plans.get(name, [])])
        parts = []
        valid = bool(floor) and bool(grouped[story])
        handles = []
        regions = []
        seeds = []
        for row in grouped[story]:
            native = entities[row["handle"]]
            handles.append(row["handle"])
            offset = floor["offset_mm"] if floor else (0, 0)
            shape = Polygon([(x - offset[0], y - offset[1]) for x, y in native["outline_mm"]],
                            [[(x - offset[0], y - offset[1]) for x, y in ring] for ring in native["holes_mm"]])
            supported = shape.is_valid and shape.area > 0 and not shape.interiors
            seed = native["position_mm"]
            point = Point(seed[0] - offset[0], seed[1] - offset[1])
            strict_seed = supported and shape.contains(point)
            convex_extra = shape.convex_hull.difference(shape).area if supported else float("inf")
            convex_boundary_distance = shape.boundary.hausdorff_distance(shape.convex_hull.boundary) if supported else float("inf")
            convex_boundary_limit = max(1e-7, max(ulp(value) for value in shape.bounds) * 4)
            convex = supported and convex_extra <= max(1e-6, shape.area * 1e-12) and convex_boundary_distance <= convex_boundary_limit
            outside = shape.difference(source).area if supported else float("inf")
            region_limit = max(1.0, shape.length * precision / sqrt(2))
            fields = supported and native["category"] == 1 and signed_ring_area(native["outline_mm"]) > 0
            fields = fields and strict_seed and all(abs(area * 1e6 - shape.area) <= max(1e-6, shape.area * 1e-10)
                                                     for area in (native["area_m2"], *native["statistics"][:2]))
            valid = valid and fields and outside <= region_limit
            regions.append({"identifier": row["identifier"], "handle": row["handle"],
                            "area_m2": shape.area / 1e6, "extra_area_m2": outside / 1e6,
                            "convex_hull_extra_area_m2": convex_extra / 1e6,
                            "convex_boundary_distance_mm": convex_boundary_distance,
                            "convex": convex, "seed_strictly_inside": strict_seed,
                            "seed_boundary_clearance_mm": shape.boundary.distance(point) if supported else 0.0,
                            "fields_valid": fields, "source_coverage_passed": outside <= region_limit})
            seeds.append(point)
            if supported:
                parts.append(shape)
        actual = unary_union(parts)
        overlap = max(0.0, sum(part.area for part in parts) - actual.area)
        difference = source.symmetric_difference(actual).area
        area_limit = max(1.0, source.length * precision / sqrt(2))
        for region, point in zip(regions, seeds):
            region["seed_region_count"] = sum(part.covers(point) for part in parts)
            region["passed"] = bool(region["fields_valid"] and region["source_coverage_passed"] and region["convex"] and region["seed_region_count"] == 1)
        uniqueness = len(handles) == len(set(handles)) and overlap <= max(1.0, source.area * 1e-10) and all(region["seed_region_count"] == 1 for region in regions)
        matched = bool(source.area > 0 and valid and difference <= area_limit)
        actual_boundary = unary_union([set_precision(part, precision) for part in parts])
        boundary_distance = source_boundary.boundary.hausdorff_distance(actual_boundary.boundary) if source_boundary.area > 0 and actual_boundary.area > 0 else float("inf")
        boundary_limit = precision * (1 + sqrt(2))
        boundary_matched = boundary_distance <= boundary_limit + 1e-6
        convex = bool(regions) and all(region["convex"] for region in regions)
        records.append({"story": story, "source_stories": stories, "native_regions": len(handles),
                        "source_area_m2": source.area / 1e6, "native_union_area_m2": actual.area / 1e6,
                        "symmetric_difference_m2": difference / 1e6, "area_tolerance_m2": area_limit / 1e6,
                         "overlap_area_m2": overlap / 1e6, "regions_valid": bool(valid), "coverage_passed": matched,
                         "uniqueness_passed": uniqueness,
                         "boundary_hausdorff_mm": boundary_distance, "boundary_tolerance_mm": boundary_limit,
                         "boundary_passed": boundary_matched, "native_fill_passed": convex, "regions": regions,
                         "internal_seam_length_mm": max(0.0, (sum(part.length for part in parts) - actual.length) / 2),
                         "passed": matched and uniqueness and boundary_matched and convex})
    return {"scope": "SDK room-plan unions versus independently decoded convex category-1 native regions, concavity and courtyard boundaries, strict interior seeds, winding and pairwise exclusion",
            "precision_mm": precision, "area_tolerance_basis": "source_perimeter_times_grid_rounding_distance",
            "native_fill_policy": "convex faces with source-exact concavities and courtyards retained by the region union",
            "passed": bool(records) and all(row["passed"] for row in records), "records": records}


def compare_source(model, manifest, readback):
    geometry = readback["geometry"]
    entities = geometry["entities"]
    floors = {floor["story"]: floor for floor in manifest["floors"]}
    floors[manifest["roof_layout"]["story"]] = manifest["roof_layout"]
    primary = [row for row in manifest["floors"] if not row.get("series")]
    ground = entities[manifest["ground_frame"]["handle"]]["height_mm"]
    bases = {story: ground + sum(entities[row["frame_handle"]]["height_mm"] for row in primary if row["floor_number"] < floor["floor_number"]) for story, floor in floors.items()}
    if manifest.get("site_layout"):
        site = manifest["site_layout"]
        floors[site["story"]] = site
        bases[site["story"]] = 0.0
    scale = hb.unit_scale(model.units)
    clearance_walls = physical_walls(manifest, entities, bases)
    clearance_cache = {}

    def absolute(points, story):
        floor = floors[story]
        return [(point[0] - floor["offset_mm"][0], point[1] - floor["offset_mm"][1], point[2] + bases[story]) for point in points]

    rooms = {row["identifier"]: row for row in manifest["rooms"]}
    virtual_floor_faces = {entry["identifier"] for entry in manifest.get("boundary_conditions", {}).get("faces", []) if any(binding["representation"] in {"native_room_virtual_floor", "native_adjacent_virtual_floor"} for binding in entry["native"])}
    walls = defaultdict(list)
    for row in manifest["walls"]:
        if row.get("virtual_plan"):
            continue
        native = entities[row["handle"]]
        points = wall_points(native)
        candidate = (absolute(points, row["story"]), [])
        for handle in {native["left_space"], native["right_space"]} - {0}:
            walls[handle].append(candidate)
    surfaces = defaultdict(list)
    bound_roofs = set()
    native_openings = defaultdict(list)
    for row in manifest["surfaces"]:
        native = entities[row["handle"]]
        candidates = [(absolute(ring, row["story"]), [absolute(hole, row["story"]) for hole in holes])
                      for ring, holes in surface_polygons(native)]
        if row["kind"] == "Wall" and native["type"] == "POLYLINE_PFACE":
            candidates = [(absolute(mesh_outer_boundary(native), row["story"]), [])]
        if row["kind"] in {"Wall", "WallWindow", "WallDoor"}:
            walls[rooms[row["source_room"]]["handle"]].extend(candidates)
            if row["kind"] in {"WallWindow", "WallDoor"}:
                native_openings[row["identifier"]].extend(candidates)
        elif row["kind"] == "Skylight":
            native_openings[row["identifier"]].extend(candidates)
            surfaces[row["host_identifier"]].extend(candidates)
            if native["type"] == "POLYLINE_PFACE":
                bound_roofs.add(row["host_identifier"])
        else:
            surfaces[row["identifier"]].extend(candidates)
            if native["type"] == "POLYLINE_PFACE" and row["kind"] == "RoofCeiling":
                bound_roofs.add(row["identifier"])
    mesh_areas = Counter()
    for row in manifest.get("defined_skylights", []):
        if not row["thermal_surface_handles"]:
            poly = geometry["polylines"][row["handle"]]
            points = absolute(wcs_points(dict(poly, outline_mm=poly["points"])), row["story"])
            if row.get("projected_to_plan"):
                host = next(s for s in manifest["surfaces"] if s["kind"] == "RoofCeiling" and s["identifier"] == row["host_identifier"])
                native = entities[host["handle"]]
                x0, y0, z0 = absolute(wcs_points(native), host["story"])[0]
                nx, ny, nz = native["normal"]
                points = [(x, y, z0 - ((x - x0) * nx + (y - y0) * ny) / nz) for x, y, z in points]
            native_openings[row["identifier"]].append((points, []))
    mesh_normals = defaultdict(list)
    for row in manifest.get("floor_meshes", []):
        for triangle in geometry["polyfaces"][row["handle"]]["triangles_mm"]:
            points = absolute(triangle, row["story"])
            surface = Face3D(tuple(Point3D(*p) for p in points))
            mesh_areas[row["identifier"]] += surface.area
            mesh_normals[row["identifier"]].append(surface.normal)
            surfaces[row["identifier"]].append((points, []))
    for row in manifest["openings"]:
        native = entities[row["handle"]]
        block = geometry["blocks"][native["block_3d"]]
        tags = dict(block["xdata"])
        profile = geometry["polylines"].get(tags.get(1005))
        if profile is None:
            continue
        host = entities[native["wall"]]
        contour = opening_boundary_profile(native, profile)
        points = opening_points(native, host, contour) if host["type"] == "SWR_WALL" else [(native["position_mm"][0] + u * native["width_mm"] / 1200 * cos(native["angle_rad"]), native["position_mm"][1] + u * native["width_mm"] / 1200 * sin(native["angle_rad"]), native["position_mm"][2] + v * native["height_mm"] / 1200) for u, v in contour]
        for identifier in row["source_identifiers"]:
            native_openings[identifier].append((absolute(points, row["story"]), []))
    room_records, face_records, opening_records, wall_records = [], [], [], []
    plans = defaultdict(list)
    for room in model.rooms:
        row = rooms[room.identifier]
        native = entities[row["handle"]]
        boundaries = hb.room_plan_boundaries(room)
        expected = unary_union([Polygon([(point.x * scale, point.y * scale) for point in boundary.boundary], [[(point.x * scale, point.y * scale) for point in hole] for hole in boundary.holes or ()]) for boundary in boundaries])
        plans[row["story"]].append(expected)
        actual = Polygon([(x - floors[row["story"]]["offset_mm"][0], y - floors[row["story"]]["offset_mm"][1]) for x, y in native["outline_mm"]], [[(x - floors[row["story"]]["offset_mm"][0], y - floors[row["story"]]["offset_mm"][1]) for x, y in hole] for hole in native["holes_mm"]])
        metric = area_metrics(expected, actual, 1e-6)
        metric["boundary_hausdorff_mm"] = expected.boundary.hausdorff_distance(actual.boundary)
        elevation = native["position_mm"][2] + bases[row["story"]]
        metric.update(identifier=room.identifier, source_elevation_mm=hb.room_floor_elevation(room) * scale, native_elevation_mm=elevation, source_floor_area_m2=hb.room_floor_area(room) * (scale / 1000) ** 2, plan_boundary_basis=row.get("plan_boundary_basis", "source_floor"))
        metric["passed"] = metric["passed"] and metric["boundary_hausdorff_mm"] <= 1.0 and abs(elevation - metric["source_elevation_mm"]) <= 1.0 and abs(native["height_mm"] - hb.room_height(room) * scale) <= 1.0
        room_records.append(metric)
        source_walls = [_Surface(face.identifier, "Wall", face.geometry.scale(scale)) for face in room.faces if str(face.type) == "Wall" or str(face.type) == "AirBoundary" and abs(face.normal.z) <= 1e-4]
        observed_walls = [_Surface(f"native:{index}", "Wall", Face3D(tuple(Point3D(*point) for point in boundary))) for index, (boundary, holes) in enumerate(walls[row["handle"]])]
        comparison = _compare(source_walls, observed_walls, 0.05, 1.0)
        wall_records.append({"identifier": room.identifier, **comparison})
        for face in room.faces:
            kind = str(face.type)
            record = {"identifier": face.identifier, "source_room": room.identifier, "kind": kind, "source_boundary": source_boundary(face)}
            if kind == "Wall" or kind == "AirBoundary" and abs(face.normal.z) <= 1e-4:
                record.update(coverage(face.geometry, walls[row["handle"]], scale, tolerance=1e-8 if abs(face.normal.z) > 1e-4 else 0.05, check_extra=False))
            elif kind in {"Floor", "RoofCeiling"} and face.identifier in surfaces:
                record.update(coverage(face.geometry, surfaces[face.identifier], scale,
                                       tolerance=1e-8 if face.identifier in mesh_areas or face.identifier in bound_roofs else 0.05))
                if face.identifier in bound_roofs:
                    parts = [Face3D(tuple(Point3D(*p) for p in ring)) for ring, _ in surfaces[face.identifier]]
                    total = sum(part.area for part in parts) / 1e6
                    excess = max(0.0, total - record["native_area_m2"])
                    record.update(mesh_sum_area_m2=total, mesh_overlap_area_m2=excess,
                                  outward_mesh_faces=all(p.normal.dot(face.normal) > 0.9999 for p in parts))
                    record["passed"] = (record["passed"] and not record.get("rejected_parts", 0) and record["outward_mesh_faces"]
                                        and excess <= max(1e-6, record["source_area_m2"] * 1e-8))
                if face.identifier in mesh_areas:
                    native_area = mesh_areas[face.identifier]
                    source_area = face.area * scale ** 2
                    record["native_triangle_area_m2"] = native_area / 1e6
                    record["outward_triangles"] = all(normal.dot(face.normal) > 0.9999 for normal in mesh_normals[face.identifier])
                    record["passed"] = record["passed"] and record["outward_triangles"] and abs(native_area - source_area) <= max(1.0, source_area * 1e-8)
            elif kind in {"Floor", "RoofCeiling"}:
                if kind == "Floor" and row.get("explicit_floor_meshes"):
                    record.update(status="explicit_floor_mesh_required", passed=False)
                else:
                    record.update(status="host_assembly_required", passed=None)
            elif kind == "AirBoundary" and face.identifier in virtual_floor_faces:
                record.update(status="native_virtual_floor_written_host_pending", passed=None)
            else:
                record.update(status="native_air_boundary_adaptation_required", passed=False)
            face_records.append(record)
            for item in (*face.apertures, *face.doors):
                raw = coverage(item.geometry, native_openings[item.identifier], scale, tolerance=1e-8)
                source_shape_passed = raw["passed"]
                if (kind == "Wall" or abs(item.normal.z) < 1e-4) and manifest.get("opening_clearance"):
                    effective = effective_source_shape(item, manifest, clearance_walls, clearance_cache)
                    approved = coverage(item.geometry, native_openings[item.identifier], scale, tolerance=1e-8, expected_shape=effective)
                    raw.update(raw_source_coverage_passed=raw["passed"], passed=approved["passed"], effective_area_m2=effective.area / 1e6, effective_missing_area_m2=approved["missing_area_m2"], effective_extra_area_m2=approved["extra_area_m2"], clearance_trimmed_area_m2=raw["source_area_m2"] - effective.area / 1e6, adaptation_policy="native_wall_volume_clearance")
                raw.update(source_shape_passed=source_shape_passed,
                           source_shape_status="source_shape_preserved" if source_shape_passed else "clearance_adapted" if raw["passed"] else "source_shape_review",
                           source_shape_relative_difference=max(raw["missing_area_m2"], raw["extra_area_m2"]) / raw["source_area_m2"] if raw["source_area_m2"] > 0 else 0.0)
                opening_records.append({"identifier": item.identifier, "source_room": room.identifier, "host_identifier": face.identifier,
                                        "source_boundary": source_boundary(item), **raw})
    outlines = compare_building_outlines(manifest, entities, plans)
    references = compare_references(model, manifest, geometry["lines"], floors, bases)
    shades = compare_shade_meshes(model, manifest, geometry.get("polyfaces", {}), bases)
    boundaries = compare_boundary_conditions(model, manifest, entities)
    failures = [record for record in (*room_records, *face_records, *opening_records, *wall_records) if record["passed"] is False]
    failures.extend(record for record in outlines["records"] if not record["passed"])
    failures.extend(record for record in references["records"] if not record["passed"])
    if not references["complete"]:
        failures.append({"status": "source_reference_coverage_required"})
    failures.extend(record for record in shades["records"] if not record["passed"])
    if not shades["complete"]:
        failures.append({"status": "source_shade_coverage_required"})
    failures.extend(record for record in boundaries["records"] if not record["passed"])
    if not boundaries["complete"]:
        failures.append({"status": "source_boundary_coverage_required"})
    summary = {"rooms": len(room_records), "passed_room_plans": sum(row["passed"] for row in room_records), "passed_room_wall_unions": sum(row["passed"] for row in wall_records), "faces": len(face_records), "explicit_native_faces_passed": sum(row["passed"] is True for row in face_records), "host_derived_faces_pending": sum(row["passed"] is None for row in face_records), "native_face_review": sum(row["passed"] is False for row in face_records), "source_openings": len(opening_records), "passed_openings": sum(row["passed"] for row in opening_records), "review_openings": sum(not row["passed"] for row in opening_records), "source_references": references["source_count"], "passed_source_references": sum(row["passed"] for row in references["records"]), "source_reference_coverage_complete": references["complete"], "source_shades": shades["source_objects"], "passed_shades": sum(row["passed"] for row in shades["records"]), "native_shading": "offline_geometry_compared_host_pending" if shades["source_objects"] and shades["passed"] else "source_geometry_review_required" if shades["source_objects"] else "no_source_shading_objects", "source_special_boundaries": len(boundaries["records"]), "passed_special_boundaries": sum(row["passed"] for row in boundaries["records"]), "review_items": len(failures)}
    summary.update(building_outline_frames=len(outlines["records"]), passed_building_outline_frames=sum(row["passed"] for row in outlines["records"]),
                   passed_source_opening_shapes=sum(row["source_shape_passed"] for row in opening_records),
                   adapted_source_opening_shapes=sum(row["source_shape_status"] == "clearance_adapted" for row in opening_records),
                   source_opening_trimmed_area_m2=sum(max(0.0, row.get("clearance_trimmed_area_m2", 0.0)) for row in opening_records))
    return {"schema": "offline_dwg_source_coverage_v1", "status": "source_geometry_review_required" if failures else "explicit_geometry_compared_host_pending", "scope": "SDK source geometry versus independently decoded DWG room polygons, building regions, world placement, gross wall profiles, explicit roof panels, opening block boundaries, shading meshes, source-reference lines and native boundary metadata", "absolute_tolerance_mm": 1.0, "relative_area_tolerance": 0.05, "source_opening_shape_relative_tolerance": 1e-8, "host_validation": "pending", "summary": summary, "room_plans": room_records, "room_wall_unions": wall_records, "building_outlines": outlines, "faces": face_records, "openings": opening_records, "source_references": references, "shading": shades, "boundary_conditions": boundaries}


def compare_references(model, manifest, lines, floors, bases):
    components = {item.identifier: (item, "Shade") for item in model.shades}
    components.update((item.identifier, (item, "ShadeMesh")) for item in model.shade_meshes)
    components.update((face.identifier, (face, str(face.type))) for room in model.rooms for face in room.faces if str(face.type) == "AirBoundary" or str(face.type) == "Wall" and abs(face.normal.z) > 1e-4)
    records = []
    scale = hb.unit_scale(model.units)
    for record in manifest.get("source_references", []):
        identifier = record["identifier"]
        if identifier not in components:
            records.append({"identifier": identifier, "passed": False, "status": "source_identity_review_required"})
            continue
        item, kind = components[identifier]
        geometry = item.geometry
        rings = [geometry.boundary, *(geometry.holes or ())] if kind != "ShadeMesh" else [tuple(geometry.vertices[index] for index in face) for face in geometry.faces]
        edges = [(tuple(value * scale for value in start), tuple(value * scale for value in end)) for ring in rings for start, end in zip(ring, (*ring[1:], ring[0]))]
        floor = floors[record["story"]]
        passed = len(edges) == len(record["handles"])
        for index, (handle, (start, end)) in enumerate(zip(record["handles"], edges)):
            line = lines.get(handle, {})
            for key, expected in (("start_mm", start), ("end_mm", end)):
                point = line.get(key)
                actual = (point[0] - floor["offset_mm"][0], point[1] - floor["offset_mm"][1], point[2] + bases[record["story"]]) if point else ()
                passed = passed and close(actual, expected, 0.01)
            passed = passed and all(tag in line.get("xdata", []) for tag in ((1000, identifier), (1000, kind), (1000, "SourceReference"), (1071, index)))
        records.append({"identifier": identifier, "kind": kind, "edges": len(edges), "passed": passed, "native_status": record.get("native_status", "adaptation_required")})
    counts = Counter(record["identifier"] for record in records)
    return {"source_count": len(components), "complete": set(counts) == set(components) and all(count == 1 for count in counts.values()), "records": records}


def wall_shape(row, start=None, direction=None):
    first, last = row["start_mm"], row["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
    origin = first if start is None else start
    vx, vy = (ux, uy) if direction is None else direction
    points = wall_points(row)
    polygon = Polygon([((x - origin[0]) * vx + (y - origin[1]) * vy, z) for x, y, z in points])
    if not polygon.is_valid:
        decoded = polygon.buffer(0)
        if decoded.is_valid and abs(decoded.area - polygon.area) <= max(1.0, polygon.area * 1e-9):
            return decoded
    return polygon


def inspect_quality(manifest, readback):
    geometry = readback["geometry"]
    entities = geometry["entities"]
    floors = {row["story"]: row for row in manifest["floors"]}
    primary = [row for row in manifest["floors"] if not row.get("series")]
    ground = entities[manifest["ground_frame"]["handle"]]["height_mm"]
    bases = {story: ground + sum(entities[row["frame_handle"]]["height_mm"] for row in primary if row["floor_number"] < floor["floor_number"]) for story, floor in floors.items()}
    walls = physical_walls(manifest, entities, bases)
    repeated_sides = [{"code": "same_room_on_both_wall_sides", "wall": row["handle"], "room": entities[row["handle"]]["left_space"]}
                      for row in manifest["walls"] if entities[row["handle"]]["left_space"] and
                      entities[row["handle"]]["left_space"] == entities[row["handle"]]["right_space"]]
    issues = list(repeated_sides)
    bindings = []
    projection_reviews = []
    for source in manifest["openings"]:
        native = entities[source["handle"]]
        host = walls.get(native["wall"])
        if host is None:
            surface = entities.get(native["wall"], {}).get("type") == "SWR_SLAB"
            bindings.append({"handle": source["handle"], "wall": native["wall"], "scope": "surface_host_identity_only", "passed": surface})
            if not surface:
                issues.append({"code": "native_opening_host_required", "handle": source["handle"], "host": native["wall"]})
            continue
        start, end = host["start_mm"], host["end_mm"]
        length = hypot(end[0] - start[0], end[1] - start[1])
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        floor = floors[source["story"]]
        x, y, z = native["position_mm"]
        x, y, z = x - floor["offset_mm"][0], y - floor["offset_mm"][1], z + bases[source["story"]]
        perpendicular = abs((x - start[0]) * uy - (y - start[1]) * ux)
        alignment = abs(cos(native["angle_rad"]) * uy - sin(native["angle_rad"]) * ux)
        block = geometry["blocks"][native["block_3d"]]
        boundary = geometry["polylines"].get(dict(block["xdata"]).get(1005))
        profile = opening_boundary_profile(native, boundary) if boundary else []
        points = opening_points({**native, "position_mm": (x, y, z)}, host, profile)
        shape = Polygon([((a - start[0]) * ux + (b - start[1]) * uy, c) for a, b, c in points])
        outside = shape.difference(wall_shape(host)).area / cos(host.get("oblique_angle", 0.0)) if shape.is_valid and points else float("inf")
        reciprocal = source["handle"] in entities[native["wall"]]["openings"]
        passed = perpendicular <= 0.5 and alignment <= 1e-7 and outside <= 1.0 and shape.is_valid and shape.area > 0 and reciprocal
        vector = tuple(b - a for a, b in zip(start, end))
        ratio = sum((value - base) * delta for value, base, delta in zip((x, y, z), start, vector)) / sum(delta ** 2 for delta in vector)
        projection_shift = hypot(start[0] + ratio * vector[0] - x, start[1] + ratio * vector[1] - y)
        bindings.append({"handle": source["handle"], "wall": native["wall"], "axis_distance_mm": perpendicular, "axis_alignment_error": alignment, "outside_host_area_m2": outside / 1e6, "reciprocal": reciprocal, "native_base_projection_shift_mm": projection_shift, "passed": passed})
        if projection_shift > 0.001:
            issue = {"code": "native_opening_base_projection_shift", "handle": source["handle"], "wall": native["wall"], "shift_mm": projection_shift}
            projection_reviews.append(issue)
            issues.append(issue)
        if not passed:
            issues.append({"code": "native_opening_attachment_geometry_required", **bindings[-1]})
    pairs = []
    values = list(walls.values())
    for index, first in enumerate(values):
        a, b = first["start_mm"], first["end_mm"]
        length = hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        shape = wall_shape(first)
        for other in values[index + 1:]:
            c, d = other["start_mm"], other["end_mm"]
            distance = hypot(d[0] - c[0], d[1] - c[1])
            direction = (ux * (d[0] - c[0]) + uy * (d[1] - c[1])) / distance
            slope = -tan(first.get("oblique_angle", 0.0))
            other_slope = -tan(other.get("oblique_angle", 0.0)) * direction
            if abs(ux * (d[1] - c[1]) / distance - uy * (d[0] - c[0]) / distance) > 1e-7 or abs(slope - other_slope) > 1e-7 or max(abs(-(point[0] - a[0]) * uy + (point[1] - a[1]) * ux - slope * (point[2] - a[2])) * cos(first.get("oblique_angle", 0.0)) for point in wall_points(other)) > 0.01:
                continue
            overlap = shape.intersection(wall_shape(other, a, (ux, uy))).area / cos(first.get("oblique_angle", 0.0))
            if overlap > 1.0:
                issue = {"code": "collinear_native_wall_overlap", "first": first["handle"], "second": other["handle"], "first_story": first["story"], "second_story": other["story"], "scope": "same_storey" if first["story"] == other["story"] else "cross_storey", "overlap_area_m2": overlap / 1e6}
                pairs.append(issue)
                issues.append(issue)
    plan_pairs = plan_wall_conflicts([{**source, **entities[source["handle"]]} for source in manifest["walls"]])
    issues.extend({"code": "native_plan_wall_axis_conflict", **pair} for pair in plan_pairs)
    profiles = {row["handle"] for row in manifest["walls"] if entities[row["handle"]].get("profile_mm")}
    oblique = {row["handle"] for row in manifest["walls"] if abs(entities[row["handle"]].get("oblique_angle", 0.0)) > 1e-8}
    corners = [{"handle": row["handle"], "neighbor": neighbor} for row in manifest["walls"] for neighbor in entities[row["handle"]]["neighbors"] if neighbor and (row["handle"] in profiles and neighbor in oblique or row["handle"] in oblique and neighbor in profiles)]
    bounds = []
    for handle in profiles:
        row = entities[handle]
        length = sum((a - b) ** 2 for a, b in zip(row["start_mm"], row["end_mm"])) ** 0.5
        if any(x < -0.001 or x > length + 0.001 for x, z in row["profile_mm"]):
            bounds.append({"handle": handle, "baseline_length_mm": length})
    issues.extend({"code": "native_profile_corner_dependency", **row} for row in corners)
    issues.extend({"code": "native_profile_baseline_bounds", **row} for row in bounds)
    return {"scope": "Independently decoded native opening support, reciprocal wall references, physical wall spans, projected CAD wall axes and explicit top-profile compatibility", "status": "offline_structural_checks_passed" if not issues else "offline_structural_review_required", "passed": not issues, "opening_bindings_passed": all(row["passed"] for row in bindings) and len(bindings) == len(manifest["openings"]), "opening_base_projection_passed": not projection_reviews, "same_storey_wall_uniqueness_passed": all(row["scope"] == "cross_storey" for row in pairs), "cross_storey_wall_uniqueness_passed": all(row["scope"] == "same_storey" for row in pairs), "native_plan_wall_uniqueness_passed": not plan_pairs, "native_profile_corner_independence_passed": not corners, "native_profile_baseline_bounds_passed": not bounds, "opening_bindings": bindings, "opening_base_projection_reviews": projection_reviews, "overlapping_wall_spans": pairs, "projected_wall_axis_conflicts": plan_pairs, "profile_corner_dependencies": corners, "profile_baseline_reviews": bounds, "issues": issues, "besi_ZQJC": "dedicated_host_pending", "besi_CDJC": "dedicated_host_pending"}


def compare_host_bindings(manifest, report):
    observed = {row["handle"].upper(): row for row in report.get("opening_bindings", [])}
    records = []
    for source in manifest["openings"]:
        row = observed.get(format(source["handle"], "X"), {})
        passed = row.get("host_handle", "").upper() == format(source["wall"], "X") and row.get("host_class") in {"SWR_WALL", "SWR_SLAB"}
        if row.get("host_class") == "SWR_WALL":
            passed = passed and row.get("reciprocal") is True and row.get("wall_thickness_mm", 0) > 0
        records.append({"handle": source["handle"], "wall": source["wall"], "passed": bool(passed)})
    return {"scope": "Live native TDbOpening wall IDs, TDbWall opening lists and resolved wall thickness", "passed": report.get("status") == "completed" and report.get("identity_passed", True) is True and all(row["passed"] for row in records), "records": records}


def inspect_skylight_properties(model, manifest, readback):
    from .skylights import THERMAL_LAYER, inspect_definitions

    sources = {item.identifier: item for room in model.rooms for face in room.faces if str(face.type) == "RoofCeiling" for item in face.apertures}
    rooms = {row["identifier"]: row["native_code"] for row in manifest["rooms"]}
    entities = readback["geometry"]["entities"]
    constructions = {row["id"]: row for row in manifest.get("source_energy", {}).get("constructions", [])}
    frames = {row["story"]: row for row in (*manifest["floors"], manifest["roof_layout"])}
    roof_shapes = {}
    roof_bindings = {}
    auxiliary = {handle for d in manifest.get("defined_skylights", []) for handle in d["thermal_surface_handles"]}
    records = []
    def projected(native, frame, plane):
        def project(ring):
            return [tuple(plane.xyz_to_xy(Point3D(p[0] - frame["offset_mm"][0], p[1] - frame["offset_mm"][1],
                                                  p[2] + frame["reference_elevation_mm"]))) for p in ring]
        return [Polygon(project(ring), [project(hole) for hole in holes]) for ring, holes in surface_polygons(native)]
    for row in manifest.get("surfaces", []):
        if row["kind"] != "Skylight":
            continue
        native = entities[row["handle"]]
        source = sources.get(row["identifier"])
        values = native.get("property_records", {}).get("THSWARE_STRUCTLIB_XREC", [])
        identity = next((int(value) for code, value in values if code == 302), None)
        construction = constructions.get(identity, {})
        overlap = 0.0
        host_bound = True
        if source is not None:
            plane = source.parent.geometry.scale(hb.unit_scale(model.units)).plane
            if source.parent.identifier not in roof_shapes:
                shapes = []
                bindings = []
                for roof in manifest.get("surfaces", []):
                    if roof["kind"] != "RoofCeiling" or roof["identifier"] != source.parent.identifier:
                        continue
                    frame = frames[roof["story"]]
                    bindings.append(entities[roof["handle"]]["source_room"] == rooms.get(row["source_room"]))
                    shapes.extend(projected(entities[roof["handle"]], frame, plane))
                roof_shapes[source.parent.identifier] = unary_union(shapes)
                roof_bindings[source.parent.identifier] = all(bindings)
            host_bound = roof_bindings[source.parent.identifier]
            frame = frames[row["story"]]
            shape = unary_union(projected(native, frame, plane))
            overlap = shape.intersection(roof_shapes[source.parent.identifier]).area
        mesh = native["type"] == "POLYLINE_PFACE"
        checks = {"native_usage": native["face_usage"] == 2 and native["board_type"] == 3,
                  "definition_display": row["handle"] not in auxiliary or native["layer"] == THERMAL_LAYER and not native["layer_visible"],
                  "source_room": native["source_room"] == rooms.get(row["source_room"]), "source_construction": identity == row.get("construction_id") and construction.get("category") == "天窗",
                  "source_name": source is not None and (1000, source.display_name or source.identifier) in native["application_xdata"].get("HB_BESI", []),
                  "native_compact_label": native["application_xdata"].get("_ARCH_SLAB_TEXT") == [(1000, "天窗")],
                  "source_thickness": source is not None and (mesh or close(native["thickness_mm"], 0.0)) and close(row.get("source_thickness_mm", -1.0), hb.face_thickness_m(source) * 1000), "opaque_host_cutout": overlap <= 1.0, "opaque_host_room_binding": host_bound}
        if not mesh:
            checks["native_description"] = native["object_description"] == "天窗"
        records.append({"handle": row["handle"], "identifier": row["identifier"], "opaque_roof_overlap_m2": overlap / 1e6, "checks": checks, "passed": all(checks.values())})
    definitions = inspect_definitions(model, manifest, readback)
    standalone = {r["identifier"] for r in manifest.get("defined_skylights", []) if not r["thermal_surface_handles"]}
    mesh_glazing = inspect_mesh_glazing(model, manifest, readback)
    return {"scope": "defined_closed_skylight_geometry_number_glazing_and_room_bound_thermal_surfaces", "records": records,
            "definitions": definitions, "mesh_glazing": mesh_glazing,
            "passed": definitions["passed"] and mesh_glazing["passed"] and ({row["identifier"] for row in records} | standalone) == set(sources)
            and all(row["passed"] for row in records)}


def inspect_mesh_glazing(model, manifest, readback):
    meshes = readback["geometry"]["polyfaces"]
    rooms = {row["identifier"]: readback["geometry"]["entities"][row["handle"]]["identifier"] for row in manifest["rooms"]}
    frames = {row["story"]: row for row in (*manifest["floors"], manifest["roof_layout"])}
    scale = hb.unit_scale(model.units)
    sources = {item.identifier: item for room in model.rooms for face in room.faces for item in face.apertures}
    glass = {p["values"]["ID"]: p["values"] for p in readback["geometry"]["properties"].values() if "WinSHGC" in p["values"]}
    energy = manifest["source_energy"]
    grouped = defaultdict(list)
    opaque = defaultdict(list)
    for row in manifest["surfaces"]:
        if row.get("native_class") != "POLYLINE_PFACE":
            continue
        if row["face_usage"] == 2:
            grouped[row["identifier"]].append(row)
        else:
            opaque[row["identifier"]].append(row)
    def world(row):
        frame = frames[row["story"]]
        return [[(x-frame["offset_mm"][0], y-frame["offset_mm"][1], z+frame["reference_elevation_mm"]) for x, y, z in ring]
                for ring in meshes.get(row["handle"], {}).get("polygons_mm", ())]
    combined = {s for row in manifest["openings"] for s in row["source_identifiers"]}
    hosts = {}
    records = []
    for identifier, rows in grouped.items():
        item = sources.get(identifier)
        if item is None:
            records.append({"identifier": identifier, "passed": False})
            continue
        face = item.parent
        plane = face.geometry.scale(scale).plane
        code = rooms[face.parent.identifier]
        if face.identifier not in hosts:
            hosts[face.identifier] = unary_union([Polygon([tuple(plane.xyz_to_xy(Point3D(*p))) for p in ring])
                                                  for row in opaque[face.identifier] for ring in world(row)])
        thermal = hb.thermal_properties(item)
        required = (("WimK", thermal.u_factor(model.units)), ("WinSHGC", thermal.shgc(model.units)),
                    ("Trans", item.properties.energy.construction.visible_transmittance))
        rings = []
        matched = True
        for row in rows:
            mesh = meshes.get(row["handle"], {})
            identity = energy["role_assignments"].get(row["native_carrier_category"], {}).get(identifier) if row.get("native_carrier_category") else energy["assignments"].get(identifier)
            props = mesh.get("property_records", {})
            matched = (matched and row["host_identifier"] == face.identifier and row["source_room"] == face.parent.identifier
                       and mesh.get("application_xdata", {}).get("HB_BESI", [])[:4] == [(1000, identifier), (1000, row["kind"]), (1000, face.parent.identifier), (1000, face.identifier)]
                       and mesh.get("application_xdata", {}).get("BECS_FACE_USAGE") == [(1071, 2)]
                       and props.get("BECS_ROOF_SPACE_CODE") == [(280, 1), (301, code)] and props.get("BECS_ROOF_BORDTYPE") == [(280, 1), (301, "3")]
                       and identity in glass and props.get("THSWARE_STRUCTLIB_XREC") == [(301, ""), (302, str(identity))]
                       and all(key in glass[identity] and close(glass[identity][key], value, 1e-8) for key, value in required))
            rings.extend(world(row))
        shape = unary_union([Polygon([tuple(plane.xyz_to_xy(Point3D(*p))) for p in ring]) for ring in rings])
        metric = coverage(item.geometry, [(ring, []) for ring in rings], scale, tolerance=1e-8)
        parts = [Face3D(tuple(Point3D(*p) for p in ring)) for ring in rings]
        overlap = shape.intersection(hosts[face.identifier]).area
        duplicate = max(0.0, sum(p.area for p in parts) - shape.area)
        partial = identifier in combined
        limit = max(1.0, item.area * scale**2 * 1e-8)
        records.append({"identifier": identifier, "source_room": face.parent.identifier, "host_identifier": face.identifier,
                        "kind": rows[0]["kind"], "mixed_with_native_openings": partial, **metric, "source_thermal_and_owner": bool(matched),
                        "duplicate_area_m2": duplicate / 1e6, "opaque_overlap_m2": overlap / 1e6,
                        "passed": bool(matched and parts and all(p.normal.dot(item.normal) > 0.9999 for p in parts) and not metric.get("rejected_parts", 0)
                                       and (metric["passed"] or partial and metric["extra_area_m2"] * 1e6 <= limit)
                                       and duplicate <= limit and overlap <= limit)})
    return {"passed": all(row["passed"] for row in records), "records": records}


def validate(model, data, report):
    """Read back native bytes and attach source, quality and unit validations."""
    from .orientation import orientation_model
    if "face_orientation" in report:
        model, orientation = orientation_model(model)
        require(all(orientation[k] == report["face_orientation"].get(k) for k in ("counts", "reclassified", "vertical_tolerance_degrees")),
                "Face roles require the SDK source orientation and boundary evidence")
    readback = inspect_native(data, report, include_geometry=True)
    report["source_geometry_validation"] = compare_source(model, report, readback)
    report["native_quality"] = inspect_quality(report, readback)
    report["native_skylight_properties"] = inspect_skylight_properties(model, report, readback)
    report["validation"] = {key: value for key, value in readback.items() if key != "geometry"}
    report["unit_cross_check"] = check_absolute_units(model, report)
    return report["validation"]


def check_absolute_units(model, report):
    """Cross-check native dimensions against SDK unit conversion in absolute units."""
    from honeybee.units import conversion_factor_to_meters
    millimeters_per_unit = conversion_factor_to_meters(model.units) * 1000.0
    floors = {row["story"]: row for row in report.get("floors", [])}
    rooms = {room.identifier: room for room in model.rooms}
    room_checks = []
    skipped = []
    for row in report.get("rooms", []):
        room = rooms.get(row["identifier"])
        if room is None:
            room_checks.append({"identifier": row["identifier"], "passed": False, "reason": "source_room_missing"})
            continue
        boundaries = hb.room_plan_boundaries(room)
        if len(boundaries) != 1:
            skipped.append({"identifier": room.identifier, "reason": "multi_region_room"})
            continue
        expected_area = sum(float(boundary.area) for boundary in boundaries) * (millimeters_per_unit / 1000.0) ** 2
        expected_source_area = float(room.floor_area) * (millimeters_per_unit / 1000.0) ** 2
        expected_height = (max(face.geometry.max.z for face in room.faces) - min(face.geometry.min.z for face in room.faces)) * millimeters_per_unit
        expected_elevation = min(boundary.min.z for boundary in boundaries) * millimeters_per_unit
        floor = floors.get(row["story"], {})
        native_elevation = row["position_mm"][2] + floor.get("reference_elevation_mm", 0.0)
        checks = {
            "native_area": abs(row["area_m2"] - expected_area) <= max(1e-4, expected_area * 1e-5),
            "source_area": abs(row["source_area_m2"] - expected_source_area) <= max(1e-4, expected_source_area * 1e-5),
            "native_height": abs(row["height_mm"] - expected_height) <= 1.0,
            "native_elevation": abs(native_elevation - expected_elevation) <= 1.0,
        }
        room_checks.append({"identifier": room.identifier, "passed": all(checks.values()), "checks": checks, "native_area_m2": row["area_m2"], "expected_area_m2": expected_area, "native_source_area_m2": row["source_area_m2"], "expected_source_area_m2": expected_source_area, "native_height_mm": row["height_mm"], "expected_height_mm": expected_height, "native_elevation_mm": native_elevation, "expected_elevation_mm": expected_elevation})
    face_rooms = {face.identifier: (face, room) for room in model.rooms for face in room.faces}
    wall_groups = defaultdict(list)
    for row in report.get("walls", []):
        wall_groups[row["identifier"]].append(row)
    wall_checks = []
    for identifier, rows in wall_groups.items():
        source = face_rooms.get(identifier)
        if source is None:
            skipped.append({"identifier": identifier, "reason": "non_horizontal_or_missing_face"})
            continue
        source_face, room = source
        if abs(source_face.normal.z) > 1e-4:
            skipped.append({"identifier": identifier, "reason": "non_horizontal_or_missing_face"})
            continue
        if any(row.get("profile_status") != "horizontal_section" for row in rows):
            skipped.append({"identifier": identifier, "reason": "non_horizontal_section_rows"})
            continue
        if len(rows) != 1:
            skipped.append({"identifier": identifier, "reason": "split_native_wall"})
            continue
        source_height = (source_face.geometry.max.z - source_face.geometry.min.z) * millimeters_per_unit
        room_height = (max(face.geometry.max.z for face in room.faces) - min(face.geometry.min.z for face in room.faces)) * millimeters_per_unit
        if abs(source_height - room_height) > 1.0:
            skipped.append({"identifier": identifier, "reason": "partial_source_wall"})
            continue
        passed = abs(rows[0]["height_mm"] - source_height) <= 1.0
        wall_checks.append({"identifier": identifier, "passed": passed, "native_height_mm": rows[0]["height_mm"], "expected_height_mm": source_height})
    passed = bool(room_checks) and all(row["passed"] for row in room_checks) and all(row["passed"] for row in wall_checks)
    return {"schema": "gbas_absolute_units_v1", "status": "passed" if passed else "unit_review_required", "passed": passed, "units": model.units, "millimeters_per_unit": millimeters_per_unit, "rooms": room_checks, "walls": wall_checks, "skipped": skipped}


class ExportValidationError(ValueError):
    def __init__(self, report):
        self.report = report
        failed = [key for key, passed in report["self_check"]["checks"].items() if not passed]
        super().__init__("Native export requires resolved preimport checks: " + ", ".join(failed))


def inspect_export(report):
    """Return the preimport gate result for a completed export report."""
    geometry = report["source_geometry_validation"]
    summary = geometry["summary"]
    quality = report["native_quality"]
    surfaces = report.get("surfaces", [])
    walls = report.get("walls", [])
    energy = report.get("source_energy", {})
    source_identifiers = set(energy.get("source_identifiers", []))
    excluded = {row["identifier"] for row in energy.get("excluded", [])}
    assigned = set(energy.get("assignments", {}))
    thermal = (
        energy.get("schema") == "gbas_source_energy_v1"
        and not energy.get("binding_conflicts")
        and bool(source_identifiers)
        and assigned == source_identifiers - excluded
    )
    checks = {
        "native_binary_readback": report["validation"]["status"] == "offline_readback_passed",
        "native_room_outline_display": report["validation"].get("plan_display", {}).get("passed") is True,
        "source_room_plans": summary["passed_room_plans"] == summary["rooms"] == report["counts"]["rooms"],
        "source_wall_coverage": summary["passed_room_wall_unions"] == summary["rooms"],
        "source_geometry_coverage": summary["review_items"] == 0,
        "source_opening_coverage": summary["passed_openings"] == summary["source_openings"],
        "native_building_outline_regions": geometry.get("building_outlines", {}).get("passed") is True,
        "source_shade_coverage": geometry["shading"]["passed"] is True,
        "native_environment_shade_layers": all(row.get("layer") == hb.LAYER for row in report.get("shading", {}).get("records", []) if not row.get("is_indoor")),
        "source_boundary_metadata": geometry["boundary_conditions"]["passed"] is True,
        "native_opening_hosts": quality["opening_bindings_passed"] is True,
        "native_opening_base_projection": quality.get("opening_base_projection_passed") is True,
        "native_skylight_properties": report.get("native_skylight_properties", {}).get("passed") is True,
        "native_same_frame_wall_uniqueness": quality["same_storey_wall_uniqueness_passed"] is True,
        "native_distinct_wall_sides": all(issue["code"] != "same_room_on_both_wall_sides" for issue in quality["issues"]),
        "native_projected_wall_axis_uniqueness": quality.get("native_plan_wall_uniqueness_passed") is True,
        "native_profile_corner_independence": quality.get("native_profile_corner_independence_passed") is True,
        "native_profile_baseline_bounds": quality.get("native_profile_baseline_bounds_passed") is True,
        "native_wall_window_panels_zero": sum(row.get("face_usage") in (5, 6) for row in surfaces) == 0,
        "native_wall_heights_positive": all(row.get("height_mm", 0) > 0 for row in walls),
        "native_topology_helpers_virtual": all(row.get("catalog") == 4 and row.get("base_mode") == 0 and not row.get("openings") for row in walls if row.get("virtual_plan")),
        "source_thermal_bindings": thermal,
        "native_absolute_units": report.get("unit_cross_check", {}).get("passed") is True,
    }
    warnings = []
    if report.get("floor_meshes"):
        placement = report["validation"].get("physical_floor_frame", {}).get("status")
        checks["native_floor_mesh_placement"] = placement in {"in_source_room_storey", "isolated_from_roof"}
        unsupported = sorted({row["identifier"] for row in report["floor_meshes"] if row["boundary_condition"] != "Outdoors"})
        checks["native_profiled_floor_boundary_conditions"] = not unsupported
        if unsupported:
            warnings.append({"code": "profiled_floor_requires_native_boundary_association", "source_faces": unsupported,
                             "followup": "verify_native_ground_insulation_or_reciprocal_room_on_physical_floor"})
    required = dict(checks)
    cross_frame = [row for row in quality["overlapping_wall_spans"] if row["scope"] == "cross_storey"]
    if cross_frame:
        warnings.append({"code": "cross_frame_world_wall_coincidence", "count": len(cross_frame), "scope": "distinct_native_floor_frames", "followup": "native_assembly_and_interstorey_thermal_review"})
    adapted_openings = [row for row in geometry["openings"] if row.get("source_shape_status") == "clearance_adapted"]
    if adapted_openings:
        warnings.append({"code": "source_opening_clearance_geometry_change", "count": len(adapted_openings),
                         "trimmed_area_m2": sum(max(0.0, row.get("clearance_trimmed_area_m2", 0.0)) for row in adapted_openings),
                         "maximum_source_shape_relative_difference": max(row["source_shape_relative_difference"] for row in adapted_openings),
                         "followup": "source_shape_and_native_preview_acceptance"})
    repairs = {
        "shared_source_wall_planes": len(report.get("source_geometry_repairs", [])),
        "native_plan_wall_axes": len(report.get("native_plan_compatibility", {}).get("records", [])),
        "same_room_wall_sides": sum(bool(wall.get("wall_side_repair")) for wall in walls),
        "native_profile_corner_relations": len(report.get("native_profile_compatibility", {}).get("records", [])),
        "native_opening_baseline_origins": len(report.get("native_opening_baseline_compatibility", {}).get("records", [])),
        "source_wall_completion": len(report.get("native_wall_completion", {}).get("walls", [])),
        "coincident_same_frame_walls_merged": len(report.get("native_wall_completion", {}).get("shared_native_walls", [])),
        "elevated_native_walls": len(report.get("elevated_walls", [])),
        "opening_clearance_parts": report.get("opening_clearance", {}).get("trimmed_parts", 0),
        "short_edge_skylights_partitioned": len({row["identifier"] for row in report.get("surfaces", []) if row.get("calculation_partition") == "area_preserving_short_edge_triangles"}),
    }
    passed = all(required.values())
    return {"schema": "gbas_preimport_checks_v1", "status": "passed_with_warnings" if passed and warnings else "passed" if passed else "repair_review_required", "passed": passed, "checks": checks, "required_checks": required, "automatic_repairs": repairs, "warnings": warnings, "project_configuration": "host_test_or_user_settings", "host_geometry_verification": "required", "host_energy_verification": "required"}


def require_export(report):
    """Attach the preimport gate and raise when a required check fails."""
    report["self_check"] = inspect_export(report)
    if not report["self_check"]["passed"]:
        raise ExportValidationError(report)
