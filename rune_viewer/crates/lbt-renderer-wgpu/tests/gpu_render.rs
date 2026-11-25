#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;

use lbt_renderer_wgpu::{BuildingRenderer, RenderState, RendererError, pick_scene_ray};
use lbt_scene::{
    Bounds3, CameraPreset, ColorBy, EdgeVertex, IsolationMode, MeshVertex, ObjectKind,
    ObjectRecord, ObjectTargetRef, SceneData, SectionAxis, SectionSpec,
};

fn add_quad(
    vertices: &mut Vec<MeshVertex>,
    indices: &mut Vec<u32>,
    edges: &mut Vec<EdgeVertex>,
    corners: [[f32; 3]; 4],
    normal: [f32; 3],
    object_id: u32,
    kind: ObjectKind,
    add_edges: bool,
) {
    let base = vertices.len() as u32;
    let kind_code = kind.kind_code();
    for p in corners {
        vertices.push(MeshVertex {
            position: p,
            normal,
            object_id,
            kind_code,
        });
    }
    indices.extend_from_slice(&[base, base + 1, base + 2, base, base + 2, base + 3]);
    if add_edges {
        for i in 0..4 {
            let a = corners[i];
            let b = corners[(i + 1) % 4];
            edges.push(EdgeVertex {
                position: a,
                object_id,
            });
            edges.push(EdgeVertex {
                position: b,
                object_id,
            });
        }
    }
}

/// Add a planar vertical wall on `Y = y` (`x0..x1`, `z0..z1`) punched around rectangular openings.
fn add_punched_y_wall(
    vertices: &mut Vec<MeshVertex>,
    indices: &mut Vec<u32>,
    edges: &mut Vec<EdgeVertex>,
    y: f32,
    x0: f32,
    x1: f32,
    z0: f32,
    z1: f32,
    normal: [f32; 3],
    object_id: u32,
    openings: &[(f32, f32, f32, f32)], // (ox0, ox1, oz0, oz1)
) {
    if openings.is_empty() {
        add_quad(
            vertices,
            indices,
            edges,
            [[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]],
            normal,
            object_id,
            ObjectKind::Face,
            true,
        );
        return;
    }

    // Outer wall boundary edges
    let outer = [[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]];
    for i in 0..4 {
        edges.push(EdgeVertex {
            position: outer[i],
            object_id,
        });
        edges.push(EdgeVertex {
            position: outer[(i + 1) % 4],
            object_id,
        });
    }

    // Subdivide grid along sorted X and Z breakpoints and emit non-opening cells.
    let mut xs = vec![x0, x1];
    let mut zs = vec![z0, z1];
    for &(ox0, ox1, oz0, oz1) in openings {
        xs.push(ox0);
        xs.push(ox1);
        zs.push(oz0);
        zs.push(oz1);
    }
    xs.sort_by(|a, b| a.total_cmp(b));
    xs.dedup_by(|a, b| (*a - *b).abs() < 1e-5);
    zs.sort_by(|a, b| a.total_cmp(b));
    zs.dedup_by(|a, b| (*a - *b).abs() < 1e-5);

    for ix in 0..xs.len().saturating_sub(1) {
        for iz in 0..zs.len().saturating_sub(1) {
            let cx = 0.5 * (xs[ix] + xs[ix + 1]);
            let cz = 0.5 * (zs[iz] + zs[iz + 1]);
            let inside_opening = openings
                .iter()
                .any(|&(ox0, ox1, oz0, oz1)| cx > ox0 && cx < ox1 && cz > oz0 && cz < oz1);
            if !inside_opening {
                add_quad(
                    vertices,
                    indices,
                    edges,
                    [
                        [xs[ix], y, zs[iz]],
                        [xs[ix + 1], y, zs[iz]],
                        [xs[ix + 1], y, zs[iz + 1]],
                        [xs[ix], y, zs[iz + 1]],
                    ],
                    normal,
                    object_id,
                    ObjectKind::Face,
                    false,
                );
            }
        }
    }
}

/// Add a planar vertical wall on `X = x` (`y0..y1`, `z0..z1`) punched around rectangular openings.
fn add_punched_x_wall(
    vertices: &mut Vec<MeshVertex>,
    indices: &mut Vec<u32>,
    edges: &mut Vec<EdgeVertex>,
    x: f32,
    y0: f32,
    y1: f32,
    z0: f32,
    z1: f32,
    normal: [f32; 3],
    object_id: u32,
    openings: &[(f32, f32, f32, f32)], // (oy0, oy1, oz0, oz1)
) {
    if openings.is_empty() {
        add_quad(
            vertices,
            indices,
            edges,
            [[x, y0, z0], [x, y1, z0], [x, y1, z1], [x, y0, z1]],
            normal,
            object_id,
            ObjectKind::Face,
            true,
        );
        return;
    }

    let outer = [[x, y0, z0], [x, y1, z0], [x, y1, z1], [x, y0, z1]];
    for i in 0..4 {
        edges.push(EdgeVertex {
            position: outer[i],
            object_id,
        });
        edges.push(EdgeVertex {
            position: outer[(i + 1) % 4],
            object_id,
        });
    }

    let mut ys = vec![y0, y1];
    let mut zs = vec![z0, z1];
    for &(oy0, oy1, oz0, oz1) in openings {
        ys.push(oy0);
        ys.push(oy1);
        zs.push(oz0);
        zs.push(oz1);
    }
    ys.sort_by(|a, b| a.total_cmp(b));
    ys.dedup_by(|a, b| (*a - *b).abs() < 1e-5);
    zs.sort_by(|a, b| a.total_cmp(b));
    zs.dedup_by(|a, b| (*a - *b).abs() < 1e-5);

    for iy in 0..ys.len().saturating_sub(1) {
        for iz in 0..zs.len().saturating_sub(1) {
            let cy = 0.5 * (ys[iy] + ys[iy + 1]);
            let cz = 0.5 * (zs[iz] + zs[iz + 1]);
            let inside_opening = openings
                .iter()
                .any(|&(oy0, oy1, oz0, oz1)| cy > oy0 && cy < oy1 && cz > oz0 && cz < oz1);
            if !inside_opening {
                add_quad(
                    vertices,
                    indices,
                    edges,
                    [
                        [x, ys[iy], zs[iz]],
                        [x, ys[iy + 1], zs[iz]],
                        [x, ys[iy + 1], zs[iz + 1]],
                        [x, ys[iy], zs[iz + 1]],
                    ],
                    normal,
                    object_id,
                    ObjectKind::Face,
                    false,
                );
            }
        }
    }
}

