"""Geometry comparison, oblique wall projection and opening profile helpers."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass, replace
from heapq import heappop, heappush
from itertools import product
from math import acos, atan, cos, degrees, dist, floor, hypot, isfinite, radians, sin, tan, ulp

from honeybee.face import Face
from honeybee.units import conversion_factor_to_meters
from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Face3D, LineSegment3D, Point3D, Polyface3D, Polyline3D
from ladybug_geometry.triangulation import earcut
from shapely import STRtree, set_precision
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
from shapely.validation import explain_validity

from .. import model

SURFACE_KINDS = ("Floor", "RoofCeiling", "Wall", "AirBoundary")
OPENING_KINDS = ("Window", "Door")
RATIO_EPSILON = 1e-10
AREA_EPSILON = 1e-7
PLANE_NORMAL_LIMIT_DEGREES = 1.0
OVERLAY_PRECISION_MM = 1e-7


def _convex_region(polygon):
    tolerance = max(1e-7, max(ulp(value) for value in polygon.bounds) * 4)
    return not polygon.interiors and polygon.boundary.hausdorff_distance(polygon.convex_hull.boundary) <= tolerance


def convex_regions(polygon):
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Native regions require a valid positive-area polygon")
    source = set_precision(polygon, 0.0)
    origin_x, origin_y, _, _ = source.bounds
    polygon = translate(source, -origin_x, -origin_y)
    tolerance = max(1e-6, polygon.area * 1e-12)
    if _convex_region(polygon):
        return [source]
    points = list(polygon.exterior.coords)[:-1]
    holes = []
    for ring in polygon.interiors:
        holes.append(len(points))
        points.extend(list(ring.coords)[:-1])
    indices = earcut([value for point in points for value in point], holes or None)
    regions = {index // 3: Polygon([points[value] for value in indices[index:index + 3]])
               for index in range(0, len(indices), 3)}
    if any(not part.is_valid or part.area <= 0 for part in regions.values()):
        raise ValueError("Native regions require valid positive-area triangulation")
    edges = defaultdict(list)
    neighbors = defaultdict(set)
    for identity, part in regions.items():
        ring = list(part.exterior.coords)
        for first, last in zip(ring, ring[1:]):
            edges[tuple(sorted((first, last)))].append(identity)
    for shared in edges.values():
        for first in shared:
            neighbors[first].update(set(shared) - {first})
    candidates = []

    def candidate(first, second):
        first, second = sorted((first, second))
        a, b = regions[first], regions[second]
        shared = a.boundary.intersection(b.boundary).length
        merged = a.union(b)
        if shared > 0 and merged.geom_type == "Polygon" and merged.is_valid and _convex_region(merged):
            heappush(candidates, (-shared, *merged.bounds, first, second, merged))

    for first in regions:
        for second in sorted(neighbors[first]):
            if first < second:
                candidate(first, second)
    identity = len(regions)
    while candidates:
        _, _, _, _, _, first, second, merged = heappop(candidates)
        if first not in regions or second not in regions:
            continue
        adjacent = (neighbors.pop(first) | neighbors.pop(second)) - {first, second}
        regions.pop(first)
        regions.pop(second)
        regions[identity] = merged
        neighbors[identity] = adjacent
        for other in sorted(adjacent):
            neighbors[other].difference_update((first, second))
            neighbors[other].add(identity)
            candidate(identity, other)
        identity += 1
    result = list(regions.values())
    union = unary_union(result)
    if polygon.symmetric_difference(union).area > tolerance or abs(sum(part.area for part in result) - polygon.area) > tolerance:
        raise ValueError("Native regions require conserved concavities and courtyard coverage")
    result = [translate(part, origin_x, origin_y) for part in result]
    tolerance = max(tolerance, source.length * max(ulp(value) for value in source.bounds) * 2)
    if source.symmetric_difference(unary_union(result)).area > tolerance or abs(sum(part.area for part in result) - source.area) > tolerance:
        raise ValueError("Native region placement requires conserved area and courtyard coverage")
    return sorted(result, key=lambda part: (*part.bounds, part.area))


def simple_roof_regions(shape):
    regions = convex_regions(shape)
    while len(regions) > 1:
        pairs = []
        for i, j in STRtree(regions).query(regions, predicate="touches").T:
            if i >= j:
                continue
            first, second = regions[i], regions[j]
            seam = first.boundary.intersection(second.boundary).length
            if seam <= 0:
                continue
            joined = first.union(second)
            if joined.geom_type != "Polygon" or not joined.is_valid or joined.interiors:
                continue
            ring = list(joined.exterior.coords)[:-1]
            sign = 1 if joined.exterior.is_ccw else -1
            reflex = sum(sign * ((b[0]-a[0]) * (c[1]-b[1]) - (b[1]-a[1]) * (c[0]-b[0])) < -1e-12 * dist(a, b) * dist(b, c)
                         for a, b, c in zip(ring[-1:] + ring[:-1], ring, ring[1:] + ring[:1]))
            pairs.append((-seam, reflex, i, j, joined))
        if not pairs:
            break
        used, merged = set(), []
        for _, _, i, j, joined in sorted(pairs, key=lambda pair: pair[:-1]):
            if i not in used and j not in used:
                used.update((i, j))
                merged.append(joined)
        regions = [piece for i, piece in enumerate(regions) if i not in used] + merged
    union = unary_union(regions)
    if max(shape.symmetric_difference(union).area, abs(sum(p.area for p in regions) - union.area)) > shape.area * 1e-10:
        raise ValueError("Simple roof regions require conserved opaque area and disjoint interiors")
    return sorted(regions, key=lambda p: (*p.bounds, p.area))


@dataclass(frozen=True)
class _Surface:
    identifier: str
    kind: str
    geometry: Face3D
    source_identifier: str = ""
    host_identifier: str = ""


def _points(surface):
    return tuple(surface.geometry.boundary) + tuple(
        point for hole in surface.geometry.holes or () for point in hole
    )


def _polygon(surface, plane, decodings=None, shared_vertices=None):
    def ring(points):
        return [tuple(plane.xyz_to_xy(shared_vertices.get(tuple(point), point) if shared_vertices else point)) for point in points]

    polygon = Polygon(
        ring(surface.geometry.boundary),
        [ring(hole) for hole in surface.geometry.holes or ()],
    )
    if polygon.is_valid:
        stable = set_precision(polygon, OVERLAY_PRECISION_MM)
        return stable if stable.area > AREA_EPSILON and abs(stable.area - polygon.area) <= max(AREA_EPSILON, polygon.area * 1e-9) else polygon
    decoded = polygon.buffer(0)
    limit = max(AREA_EPSILON, abs(polygon.area) * 1e-9)
    if decoded.is_empty or not decoded.is_valid or abs(decoded.area - polygon.area) > limit:
        return polygon
    if decodings is not None:
        decodings.append({"identifier": surface.identifier, "encoding": "area_preserving_projected_boundary", "original_area_mm2": polygon.area, "decoded_area_mm2": decoded.area, "area_delta_mm2": decoded.area - polygon.area, "original_validity": explain_validity(polygon)})
    stable = set_precision(decoded, OVERLAY_PRECISION_MM)
    return stable if stable.area > AREA_EPSILON and abs(stable.area - decoded.area) <= limit else decoded


def _plane_report(plane):
    return {
        "origin_mm": list(plane.o),
        "normal": list(plane.n),
        "offset_mm": plane.n.dot(plane.o),
    }


def _plane_distance(first, second):
    return max(second.geometry.plane.distance_to_point(point) for point in _points(first))


def _coplanar(first, second, absolute_tolerance_mm):
    limit = absolute_tolerance_mm + 1e-7
    parallel = abs(first.geometry.normal.dot(second.geometry.normal)) >= cos(radians(PLANE_NORMAL_LIMIT_DEGREES))
    return parallel and _plane_distance(first, second) <= limit and _plane_distance(second, first) <= limit


def _ring(values, scale):
    result = []
    for value in values:
        if len(value) != 3:
            raise ValueError("Three coordinates are required for each vertex")
        point = tuple(float(coordinate) * scale for coordinate in value)
        if any(not isfinite(coordinate) for coordinate in point):
            raise ValueError("Finite coordinates are required for each vertex")
        if not result or point != result[-1]:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    if len(result) < 3:
        raise ValueError("A boundary ring requires three distinct vertices")
    return tuple(Point3D(*point) for point in result)


def _read_surface(record, scale, absolute_tolerance_mm, issues, identifier, kinds):
    identity = str(record.get("identifier", identifier))
    kind = str(record.get("kind", ""))
    try:
        if kind not in kinds:
            raise ValueError("A supported surface kind is required")
        boundary = _ring(record.get("boundary_mm", ()), scale)
        holes = tuple(_ring(hole, scale) for hole in record.get("holes_mm", ()) or ())
        surface = _Surface(
            identity,
            kind,
            Face3D(boundary, holes=holes or None),
            str(record.get("source_identifier", "")),
            str(record.get("host_identifier", "")),
        )
        deviation = max(surface.geometry.plane.distance_to_point(point) for point in _points(surface))
        if deviation > absolute_tolerance_mm + 1e-7:
            issues.append({"code": "nonplanar_surface", "identifier": identity, "maximum_deviation_mm": deviation})
            return None
        polygon = _polygon(surface, surface.geometry.plane)
        if not polygon.is_valid or polygon.area <= AREA_EPSILON:
            issues.append({"code": "invalid_polygon", "identifier": identity, "detail": explain_validity(polygon)})
            return None
        return surface
    except (ValueError, TypeError, AssertionError, ZeroDivisionError, OverflowError) as error:
        issues.append({"code": "invalid_surface", "identifier": identity, "detail": str(error)})
        return None


def _source_record(item, kind, host_identifier=""):
    return {
        "identifier": item.identifier,
        "kind": kind,
        "host_identifier": host_identifier,
        "boundary_mm": [tuple(point) for point in item.geometry.boundary],
        "holes_mm": [[tuple(point) for point in hole] for hole in item.geometry.holes or ()],
    }


def _source_room(room, scale, absolute_tolerance_mm):
    surfaces, openings, issues = [], [], []
    for face in room.faces:
        surface = _read_surface(
            _source_record(face, str(face.type)), scale, absolute_tolerance_mm,
            issues, face.identifier, SURFACE_KINDS,
        )
        if surface is not None:
            surfaces.append(surface)
        for kind, children in (("Window", face.apertures), ("Door", face.doors)):
            for child in children:
                opening = _read_surface(
                    _source_record(child, kind, face.identifier), scale,
                    absolute_tolerance_mm, issues, child.identifier, OPENING_KINDS,
                )
                if opening is not None:
                    openings.append(opening)
                    if surface is None or not _coplanar(surface, opening, absolute_tolerance_mm):
                        issues.append({"code": "opening_host_plane_mismatch", "identifier": child.identifier})
                    else:
                        opening_polygon = _polygon(opening, surface.geometry.plane)
                        host_polygon = _polygon(surface, surface.geometry.plane)
                        uncovered = opening_polygon.difference(host_polygon).area
                        noise_area = absolute_tolerance_mm * opening_polygon.length
                        if uncovered > max(AREA_EPSILON, noise_area):
                            issues.append({"code": "opening_outside_host", "identifier": child.identifier, "outside_area_m2": uncovered / 1e6})
    return surfaces, openings, issues


def _observed_room(records, absolute_tolerance_mm):
    surfaces, openings, issues = [], [], []
    if len(records) > 1:
        issues.append({"code": "duplicate_room_identifier", "count": len(records)})
    for room_record in records:
        for key, target, kinds in (("surfaces", surfaces, SURFACE_KINDS), ("openings", openings, OPENING_KINDS)):
            for index, record in enumerate(room_record.get(key, ()) or ()):
                if not isinstance(record, dict):
                    issues.append({"code": "invalid_surface_record", "collection": key, "index": index})
                    continue
                surface = _read_surface(
                    record, 1.0, absolute_tolerance_mm, issues,
                    "{}_{:04d}".format(key, len(target)), kinds,
                )
                if surface is not None:
                    target.append(surface)
    return surfaces, openings, issues


def _groups(sources, observed, absolute_tolerance_mm):
    groups = []
    for side, surfaces in (("source", sources), ("observed", observed)):
        for surface in surfaces:
            for group in groups:
                if surface.kind == group["kind"] and all(
                    _coplanar(surface, member, absolute_tolerance_mm)
                    for member in group["source"] + group["observed"]
                ):
                    break
            else:
                group = {"kind": surface.kind, "plane": surface.geometry.plane, "source": [], "observed": []}
                groups.append(group)
            group[side].append(surface)
    return groups


def _metrics(source_area, observed_area, overlap_area, tolerance):
    overlap_area = max(0.0, min(source_area, observed_area, overlap_area))
    missing_area = max(0.0, source_area - overlap_area)
    extra_area = max(0.0, observed_area - overlap_area)
    missing_ratio = missing_area / source_area if source_area > AREA_EPSILON else 0.0
    extra_ratio = extra_area / source_area if source_area > AREA_EPSILON else float(extra_area > AREA_EPSILON)
    relative = abs(observed_area - source_area) / source_area if source_area > AREA_EPSILON else float(observed_area > AREA_EPSILON)
    return {
        "source_area_m2": source_area / 1e6,
        "observed_area_m2": observed_area / 1e6,
        "overlap_area_m2": overlap_area / 1e6,
        "missing_area_m2": missing_area / 1e6,
        "extra_area_m2": extra_area / 1e6,
        "missing_ratio": missing_ratio,
        "extra_ratio": extra_ratio,
        "coverage": 1.0 - missing_ratio,
        "relative_area_difference": relative,
        "passed": max(missing_ratio, extra_ratio, relative) <= tolerance + RATIO_EPSILON,
    }


def _compare(sources, observed, tolerance, absolute_tolerance_mm):
    plane_groups, source_components, observed_components = [], [], []
    decodings = []
    source_area = observed_area = overlap_area = source_overlap = observed_overlap = 0.0
    for group in _groups(sources, observed, absolute_tolerance_mm):
        source_polygons = [_polygon(surface, group["plane"], decodings) for surface in group["source"]]
        observed_polygons = [_polygon(surface, group["plane"], decodings) for surface in group["observed"]]
        source_union, observed_union = unary_union(source_polygons), unary_union(observed_polygons)
        intersection = source_union.intersection(observed_union).area
        source_area += source_union.area
        observed_area += observed_union.area
        overlap_area += intersection
        source_overlap += max(0.0, sum(polygon.area for polygon in source_polygons) - source_union.area)
        observed_overlap += max(0.0, sum(polygon.area for polygon in observed_polygons) - observed_union.area)
        plane_groups.append({
            "plane": _plane_report(group["plane"]),
            "source_identifiers": [surface.identifier for surface in group["source"]],
            "observed_identifiers": [surface.identifier for surface in group["observed"]],
            **_metrics(source_union.area, observed_union.area, intersection, tolerance),
        })
        for surface, polygon in zip(group["source"], source_polygons):
            covered = polygon.intersection(observed_union).area
            missing = max(0.0, polygon.area - covered)
            ratio = missing / polygon.area if polygon.area > AREA_EPSILON else 0.0
            source_components.append({
                "identifier": surface.identifier,
                "source_area_m2": polygon.area / 1e6,
                "observed_covered_area_m2": covered / 1e6,
                "missing_area_m2": missing / 1e6,
                "missing_ratio": ratio,
                "coverage": 1.0 - ratio,
                "passed": ratio <= tolerance + RATIO_EPSILON,
            })
        for surface, polygon in zip(group["observed"], observed_polygons):
            covered = polygon.intersection(source_union).area
            extra = max(0.0, polygon.area - covered)
            ratio = extra / polygon.area if polygon.area > AREA_EPSILON else 0.0
            observed_components.append({
                "identifier": surface.identifier,
                "source_identifier": surface.source_identifier,
                "observed_area_m2": polygon.area / 1e6,
                "source_covered_area_m2": covered / 1e6,
                "extra_area_m2": extra / 1e6,
                "extra_ratio": ratio,
                "coverage": 1.0 - ratio,
                "passed": ratio <= tolerance + RATIO_EPSILON,
            })
    metrics = _metrics(source_area, observed_area, overlap_area, tolerance)
    metrics.update({
        "source_overlap_area_m2": source_overlap / 1e6,
        "observed_overlap_area_m2": observed_overlap / 1e6,
        "source_surfaces": source_components,
        "observed_surfaces": observed_components,
        "plane_groups": plane_groups,
        "polygon_decodings": decodings,
    })
    metrics["passed"] = metrics["passed"] and all(
        item["passed"] for item in source_components + observed_components
    )
    return metrics


def _polygons(geometry):
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area > AREA_EPSILON else []
    return [polygon for item in getattr(geometry, "geoms", ()) for polygon in _polygons(item)]


def _from_polygon(polygon, plane, template):
    def ring(coordinates):
        return tuple(plane.xy_to_xyz(Point2D(*point)) for point in list(coordinates)[:-1])

    return replace(template, geometry=Face3D(
        ring(polygon.exterior.coords),
        holes=tuple(ring(interior.coords) for interior in polygon.interiors) or None,
    ))


def _envelopes(surfaces, openings, absolute_tolerance_mm):
    envelopes, fills = [], []
    for surface in surfaces:
        plane = surface.geometry.plane
        decodings = []
        polygon = _polygon(surface, plane, decodings)
        exterior = unary_union([Polygon(piece.exterior) for piece in _polygons(polygon)])
        patches = [
            _polygon(opening, plane).intersection(exterior)
            for opening in openings if _coplanar(surface, opening, absolute_tolerance_mm)
        ]
        envelope = unary_union([polygon] + patches) if patches else polygon
        if not decodings and envelope.equals(polygon):
            envelopes.append(surface)
        else:
            envelopes.extend(_from_polygon(piece, plane, surface) for piece in _polygons(envelope))
        fill_area = max(0.0, envelope.area - polygon.area)
        if fill_area > AREA_EPSILON:
            fills.append({"identifier": surface.identifier, "opening_fill_area_m2": fill_area / 1e6})
    return envelopes, fills


def _roundoff_vertices(surfaces):
    if len(surfaces) < 2:
        return {}
    rings = [[list(map(tuple, ring)) for ring in (s.geometry.boundary, *(s.geometry.holes or ()))] for s in surfaces]
    precision = min(OVERLAY_PRECISION_MM, 16 * max(ulp(abs(v)) for face in rings for ring in face for p in ring for v in p))
    nodes, indices = _shell_nodes(rings, precision)
    ambiguous = set()
    for face in rings:
        by_node = {}
        for ring in face:
            for p in ring:
                i = indices[p]
                if by_node.setdefault(i, p) != p:
                    ambiguous.add(i)
    return {p: Point3D(*nodes[i]) for p,i in indices.items() if i not in ambiguous and p != nodes[i]}


def _union_surfaces(surfaces, absolute_tolerance_mm):
    result = []
    for group in _groups(surfaces, [], min(absolute_tolerance_mm, OVERLAY_PRECISION_MM)):
        plane = group["plane"]
        decodings = []
        shared = _roundoff_vertices(group["source"])
        polygons = [_polygon(surface, plane, decodings, shared) for surface in group["source"]]
        if len(polygons) == 1 and not decodings:
            result.append(group["source"][0])
            continue
        union = unary_union(polygons)
        parts = _polygons(union)
        holes = [ring for part in parts for ring in part.interiors]
        if (holes and not decodings and not any(p.interiors for p in polygons)
                and all(Polygon(ring).buffer(-2 * OVERLAY_PRECISION_MM).is_empty for ring in holes)
                and abs(sum(p.area for p in polygons) - union.area) <= OVERLAY_PRECISION_MM * sum(p.length for p in polygons)):
            result.extend(group["source"])
        else:
            result.extend(_from_polygon(polygon, plane, group["source"][0]) for polygon in parts)
    return result


def _edge_counts(polyface):
    return {
        "edge_count": len(polyface.edges),
        "paired_edge_count": len(polyface.internal_edges),
        "naked_edge_count": len(polyface.naked_edges),
        "non_manifold_edge_count": len(polyface.non_manifold_edges),
        "naked_edge_length_mm": sum(edge.length for edge in polyface.naked_edges),
    }


def _shell_nodes(rings, tolerance):
    cells, members, indices, nodes = defaultdict(list), [], {}, []
    for point in sorted({p for face in rings for ring in face for p in ring}):
        cell = tuple(floor(x / tolerance) for x in point)
        nearby = product(*(range(x - 1, x + 2) for x in cell))
        matches = (i for key in nearby for i in cells.get(key, ())
                   if all(dist(point, other) <= tolerance for other in members[i]))
        i = min(matches, key=lambda i: (dist(nodes[i], point), i), default=len(nodes))
        if i == len(nodes):
            cells[cell].append(i)
            nodes.append(point)
            members.append([])
        members[i].append(point)
        indices[point] = i
    return nodes, indices


def _shell_segments(first, last, indices, nodes, axes, tolerance):
    start, end = indices[first], indices[last]
    if start == end:
        return
    bounds = [(min(x, y) - tolerance, max(x, y) + tolerance) for x, y in zip(first, last)]
    ranges = [(bisect_left(axis, (low,)), bisect_right(axis, (high, len(nodes))), axis)
              for axis, (low, high) in zip(axes, bounds)]
    low, high, axis = min(ranges, key=lambda item: item[1] - item[0])
    vector = tuple(y - x for x, y in zip(first, last))
    length2 = sum(x * x for x in vector)
    splits = []
    for _, i in axis[low:high]:
        point = nodes[i]
        if i in (start, end) or any(x < lo or x > hi for x, (lo, hi) in zip(point, bounds)):
            continue
        fraction = sum((x - y) * z for x, y, z in zip(point, first, vector)) / length2
        if 0 < fraction < 1:
            projected = tuple(x + fraction * y for x, y in zip(first, vector))
            if dist(point, projected) <= tolerance and min(dist(first, projected), dist(last, projected)) > tolerance:
                splits.append((fraction, i, projected))
    knots = [(0, start, first), *sorted(splits), (1, end, last)]
    for (_, a, p), (_, b, q) in zip(knots, knots[1:]):
        yield ((a, b), 1, p, q) if a < b else ((b, a), -1, q, p)


def _shell_edge_pairing(surfaces, tolerance):
    rings = [[[tuple(p) for p in ring] for ring in (s.geometry.boundary, *(s.geometry.holes or ()))]
             for s in surfaces]
    nodes, indices = _shell_nodes(rings, tolerance)
    axes = [sorted((p[i], j) for j, p in enumerate(nodes)) for i in range(3)]
    uses = defaultdict(list)
    collapsed = 0
    for face, loops in enumerate(rings):
        for loop, ring in enumerate(loops):
            if len({indices[p] for p in ring}) == 1 and any(dist(p, ring[0]) > 2 * OVERLAY_PRECISION_MM for p in ring):
                collapsed += 1
            for first, last in zip(ring, ring[1:] + ring[:1]):
                for key, direction, p, q in _shell_segments(first, last, indices, nodes, axes, tolerance):
                    uses[key].append((face, loop, direction, p, q))

    def deviation(a, b):
        return max(dist(a[3], b[3]), dist(a[4], b[4]))

    naked, paired, non_manifold, folded = [], 0, 0, 0
    maximum_pair = maximum_fold = 0.0
    for key, entries in uses.items():
        remaining = []
        for row in entries:
            retrace_limit = min(tolerance, 2 * OVERLAY_PRECISION_MM) if row[1] else tolerance
            reverse = next((i for i, other in enumerate(remaining)
                            if other[:2] == row[:2] and other[2] == -row[2] and deviation(row, other) <= retrace_limit), None)
            if reverse is None:
                remaining.append(row)
            else:
                maximum_fold = max(maximum_fold, deviation(row, remaining.pop(reverse)))
                folded += 1
        if len(remaining) == 1:
            naked.append(LineSegment3D.from_end_points(*(Point3D(*nodes[i]) for i in key)))
        elif len(remaining) == 2 and remaining[0][0] != remaining[1][0]:
            gap = deviation(*remaining)
            if gap <= tolerance:
                maximum_pair = max(maximum_pair, gap)
                paired += 1
            else:
                naked.extend(LineSegment3D.from_end_points(Point3D(*p), Point3D(*q)) for _, _, _, p, q in remaining)
        elif remaining:
            non_manifold += 1
    counts = {"edge_count": paired + len(naked) + non_manifold, "paired_edge_count": paired,
              "naked_edge_count": len(naked), "non_manifold_edge_count": non_manifold,
              "naked_edge_length_mm": sum(edge.length for edge in naked)}
    return counts, naked, {"unpaired_collapsed_ring_count": collapsed, "cancelled_same_ring_retraces": folded, "maximum_retrace_distance_mm": maximum_fold,
                           "maximum_paired_endpoint_distance_mm": maximum_pair}


def _shell(surfaces, absolute_tolerance_mm):
    report = {
        "closed": False,
        "volume_m3": None,
        "face_count": len(surfaces),
        "normalized_face_count": 0,
        "edge_pairing": {"edge_count": 0, "paired_edge_count": 0, "naked_edge_count": 0, "non_manifold_edge_count": 0, "naked_edge_length_mm": 0.0},
        "boundary_loops": [],
        "boundary_loop_count": 0,
        "open_boundary_chain_count": 0,
        "absolute_tolerance_mm": absolute_tolerance_mm,
    }
    if not surfaces:
        report["issue"] = "empty_shell"
        return report
    try:
        raw = Polyface3D.from_faces([surface.geometry for surface in surfaces], absolute_tolerance_mm)
        normalized = _union_surfaces(surfaces, absolute_tolerance_mm)
        counts, naked, normalization = _shell_edge_pairing(normalized, absolute_tolerance_mm)
        report["raw_edge_pairing"] = _edge_counts(raw)
        report["edge_pairing"] = counts
        report.update(normalization)
        report["normalized_face_count"] = len(normalized)
        report["edge_normalization_applied"] = report["raw_edge_pairing"] != report["edge_pairing"]
        for boundary in Polyline3D.join_segments(naked, absolute_tolerance_mm):
            vertices = boundary.vertices if isinstance(boundary, Polyline3D) else (boundary.p1, boundary.p2)
            closed = isinstance(boundary, Polyline3D) and boundary.is_closed(absolute_tolerance_mm)
            report["boundary_loops"].append({
                "closed": closed,
                "vertices_mm": [list(point) for point in vertices],
                "length_mm": boundary.length,
            })
        report["boundary_loop_count"] = sum(item["closed"] for item in report["boundary_loops"])
        report["open_boundary_chain_count"] = sum(not item["closed"] for item in report["boundary_loops"])
        report["closed"] = counts["paired_edge_count"] > 0 and not naked and counts["non_manifold_edge_count"] == 0 and not normalization["unpaired_collapsed_ring_count"]
        if report["closed"]:
            faces = Polyface3D.get_outward_faces([surface.geometry for surface in normalized], absolute_tolerance_mm)
            origin = faces[0].boundary[0]
            volume = abs(sum((face.boundary[0] - origin).dot(face.normal) * face.area for face in faces) / 3)
            if isfinite(volume) and volume > AREA_EPSILON:
                report["volume_m3"] = volume / 1e9
            else:
                report["closed"] = False
                report["issue"] = "zero_or_invalid_volume"
    except (ValueError, TypeError, AssertionError, ZeroDivisionError, IndexError, GEOSException) as error:
        report["closed"] = False
        report["issue"] = "shell_construction_error"
        report["detail"] = str(error)
    return report


def _opening_candidates(source, observed, absolute_tolerance_mm):
    identified = [item for item in observed if item.kind == source.kind and source.identifier in (item.identifier, item.source_identifier)]
    if identified:
        return identified
    source_polygon = _polygon(source, source.geometry.plane)
    return [
        item for item in observed
        if item.kind == source.kind and _coplanar(source, item, absolute_tolerance_mm)
        and source_polygon.intersection(_polygon(item, source.geometry.plane)).area > AREA_EPSILON
    ]


def _opening_report(source, sources, observed, surfaces, tolerance, absolute_tolerance_mm, expected=None):
    candidates = _opening_candidates(source, observed, absolute_tolerance_mm)
    effective = [source] if expected is None else expected
    comparison = _compare(effective, candidates, tolerance, absolute_tolerance_mm)
    host = next((item for item in sources if item.identifier == source.host_identifier), None)
    observed_hosts = [
        item for item in surfaces if host is not None and item.kind == host.kind
        and _coplanar(host, item, absolute_tolerance_mm)
        and _coplanar(source, item, absolute_tolerance_mm)
    ]
    host_polygons = [Polygon(piece.exterior) for item in observed_hosts for piece in _polygons(_polygon(item, source.geometry.plane))]
    source_polygon = unary_union([_polygon(item, source.geometry.plane) for item in effective])
    support = unary_union(host_polygons)
    host_coverage = source_polygon.intersection(support).area / source_polygon.area if source_polygon.area > AREA_EPSILON else 1.0
    host_matches = host is not None and (bool(observed_hosts) or not effective) and host_coverage >= 1.0 - tolerance - RATIO_EPSILON
    plane_matches = []
    for candidate in candidates:
        reference = host if host is not None else source
        dot = abs(reference.geometry.normal.dot(candidate.geometry.normal))
        plane_matches.append({
            "identifier": candidate.identifier,
            "declared_host_identifier": candidate.host_identifier,
            "plane": _plane_report(candidate.geometry.plane),
            "normal_angle_degrees": degrees(acos(min(1.0, max(0.0, dot)))),
            "maximum_host_plane_distance_mm": _plane_distance(candidate, reference),
            "coplanar_with_source_host": _coplanar(candidate, reference, absolute_tolerance_mm),
        })
    return {
        "identifier": source.identifier,
        "kind": source.kind,
        "source_host_identifier": source.host_identifier,
        "source_host_kind": host.kind if host is not None else None,
        "source_plane": _plane_report(source.geometry.plane),
        "source_host_plane": _plane_report(host.geometry.plane) if host is not None else None,
        "source_area_3d_m2": comparison["source_area_m2"],
        "untrimmed_source_area_3d_m2": source.geometry.area / 1e6,
        "clearance_trimmed_area_m2": (source.geometry.area - source_polygon.area) / 1e6,
        "raw_source_shape_comparison": _compare([source], candidates, tolerance, absolute_tolerance_mm) if expected is not None else None,
        "observed_area_3d_m2": comparison["observed_area_m2"],
        "observed_identifiers": [item.identifier for item in candidates],
        "observed_host_identifiers": [item.identifier for item in observed_hosts],
        "host_plane_match": bool(observed_hosts),
        "host_shape_coverage": host_coverage,
        "host_matched": host_matches,
        "plane_matches": plane_matches,
        "shape_comparison": comparison,
        "passed": comparison["passed"] and host_matches,
    }


def _maximum_ratio(comparisons):
    values = [0.0]
    for comparison in comparisons:
        values.extend(comparison[key] for key in ("missing_ratio", "extra_ratio", "relative_area_difference"))
        values.extend(item["missing_ratio"] for item in comparison["source_surfaces"])
        values.extend(item["extra_ratio"] for item in comparison["observed_surfaces"])
    return max(values)


def _compare_room(room, records, scale, tolerance, absolute_tolerance_mm, opening_expectations=None):
    source_surfaces, source_openings, source_issues = _source_room(room, scale, absolute_tolerance_mm)
    expectations = opening_expectations or {}
    effective_openings = [item for opening in source_openings for item in expectations.get(opening.identifier, [opening])]
    observed_surfaces, observed_openings, observed_issues = _observed_room(records, absolute_tolerance_mm)
    observed_envelopes, fills = _envelopes(observed_surfaces, observed_openings, absolute_tolerance_mm)
    source_shell = _shell(source_surfaces, absolute_tolerance_mm)
    observed_shell = _shell(observed_envelopes, absolute_tolerance_mm)
    kinds = {
        kind: _compare(
            [surface for surface in source_surfaces if surface.kind == kind],
            [surface for surface in observed_envelopes if surface.kind == kind],
            tolerance, absolute_tolerance_mm,
        ) for kind in SURFACE_KINDS
    }
    opening_kinds = {
        kind: _compare(
            [opening for opening in effective_openings if opening.kind == kind],
            [opening for opening in observed_openings if opening.kind == kind],
            tolerance, absolute_tolerance_mm,
        ) for kind in OPENING_KINDS
    }
    openings = [
        _opening_report(opening, source_surfaces, observed_openings, observed_surfaces, tolerance, absolute_tolerance_mm, expectations.get(opening.identifier))
        for opening in source_openings
    ]
    issues = []
    if not records:
        issues.append("observed_room_missing")
    for kind in ("Floor", "RoofCeiling"):
        def supports(surface):
            return surface.kind == kind or surface.kind == "AirBoundary" and (surface.geometry.normal.z < -0.9999 if kind == "Floor" else surface.geometry.normal.z > 0.9999)
        if not any(supports(surface) for surface in source_surfaces):
            source_issues.append({"code": "critical_surface_kind_missing", "kind": kind})
        if not any(supports(surface) for surface in observed_surfaces):
            observed_issues.append({"code": "critical_surface_kind_missing", "kind": kind})
    for side, surfaces, shell, errors in (
        ("source", source_surfaces, source_shell, source_issues),
        ("observed", observed_envelopes, observed_shell, observed_issues),
    ):
        if not shell["closed"]:
            errors.append({"code": "shell_open", "boundary_loop_count": shell["boundary_loop_count"], "open_boundary_chain_count": shell["open_boundary_chain_count"]})
        for kind, comparison in kinds.items():
            overlap_area = comparison[side + "_overlap_area_m2"] * 1e6
            noise_area = absolute_tolerance_mm * sum(
                _polygon(surface, surface.geometry.plane).length for surface in surfaces if surface.kind == kind
            )
            if overlap_area > max(AREA_EPSILON, noise_area):
                errors.append({"code": "overlapping_surfaces", "kind": kind, "overlap_area_m2": overlap_area / 1e6})
    for side, items, errors in (
        ("source", effective_openings, source_issues),
        ("observed", observed_openings, observed_issues),
    ):
        for kind, comparison in opening_kinds.items():
            overlap_area = comparison[side + "_overlap_area_m2"] * 1e6
            noise_area = absolute_tolerance_mm * sum(
                _polygon(item, item.geometry.plane).length for item in items if item.kind == kind
            )
            if overlap_area > max(AREA_EPSILON, noise_area):
                errors.append({"code": "overlapping_openings", "kind": kind, "overlap_area_m2": overlap_area / 1e6})
    source_volume = source_shell["volume_m3"]
    observed_volume = observed_shell["volume_m3"]
    relative_volume = abs(observed_volume - source_volume) / source_volume if source_volume and observed_volume is not None else None
    honeybee_volume = None
    honeybee_difference = None
    try:
        honeybee_volume = float(room.volume) * (scale / 1000) ** 3
        if not isfinite(honeybee_volume):
            honeybee_volume = None
        if source_volume and honeybee_volume is not None:
            honeybee_difference = abs(honeybee_volume - source_volume) / source_volume
            if honeybee_difference > tolerance + RATIO_EPSILON:
                source_issues.append({"code": "honeybee_shell_volume_difference", "relative_difference": honeybee_difference})
    except (ValueError, TypeError, AssertionError, ZeroDivisionError, IndexError) as error:
        source_issues.append({"code": "honeybee_volume_error", "detail": str(error)})
    volume = {
        "source_m3": source_volume,
        "observed_m3": observed_volume,
        "relative_difference": relative_volume,
        "source_honeybee_m3": honeybee_volume,
        "source_honeybee_relative_difference": honeybee_difference,
        "passed": relative_volume is not None and relative_volume <= tolerance + RATIO_EPSILON,
    }
    if source_issues:
        issues.append("source_geometry_review_required")
    if observed_issues:
        issues.append("observed_geometry_review_required")
    if any(not comparison["passed"] for comparison in kinds.values()):
        issues.append("surface_coverage_exceeds_tolerance")
    if any(not comparison["passed"] for comparison in opening_kinds.values()) or any(not item["passed"] for item in openings):
        issues.append("opening_geometry_review_required")
    if not volume["passed"]:
        issues.append("volume_geometry_review_required")
    comparisons = list(kinds.values()) + list(opening_kinds.values()) + [item["shape_comparison"] for item in openings]
    maximum = max(_maximum_ratio(comparisons), relative_volume or 0.0, honeybee_difference or 0.0)
    surface_area = _metrics(
        sum(item["source_area_m2"] for item in kinds.values()) * 1e6,
        sum(item["observed_area_m2"] for item in kinds.values()) * 1e6,
        sum(item["overlap_area_m2"] for item in kinds.values()) * 1e6,
        tolerance,
    )
    return {
        "identifier": room.identifier,
        "status": "passed" if not issues else "geometry_review_required",
        "passed": not issues,
        "surface_area": surface_area,
        "surface_kinds": kinds,
        "opening_kinds": opening_kinds,
        "openings": openings,
        "skylights": [item for item in openings if item["kind"] == "Window" and item["source_host_kind"] == "RoofCeiling"],
        "source_shell": source_shell,
        "observed_shell": observed_shell,
        "observed_opening_fills": fills,
        "volume": volume,
        "max_relative_difference": maximum,
        "source_issues": source_issues,
        "observed_issues": observed_issues,
        "issues": issues,
    }


def compare_model_geometry(model, observed_rooms, tolerance=0.05, absolute_tolerance_mm=1.0, opening_expectations=None):
    tolerance = float(tolerance)
    absolute_tolerance_mm = float(absolute_tolerance_mm)
    if not isfinite(tolerance) or not 0.0 <= tolerance <= 1.0:
        raise ValueError("Relative tolerance must be finite and within [0, 1]")
    if not isfinite(absolute_tolerance_mm) or absolute_tolerance_mm <= 0.0:
        raise ValueError("Absolute tolerance must be a positive finite millimetre value")
    scale = conversion_factor_to_meters(model.units) * 1000
    grouped, issues = {}, []
    observed_rooms = list(observed_rooms or ())
    for index, record in enumerate(observed_rooms):
        if not isinstance(record, dict) or not record.get("identifier"):
            issues.append({"code": "invalid_observed_room", "index": index})
            continue
        grouped.setdefault(str(record["identifier"]), []).append(record)
    rooms = [
        _compare_room(room, grouped.get(room.identifier, []), scale, tolerance, absolute_tolerance_mm, opening_expectations)
        for room in model.rooms
    ]
    expected = {room.identifier for room in model.rooms}
    unexpected = []
    for identifier, records in grouped.items():
        if identifier in expected:
            continue
        surfaces, openings, errors = _observed_room(records, absolute_tolerance_mm)
        unexpected.append({
            "identifier": identifier,
            "surface_count": len(surfaces),
            "opening_count": len(openings),
            "observed_area_m2": sum(surface.geometry.area for surface in surfaces) / 1e6,
            "issues": errors,
            "passed": False,
        })
    if not rooms:
        issues.append({"code": "source_rooms_empty"})
    if not observed_rooms:
        issues.append({"code": "observed_rooms_empty"})
    if unexpected:
        issues.append({"code": "unexpected_observed_rooms", "identifiers": [room["identifier"] for room in unexpected]})
    if any(not room["passed"] for room in rooms):
        issues.append({"code": "room_geometry_review_required", "identifiers": [room["identifier"] for room in rooms if not room["passed"]]})
    maximum = max([room["max_relative_difference"] for room in rooms] + [1.0 if unexpected else 0.0])
    volume_available = bool(rooms) and all(room["volume"]["relative_difference"] is not None for room in rooms)
    summary = {
        "source_room_count": len(rooms),
        "observed_room_count": len(observed_rooms),
        "passed_room_count": sum(room["passed"] for room in rooms),
        "source_anomaly_room_count": sum(bool(room["source_issues"]) for room in rooms),
        "source_closed_shell_count": sum(room["source_shell"]["closed"] for room in rooms),
        "observed_closed_shell_count": sum(room["observed_shell"]["closed"] for room in rooms),
        "source_skylight_count": sum(len(room["skylights"]) for room in rooms),
        "passed_skylight_count": sum(item["passed"] for room in rooms for item in room["skylights"]),
        "source_area_m2": sum(room["surface_area"]["source_area_m2"] for room in rooms),
        "observed_area_m2": sum(room["surface_area"]["observed_area_m2"] for room in rooms),
        "source_volume_m3": sum(room["volume"]["source_m3"] or 0.0 for room in rooms) if all(room["source_shell"]["closed"] for room in rooms) and rooms else None,
        "observed_volume_m3": sum(room["volume"]["observed_m3"] or 0.0 for room in rooms) if volume_available else None,
        "volume_comparison_available": volume_available,
        "max_relative_difference": maximum,
    }
    return {
        "schema": "offline_dwg_geometry_v1",
        "status": "passed" if not issues else "geometry_review_required",
        "passed": not issues,
        "tolerance": tolerance,
        "absolute_tolerance_mm": absolute_tolerance_mm,
        "plane_normal_limit_degrees": PLANE_NORMAL_LIMIT_DEGREES,
        "overlay_precision_mm": OVERLAY_PRECISION_MM,
        "coordinate_units": "Millimeters",
        "area_basis": "3D coplanar union/difference of gross room envelopes; actual hosted opening polygons fill observed surface cutouts",
        "ratio_basis": "Kind missing/extra ratios use source union area; each source component also limits missing/source and each observed component limits extra/observed",
        "shell_basis": "Coplanar unions and noded 3D boundary segments; each pair requires distinct faces and both endpoint distances within the absolute tolerance",
        "max_relative_difference": maximum,
        "summary": summary,
        "rooms": rooms,
        "unexpected_rooms": unexpected,
        "issues": issues,
    }


def wall_point(row, along, elevation):
    first, last = row["start_mm"], row["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
    shift = -tan(row.get("oblique_angle", 0.0)) * (elevation - first[2])
    return first[0] + along * ux - shift * uy, first[1] + along * uy + shift * ux, elevation


def wall_points(row):
    first, last = row["start_mm"], row["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    rise = last[2] - first[2]
    if row.get("oblique_angle"):
        angle = row["oblique_angle"]
        ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
        normal = (uy * cos(angle), -ux * cos(angle), -sin(angle))
        distance = sum((last[index] - first[index]) * normal[index] for index in range(3))
        projected = tuple(last[index] - distance * normal[index] for index in range(3))
        points = [first, projected, wall_point(row, length, first[2] + row["height_mm"]), wall_point(row, 0, first[2] + row["height_mm"])]
        clean = []
        for point in points:
            if not clean or sum((a - b) ** 2 for a, b in zip(clean[-1], point)) > 1e-12:
                clean.append(point)
        if len(clean) > 1 and sum((a - b) ** 2 for a, b in zip(clean[0], clean[-1])) <= 1e-12:
            clean.pop()
        return clean
    if abs(rise) > 1e-8 and not row.get("oblique_angle"):
        if not row.get("profile_mm"):
            return [first, last, (last[0], last[1], last[2] + row["height_mm"]), (first[0], first[1], first[2] + row["height_mm"])]
        distance = hypot(length, rise)
        ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
        points = [first, last, *[(first[0] + ux * (along * length - height * rise) / distance,
                                first[1] + uy * (along * length - height * rise) / distance,
                                first[2] + (along * rise + height * length) / distance) for along, height in reversed(row["profile_mm"])]]
        clean = []
        for point in points:
            if not clean or sum((a - b) ** 2 for a, b in zip(clean[-1], point)) > 1e-12:
                clean.append(point)
        if len(clean) > 1 and sum((a - b) ** 2 for a, b in zip(clean[0], clean[-1])) <= 1e-12:
            clean.pop()
        return clean
    profile = row.get("profile_mm") or [(0.0, row["height_mm"]), (length, row["height_mm"])]
    return [first, last, *[wall_point(row, along, first[2] + height) for along, height in reversed(profile)]]


def opening_boundary_profile(row, boundary):
    angle = row["angle_rad"]
    nx, ny, nz = boundary["normal"]
    direction = 1.0 if -nx * sin(angle) + ny * cos(angle) < -1e-6 else -1.0
    return [(direction * x, z) for x, z in boundary["points"]]


def opening_points(row, host, profile=None):
    profile = row.get("profile_mm", ()) if profile is None else profile
    x, y, z = row["position_mm"]
    angle = row["angle_rad"]
    first, last = host["start_mm"], host["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    ux, uy = (last[0] - first[0]) / length, (last[1] - first[1]) / length
    oblique = host.get("oblique_angle", 0.0)
    result = []
    for u, v in profile:
        elevation = z + v * row["height_mm"] / 1200 * cos(oblique)
        shift = -tan(oblique) * (elevation - first[2])
        along = u * row["width_mm"] / 1200
        result.append((x + along * cos(angle) - shift * uy, y + along * sin(angle) + shift * ux, elevation))
    return result


def source_oblique_wall(face, room, floor, geometry=None):
    from .walls import source_wall

    geometry = geometry or face.geometry
    scale = floor["scale"]
    normal = face.normal
    horizontal = hypot(normal.x, normal.y)
    if abs(normal.z) <= 1e-8 or horizontal <= 1e-4 or geometry.holes:
        return None
    if any(max(item.plane.distance_to_point(point) * scale for point in (*item.boundary, *(point for ring in item.holes or () for point in ring))) > 0.001 for item in (geometry, face.geometry)):
        return None
    bottom = min(point.z for point in geometry.boundary)
    slope = normal.z / horizontal
    left = (-normal.x / horizontal, -normal.y / horizontal)
    boundary = tuple(Point3D(point.x - (point.z - bottom) * slope * left[0], point.y - (point.z - bottom) * slope * left[1], point.z) for point in geometry.boundary)
    flattened = Face(face.identifier, Face3D(boundary), face.type, face.boundary_condition)
    flattened.properties.energy.construction = face.properties.energy.construction
    row = source_wall(flattened, room, floor, allow_base=True)
    if row is None:
        return None
    first, last = row["start_mm"], row["end_mm"]
    length = hypot(last[0] - first[0], last[1] - first[1])
    left = (-(last[1] - first[1]) / length, (last[0] - first[0]) / length)
    row.update(oblique_angle=-atan(-normal.z / (normal.x * left[0] + normal.y * left[1])), source_oblique=True, profile_status="source_oblique_native_wall")
    candidate = Face3D(tuple(Point3D(point[0] - floor["offset_mm"][0], point[1] - floor["offset_mm"][1], point[2] + floor["reference_elevation_mm"]) for point in wall_points(row)))
    source = geometry.scale(scale)
    expected = _polygon(_Surface(face.identifier, "Wall", source), source.plane)
    actual = _polygon(_Surface(face.identifier, "Wall", candidate), source.plane)
    if max(source.plane.distance_to_point(point) for point in candidate.boundary) > 0.001 or expected.symmetric_difference(actual).area > max(1.0, expected.area * 1e-8):
        return None
    row.update(source_area_m2=source.area / 1e6, native_area_m2=candidate.area / 1e6)
    return row


def sloped_oblique_wall(face, room, floor, geometry=None):

    geometry = geometry or face.geometry
    horizontal = hypot(face.normal.x, face.normal.y)
    if abs(face.normal.z) <= 1e-8 or horizontal <= 1e-4 or geometry.holes:
        return None
    scale = floor["scale"]
    source = geometry.scale(scale)
    if max(source.plane.distance_to_point(point) for point in source.boundary) > 0.001:
        return None
    top, bottom = source.max.z, source.min.z
    if top - bottom <= 0.001:
        return None
    points = list(source.boundary)
    expected = _polygon(_Surface(face.identifier, "Wall", source), source.plane)
    for index, first in enumerate(points):
        if first.z - bottom > 0.001:
            continue
        for last in (points[index - 1], points[(index + 1) % len(points)]):
            rise = last.z - first.z
            if rise <= 0.001:
                continue
            ux, uy = -face.normal.y / horizontal, face.normal.x / horizontal
            along = (last.x - first.x) * ux + (last.y - first.y) * uy
            reversed_axis = along < 0
            if reversed_axis:
                ux, uy, along = -ux, -uy, -along
            if along <= 0.01:
                continue
            angle = atan(face.normal.z / (-face.normal.x * uy + face.normal.y * ux))
            dx, dy = floor["offset_mm"]
            row = {"identifier": face.identifier, "source_identifiers": [face.identifier], "story": floor["story"], "source_room": room.identifier,
                   "start_mm": (first.x + dx, first.y + dy, first.z - floor["reference_elevation_mm"]),
                   "end_mm": (first.x + along * ux + dx, first.y + along * uy + dy, first.z + rise / cos(angle) ** 2 - floor["reference_elevation_mm"]),
                   "height_mm": top - first.z, "thickness_mm": max(1.0, model.face_thickness_m(face) * 1000),
                    "oblique_angle": angle, "openings": [], "neighbors": [0, 0, 0, 0],
                    "left_space": 0 if reversed_axis else floor["room_handle"], "right_space": floor["room_handle"] if reversed_axis else 0,
                   "source_oblique": True, "source_sloped_base": True, "source_oblique_sloped_base": True,
                   "source_elevated": first.z - model.room_floor_elevation(room) * scale > 0.5,
                   "profile_status": "native_oblique_3D_baseline_side_projection"}
            candidate = Face3D(tuple(Point3D(point[0] - dx, point[1] - dy, point[2] + floor["reference_elevation_mm"]) for point in wall_points(row)))
            actual = _polygon(_Surface(face.identifier, "Wall", candidate), source.plane)
            if max(source.plane.distance_to_point(point) for point in candidate.boundary) <= 0.001 and expected.symmetric_difference(actual).area <= max(1.0, expected.area * 1e-8):
                row.update(source_area_m2=source.area / 1e6, native_area_m2=candidate.area / 1e6)
                return row
    return None


def polygons(shape):
    if shape.geom_type == "Polygon":
        return [shape] if shape.area > 1e-6 else []
    return [piece for item in getattr(shape, "geoms", ()) for piece in polygons(item)]


def source_opening_parts(item, walls, scale, limits):
    if item.host_type != "Wall" or abs(item.normal.z) > 1e-4:
        return []
    ux, uy = item.normal.y, -item.normal.x
    length = hypot(ux, uy)
    ux, uy = ux / length, uy / length
    origin = item.boundary[0].scale(scale)
    source = set_precision(Polygon([((point.x * scale - origin.x) * ux + (point.y * scale - origin.y) * uy, point.z * scale) for point in item.boundary]), OVERLAY_PRECISION_MM)
    candidates = []
    elevation = limits[item.room_identifier][0]
    for index, segment in enumerate(walls):
        if abs(segment.normal.dot(item.normal)) < 0.9999 or abs(limits[segment.room_identifier][0] - elevation) * scale > 0.5:
            continue
        points = (segment.start.scale(scale), segment.end.scale(scale))
        if max(abs((point.x - origin.x) * uy - (point.y - origin.y) * ux) for point in points) > 0.5:
            continue
        low, high = sorted((point.x - origin.x) * ux + (point.y - origin.y) * uy for point in points)
        base, height = limits[segment.room_identifier]
        clipped = source.intersection(box(low, base * scale, high, (base + height) * scale))
        if clipped.area > 1e-6:
            candidates.append((segment.face_identifier != item.host_identifier, segment.room_identifier != item.room_identifier, segment.exterior != item.host_exterior, index, clipped))
    covered = Polygon()
    result = []
    for _, _, _, index, clipped in sorted(candidates, key=lambda row: row[:4]):
        segment = walls[index]
        dx, dy = (segment.end.x - segment.start.x) * scale, (segment.end.y - segment.start.y) * scale
        length = hypot(dx, dy)
        sx, sy = segment.start.x * scale, segment.start.y * scale
        for polygon in polygons(clipped.difference(covered)):
            if polygon.interiors:
                continue
            coordinates = [(((origin.x + x * ux - sx) * dx + (origin.y + x * uy - sy) * dy) / length, z) for x, z in list(polygon.exterior.coords)[:-1]]
            low, high = min(x for x, z in coordinates), max(x for x, z in coordinates)
            bottom, top = min(z for x, z in coordinates), max(z for x, z in coordinates)
            if high - low <= 1e-6 or top - bottom <= 1e-6:
                continue
            center = (low + high) / 2
            profile = [((x - center) * 1200 / (high - low), (z - bottom) * 1200 / (top - bottom)) for x, z in coordinates]
            result.append({"host": index, "low": low, "high": high, "bottom": bottom, "top": top, "profile": profile})
        covered = unary_union([covered, clipped])
    return result


def area_metrics(expected, observed, tolerance):
    missing = expected.difference(observed).area
    extra = observed.difference(expected).area
    limit = max(1.0, expected.area * tolerance)
    return {"source_area_m2": expected.area / 1e6, "native_area_m2": observed.area / 1e6, "missing_area_m2": missing / 1e6, "extra_area_m2": extra / 1e6, "passed": missing <= limit and extra <= limit}


def coverage(geometry, candidates, scale, tolerance=0.05, check_extra=True, expected_shape=None):
    geometry = geometry.scale(scale)
    plane = geometry.plane
    decodings = []
    expected = _polygon(_Surface("Source", "Surface", geometry), plane, decodings)
    if expected_shape is not None:
        expected = expected_shape
    if not expected.is_valid or expected.area <= 0 and expected_shape is None:
        area = max(0.0, expected.area) / 1e6
        return {"passed": False, "status": "source_polygon_review_required", "source_area_m2": area, "native_area_m2": 0.0, "missing_area_m2": area, "extra_area_m2": 0.0}
    polygons = []
    rejected = 0
    for boundary, holes in candidates:
        points = [Point3D(*point) for point in boundary]
        hole_points = [[Point3D(*point) for point in hole] for hole in holes]
        candidate = Face3D(tuple(points), holes=tuple(tuple(hole) for hole in hole_points) or None)
        normal = candidate.normal
        distance = max(plane.distance_to_point(point) for point in (*points, *(point for hole in hole_points for point in hole)))
        if abs(normal.dot(geometry.normal)) < cos(radians(1.0)) or distance > 1.0 + 1e-6:
            rejected += 1
            continue
        polygon = _polygon(_Surface(f"Native:{len(polygons) + rejected}", "Surface", candidate), plane, decodings)
        if polygon.is_valid:
            polygons.append(polygon)
        else:
            rejected += 1
    result = area_metrics(expected, unary_union(polygons), tolerance)
    if not check_extra:
        result["passed"] = result["missing_area_m2"] * 1e6 <= max(1.0, expected.area * tolerance)
        result["extra_area_scope"] = "room_wall_plane_unions"
    result.update(status="native_geometry_compared", native_parts=len(polygons), rejected_parts=rejected, polygon_decodings=decodings)
    return result
