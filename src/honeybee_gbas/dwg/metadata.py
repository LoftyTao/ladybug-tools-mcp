"""Source reference, boundary condition and thermal property metadata."""

from __future__ import annotations

from collections import Counter

from honeybee.facetype import face_types
from honeybee.model import Model
from ladybug_geometry.geometry3d import Face3D, Plane, Vector3D

from .. import energy, model as hb
from ..model import source_room_codes
from .records import add_properties, attach_xrecords


def add_source_references(drawing, model, report):
    scale = hb.unit_scale(model.units)
    floors = {row["story"]: row for row in report["floors"]}
    room_floors = {row["identifier"]: floors[row["story"]] for row in report["rooms"]}
    records = []
    native_shades = {row["identifier"] for row in report.get("shading", {}).get("records", [])}
    components = [(shade, "Shade", room_floors[hb.owner_room(shade).identifier] if hb.owner_room(shade) is not None else report["site_layout"]) for shade in model.shades]
    components.extend((mesh, "ShadeMesh", report["site_layout"]) for mesh in model.shade_meshes)
    for room in model.rooms:
        floor = room_floors[room.identifier]
        components.extend((face, str(face.type), floor) for face in room.faces if str(face.type) == "AirBoundary" or str(face.type) == "Wall" and abs(face.normal.z) > 1e-4)
    points = []
    for component, kind, floor in components:
        geometry = component.geometry
        boundaries = [geometry.boundary, *(geometry.holes or ())] if kind != "ShadeMesh" else [tuple(geometry.vertices[index] for index in face) for face in geometry.faces]
        rings = [[(point.x * scale + floor["offset_mm"][0], point.y * scale + floor["offset_mm"][1], point.z * scale - floor["reference_elevation_mm"]) for point in boundary] for boundary in boundaries]
        handles = []
        for ring in rings:
            for start, end in zip(ring, (*ring[1:], ring[0])):
                entity = drawing.add_line(start, end, "HB-Source-3D")
                entity.xdata = ((1000, component.identifier), (1000, kind), (1000, "SourceReference"), (1071, len(handles)))
                handles.append(entity.handle)
            points.extend(ring)
        records.append({"identifier": component.identifier, "kind": kind, "story": floor["story"], "source_area_m2": float(geometry.area) * (scale / 1000) ** 2, "is_indoor": bool(getattr(component, "is_indoor", False)), "boundaries_mm": rings, "handles": handles, "status": "source_reference_written", "native_status": "native_polyface_written" if component.identifier in native_shades else "adaptation_required"})
    if points:
        low, high = drawing.extents
        drawing.extents = (tuple(min(low[axis], *(point[axis] for point in points)) for axis in range(3)), tuple(max(high[axis], *(point[axis] for point in points)) for axis in range(3)))
    report["source_references"] = records
    report["shading"].update(reference_shades=sum(row["kind"] == "Shade" for row in records), reference_shade_meshes=sum(row["kind"] == "ShadeMesh" for row in records), reference_layer="HB-Source-3D")
    return records


def boundary_kind(face):
    if str(face.type) == "AirBoundary":
        return "AirBoundary"
    return str(face.boundary_condition)


def source_boundary(item):
    condition = item.boundary_condition
    objects = tuple(getattr(condition, "boundary_condition_objects", ()))
    details = condition.to_dict(full=True) if str(condition) == "Outdoors" else condition.to_dict()
    return {**details, "air_boundary": str(getattr(item, "type", "")) == "AirBoundary",
            "adjacent_room": objects[-1] if objects else None}


