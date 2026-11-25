//! Local-plane `Face3D` triangulation, hole-punching, edge extraction, and normal orientation.

use std::collections::HashSet;

use glam::{DVec2, DVec3};

use crate::types::{Bounds3, EdgeVertex, MeshVertex, ObjectKind};

/// Small geometric clearance (in meters) used to detect touching or crossing sub-face contours.
const TOUCH_EPSILON_M: f64 = 1e-5;
/// Maximum allowed distance (in meters) from a sub-face vertex to the host face's plane.
const COPLANAR_TOLERANCE_M: f64 = 0.02;
/// Offset distance (in meters) applied along the host normal when punched triangulation falls back.
pub const SUBFACE_FALLBACK_NORMAL_OFFSET_M: f64 = 0.003;

/// Optional plane metadata attached to a Honeybee `Face3D`.
#[derive(Clone, Copy, Debug)]
pub struct PlaneInput {
    pub origin: DVec3,
    pub normal: DVec3,
    pub x_axis: Option<DVec3>,
}

/// Orthonormal right-handed 2D basis (`u_axis x v_axis = normal`) for a planar `Face3D`.
#[derive(Clone, Copy, Debug)]
pub struct LocalBasis {
    pub origin: DVec3,
    pub u_axis: DVec3,
    pub v_axis: DVec3,
    pub normal: DVec3,
}

impl LocalBasis {
    /// Project a 3D point onto the local 2D `(u, v)` plane.
    #[inline]
    pub fn project(&self, p: DVec3) -> DVec2 {
        let d = p - self.origin;
        DVec2::new(d.dot(self.u_axis), d.dot(self.v_axis))
    }

    /// Signed perpendicular distance from a 3D point to this plane.
    #[inline]
    pub fn signed_distance(&self, p: DVec3) -> f64 {
        (p - self.origin).dot(self.normal)
    }
}

/// Output of triangulating a single `Face3D` (or polygonal mesh face).
#[derive(Clone, Debug)]
pub struct TriangulatedGeometry {
    pub vertices: Vec<MeshVertex>,
    pub indices: Vec<u32>,
    pub edge_loops: Vec<Vec<[f32; 3]>>,
    pub normal: [f32; 3],
    pub area: f64,
    pub centroid: [f32; 3],
    pub bounds: Bounds3,
}

impl TriangulatedGeometry {
    fn empty(normal: [f32; 3]) -> Self {
        Self {
            vertices: Vec::new(),
            indices: Vec::new(),
            edge_loops: Vec::new(),
            normal,
            area: 0.0,
            centroid: [0.0, 0.0, 0.0],
            bounds: Bounds3::empty(),
        }
    }
}

/// Result of triangulating a host `Face` along with its hole-punching decision for sub-faces.
#[derive(Clone, Debug)]
pub struct HostTriangulation {
    pub geometry: TriangulatedGeometry,
    /// Gross face area (outer boundary minus explicit `Face3D.holes`, before sub-face punching).
    pub gross_area: f64,
    /// True when child apertures/doors were successfully punched out of the host face.
    pub punched_subfaces: bool,
    /// Normal offset (`0.0` when punched, `0.003`m on fallback) for child apertures/doors.
    pub subface_offset_m: f64,
}

/// Classify a 3D surface normal into `"N"`, `"NE"`, `"E"`, `"SE"`, `"S"`, `"SW"`, `"W"`, `"NW"`,
/// `"horizontal_up"`, or `"horizontal_down"`, matching `garden.honeybee_core.search`.
pub fn orientation_label(normal: [f32; 3]) -> &'static str {
    const SECTORS: [&str; 8] = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    let nx = f64::from(normal[0]);
    let ny = f64::from(normal[1]);
    let nz = f64::from(normal[2]);
    let mag = (nx * nx + ny * ny + nz * nz).sqrt();
    if !mag.is_finite() || mag <= 1e-12 {
        return "horizontal_up";
    }
    let nx = nx / mag;
    let ny = ny / mag;
    let nz = nz / mag;
    if nz >= 0.7 {
        return "horizontal_up";
    }
    if nz <= -0.7 {
        return "horizontal_down";
    }
    let azimuth_deg = nx.atan2(ny).to_degrees().rem_euclid(360.0);
    let idx = (((azimuth_deg + 22.5) % 360.0) / 45.0).floor() as usize % 8;
    SECTORS[idx]
}

