"""Pure-Python / NumPy vectorized Möller–Trumbore ray-triangle intersection engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.fraction import Fraction
from ladybug.header import Header
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.viewsphere import view_sphere
from ladybug_geometry.geometry3d import Face3D, LineSegment3D, Mesh3D, Point3D, Vector3D


@dataclass(frozen=True)
class TriangleMesh:
    """Triangulated 3D surface representation for vectorized ray intersection."""

    v0: np.ndarray
    e1: np.ndarray
    e2: np.ndarray
    normals: np.ndarray
    face_indices: np.ndarray
    face_count: int
    bbox_min: np.ndarray | None
    bbox_max: np.ndarray | None

    @property
    def triangle_count(self) -> int:
        return int(self.v0.shape[0])


def _empty_triangle_mesh(face_count: int = 0) -> TriangleMesh:
    empty = np.empty((0, 3), dtype=np.float64)
    return TriangleMesh(
        v0=empty,
        e1=empty,
        e2=empty,
        normals=empty,
        face_indices=np.empty((0,), dtype=np.int32),
        face_count=face_count,
        bbox_min=None,
        bbox_max=None,
    )


def _append_triangle(
    tri_v0: list[tuple[float, float, float]],
    tri_v1: list[tuple[float, float, float]],
    tri_v2: list[tuple[float, float, float]],
    tri_normals: list[tuple[float, float, float]],
    tri_faces: list[int],
    p0: Point3D,
    p1: Point3D,
    p2: Point3D,
    normal: Vector3D,
    face_idx: int,
) -> None:
    tri_v0.append((float(p0.x), float(p0.y), float(p0.z)))
    tri_v1.append((float(p1.x), float(p1.y), float(p1.z)))
    tri_v2.append((float(p2.x), float(p2.y), float(p2.z)))
    tri_normals.append((float(normal.x), float(normal.y), float(normal.z)))
    tri_faces.append(face_idx)


def triangulate_geometry(geometries: Iterable[Face3D | Mesh3D]) -> TriangleMesh:
    """Convert Ladybug ``Face3D`` and ``Mesh3D`` objects into a ``TriangleMesh``."""
    tri_v0: list[tuple[float, float, float]] = []
    tri_v1: list[tuple[float, float, float]] = []
    tri_v2: list[tuple[float, float, float]] = []
    tri_normals: list[tuple[float, float, float]] = []
    tri_faces: list[int] = []
    face_counter = 0

    for geo in geometries:
        if isinstance(geo, Mesh3D):
            for f_idx, f_verts in enumerate(geo.face_vertices):
                f_norm = geo.face_normals[f_idx]
                n_verts = len(f_verts)
                if n_verts == 3:
                    _append_triangle(
                        tri_v0, tri_v1, tri_v2, tri_normals, tri_faces,
                        f_verts[0], f_verts[1], f_verts[2], f_norm, face_counter,
                    )
                elif n_verts == 4:
                    _append_triangle(
                        tri_v0, tri_v1, tri_v2, tri_normals, tri_faces,
                        f_verts[0], f_verts[1], f_verts[2], f_norm, face_counter,
                    )
                    _append_triangle(
                        tri_v0, tri_v1, tri_v2, tri_normals, tri_faces,
                        f_verts[0], f_verts[2], f_verts[3], f_norm, face_counter,
                    )
                elif n_verts > 4:
                    for k in range(1, n_verts - 1):
                        _append_triangle(
                            tri_v0, tri_v1, tri_v2, tri_normals, tri_faces,
                            f_verts[0], f_verts[k], f_verts[k + 1], f_norm, face_counter,
                        )
                face_counter += 1
        elif isinstance(geo, Face3D):
            tri_mesh = geo.triangulated_mesh3d
            f_norm = geo.normal
            for f_verts in tri_mesh.face_vertices:
                if len(f_verts) >= 3:
                    _append_triangle(
                        tri_v0, tri_v1, tri_v2, tri_normals, tri_faces,
                        f_verts[0], f_verts[1], f_verts[2], f_norm, face_counter,
                    )
            face_counter += 1
        else:
            raise TypeError(f"Expected Face3D or Mesh3D; got {type(geo).__name__}.")

    if not tri_v0:
        return _empty_triangle_mesh(face_count=face_counter)

    v0 = np.asarray(tri_v0, dtype=np.float64)
    v1 = np.asarray(tri_v1, dtype=np.float64)
    v2 = np.asarray(tri_v2, dtype=np.float64)
    all_pts = np.vstack((v0, v1, v2))
    return TriangleMesh(
        v0=v0,
        e1=v1 - v0,
        e2=v2 - v0,
        normals=np.asarray(tri_normals, dtype=np.float64),
        face_indices=np.asarray(tri_faces, dtype=np.int32),
        face_count=face_counter,
        bbox_min=all_pts.min(axis=0),
        bbox_max=all_pts.max(axis=0),
    )


def _points_array(points: Iterable[Point3D]) -> np.ndarray:
    pts = [(float(p.x), float(p.y), float(p.z)) for p in points]
    if not pts:
        return np.empty((0, 3), dtype=np.float64)
    return np.asarray(pts, dtype=np.float64)


def _vectors_array(vectors: Iterable[Vector3D], *, normalize: bool = True) -> np.ndarray:
    vecs = [(float(v.x), float(v.y), float(v.z)) for v in vectors]
    if not vecs:
        return np.empty((0, 3), dtype=np.float64)
    arr = np.asarray(vecs, dtype=np.float64)
    if normalize:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        arr = arr / norms
    return arr


def _ray_tri_hits_chunk(
    origins: np.ndarray,
    directions: np.ndarray,
    tris: TriangleMesh,
    *,
    t_min: float = 1e-5,
    eps_det: float = 1e-9,
    eps_bary: float = 1e-7,
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized Möller–Trumbore ray-triangle test for a batch of rays."""
    b = origins.shape[0]
    m = tris.triangle_count
    if b == 0 or m == 0:
        return np.zeros((b, m), dtype=bool), np.full((b, m), np.inf, dtype=np.float64)

    # Broadcast shapes: origins (B, 1, 3), directions (B, 1, 3), tris (1, M, 3)
    d = directions[:, None, :]
    e1 = tris.e1[None, :, :]
    e2 = tris.e2[None, :, :]
    v0 = tris.v0[None, :, :]

    pvec = np.cross(d, e2)
    det = np.sum(e1 * pvec, axis=2)
    valid = np.abs(det) > eps_det
    inv_det = np.where(valid, 1.0 / np.where(valid, det, 1.0), 0.0)

    tvec = origins[:, None, :] - v0
    u = np.sum(tvec * pvec, axis=2) * inv_det
    valid &= (u >= -eps_bary) & (u <= 1.0 + eps_bary)

    qvec = np.cross(tvec, e1)
    v = np.sum(d * qvec, axis=2) * inv_det
    valid &= (v >= -eps_bary) & (u + v <= 1.0 + eps_bary)

    t = np.sum(e2 * qvec, axis=2) * inv_det
    valid &= t > t_min
    t = np.where(valid, t, np.inf)
    return valid, t