def planar_shared_walls(model):
    scale = hb.unit_scale(model.units)
    faces = {face.identifier: face for room in model.rooms for face in room.faces}
    planned = {}
    repairs = []
    visited = set()
    for face in faces.values():
        adjacent = getattr(face.boundary_condition, "boundary_condition_objects", ())
        other = faces.get(adjacent[0]) if adjacent else None
        reverse = getattr(other.boundary_condition, "boundary_condition_objects", ()) if other else ()
        if face.identifier in visited or other is None or not reverse or reverse[0] != face.identifier:
            continue
        pair = face, other
        visited.update(item.identifier for item in pair)
        if any(str(item.type) != "Wall" or str(item.boundary_condition) != "Surface" or abs(item.normal.z) > 1e-4 for item in pair):
            continue
        deviations = {item.identifier: max(item.geometry.plane.distance_to_point(point) * scale for point in item.geometry.boundary) for item in pair}
        if max(deviations.values()) <= 0.001 or not face.geometry.is_geometrically_equivalent(other.geometry, 1.0 / scale):
            continue
        anchor = min(pair, key=lambda item: (deviations[item.identifier], abs(item.normal.z), item.identifier))
        plane = Plane(n=Vector3D(anchor.normal.x, anchor.normal.y, 0), o=anchor.geometry.plane.o)
        components = [component for item in pair for component in (item, *item.apertures, *item.doors)]
        distances = {item.identifier: max(plane.distance_to_point(point) * scale for ring in (item.geometry.boundary, *(item.geometry.holes or ())) for point in ring) for item in components}
        if max(distances.values()) > 1.0:
            continue
        for item in components:
            def ring(points):
                return tuple(plane.xy_to_xyz(plane.xyz_to_xy(point)) for point in points)
            geometry = Face3D(ring(item.geometry.boundary), holes=tuple(ring(hole) for hole in item.geometry.holes or ()) or None)
            planned[item.identifier] = geometry.to_dict()
        canonical = Face3D.from_dict(planned[anchor.identifier])
        for item in pair:
            geometry = canonical if item.normal.dot(canonical.normal) > 0 else canonical.flip()
            maximum = max(min(point.distance_to_point(candidate) for candidate in geometry.boundary) * scale for point in item.geometry.boundary)
            if maximum > 1.0:
                raise ValueError("Shared wall canonical boundaries require bounded source vertex correspondence")
            planned[item.identifier] = geometry.to_dict()
            distances[item.identifier] = maximum
        repairs.append({"source_faces": [item.identifier for item in pair], "anchor_face": anchor.identifier,
                        "source_plane_deviation_mm": deviations, "maximum_displacement_mm": distances,
                        "method": "reciprocal_near_vertical_shared_wall_plane_projection", "displacement_limit_mm": 1.0})
    if not planned:
        return model, repairs
    data = model.to_dict()
    for room in data["rooms"]:
        for face in room["faces"]:
            for item in (face, *face.get("apertures", []), *face.get("doors", [])):
                if item["identifier"] in planned:
                    item["geometry"] = planned[item["identifier"]]
    data["tolerance"] = 0
    working = Model.from_dict(data)
    working.tolerance = model.tolerance
    return working, repairs


def geometry_model(model, repairs=None):
    semantics = {face.identifier: boundary_kind(face) if boundary_kind(face) in {"Adiabatic", "AirBoundary"} else "Physical" for room in model.rooms for face in room.faces}
    working = model.duplicate()
    for room in working.rooms:
        for face in room.faces:
            if str(face.type) == "AirBoundary" and abs(face.normal.z) <= 1e-4:
                face.type = face_types.wall
    working, changes = planar_shared_walls(working)
    if repairs is not None:
        repairs.extend(changes)
    return working, semantics


