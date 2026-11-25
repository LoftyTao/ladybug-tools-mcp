from __future__ import annotations

from collections import defaultdict
from math import fsum, isclose

from shapely.geometry import Polygon

from .. import model as hb
from .geometry import coverage
from .records import attach_xrecords
from .surfaces import axes, dot


LAYER = "建-门窗-天窗"
LABEL = "_LOUVER_LBL_"
THERMAL_LAYER = "HB-Thermal-Skylight"


def add_defined_skylights(drawing, model, report):
    frames = {row["story"]: row for row in report["floors"]}
    rooms = {row["identifier"]: row for row in report["rooms"]}
    scale = hb.unit_scale(model.units)
    energy = report["source_energy"]
    carriers = defaultdict(list)
    for row in report["surfaces"]:
        if row["kind"] == "Skylight":
            carriers[row["identifier"]].append(row["handle"])
    definitions = []
    handles = defaultdict(list)
    for room in model.rooms:
        frame = frames[rooms[room.identifier]["story"]]
        for face in room.faces:
            if str(face.type) != "RoofCeiling":
                continue
            for item in face.apertures:
                geometry = item.geometry
                rings = (geometry.boundary,)
                if geometry.holes:
                    mesh = geometry.triangulated_mesh3d
                    rings = tuple(tuple(mesh.vertices[index] for index in triangle) for triangle in mesh.faces)
                first, second, normal = axes(tuple(geometry.normal))
                projected = abs(normal[2]) > 1e-6 and abs(normal[2] - 1) > 1e-12
                identity = energy["assignments"][item.identifier]
                number = f"TC{len(handles) + 1:03d}"
                for index, ring in enumerate(rings):
                    points = [(point.x * scale + frame["offset_mm"][0], point.y * scale + frame["offset_mm"][1],
                               point.z * scale - frame["reference_elevation_mm"]) for point in ring]
                    elevations = [dot(point, normal) for point in points]
                    elevation = fsum(elevations) / len(points)
                    if max(abs(value - elevation) for value in elevations) > 1.0:
                        raise ValueError(f"Skylight {item.identifier} requires a planar definition")
                    outline = [(p[0], p[1]) for p in points] if projected else [(dot(point, first), dot(point, second)) for point in points]
                    polygon = Polygon(outline)
                    if not polygon.is_valid or polygon.area <= 0:
                        raise ValueError(f"Skylight {item.identifier} requires a simple closed boundary")
                    if not polygon.exterior.is_ccw:
                        outline.reverse()
                    if LAYER not in drawing.layers:
                        drawing.layers[LAYER] = drawing.layers.pop("建筑-门窗-天窗")
                    drawing.add_appid(LABEL)
                    entity = drawing.add_polyline(outline, LAYER, closed=True, elevation=0.0 if projected else elevation,
                                                  normal=(0.0, 0.0, 1.0) if projected else normal)
                    entity.application_xdata[LABEL] = ((1000, number),)
                    entity.xdata = ((1000, item.identifier), (1000, "Skylight"), (1000, face.identifier), (1000, room.identifier))
                    attach_xrecords(drawing, entity, {"THSWARE_STRUCTLIB_XREC": [(301, ""), (302, str(identity))]})
                    energy["entity_bindings"].append({"handle": entity.handle, "property": "THSWARE_STRUCTLIB_XREC",
                                                      "construction_id": identity, "sources": [item.identifier]})
                    definitions.append({"handle": entity.handle, "identifier": item.identifier, "name": item.display_name,
                                        "host_identifier": face.identifier, "source_room": room.identifier, "story": frame["story"],
                                        "number": number, "part": index, "area_m2": polygon.area / (abs(normal[2]) if projected else 1) / 1e6,
                                        "projected_to_plan": projected, "construction_id": identity,
                                        "source_thickness_mm": hb.face_thickness_m(item) * 1000,
                                        "thermal_surface_handles": carriers[item.identifier]})
                    handles[item.identifier].append(entity.handle)
    for row in report.get("skylights", []):
        if row["identifier"] in handles:
            row["definition_handles"] = handles[row["identifier"]]
    fallback = {h for row in definitions for h in row["thermal_surface_handles"]}
    if fallback:
        drawing.layers[THERMAL_LAYER] = (drawing.allocate(), 4, False)
        for entity in drawing.entities:
            if entity.handle in fallback:
                entity.layer = THERMAL_LAYER
        report["display_policy"]["hidden_reference_layers"].append(THERMAL_LAYER)
    for row in definitions:
        if not row["thermal_surface_handles"]:
            opening = {"identifier": row["identifier"], "source_identifiers": [row["identifier"]], "kind": "Skylight",
                       "host_identifier": row["host_identifier"], "part": row["part"], "area_m2": row["area_m2"],
                       "representation": "defined_closed_polyline", "definition_handle": row["handle"], "definition_handles": handles[row["identifier"]]}
            report["skylights"].append(opening)
            report["roof_openings"].append(opening)
    report["reference_openings"] = [r for r in report["reference_openings"] if r["identifier"] not in handles]
    report["defined_skylights"] = definitions
    report["counts"]["native_skylight_definitions"] = len(definitions)
    report["counts"]["native_skylights"] = len(report["skylights"])
    report["counts"]["reference_openings"] = len(report["reference_openings"])
    return definitions