fn make_record(
    object_id: u32,
    kind: ObjectKind,
    identifier: &str,
    parent_object_id: Option<u32>,
    owner_room_id: Option<u32>,
    face_type: Option<&str>,
    boundary_condition: Option<&str>,
    story: &str,
    zone: &str,
    wwr: Option<f32>,
    bounds: Bounds3,
) -> ObjectRecord {
    ObjectRecord {
        object_id,
        kind,
        identifier: identifier.to_owned(),
        display_name: Some(identifier.to_owned()),
        target: ObjectTargetRef::new(None, "Sample_Office", kind, identifier),
        bounds,
        centroid: bounds.center(),
        parent_object_id,
        owner_room_id,
        is_orphaned: owner_room_id.is_none(),
        is_glass: false,
        is_indoor_shade: false,
        is_detached_shade: false,
        is_shade_mesh: false,
        face_type: face_type.map(str::to_owned),
        boundary_condition: boundary_condition.map(str::to_owned),
        story: Some(story.to_owned()),
        zone: Some(zone.to_owned()),
        program_type: Some("Office::OpenOffice".to_owned()),
        construction_set: Some("ASHRAE_90_1_CZ4".to_owned()),
        hvac: Some("VAV_Chiller".to_owned()),
        wwr,
        area: None,
    }
}

struct SampleBuilding {
    scene: SceneData,
    room1_id: u32,
    room2_id: u32,
    floor1_id: u32,
    south_wall1_id: u32,
    south_ap1_id: u32,
    south_shade1_id: u32,
    upper_roof_id: u32,
    terrace_roof_id: u32,
}