def apply_boundary_conditions(drawing, model, report):
    faces = {face.identifier: face for room in model.rooms for face in room.faces}
    entities = {entity.handle: entity for entity in drawing.entities}
    mapped = {identifier: [] for identifier in faces}
    issues = []
    for row in report["walls"]:
        if row.get("virtual_plan"):
            continue
        identifiers = row.get("source_identifiers") or [row["identifier"]]
        source_ids = set(identifier for identifier in identifiers if identifier in faces)
        for identifier in tuple(source_ids):
            adjacent = getattr(faces[identifier].boundary_condition, "boundary_condition_objects", ())
            if adjacent and adjacent[0] in faces:
                source_ids.add(adjacent[0])
        source = [faces[identifier] for identifier in sorted(source_ids)]
        kinds = {boundary_kind(face) for face in source}
        if kinds.intersection({"Adiabatic", "AirBoundary"}) and len(kinds) > 1:
            issues.append({"code": "wall_boundary_partition_required", "handle": row["handle"], "source_faces": identifiers, "boundary_kinds": sorted(kinds)})
            continue
        kind = next(iter(kinds), "Unassigned")
        row["boundary_condition"] = kind
        row["catalog"] = 4 if kind == "AirBoundary" else 1 if kind in {"Surface", "Adiabatic"} else 2
        if kind == "Ground":
            row["border_type"] = 4
            attach_xrecords(drawing, entities[row["handle"]], {"THSWRAE_WALL_XREC": [(301, value) for value in ("4", "-1", "0.000000", "1", "0.000000")]})
        if kind == "Adiabatic":
            row["border_type"] = 6
            attach_xrecords(drawing, entities[row["handle"]], {"THSWRAE_WALL_XREC": [(301, value) for value in ("6", "-1", "0.000000", "1", "0.000000")]})
        for face in source:
            mapped[face.identifier].append({"handle": row["handle"], "representation": "native_virtual_wall" if kind == "AirBoundary" else "native_insulated_wall" if kind == "Adiabatic" else "native_wall", "catalog": row["catalog"], "border_type": row.get("border_type")})
    for row in report["surfaces"]:
        identifier = row.get("source_face_identifier") or row["identifier"]
        source = faces.get(identifier)
        if source is None:
            continue
        kind = boundary_kind(source)
        row["boundary_condition"] = kind
        if kind == "Adiabatic" and row["kind"] in {"Wall", "Floor", "RoofCeiling"}:
            row["board_type"] = 1
            attach_xrecords(drawing, entities[row["handle"]], {"BECS_ROOF_BORDTYPE": [(280, 1), (301, "1")]})
            if row["kind"] == "Wall":
                attach_xrecords(drawing, entities[row["handle"]], {"THSWRAE_WALL_XREC": [(301, value) for value in ("6", "-1", "0.000000", "1", "0.000000")]})
            mapped[source.identifier].append({"handle": row["handle"], "representation": "native_insulated_surface", "board_type": 1})
        elif kind == "AirBoundary":
            issues.append({"code": "virtual_surface_protocol_pending", "identifier": source.identifier, "handle": row["handle"]})
    rooms = {row["identifier"]: row for row in report["rooms"]}
    for room in model.rooms:
        native = rooms[room.identifier]
        physical = [face for face in room.faces if str(face.type) == "Floor"]
        air = [face for face in room.faces if str(face.type) == "AirBoundary" and face.normal.z < -0.9999]
        if air and not physical:
            native["has_floor"] = False
            native["floor_boundary_condition"] = "AirBoundary"
            tags = [(301, value) for value in ("", "", "", "1", "1", "0", "", "", "0", "", "")]
            attach_xrecords(drawing, entities[native["handle"]], {"THSWARE_ROOM_XREC": tags})
            for face in air:
                mapped[face.identifier].append({"handle": native["handle"], "representation": "native_room_virtual_floor", "has_floor": False})
        elif air:
            issues.append({"code": "partial_air_floor_partition_pending", "room": room.identifier, "source_faces": [face.identifier for face in air]})
        if physical and not air and all(boundary_kind(face) == "Adiabatic" for face in physical):
            native["floor_boundary_condition"] = "Adiabatic"
            attach_xrecords(drawing, entities[native["handle"]], {"BECS_ROOM_EXT_FLOOR_INSULATE": [(280, 1), (301, "1")]})
            for face in physical:
                mapped[face.identifier].append({"handle": native["handle"], "representation": "native_room_insulated_floor", "external_floor_insulate": 1})
    scale = hb.unit_scale(model.units)
    for face in faces.values():
        if str(face.type) != "AirBoundary" or face.normal.z < 0.9999:
            continue
        adjacent = getattr(face.boundary_condition, "boundary_condition_objects", ())
        other = faces.get(adjacent[0]) if adjacent else None
        if other is None or boundary_kind(other) != "AirBoundary" or other.normal.z > -0.9999:
            continue
        native = rooms[other.parent.identifier]
        if native.get("has_floor") is False and face.geometry.is_geometrically_equivalent(other.geometry, 0.5 / scale):
            mapped[face.identifier].append({"handle": native["handle"], "representation": "native_adjacent_virtual_floor", "adjacent_source_face": other.identifier, "has_floor": False})
    records = []
    for identifier, face in faces.items():
        kind = boundary_kind(face)
        if kind not in {"Adiabatic", "AirBoundary"}:
            continue
        handles = mapped[identifier]
        status = "native_boundary_written_host_pending" if handles else "native_boundary_adaptation_required"
        if not handles:
            issues.append({"code": "source_boundary_mapping_required", "identifier": identifier, "boundary_condition": kind})
        records.append({"identifier": identifier, "source_room": face.parent.identifier, "source_type": str(face.type), "boundary_condition": kind, "normal": tuple(face.normal), "status": status, "native": handles, "air_mixing": "calculation_mapping_pending" if kind == "AirBoundary" else None})
    report["boundary_conditions"] = {"schema": "native_boundary_conditions_v1", "status": "native_boundary_review_required" if issues else "native_boundaries_written_host_pending", "source_counts": dict(Counter(row["boundary_condition"] for row in records)), "native_virtual_walls": sum(row.get("catalog") == 4 for row in report["walls"]), "native_insulated_walls": sum(row.get("border_type") == 6 for row in report["walls"]), "virtual_floor_rooms": sum(row.get("has_floor") is False for row in report["rooms"]), "faces": records, "issues": issues, "calculation_validation": "pending"}
    report["counts"].update(native_virtual_walls=report["boundary_conditions"]["native_virtual_walls"], native_insulated_walls=report["boundary_conditions"]["native_insulated_walls"], virtual_floor_rooms=report["boundary_conditions"]["virtual_floor_rooms"])