/// Infer Honeybee `face_type` from a surface normal when omitted in JSON.
pub fn infer_face_type_from_normal(normal: [f32; 3]) -> &'static str {
    let n = DVec3::new(f64::from(normal[0]), f64::from(normal[1]), f64::from(normal[2]));
    let len = n.length();
    if !len.is_finite() || len <= 1e-12 {
        return "Wall";
    }
    let nz = (n.z / len).clamp(-1.0, 1.0);
    let angle_deg = nz.acos().to_degrees();
    if angle_deg < 60.0 {
        "RoofCeiling"
    } else if angle_deg < 130.0 {
        "Wall"
    } else {
        "Floor"
    }
}

/// Clean a 3D loop by rejecting non-finite points and collapsing duplicate/closing vertices.
pub fn clean_loop_3d(points: &[DVec3]) -> Option<Vec<DVec3>> {
    if points.len() < 3 {
        return None;
    }
    let mut cleaned: Vec<DVec3> = Vec::with_capacity(points.len());
    for &pt in points {
        if !pt.is_finite() {
            return None;
        }
        if let Some(&prev) = cleaned.last() {
            if prev.distance_squared(pt) < 1e-16 {
                continue;
            }
        }
        cleaned.push(pt);
    }
    if cleaned.len() >= 2 && cleaned[0].distance_squared(*cleaned.last().unwrap()) < 1e-16 {
        cleaned.pop();
    }
    if cleaned.len() < 3 {
        None
    } else {
        Some(cleaned)
    }
}

/// Compute Newell's polygon normal for a possibly non-convex 3D vertex ring.
pub fn newell_normal(points: &[DVec3]) -> DVec3 {
    let mut n = DVec3::ZERO;
    let count = points.len();
    for i in 0..count {
        let a = points[i];
        let b = points[(i + 1) % count];
        n.x += (a.y - b.y) * (a.z + b.z);
        n.y += (a.z - b.z) * (a.x + b.x);
        n.z += (a.x - b.x) * (a.y + b.y);
    }
    n
}

fn default_u_axis(normal: DVec3) -> DVec3 {
    if normal.x.abs() < 1e-12 && normal.y.abs() < 1e-12 {
        DVec3::X
    } else {
        DVec3::new(normal.y, -normal.x, 0.0).normalize()
    }
}

/// Build an orthonormal local 2D basis from optional `Plane` metadata or Newell fallback.
pub fn build_local_basis(boundary: &[DVec3], plane: Option<PlaneInput>) -> Option<LocalBasis> {
    if boundary.len() < 3 {
        return None;
    }
    let newell = newell_normal(boundary);
    if let Some(p) = plane {
        if p.normal.is_finite() && p.normal.length_squared() > 1e-18 {
            let normal = p.normal.normalize();
            let origin = if p.origin.is_finite() {
                p.origin
            } else {
                boundary[0]
            };
            let u_axis = match p.x_axis {
                Some(x) if x.is_finite() => {
                    let projected = x - normal * x.dot(normal);
                    if projected.length_squared() > 1e-12 {
                        projected.normalize()
                    } else {
                        default_u_axis(normal)
                    }
                }
                _ => default_u_axis(normal),
            };
            let v_axis = normal.cross(u_axis).normalize();
            if v_axis.is_finite() && v_axis.length_squared() > 0.5 {
                return Some(LocalBasis {
                    origin,
                    u_axis,
                    v_axis,
                    normal,
                });
            }
        }
    }

    if !newell.is_finite() || newell.length_squared() <= 1e-20 {
        return None;
    }
    let normal = newell.normalize();
    let u_axis = default_u_axis(normal);
    let v_axis = normal.cross(u_axis).normalize();
    Some(LocalBasis {
        origin: boundary[0],
        u_axis,
        v_axis,
        normal,
    })
}

