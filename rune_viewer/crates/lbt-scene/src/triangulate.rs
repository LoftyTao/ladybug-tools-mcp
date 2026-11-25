//! Local-plane `Face3D` triangulation, hole-punching, edge extraction, and normal orientation.

use std::collections::{BTreeMap, HashSet};

use glam::{DVec2, DVec3};

use crate::types::{Bounds3, EdgeVertex, MeshVertex, ObjectKind};

/// Small geometric clearance (in meters) used to detect strictly touching or crossing contours
/// on the fast earcut path.
const TOUCH_EPSILON_M: f64 = 1e-5;
/// 2D vertex snapping and collinear-split tolerance (in meters) for touching/collinear punching.
const SNAP_EPS_2D_M: f64 = 1e-4;
/// Maximum allowed distance (in meters) from a sub-face vertex to the host face's plane.
pub const COPLANAR_TOLERANCE_M: f64 = 0.02;
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

    /// Reconstruct a 3D point on this plane from local 2D `(u, v)` coordinates.
    #[inline]
    pub fn unproject(&self, p: DVec2) -> DVec3 {
        self.origin + self.u_axis * p.x + self.v_axis * p.y
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
    /// Area centroid of the gross host face boundary (before sub-face punching), used for
    /// coincident duplicate face detection independent of aperture layout.
    pub gross_centroid: [f32; 3],
    /// Outer bounds of the host face before sub-face punching.
    pub gross_bounds: Bounds3,
    /// True when at least one child aperture/door was successfully punched out of the host face.
    pub punched_subfaces: bool,
    /// Summary normal offset (`0.0` when all subfaces punched, `0.003`m if any subface fell back).
    pub subface_offset_m: f64,
    /// Per-subface normal offset aligned with input `subface_loops` order.
    pub subface_offsets: Vec<f64>,
    /// Per-subface coplanarity flag aligned with input `subface_loops` order.
    pub subface_coplanar: Vec<bool>,
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
    let n = DVec3::new(
        f64::from(normal[0]),
        f64::from(normal[1]),
        f64::from(normal[2]),
    );
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
        if let Some(&prev) = cleaned.last()
            && prev.distance_squared(pt) < 1e-16
        {
            continue;
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
    if let Some(p) = plane
        && p.normal.is_finite()
        && p.normal.length_squared() > 1e-18
    {
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

fn polygon_centroid_2d(poly: &[DVec2]) -> Option<DVec2> {
    let area = signed_area_2d(poly);
    if !area.is_finite() || area.abs() <= 1e-12 {
        return None;
    }
    let mut cx = 0.0;
    let mut cy = 0.0;
    let n = poly.len();
    for i in 0..n {
        let a = poly[i];
        let b = poly[(i + 1) % n];
        let cross = a.x * b.y - b.x * a.y;
        cx += (a.x + b.x) * cross;
        cy += (a.y + b.y) * cross;
    }
    let factor = 1.0 / (6.0 * area);
    let c = DVec2::new(cx * factor, cy * factor);
    c.is_finite().then_some(c)
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

fn point_near_loop_boundary_2d(pt: DVec2, poly: &[DVec2], eps: f64) -> bool {
    let eps_sq = eps * eps;
    let n = poly.len();
    for i in 0..n {
        if point_to_segment_distance_sq_2d(pt, poly[i], poly[(i + 1) % n]) <= eps_sq {
            return true;
        }
    }
    false
}

fn point_in_or_on_polygon_2d(pt: DVec2, poly: &[DVec2], eps: f64) -> bool {
    point_near_loop_boundary_2d(pt, poly, eps) || point_in_polygon_2d(pt, poly)
}

fn point_strictly_inside_polygon_2d(pt: DVec2, poly: &[DVec2], eps: f64) -> bool {
    point_in_polygon_2d(pt, poly) && !point_near_loop_boundary_2d(pt, poly, eps)
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

/// True only when open segments `(a1, a2)` and `(b1, b2)` properly cross in their interiors
/// (endpoint touches and collinear edge overlaps return `false`).
fn segments_properly_cross_2d(a1: DVec2, a2: DVec2, b1: DVec2, b2: DVec2, eps: f64) -> bool {
    let eps_sq = eps * eps;
    if point_to_segment_distance_sq_2d(a1, b1, b2) <= eps_sq
        || point_to_segment_distance_sq_2d(a2, b1, b2) <= eps_sq
        || point_to_segment_distance_sq_2d(b1, a1, a2) <= eps_sq
        || point_to_segment_distance_sq_2d(b2, a1, a2) <= eps_sq
    {
        return false;
    }
    let o1 = orient_2d(a1, a2, b1);
    let o2 = orient_2d(a1, a2, b2);
    let o3 = orient_2d(b1, b2, a1);
    let o4 = orient_2d(b1, b2, a2);
    o1 * o2 < 0.0 && o3 * o4 < 0.0
}

fn loops_properly_cross_2d(a: &[DVec2], b: &[DVec2], eps: f64) -> bool {
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
            if segments_properly_cross_2d(a1, a2, b1, b2, eps) {
                return true;
            }
        }
    }
    false
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

fn normalize_ccw_2d(poly: &[DVec2]) -> Vec<DVec2> {
    if signed_area_2d(poly) >= 0.0 {
        poly.to_vec()
    } else {
        poly.iter().copied().rev().collect()
    }
}

/// Triangulate a simple 2D polygon and return centroids of all positive-area triangles
/// (used for reliable interior sampling of both convex and concave polygons).
fn interior_sample_points_2d(poly_ccw: &[DVec2]) -> Option<Vec<DVec2>> {
    if poly_ccw.len() < 3 {
        return None;
    }
    let mut coords = Vec::with_capacity(poly_ccw.len() * 2);
    for p in poly_ccw {
        coords.push(p.x);
        coords.push(p.y);
    }
    let raw = earcutr::earcut(&coords, &[], 2).ok()?;
    if raw.is_empty() || raw.len() % 3 != 0 {
        return None;
    }
    let mut samples = Vec::with_capacity(raw.len() / 3);
    for tri in raw.chunks_exact(3) {
        let (a, b, c) = (poly_ccw[tri[0]], poly_ccw[tri[1]], poly_ccw[tri[2]]);
        let area = 0.5 * orient_2d(a, b, c).abs();
        if area > 1e-10 {
            samples.push((a + b + c) / 3.0);
        }
    }
    if samples.is_empty() {
        None
    } else {
        Some(samples)
    }
}

/// Attempt `earcutr::earcut` on `outer_3d` with strictly-interior, strictly-disjoint `holes_3d`
/// projected onto `basis`.
///
/// Validates containment, pairwise hole disjointness, non-empty finite indices, consistent
/// triangle winding against `basis.normal`, zero triangles inside holes, and area conservation.
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

        if !holes_2d.is_empty() {
            let tri_c = (a2 + b2 + c2) / 3.0;
            if holes_2d
                .iter()
                .any(|h| point_strictly_inside_polygon_2d(tri_c, h, TOUCH_EPSILON_M))
            {
                return None;
            }
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

/// Exact 2D directed half-edge subtraction for host faces whose apertures/doors touch the host
/// outer boundary (e.g., bottom-touching doors), share edges with neighboring apertures/doors
/// (mullions / ribbon windows / T-junctions), split the host face into multiple regions, or cover
/// 100% of the host face.
///
/// Every emitted triangle is mathematically checked for positive orientation, conserved area,
/// containment inside `outer_2d`, and strict exclusion from every punched hole.
fn try_triangulate_half_edge_punched(
    basis: &LocalBasis,
    outer_3d: &[DVec3],
    explicit_holes_3d: &[Vec<DVec3>],
    punch_holes_2d_ccw: &[Vec<DVec2>],
    object_id: u32,
    kind: ObjectKind,
) -> Option<TriangulatedGeometry> {
    let outer_2d_raw: Vec<DVec2> = outer_3d.iter().map(|&p| basis.project(p)).collect();
    let outer_2d_ccw = normalize_ccw_2d(&outer_2d_raw);
    let outer_area = signed_area_2d(&outer_2d_ccw).abs();
    if !outer_area.is_finite() || outer_area <= 1e-8 {
        return None;
    }

    let holes_area_sum: f64 = punch_holes_2d_ccw
        .iter()
        .map(|h| signed_area_2d(h).abs())
        .sum();
    let expected_area = (outer_area - holes_area_sum).max(0.0);

    // 1. Pool all vertices with SNAP_EPS_2D_M merging so shared/touching endpoints unify.
    let mut pool: Vec<DVec2> = Vec::new();
    let mut intern = |p: DVec2| -> usize {
        let eps_sq = SNAP_EPS_2D_M * SNAP_EPS_2D_M;
        for (idx, &existing) in pool.iter().enumerate() {
            if existing.distance_squared(p) <= eps_sq {
                return idx;
            }
        }
        let idx = pool.len();
        pool.push(p);
        idx
    };

    // Build initial directed edges: outer CCW + every hole CW (interior always on left!).
    let mut raw_edges: Vec<(usize, usize)> = Vec::new();
    let push_ring = |ring: &[DVec2], edges: &mut Vec<(usize, usize)>, intern_fn: &mut dyn FnMut(DVec2) -> usize| {
        let ids: Vec<usize> = ring.iter().map(|&p| intern_fn(p)).collect();
        let n = ids.len();
        for i in 0..n {
            let u = ids[i];
            let v = ids[(i + 1) % n];
            if u != v {
                edges.push((u, v));
            }
        }
    };

    push_ring(&outer_2d_ccw, &mut raw_edges, &mut intern);
    for h_ccw in punch_holes_2d_ccw {
        let h_cw: Vec<DVec2> = h_ccw.iter().copied().rev().collect();
        push_ring(&h_cw, &mut raw_edges, &mut intern);
    }

    // 2. Split every directed segment at all collinear pooled vertices lying strictly inside it.
    let mut split_edges: Vec<(usize, usize)> = Vec::with_capacity(raw_edges.len() * 2);
    let mut splits: Vec<(f64, usize)> = Vec::new();
    for (u, v) in raw_edges {
        let a = pool[u];
        let b = pool[v];
        let ab = b - a;
        let len_sq = ab.length_squared();
        if len_sq <= (SNAP_EPS_2D_M * SNAP_EPS_2D_M) {
            continue;
        }
        let len = len_sq.sqrt();
        splits.clear();
        for (idx, &p) in pool.iter().enumerate() {
            if idx == u || idx == v {
                continue;
            }
            let ap = p - a;
            let t = ap.dot(ab) / len_sq;
            if t <= 0.0 || t >= 1.0 {
                continue;
            }
            let dist_along = t * len;
            if dist_along <= SNAP_EPS_2D_M || (len - dist_along) <= SNAP_EPS_2D_M {
                continue;
            }
            let proj = a + ab * t;
            if proj.distance_squared(p) <= SNAP_EPS_2D_M * SNAP_EPS_2D_M {
                splits.push((t, idx));
            }
        }
        if splits.is_empty() {
            split_edges.push((u, v));
        } else {
            splits.sort_by(|x, y| x.0.total_cmp(&y.0));
            let mut prev = u;
            for &(_, mid) in &splits {
                if mid != prev {
                    split_edges.push((prev, mid));
                    prev = mid;
                }
            }
            if prev != v {
                split_edges.push((prev, v));
            }
        }
    }

    // 3. Cancel opposite directed edge pairs (shared mullions & boundary-touching notches).
    let mut edge_counts: BTreeMap<(usize, usize), usize> = BTreeMap::new();
    for (u, v) in split_edges {
        if u == v {
            continue;
        }
        if let Some(rev_count) = edge_counts.get_mut(&(v, u)) {
            if *rev_count > 1 {
                *rev_count -= 1;
            } else {
                edge_counts.remove(&(v, u));
            }
        } else {
            *edge_counts.entry((u, v)).or_insert(0) += 1;
        }
    }

    // Prepare host wireframe loops (original outer + explicit Face3D holes).
    let mut edge_loops = Vec::with_capacity(1 + explicit_holes_3d.len());
    edge_loops.push(outer_3d.iter().copied().map(to_f32_3).collect());
    for h in explicit_holes_3d {
        edge_loops.push(h.iter().copied().map(to_f32_3).collect());
    }

    let mut outer_bounds = Bounds3::empty();
    for &p in outer_3d {
        outer_bounds.expand_point(to_f32_3(p));
    }
    let normal_f32 = to_f32_3(basis.normal);

    // Handle 100%-glazed host face where all boundaries cancelled cleanly!
    if edge_counts.is_empty() {
        if expected_area <= (1e-4_f64).max(2e-3 * outer_area) {
            let centroid = polygon_centroid_2d(&outer_2d_ccw)
                .map(|c2| to_f32_3(basis.unproject(c2)))
                .unwrap_or_else(|| outer_bounds.center());
            return Some(TriangulatedGeometry {
                vertices: Vec::new(),
                indices: Vec::new(),
                edge_loops,
                normal: normal_f32,
                area: 0.0,
                centroid,
                bounds: outer_bounds,
            });
        }
        return None;
    }

    // 4. Trace directed edges into closed loops, keeping host interior on the LEFT.
    let mut half_edges: Vec<(usize, usize)> = Vec::new();
    let mut outgoing: Vec<Vec<usize>> = vec![Vec::new(); pool.len()];
    for ((u, v), count) in edge_counts {
        for _ in 0..count {
            let eid = half_edges.len();
            half_edges.push((u, v));
            outgoing[u].push(eid);
        }
    }

    let mut used = vec![false; half_edges.len()];
    let mut traced_loops: Vec<Vec<DVec2>> = Vec::new();
    let total_edges = half_edges.len();

    for start_eid in 0..total_edges {
        if used[start_eid] {
            continue;
        }
        used[start_eid] = true;
        let (start_u, mut curr) = half_edges[start_eid];
        let mut prev = start_u;
        let mut loop_ids: Vec<usize> = vec![start_u];
        let mut steps = 0_usize;

        while curr != start_u {
            loop_ids.push(curr);
            steps += 1;
            if steps > total_edges {
                return None;
            }
            let b_vec = pool[prev] - pool[curr];
            let b_ang = b_vec.y.atan2(b_vec.x);

            let mut best_eid: Option<usize> = None;
            let mut best_cw = f64::INFINITY;
            for &cand_eid in &outgoing[curr] {
                if used[cand_eid] {
                    continue;
                }
                let (_, cand_next) = half_edges[cand_eid];
                let out_vec = pool[cand_next] - pool[curr];
                let out_ang = out_vec.y.atan2(out_vec.x);
                let mut cw = (b_ang - out_ang).rem_euclid(std::f64::consts::TAU);
                if cw <= 1e-12 {
                    cw = std::f64::consts::TAU;
                }
                if cw < best_cw {
                    best_cw = cw;
                    best_eid = Some(cand_eid);
                }
            }

            let next_eid = best_eid?;
            used[next_eid] = true;
            prev = curr;
            curr = half_edges[next_eid].1;
        }

        if loop_ids.len() >= 3 {
            let ring: Vec<DVec2> = loop_ids.into_iter().map(|id| pool[id]).collect();
            if signed_area_2d(&ring).abs() > 1e-8 {
                traced_loops.push(ring);
            }
        }
    }

    // 5. Partition traced loops into CCW solid outer shells and CW interior holes.
    let mut shells: Vec<(Vec<DVec2>, f64, Vec<Vec<DVec2>>)> = Vec::new();
    let mut interior_holes: Vec<Vec<DVec2>> = Vec::new();
    for ring in traced_loops {
        let sa = signed_area_2d(&ring);
        if sa > 1e-8 {
            shells.push((ring, sa, Vec::new()));
        } else if sa < -1e-8 {
            interior_holes.push(ring);
        }
    }
    if shells.is_empty() {
        return None;
    }

    // Assign each CW hole to its smallest enclosing CCW shell.
    for hole in interior_holes {
        let hole_ccw: Vec<DVec2> = hole.iter().copied().rev().collect();
        let probe = interior_sample_points_2d(&hole_ccw)
            .and_then(|s| s.into_iter().next())
            .or_else(|| polygon_centroid_2d(&hole_ccw))
            .unwrap_or(hole[0]);

        let mut best_shell: Option<(usize, f64)> = None;
        for (s_idx, (shell_ring, shell_area, _)) in shells.iter().enumerate() {
            if point_in_or_on_polygon_2d(probe, shell_ring, SNAP_EPS_2D_M)
                && best_shell.is_none_or(|(_, best_a)| *shell_area < best_a)
            {
                best_shell = Some((s_idx, *shell_area));
            }
        }
        let (target_shell, _) = best_shell?;
        shells[target_shell].2.push(hole);
    }

    // 6. Triangulate every solid shell + its enclosed CW holes with earcutr & verify strictly!
    let kind_code = kind.kind_code();
    let mut out_vertices: Vec<MeshVertex> = Vec::new();
    let mut out_indices: Vec<u32> = Vec::new();
    let mut area_sum_2d = 0.0_f64;
    let mut area_sum_3d = 0.0_f64;
    let mut weighted_centroid = DVec3::ZERO;
    let mut bounds = Bounds3::empty();

    for (shell_ccw, _shell_area, shell_holes_cw) in shells {
        let base_vert = out_vertices.len() as u32;
        let total_pts = shell_ccw.len() + shell_holes_cw.iter().map(Vec::len).sum::<usize>();
        let mut coords = Vec::with_capacity(total_pts * 2);
        let mut local_2d = Vec::with_capacity(total_pts);
        let mut local_3d = Vec::with_capacity(total_pts);
        let mut hole_offsets = Vec::with_capacity(shell_holes_cw.len());

        for &p2 in &shell_ccw {
            coords.push(p2.x);
            coords.push(p2.y);
            local_2d.push(p2);
            local_3d.push(basis.unproject(p2));
        }
        for h_cw in &shell_holes_cw {
            hole_offsets.push(local_2d.len());
            for &p2 in h_cw {
                coords.push(p2.x);
                coords.push(p2.y);
                local_2d.push(p2);
                local_3d.push(basis.unproject(p2));
            }
        }

        let raw_tris = earcutr::earcut(&coords, &hole_offsets, 2).ok()?;
        if raw_tris.is_empty() || raw_tris.len() % 3 != 0 {
            return None;
        }

        for &p3 in &local_3d {
            let pos = to_f32_3(p3);
            if !pos[0].is_finite() || !pos[1].is_finite() || !pos[2].is_finite() {
                return None;
            }
            bounds.expand_point(pos);
            out_vertices.push(MeshVertex {
                position: pos,
                normal: normal_f32,
                object_id,
                kind_code,
            });
        }

        for tri in raw_tris.chunks_exact(3) {
            let (ia, ib, ic) = (tri[0], tri[1], tri[2]);
            if ia >= local_2d.len() || ib >= local_2d.len() || ic >= local_2d.len() {
                return None;
            }
            let a2 = local_2d[ia];
            let b2 = local_2d[ib];
            let c2 = local_2d[ic];
            let signed_tri = 0.5 * orient_2d(a2, b2, c2);
            if !signed_tri.is_finite() || signed_tri < -1e-7 {
                return None;
            }
            if signed_tri <= 1e-12 {
                continue;
            }

            // Guarantee zero host triangles overlap any punched hole!
            let tri_c = (a2 + b2 + c2) / 3.0;
            if !point_in_or_on_polygon_2d(tri_c, &outer_2d_ccw, SNAP_EPS_2D_M) {
                return None;
            }
            if punch_holes_2d_ccw
                .iter()
                .any(|h| point_strictly_inside_polygon_2d(tri_c, h, SNAP_EPS_2D_M))
            {
                return None;
            }

            let (p0, mut p1, mut p2) = (local_3d[ia], local_3d[ib], local_3d[ic]);
            let mut out_tri = [base_vert + ia as u32, base_vert + ib as u32, base_vert + ic as u32];
            if (p1 - p0).cross(p2 - p0).dot(basis.normal) < 0.0 {
                out_tri.swap(1, 2);
                std::mem::swap(&mut p1, &mut p2);
            }
            let tri_area_3d = 0.5 * (p1 - p0).cross(p2 - p0).length();
            if !tri_area_3d.is_finite() {
                return None;
            }
            area_sum_2d += signed_tri;
            area_sum_3d += tri_area_3d;
            weighted_centroid += ((p0 + p1 + p2) / 3.0) * tri_area_3d;
            out_indices.extend_from_slice(&out_tri);
        }
    }

    let area_tol = (1e-4_f64).max(2e-3 * expected_area.max(outer_area * 1e-3));
    if (area_sum_2d - expected_area).abs() > area_tol {
        return None;
    }

    if !bounds.is_valid() {
        bounds = outer_bounds;
    }
    let centroid = if area_sum_3d > 1e-12 {
        to_f32_3(weighted_centroid / area_sum_3d)
    } else {
        bounds.center()
    };

    Some(TriangulatedGeometry {
        vertices: out_vertices,
        indices: out_indices,
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

    if !clean_holes.is_empty()
        && let Some(punched) = try_triangulate_earcut(
            &basis,
            &clean_outer,
            &clean_holes,
            object_id,
            kind,
            clean_holes.len(),
        )
    {
        return punched;
    }

    triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, kind)
}

/// Validate whether a candidate 2D hole (CCW) lies inside/on `outer_2d_ccw` and does not
/// overlap any previously accepted hole with positive area.
fn validate_punch_hole_2d(
    cand_ccw: &[DVec2],
    outer_2d_ccw: &[DVec2],
    accepted: &[(Vec<DVec2>, Vec<DVec2>)],
) -> Option<Vec<DVec2>> {
    let area = signed_area_2d(cand_ccw).abs();
    if !area.is_finite() || area <= 1e-8 {
        return None;
    }
    if loops_properly_cross_2d(cand_ccw, outer_2d_ccw, SNAP_EPS_2D_M) {
        return None;
    }
    // Every vertex and edge midpoint must lie inside or on the host outer boundary.
    let n = cand_ccw.len();
    for i in 0..n {
        let a = cand_ccw[i];
        let b = cand_ccw[(i + 1) % n];
        if !point_in_or_on_polygon_2d(a, outer_2d_ccw, SNAP_EPS_2D_M) {
            return None;
        }
        let mid = 0.5 * (a + b);
        if !point_in_or_on_polygon_2d(mid, outer_2d_ccw, SNAP_EPS_2D_M) {
            return None;
        }
    }

    let samples = interior_sample_points_2d(cand_ccw)?;
    if !samples
        .iter()
        .all(|&pt| point_in_or_on_polygon_2d(pt, outer_2d_ccw, SNAP_EPS_2D_M))
    {
        return None;
    }

    // Reject positive-area overlap with any previously accepted hole (touching edges/vertices OK!).
    for (prev_ccw, prev_samples) in accepted {
        if loops_properly_cross_2d(cand_ccw, prev_ccw, SNAP_EPS_2D_M) {
            return None;
        }
        if samples
            .iter()
            .any(|&pt| point_strictly_inside_polygon_2d(pt, prev_ccw, SNAP_EPS_2D_M))
        {
            return None;
        }
        if prev_samples
            .iter()
            .any(|&pt| point_strictly_inside_polygon_2d(pt, cand_ccw, SNAP_EPS_2D_M))
        {
            return None;
        }
    }

    Some(samples)
}

/// Triangulate a host `Face` along with its explicit `Face3D.holes` and child `subface_loops`
/// (apertures + doors).
///
/// 1. Fast path: strictly interior, strictly disjoint holes via `earcutr`.
/// 2. General touching/collinear path: exact 2D half-edge collinear splitting + opposite-edge
///    cancellation, cleanly punching boundary-touching doors, edge-sharing windows, wall-splitting
///    openings, and 100%-glazed faces without leaving overlapping host triangles behind sub-faces.
/// 3. Fallback: any genuinely invalid/crossing/non-coplanar sub-face gets a clean normal offset
///    (`SUBFACE_FALLBACK_NORMAL_OFFSET_M`) without forcing valid sibling sub-faces to unpunch.
pub fn triangulate_host_face(
    boundary: &[DVec3],
    explicit_holes: &[Vec<DVec3>],
    subface_loops: &[Vec<DVec3>],
    plane: Option<PlaneInput>,
    object_id: u32,
) -> HostTriangulation {
    let n_sub = subface_loops.len();
    let Some(clean_outer) = clean_loop_3d(boundary) else {
        return HostTriangulation {
            geometry: TriangulatedGeometry::empty([0.0, 0.0, 1.0]),
            gross_area: 0.0,
            gross_centroid: [0.0, 0.0, 0.0],
            gross_bounds: Bounds3::empty(),
            punched_subfaces: false,
            subface_offset_m: 0.0,
            subface_offsets: vec![0.0; n_sub],
            subface_coplanar: vec![false; n_sub],
        };
    };
    let Some(basis) = build_local_basis(&clean_outer, plane) else {
        return HostTriangulation {
            geometry: TriangulatedGeometry::empty([0.0, 0.0, 1.0]),
            gross_area: 0.0,
            gross_centroid: [0.0, 0.0, 0.0],
            gross_bounds: Bounds3::empty(),
            punched_subfaces: false,
            subface_offset_m: 0.0,
            subface_offsets: vec![0.0; n_sub],
            subface_coplanar: vec![false; n_sub],
        };
    };

    let clean_explicit: Vec<Vec<DVec3>> = explicit_holes
        .iter()
        .filter_map(|h| clean_loop_3d(h))
        .collect();
    let explicit_count = clean_explicit.len();

    let outer_2d: Vec<DVec2> = clean_outer.iter().map(|&p| basis.project(p)).collect();
    let outer_2d_ccw = normalize_ccw_2d(&outer_2d);
    let outer_area = signed_area_2d(&outer_2d_ccw).abs();
    let explicit_holes_area: f64 = clean_explicit
        .iter()
        .map(|h| {
            let h2: Vec<DVec2> = h.iter().map(|&p| basis.project(p)).collect();
            signed_area_2d(&h2).abs()
        })
        .sum();
    let gross_area = (outer_area - explicit_holes_area).max(0.0);

    let mut gross_bounds = Bounds3::empty();
    for &p in &clean_outer {
        gross_bounds.expand_point(to_f32_3(p));
    }
    let gross_centroid = polygon_centroid_2d(&outer_2d_ccw)
        .map(|c2| to_f32_3(basis.unproject(c2)))
        .unwrap_or_else(|| gross_bounds.center());

    let subface_coplanar: Vec<bool> = subface_loops
        .iter()
        .map(|sf| {
            !sf.is_empty()
                && sf
                    .iter()
                    .all(|&p| p.is_finite() && basis.signed_distance(p).abs() <= COPLANAR_TOLERANCE_M)
        })
        .collect();

    if !subface_loops.is_empty() {
        // 1. Fast path: all subfaces strictly interior and pairwise disjoint.
        let mut clean_subfaces = Vec::with_capacity(n_sub);
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
                    gross_centroid,
                    gross_bounds,
                    punched_subfaces: true,
                    subface_offset_m: 0.0,
                    subface_offsets: vec![0.0; n_sub],
                    subface_coplanar,
                };
            }
        }

        // 2. General path: handle boundary-touching doors, edge-sharing windows, wall-splitting
        //    openings, 100%-glazed walls, and partial valid subface sets via exact 2D half-edge
        //    subtraction.
        let mut accepted_holes: Vec<(Vec<DVec2>, Vec<DVec2>)> = Vec::new();
        for eh in &clean_explicit {
            if eh
                .iter()
                .all(|&p| basis.signed_distance(p).abs() <= COPLANAR_TOLERANCE_M)
            {
                let h2_ccw = normalize_ccw_2d(&eh.iter().map(|&p| basis.project(p)).collect::<Vec<_>>());
                if let Some(samples) = validate_punch_hole_2d(&h2_ccw, &outer_2d_ccw, &accepted_holes) {
                    accepted_holes.push((h2_ccw, samples));
                }
            }
        }

        let mut punched_flags = vec![false; n_sub];
        let mut punched_count = 0_usize;
        for (idx, sf) in subface_loops.iter().enumerate() {
            if !subface_coplanar[idx] {
                continue;
            }
            let Some(cleaned) = clean_loop_3d(sf) else {
                continue;
            };
            let h2_ccw = normalize_ccw_2d(&cleaned.iter().map(|&p| basis.project(p)).collect::<Vec<_>>());
            if let Some(samples) = validate_punch_hole_2d(&h2_ccw, &outer_2d_ccw, &accepted_holes) {
                accepted_holes.push((h2_ccw, samples));
                punched_flags[idx] = true;
                punched_count += 1;
            }
        }

        if punched_count > 0 {
            let punch_loops_2d: Vec<Vec<DVec2>> =
                accepted_holes.into_iter().map(|(ring, _)| ring).collect();
            if let Some(punched_geom) = try_triangulate_half_edge_punched(
                &basis,
                &clean_outer,
                &clean_explicit,
                &punch_loops_2d,
                object_id,
                ObjectKind::Face,
            ) {
                let subface_offsets: Vec<f64> = punched_flags
                    .iter()
                    .map(|&was_punched| {
                        if was_punched {
                            0.0
                        } else {
                            SUBFACE_FALLBACK_NORMAL_OFFSET_M
                        }
                    })
                    .collect();
                let any_fallback = punched_count < n_sub;
                return HostTriangulation {
                    geometry: punched_geom,
                    gross_area,
                    gross_centroid,
                    gross_bounds,
                    punched_subfaces: true,
                    subface_offset_m: if any_fallback {
                        SUBFACE_FALLBACK_NORMAL_OFFSET_M
                    } else {
                        0.0
                    },
                    subface_offsets,
                    subface_coplanar,
                };
            }
        }
    }

    // 3. Fallback: unpunched host face (preserving explicit Face3D holes when valid) + 0.003m offset.
    let host_geom = if !clean_explicit.is_empty() {
        try_triangulate_earcut(
            &basis,
            &clean_outer,
            &clean_explicit,
            object_id,
            ObjectKind::Face,
            explicit_count,
        )
        .unwrap_or_else(|| {
            triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, ObjectKind::Face)
        })
    } else {
        triangulate_outer_only_best_effort(&basis, &clean_outer, object_id, ObjectKind::Face)
    };

    let fallback_offset = if subface_loops.is_empty() {
        0.0
    } else {
        SUBFACE_FALLBACK_NORMAL_OFFSET_M
    };

    HostTriangulation {
        geometry: host_geom,
        gross_area,
        gross_centroid,
        gross_bounds,
        punched_subfaces: false,
        subface_offset_m: fallback_offset,
        subface_offsets: vec![fallback_offset; n_sub],
        subface_coplanar,
    }
}

/// Shift all mesh vertices, edge loops, centroid, and bounds of a `TriangulatedGeometry`
/// along `offset` (used for interior Room `Surface` insets and sub-face fallback offsets).
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
    let use_edges_for_bounds = geom.vertices.is_empty();
    for loop_pts in &mut geom.edge_loops {
        for p in loop_pts {
            p[0] += offset[0];
            p[1] += offset[1];
            p[2] += offset[2];
            if use_edges_for_bounds {
                new_bounds.expand_point(*p);
            }
        }
    }
    if new_bounds.is_valid() {
        geom.bounds = new_bounds;
    } else if geom.bounds.is_valid() {
        for (i, delta) in offset.iter().enumerate() {
            geom.bounds.min[i] += *delta;
            geom.bounds.max[i] += *delta;
        }
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