def compare_boundary_conditions(model, report, entities):
    faces = {face.identifier: face for room in model.rooms for face in room.faces if boundary_kind(face) in {"Adiabatic", "AirBoundary"}}
    records = []
    for row in report.get("boundary_conditions", {}).get("faces", []):
        source = faces.get(row["identifier"])
        passed = source is not None and boundary_kind(source) == row["boundary_condition"] and bool(row["native"])
        for binding in row["native"]:
            native = entities.get(binding["handle"], {})
            properties = native.get("property_records", {})
            representation = binding["representation"]
            if representation == "native_virtual_wall":
                valid = native.get("type") == "SWR_WALL" and native.get("catalog") == 4 and native.get("base_mode") == 0 and native.get("height_mm", 0) > 0
            elif representation == "native_insulated_wall":
                valid = properties.get("THSWRAE_WALL_XREC", []) == [(301, value) for value in ("6", "-1", "0.000000", "1", "0.000000")]
            elif representation == "native_insulated_surface":
                valid = native.get("type") in {"SWR_SLAB", "POLYLINE_PFACE"} and native.get("board_type") == 1
            elif representation in {"native_room_virtual_floor", "native_adjacent_virtual_floor"}:
                values = properties.get("THSWARE_ROOM_XREC", [])
                valid = native.get("type") == "SWR_SPACE" and bool(native.get("flags", 0) & 8) and len(values) == 11 and values[8] == (301, "0")
                if valid and representation == "native_adjacent_virtual_floor":
                    other = faces.get(binding["adjacent_source_face"])
                    adjacent = getattr(source.boundary_condition, "boundary_condition_objects", ()) if source is not None else ()
                    valid = other is not None and adjacent and adjacent[0] == other.identifier and source.geometry.is_geometrically_equivalent(other.geometry, 0.5 / hb.unit_scale(model.units))
            elif representation == "native_room_insulated_floor":
                valid = properties.get("BECS_ROOM_EXT_FLOOR_INSULATE") == [(280, 1), (301, "1")]
            else:
                valid = False
            passed = passed and valid
        records.append({"identifier": row["identifier"], "boundary_condition": row["boundary_condition"], "passed": bool(passed), "native_representations": [binding["representation"] for binding in row["native"]], "host_validation": "pending"})
    identifiers = [row["identifier"] for row in records]
    complete = len(identifiers) == len(set(identifiers)) and set(identifiers) == set(faces)
    return {"scope": "Source thermal boundary identities versus independently decoded native catalogs, base modes and exact boundary property records", "passed": complete and all(row["passed"] for row in records), "complete": complete, "records": records, "host_validation": "pending", "air_mixing": "calculation_mapping_pending"}