fn signed_area_2d(poly: &[DVec2]) -> f64 {
    let n = poly.len();
    if n < 3 {
        return 0.0;
    }
    let mut sum = 0.0;
    for i in 0..n {
        let a = poly[i];
        let b = poly[(i + 1) % n];
        sum += a.x * b.y - b.x * a.y;
    }
    0.5 * sum
}

fn point_in_polygon_2d(pt: DVec2, poly: &[DVec2]) -> bool {
    let mut inside = false;
    let n = poly.len();
    for i in 0..n {
        let a = poly[i];
        let b = poly[(i + 1) % n];
        let intersects = ((a.y > pt.y) != (b.y > pt.y))
            && (pt.x < (b.x - a.x) * (pt.y - a.y) / (b.y - a.y) + a.x);
        if intersects {
            inside = !inside;
        }
    }
    inside
}

fn point_to_segment_distance_sq_2d(p: DVec2, a: DVec2, b: DVec2) -> f64 {
    let ab = b - a;
    let len_sq = ab.length_squared();
    if len_sq <= 1e-24 {
        return p.distance_squared(a);
    }
    let t = ((p - a).dot(ab) / len_sq).clamp(0.0, 1.0);
    let proj = a + ab * t;
    p.distance_squared(proj)
}

fn orient_2d(a: DVec2, b: DVec2, c: DVec2) -> f64 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn on_segment_bbox(a: DVec2, b: DVec2, p: DVec2, eps: f64) -> bool {
    p.x >= a.x.min(b.x) - eps
        && p.x <= a.x.max(b.x) + eps
        && p.y >= a.y.min(b.y) - eps
        && p.y <= a.y.max(b.y) + eps
}

fn segment_distance_sq_2d(a1: DVec2, a2: DVec2, b1: DVec2, b2: DVec2) -> f64 {
    // Check proper / collinear intersection first so distance is exact 0.0 on crossings.
    let o1 = orient_2d(a1, a2, b1);
    let o2 = orient_2d(a1, a2, b2);
    let o3 = orient_2d(b1, b2, a1);
    let o4 = orient_2d(b1, b2, a2);
    if (o1 * o2 < 0.0 && o3 * o4 < 0.0)
        || (o1.abs() <= 1e-12 && on_segment_bbox(a1, a2, b1, 1e-12))
        || (o2.abs() <= 1e-12 && on_segment_bbox(a1, a2, b2, 1e-12))
        || (o3.abs() <= 1e-12 && on_segment_bbox(b1, b2, a1, 1e-12))
        || (o4.abs() <= 1e-12 && on_segment_bbox(b1, b2, a2, 1e-12))
    {
        return 0.0;
    }

    point_to_segment_distance_sq_2d(a1, b1, b2)
        .min(point_to_segment_distance_sq_2d(a2, b1, b2))
        .min(point_to_segment_distance_sq_2d(b1, a1, a2))
        .min(point_to_segment_distance_sq_2d(b2, a1, a2))
}

fn loops_touch_or_intersect_2d(a: &[DVec2], b: &[DVec2], eps: f64) -> bool {
    let eps_sq = eps * eps;
    for i in 0..a.len() {
        let a1 = a[i];
        let a2 = a[(i + 1) % a.len()];
        let min_ax = a1.x.min(a2.x) - eps;
        let max_ax = a1.x.max(a2.x) + eps;
        let min_ay = a1.y.min(a2.y) - eps;
        let max_ay = a1.y.max(a2.y) + eps;
        for j in 0..b.len() {
            let b1 = b[j];
            let b2 = b[(j + 1) % b.len()];
            if b1.x.max(b2.x) < min_ax
                || b1.x.min(b2.x) > max_ax
                || b1.y.max(b2.y) < min_ay
                || b1.y.min(b2.y) > max_ay
            {
                continue;
            }
            if segment_distance_sq_2d(a1, a2, b1, b2) <= eps_sq {
                return true;
            }
        }
    }
    false
}