fn build_sample_building() -> SampleBuilding {
    let mut vertices = Vec::new();
    let mut indices = Vec::new();
    let mut edges = Vec::new();
    let mut objects = Vec::new();

    // Room 1: Story_1 (0..10, 0..6, 0..3.2)
    let room1_id = 1;
    objects.push(make_record(
        room1_id,
        ObjectKind::Room,
        "Office_Ground",
        None,
        Some(room1_id),
        None,
        None,
        "Level_1",
        "Core_South",
        Some(0.32),
        Bounds3::new([0.0, 0.0, 0.0], [10.0, 6.0, 3.2]),
    ));

    // Ground Floor (id 2)
    let floor1_id = 2;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 6.0, 0.0],
            [0.0, 6.0, 0.0],
        ],
        [0.0, 0.0, -1.0],
        floor1_id,
        ObjectKind::Face,
        true,
    );
    objects.push(make_record(
        floor1_id,
        ObjectKind::Face,
        "Ground_Floor",
        Some(room1_id),
        Some(room1_id),
        Some("Floor"),
        Some("Ground"),
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([0.0, 0.0, 0.0], [10.0, 6.0, 0.0]),
    ));

    // Story 1 South Wall (id 3) with 2 windows
    let south_wall1_id = 3;
    let w1 = (1.2, 4.4, 0.85, 2.55);
    let w2 = (5.6, 8.8, 0.85, 2.55);
    add_punched_y_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        0.0,
        0.0,
        10.0,
        0.0,
        3.2,
        [0.0, -1.0, 0.0],
        south_wall1_id,
        &[w1, w2],
    );
    objects.push(make_record(
        south_wall1_id,
        ObjectKind::Face,
        "Ground_South_Wall",
        Some(room1_id),
        Some(room1_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        Some(0.34),
        Bounds3::new([0.0, 0.0, 0.0], [10.0, 0.0, 3.2]),
    ));

    // South Apertures (id 4, 5)
    let south_ap1_id = 4;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [w1.0, 0.0, w1.2],
            [w1.1, 0.0, w1.2],
            [w1.1, 0.0, w1.3],
            [w1.0, 0.0, w1.3],
        ],
        [0.0, -1.0, 0.0],
        south_ap1_id,
        ObjectKind::Aperture,
        true,
    );
    objects.push(make_record(
        south_ap1_id,
        ObjectKind::Aperture,
        "Ground_South_Win_W",
        Some(south_wall1_id),
        Some(room1_id),
        None,
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([w1.0, 0.0, w1.2], [w1.1, 0.0, w1.3]),
    ));

    let south_ap2_id = 5;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [w2.0, 0.0, w2.2],
            [w2.1, 0.0, w2.2],
            [w2.1, 0.0, w2.3],
            [w2.0, 0.0, w2.3],
        ],
        [0.0, -1.0, 0.0],
        south_ap2_id,
        ObjectKind::Aperture,
        true,
    );
    objects.push(make_record(
        south_ap2_id,
        ObjectKind::Aperture,
        "Ground_South_Win_E",
        Some(south_wall1_id),
        Some(room1_id),
        None,
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([w2.0, 0.0, w2.2], [w2.1, 0.0, w2.3]),
    ));

    // South Overhang Shade (id 6)
    let south_shade1_id = 6;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.8, -1.1, 2.75],
            [9.2, -1.1, 2.75],
            [9.2, 0.0, 2.75],
            [0.8, 0.0, 2.75],
        ],
        [0.0, 0.0, 1.0],
        south_shade1_id,
        ObjectKind::Shade,
        true,
    );
    objects.push(make_record(
        south_shade1_id,
        ObjectKind::Shade,
        "South_Overhang",
        Some(south_wall1_id),
        Some(room1_id),
        None,
        None,
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([0.8, -1.1, 2.75], [9.2, 0.0, 2.75]),
    ));

    // Story 1 East Wall (id 7) with Door (id 8)
    let east_wall1_id = 7;
    let door_o = (2.1, 3.9, 0.0, 2.25);
    add_punched_x_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        10.0,
        0.0,
        6.0,
        0.0,
        3.2,
        [1.0, 0.0, 0.0],
        east_wall1_id,
        &[door_o],
    );
    objects.push(make_record(
        east_wall1_id,
        ObjectKind::Face,
        "Ground_East_Wall",
        Some(room1_id),
        Some(room1_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        Some(0.0),
        Bounds3::new([10.0, 0.0, 0.0], [10.0, 6.0, 3.2]),
    ));

    let door_id = 8;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [10.0, door_o.0, door_o.2],
            [10.0, door_o.1, door_o.2],
            [10.0, door_o.1, door_o.3],
            [10.0, door_o.0, door_o.3],
        ],
        [1.0, 0.0, 0.0],
        door_id,
        ObjectKind::Door,
        true,
    );
    objects.push(make_record(
        door_id,
        ObjectKind::Door,
        "East_Entry_Door",
        Some(east_wall1_id),
        Some(room1_id),
        None,
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([10.0, door_o.0, door_o.2], [10.0, door_o.1, door_o.3]),
    ));

    // Story 1 North & West Walls (id 9, 10)
    add_punched_y_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        6.0,
        0.0,
        10.0,
        0.0,
        3.2,
        [0.0, 1.0, 0.0],
        9,
        &[],
    );
    objects.push(make_record(
        9,
        ObjectKind::Face,
        "Ground_North_Wall",
        Some(room1_id),
        Some(room1_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        Some(0.0),
        Bounds3::new([0.0, 6.0, 0.0], [10.0, 6.0, 3.2]),
    ));

    add_punched_x_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        0.0,
        0.0,
        6.0,
        0.0,
        3.2,
        [-1.0, 0.0, 0.0],
        10,
        &[],
    );
    objects.push(make_record(
        10,
        ObjectKind::Face,
        "Ground_West_Wall",
        Some(room1_id),
        Some(room1_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        Some(0.0),
        Bounds3::new([0.0, 0.0, 0.0], [0.0, 6.0, 3.2]),
    ));

    // Story 1 Exposed Terrace Roof (x: 6..10, y: 0..6, z = 3.2, id 11) + Front Strip (x: 0..6, y: 0..1, z = 3.2)
    let terrace_roof_id = 11;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [6.0, 0.0, 3.2],
            [10.0, 0.0, 3.2],
            [10.0, 6.0, 3.2],
            [6.0, 6.0, 3.2],
        ],
        [0.0, 0.0, 1.0],
        terrace_roof_id,
        ObjectKind::Face,
        true,
    );
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.0, 0.0, 3.2],
            [6.0, 0.0, 3.2],
            [6.0, 1.0, 3.2],
            [0.0, 1.0, 3.2],
        ],
        [0.0, 0.0, 1.0],
        terrace_roof_id,
        ObjectKind::Face,
        true,
    );
    objects.push(make_record(
        terrace_roof_id,
        ObjectKind::Face,
        "Level1_Terrace_Roof",
        Some(room1_id),
        Some(room1_id),
        Some("RoofCeiling"),
        Some("Outdoors"),
        "Level_1",
        "Core_South",
        None,
        Bounds3::new([0.0, 0.0, 3.2], [10.0, 6.0, 3.2]),
    ));

    // Room 2: Story_2 (0..6, 1..6, 3.2..6.2)
    let room2_id = 12;
    objects.push(make_record(
        room2_id,
        ObjectKind::Room,
        "Office_Upper",
        None,
        Some(room2_id),
        None,
        None,
        "Level_2",
        "Penthouse_Zone",
        Some(0.45),
        Bounds3::new([0.0, 1.0, 3.2], [6.0, 6.0, 6.2]),
    ));

    // Interior ceiling/floor slab between Story 1 and Story 2 (id 13)
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.0, 1.0, 3.2],
            [6.0, 1.0, 3.2],
            [6.0, 6.0, 3.2],
            [0.0, 6.0, 3.2],
        ],
        [0.0, 0.0, -1.0],
        13,
        ObjectKind::Face,
        true,
    );
    objects.push(make_record(
        13,
        ObjectKind::Face,
        "Upper_Floor_Slab",
        Some(room2_id),
        Some(room2_id),
        Some("Floor"),
        Some("Surface"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([0.0, 1.0, 3.2], [6.0, 6.0, 3.2]),
    ));

    // Story 2 South Wall (id 14) + Clerestory Window (id 15) + Louver Shade (id 16)
    let u_win = (0.8, 5.2, 4.0, 5.6);
    add_punched_y_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        1.0,
        0.0,
        6.0,
        3.2,
        6.2,
        [0.0, -1.0, 0.0],
        14,
        &[u_win],
    );
    objects.push(make_record(
        14,
        ObjectKind::Face,
        "Upper_South_Wall",
        Some(room2_id),
        Some(room2_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        Some(0.48),
        Bounds3::new([0.0, 1.0, 3.2], [6.0, 1.0, 6.2]),
    ));

    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [u_win.0, 1.0, u_win.2],
            [u_win.1, 1.0, u_win.2],
            [u_win.1, 1.0, u_win.3],
            [u_win.0, 1.0, u_win.3],
        ],
        [0.0, -1.0, 0.0],
        15,
        ObjectKind::Aperture,
        true,
    );
    objects.push(make_record(
        15,
        ObjectKind::Aperture,
        "Upper_South_Win",
        Some(14),
        Some(room2_id),
        None,
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([u_win.0, 1.0, u_win.2], [u_win.1, 1.0, u_win.3]),
    ));

    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.6, 0.2, 5.75],
            [5.4, 0.2, 5.75],
            [5.4, 1.0, 5.75],
            [0.6, 1.0, 5.75],
        ],
        [0.0, 0.0, 1.0],
        16,
        ObjectKind::Shade,
        true,
    );
    objects.push(make_record(
        16,
        ObjectKind::Shade,
        "Upper_South_Shade",
        Some(14),
        Some(room2_id),
        None,
        None,
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([0.6, 0.2, 5.75], [5.4, 1.0, 5.75]),
    ));

    // Story 2 East Wall (id 17) + East Window (id 18)
    let ue_win = (2.0, 5.0, 4.0, 5.5);
    add_punched_x_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        6.0,
        1.0,
        6.0,
        3.2,
        6.2,
        [1.0, 0.0, 0.0],
        17,
        &[ue_win],
    );
    objects.push(make_record(
        17,
        ObjectKind::Face,
        "Upper_East_Wall",
        Some(room2_id),
        Some(room2_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        Some(0.30),
        Bounds3::new([6.0, 1.0, 3.2], [6.0, 6.0, 6.2]),
    ));
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [6.0, ue_win.0, ue_win.2],
            [6.0, ue_win.1, ue_win.2],
            [6.0, ue_win.1, ue_win.3],
            [6.0, ue_win.0, ue_win.3],
        ],
        [1.0, 0.0, 0.0],
        18,
        ObjectKind::Aperture,
        true,
    );
    objects.push(make_record(
        18,
        ObjectKind::Aperture,
        "Upper_East_Win",
        Some(17),
        Some(room2_id),
        None,
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([6.0, ue_win.0, ue_win.2], [6.0, ue_win.1, ue_win.3]),
    ));

    // Story 2 North & West Walls (id 19, 20)
    add_punched_y_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        6.0,
        0.0,
        6.0,
        3.2,
        6.2,
        [0.0, 1.0, 0.0],
        19,
        &[],
    );
    objects.push(make_record(
        19,
        ObjectKind::Face,
        "Upper_North_Wall",
        Some(room2_id),
        Some(room2_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([0.0, 6.0, 3.2], [6.0, 6.0, 6.2]),
    ));
    add_punched_x_wall(
        &mut vertices,
        &mut indices,
        &mut edges,
        0.0,
        1.0,
        6.0,
        3.2,
        6.2,
        [-1.0, 0.0, 0.0],
        20,
        &[],
    );
    objects.push(make_record(
        20,
        ObjectKind::Face,
        "Upper_West_Wall",
        Some(room2_id),
        Some(room2_id),
        Some("Wall"),
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([0.0, 1.0, 3.2], [0.0, 6.0, 6.2]),
    ));

    // Upper Roof (id 21)
    let upper_roof_id = 21;
    add_quad(
        &mut vertices,
        &mut indices,
        &mut edges,
        [
            [0.0, 1.0, 6.2],
            [6.0, 1.0, 6.2],
            [6.0, 6.0, 6.2],
            [0.0, 6.0, 6.2],
        ],
        [0.0, 0.0, 1.0],
        upper_roof_id,
        ObjectKind::Face,
        true,
    );
    objects.push(make_record(
        upper_roof_id,
        ObjectKind::Face,
        "Upper_Roof",
        Some(room2_id),
        Some(room2_id),
        Some("RoofCeiling"),
        Some("Outdoors"),
        "Level_2",
        "Penthouse_Zone",
        None,
        Bounds3::new([0.0, 1.0, 6.2], [6.0, 6.0, 6.2]),
    ));

    let mut bounds = Bounds3::empty();
    for v in &vertices {
        bounds.expand_point(v.position);
    }

    SampleBuilding {
        scene: SceneData {
            model_identifier: "Sample_Stepped_Office".to_owned(),
            display_name: Some("Sample Stepped Office".to_owned()),
            units: Some("Meters".to_owned()),
            source_path: None,
            bounds,
            vertices,
            indices,
            edge_vertices: edges,
            objects,
            stories: vec!["Level_1".to_owned(), "Level_2".to_owned()],
        },
        room1_id,
        room2_id,
        floor1_id,
        south_wall1_id,
        south_ap1_id,
        south_shade1_id,
        upper_roof_id,
        terrace_roof_id,
    }
}

