"""BESI native entity record codecs and shared record helpers."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import replace
from xml.sax.saxutils import escape

from ladybug_geometry.geometry3d import Point3D
from shapely.geometry import LineString, Polygon, box

from .binary import Drawing

LAYERS = (
    ("建-墙-砖", 7, True), ("建-房间", 3, True), ("建-门窗", 4, True),
    ("公-视口", 6, True), ("建-填充", 8, True), ("建-门窗-玻璃", 4, True),
    ("建-门窗-窗框", 7, True), ("建-墙", 7, True), ("建-门窗-编号", 2, True),
    ("HB-Source-3D", 8, False), ("HB-Labels", 2, True),
    ("建-楼板", 8, True), ("建-屋顶", 2, True), ("建-天窗", 4, True),
    ("建筑-门窗-天窗", 4, True),
    ("建-建筑区域", 3, False),
)

NATIVE_CLASSES = {
    "TDbWall": "SWR_WALL",
    "TDbOpening": "SWR_OPENING",
    "TDbSpace": "SWR_SPACE",
    "TDbFloorFrame": "SWR_FLOOR_FRAME",
    "TDbSlab": "SWR_SLAB",
}

DESIGN_SIZE_MM = 1200.0


class Filer:
    def __init__(self, writer, references):
        self.w = writer
        self.references = references

    def ref(self, handle, hard=False):
        self.references.append((5 if hard else 4, handle))

    def base(self, identifier, mode=0, description=""):
        self.w.rc(251)
        self.w.bd(100.0)
        self.w.bd(0.0)
        self.w.rc(0)
        self.w.text(description)
        self.w.text("<SRootEntity><HoneybeeSource>" + escape(identifier) + "</HoneybeeSource></SRootEntity>")
        self.w.rc(mode)

    def poly(self, points, closed=True):
        self.w.rc(int(closed))
        self.w.bs(len(points))
        for point in points:
            for coordinate in point[:2]:
                self.w.rd(coordinate)
            self.w.bd(point[2] if len(point) == 3 else 0.0)


def new_drawing():
    drawing = Drawing(LAYERS, ("_SPACE", "_WINDOW"))
    codes = {}
    for cpp, name in NATIVE_CLASSES.items():
        codes[name] = drawing.add_class(cpp, name)
    codes["SWR_PROPOBJ"] = drawing.add_class("SwrPropObj", "SWR_PROPOBJ", False, "SWR_ARCHCORE", 3071)
    drawing.add_appid("BECS_FACE_USAGE")
    return drawing, codes


def signed_area(points):
    x, y = points[0]
    return math.fsum((a[0] - x) * (b[1] - y) - (a[1] - y) * (b[0] - x) for a, b in zip(points, (*points[1:], points[0]))) / 2


def oriented(points, clockwise):
    points = [tuple(point[:2]) for point in points]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 3 or abs(signed_area(points)) < 1e-6:
        raise ValueError("Native polygons require a positive finite planar area")
    return list(reversed(points)) if (signed_area(points) > 0) == clockwise else points


def add_native(drawing, code, layer, record, encode, xdata=()):
    references = []
    def body(w):
        references.clear()
        encode(Filer(w, references), record, drawing)
    entity = drawing.add_entity(code, layer, body, references=references, metadata=record, xdata=tuple(xdata))
    record["handle"] = entity.handle
    return entity


def wall(f, row, d):
    w = f.w
    f.base(row["identifier"], row.get("base_mode", 1 if row.get("virtual_plan") else 0))
    w.rc(6)
    w.point(row["start_mm"])
    w.point(row["end_mm"])
    w.bd(0.0)
    w.bl(0x10000100 | (0x10 if row.get("profile_mm") else 0))
    w.bd(row["thickness_mm"] / 2)
    w.bd(row["thickness_mm"] / 2)
    w.bd(row["height_mm"])
    for handle in (0, 0, *row["neighbors"]):
        f.ref(handle)
    w.rc(row.get("catalog", 2))
    if row.get("profile_mm"):
        f.poly(row["profile_mm"], False)
    w.bs(len(row["openings"]))
    for handle in row["openings"]:
        f.ref(handle)
    w.rc(row.get("material", 40))
    w.rc(0)
    for _ in range(5):
        w.bd(0.0)
    for name in ("0", "0", "建-填充", "0"):
        f.ref(d.layers[name][0], True)
    f.ref(row["left_space"])
    f.ref(row["right_space"])
    w.bd(row.get("oblique_angle", 0.0))


def space(f, row, d):
    w = f.w
    f.base(row["identifier"])
    w.rc(4)
    w.point(row["position_mm"])
    w.text(row.get("native_code", row["identifier"]))
    w.text(row["name"])
    for value in (row["area_m2"], row["area_m2"], row["perimeter_mm"] * row["height_mm"] / 1e6, 0.0, 0.0, 0.0, row["height_mm"], row["perimeter_mm"]):
        w.bd(value)
    f.poly(row["outline_mm"])
    w.bs((0x400 if row.get("show_outline", row["category"] == 0) else 0) | (8 if row.get("has_floor") is False else 0))
    w.rc(row["category"])
    w.rc(0)
    w.rc(0)
    f.ref(d.styles["_SPACE"], True)
    w.bd(5.0)
    w.bd(0.0)
    w.bd(0.0)
    w.rc(len(row["walls"]))
    for handle in row["walls"]:
        f.ref(handle)


def opening(f, row, d):
    w = f.w
    f.base(row["identifier"])
    w.rc(3)
    w.point(row["position_mm"])
    for value in (row["width_mm"], 0.0, row["height_mm"], row["angle_rad"]):
        w.bd(value)
    w.rc(3 if row["kind"] == "Door" else 0)
    w.rc(row.get("native_kind", 0 if row["kind"] == "Door" else 1))
    w.bd(0.0)
    w.text(row["mark"])
    f.ref(row["block_2d"], True)
    f.ref(row["block_3d"], True)
    x, y, _ = row["position_mm"]
    w.point((x, y + 375.0, 0.0))
    f.ref(row["wall"])
    w.bl(0)
    for handle in (d.styles["_WINDOW"], d.layers["建-门窗-编号"][0], d.layers["建-门窗-玻璃"][0], d.layers["建-门窗-窗框"][0], d.layers["建-墙"][0]):
        f.ref(handle, True)
    for value in (3.5, 120.0, 40.0, 40.0):
        w.bd(value)
    w.bs(0)
    w.rc(3 if row["kind"] == "Door" else 0)


def floor_frame(f, row, d):
    w = f.w
    f.base(row["identifier"])
    w.rc(1)
    for value in (*row["center_mm"], *row["alignment_mm"]):
        w.rd(value)
    for value in (row["width_mm"], row["depth_mm"], row["height_mm"]):
        w.bd(value)
    w.text(str(row["floor_number"]))


def slab(f, row, d):
    w = f.w
    f.base(row["identifier"], description=row.get("object_description", ""))
    w.rc(3)
    w.bd(row.get("thickness_mm", 0.0))
    w.bl(0)
    w.bd(row["elevation_mm"])
    f.poly(row["outline_mm"])
    w.bs(len(row.get("holes_mm", ())))
    for hole in row.get("holes_mm", ()):
        f.poly(hole)
    w.point(row["normal"])
    w.rc(0)
    for name in ("0", "0", "建-填充"):
        f.ref(d.layers[name][0], True)


def attach_surface_properties(drawing, entity, room_identifier, usage, board_type):
    entries = {name: drawing.allocate() for name in ("BECS_ROOF_SPACE_CODE", "BECS_ROOF_BORDTYPE")}
    entity.dictionary = drawing.add_dictionary(entity.handle, entries)
    for name, value in (("BECS_ROOF_SPACE_CODE", room_identifier), ("BECS_ROOF_BORDTYPE", str(board_type))):
        drawing.add_xrecord(entries[name], entity.dictionary, [(280, 1), (301, value)])
    entity.application_xdata["BECS_FACE_USAGE"] = ((1071, usage),)


def attach_xrecords(drawing, entity, records):
    if entity.dictionary:
        owner, entries = drawing.dictionary_entries[entity.dictionary]
        entries = dict(entries)
    else:
        owner, entries = entity.handle, {}
    values = {name: entries.get(name) or drawing.allocate() for name in records}
    entries.update(values)
    if entity.dictionary:
        drawing.set_dictionary_entries(entity.dictionary, owner, entries)
    else:
        entity.dictionary = drawing.add_dictionary(owner, entries)
    identities = set(values.values())
    drawing.additional_objects = [(identity, payload) for identity, payload in drawing.additional_objects if identity not in identities]
    for name, tags in records.items():
        drawing.add_xrecord(values[name], entity.dictionary, tags)


def add_properties(drawing, code, handle, owner, properties, dictionary=0):
    references = []
    def body(w):
        w.rc(1)
        w.bs(len(properties))
        for name, typ, value in properties:
            w.rc(typ)
            w.text(name)
            if typ == 0:
                w.bl(value & 0xFFFFFFFF)
            elif typ == 1:
                w.bd(value)
            elif typ == 2:
                w.text(value)
            elif typ == 3:
                w.point(value)
            elif typ == 6:
                w.bs(len(value))
                references.extend((4, identity) for identity in value)
            else:
                raise ValueError("Native properties require a supported native type")
    drawing.add_object(code, handle, owner, body, references, dictionary)


def attach_floor_series(drawing, codes, entity, series):
    if not series:
        return
    record = drawing.allocate()
    entity.dictionary = drawing.add_dictionary(entity.handle, {"SRootEntity": record})
    add_properties(drawing, codes["SWR_PROPOBJ"], record, entity.dictionary, [("Floor_Series", 2, series)])


def attach_room_properties(drawing, codes, entity, holes):
    height_record = drawing.allocate()
    entries = {"BECS_ROOM_HEIGHT_BY_STOREY": height_record}
    inner = None
    if holes:
        entries["SwrInnerSpace"] = drawing.allocate()
        inner = {"parent": entries["SwrInnerSpace"], "children": [drawing.allocate() for _ in holes], "owner": entity.dictionary}
    entity.dictionary = drawing.add_dictionary(entity.handle, entries)
    drawing.add_xrecord(height_record, entity.dictionary, [(280, 1), (301, "0")])
    if inner:
        inner["owner"] = entity.dictionary
    return inner


def write_inner_rings(drawing, codes, inner, holes, wall_handles):
    parent = inner["parent"]
    children = {f"InnerSpc{index}": handle for index, handle in enumerate(inner["children"])}
    if "dictionary" in inner:
        dictionary = inner["dictionary"]
        drawing.additional_objects = [(handle, body) for handle, body in drawing.additional_objects if handle not in inner["children"]]
    else:
        dictionary = drawing.add_dictionary(parent, children)
        inner["dictionary"] = dictionary
        add_properties(drawing, codes["SWR_PROPOBJ"], parent, inner["owner"], [("NumSpc", 0, len(holes))], dictionary)
    for index, hole in enumerate(holes):
        points = oriented(hole, False)
        properties = [("NumPts", 0, len(points)), *[(f"P{number}", 3, (*point, 0.0)) for number, point in enumerate(points)], ("EncloseWall", 6, wall_handles[index])]
        add_properties(drawing, codes["SWR_PROPOBJ"], children[f"InnerSpc{index}"], dictionary, properties)


def connect_walls(records):
    nodes = defaultdict(list)
    for record in records:
        for endpoint, point in enumerate((record["start_mm"], record["end_mm"])):
            other = record["end_mm"] if endpoint == 0 else record["start_mm"]
            key = tuple(round(value, 2) for value in point)
            nodes[key].append((math.atan2(other[1] - point[1], other[0] - point[0]), record, endpoint))
    for group in nodes.values():
        group.sort(key=lambda item: (item[0], item[1]["handle"]))
        if len(group) < 2:
            continue
        for index, (_, record, endpoint) in enumerate(group):
            following = group[(index + 1) % len(group)][1]["handle"]
            previous = group[index - 1][1]["handle"]
            slots = (following, previous) if endpoint == 0 else (previous, following)
            record["neighbors"][endpoint * 2:endpoint * 2 + 2] = slots


def hole_wall_handles(hole, walls):
    edges = [LineString([first, last]) for first, last in zip(hole, (*hole[1:], hole[0]))]
    handles = set()
    for row in walls:
        line = LineString([row["start_mm"][:2], row["end_mm"][:2]])
        if any(line.distance(edge) <= max(100.0, row["thickness_mm"]) for edge in edges):
            handles.add(row["handle"])
    return sorted(handles)


def wall_opening_bounds(item):
    if item.host_type != "Wall" or abs(item.normal.z) > 1e-4:
        return item
    ux, uy = item.normal.y, -item.normal.x
    length = math.hypot(ux, uy)
    ux, uy = ux / length, uy / length
    origin = item.boundary[0]
    positions = [(point.x - origin.x) * ux + (point.y - origin.y) * uy for point in item.boundary]
    low, high = min(positions), max(positions)
    bottom, top = min(point.z for point in item.boundary), max(point.z for point in item.boundary)
    start = Point3D(origin.x + low * ux, origin.y + low * uy, bottom)
    end = Point3D(origin.x + high * ux, origin.y + high * uy, bottom)
    center = Point3D((start.x + end.x) / 2, (start.y + end.y) / 2, bottom)
    return replace(item, width=high - low, height=top - bottom, start=start, end=end, center=center, vertical_height=top - bottom)


def opening_profile(item, segment, scale, low=None, high=None, bottom=None, top=None, include_bounds=False):
    boundary = tuple(item.boundary)
    dx = (segment.end.x - segment.start.x) * scale
    dy = (segment.end.y - segment.start.y) * scale
    length = math.hypot(dx, dy)
    if length <= 0 or len(boundary) < 3:
        return None
    ux, uy = dx / length, dy / length
    origin_x, origin_y = segment.start.x * scale, segment.start.y * scale
    source_bottom = min(point.z for point in boundary) * scale
    along = [((point.x * scale - origin_x) * ux + (point.y * scale - origin_y) * uy) for point in boundary]
    vertical = [point.z * scale for point in boundary]
    shape = Polygon(zip(along, vertical))
    if shape.is_empty or not shape.is_valid or shape.area <= 1e-6:
        return None
    center = ((item.center.x * scale - origin_x) * ux + (item.center.y * scale - origin_y) * uy)
    if low is None:
        low = center - item.width * scale / 2
    if high is None:
        high = center + item.width * scale / 2
    bottom = source_bottom if bottom is None else bottom
    top = max(vertical) if top is None else top
    clipped = shape.intersection(box(low, bottom, high, top))
    if clipped.is_empty:
        return None
    if clipped.geom_type == "MultiPolygon":
        clipped = max(clipped.geoms, key=lambda polygon: polygon.area)
    if clipped.geom_type != "Polygon" or clipped.area <= 1e-6:
        return None
    points = list(clipped.exterior.coords)[:-1]
    low_x, high_x = min(point[0] for point in points), max(point[0] for point in points)
    low_z, high_z = min(point[1] for point in points), max(point[1] for point in points)
    if high_x - low_x <= 1e-6 or high_z - low_z <= 1e-6:
        return None
    center_x = (low_x + high_x) / 2
    profile = [
        ((point[0] - center_x) * DESIGN_SIZE_MM / (high_x - low_x),
         (point[1] - low_z) * DESIGN_SIZE_MM / (high_z - low_z))
        for point in points
    ]
    if include_bounds:
        return {"profile": profile, "low": low_x, "high": high_x, "bottom": low_z, "top": high_z}
    return profile


def opening_block(drawing, kind, profile, thickness_mm, angle_rad):
    if profile is None:
        return drawing.blocks[f"$ARCHSYS${kind}3D"][0]
    thickness = max(float(thickness_mm), 1.0)
    normal = (0.0, 1.0 if math.cos(angle_rad) >= 0 else -1.0, 0.0)
    key = hashlib.sha256(repr((kind, round(thickness, 3), normal, tuple((round(x, 3), round(z, 3)) for x, z in profile))).encode("utf-8")).hexdigest()[:12]
    name = f"$HB${kind}3D${key}"
    if name in drawing.blocks:
        return drawing.blocks[name][0]
    block = drawing.add_block(name)
    if "_TCH_BOUNDARY" not in drawing.layers:
        drawing.layers["_TCH_BOUNDARY"] = (drawing.allocate(), 7, False)
    boundary = drawing.add_polyline([(-x, z) for x, z in profile], "_TCH_BOUNDARY", owner=block, normal=normal)
    appid = drawing.add_appid("_TCH")
    drawing.block_xdata[block] = ((appid, ((1040, DESIGN_SIZE_MM), (1040, DESIGN_SIZE_MM), (1005, boundary.handle))),)
    drawing.block_metadata[name] = {"design_size_mm": DESIGN_SIZE_MM, "thickness_mm": thickness, "vertices": len(profile), "boundary_handle": boundary.handle, "outline_protocol": "_TCH_BOUNDARY"}
    half = thickness / 2
    vertices = [(x, -half, z) for x, z in profile] + [(x, half, z) for x, z in profile]
    count = len(profile)
    for index in range(count):
        following = (index + 1) % count
        drawing.add_line(vertices[index], vertices[following], owner=block)
        drawing.add_line(vertices[index + count], vertices[following + count], owner=block)
        drawing.add_line(vertices[index], vertices[index + count], owner=block)
    return block