def inspect_definitions(model, manifest, readback):
    from .surfaces import wcs_points

    sources = {item.identifier: (item, face, room) for room in model.rooms for face in room.faces
               if str(face.type) == "RoofCeiling" for item in face.apertures}
    frames = {row["story"]: row for row in manifest["floors"]}
    room_stories = {row["identifier"]: row["story"] for row in manifest["rooms"]}
    energy = manifest["source_energy"]
    constructions = {row["id"]: row for row in energy["constructions"]}
    glazing = {row["values"]["ID"]: row["values"] for row in readback["geometry"]["properties"].values()
               if "WinSHGC" in row["values"]}
    polys = readback["geometry"]["polylines"]
    declared = manifest.get("defined_skylights", ())
    handles = {row["handle"] for row in declared}
    found = {handle for handle, row in polys.items() if row.get("layer") == LAYER or LABEL in row.get("application_xdata", {})}
    geometries = defaultdict(list)
    part_areas = defaultdict(float)
    scale = hb.unit_scale(model.units)
    records = []
    for row in declared:
        identifier = row["identifier"]
        source = sources.get(identifier)
        poly = polys.get(row["handle"], {})
        frame = frames.get(row["story"])
        if source is None or not poly or frame is None:
            records.append({"handle": row["handle"], "identifier": identifier, "passed": False})
            continue
        item, face, room = source
        apps = poly.get("application_xdata", {})
        tags = apps.get("HB_BESI", ())
        identity = energy["assignments"].get(identifier)
        shape = Polygon(poly["points"]) if len(poly["points"]) >= 3 else Polygon()
        normal = tuple(item.geometry.normal)
        projected = abs(normal[2]) > 1e-6 and abs(normal[2] - 1) > 1e-12
        if shape.is_valid and shape.area > 0:
            points = wcs_points(dict(poly, outline_mm=poly["points"]))
            world = [(x - frame["offset_mm"][0], y - frame["offset_mm"][1], z + frame["reference_elevation_mm"]) for x, y, z in points]
            if projected:
                x0, y0, z0 = tuple(item.geometry.boundary[0].scale(scale))
                world = [(x, y, z0 - ((x - x0) * normal[0] + (y - y0) * normal[1]) / normal[2]) for x, y, _ in world]
            geometries[identifier].append((world, []))
        part_areas[identifier] += shape.area / (abs(normal[2]) if projected else 1)
        thermal = hb.thermal_properties(item)
        glass = glazing.get(identity, {})
        checks = {
            "defined_closed_polyline": poly["closed"] and bool(poly.get("layer_visible")) and poly.get("layer") == LAYER
                                       and shape.is_valid and shape.area > 0,
            "number": bool(row["number"]) and apps.get(LABEL) == [(1000, row["number"])],
            "source": row["host_identifier"] == face.identifier and row["source_room"] == room.identifier
                      and row["story"] == room_stories[room.identifier]
                      and list(tags) == [(1000, identifier), (1000, "Skylight"), (1000, face.identifier), (1000, room.identifier)],
            "source_normal": (dot(poly["normal"], (0, 0, 1) if projected else normal) >= 1 - 1e-10
                              and (not projected or abs(poly["elevation_mm"]) <= 1e-7)),
            "construction": identity is not None and identity == row["construction_id"] and constructions.get(identity, {}).get("category") == "天窗"
                            and poly.get("property_records", {}).get("THSWARE_STRUCTLIB_XREC") == [(301, ""), (302, str(identity))],
            "source_glazing": all(key in glass and isclose(glass[key], value, abs_tol=1e-8) for key, value in
                                  (("WimK", thermal.u_factor(model.units)), ("WinSHGC", thermal.shgc(model.units)),
                                   ("Trans", item.properties.energy.construction.visible_transmittance))),
        }
        records.append({"handle": row["handle"], "identifier": identifier, "checks": checks, "passed": all(checks.values())})
    geometry = []
    for identifier, (item, _, _) in sources.items():
        candidates = geometries[identifier]
        result = coverage(item.geometry, candidates, scale, tolerance=1e-8)
        delta = abs(part_areas[identifier] - item.area * scale**2)
        geometry.append({"identifier": identifier, **result, "sum_area_difference_mm2": delta,
                         "passed": result["passed"] and result.get("rejected_parts", 0) == 0 and delta <= max(1.0, item.area * scale**2 * 1e-8)})
    return {"protocol": "LJ_DYTC", "layer": LAYER, "number_app": LABEL, "source_count": len(sources), "records": records,
            "geometry": geometry, "unexpected_handles": sorted(found - handles), "missing_handles": sorted(handles - found),
            "passed": len(handles) == len(declared) and found == handles and all(row["passed"] for row in (*records, *geometry))}