fn screenshot_dir() -> PathBuf {
    std::env::var_os("LBT_RENDERER_TEST_OUT_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir)
}

fn save_png(name: &str, bytes: &[u8]) {
    assert!(bytes.starts_with(b"\x89PNG\r\n\x1a\n"), "valid PNG signature");
    let dir = screenshot_dir();
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join(name), bytes).unwrap();
}

fn assert_image_has_contrast(rgba: &[u8]) {
    assert!(!rgba.is_empty());
    let first = &rgba[0..4];
    let diff = rgba.chunks_exact(4).any(|px| {
        (px[0] as i32 - first[0] as i32).abs() > 12
            || (px[1] as i32 - first[1] as i32).abs() > 12
            || (px[2] as i32 - first[2] as i32).abs() > 12
    });
    assert!(diff, "rendered image should contain visible scene contrast");
}

#[test]
fn renders_axon_top_section_ghost_context_and_light_mode() {
    let sample = build_sample_building();
    let mut renderer = BuildingRenderer::new().expect("wgpu renderer should initialize");
    eprintln!(
        "lbt-renderer-wgpu test adapter: {} ({:?}, MSAA {}x)",
        renderer.adapter_info().name,
        renderer.adapter_info().backend,
        renderer.sample_count()
    );

    renderer.set_scene(&sample.scene);

    // 1. Axon Dark Studio (default ColorBy::Type)
    renderer.set_render_state(&RenderState {
        selected_ids: vec![sample.south_shade1_id],
        ..Default::default()
    });
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, sample.scene.bounds, None);

    let mut rgba_buf = Vec::new();
    renderer.render_rgba(960, 540, &mut rgba_buf).unwrap();
    assert_eq!(rgba_buf.len(), 960 * 540 * 4);
    assert_image_has_contrast(&rgba_buf);
    let axon_png = renderer.render_png(960, 540).unwrap();
    save_png("gpu_test_axon.png", &axon_png);

    // 2. Top Ortho
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, sample.scene.bounds, None);
    assert!(renderer.camera().is_orthographic());
    let top_png = renderer.render_png(960, 540).unwrap();
    save_png("gpu_test_top.png", &top_png);

    // 3. Section Cut at Z = 1.6m from Axon view
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, sample.scene.bounds, None);
    renderer.set_render_state(&RenderState {
        section: Some(SectionSpec {
            enabled: true,
            axis: SectionAxis::Z,
            value: Some(1.6),
            story: None,
            invert: false,
        }),
        ..Default::default()
    });
    let section_png = renderer.render_png(960, 540).unwrap();
    assert_ne!(section_png, axon_png);
    save_png("gpu_test_section.png", &section_png);

    // 4. Ghost Context Highlight (South wall + aperture + shade highlighted, error on upper roof)
    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Type,
        highlighted_ids: vec![
            sample.south_wall1_id,
            sample.south_ap1_id,
            sample.south_shade1_id,
        ],
        isolation_mode: IsolationMode::GhostContext,
        validation_error_ids: vec![sample.upper_roof_id],
        dark_mode: true,
        show_edges: true,
        ..Default::default()
    });
    let ghost_png = renderer.render_png(960, 540).unwrap();
    assert_ne!(ghost_png, axon_png);
    save_png("gpu_test_ghost_context.png", &ghost_png);

    // 5. Light Studio with ColorBy::Story
    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Story,
        dark_mode: false,
        show_edges: true,
        ..Default::default()
    });
    let light_png = renderer.render_png(960, 540).unwrap();
    save_png("gpu_test_light_story.png", &light_png);
}

