//! Fast CPU Möller–Trumbore ray-triangle picking for browser/WASM and fallback backends.

use std::collections::HashSet;

use glam::Vec3;
use lbt_scene::{IsolationMode, ObjectKind, SceneData};

use crate::core::{
    PickHit, RenderState, active_editing_room_in_scene, expand_room_descendants_with_map,
    resolve_owner_room_map, resolve_section_plane,
};

/// Distance tie tolerance (meters) within which subfaces (`Aperture`/`Door`) take priority
/// over coplanar host `Face` triangles.
const SUBFACE_TIE_EPS: f32 = 1e-3;

#[inline]
fn is_subface_kind(kind_code: u32) -> bool {
    kind_code == ObjectKind::Aperture.kind_code() || kind_code == ObjectKind::Door.kind_code()
}

#[derive(Copy, Clone)]
struct CandidateHit {
    t: f32,
    is_subface: bool,
    hit: PickHit,
}

fn update_best(best: &mut Option<CandidateHit>, cand: CandidateHit) {
    let replace = match *best {
        None => true,
        Some(prev) => {
            if cand.t < prev.t - SUBFACE_TIE_EPS {
                true
            } else if (cand.t - prev.t).abs() <= SUBFACE_TIE_EPS {
                if cand.is_subface != prev.is_subface {
                    cand.is_subface
                } else {
                    cand.t < prev.t
                }
            } else {
                false
            }
        }
    };
    if replace {
        *best = Some(cand);
    }
}

