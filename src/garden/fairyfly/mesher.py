"""Headless Gmsh Q4 finite-element meshing for Fairyfly / THERM models."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import tempfile
import threading
import xml.etree.ElementTree as ET
import zipfile

import gmsh

from fairyfly_next_therm.condition.transient import Transient
from fairyfly_next_therm.native_mesh import mesh_to_xml

_GMSH_LOCK = threading.Lock()
_GEOM_TOL = 1e-3
_RESULT_MEMBER_NAMES = frozenset({
    "SteadyStateResults.xml",
    "SteadyStateMeshResults.xml",
    "pyHygroTherm.json",
})


@dataclass(frozen=True)
class _Vertex:
    X: float
    Y: float
    Z: float = 0.0


@dataclass(frozen=True)
class _Face:
    A: int
    B: int
    C: int
    D: int


@dataclass(frozen=True)
class _Mesh:
    Vertices: tuple[_Vertex, ...]
    Faces: tuple[_Face, ...]


def thmz_has_mesh(thmz_path: str | Path) -> bool:
    """Return True if a THMZ archive contains a populated Mesh.xml."""
    path = Path(thmz_path)
    if not path.is_file():
        raise FileNotFoundError(f"THMZ archive not found: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        try:
            mesh_bytes = archive.read("Mesh.xml")
        except KeyError:
            return False
    try:
        mesh_root = ET.fromstring(mesh_bytes)
    except ET.ParseError:
        return False
    nodes = mesh_root.findall("Case/Nodes/Node")
    elements = mesh_root.findall("Case/Elements/Element")
    return bool(nodes and elements)


def _finite_float(text: str | None, field: str) -> float:
    try:
        value = float(text)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number.") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number.")
    return value


def _polygon_area(pts: list[tuple[float, float]]) -> float:
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def _intern_point(
    x: float,
    y: float,
    canonical: list[tuple[float, float]],
    tol: float = _GEOM_TOL,
) -> int:
    for idx, (cx, cy) in enumerate(canonical):
        if math.hypot(x - cx, y - cy) <= tol:
            return idx
    canonical.append((x, y))
    return len(canonical) - 1


def _split_segment(
    u: int,
    v: int,
    canonical: list[tuple[float, float]],
    tol: float = _GEOM_TOL,
) -> list[tuple[int, int]]:
    ux, uy = canonical[u]
    vx, vy = canonical[v]
    dx, dy = vx - ux, vy - uy
    length = math.hypot(dx, dy)
    if length <= tol:
        return []
    interior: list[tuple[float, int]] = []
    for idx, (px, py) in enumerate(canonical):
        if idx == u or idx == v:
            continue
        rx, ry = px - ux, py - uy
        proj = (rx * dx + ry * dy) / length
        perp = abs(rx * dy - ry * dx) / length
        if perp <= tol and tol < proj < length - tol:
            interior.append((proj, idx))
    interior.sort(key=lambda item: item[0])
    chain = [u, *(idx for _, idx in interior), v]
    return [(chain[i], chain[i + 1]) for i in range(len(chain) - 1) if chain[i] != chain[i + 1]]


def _is_strictly_convex_quad(
    pts: tuple[tuple[float, float], ...],
) -> bool:
    signs: list[int] = []
    for i in range(4):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % 4]
        cx, cy = pts[(i + 2) % 4]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) <= 1e-12:
            return False
        signs.append(1 if cross > 0 else -1)
    return len(set(signs)) == 1


def _extract_q4_mesh(
    model_xml: ET.Element,
    boundary_conditions: ET.Element,
    transient_conditions: dict[str, Any] | None,
) -> ET.Element:
    elem_types, _elem_tags, node_tags_by_type = gmsh.model.mesh.getElements(dim=2)
    if not elem_types:
        raise ValueError("Gmsh produced no 2D mesh elements.")
    if any(int(etype) != 3 for etype in elem_types):
        raise ValueError(f"Gmsh produced unsupported non-Q4 element types: {list(elem_types)}")

    quad_raw: list[tuple[int, int, int, int]] = []
    for node_tags in node_tags_by_type:
        if len(node_tags) % 4 != 0:
            raise ValueError("Gmsh returned malformed Q4 element connectivity.")
        for i in range(0, len(node_tags), 4):
            q = (int(node_tags[i]), int(node_tags[i + 1]), int(node_tags[i + 2]), int(node_tags[i + 3]))
            if len(set(q)) != 4:
                raise ValueError("Gmsh produced a degenerate Q4 element.")
            quad_raw.append(q)
    if not quad_raw:
        raise ValueError("Gmsh produced zero Q4 elements.")

    all_node_tags, coords, _ = gmsh.model.mesh.getNodes()
    tag_to_xy = {
        int(tag): (float(coords[3 * i]), float(coords[3 * i + 1]))
        for i, tag in enumerate(all_node_tags)
    }

    used_tags = sorted({tag for q in quad_raw for tag in q})
    remap = {tag: idx for idx, tag in enumerate(used_tags)}
    vertices = tuple(_Vertex(tag_to_xy[tag][0], tag_to_xy[tag][1], 0.0) for tag in used_tags)

    faces: list[_Face] = []
    for q in quad_raw:
        corners_xy = tuple(tag_to_xy[tag] for tag in q)
        if not _is_strictly_convex_quad(corners_xy):
            raise ValueError("Gmsh produced a non-convex Q4 element.")
        faces.append(_Face(remap[q[0]], remap[q[1]], remap[q[2]], remap[q[3]]))

    mesh_obj = _Mesh(Vertices=vertices, Faces=tuple(faces))
    return mesh_to_xml(
        model_xml,
        boundary_conditions,
        mesh_obj,
        transient_conditions=transient_conditions,
    )


def gmsh_mesh_to_xml(
    model_xml: ET.Element,
    boundary_conditions: ET.Element,
    target_quad_count: int = 20,
    transient_conditions: dict[str, Any] | None = None,
) -> ET.Element:
    """Generate a conforming strictly-convex Q4 Mesh.xml using headless Gmsh."""
    polygons = model_xml.findall("Polygons/Polygon")
    if not polygons or any(p.findtext("Type") != "Material" for p in polygons):
        raise ValueError("Gmsh meshing requires non-empty Material polygons in Model.xml.")

    canonical_points: list[tuple[float, float]] = []
    poly_point_rings: list[list[int]] = []
    total_area = 0.0

    for polygon in polygons:
        raw_pts = [
            (_finite_float(pt.findtext("x"), "Polygon x"), _finite_float(pt.findtext("y"), "Polygon y"))
            for pt in polygon.findall("Points/Point")
        ]
        if len(raw_pts) < 3:
            raise ValueError("Each material polygon requires at least three points.")
        total_area += _polygon_area(raw_pts)
        ring: list[int] = []
        for x, y in raw_pts:
            idx = _intern_point(x, y, canonical_points)
            if not ring or ring[-1] != idx:
                ring.append(idx)
        if len(ring) >= 2 and ring[0] == ring[-1]:
            ring.pop()
        if len(ring) < 3:
            raise ValueError("Polygon collapsed to fewer than three distinct vertices.")
        poly_point_rings.append(ring)

    for boundary in model_xml.findall("Boundaries/Boundary"):
        if boundary.findtext("Type") not in ("Boundary Condition", "Frame Cavity"):
            continue
        for tag in ("StartPoint", "EndPoint"):
            pt = boundary.find(tag)
            if pt is None:
                continue
            bx = _finite_float(pt.findtext("x"), f"{tag} x")
            by = _finite_float(pt.findtext("y"), f"{tag} y")
            _intern_point(bx, by, canonical_points)

    xs = [pt[0] for pt in canonical_points]
    ys = [pt[1] for pt in canonical_points]
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), 1e-2)
    area = max(total_area, 1e-4)
    lc = math.sqrt(area / max(int(target_quad_count), 4))
    lc = max(max(1e-2, max_dim / 500.0), min(lc, max(max_dim / 2.0, 1e-2)))

    poly_sub_edges: list[list[tuple[int, int]]] = []
    unique_segments: set[tuple[int, int]] = set()
    for ring in poly_point_rings:
        edges: list[tuple[int, int]] = []
        for i in range(len(ring)):
            u = ring[i]
            v = ring[(i + 1) % len(ring)]
            for a, b in _split_segment(u, v, canonical_points):
                edges.append((a, b))
                unique_segments.add((min(a, b), max(a, b)))
        if len(edges) < 3:
            raise ValueError("Polygon boundary loop has fewer than three segments.")
        poly_sub_edges.append(edges)

    with _GMSH_LOCK:
        saved_win_path: str | None = None
        if os.name == "nt":
            try:
                import ctypes

                buf_size = 65536
                buf = ctypes.create_unicode_buffer(buf_size)
                length = ctypes.windll.kernel32.GetEnvironmentVariableW("PATH", buf, buf_size)
                if 0 < length < buf_size:
                    saved_win_path = buf.value
            except Exception:
                saved_win_path = os.environ.get("PATH")
        if gmsh.isInitialized():
            gmsh.finalize()
        gmsh.initialize([], readConfigFiles=False, interruptible=False)
        if os.name == "nt" and saved_win_path:
            # Gmsh initialization on Windows truncates the Win32 PEB PATH via putenv.
            os.environ["PATH"] = saved_win_path
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.option.setNumber("General.Verbosity", 0)
            gmsh.model.add("fairyfly_q4")

            point_tags = [
                gmsh.model.geo.addPoint(x, y, 0.0, lc)
                for x, y in canonical_points
            ]
            line_tags = {
                key: gmsh.model.geo.addLine(point_tags[key[0]], point_tags[key[1]])
                for key in sorted(unique_segments)
            }
            for edges in poly_sub_edges:
                signed = [
                    line_tags[(a, b)] if a < b else -line_tags[(b, a)]
                    for a, b in edges
                ]
                loop_tag = gmsh.model.geo.addCurveLoop(signed)
                gmsh.model.geo.addPlaneSurface([loop_tag])
            gmsh.model.geo.synchronize()

            # Stage 1: direct frontal-Delaunay quad meshing with Blossom recombination
            try:
                gmsh.option.setNumber("Mesh.Algorithm", 8)
                gmsh.option.setNumber("Mesh.RecombineAll", 1)
                gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 2)
                gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1)
                gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.25)
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
                gmsh.model.mesh.generate(2)
                return _extract_q4_mesh(model_xml, boundary_conditions, transient_conditions)
            except Exception as first_err:
                # Stage 2 fallback: triangle-to-Q4 subdivision always yields convex Q4s
                try:
                    gmsh.model.mesh.clear()
                    gmsh.option.setNumber("Mesh.Algorithm", 6)
                    gmsh.option.setNumber("Mesh.RecombineAll", 0)
                    gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1)
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.25)
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc * 1.4)
                    gmsh.model.mesh.generate(2)
                    return _extract_q4_mesh(model_xml, boundary_conditions, transient_conditions)
                except Exception as second_err:
                    raise ValueError(
                        f"Gmsh Q4 meshing failed (stage 1: {first_err}; stage 2: {second_err})"
                    ) from second_err
        finally:
            if gmsh.isInitialized():
                gmsh.finalize()
            if os.name == "nt" and saved_win_path:
                os.environ["PATH"] = saved_win_path


def _load_transient_conditions_from_archive(archive: zipfile.ZipFile) -> dict[str, Transient]:
    names = archive.namelist()
    if "TransientTypeBC.xml" not in names:
        return {}
    timestep_lookup: dict[str, bytes] = {}
    for name in names:
        norm = name.replace("\\", "/")
        if norm.startswith("timestep input files/"):
            content = archive.read(name)
            timestep_lookup[norm] = content
            timestep_lookup[norm.rsplit("/", 1)[-1]] = content

    bct_root = ET.fromstring(archive.read("TransientTypeBC.xml"))
    conditions: dict[str, Transient] = {}
    for record in bct_root.findall("BoundaryConditionType"):
        tf_name = (record.findtext("TimestepFileName") or "").strip().replace("\\", "/")
        timesteps = None
        if tf_name:
            raw_bytes = timestep_lookup.get(tf_name) or timestep_lookup.get(tf_name.rsplit("/", 1)[-1])
            if raw_bytes is not None:
                timesteps = Transient.timesteps_from_xml(ET.fromstring(raw_bytes))
        cond = Transient.from_therm_xml(record, timesteps=timesteps)
        conditions[cond.display_name] = cond
    return conditions


def mesh_thmz_in_place(thmz_path: str | Path, target_quad_count: int = 20) -> str:
    """Generate Mesh.xml inside an unmeshed THMZ archive atomically."""
    path = Path(thmz_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"THMZ archive not found: {path}")

    with zipfile.ZipFile(path, "r") as archive:
        model_xml = ET.fromstring(archive.read("Model.xml"))
        boundary_conditions = ET.fromstring(archive.read("SteadyStateBC.xml"))
        transient_conditions = _load_transient_conditions_from_archive(archive)
        retained_members: list[tuple[str, bytes]] = []
        for member_name in archive.namelist():
            norm = member_name.replace("\\", "/")
            if (
                member_name == "Mesh.xml"
                or member_name in _RESULT_MEMBER_NAMES
                or norm.startswith("transient results/")
            ):
                continue
            retained_members.append((member_name, archive.read(member_name)))

    mesh_xml = gmsh_mesh_to_xml(
        model_xml,
        boundary_conditions,
        target_quad_count=target_quad_count,
        transient_conditions=transient_conditions or None,
    )
    mesh_bytes = ET.tostring(mesh_xml, encoding="utf-8")

    fd, staged_name = tempfile.mkstemp(prefix=".gmsh-", suffix=".thmz", dir=str(path.parent))
    staged = Path(staged_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as out:
                for member_name, data in retained_members:
                    out.writestr(member_name, data)
                out.writestr("Mesh.xml", mesh_bytes)
            stream.flush()
            if hasattr(os, "fsync"):
                os.fsync(stream.fileno())
        os.replace(staged, path)
    finally:
        if staged.exists():
            staged.unlink()
    return str(path)