#[test]
fn pick_at_returns_accurate_object_id_and_world_point_and_respects_section_and_isolate() {
    let sample = build_sample_building();
    let mut renderer = BuildingRenderer::new().expect("wgpu renderer should initialize");
    renderer.set_scene(&sample.scene);
    renderer.set_render_state(&RenderState::default());

    let w = 800;
    let h = 600;
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, sample.scene.bounds, None);

    // Pick center of Upper Roof ([3.0, 3.5, 6.2])
    let upper_pt = [3.0, 3.5, 6.2];
    let px = renderer
        .camera()
        .project_world(upper_pt, w, h)
        .expect("upper roof visible");
    let hit = renderer
        .pick_at(px[0], px[1], w, h)
        .unwrap()
        .expect("should hit upper roof");
    assert_eq!(hit.object_id, sample.upper_roof_id);
    assert!(
        (hit.world_point[2] - 6.2).abs() < 0.05,
        "world_point z should be ~6.2, got {:?}",
        hit.world_point
    );
    assert!((hit.world_point[0] - 3.0).abs() < 0.15);
    assert!((hit.world_point[1] - 3.5).abs() < 0.15);

    // Pick center of Lower Terrace Roof ([8.0, 3.0, 3.2])
    let terrace_pt = [8.0, 3.0, 3.2];
    let t_px = renderer
        .camera()
        .project_world(terrace_pt, w, h)
        .expect("terrace visible");
    let t_hit = renderer
        .pick_at(t_px[0], t_px[1], w, h)
        .unwrap()
        .expect("should hit terrace roof");
    assert_eq!(t_hit.object_id, sample.terrace_roof_id);
    assert!((t_hit.world_point[2] - 3.2).abs() < 0.05);

    // Background pixel should return None
    assert!(renderer.pick_at(2.0, 2.0, w, h).unwrap().is_none());
    // Out-of-bounds should return Ok(None)
    assert!(renderer.pick_at(-5.0, 10.0, w, h).unwrap().is_none());
    assert!(renderer.pick_at(900.0, 10.0, w, h).unwrap().is_none());

    // Section cut at Z = 1.6 should slice away both roofs and hit Ground Floor at Z = 0.0
    renderer.set_render_state(&RenderState {
        section: Some(SectionSpec {
            enabled: true,
            axis: SectionAxis::Z,
            value: Some(1.6),
            story: None,
            invert: false,
        }),
        ..Default::default()
    });
    let floor_hit = renderer
        .pick_at(t_px[0], t_px[1], w, h)
        .unwrap()
        .expect("floor below section cut should be picked");
    assert_eq!(floor_hit.object_id, sample.floor1_id);
    assert!(
        floor_hit.world_point[2].abs() < 0.05,
        "ground floor z should be ~0.0, got {:?}",
        floor_hit.world_point
    );

    // Room-level Isolate mode: isolate Room 1 -> Upper Roof (Room 2) disappears and ray lands on Room 1 Ground Floor!
    renderer.set_render_state(&RenderState {
        highlighted_ids: vec![sample.room1_id],
        isolation_mode: IsolationMode::Isolate,
        ..Default::default()
    });
    let r1_floor_hit = renderer
        .pick_at(px[0], px[1], w, h)
        .unwrap()
        .expect("room1 ground floor underneath hidden room2 roof should be picked");
    assert_eq!(r1_floor_hit.object_id, sample.floor1_id);
    assert!(r1_floor_hit.world_point[2].abs() < 0.05);

    let r1_hit = renderer
        .pick_at(t_px[0], t_px[1], w, h)
        .unwrap()
        .expect("room1 terrace should remain pickable when room1 is isolated");
    assert_eq!(r1_hit.object_id, sample.terrace_roof_id);

    // Isolate ONLY terrace_roof_id -> picking [3.0, 3.5] hits nothing (None)!
    renderer.set_render_state(&RenderState {
        highlighted_ids: vec![sample.terrace_roof_id],
        isolation_mode: IsolationMode::Isolate,
        ..Default::default()
    });
    assert!(
        renderer.pick_at(px[0], px[1], w, h).unwrap().is_none(),
        "non-isolated footprint must return None"
    );

    // Story-based section cut (story: Some("Level_1"), value: None) cuts away Level_1 roof and picks floor!
    renderer.set_render_state(&RenderState {
        section: Some(SectionSpec {
            enabled: true,
            axis: SectionAxis::Z,
            value: None,
            story: Some("Level_1".to_owned()),
            invert: false,
        }),
        ..Default::default()
    });
    let story_cut_hit = renderer
        .pick_at(t_px[0], t_px[1], w, h)
        .unwrap()
        .expect("floor below Level_1 story section cut should be picked");
    assert_eq!(story_cut_hit.object_id, sample.floor1_id);
}