/// Intersect a world-space ray with visible scene triangles, honoring isolation, section cuts,
/// and SketchUp/OpenStudio-style Room Edit Mode ([`RenderState::editing_room_id`]).
///
/// Behavior:
/// - Mirrors GPU pick visibility (`IsolationMode::Isolate` hides non-highlighted objects;
///   fragments past `section_plane` are skipped).
/// - Populates [`PickHit::owner_room_id`] and [`PickHit::is_ghosted`] on every returned hit so
///   callers can cleanly implement Room-first selection and Room Edit Mode exit-on-outside-click.
/// - When [`RenderState::editing_room_id`] is `Some(room_id)`, descendants of `room_id` take
///   priority over ghosted outer context shells so neighboring room exteriors never block picking
///   inside the edited room; if the ray misses the edited room completely, any ghosted context hit
///   is returned with `is_ghosted == true`.
pub fn pick_scene_ray(
    scene: &SceneData,
    state: &RenderState,
    ray_origin: [f32; 3],
    ray_dir: [f32; 3],
) -> Option<PickHit> {
    if scene.indices.len() < 3 || scene.vertices.is_empty() {
        return None;
    }

    let dir_vec = Vec3::from_array(ray_dir);
    let dir_len = dir_vec.length();
    if !dir_len.is_finite() || dir_len <= 1e-7 {
        return None;
    }
    let dir = dir_vec / dir_len;
    let orig = Vec3::from_array(ray_origin);

    let owner_room_map = resolve_owner_room_map(&scene.objects);
    let highlighted_set =
        expand_room_descendants_with_map(&scene.objects, &owner_room_map, &state.highlighted_ids);
    let hide_unhighlighted =
        !highlighted_set.is_empty() && state.isolation_mode == IsolationMode::Isolate;
    let ghost_unhighlighted =
        !highlighted_set.is_empty() && state.isolation_mode == IsolationMode::GhostContext;
    let active_edit_room =
        active_editing_room_in_scene(&scene.objects, &owner_room_map, state.editing_room_id);

    let mut hidden_ids: HashSet<u32> = HashSet::new();
    let mut ghosted_ids: HashSet<u32> = HashSet::new();
    for obj in &scene.objects {
        if obj.object_id == 0 {
            continue;
        }
        let is_highlighted = highlighted_set.contains(&obj.object_id);
        if hide_unhighlighted && !is_highlighted {
            hidden_ids.insert(obj.object_id);
        } else if ghost_unhighlighted && !is_highlighted {
            ghosted_ids.insert(obj.object_id);
        } else if let Some(edit_rid) = active_edit_room
            && owner_room_map.get(&obj.object_id).copied().flatten() != Some(edit_rid)
        {
            ghosted_ids.insert(obj.object_id);
        }
    }

    let (section_enabled, section_plane) = resolve_section_plane(scene, state.section.as_ref());
    let cut_normal = Vec3::new(section_plane[0], section_plane[1], section_plane[2]);
    let cut_threshold = section_plane[3];

    let mut best_active: Option<CandidateHit> = None;
    let mut best_ghost: Option<CandidateHit> = None;

    for tri in scene.indices.chunks_exact(3) {
        let Some(va) = scene.vertices.get(tri[0] as usize) else {
            continue;
        };
        let Some(vb) = scene.vertices.get(tri[1] as usize) else {
            continue;
        };
        let Some(vc) = scene.vertices.get(tri[2] as usize) else {
            continue;
        };

        let object_id = va.object_id;
        if object_id == 0 || hidden_ids.contains(&object_id) {
            continue;
        }

        let v0 = Vec3::from_array(va.position);
        let v1 = Vec3::from_array(vb.position);
        let v2 = Vec3::from_array(vc.position);

        let e1 = v1 - v0;
        let e2 = v2 - v0;
        let pvec = dir.cross(e2);
        let det = e1.dot(pvec);
        if det.abs() < 1e-8 {
            continue;
        }
        let inv_det = 1.0 / det;
        let tvec = orig - v0;
        let u = tvec.dot(pvec) * inv_det;
        if !(-1e-5..=1.0 + 1e-5).contains(&u) {
            continue;
        }
        let qvec = tvec.cross(e1);
        let v = dir.dot(qvec) * inv_det;
        if v < -1e-5 || (u + v) > 1.0 + 1e-5 {
            continue;
        }
        let t = e2.dot(qvec) * inv_det;
        if !t.is_finite() || t < 0.0 {
            continue;
        }

        let is_ghosted = ghosted_ids.contains(&object_id);
        let bucket_best_t = if is_ghosted {
            best_ghost.map_or(f32::INFINITY, |c| c.t)
        } else {
            best_active.map_or(f32::INFINITY, |c| c.t)
        };
        if t > bucket_best_t + SUBFACE_TIE_EPS {
            continue;
        }

        let hit_pos = orig + dir * t;
        if section_enabled && hit_pos.dot(cut_normal) > cut_threshold {
            continue;
        }

        let owner_room_id = owner_room_map.get(&object_id).copied().flatten();
        let cand = CandidateHit {
            t,
            is_subface: is_subface_kind(va.kind_code),
            hit: PickHit {
                object_id,
                owner_room_id,
                is_ghosted,
                world_point: hit_pos.to_array(),
            },
        };
        if is_ghosted {
            update_best(&mut best_ghost, cand);
        } else {
            update_best(&mut best_active, cand);
        }
    }

    if active_edit_room.is_some() {
        // In Room Edit Mode, descendants of the edited room ALWAYS take priority over ghosted
        // outer shells so neighboring rooms in front of the camera never block interior picking.
        best_active.or(best_ghost).map(|c| c.hit)
    } else {
        match (best_active, best_ghost) {
            (Some(a), Some(g)) => {
                let mut combined = Some(a);
                update_best(&mut combined, g);
                combined.map(|c| c.hit)
            }
            (Some(a), None) => Some(a.hit),
            (None, Some(g)) => Some(g.hit),
            (None, None) => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use lbt_scene::{
        Bounds3, MeshVertex, ObjectKind, ObjectRecord, ObjectTargetRef, SectionAxis, SectionSpec,
    };

    use super::*;

    fn make_record(
        object_id: u32,
        kind: ObjectKind,
        identifier: &str,
        parent_object_id: Option<u32>,
        owner_room_id: Option<u32>,
        is_orphaned: bool,
    ) -> ObjectRecord {
        ObjectRecord {
            object_id,
            kind,
            identifier: identifier.to_owned(),
            display_name: None,
            target: ObjectTargetRef::new(None, "test_model", kind, identifier),
            bounds: Bounds3::new([-2.0, -2.0, 0.0], [2.0, 2.0, 5.0]),
            centroid: [0.0, 0.0, 2.5],
            parent_object_id,
            owner_room_id,
            is_orphaned,
            is_glass: false,
            is_indoor_shade: false,
            is_detached_shade: false,
            is_shade_mesh: false,
            face_type: Some("RoofCeiling".to_owned()),
            boundary_condition: Some("Outdoors".to_owned()),
            story: None,
            zone: None,
            program_type: None,
            construction_set: None,
            hvac: None,
            wwr: None,
            area: Some(8.0),
        }
    }

    fn make_tri(z: f32, object_id: u32, kind: ObjectKind) -> [MeshVertex; 3] {
        [
            MeshVertex {
                position: [-2.0, -2.0, z],
                normal: [0.0, 0.0, 1.0],
                object_id,
                kind_code: kind.kind_code(),
            },
            MeshVertex {
                position: [2.0, -2.0, z],
                normal: [0.0, 0.0, 1.0],
                object_id,
                kind_code: kind.kind_code(),
            },
            MeshVertex {
                position: [0.0, 2.0, z],
                normal: [0.0, 0.0, 1.0],
                object_id,
                kind_code: kind.kind_code(),
            },
        ]
    }

    fn quad_scene() -> SceneData {
        let mut vertices = Vec::new();
        vertices.extend_from_slice(&make_tri(4.0, 1, ObjectKind::Face));
        vertices.extend_from_slice(&make_tri(1.0, 2, ObjectKind::Face));

        SceneData {
            bounds: Bounds3::new([-2.0, -2.0, 1.0], [2.0, 2.0, 4.0]),
            vertices,
            indices: vec![0, 1, 2, 3, 4, 5],
            objects: vec![
                make_record(1, ObjectKind::Face, "top_face", None, None, true),
                make_record(2, ObjectKind::Face, "bottom_face", None, None, true),
            ],
            ..Default::default()
        }
    }

    fn two_room_layered_scene() -> SceneData {
        // Room A (id=10) has a face at z=4.0 (occluder closer to top camera at z=10)
        // Room B (id=20) has a face at z=1.0 AND an aperture at z=1.0 (behind Room A)
        // Orphaned shade (id=30) at x=[4..8], z=2.0
        let mut vertices = Vec::new();
        vertices.extend_from_slice(&make_tri(4.0, 11, ObjectKind::Face));
        vertices.extend_from_slice(&make_tri(1.0, 21, ObjectKind::Face));
        vertices.extend_from_slice(&make_tri(1.0, 22, ObjectKind::Aperture));
        vertices.extend_from_slice(&[
            MeshVertex {
                position: [4.0, -2.0, 2.0],
                normal: [0.0, 0.0, 1.0],
                object_id: 30,
                kind_code: ObjectKind::Shade.kind_code(),
            },
            MeshVertex {
                position: [8.0, -2.0, 2.0],
                normal: [0.0, 0.0, 1.0],
                object_id: 30,
                kind_code: ObjectKind::Shade.kind_code(),
            },
            MeshVertex {
                position: [6.0, 2.0, 2.0],
                normal: [0.0, 0.0, 1.0],
                object_id: 30,
                kind_code: ObjectKind::Shade.kind_code(),
            },
        ]);

        SceneData {
            bounds: Bounds3::new([-2.0, -2.0, 1.0], [8.0, 2.0, 4.0]),
            vertices,
            indices: vec![0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            objects: vec![
                make_record(10, ObjectKind::Room, "Room_A", None, Some(10), false),
                make_record(11, ObjectKind::Face, "Room_A_Roof", Some(10), Some(10), false),
                make_record(20, ObjectKind::Room, "Room_B", None, Some(20), false),
                make_record(21, ObjectKind::Face, "Room_B_Face", Some(20), Some(20), false),
                make_record(22, ObjectKind::Aperture, "Room_B_Ap", Some(21), Some(20), false),
                make_record(30, ObjectKind::Shade, "Context_Shade", None, None, true),
            ],
            ..Default::default()
        }
    }

    #[test]
    fn picks_closest_triangle_and_honors_section_and_isolation() {
        let scene = quad_scene();
        let origin = [0.0, 0.0, 10.0];
        let dir = [0.0, 0.0, -1.0];

        let hit = pick_scene_ray(&scene, &RenderState::default(), origin, dir).expect("hit top");
        assert_eq!(hit.object_id, 1);
        assert_eq!(hit.owner_room_id, None);
        assert!(!hit.is_ghosted);
        assert!((hit.world_point[2] - 4.0).abs() < 1e-4);

        let cut_state = RenderState {
            section: Some(SectionSpec {
                enabled: true,
                axis: SectionAxis::Z,
                value: Some(2.5),
                story: None,
                invert: false,
            }),
            ..RenderState::default()
        };
        let cut_hit = pick_scene_ray(&scene, &cut_state, origin, dir).expect("hit below cut");
        assert_eq!(cut_hit.object_id, 2);
        assert!((cut_hit.world_point[2] - 1.0).abs() < 1e-4);

        let iso_state = RenderState {
            highlighted_ids: vec![2],
            isolation_mode: IsolationMode::Isolate,
            ..RenderState::default()
        };
        let iso_hit = pick_scene_ray(&scene, &iso_state, origin, dir).expect("hit isolated");
        assert_eq!(iso_hit.object_id, 2);
    }

    #[test]
    fn room_edit_mode_prioritizes_active_room_descendants_over_ghosted_occluders() {
        let scene = two_room_layered_scene();
        let origin = [0.0, 0.0, 10.0];
        let dir = [0.0, 0.0, -1.0];

        // Model mode (editing_room_id == None): hits closest exterior shell (Room A roof at z=4).
        let model_hit = pick_scene_ray(&scene, &RenderState::default(), origin, dir)
            .expect("model mode hits Room A");
        assert_eq!(model_hit.object_id, 11);
        assert_eq!(model_hit.owner_room_id, Some(10));
        assert!(!model_hit.is_ghosted);

        // Room Edit Mode for Room B (id=20): skips ghosted Room A roof in front and picks Room B's
        // coplanar Aperture over its host Face!
        let edit_b_state = RenderState {
            editing_room_id: Some(20),
            ..RenderState::default()
        };
        let edit_hit = pick_scene_ray(&scene, &edit_b_state, origin, dir)
            .expect("edit mode should pick through ghosted Room A into Room B");
        assert_eq!(edit_hit.object_id, 22);
        assert_eq!(edit_hit.owner_room_id, Some(20));
        assert!(!edit_hit.is_ghosted);
        assert!((edit_hit.world_point[2] - 1.0).abs() < 1e-4);

        // Clicking outside Room B onto orphaned Context Shade returns ghosted hit so caller can exit!
        let outside_hit = pick_scene_ray(&scene, &edit_b_state, [6.0, 0.0, 10.0], dir)
            .expect("clicking ghosted context returns ghosted hit");
        assert_eq!(outside_hit.object_id, 30);
        assert_eq!(outside_hit.owner_room_id, None);
        assert!(outside_hit.is_ghosted);
    }

    #[test]
    fn miss_returns_none() {
        let scene = quad_scene();
        let miss = pick_scene_ray(&scene, &RenderState::default(), [10.0, 10.0, 10.0], [0.0, 0.0, -1.0]);
        assert!(miss.is_none());
    }
}