def compare_assembled_boundaries(model, manifest, native_report):
    assembly = native_report.get("result") or native_report.get("assembly") or {}
    code_sources = source_room_codes(manifest)
    rooms = {code_sources.get(row["code"], row["code"]): row for floor in assembly.get("floors", []) for row in floor.get("room_details", [])}
    enclosures = {str(row["handle"]).upper(): row for floor in assembly.get("floors", []) for key in ("wall_details", "floor_details") for row in floor.get(key, []) if row.get("handle")}
    room_handles = {row["handle"]: row["identifier"] for row in manifest["rooms"]}
    source_faces = {face.identifier for room in model.rooms for face in room.faces if boundary_kind(face) in {"Adiabatic", "AirBoundary"}}
    records = []

    def flags(row):
        value = row.get("flags_hex", "0")
        return int(value, 16) if isinstance(value, str) else int(value)

    for entry in manifest.get("boundary_conditions", {}).get("faces", []):
        matched = bool(entry["native"])
        for binding in entry["native"]:
            representation = binding["representation"]
            if representation in {"native_room_virtual_floor", "native_adjacent_virtual_floor", "native_room_insulated_floor"}:
                room = rooms.get(room_handles.get(binding["handle"]), {})
                if representation == "native_room_insulated_floor":
                    valid = bool(flags(room) & 0x10)
                else:
                    floors = room.get("floor_details", [])
                    valid = bool(flags(room) & 2) and bool(floors) and all(flags(floor) & 0x40 for floor in floors)
                    if valid and representation == "native_adjacent_virtual_floor":
                        lower = rooms.get(entry["source_room"], {})
                        valid = bool(set(lower.get("ceiling_object_ids", [])).intersection(room.get("floor_object_ids", [])))
            else:
                enclosure = enclosures.get(format(binding["handle"], "X"), {})
                mask = 0x40 if representation == "native_virtual_wall" else 2
                valid = bool(flags(enclosure) & mask)
            matched = matched and valid
        records.append({"identifier": entry["identifier"], "boundary_condition": entry["boundary_condition"], "passed": bool(matched), "native_representations": [row["representation"] for row in entry["native"]]})
    identifiers = [row["identifier"] for row in records]
    complete = len(identifiers) == len(set(identifiers)) and set(identifiers) == source_faces
    passed = native_report.get("status") in {"completed", "review_required"} and assembly.get("assembled") is True and complete and all(row["passed"] for row in records)
    return {"scope": "BESI assembled insulation and virtual enclosure flags, room floor flags and shared native floor object identities", "passed": bool(passed), "complete": complete, "records": records, "calculation_loads": "pending", "air_mixing": "pending"}

PROJECT_MARKER = "8A358EF8-94D1-4088-8EAB-FD7FE4D41004"


def write_node(drawing, codes, value, owner, handle=None):
    handle = drawing.allocate() if handle is None else handle
    children = value["children"]
    child_handles = {child["key"]: drawing.allocate() for child in children}
    dictionary = drawing.add_dictionary(handle, child_handles) if children else 0
    add_properties(drawing, codes["SWR_PROPOBJ"], handle, owner, value["properties"], dictionary)
    for child in children:
        write_node(drawing, codes, child, dictionary, child_handles[child["key"]])
    return handle