#[test]
fn software_warp_fallback_renders_and_picks() {
    let sample = build_sample_building();
    let mut renderer =
        BuildingRenderer::new_software().expect("software/WARP fallback renderer should initialize");
    eprintln!(
        "lbt-renderer-wgpu software fallback adapter: {} ({:?})",
        renderer.adapter_info().name,
        renderer.adapter_info().backend
    );
    renderer.set_scene(&sample.scene);
    renderer
        .camera_mut()
        .fit_objects(&sample.scene, &[sample.room1_id]);
    let mut rgba = Vec::new();
    renderer.render_rgba(320, 180, &mut rgba).unwrap();
    assert_eq!(rgba.len(), 320 * 180 * 4);
    assert_image_has_contrast(&rgba);

    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, sample.scene.bounds, None);
    let px = renderer
        .camera()
        .project_world([3.0, 3.5, 6.2], 320, 180)
        .unwrap();
    let hit = renderer
        .pick_at(px[0], px[1], 320, 180)
        .unwrap()
        .expect("WARP pick_at should hit upper roof");
    assert_eq!(hit.object_id, sample.upper_roof_id);
}

#[test]
fn renders_real_hbjson_single_family_home_from_lbt_scene() {
    let hbjson = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("resources")
        .join("honeybee-core")
        .join("tests")
        .join("json")
        .join("single_family_home.hbjson");
    let scene = lbt_scene::load_hbjson_file(&hbjson, None)
        .expect("single_family_home.hbjson should load via lbt_scene");
    assert!(!scene.vertices.is_empty());
    assert!(!scene.indices.is_empty());

    let mut renderer = BuildingRenderer::new().expect("wgpu renderer should initialize");
    renderer.set_scene(&scene);
    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Type,
        dark_mode: true,
        show_edges: true,
        ..Default::default()
    });
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, scene.bounds, None);
    let png = renderer.render_png(960, 540).unwrap();
    save_png("gpu_test_single_family_home.png", &png);

    // Verify center pick hits a real object in the Honeybee model
    let center_px = renderer
        .camera()
        .project_world(scene.bounds.center(), 960, 540)
        .unwrap();
    let hit = renderer.pick_at(center_px[0], center_px[1], 960, 540).unwrap();
    assert!(hit.is_some(), "picking center of single_family_home should hit geometry");
}

