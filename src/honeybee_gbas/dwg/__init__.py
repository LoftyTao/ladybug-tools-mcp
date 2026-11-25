"""Native GBAS DWG construction, export and validation."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import replace

from ladybug_geometry.geometry3d import Point3D
from shapely import set_precision
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .. import model as hb
from ..layout import AxisConnector, _collinear, floor_section, plan_levels, plan_native_levels
from ..model import inspect_model, room_codes
from . import validation
from .geometry import convex_regions, source_opening_parts
from .metadata import add_source_constructions, add_source_references, apply_boundary_conditions, geometry_model
from .records import (
    add_native, attach_floor_series, attach_room_properties, connect_walls, floor_frame,
    hole_wall_handles, new_drawing, opening, opening_block, oriented, space, wall,
    wall_opening_bounds, write_inner_rings,
)
from .surfaces import (
    add_ceiling_surfaces, add_inclined_floor_carriers, add_roof_storey, add_shade_meshes,
    add_profiled_floors, add_surfaces, add_wall_profiles, add_wall_surfaces, close_room_boundaries, explicit_floor_selection,
    prepare_wall_surfaces, promote_inclined_enclosures, route_envelope_storeys, write_bound_roof_meshes,
)
from .walls import (
    apply_opening_clearance, complete_elevated_walls, complete_native_wall_parts,
    isolate_profile_corners, refresh_room_space_references, rehost_wall_openings, separate_plan_wall_axes, stabilize_opening_baselines,
)


def host_index(item, walls, scale, limits):
    candidates = []
    elevation = limits[item.room_identifier][0]
    low = min(point.z for point in item.boundary)
    high = max(point.z for point in item.boundary)
    tolerance = 0.5 / scale
    for index, segment in enumerate(walls):
        base, height = limits[segment.room_identifier]
        if abs(base - elevation) > tolerance or low < base - tolerance or high > base + height + tolerance:
            continue
        dx, dy = segment.end.x - segment.start.x, segment.end.y - segment.start.y
        length = math.hypot(dx, dy)
        if length <= 0:
            continue
        ux, uy = dx / length, dy / length
        px, py = item.center.x - segment.start.x, item.center.y - segment.start.y
        along = px * ux + py * uy
        perpendicular = abs(px * uy - py * ux)
        if perpendicular > max(tolerance, segment.thickness_m * 2):
            continue
        if along - item.width / 2 >= -tolerance and along + item.width / 2 <= length + tolerance:
            candidates.append((segment.face_identifier != item.host_identifier, segment.exterior != item.host_exterior, index))
    return min(candidates)[2] if candidates else None


def node_walls(segments, scale, limits):
    lines = [LineString([(item.start.x, item.start.y), (item.end.x, item.end.y)]) for item in segments]
    result = []
    for index, (segment, line) in enumerate(zip(segments, lines)):
        values = {0.0, line.length}
        for other, candidate in zip(segments, lines):
            if abs(limits[segment.room_identifier][0] - limits[other.room_identifier][0]) > 0.5 / scale:
                continue
            intersection = line.intersection(candidate)
            points = list(intersection.geoms) if intersection.geom_type == "MultiPoint" else [intersection] if intersection.geom_type == "Point" else []
            for point in points:
                distance = line.project(point)
                if 0.5 / scale < distance < line.length - 0.5 / scale:
                    values.add(distance)
        values = sorted(values)
        for low, high in zip(values, values[1:]):
            if high - low < 0.1 / scale:
                continue
            start, end = line.interpolate(low), line.interpolate(high)
            result.append(replace(segment, start=Point3D(start.x, start.y, segment.start.z), end=Point3D(end.x, end.y, segment.end.z)))
    return result


def coalesce_walls(segments, scale, limits, semantics=None):
    result = list(segments)
    while True:
        nodes = defaultdict(list)
        for index, segment in enumerate(result):
            for endpoint, point in enumerate((segment.start, segment.end)):
                key = (round(point.x * scale, 2), round(point.y * scale, 2), round(limits[segment.room_identifier][0] * scale, 2))
                nodes[key].append((index, endpoint))
        for group in nodes.values():
            if len(group) != 2 or group[0][0] == group[1][0]:
                continue
            (first_index, first_endpoint), (second_index, second_endpoint) = group
            first, second = result[first_index], result[second_index]
            if semantics and semantics.get(first.face_identifier) != semantics.get(second.face_identifier):
                continue
            if first.room_identifier != second.room_identifier or first.exterior != second.exterior or abs(first.thickness_m - second.thickness_m) > 1e-9 or first.normal.dot(second.normal) < 0.999999:
                continue
            if not _collinear(first, second, 0.01 / scale):
                continue
            shared = first.start if first_endpoint == 0 else first.end
            far_first = first.end if first_endpoint == 0 else first.start
            far_second = second.end if second_endpoint == 0 else second.start
            if (far_first.x - shared.x) * (far_second.x - shared.x) + (far_first.y - shared.y) * (far_second.y - shared.y) >= 0:
                continue
            result[first_index] = replace(first, **{"start" if first_endpoint == 0 else "end": far_second}, height=max(first.height, second.height))
            result.pop(second_index)
            break
        else:
            return result


def building_area_regions(polygon):
    return convex_regions(polygon)


def assign_wall_sides(records, rooms, polygons, segments):
    for record, segment in zip(records, segments):
        first, last = record["start_mm"], record["end_mm"]
        dx, dy = last[0] - first[0], last[1] - first[1]
        length = math.hypot(dx, dy)
        for sign, field in ((1, "left_space"), (-1, "right_space")):
            scores = []
            for row in rooms:
                if abs(row["position_mm"][2] - first[2]) > 0.5:
                    continue
                shape = polygons[row["identifier"]]
                votes = 0
                for fraction in (0.25, 0.5, 0.75):
                    distance = record["thickness_mm"] / 2 + 0.5
                    point = Point(first[0] + dx * fraction - sign * dy / length * distance, first[1] + dy * fraction + sign * dx / length * distance)
                    votes += int(shape.covers(point))
                if votes:
                    scores.append((-votes, row["identifier"], row["handle"]))
            if scores:
                record[field] = min(scores)[2]
                room = next(row for row in rooms if row["handle"] == record[field])
                if record["handle"] not in room["walls"]:
                    room["walls"].append(record["handle"])
        if record["left_space"] and record["left_space"] == record["right_space"]:
            previous = record["left_space"]
            owner = next(row for row in rooms if row["identifier"] == segment.room_identifier)
            outward_left = -dy * segment.normal.x + dx * segment.normal.y > 0
            record.update(left_space=0 if outward_left else owner["handle"], right_space=owner["handle"] if outward_left else 0,
                          wall_side_repair="source_outward_normal_resolves_same_room_votes")
            if previous != owner["handle"]:
                next(row for row in rooms if row["handle"] == previous)["walls"].remove(record["handle"])
                owner["walls"].append(record["handle"])


def add_symbols(drawing):
    for kind in ("WIN", "DOOR"):
        block = drawing.add_block(f"$ARCHSYS${kind}2D")
        if kind == "WIN":
            for offset in (-0.5, -1 / 6, 1 / 6, 0.5):
                drawing.add_line((-0.5, offset, 0.0), (0.5, offset, 0.0), owner=block)
        else:
            drawing.add_polyline(((0.45, 0.0), (0.5, 0.0), (0.5, 1.0), (0.45, 1.0)), owner=block)
            points = [(0.5 + math.cos(math.pi / 2 + math.pi / 2 * index / 16), math.sin(math.pi / 2 + math.pi / 2 * index / 16)) for index in range(17)]
            drawing.add_polyline(points, closed=False, owner=block)
        block = drawing.add_block(f"$ARCHSYS${kind}3D")
        vertices = [(-600.0, -30.0, 0.0), (600.0, -30.0, 0.0), (600.0, 30.0, 0.0), (-600.0, 30.0, 0.0), (-600.0, -30.0, 1200.0), (600.0, -30.0, 1200.0), (600.0, 30.0, 1200.0), (-600.0, 30.0, 1200.0)]
        for first, second in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            drawing.add_line(vertices[first], vertices[second], owner=block)


def remove_collinear(points, tolerance=0.01):
    values = [tuple(point[:2]) for point in points]
    if len(values) > 1 and values[0] == values[-1]:
        values.pop()
    changed = True
    while changed and len(values) > 3:
        changed = False
        result = []
        for index, point in enumerate(values):
            previous = values[index - 1]
            following = values[(index + 1) % len(values)]
            dx, dy = following[0] - previous[0], following[1] - previous[1]
            length = math.hypot(dx, dy)
            if length > 0 and abs((point[0] - previous[0]) * dy - (point[1] - previous[1]) * dx) / length <= tolerance:
                changed = True
                continue
            result.append(point)
        values = result
    return values

DESIGN_SIZE_MM = 1200.0


def build_plan(model, wall_axis="centerline", ceiling_storeys=False, floor_slabs=True, surface_mode="occupied", primary_levels=False, source_shade_layout=False, wall_semantics=None):
    """Write the base native plan and return its drawing and report."""
    drawing, codes = new_drawing()
    calculation_codes = room_codes(room.identifier for room in model.rooms)
    visible_names = hb.room_names(model)
    add_symbols(drawing)
    scale = hb.unit_scale(model.units)
    report = {"format": "gbas-native-dwg-v1", "model": model.identifier, "source_units": model.units, "drawing_units": "Millimeters", "room_seed_basis": "deterministic Shapely point_on_surface of the source floor polygon", "building_outline_precision_mm": 0.01, "floors": [], "rooms": [], "walls": [], "openings": [], "reference_openings": [], "building_outlines": [], "wall_profiles_for_review": [], "preflight": inspect_model(model), "adaptation_scope": "native horizontal-section walls, rectangular wall openings, explicit source room polygons, inner-ring properties and source reference edges", "area_basis": "Honeybee source floor polygons; CAD wall-inner-edge area remains a separate comparison", "native_codec_status": "native_binary_contract", "calculation_status": "project_properties_and_calculation_pending"}
    planner = plan_native_levels if primary_levels else plan_levels
    layouts = planner(model, include_orphan_shades=not source_shade_layout)
    ceiling_layouts = {}
    elevations = {item.identifier: item.source_elevation_mm for item in layouts}
    ceiling_cursor = max(item.frame_bounds_mm[2] for item in layouts) + 5000.0
    room_levels = {room.identifier: floor for floor in layouts for room in model.rooms if room.identifier in floor.room_identifiers}
    complex_faces = {row["identifier"] for row in report["preflight"]["issues"] if row["code"] in {"wall_profile", "wall_bottom_profile", "inclined_wall"}}
    for floor in layouts:
        source_rooms = [room for room in model.rooms if room.identifier in floor.room_identifiers]
        room_top = max(hb.room_elevation_bounds(room)[1] * scale for room in source_rooms) - floor.reference_elevation_mm
        frame_height = room_top if ceiling_storeys and room_top > 0 else floor.height_mm
        limits = {room.identifier: (hb.room_floor_elevation(room), hb.room_height(room)) for room in source_rooms}
        dx, dy = floor.offset_mm
        floor_row = {"story": floor.identifier, "source_story": floor.story, "series": floor.series, "floor_number": floor.floor_number, "source_elevation_mm": floor.source_elevation_mm, "reference_elevation_mm": floor.reference_elevation_mm, "local_elevation_mm": floor.source_elevation_mm - floor.reference_elevation_mm, "offset_mm": floor.offset_mm, "height_mm": frame_height, "source_height_mm": floor.height_mm, "role": "occupied"}
        report["floors"].append(floor_row)
        polygons = {}
        room_rows = []
        inner_records = []
        from honeybee.model import Model
        section_model = Model(model.identifier, source_rooms, units=model.units, tolerance=model.tolerance, angle_tolerance=model.angle_tolerance)
        sections = floor_section(section_model, floor.story, wall_axis, 1200.0, None, True)
        source_walls = [item for item in sections if abs(item.normal.z) <= 1e-4 and not isinstance(item, AxisConnector)]
        source_walls = [item for item in source_walls if item.room_identifier in floor.room_identifiers]
        source_walls = node_walls(source_walls, scale, limits)
        source_walls = coalesce_walls(source_walls, scale, limits, wall_semantics)
        for room in source_rooms:
            boundaries = hb.room_plan_boundaries(room)
            if len(boundaries) != 1:
                raise ValueError(f"Native DWG export requires one horizontal floor polygon per room: {room.identifier}")
            face = boundaries[0]
            exterior = [(point.x * scale + dx, point.y * scale + dy) for point in face.boundary]
            holes = [[(point.x * scale + dx, point.y * scale + dy) for point in boundary] for boundary in face.holes or ()]
            exterior = remove_collinear(exterior)
            holes = [remove_collinear(hole) for hole in holes]
            polygon = Polygon(exterior, holes)
            if polygon.is_empty or not polygon.is_valid:
                raise ValueError(f"Native DWG export requires valid source floor polygons: {room.identifier}")
            polygons[room.identifier] = polygon
            seed = polygon.representative_point()
            base, height = limits[room.identifier]
            row = {"identifier": room.identifier, "name": visible_names[room.identifier], "story": floor.identifier, "source_story": floor.story, "series": floor.series, "category": 0, "position_mm": (seed.x, seed.y, base * scale - floor.reference_elevation_mm), "area_m2": polygon.area / 1e6, "source_area_m2": hb.room_floor_area(room) * (scale / 1000) ** 2, "perimeter_mm": polygon.length, "height_mm": height * scale, "outline_mm": oriented(exterior, True), "holes_mm": holes, "walls": []}
            row["native_code"] = calculation_codes[room.identifier]
            row["show_outline"] = True
            air_floor = any(str(face.type) == "AirBoundary" and face.normal.z < -0.9999 for face in room.faces)
            row["plan_boundary_basis"] = "source_floor_and_downward_air_boundary" if air_floor and room.horizontal_floor_boundaries() else "downward_air_boundary" if air_floor else "source_floor"
            plan_area = row["area_m2"] if air_floor else row["source_area_m2"]
            entity = add_native(drawing, codes["SWR_SPACE"], "建-房间", row, space, [(1000, room.identifier), (1000, "Room"), (1010, (*row["position_mm"][:2], 0.0)), (1040, plan_area), (1000, f"height_mm={row['height_mm']:.16g}"), (1000, f"floor_elevation_mm={row['position_mm'][2]:.16g}"), *([(1000, f"energy_floor_area_m2={row['source_area_m2']:.16g}")] if air_floor else [])])
            inner = attach_room_properties(drawing, codes, entity, holes)
            if inner:
                row["inner_properties"] = inner
                inner_records.append((row, inner))
            room_rows.append(row)
            report["rooms"].append(row)
        wall_rows = []
        for index, segment in enumerate(source_walls):
            base, height = limits[segment.room_identifier]
            elevation = base * scale - floor.reference_elevation_mm
            row = {"identifier": segment.face_identifier, "story": floor.identifier, "source_story": floor.story, "section_index": index, "source_room": segment.room_identifier, "start_mm": (segment.start.x * scale + dx, segment.start.y * scale + dy, elevation), "end_mm": (segment.end.x * scale + dx, segment.end.y * scale + dy, elevation), "height_mm": height * scale, "thickness_mm": segment.thickness_m * 1000.0, "openings": [], "neighbors": [0, 0, 0, 0], "left_space": 0, "right_space": 0, "profile_status": "source_reference_and_rectangular_section" if segment.face_identifier in complex_faces else "horizontal_section"}
            add_native(drawing, codes["SWR_WALL"], "建-墙-砖", row, wall, [(1000, segment.face_identifier), (1000, "Wall")])
            wall_rows.append(row)
            report["walls"].append(row)
        connect_walls(wall_rows)
        assign_wall_sides(wall_rows, room_rows, polygons, source_walls)
        close_room_boundaries(drawing, codes, report, room_rows, wall_rows)
        connect_walls(wall_rows)
        for room_row, inner in inner_records:
            handles = [hole_wall_handles(hole, wall_rows) for hole in room_row["holes_mm"]]
            if any(not item for item in handles):
                raise ValueError(f"Native room inner rings require enclosing wall references: {room_row['identifier']}")
            write_inner_rings(drawing, codes, inner, room_row["holes_mm"], handles)
        subfaces = {item.identifier: item for room in model.rooms for face in room.faces for item in (*face.apertures, *face.doors)}
        seen = {}
        for item in (opening for opening in hb.openings(model, floor.story) if opening.room_identifier in floor.room_identifiers):
            item = wall_opening_bounds(item)
            key = (item.kind, tuple(sorted(tuple(round(value * scale, 2) for value in (point.x, point.y, point.z)) for point in item.boundary)))
            if key in seen:
                for row in seen[key]:
                    row["source_identifiers"].append(item.identifier)
                continue
            rectangle = subfaces[item.identifier].geometry.extract_rectangle(0.1 / scale) if abs(item.normal.z) <= 1e-4 else None
            host = host_index(item, source_walls, scale, limits) if item.host_type == "Wall" else None
            exact_parts = source_opening_parts(item, source_walls, scale, limits)
            if host is None and not exact_parts:
                reason = "host_wall_mapping_review" if rectangle is None or rectangle[2] else "opening_profile_reference"
                row = {"identifier": item.identifier, "source_identifiers": [item.identifier], "kind": item.kind, "story": floor.identifier, "reason": reason, "profile_reference": rectangle is None or bool(rectangle[2])}
                report["reference_openings"].append(row)
                seen[key] = [row]
                continue
            pieces, blockers = exact_parts, []
            if not pieces:
                row = {"identifier": item.identifier, "source_identifiers": [item.identifier], "kind": item.kind, "story": floor.identifier, "reason": "wall_intersection_reference"}
                report["reference_openings"].append(row)
                seen[key] = [row]
                continue
            kind = "DOOR" if item.kind == "Door" else "WIN"
            seen[key] = []
            for piece in pieces:
                host = piece["host"]
                segment = source_walls[host]
                ux, uy = segment.end.x - segment.start.x, segment.end.y - segment.start.y
                length = math.hypot(ux, uy)
                low, high, bottom, top = (piece[key] for key in ("low", "high", "bottom", "top"))
                along = (low + high) / 2
                profile = piece["profile"]
                block_3d = opening_block(drawing, kind, profile, wall_rows[host]["thickness_mm"], math.atan2(uy, ux))
                row = {"identifier": item.identifier, "source_identifiers": [item.identifier], "kind": item.kind, "story": floor.identifier, "mark": f"{'M' if item.kind == 'Door' else 'C'}{len(report['openings']) + 1:03d}", "position_mm": (segment.start.x * scale + along * ux / length + dx, segment.start.y * scale + along * uy / length + dy, bottom - floor.reference_elevation_mm), "width_mm": high - low, "height_mm": top - bottom, "angle_rad": math.atan2(uy, ux), "wall": wall_rows[host]["handle"], "block_2d": drawing.blocks[f"$ARCHSYS${kind}2D"][0], "block_3d": block_3d, "clipping_blockers": blockers, "profile_mm": profile}
                row["geometry_policy"] = "source_contour_partition"
                entity = add_native(drawing, codes["SWR_OPENING"], "建-门窗", row, opening, [(1000, item.identifier), (1000, item.kind)])
                wall_rows[host]["openings"].append(entity.handle)
                report["openings"].append(row)
                seen[key].append(row)
        union = unary_union([set_precision(shape, 0.01) for shape in polygons.values()])
        source_buildings = list(union.geoms) if union.geom_type == "MultiPolygon" else [union]
        buildings = [part for polygon in source_buildings for part in building_area_regions(polygon)]
        for index, polygon in enumerate(buildings):
            seed = polygon.representative_point()
            holes = [list(ring.coords)[:-1] for ring in polygon.interiors]
            row = {"identifier": f"{floor.identifier}:{index}", "name": "建筑轮廓", "story": floor.identifier, "category": 1, "position_mm": (seed.x, seed.y, 0.0), "area_m2": polygon.area / 1e6, "perimeter_mm": polygon.length, "height_mm": floor.height_mm, "outline_mm": oriented(list(polygon.exterior.coords), False), "holes_mm": holes, "walls": []}
            row["outline_policy"] = "convex_source_coverage_partition"
            row.update(layer="建-建筑区域", show_outline=False, display_role="calculation_region")
            entity = add_native(drawing, codes["SWR_SPACE"], row["layer"], row, space, [(1000, floor.identifier), (1000, "BuildingOutline"), (1000, f"interior_rings={len(holes)}"), (1071, index), (1010, (seed.x, seed.y, 0.0))])
            inner = attach_room_properties(drawing, codes, entity, holes)
            if inner:
                row["inner_properties"] = inner
                write_inner_rings(drawing, codes, inner, holes, [hole_wall_handles(hole, wall_rows) for hole in holes])
            report["building_outlines"].append(row)
        x0, y0, x1, y1 = floor.frame_bounds_mm
        frame = {"identifier": floor.identifier, "floor_number": floor.floor_number, "series": floor.series, "center_mm": ((x0 + x1) / 2, (y0 + y1) / 2), "alignment_mm": floor.alignment_mm, "width_mm": x1 - x0, "depth_mm": y1 - y0, "height_mm": frame_height}
        entity = add_native(drawing, codes["SWR_FLOOR_FRAME"], "公-视口", frame, floor_frame, [(1000, floor.identifier), (1000, "FloorFrame"), (1000, f"series={floor.series}")])
        attach_floor_series(drawing, codes, entity, floor.series)
        floor_row["frame_handle"] = entity.handle
        floor_row["frame"] = frame
        drawing.add_text(floor.identifier, (x0, y1 + 500.0, 0.0), 350.0, "HB-Labels")
        if ceiling_storeys:
            index = layouts.index(floor)
            top = floor.reference_elevation_mm + room_top
            gap = elevations[layouts[index + 1].identifier] - top if index + 1 < len(layouts) else 1000.0
            gap = max(100.0, gap)
            roof_x0 = ceiling_cursor
            ceiling_cursor += (x1 - x0) + 5000.0
            ceiling = replace(floor, identifier=f"{floor.identifier} Ceiling", floor_number=len(report["floors"]) + 1, source_elevation_mm=top, reference_elevation_mm=top, height_mm=gap, offset_mm=(floor.offset_mm[0] + roof_x0 - x0, floor.offset_mm[1]), frame_bounds_mm=(roof_x0, y0, roof_x0 + x1 - x0, y1), alignment_mm=(roof_x0, y0))
            ceiling_frame = {"identifier": ceiling.identifier, "floor_number": ceiling.floor_number, "series": "", "center_mm": (roof_x0 + (x1 - x0) / 2, (y0 + y1) / 2), "alignment_mm": ceiling.alignment_mm, "width_mm": x1 - x0, "depth_mm": y1 - y0, "height_mm": gap}
            ceiling_entity = add_native(drawing, codes["SWR_FLOOR_FRAME"], "公-视口", ceiling_frame, floor_frame, [(1000, ceiling.identifier), (1000, "FloorFrame")])
            report["floors"].append({"story": ceiling.identifier, "floor_number": ceiling.floor_number, "source_elevation_mm": top, "offset_mm": ceiling.offset_mm, "height_mm": gap, "source_height_mm": floor.height_mm, "role": "ceiling", "source_story": floor.story, "frame_handle": ceiling_entity.handle, "frame": ceiling_frame})
            for room in source_rooms:
                ceiling_layouts[room.identifier] = ceiling
            drawing.add_text(ceiling.identifier, (roof_x0, y1 + 500.0, 0.0), 350.0, "HB-Labels")
        for room in source_rooms:
            for face in room.faces:
                if face.identifier in complex_faces:
                    report["wall_profiles_for_review"].append(face.identifier)
    ground_x0 = max(item.frame_bounds_mm[2] for item in layouts) + 5000.0
    ground_y0 = min(item.frame_bounds_mm[1] for item in layouts)
    ground_width = max(item.frame_bounds_mm[2] - item.frame_bounds_mm[0] for item in layouts)
    ground_depth = max(item.frame_bounds_mm[3] - item.frame_bounds_mm[1] for item in layouts)
    ground_height = min(item.source_elevation_mm for item in layouts)
    source_low = (layouts[0].alignment_mm[0] - layouts[0].offset_mm[0], layouts[0].alignment_mm[1] - layouts[0].offset_mm[1])
    site_low, site_high = list(source_low), [source_low[0] + ground_width, source_low[1] + ground_depth]
    if source_shade_layout:
        points = [point for shade in model.shades if hb.owner_room(shade) is None for point in shade.geometry.boundary]
        points.extend(point for mesh in model.shade_meshes for point in mesh.geometry.vertices)
        for axis in range(2):
            site_low[axis] = min(site_low[axis], *(tuple(point)[axis] * scale - 1000 for point in points)) if points else site_low[axis]
            site_high[axis] = max(site_high[axis], *(tuple(point)[axis] * scale + 1000 for point in points)) if points else site_high[axis]
    ground_width, ground_depth = (site_high[axis] - site_low[axis] for axis in range(2))
    site_offset = (ground_x0 - site_low[0], ground_y0 - site_low[1])
    ground = {"identifier": "Ground", "floor_number": 0, "series": "", "center_mm": (ground_x0 + ground_width / 2, ground_y0 + ground_depth / 2), "alignment_mm": (source_low[0] + site_offset[0], source_low[1] + site_offset[1]), "width_mm": ground_width, "depth_mm": ground_depth, "height_mm": ground_height}
    ground_entity = add_native(drawing, codes["SWR_FLOOR_FRAME"], "公-视口", ground, floor_frame, [(1000, "Ground"), (1000, "FloorFrame"), (1000, "ground_elevation")])
    report["ground_frame"] = dict(ground, handle=ground_entity.handle, label="0")
    if source_shade_layout:
        report["site_layout"] = {"story": "Site", "role": "site", "floor_number": 0, "series": "", "source_elevation_mm": 0.0, "reference_elevation_mm": 0.0, "offset_mm": site_offset, "height_mm": 0.0, "frame_bounds_mm": (ground_x0, ground_y0, ground_x0 + ground_width, ground_y0 + ground_depth), "frame_handle": ground_entity.handle, "frame": report["ground_frame"], "native_object_scope": "SEBuilding_site_shading_list", "datum_height_mm": ground_height}
    drawing.add_text("总图 / 0" if source_shade_layout else "0", (ground_x0, ground_y0 + ground_depth + 500.0, 0.0), 350.0, "HB-Labels")
    add_wall_profiles(model, report, wall_semantics)
    if surface_mode == "deferred":
        report.update(surfaces=[], roof_openings=[], skylights=[])
    elif ceiling_storeys:
        add_ceiling_surfaces(drawing, codes, model, ceiling_layouts, report)
    else:
        add_surfaces(drawing, codes, model, room_levels, report, floor_slabs)
    roof_openings = {row["identifier"]: row for row in report.get("roof_openings", [])}
    report["reference_openings"] = [row for row in report["reference_openings"] if row["identifier"] not in roof_openings]
    drawing.extents = ((min(row["frame"]["center_mm"][0] - row["frame"]["width_mm"] / 2 for row in report["floors"]), min(item.frame_bounds_mm[1] for item in layouts), min(0.0, *(row["position_mm"][2] for row in report["rooms"]))), (max(max(row["frame"]["center_mm"][0] + row["frame"]["width_mm"] / 2 for row in report["floors"]), ground_x0 + ground_width), max(max(item.frame_bounds_mm[3] for item in layouts), ground_y0 + ground_depth) + 1000, max(row["height_mm"] + row["position_mm"][2] for row in report["rooms"])))
    report["classes"] = [vars(item) for item in drawing.classes]
    skylights = report.get("skylights", [])
    source_skylights = sum(len(face.apertures) for room in model.rooms for face in room.faces if str(face.type) == "RoofCeiling")
    report["counts"] = {"rooms": len(report["rooms"]), "walls": len(report["walls"]), "native_openings": len(report["openings"]), "reference_openings": len(report["reference_openings"]), "building_outlines": len(report["building_outlines"]), "floor_frames": len(report["floors"]) + 1, "inner_rings": sum(len(row["holes_mm"]) for row in report["rooms"]), "wall_profiles_for_review": len(report["wall_profiles_for_review"])}
    report["counts"].update(native_openings=len(report["openings"]), reference_openings=len(report["reference_openings"]), native_skylights=len(skylights), source_skylights=source_skylights)
    report["counts"].update(native_slabs=len(report["surfaces"]), native_wall_profiles=sum(row["status"] == "native_profile" for row in report["wall_profile_geometry"]), source_floor_faces=len({row["identifier"] for row in report["surfaces"] if row["kind"] == "Floor"}), source_roof_faces=len({row["identifier"] for row in report["surfaces"] if row["kind"] == "RoofCeiling"}), source_skylights=source_skylights)
    report["geometry_acceptance"] = {"status": "host_geometry_pending", "relative_tolerance": 0.05, "mandatory": ["closed_room_shells", "source_floor_and_roof_coverage", "sloped_roof_planes", "skylight_geometry_and_host_relations", "per_room_volume"]}
    return drawing, report


def build(model, bind_roofs=True, envelope_storeys=True, primary_levels=True, inclined_carriers=False, inclined_floors=False):
    """Build a native DWG model and return its drawing and report."""
    from .orientation import orientation_model
    source = model
    model, orientation = orientation_model(model)
    source_stories = {room.identifier: room.story or "Unassigned" for room in model.rooms}
    source_volumes = {room.identifier: room.volume * (hb.unit_scale(model.units) / 1000) ** 3 for room in model.rooms}
    repairs = []
    working, semantics = geometry_model(model, repairs)
    partitions = {face.identifier: (semantics[face.identifier], str(face.boundary_condition), face.properties.energy.construction)
                  for room in model.rooms for face in room.faces}
    drawing, report = build_plan(working, "surface", floor_slabs=False, surface_mode="deferred", primary_levels=primary_levels, source_shade_layout=True, wall_semantics=partitions)
    report["source_geometry_repairs"] = repairs
    report["face_orientation"] = orientation
    report["display_policy"] = {"primary": "native_BESI_entities_and_labels", "hidden_reference_layers": ["HB-Source-3D"]}
    codes = {item.name: item.number for item in drawing.classes}
    prepare_wall_surfaces(drawing, codes, working, report)
    complete_elevated_walls(drawing, codes, working, report)
    explicit_floors = explicit_floor_selection(working, report) if inclined_carriers and not inclined_floors else {}
    complete_native_wall_parts(drawing, codes, working, report, partitions, explicit_floors)
    for row in report["walls"]:
        if semantics.get(row["identifier"]) == "AirBoundary":
            row["catalog"] = 4
    separate_plan_wall_axes(report)
    isolate_profile_corners(report)
    rehost_wall_openings(drawing, codes, working, report)
    apply_opening_clearance(drawing, codes, working, report)
    stabilize_opening_baselines(drawing, report)
    add_roof_storey(drawing, codes, working, report, bind_roofs=bind_roofs, explicit_floor_rooms=explicit_floors, spatial_skylights=envelope_storeys)
    if inclined_floors:
        add_inclined_floor_carriers(drawing, codes, working, report)
    add_wall_surfaces(drawing, codes, working, report)
    if envelope_storeys:
        route_envelope_storeys(drawing, codes, report)
    if explicit_floors:
        add_profiled_floors(drawing, working, report, explicit_floors)
    apply_boundary_conditions(drawing, model, report)
    if inclined_carriers:
        promote_inclined_enclosures(drawing, report, model.angle_tolerance)
    refresh_room_space_references(drawing, report)
    roof_opening_ids = {row["identifier"] for row in report["roof_openings"]}
    report["reference_openings"] = [row for row in report["reference_openings"] if row["identifier"] not in roof_opening_ids]
    for row in report["rooms"]:
        row["source_story"] = source_stories[row["identifier"]]
        row["source_volume_m3"] = source_volumes[row["identifier"]]
        row["story_group"] = row["story"]
    report["counts"].update(walls=len(report["walls"]), native_slabs=len(report["surfaces"]), native_openings=len(report["openings"]), reference_openings=len(report["reference_openings"]), native_skylights=len(report["skylights"]), floor_frames=len(report["floors"]) + 2)
    report["counts"]["native_roof_faces"] = len({row["identifier"] for row in report["surfaces"] if row["kind"] == "RoofCeiling"})
    report["counts"]["source_floor_faces"] = len({face.identifier for room in model.rooms for face in room.faces if str(face.type) == "Floor"})
    source_roofs = [face for room in source.rooms for face in room.faces if str(face.type) == "RoofCeiling"]
    report["counts"]["source_roof_faces"] = len(source_roofs)
    report["counts"]["source_skylights"] = sum(len(face.apertures) for face in source_roofs)
    report["geometry_acceptance"] = {
        "status": "host_geometry_pending",
        "relative_tolerance": 0.05,
        "absolute_tolerance_mm": 1.0,
        "mandatory": ["source_room_count_and_codes", "closed_room_shells", "absolute_elevation", "source_floor_and_roof_coverage", "sloped_roof_planes", "skylight_geometry_and_host_relations", "wall_opening_geometry", "per_room_volume", "native_calculated_floor_area", "native_thermal_boundary_assembly"],
        "room_equivalence": {"status": "native_assembly_required", "phases": ["before", "reopened"],
                             "room_identity": "one_native_room_per_source_identifier",
                             "closure": "per_room_edge_pairing", "volume": "per_room_sdk_native_getter_and_closed_shell_m3",
                             "coordinate_tolerance_mm": 1.0, "volume_budget_m3": "gross_room_enclosure_area_m2 * 0.001 m",
                             "categorical_tolerance": 0,
                             "boundary": "source_face_and_subface_type_with_reciprocal_adjacent_room",
                             "source_boundaries": ["source_geometry_validation.faces", "source_geometry_validation.openings"]},
    }
    if explicit_floors:
        report["geometry_acceptance"]["profiled_floor_views"] = {
            "modules": ["BECS", "BESI", "DALI", "VENT"], "phases": ["before", "reopened"],
            "basis": "same_export_source_and_drawing",
            "required": ["native_room_geometry", "physical_floor_in_occupied_storey", "glazed_host_gross_net_and_attached_glass", "owned_model_viewer"],
            "floor_protocol": "room_bound_polyface_usage_8_on_native_model_viewer_layer",
            "daylight_ventilation_side": "manual_floor_geometry_can_be_listed_as_a_room_ceiling",
            "status": "host_observation_required"}
    add_shade_meshes(drawing, model, report)
    if model.shades or model.shade_meshes:
        report["geometry_acceptance"]["mandatory"].extend(["source_shade_mesh_geometry", "native_exterior_shading_assembly"])
    report["editability"] = {
        "schema": "native_object_editability_v1",
        "selection_priority": ["native_wall_and_opening", "native_wall_top_profile", "native_inclined_enclosure", "residual_source_panel"],
        "native_physical_walls": sum(not row.get("virtual_plan") and row.get("catalog") != 4 for row in report["walls"]),
        "native_thermal_virtual_walls": report["counts"]["native_virtual_walls"],
        "native_insulated_walls": report["counts"]["native_insulated_walls"],
        "native_elevated_walls": report["counts"]["native_elevated_walls"],
        "native_wall_top_profiles": report["counts"]["native_wall_profiles"],
        "native_openings": len(report["openings"]),
        "residual_wall_panels": len(report["wall_panels"]),
        "virtual_plan_walls": report["counts"]["native_plan_walls"],
        "shade_geometry_objects": report["shading"]["native_meshes"],
        "shade_representation": report["shading"]["representation"],
        "grip_editing": "host_verification_pending",
        "cad_3d_display": "visual_verification_pending",
        "acceptance_scope": "Object selection counts supplement geometric validation; editor behavior and visible 3D geometry receive separate host evidence",
    }
    add_source_references(drawing, model, report)
    add_source_constructions(drawing, codes, model, report)
    from .skylights import add_defined_skylights
    add_defined_skylights(drawing, model, report)
    write_bound_roof_meshes(drawing, report)
    return drawing, report