def add_source_constructions(drawing, codes, model, report):
    roles = {}
    surfaces = [*report.get("surfaces", []), *report.get("floor_meshes", [])]
    for row in surfaces:
        if row.get("native_carrier_category"):
            roles.setdefault(row["native_carrier_category"], set()).add(row["identifier"])
    below_datum = {face.identifier for room in model.rooms for face in room.faces
                   if str(face.type) == "Floor" and face.geometry.min.z * hb.unit_scale(model.units) < -0.001}
    for role in ("周边地面", "非周边地面"):
        roles.setdefault(role, set()).update(below_datum)
    plan = energy.plan_constructions(model, native_roles=roles)
    room_library, room_types, room_assignments = energy.plan_room_types(model)
    root = energy.node("_GBSWR_PROJECT_ENC", children=[*energy.construction_libraries(plan), room_library])
    project_root = write_node(drawing, codes, root, drawing.dictionaries[0])
    drawing.named_objects[root["key"]] = project_root
    drawing.named_objects[PROJECT_MARKER] = drawing.add_dictionary(drawing.dictionaries[0], {})
    entities = {entity.handle: entity for entity in drawing.entities}
    bindings = []
    conflicts = []

    def attach(row, identifiers, key="THSWARE_STRUCTLIB_XREC", role=None):
        assignments = plan.assignments if role is None else plan.role_assignments.get(role, {})
        ids = {assignments[identifier] for identifier in identifiers if identifier in assignments}
        if len(ids) == 1:
            identity = ids.pop()
            tags = [(301, ""), (302, str(identity))] if key == "THSWARE_STRUCTLIB_XREC" else [(280, 1), (301, str(identity))]
            attach_xrecords(drawing, entities[row["handle"]], {key: tags})
            bindings.append({"handle": row["handle"], "property": key, "construction_id": identity, "sources": list(identifiers)})
            if key == "THSWARE_STRUCTLIB_XREC":
                row["construction_id"] = identity
            else:
                row.setdefault("construction_ids", {})[key] = identity
        elif ids:
            conflicts.append({"handle": row["handle"], "property": key, "sources": list(identifiers), "construction_ids": sorted(ids)})

    for row in report["walls"]:
        if not row.get("virtual_plan"):
            attach(row, row.get("source_identifiers", [row["identifier"]]))
    for row in report["openings"]:
        attach(row, row.get("source_identifiers", [row["identifier"]]))
    for row in surfaces:
        attach(row, [row["identifier"]], role=row.get("native_carrier_category"))
    rooms = {room.identifier: room for room in model.rooms}
    for row in report["rooms"]:
        entity = entities[row["handle"]]
        owner, entries = drawing.dictionary_entries[entity.dictionary]
        entries = dict(entries)
        properties = entries.get("SRootEntity") or drawing.allocate()
        entries["SRootEntity"] = properties
        drawing.set_dictionary_entries(entity.dictionary, owner, entries)
        add_properties(drawing, codes["SWR_PROPOBJ"], properties, entity.dictionary, [("SpcUsage", 2, room_assignments[row["identifier"]])])
        row["room_type"] = room_assignments[row["identifier"]]
        floors = [face for face in rooms[row["identifier"]].faces if str(face.type) == "Floor"]
        interior = [face for face in floors if str(face.boundary_condition) not in {"Outdoors", "Ground"}]
        attach(row, [face.identifier for face in interior or floors], "BECS_ROOM_FLOOR_ID")
        for key, role in (("BECS_ROOM_NOHEATFLOOR_ID", "非控温房间楼板"), ("BECS_ROOM_UNHT_FLOOR_ID", "控温与非控温空间楼板")):
            attach(row, [face.identifier for face in interior or floors], key, role)
        for boundary, keys in (("Outdoors", (("BECS_ROOM_EX_FLOOR_ID", "挑空楼板"), ("BECS_ROOM_OVERHEAD_FLOOR_ID", "架空楼板"))),
                               ("Ground", (("BECS_ROOM_EX_GROUND_ID", "周边地面"), ("BECS_ROOM_INSIDE_GROUND_ID", "非周边地面")))):
            for key, role in keys:
                attach(row, [face.identifier for face in floors if str(face.boundary_condition) == boundary
                             or boundary == "Ground" and face.identifier in below_datum], key, role)
        classified = [face for face in floors if face.identifier in below_datum and str(face.boundary_condition) != "Ground"]
        if classified:
            row["native_ground_classification"] = {"basis": "native_below_zero_source_elevation",
                                                   "source_boundaries": {face.identifier: str(face.boundary_condition) for face in classified},
                                                   "construction_policy": "source_layers_and_resistance_in_native_ground_roles"}
        roofs = [face for face in rooms[row["identifier"]].faces if str(face.type) == "RoofCeiling"]
        exterior_roofs = [face for face in roofs if str(face.boundary_condition) == "Outdoors"]
        attach(row, [face.identifier for face in exterior_roofs or roofs if str(face.boundary_condition) != "Ground"], "BECS_ROOM_ROOF_ID")
        attach(row, [face.identifier for face in roofs if str(face.boundary_condition) == "Ground"], "BECS_ROOM_GROUNDROOF_ID", "地下室覆土顶板")
    source_identifiers = sorted({face.identifier for room in model.rooms for face in room.faces} | {item.identifier for room in model.rooms for face in room.faces for item in (*face.apertures, *face.doors)})
    report["source_energy"] = {"schema": "gbas_source_energy_v1", "source_identifiers": source_identifiers, "materials": list(plan.materials),
                               "constructions": list(plan.constructions), "assignments": plan.assignments,
                               "role_assignments": plan.role_assignments,
                               "project_root": project_root,
                               "entity_bindings": bindings, "binding_conflicts": conflicts, "excluded": list(plan.excluded),
                               "room_types": room_types, "room_assignments": room_assignments,
                               "project_configuration": "host_or_user", "native_readback": "pending"}
    return plan