#[test]
fn handles_unaligned_widths_zero_dimensions_and_reuses_rgba_capacity() {
    let sample = build_sample_building();
    let mut renderer = BuildingRenderer::new().expect("wgpu renderer should initialize");
    renderer.set_scene(&sample.scene);
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, sample.scene.bounds, None);

    // Odd dimensions where width * 4 is not 256-byte aligned (333 * 4 = 1332)
    let mut rgba = Vec::new();
    renderer.render_rgba(333, 211, &mut rgba).unwrap();
    assert_eq!(rgba.len(), 333 * 211 * 4);
    assert_image_has_contrast(&rgba);

    // Capacity reuse check
    let cap_before = rgba.capacity();
    let ptr_before = rgba.as_ptr();
    renderer.render_rgba(333, 211, &mut rgba).unwrap();
    assert_eq!(rgba.len(), 333 * 211 * 4);
    assert_eq!(rgba.capacity(), cap_before);
    assert_eq!(rgba.as_ptr(), ptr_before);

    // Pick on odd viewport size
    let center_px = renderer
        .camera()
        .project_world([5.0, 3.0, 3.2], 333, 211)
        .unwrap();
    let _ = renderer.pick_at(center_px[0], center_px[1], 333, 211).unwrap();

    // Zero dimensions should return InvalidDimensions error
    assert_eq!(
        renderer.render_rgba(0, 100, &mut rgba),
        Err(RendererError::InvalidDimensions {
            width: 0,
            height: 100
        })
    );
    assert_eq!(
        renderer.pick_at(0.0, 0.0, 100, 0),
        Err(RendererError::InvalidDimensions {
            width: 100,
            height: 0
        })
    );
}

#[test]
fn room_edit_mode_fades_rest_of_model_and_prioritizes_active_room_picking() {
    let sample = build_sample_building();
    let mut renderer = BuildingRenderer::new().expect("wgpu renderer should initialize");
    renderer.set_scene(&sample.scene);

    let w = 800;
    let h = 600;
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, sample.scene.bounds, None);

    // Full model render vs Room Edit Mode on Room 1 (fades Room 2 into clean single-layer ghost shell)
    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Type,
        dark_mode: true,
        show_edges: true,
        ..Default::default()
    });
    let full_png = renderer.render_png(w, h).unwrap();

    let edit_r1_state = RenderState {
        color_by: ColorBy::Type,
        editing_room_id: Some(sample.room1_id),
        selected_ids: vec![sample.south_wall1_id],
        dark_mode: true,
        show_edges: true,
        ..Default::default()
    };
    renderer.set_render_state(&edit_r1_state);
    let edit_r1_png = renderer.render_png(w, h).unwrap();
    assert_ne!(
        edit_r1_png, full_png,
        "Room Edit Mode must visibly fade non-active rooms"
    );
    save_png("gpu_test_room_edit_mode.png", &edit_r1_png);

    // Switch to Top view where ghosted Room 2 Upper Roof (z=6.2) sits directly ABOVE Room 1 Ground Floor (z=0.0).
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, sample.scene.bounds, None);
    let stacked_px = renderer
        .camera()
        .project_world([3.0, 3.5, 6.2], w, h)
        .expect("stacked point visible");

    // In Room Edit Mode for Room 1, GPU pick_at AND CPU pick_scene_ray MUST pass through ghosted
    // Room 2 roof and pick Room 1 Ground Floor!
    let gpu_hit = renderer
        .pick_at(stacked_px[0], stacked_px[1], w, h)
        .unwrap()
        .expect("GPU pick_at should pick Room 1 floor beneath ghosted Room 2");
    assert_eq!(gpu_hit.object_id, sample.floor1_id);
    assert_eq!(gpu_hit.owner_room_id, Some(sample.room1_id));
    assert!(!gpu_hit.is_ghosted);
    assert!(gpu_hit.world_point[2].abs() < 0.05);

    let (ray_o, ray_d) = renderer.camera().screen_ray(stacked_px[0], stacked_px[1], w, h);
    let cpu_hit = pick_scene_ray(&sample.scene, &edit_r1_state, ray_o, ray_d)
        .expect("CPU pick_scene_ray should match GPU pick_at in Room Edit Mode");
    assert_eq!(cpu_hit.object_id, sample.floor1_id);
    assert_eq!(cpu_hit.owner_room_id, Some(sample.room1_id));
    assert!(!cpu_hit.is_ghosted);

    // Switch to Room Edit Mode for Room 2: clicking on Room 1's exposed terrace ([8.0, 3.0, 3.2],
    // where Room 2 has no geometry) returns the ghosted Room 1 terrace with is_ghosted == true!
    let edit_r2_state = RenderState {
        editing_room_id: Some(sample.room2_id),
        ..Default::default()
    };
    renderer.set_render_state(&edit_r2_state);
    let terrace_px = renderer
        .camera()
        .project_world([8.0, 3.0, 3.2], w, h)
        .expect("terrace visible");
    let outside_gpu = renderer
        .pick_at(terrace_px[0], terrace_px[1], w, h)
        .unwrap()
        .expect("clicking ghosted terrace outside Room 2 returns ghosted hit");
    assert_eq!(outside_gpu.object_id, sample.terrace_roof_id);
    assert_eq!(outside_gpu.owner_room_id, Some(sample.room1_id));
    assert!(outside_gpu.is_ghosted);

    let (t_ray_o, t_ray_d) = renderer.camera().screen_ray(terrace_px[0], terrace_px[1], w, h);
    let outside_cpu = pick_scene_ray(&sample.scene, &edit_r2_state, t_ray_o, t_ray_d)
        .expect("CPU raypick should also return ghosted hit outside Room 2");
    assert_eq!(outside_cpu.object_id, sample.terrace_roof_id);
    assert_eq!(outside_cpu.owner_room_id, Some(sample.room1_id));
    assert!(outside_cpu.is_ghosted);
}