/// Return `true` if `inner` lies strictly inside `outer` without touching or crossing any edge.
fn loop_strictly_inside_2d(inner: &[DVec2], outer: &[DVec2], eps: f64) -> bool {
    if inner.len() < 3 || outer.len() < 3 {
        return false;
    }
    if loops_touch_or_intersect_2d(inner, outer, eps) {
        return false;
    }
    if !inner.iter().all(|&pt| point_in_polygon_2d(pt, outer)) {
        return false;
    }
    if outer.iter().any(|&pt| point_in_polygon_2d(pt, inner)) {
        return false;
    }
    true
}

/// Return `true` if `a` and `b` are strictly disjoint (neither inside nor touching the other).
fn loops_strictly_disjoint_2d(a: &[DVec2], b: &[DVec2], eps: f64) -> bool {
    if loops_touch_or_intersect_2d(a, b, eps) {
        return false;
    }
    if a.iter().any(|&pt| point_in_polygon_2d(pt, b)) {
        return false;
    }
    if b.iter().any(|&pt| point_in_polygon_2d(pt, a)) {
        return false;
    }
    true
}

fn to_f32_3(v: DVec3) -> [f32; 3] {
    [v.x as f32, v.y as f32, v.z as f32]
}

/// Attempt `earcutr::earcut` on `outer_3d` with `holes_3d` projected onto `basis`.
///
/// Validates containment, pairwise hole disjointness, non-empty finite indices, consistent
/// triangle winding against `basis.normal`, and area conservation (`outer - sum(holes)`).
fn try_triangulate_earcut(
    basis: &LocalBasis,
    outer_3d: &[DVec3],
    holes_3d: &[Vec<DVec3>],
    object_id: u32,
    kind: ObjectKind,
    explicit_hole_count: usize,
) -> Option<TriangulatedGeometry> {
    let outer_2d: Vec<DVec2> = outer_3d.iter().map(|&p| basis.project(p)).collect();
    let outer_signed_area = signed_area_2d(&outer_2d);
    let outer_area = outer_signed_area.abs();
    if !outer_area.is_finite() || outer_area <= 1e-8 {
        return None;
    }

    let mut holes_2d: Vec<Vec<DVec2>> = Vec::with_capacity(holes_3d.len());
    let mut holes_area_sum = 0.0_f64;

    for hole in holes_3d {
        if hole.len() < 3 {
            return None;
        }
        // Reject holes that deviate from the host plane.
        if hole
            .iter()
            .any(|&p| basis.signed_distance(p).abs() > COPLANAR_TOLERANCE_M)
        {
            return None;
        }
        let h2: Vec<DVec2> = hole.iter().map(|&p| basis.project(p)).collect();
        let h_area = signed_area_2d(&h2).abs();
        if !h_area.is_finite() || h_area <= 1e-8 {
            return None;
        }
        if !loop_strictly_inside_2d(&h2, &outer_2d, TOUCH_EPSILON_M) {
            return None;
        }
        for prev in &holes_2d {
            if !loops_strictly_disjoint_2d(&h2, prev, TOUCH_EPSILON_M) {
                return None;
            }
        }
        holes_area_sum += h_area;
        holes_2d.push(h2);
    }

    let expected_area = outer_area - holes_area_sum;
    if expected_area <= 1e-7 {
        return None;
    }

    let total_verts = outer_3d.len() + holes_3d.iter().map(Vec::len).sum::<usize>();
    let mut coords_2d: Vec<f64> = Vec::with_capacity(total_verts * 2);
    let mut verts_3d: Vec<DVec3> = Vec::with_capacity(total_verts);
    let mut verts_2d: Vec<DVec2> = Vec::with_capacity(total_verts);
    let mut hole_indices: Vec<usize> = Vec::with_capacity(holes_3d.len());

    // Normalize 2D ring winding for earcutr (outer CCW, holes CW) while keeping 3D positions paired.
    if outer_signed_area >= 0.0 {
        for (p3, p2) in outer_3d.iter().zip(outer_2d.iter()) {
            coords_2d.push(p2.x);
            coords_2d.push(p2.y);
            verts_3d.push(*p3);
            verts_2d.push(*p2);
        }
    } else {
        for (p3, p2) in outer_3d.iter().rev().zip(outer_2d.iter().rev()) {
            coords_2d.push(p2.x);
            coords_2d.push(p2.y);
            verts_3d.push(*p3);
            verts_2d.push(*p2);
        }
    }

    for (h3, h2) in holes_3d.iter().zip(holes_2d.iter()) {
        hole_indices.push(verts_3d.len());
        let h_signed = signed_area_2d(h2);
        if h_signed <= 0.0 {
            for (p3, p2) in h3.iter().zip(h2.iter()) {
                coords_2d.push(p2.x);
                coords_2d.push(p2.y);
                verts_3d.push(*p3);
                verts_2d.push(*p2);
            }
        } else {
            for (p3, p2) in h3.iter().rev().zip(h2.iter().rev()) {
                coords_2d.push(p2.x);
                coords_2d.push(p2.y);
                verts_3d.push(*p3);
                verts_2d.push(*p2);
            }
        }
    }

    let raw_indices = earcutr::earcut(&coords_2d, &hole_indices, 2).ok()?;
    if raw_indices.is_empty() || raw_indices.len() % 3 != 0 {
        return None;
    }

    let mut checked_indices: Vec<u32> = Vec::with_capacity(raw_indices.len());
    let mut area_sum_2d = 0.0_f64;
    let mut area_sum_3d = 0.0_f64;
    let mut weighted_centroid = DVec3::ZERO;

    for tri in raw_indices.chunks_exact(3) {
        let (ia, ib, ic) = (tri[0], tri[1], tri[2]);
        if ia >= verts_3d.len() || ib >= verts_3d.len() || ic >= verts_3d.len() {
            return None;
        }
        let a2 = verts_2d[ia];
        let b2 = verts_2d[ib];
        let c2 = verts_2d[ic];
        let signed_tri_2d = 0.5 * orient_2d(a2, b2, c2);
        if !signed_tri_2d.is_finite() {
            return None;
        }

        // In punched faces, an inverted triangle signals bridge/intersection corruption -> reject.
        if !holes_3d.is_empty() && signed_tri_2d < -1e-7 {
            return None;
        }
        if signed_tri_2d.abs() <= 1e-12 {
            continue;
        }

        let (p0, mut p1, mut p2) = (verts_3d[ia], verts_3d[ib], verts_3d[ic]);
        let mut out_tri = [ia as u32, ib as u32, ic as u32];
        let cross3 = (p1 - p0).cross(p2 - p0);
        if cross3.dot(basis.normal) < 0.0 {
            out_tri.swap(1, 2);
            std::mem::swap(&mut p1, &mut p2);
        }

        let tri_area_3d = 0.5 * (p1 - p0).cross(p2 - p0).length();
        if !tri_area_3d.is_finite() {
            return None;
        }

        area_sum_2d += signed_tri_2d.abs();
        area_sum_3d += tri_area_3d;
        weighted_centroid += ((p0 + p1 + p2) / 3.0) * tri_area_3d;
        checked_indices.extend_from_slice(&out_tri);
    }

    if checked_indices.is_empty() {
        return None;
    }

    let area_tol = (1e-4_f64).max(2e-3 * expected_area);
    if (area_sum_2d - expected_area).abs() > area_tol {
        return None;
    }

    let normal_f32 = to_f32_3(basis.normal);
    let kind_code = kind.kind_code();
    let mut bounds = Bounds3::empty();
    let mut vertices = Vec::with_capacity(verts_3d.len());
    for &p in &verts_3d {
        let pos = to_f32_3(p);
        if !pos[0].is_finite() || !pos[1].is_finite() || !pos[2].is_finite() {
            return None;
        }
        bounds.expand_point(pos);
        vertices.push(MeshVertex {
            position: pos,
            normal: normal_f32,
            object_id,
            kind_code,
        });
    }

    let centroid = if area_sum_3d > 1e-12 {
        to_f32_3(weighted_centroid / area_sum_3d)
    } else {
        bounds.center()
    };

    let mut edge_loops = Vec::with_capacity(1 + explicit_hole_count);
    edge_loops.push(outer_3d.iter().copied().map(to_f32_3).collect());
    for h in holes_3d.iter().take(explicit_hole_count) {
        edge_loops.push(h.iter().copied().map(to_f32_3).collect());
    }

    Some(TriangulatedGeometry {
        vertices,
        indices: checked_indices,
        edge_loops,
        normal: normal_f32,
        area: area_sum_3d,
        centroid,
        bounds,
    })
}