def _chunk_size_for_tris(tri_count: int) -> int:
    return max(1, min(2048, 200_000 // max(tri_count, 1)))


def intersect_mesh_rays(
    context_tris: TriangleMesh,
    points: list[Point3D],
    vectors: list[Vector3D],
    normals: list[Vector3D] | None = None,
    *,
    t_min: float = 1e-5,
) -> tuple[list[list[int]], list[list[float]] | None]:
    """Compute visibility matrix (1=clear, 0=blocked) and optional angle matrix."""
    n_pts = len(points)
    n_vecs = len(vectors)
    if n_pts == 0 or n_vecs == 0:
        return [[] for _ in range(n_pts)], ([[] for _ in range(n_pts)] if normals is not None else None)

    pts_arr = _points_array(points)
    vecs_arr = _vectors_array(vectors, normalize=True)

    angle_matrix: list[list[float]] | None = None
    cos_cutoff: np.ndarray | None = None
    if normals is not None:
        norms_arr = _vectors_array(normals, normalize=True)
        dots = np.clip(norms_arr @ vecs_arr.T, -1.0, 1.0)
        angles_arr = np.arccos(dots)
        angle_matrix = angles_arr.tolist()
        cos_cutoff = dots >= -1e-9  # angle <= pi / 2

    if context_tris.triangle_count == 0:
        if cos_cutoff is None:
            return [[1] * n_vecs for _ in range(n_pts)], None
        return cos_cutoff.astype(np.int8).tolist(), angle_matrix

    total_rays = n_pts * n_vecs
    ray_origins = np.repeat(pts_arr, n_vecs, axis=0)
    ray_dirs = np.tile(vecs_arr, (n_pts, 1))
    clear_flat = np.ones(total_rays, dtype=bool)
    if cos_cutoff is not None:
        clear_flat &= cos_cutoff.reshape(-1)

    active_idx = np.flatnonzero(clear_flat)
    chunk = _chunk_size_for_tris(context_tris.triangle_count)
    for start in range(0, len(active_idx), chunk):
        idx = active_idx[start : start + chunk]
        valid, _ = _ray_tri_hits_chunk(
            ray_origins[idx], ray_dirs[idx], context_tris, t_min=t_min
        )
        blocked = np.any(valid, axis=1)
        clear_flat[idx[blocked]] = False

    int_matrix = clear_flat.reshape(n_pts, n_vecs).astype(np.int8).tolist()
    return int_matrix, angle_matrix


def intersect_mesh_rays_distance(
    context_tris: TriangleMesh,
    point: Point3D,
    vectors: list[Vector3D],
    *,
    max_dist: float | None = None,
    t_min: float = 1e-5,
) -> list[float]:
    """Compute distance from ``point`` to closest hit in ``context_tris`` for each ray."""
    n_vecs = len(vectors)
    if n_vecs == 0:
        return []
    if context_tris.triangle_count == 0:
        return [float(max_dist) if max_dist is not None else -1.0] * n_vecs

    pt_arr = np.asarray([[float(point.x), float(point.y), float(point.z)]], dtype=np.float64)
    vecs_arr = _vectors_array(vectors, normalize=True)
    origins = np.repeat(pt_arr, n_vecs, axis=0)

    min_t = np.full(n_vecs, np.inf, dtype=np.float64)
    chunk = _chunk_size_for_tris(context_tris.triangle_count)
    for start in range(0, n_vecs, chunk):
        end = min(start + chunk, n_vecs)
        _, t_chunk = _ray_tri_hits_chunk(
            origins[start:end], vecs_arr[start:end], context_tris, t_min=t_min
        )
        min_t[start:end] = np.min(t_chunk, axis=1)

    if max_dist is None:
        return [float(v) if np.isfinite(v) else -1.0 for v in min_t]
    limit = float(max_dist)
    return [limit if (not np.isfinite(v) or v > limit) else float(v) for v in min_t]


def intersect_rays_with_mesh_faces(
    shade_tris: TriangleMesh,
    points: list[Point3D],
    vectors: list[Vector3D],
    *,
    context_tris: TriangleMesh | None = None,
    normals: list[Vector3D] | None = None,
    t_min: float = 1e-5,
) -> list[list[int]]:
    """Intersect study-point rays with ``shade_tris`` returning vector indices hit per face."""
    face_int: list[list[int]] = [[] for _ in range(shade_tris.face_count)]
    n_pts = len(points)
    n_vecs = len(vectors)
    if n_pts == 0 or n_vecs == 0 or shade_tris.triangle_count == 0 or shade_tris.face_count == 0:
        return face_int

    pts_arr = _points_array(points)
    vecs_arr = _vectors_array(vectors, normalize=True)

    active = np.ones((n_pts, n_vecs), dtype=bool)
    if normals is not None:
        norms_arr = _vectors_array(normals, normalize=True)
        active &= (norms_arr @ vecs_arr.T) >= -1e-9

    ray_origins = np.repeat(pts_arr, n_vecs, axis=0)
    ray_dirs = np.tile(vecs_arr, (n_pts, 1))
    vec_idx_flat = np.tile(np.arange(n_vecs, dtype=np.int32), n_pts)
    active_idx = np.flatnonzero(active.reshape(-1))

    if context_tris is not None and context_tris.triangle_count > 0 and len(active_idx) > 0:
        chunk_ctx = _chunk_size_for_tris(context_tris.triangle_count)
        keep_mask = np.ones(len(active_idx), dtype=bool)
        for start in range(0, len(active_idx), chunk_ctx):
            end = min(start + chunk_ctx, len(active_idx))
            idx = active_idx[start:end]
            valid_ctx, _ = _ray_tri_hits_chunk(
                ray_origins[idx], ray_dirs[idx], context_tris, t_min=t_min
            )
            keep_mask[start:end] = ~np.any(valid_ctx, axis=1)
        active_idx = active_idx[keep_mask]

    if len(active_idx) == 0:
        return face_int

    chunk_shade = _chunk_size_for_tris(shade_tris.triangle_count)
    for start in range(0, len(active_idx), chunk_shade):
        end = min(start + chunk_shade, len(active_idx))
        idx = active_idx[start:end]
        valid, t = _ray_tri_hits_chunk(
            ray_origins[idx], ray_dirs[idx], shade_tris, t_min=t_min
        )
        # Note: matches Rhino MeshRay(mesh, ray, face_ids) returning the closest hit face
        any_hit = np.any(valid, axis=1)
        if not np.any(any_hit):
            continue
        hit_rows = np.flatnonzero(any_hit)
        best_tri = np.argmin(t[hit_rows], axis=1)
        best_faces = shade_tris.face_indices[best_tri]
        hit_vecs = vec_idx_flat[idx[hit_rows]]
        for face_id, vec_id in zip(best_faces.tolist(), hit_vecs.tolist()):
            face_int[face_id].append(int(vec_id))

    return face_int


def trace_ray_bounces(
    all_tris: TriangleMesh,
    origin: Point3D,
    direction: Vector3D,
    *,
    max_hits: int,
    last_length: float,
    t_min: float = 1e-4,
) -> tuple[list[Point3D], list[Point3D]]:
    """Trace specular sun-ray bounces through ``all_tris``."""
    if all_tris.triangle_count == 0 or max_hits <= 0:
        return [], []

    curr_o = np.asarray([[float(origin.x), float(origin.y), float(origin.z)]], dtype=np.float64)
    d_raw = np.asarray([[float(direction.x), float(direction.y), float(direction.z)]], dtype=np.float64)
    d_norm = np.linalg.norm(d_raw)
    if d_norm == 0.0:
        return [], []
    curr_d = d_raw / d_norm

    all_pts: list[Point3D] = [Point3D(float(curr_o[0, 0]), float(curr_o[0, 1]), float(curr_o[0, 2]))]
    hit_pts: list[Point3D] = []
    escaped = False

    for _ in range(max_hits):
        valid, t = _ray_tri_hits_chunk(curr_o, curr_d, all_tris, t_min=t_min)
        if not np.any(valid):
            escaped = True
            break
        tri_idx = int(np.argmin(t[0]))
        hit_dist = float(t[0, tri_idx])
        p_hit = curr_o[0] + hit_dist * curr_d[0]
        pt_obj = Point3D(float(p_hit[0]), float(p_hit[1]), float(p_hit[2]))
        all_pts.append(pt_obj)
        hit_pts.append(pt_obj)

        n = all_tris.normals[tri_idx].copy()
        n_norm = np.linalg.norm(n)
        if n_norm == 0.0:
            break
        n /= n_norm
        if float(np.dot(curr_d[0], n)) > 0.0:
            n = -n
        d_ref = curr_d[0] - 2.0 * float(np.dot(curr_d[0], n)) * n
        ref_norm = np.linalg.norm(d_ref)
        if ref_norm == 0.0:
            break
        d_ref /= ref_norm
        curr_d = d_ref.reshape(1, 3)
        curr_o = (p_hit + d_ref * t_min).reshape(1, 3)

    if not hit_pts:
        return [], []

    if escaped or len(hit_pts) < max_hits:
        p_last = curr_o[0] - curr_d[0] * t_min + curr_d[0] * float(last_length)
        all_pts.append(Point3D(float(p_last[0]), float(p_last[1]), float(p_last[2])))

    return all_pts, hit_pts


def _human_height_points(position: Point3D, height: float, pt_count: int) -> list[Point3D]:
    feet_pt = position.move(Vector3D(0.0, 0.0, height / 100.0))
    hum_line = LineSegment3D(feet_pt, Vector3D(0.0, 0.0, height))
    if pt_count <= 1:
        return [hum_line.midpoint]
    pts = list(hum_line.subdivide_evenly(pt_count - 1))
    if len(pts) < pt_count:
        pts.append(feet_pt.move(Vector3D(0.0, 0.0, height)))
    return pts


def compute_human_to_sky_relation(
    *,
    location: Location,
    human_position: Point3D,
    context_geometries: list[Face3D | Mesh3D],
    north_angle: float = 0.0,
    height: float = 1.8,
    point_count: int = 1,
) -> tuple[HourlyContinuousCollection, float]:
    """Compute annual ``fraction_body_exposed`` and scalar ``sky_exposure`` without Rhino."""
    pt_count = max(1, int(point_count))
    human_pts = _human_height_points(human_position, float(height), pt_count)
    ctx_tris = triangulate_geometry(context_geometries)

    sp = Sunpath.from_location(location, north_angle=north_angle)
    sun_vecs: list[Vector3D] = []
    day_pattern: list[bool] = []
    for hoy in range(8760):
        sun = sp.calculate_sun_from_hoy(hoy)
        day_pattern.append(bool(sun.is_during_day))
        if sun.is_during_day:
            sun_vecs.append(sun.sun_vector_reversed)

    sun_int_mtx, _ = intersect_mesh_rays(ctx_tris, human_pts, sun_vecs)
    if sun_vecs:
        fract_per_sun = [
            sum(col_vals) / len(human_pts) for col_vals in zip(*sun_int_mtx)
        ]
    else:
        fract_per_sun = []

    fract_vals: list[float] = []
    sun_idx = 0
    for is_day in day_pattern:
        if is_day:
            fract_vals.append(float(fract_per_sun[sun_idx]))
            sun_idx += 1
        else:
            fract_vals.append(0.0)

    hdr = Header(
        Fraction(),
        "fraction",
        AnalysisPeriod(),
        {"type": "Fraction of Body Exposed to Direct Sun"},
    )
    fract_collection = HourlyContinuousCollection(hdr, fract_vals)

    sky_vecs = list(view_sphere.tregenza_dome_vectors)
    patch_weights = list(view_sphere.dome_patch_weights(1))
    sky_int_mtx, _ = intersect_mesh_rays(ctx_tris, human_pts, sky_vecs)
    n_patches = len(sky_vecs)
    sky_exp_per_pt = [
        sum((r * w) / n_patches for r, w in zip(row, patch_weights))
        for row in sky_int_mtx
    ]
    sky_exposure = max(0.0, min(1.0, sum(sky_exp_per_pt) / len(human_pts)))
    return fract_collection, float(sky_exposure)


__all__ = [
    "TriangleMesh",
    "compute_human_to_sky_relation",
    "intersect_mesh_rays",
    "intersect_mesh_rays_distance",
    "intersect_rays_with_mesh_faces",
    "trace_ray_bounces",
    "triangulate_geometry",
]