#[test]
fn paired_coplanar_air_boundaries_do_not_double_blend_and_light_theme_renders_vibrant_honeybee_colors() {
    // Build two paired coplanar opposite-normal Air Boundary quads at z = 2.0 (Room 10 & Room 20)
    // vs a single Air Boundary quad at the same location, and verify pixel alpha-blended output
    // matches (proving FLAG_CULL_BACK prevents coplanar double-blending).
    let make_air_boundary_scene = |paired: bool| -> SceneData {
        let mut vertices = Vec::new();
        let mut indices = Vec::new();
        let mut edges = Vec::new();
        let mut objects = Vec::new();

        objects.push(make_record(
            10,
            ObjectKind::Room,
            "Room_Bottom",
            None,
            Some(10),
            None,
            None,
            "L1",
            "Z1",
            None,
            Bounds3::new([-2.0, -2.0, 0.0], [2.0, 2.0, 2.0]),
        ));
        add_quad(
            &mut vertices,
            &mut indices,
            &mut edges,
            [
                [-2.0, -2.0, 2.0],
                [2.0, -2.0, 2.0],
                [2.0, 2.0, 2.0],
                [-2.0, 2.0, 2.0],
            ],
            [0.0, 0.0, 1.0],
            11,
            ObjectKind::Face,
            false,
        );
        objects.push(make_record(
            11,
            ObjectKind::Face,
            "Air_A",
            Some(10),
            Some(10),
            Some("AirBoundary"),
            Some("Surface"),
            "L1",
            "Z1",
            None,
            Bounds3::new([-2.0, -2.0, 2.0], [2.0, 2.0, 2.0]),
        ));

        if paired {
            objects.push(make_record(
                20,
                ObjectKind::Room,
                "Room_Top",
                None,
                Some(20),
                None,
                None,
                "L2",
                "Z2",
                None,
                Bounds3::new([-2.0, -2.0, 2.0], [2.0, 2.0, 4.0]),
            ));
            // Opposite winding & opposite normal (-Z), offset 4 mm matching lbt-scene room inset
            add_quad(
                &mut vertices,
                &mut indices,
                &mut edges,
                [
                    [-2.0, -2.0, 2.004],
                    [-2.0, 2.0, 2.004],
                    [2.0, 2.0, 2.004],
                    [2.0, -2.0, 2.004],
                ],
                [0.0, 0.0, -1.0],
                21,
                ObjectKind::Face,
                false,
            );
            objects.push(make_record(
                21,
                ObjectKind::Face,
                "Air_B",
                Some(20),
                Some(20),
                Some("AirBoundary"),
                Some("Surface"),
                "L2",
                "Z2",
                None,
                Bounds3::new([-2.0, -2.0, 2.004], [2.0, 2.0, 2.004]),
            ));
        }

        SceneData {
            model_identifier: "AirBoundary_Pair_Test".to_owned(),
            bounds: Bounds3::new([-2.0, -2.0, 0.0], [2.0, 2.0, 4.0]),
            vertices,
            indices,
            edge_vertices: edges,
            objects,
            ..Default::default()
        }
    };

    let mut renderer = BuildingRenderer::new_software().expect("WARP renderer initializes");
    let single = make_air_boundary_scene(false);
    let paired = make_air_boundary_scene(true);

    let state = RenderState {
        color_by: ColorBy::Type,
        dark_mode: true,
        show_edges: false,
        ..Default::default()
    };

    renderer.set_scene(&single);
    renderer.set_render_state(&state);
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, single.bounds, None);
    let mut single_rgba = Vec::new();
    renderer.render_rgba(128, 128, &mut single_rgba).unwrap();

    renderer.set_scene(&paired);
    renderer.set_render_state(&state);
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Top, single.bounds, None);
    let mut paired_rgba = Vec::new();
    renderer.render_rgba(128, 128, &mut paired_rgba).unwrap();

    // Center pixel must match closely (single-drawn translucent yellow, not double-blended!)
    let center = (64 * 128 + 64) * 4;
    let sc = &single_rgba[center..center + 4];
    let pc = &paired_rgba[center..center + 4];
    for ch in 0..3 {
        assert!(
            (sc[ch] as i32 - pc[ch] as i32).abs() <= 4,
            "paired AirBoundary should not double-blend: single={sc:?}, paired={pc:?}"
        );
    }

    // Also verify real single_family_home renders cleanly in Light mode + Room Edit Mode on WARP/GPU
    let hbjson = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("resources")
        .join("honeybee-core")
        .join("tests")
        .join("json")
        .join("single_family_home.hbjson");
    let scene = lbt_scene::load_hbjson_file(&hbjson, None).expect("load single_family_home");
    let first_room_id = scene
        .objects
        .iter()
        .find(|o| o.kind == ObjectKind::Room)
        .map(|o| o.object_id)
        .expect("single_family_home has rooms");

    renderer.set_scene(&scene);
    renderer
        .camera_mut()
        .apply_preset(CameraPreset::Axon, scene.bounds, None);
    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Type,
        dark_mode: false,
        show_edges: true,
        ..Default::default()
    });
    let light_png = renderer.render_png(640, 360).unwrap();
    save_png("gpu_test_sfh_light_type.png", &light_png);

    renderer.set_render_state(&RenderState {
        color_by: ColorBy::Type,
        editing_room_id: Some(first_room_id),
        dark_mode: true,
        show_edges: true,
        ..Default::default()
    });
    let edit_png = renderer.render_png(640, 360).unwrap();
    save_png("gpu_test_sfh_room_edit.png", &edit_png);
    assert_ne!(light_png, edit_png);
}