/// Fallback triangulation for an unpunched simple boundary (if earcut rejects a slightly pinched
/// self-touching polygon), preserving consistent winding and never panicking.
fn triangulate_outer_only_best_effort(
    basis: &LocalBasis,
    outer_3d: &[DVec3],
    object_id: u32,
    kind: ObjectKind,
) -> TriangulatedGeometry {
    if let Some(tri) = try_triangulate_earcut(basis, outer_3d, &[], object_id, kind, 0) {
        return tri;
    }

    let outer_2d: Vec<DVec2> = outer_3d.iter().map(|&p| basis.project(p)).collect();
    let mut coords_2d: Vec<f64> = Vec::with_capacity(outer_2d.len() * 2);
    for p2 in &outer_2d {
        coords_2d.push(p2.x);
        coords_2d.push(p2.y);
    }

    let normal_f32 = to_f32_3(basis.normal);
    let kind_code = kind.kind_code();
    let mut bounds = Bounds3::empty();
    let mut vertices = Vec::with_capacity(outer_3d.len());
    for &p in outer_3d {
        let pos = to_f32_3(p);
        bounds.expand_point(pos);
        vertices.push(MeshVertex {
            position: pos,
            normal: normal_f32,
            object_id,
            kind_code,
        });
    }

    let mut indices = Vec::new();
    let mut area_sum = 0.0_f64;
    let mut weighted_centroid = DVec3::ZERO;

    if let Ok(raw) = earcutr::earcut(&coords_2d, &[], 2) {
        for tri in raw.chunks_exact(3) {
            let (ia, ib, ic) = (tri[0], tri[1], tri[2]);
            if ia >= outer_3d.len() || ib >= outer_3d.len() || ic >= outer_3d.len() {
                continue;
            }
            let (p0, mut p1, mut p2) = (outer_3d[ia], outer_3d[ib], outer_3d[ic]);
            let mut out = [ia as u32, ib as u32, ic as u32];
            if (p1 - p0).cross(p2 - p0).dot(basis.normal) < 0.0 {
                out.swap(1, 2);
                std::mem::swap(&mut p1, &mut p2);
            }
            let a = 0.5 * (p1 - p0).cross(p2 - p0).length();
            if a.is_finite() && a > 1e-12 {
                area_sum += a;
                weighted_centroid += ((p0 + p1 + p2) / 3.0) * a;
                indices.extend_from_slice(&out);
            }
        }
    }

    let centroid = if area_sum > 1e-12 {
        to_f32_3(weighted_centroid / area_sum)
    } else {
        bounds.center()
    };

    TriangulatedGeometry {
        vertices,
        indices,
        edge_loops: vec![outer_3d.iter().copied().map(to_f32_3).collect()],
        normal: normal_f32,
        area: area_sum,
        centroid,
        bounds,
    }
}

/// Triangulate a standalone `Face3D` (for apertures, doors, shades, or mesh polygons).
pub fn triangulate_face3d(
    boundary: &[DVec3],
    holes: &[Vec<DVec3>],
    plane: Option<PlaneInput>,
    object_id: u32,
    kind: ObjectKind,
) -> TriangulatedGeometry {
    let Some(clean_outer) = clean_loop_3d(boundary) else {
        return TriangulatedGeometry::empty([0.0, 0.0, 1.0]);
    };
    let Some(basis) = build_local_basis(&clean_outer, plane) else {
        return TriangulatedGeometry::empty([0.0, 0.0, 1.0]);
    };
    let clean_holes: Vec<Vec<DVec3>> = holes
        .iter()
        .filter_map(|h| clean_loop_3d(h))
        .collect();

    if !clean_holes.is_empty() {
        if let Some(punched) = try_triangulate_earcut(
            &basis,
            &clean_outer,
            &clean_holes,
            object_id,
            kind,
            clean_holes.len(),
        ) {
            return punched;
        }
    }

    triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, kind)
}

/// Triangulate a host `Face` along with its explicit `Face3D.holes` and child `subface_loops`
/// (apertures + doors).
///
/// If punching all holes + sub-faces passes geometric validation, returns the punched host face
/// with `subface_offset_m = 0.0`. Otherwise falls back cleanly to the unpunched host face (still
/// honoring valid explicit `Face3D.holes`) and requests a `0.003`m offset along the host normal
/// for child apertures and doors.
pub fn triangulate_host_face(
    boundary: &[DVec3],
    explicit_holes: &[Vec<DVec3>],
    subface_loops: &[Vec<DVec3>],
    plane: Option<PlaneInput>,
    object_id: u32,
) -> HostTriangulation {
    let Some(clean_outer) = clean_loop_3d(boundary) else {
        return HostTriangulation {
            geometry: TriangulatedGeometry::empty([0.0, 0.0, 1.0]),
            gross_area: 0.0,
            punched_subfaces: false,
            subface_offset_m: 0.0,
        };
    };
    let Some(basis) = build_local_basis(&clean_outer, plane) else {
        return HostTriangulation {
            geometry: TriangulatedGeometry::empty([0.0, 0.0, 1.0]),
            gross_area: 0.0,
            punched_subfaces: false,
            subface_offset_m: 0.0,
        };
    };

    let clean_explicit: Vec<Vec<DVec3>> = explicit_holes
        .iter()
        .filter_map(|h| clean_loop_3d(h))
        .collect();
    let explicit_count = clean_explicit.len();

    let outer_2d: Vec<DVec2> = clean_outer.iter().map(|&p| basis.project(p)).collect();
    let outer_area = signed_area_2d(&outer_2d).abs();
    let explicit_holes_area: f64 = clean_explicit
        .iter()
        .map(|h| {
            let h2: Vec<DVec2> = h.iter().map(|&p| basis.project(p)).collect();
            signed_area_2d(&h2).abs()
        })
        .sum();
    let gross_area = (outer_area - explicit_holes_area).max(0.0);

    if !subface_loops.is_empty() {
        let mut clean_subfaces = Vec::with_capacity(subface_loops.len());
        let mut all_clean = true;
        for sf in subface_loops {
            if let Some(cleaned) = clean_loop_3d(sf) {
                clean_subfaces.push(cleaned);
            } else {
                all_clean = false;
                break;
            }
        }

        if all_clean {
            let mut combined_holes = clean_explicit.clone();
            combined_holes.extend(clean_subfaces);
            if let Some(punched) = try_triangulate_earcut(
                &basis,
                &clean_outer,
                &combined_holes,
                object_id,
                ObjectKind::Face,
                explicit_count,
            ) {
                return HostTriangulation {
                    geometry: punched,
                    gross_area,
                    punched_subfaces: true,
                    subface_offset_m: 0.0,
                };
            }
        }
    }

    // Fallback: unpunched host face (preserving explicit Face3D holes when valid) + 0.003m offset.
    let host_geom = if !clean_explicit.is_empty() {
        try_triangulate_earcut(
            &basis,
            &clean_outer,
            &clean_explicit,
            object_id,
            ObjectKind::Face,
            explicit_count,
        )
        .unwrap_or_else(|| triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, ObjectKind::Face))
    } else {
        triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, ObjectKind::Face)
    };

    HostTriangulation {
        geometry: host_geom,
        gross_area,
        punched_subfaces: false,
        subface_offset_m: if subface_loops.is_empty() {
            0.0
        } else {
            SUBFACE_FALLBACK_NORMAL_OFFSET_M
        },
    }
}

/// Shift all mesh vertices, edge loops, centroid, and bounds of a `TriangulatedGeometry`
/// along `offset` (used for child sub-face fallback).
pub fn offset_geometry(geom: &mut TriangulatedGeometry, offset: [f32; 3]) {
    if offset == [0.0, 0.0, 0.0] {
        return;
    }
    let mut new_bounds = Bounds3::empty();
    for v in &mut geom.vertices {
        v.position[0] += offset[0];
        v.position[1] += offset[1];
        v.position[2] += offset[2];
        new_bounds.expand_point(v.position);
    }
    for loop_pts in &mut geom.edge_loops {
        for p in loop_pts {
            p[0] += offset[0];
            p[1] += offset[1];
            p[2] += offset[2];
        }
    }
    if new_bounds.is_valid() {
        geom.bounds = new_bounds;
    }
    geom.centroid[0] += offset[0];
    geom.centroid[1] += offset[1];
    geom.centroid[2] += offset[2];
}

#[derive(Copy, Clone, Eq, PartialEq, Hash, Ord, PartialOrd)]
struct QuantizedPoint([i64; 3]);

fn quantize_point(p: [f32; 3]) -> QuantizedPoint {
    // 0.01 mm quantization for undirected per-object edge deduplication.
    QuantizedPoint([
        (f64::from(p[0]) * 100_000.0).round() as i64,
        (f64::from(p[1]) * 100_000.0).round() as i64,
        (f64::from(p[2]) * 100_000.0).round() as i64,
    ])
}

/// Emit deduplicated wireframe `EdgeVertex` pairs (`PrimitiveTopology::LineList`) for an object's
/// boundary/hole loops.
pub fn append_deduplicated_edges(
    edge_loops: &[Vec<[f32; 3]>],
    object_id: u32,
    out_edges: &mut Vec<EdgeVertex>,
) {
    let mut seen: HashSet<(QuantizedPoint, QuantizedPoint)> = HashSet::new();
    for loop_pts in edge_loops {
        let len = loop_pts.len();
        if len < 2 {
            continue;
        }
        for i in 0..len {
            let a = loop_pts[i];
            let b = loop_pts[(i + 1) % len];
            let dx = b[0] - a[0];
            let dy = b[1] - a[1];
            let dz = b[2] - a[2];
            if dx * dx + dy * dy + dz * dz < 1e-12 {
                continue;
            }
            let qa = quantize_point(a);
            let qb = quantize_point(b);
            if qa == qb {
                continue;
            }
            let key = if qa <= qb { (qa, qb) } else { (qb, qa) };
            if seen.insert(key) {
                out_edges.push(EdgeVertex {
                    position: a,
                    object_id,
                });
                out_edges.push(EdgeVertex {
                    position: b,
                    object_id,
                });
            }
        }
    }
}
