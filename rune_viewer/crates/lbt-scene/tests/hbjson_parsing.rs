use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};

use lbt_scene::{
    color_for_object, load_hbjson_file, load_hbjson_str, orientation_label, resolve_scene_colors,
    ColorBy, ObjectKind, SceneData, SceneError,
};

fn mesh_area_for_object(scene: &SceneData, object_id: u32) -> f64 {
    let mut area = 0.0_f64;
    for tri in scene.indices.chunks_exact(3) {
        let v0 = &scene.vertices[tri[0] as usize];
        if v0.object_id != object_id {
            continue;
        }
        let v1 = &scene.vertices[tri[1] as usize];
        let v2 = &scene.vertices[tri[2] as usize];
        let a = [
            f64::from(v1.position[0] - v0.position[0]),
            f64::from(v1.position[1] - v0.position[1]),
            f64::from(v1.position[2] - v0.position[2]),
        ];
        let b = [
            f64::from(v2.position[0] - v0.position[0]),
            f64::from(v2.position[1] - v0.position[1]),
            f64::from(v2.position[2] - v0.position[2]),
        ];
        let cx = a[1] * b[2] - a[2] * b[1];
        let cy = a[2] * b[0] - a[0] * b[2];
        let cz = a[0] * b[1] - a[1] * b[0];
        area += 0.5 * (cx * cx + cy * cy + cz * cz).sqrt();
    }
    area
}

fn assert_scene_invariants(scene: &SceneData) {
    assert_eq!(scene.indices.len() % 3, 0);
    assert_eq!(scene.edge_vertices.len() % 2, 0);

    let mut seen_ids = HashSet::new();
    for obj in &scene.objects {
        assert!(obj.object_id >= 1, "object_id 0 is reserved for background");
        assert!(seen_ids.insert(obj.object_id), "duplicate object_id {}", obj.object_id);
        assert_eq!(obj.target.target_type, "honeybee_object");
        assert_eq!(obj.target.domain, "honeybee");
        assert_eq!(obj.target.model_identifier, scene.model_identifier);
        assert_eq!(obj.target.object_type, obj.kind);
        assert_eq!(obj.target.object_identifier, obj.identifier);
        assert_eq!(obj.target.identifier.as_deref(), Some(obj.identifier.as_str()));
        assert!(obj.centroid.iter().all(|c| c.is_finite()));
    }

    for v in &scene.vertices {
        assert!(v.position.iter().all(|c| c.is_finite()));
        assert!(v.normal.iter().all(|c| c.is_finite()));
        assert!(scene.object_by_id(v.object_id).is_some());
        assert_eq!(
            ObjectKind::from_kind_code(v.kind_code),
            scene.object_by_id(v.object_id).map(|o| o.kind)
        );
    }

    for tri in scene.indices.chunks_exact(3) {
        for &idx in tri {
            assert!((idx as usize) < scene.vertices.len());
        }
        let v0 = &scene.vertices[tri[0] as usize];
        let v1 = &scene.vertices[tri[1] as usize];
        let v2 = &scene.vertices[tri[2] as usize];
        assert_eq!(v0.object_id, v1.object_id);
        assert_eq!(v0.object_id, v2.object_id);

        let a = [
            f64::from(v1.position[0] - v0.position[0]),
            f64::from(v1.position[1] - v0.position[1]),
            f64::from(v1.position[2] - v0.position[2]),
        ];
        let b = [
            f64::from(v2.position[0] - v0.position[0]),
            f64::from(v2.position[1] - v0.position[1]),
            f64::from(v2.position[2] - v0.position[2]),
        ];
        let cx = a[1] * b[2] - a[2] * b[1];
        let cy = a[2] * b[0] - a[0] * b[2];
        let cz = a[0] * b[1] - a[1] * b[0];
        let dot = cx * f64::from(v0.normal[0]) + cy * f64::from(v0.normal[1]) + cz * f64::from(v0.normal[2]);
        assert!(
            dot >= -1e-7,
            "triangle winding opposes vertex normal for object_id {} (dot={dot})",
            v0.object_id
        );
    }

    for ev in &scene.edge_vertices {
        assert!(ev.position.iter().all(|c| c.is_finite()));
        assert!(scene.object_by_id(ev.object_id).is_some());
    }
}

#[test]
fn parses_multi_room_multi_story_with_apertures_doors_and_shades() {
    let json = r#"{
      "type": "Model",
      "identifier": "OfficeTower",
      "display_name": "Office Tower",
      "units": "Meters",
      "rooms": [
        {
          "type": "Room",
          "identifier": "Room_L2",
          "display_name": "Level 2 Office",
          "story": "Story_2",
          "zone": "Zone_North",
          "properties": {
            "energy": {
              "program_type": {"identifier": "OpenOffice"},
              "construction_set": "SteelFrame",
              "hvac": {"identifier": "VAV_Chiller"}
            }
          },
          "faces": [
            {
              "type": "Face",
              "identifier": "L2_Floor",
              "face_type": "Floor",
              "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["L1_Roof", "Room_L1"]},
              "geometry": {"type": "Face3D", "boundary": [[0,0,3],[10,0,3],[10,6,3],[0,6,3]]}
            },
            {
              "type": "Face",
              "identifier": "L2_Roof",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,6],[10,0,6],[10,6,6],[0,6,6]]}
            }
          ]
        },
        {
          "type": "Room",
          "identifier": "Room_L1",
          "display_name": "Level 1 Lobby",
          "story": "Story_1",
          "zone": "Zone_South",
          "properties": {
            "energy": {
              "program_type": "LobbyProgram",
              "construction_set": "ConcreteSet",
              "hvac": "IdealAir"
            }
          },
          "indoor_shades": [
            {
              "type": "Shade",
              "identifier": "L1_Baffle",
              "geometry": {"type": "Face3D", "boundary": [[2,2,2.5],[8,2,2.5],[8,2.5,2.5],[2,2.5,2.5]]}
            }
          ],
          "faces": [
            {
              "type": "Face",
              "identifier": "L1_Floor",
              "face_type": "Floor",
              "boundary_condition": {"type": "Ground"},
              "geometry": {"type": "Face3D", "boundary": [[0,6,0],[10,6,0],[10,0,0],[0,0,0]]}
            },
            {
              "type": "Face",
              "identifier": "L1_SouthWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [0,0,0], "x": [1,0,0]},
                "boundary": [[0,0,0],[10,0,0],[10,0,3],[0,0,3]]
              },
              "outdoor_shades": [
                {
                  "type": "Shade",
                  "identifier": "Face_Canopy",
                  "geometry": {"type": "Face3D", "boundary": [[0,0,2.8],[10,0,2.8],[10,-1,2.8],[0,-1,2.8]]}
                }
              ],
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "South_Win",
                  "geometry": {
                    "type": "Face3D",
                    "plane": {"n": [0,-1,0], "o": [1,0,1], "x": [1,0,0]},
                    "boundary": [[1,0,1],[5,0,1],[5,0,2.5],[1,0,2.5]]
                  },
                  "outdoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Win_Overhang",
                      "geometry": {"type": "Face3D", "boundary": [[1,0,2.5],[5,0,2.5],[5,-0.5,2.5],[1,-0.5,2.5]]}
                    }
                  ]
                }
              ],
              "doors": [
                {
                  "type": "Door",
                  "identifier": "South_Door",
                  "is_glass": false,
                  "geometry": {
                    "type": "Face3D",
                    "plane": {"n": [0,-1,0], "o": [6,0,0.2], "x": [1,0,0]},
                    "boundary": [[6,0,0.2],[8,0,0.2],[8,0,2.2],[6,0,2.2]]
                  },
                  "indoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Door_Screen",
                      "geometry": {"type": "Face3D", "boundary": [[6,0.2,2.2],[8,0.2,2.2],[8,0.2,2.4],[6,0.2,2.4]]}
                    }
                  ]
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "L1_Roof",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["L2_Floor", "Room_L2"]},
              "geometry": {"type": "Face3D", "boundary": [[0,0,3],[10,0,3],[10,6,3],[0,6,3]]}
            },
            {
              "type": "Face",
              "identifier": "L1_EastAir",
              "face_type": "AirBoundary",
              "boundary_condition": {"type": "Surface"},
              "geometry": {"type": "Face3D", "boundary": [[10,0,0],[10,6,0],[10,6,3],[10,0,3]]}
            }
          ]
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, Some("garden_42"), Some("office.hbjson".into())).unwrap();
    assert_scene_invariants(&scene);

    // Stories sorted by ascending min Z elevation.
    assert_eq!(scene.stories, vec!["Story_1", "Story_2"]);
    assert_eq!(scene.source_path.as_deref(), Some("office.hbjson"));
    assert_eq!(scene.bounds.min, [0.0, -1.0, 0.0]);
    assert_eq!(scene.bounds.max, [10.0, 6.0, 6.0]);

    let room1 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Room_L1")
        .unwrap();
    assert_eq!(room1.kind, ObjectKind::Room);
    assert_eq!(room1.target.garden_id.as_deref(), Some("garden_42"));
    assert_eq!(room1.parent_object_id, None);
    assert!((room1.area.unwrap() - 60.0).abs() < 1e-6);
    // Exterior wall = 30.0 m2, aperture = 4 * 1.5 = 6.0 m2 -> wwr = 0.2
    assert!((room1.wwr.unwrap() - 0.2).abs() < 1e-5);
    assert_eq!(room1.program_type.as_deref(), Some("LobbyProgram"));
    assert_eq!(room1.construction_set.as_deref(), Some("ConcreteSet"));
    assert_eq!(room1.hvac.as_deref(), Some("IdealAir"));

    let room2 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Room_L2")
        .unwrap();
    assert_eq!(room2.program_type.as_deref(), Some("OpenOffice"));
    assert_eq!(room2.hvac.as_deref(), Some("VAV_Chiller"));

    let south_wall = scene
        .objects
        .iter()
        .find(|o| o.identifier == "L1_SouthWall")
        .unwrap();
    assert_eq!(south_wall.parent_object_id, Some(room1.object_id));
    assert_eq!(south_wall.story.as_deref(), Some("Story_1"));
    assert_eq!(south_wall.zone.as_deref(), Some("Zone_South"));
    assert!((south_wall.area.unwrap() - 30.0).abs() < 1e-6);
    assert!((south_wall.wwr.unwrap() - 0.2).abs() < 1e-5);
    // Punched wall mesh area = 30 - 6 (window) - 4 (door) = 20.0 m2!
    let punched_wall_area = mesh_area_for_object(&scene, south_wall.object_id);
    assert!(
        (punched_wall_area - 20.0).abs() < 1e-4,
        "expected punched wall area 20.0, got {punched_wall_area}"
    );
    assert_eq!(
        south_wall.target.parent,
        BTreeMap::from([("room_identifier".into(), "Room_L1".into())])
    );

    // Check child TargetRefs & parent_object_id hierarchy
    let win = scene
        .objects
        .iter()
        .find(|o| o.identifier == "South_Win")
        .unwrap();
    assert_eq!(win.parent_object_id, Some(south_wall.object_id));
    assert_eq!(
        win.target.parent,
        BTreeMap::from([
            ("room_identifier".into(), "Room_L1".into()),
            ("face_identifier".into(), "L1_SouthWall".into())
        ])
    );
    let win_edges: Vec<_> = scene
        .edge_vertices
        .iter()
        .filter(|e| e.object_id == win.object_id)
        .collect();
    // 4-edge window loop => 8 EdgeVertex items
    assert_eq!(win_edges.len(), 8);

    let win_shade = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Win_Overhang")
        .unwrap();
    assert_eq!(win_shade.parent_object_id, Some(win.object_id));
    assert_eq!(
        win_shade.target.parent,
        BTreeMap::from([
            ("room_identifier".into(), "Room_L1".into()),
            ("face_identifier".into(), "L1_SouthWall".into()),
            ("aperture_identifier".into(), "South_Win".into())
        ])
    );

    let door = scene
        .objects
        .iter()
        .find(|o| o.identifier == "South_Door")
        .unwrap();
    assert_eq!(door.parent_object_id, Some(south_wall.object_id));
    let door_shade = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Door_Screen")
        .unwrap();
    assert_eq!(door_shade.parent_object_id, Some(door.object_id));
    assert_eq!(
        door_shade.target.parent,
        BTreeMap::from([
            ("room_identifier".into(), "Room_L1".into()),
            ("face_identifier".into(), "L1_SouthWall".into()),
            ("door_identifier".into(), "South_Door".into())
        ])
    );

    let room_shade = scene
        .objects
        .iter()
        .find(|o| o.identifier == "L1_Baffle")
        .unwrap();
    assert_eq!(room_shade.parent_object_id, Some(room1.object_id));
    assert_eq!(room_shade.face_type.as_deref(), Some("IndoorShade"));
}

#[test]
fn non_convex_l_shape_and_explicit_holes_triangulate_without_plane() {
    let json = r#"{
      "type": "Model",
      "identifier": "ComplexPolygons",
      "rooms": [
        {
          "type": "Room",
          "identifier": "LRoom",
          "faces": [
            {
              "type": "Face",
              "identifier": "L_Floor",
              "face_type": "Floor",
              "boundary_condition": {"type": "Ground"},
              "geometry": {
                "type": "Face3D",
                "boundary": [[0,0,0],[0,10,0],[5,10,0],[5,5,0],[10,5,0],[10,0,0]]
              }
            },
            {
              "type": "Face",
              "identifier": "Donut_Roof",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "boundary": [[0,0,4],[10,0,4],[10,10,4],[0,10,4]],
                "holes": [
                  [[3,3,4],[3,7,4],[7,7,4],[7,3,4]]
                ]
              }
            }
          ]
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    let l_floor = scene
        .objects
        .iter()
        .find(|o| o.identifier == "L_Floor")
        .unwrap();
    assert!((l_floor.area.unwrap() - 75.0).abs() < 1e-5);
    assert!((mesh_area_for_object(&scene, l_floor.object_id) - 75.0).abs() < 1e-4);

    let donut_roof = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Donut_Roof")
        .unwrap();
    // 10*10 - 4*4 = 84.0
    assert!((donut_roof.area.unwrap() - 84.0).abs() < 1e-5);
    assert!((mesh_area_for_object(&scene, donut_roof.object_id) - 84.0).abs() < 1e-4);
    // 4 outer edges + 4 hole edges = 8 edges * 2 = 16 EdgeVertex items
    let roof_edges = scene
        .edge_vertices
        .iter()
        .filter(|e| e.object_id == donut_roof.object_id)
        .count();
    assert_eq!(roof_edges, 16);
}

#[test]
fn touching_and_degenerate_apertures_trigger_clean_normal_offset_fallback() {
    let json = r#"{
      "type": "Model",
      "identifier": "FallbackTest",
      "rooms": [
        {
          "type": "Room",
          "identifier": "R1",
          "faces": [
            {
              "type": "Face",
              "identifier": "Wall_TouchingDoor",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [0,0,0], "x": [1,0,0]},
                "boundary": [[0,0,0],[8,0,0],[8,0,3],[0,0,3]]
              },
              "doors": [
                {
                  "type": "Door",
                  "identifier": "Bottom_Touching_Door",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[1,0,0],[2.5,0,0],[2.5,0,2.1],[1,0,2.1]]
                  }
                }
              ],
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Neighbor_Win",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[4,0,1],[6,0,1],[6,0,2.5],[4,0,2.5]]
                  }
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "Wall_TouchingWindows",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,1,0], "o": [0,5,0], "x": [-1,0,0]},
                "boundary": [[8,5,0],[0,5,0],[0,5,3],[8,5,3]]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Win_Left",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[4,5,1],[1,5,1],[1,5,2],[4,5,2]]
                  }
                },
                {
                  "type": "Aperture",
                  "identifier": "Win_Right",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[7,5,1],[4,5,1],[4,5,2],[7,5,2]]
                  }
                }
              ]
            }
          ]
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    // Wall_TouchingDoor: door touches z=0 -> unpunched wall (area = 24.0) + subfaces offset along -Y by 0.003m!
    let wall1 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_TouchingDoor")
        .unwrap();
    assert!((mesh_area_for_object(&scene, wall1.object_id) - 24.0).abs() < 1e-4);

    let door = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Bottom_Touching_Door")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == door.object_id) {
        assert!((v.position[1] - (-0.003)).abs() < 1e-5, "got y={}", v.position[1]);
    }
    let win = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Neighbor_Win")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == win.object_id) {
        assert!((v.position[1] - (-0.003)).abs() < 1e-5);
    }

    // Wall_TouchingWindows: Win_Left & Win_Right share edge x=4 -> unpunched wall + subfaces offset along +Y by 0.003m!
    let wall2 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_TouchingWindows")
        .unwrap();
    assert!((mesh_area_for_object(&scene, wall2.object_id) - 24.0).abs() < 1e-4);
    let win_l = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Win_Left")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == win_l.object_id) {
        assert!((v.position[1] - 5.003).abs() < 1e-5);
    }
}

#[test]
fn parses_orphaned_geometry_shade_meshes_and_units() {
    let json = r#"{
      "type": "Model",
      "identifier": "OrphanAndMm",
      "units": "Millimeters",
      "orphaned_faces": [
        {
          "type": "Face",
          "identifier": "OrphanFace",
          "geometry": {"type": "Face3D", "boundary": [[0,0,0],[4000,0,0],[4000,0,3000],[0,0,3000]]},
          "apertures": [
            {
              "type": "Aperture",
              "identifier": "OrphanFaceAp",
              "geometry": {"type": "Face3D", "boundary": [[1000,0,1000],[3000,0,1000],[3000,0,2000],[1000,0,2000]]}
            }
          ]
        }
      ],
      "orphaned_apertures": [
        {
          "type": "Aperture",
          "identifier": "FloatingAp",
          "geometry": {"type": "Face3D", "boundary": [[5000,0,0],[6000,0,0],[6000,0,1000],[5000,0,1000]]}
        }
      ],
      "orphaned_doors": [
        {
          "type": "Door",
          "identifier": "FloatingDoor",
          "is_glass": true,
          "geometry": {"type": "Face3D", "boundary": [[7000,0,0],[8000,0,0],[8000,0,2000],[7000,0,2000]]}
        }
      ],
      "orphaned_shades": [
        {
          "type": "Shade",
          "identifier": "ContextBuilding",
          "is_detached": true,
          "geometry": {"type": "Face3D", "boundary": [[0,-5000,0],[10000,-5000,0],[10000,-5000,5000],[0,-5000,5000]]}
        }
      ],
      "shade_meshes": [
        {
          "type": "ShadeMesh",
          "identifier": "CanopyMesh",
          "geometry": {
            "type": "Mesh3D",
            "vertices": [[0,0,4000],[2000,0,4000],[2000,2000,4000],[0,2000,4000],[4000,0,4000]],
            "faces": [[0,1,2,3],[1,4,2]]
          }
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);
    assert_eq!(scene.units.as_deref(), Some("Millimeters"));

    let orphan_face = scene
        .objects
        .iter()
        .find(|o| o.identifier == "OrphanFace")
        .unwrap();
    assert_eq!(orphan_face.parent_object_id, None);
    assert!(orphan_face.target.parent.is_empty());
    // 4m * 3m = 12.0 m2 gross; punched = 12 - 2 = 10.0 m2
    assert!((orphan_face.area.unwrap() - 12.0).abs() < 1e-5);
    assert!((mesh_area_for_object(&scene, orphan_face.object_id) - 10.0).abs() < 1e-4);

    let orphan_face_ap = scene
        .objects
        .iter()
        .find(|o| o.identifier == "OrphanFaceAp")
        .unwrap();
    assert_eq!(orphan_face_ap.parent_object_id, Some(orphan_face.object_id));
    assert_eq!(
        orphan_face_ap.target.parent,
        BTreeMap::from([("face_identifier".into(), "OrphanFace".into())])
    );

    let floating_door = scene
        .objects
        .iter()
        .find(|o| o.identifier == "FloatingDoor")
        .unwrap();
    assert_eq!(floating_door.kind, ObjectKind::Door);
    assert_eq!(floating_door.face_type.as_deref(), Some("GlassDoor"));
    assert!((floating_door.area.unwrap() - 2.0).abs() < 1e-5);

    let ctx_shade = scene
        .objects
        .iter()
        .find(|o| o.identifier == "ContextBuilding")
        .unwrap();
    assert_eq!(ctx_shade.face_type.as_deref(), Some("ContextShade"));
    assert!((ctx_shade.area.unwrap() - 50.0).abs() < 1e-4);

    let canopy_mesh = scene
        .objects
        .iter()
        .find(|o| o.identifier == "CanopyMesh")
        .unwrap();
    assert_eq!(canopy_mesh.kind, ObjectKind::Shade);
    // 2x2 quad (4 m2) + triangle (2*2/2 = 2 m2) = 6 m2
    assert!((canopy_mesh.area.unwrap() - 6.0).abs() < 1e-4);
    // Quad (4 edges) + triangle (3 edges) with 1 shared edge (1,2) => 6 unique edges = 12 EdgeVertex items.
    let canopy_edges = scene
        .edge_vertices
        .iter()
        .filter(|e| e.object_id == canopy_mesh.object_id)
        .count();
    assert_eq!(canopy_edges, 12);
}

#[test]
fn handles_crossing_and_non_coplanar_apertures_dict_points_and_feet_units() {
    let json = r#"{
      "type": "Model",
      "identifier": "EdgeCasesModel",
      "units": "Feet",
      "rooms": [
        {
          "type": "Room",
          "identifier": "FootRoom",
          "faces": [
            {
              "type": "Face",
              "identifier": "CrossingWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0, -1, 0], "o": [0, 0, 0]},
                "boundary": [
                  {"x": 0.0, "y": 0.0, "z": 0.0},
                  {"x": 10.0, "y": 0.0, "z": 0.0},
                  {"x": 10.0, "y": 0.0, "z": 10.0},
                  {"x": 0.0, "y": 0.0, "z": 10.0},
                  {"x": 0.0, "y": 0.0, "z": 0.0}
                ],
                "holes": [
                  [[1,0,1],[3,0,1],[3,0,3],[1,0,3]]
                ]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Crossing_Ap",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[5,0,2],[12,0,2],[12,0,8],[5,0,8]]
                  }
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "NonCoplanarHost",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [1, 0, 0], "o": [10, 0, 0], "x": [0, 1, 0]},
                "boundary": [[10,0,0],[10,10,0],[10,10,10],[10,0,10]]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Floating_Ap",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[10.5,2,2],[10.5,8,2],[10.5,8,8],[10.5,2,8]]
                  }
                }
              ]
            }
          ]
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    // 10 ft = 3.048 m; wall = 10x10 - 2x2 hole = 96 ft2 = 8.91869184 m2
    let wall = scene
        .objects
        .iter()
        .find(|o| o.identifier == "CrossingWall")
        .unwrap();
    let expected_m2 = 96.0 * 0.3048 * 0.3048;
    assert!((wall.area.unwrap() - expected_m2).abs() < 1e-4);
    assert!((mesh_area_for_object(&scene, wall.object_id) - expected_m2).abs() < 1e-4);

    // Crossing aperture triggers fallback -> offset along [0, -1, 0] by 0.003m
    let crossing_ap = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Crossing_Ap")
        .unwrap();
    for v in scene
        .vertices
        .iter()
        .filter(|v| v.object_id == crossing_ap.object_id)
    {
        assert!((v.position[1] - (-0.003)).abs() < 1e-5);
    }

    // Non-coplanar aperture triggers fallback -> offset along +X by 0.003m from 10*0.3048 + 0.5*0.3048
    let floating_ap = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Floating_Ap")
        .unwrap();
    let expected_x = 10.5 * 0.3048 + 0.003;
    for v in scene
        .vertices
        .iter()
        .filter(|v| v.object_id == floating_ap.object_id)
    {
        assert!((f64::from(v.position[0]) - expected_x).abs() < 1e-4);
    }
}

#[test]
fn all_color_by_modes_and_orientation_labels_are_consistent() {
    let json = r#"{
      "type": "Model",
      "identifier": "ColorModel",
      "rooms": [
        {
          "type": "Room",
          "identifier": "R1",
          "story": "Level 1",
          "zone": "Perimeter_S",
          "properties": {"energy": {"program_type": "Office", "construction_set": "ASHRAE_CS", "hvac": "VAV_1"}},
          "faces": [
            {
              "type": "Face",
              "identifier": "ExtWall_ZeroWwr",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,0],[4,0,0],[4,0,3],[0,0,3]]}
            },
            {
              "type": "Face",
              "identifier": "ExtWall_HalfWwr",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[4,0,0],[4,4,0],[4,4,3],[4,0,3]]},
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "HalfWin",
                  "geometry": {"type": "Face3D", "boundary": [[4,0.5,0.5],[4,3.5,0.5],[4,3.5,2.5],[4,0.5,2.5]]}
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "IntWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Surface"},
              "geometry": {"type": "Face3D", "boundary": [[0,4,0],[4,4,0],[4,4,3],[0,4,3]]}
            },
            {
              "type": "Face",
              "identifier": "Roof",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,3],[4,0,3],[4,4,3],[0,4,3]]}
            },
            {
              "type": "Face",
              "identifier": "Floor",
              "face_type": "Floor",
              "boundary_condition": {"type": "Ground"},
              "geometry": {"type": "Face3D", "boundary": [[0,4,0],[4,4,0],[4,0,0],[0,0,0]]}
            },
            {
              "type": "Face",
              "identifier": "AirWall",
              "face_type": "AirBoundary",
              "boundary_condition": {"type": "Surface"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,0],[0,4,0],[0,4,3],[0,0,3]]}
            }
          ]
        },
        {
          "type": "Room",
          "identifier": "R2",
          "story": "Level 2",
          "zone": "Core",
          "properties": {"energy": {"program_type": "Corridor", "construction_set": "Interior_CS", "hvac": "DOAS_2"}},
          "faces": [
            {
              "type": "Face",
              "identifier": "R2_Wall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,3],[4,0,3],[4,0,6],[0,0,6]]},
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "FullishWin",
                  "geometry": {"type": "Face3D", "boundary": [[0.1,0,3.1],[3.9,0,3.1],[3.9,0,5.9],[0.1,0,5.9]]}
                }
              ]
            }
          ]
        }
      ],
      "orphaned_shades": [
        {
          "type": "Shade",
          "identifier": "TreeShade",
          "geometry": {"type": "Face3D", "boundary": [[-2,0,0],[-1,0,0],[-1,1,0],[-2,1,0]]}
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    let max_id = scene.objects.iter().map(|o| o.object_id).max().unwrap() as usize;

    for mode in ColorBy::ALL {
        let table = resolve_scene_colors(&scene, mode);
        assert_eq!(table.len(), max_id + 1);
        assert_eq!(table[0], [0.0, 0.0, 0.0, 0.0]);
        for rec in &scene.objects {
            assert_eq!(table[rec.object_id as usize], color_for_object(rec, mode));
        }
    }

    let ap = scene.objects.iter().find(|o| o.identifier == "HalfWin").unwrap();
    let wall = scene.objects.iter().find(|o| o.identifier == "ExtWall_ZeroWwr").unwrap();
    let int_wall = scene.objects.iter().find(|o| o.identifier == "IntWall").unwrap();
    let roof = scene.objects.iter().find(|o| o.identifier == "Roof").unwrap();
    let floor = scene.objects.iter().find(|o| o.identifier == "Floor").unwrap();
    let air = scene.objects.iter().find(|o| o.identifier == "AirWall").unwrap();
    let shade = scene.objects.iter().find(|o| o.identifier == "TreeShade").unwrap();
    let r2_wall = scene.objects.iter().find(|o| o.identifier == "R2_Wall").unwrap();
    let half_wall = scene.objects.iter().find(|o| o.identifier == "ExtWall_HalfWwr").unwrap();

    // Type palette sanity
    assert!((color_for_object(ap, ColorBy::Type)[3] - 0.42).abs() < 1e-6);
    assert!(color_for_object(wall, ColorBy::Type)[0] > color_for_object(wall, ColorBy::Type)[2]); // warm ochre
    assert!(color_for_object(roof, ColorBy::Type)[0] > color_for_object(roof, ColorBy::Type)[1]); // terracotta
    assert!(color_for_object(air, ColorBy::Type)[2] > color_for_object(air, ColorBy::Type)[0]); // cyan
    assert!(color_for_object(shade, ColorBy::Type)[1] > color_for_object(shade, ColorBy::Type)[0]); // teal/sage
    assert_ne!(color_for_object(wall, ColorBy::Type), color_for_object(int_wall, ColorBy::Type));
    assert_ne!(color_for_object(floor, ColorBy::Type), color_for_object(roof, ColorBy::Type));

    // BoundaryCondition distinct colors
    assert_ne!(
        color_for_object(wall, ColorBy::BoundaryCondition),
        color_for_object(int_wall, ColorBy::BoundaryCondition)
    );
    assert_ne!(
        color_for_object(wall, ColorBy::BoundaryCondition),
        color_for_object(floor, ColorBy::BoundaryCondition)
    );

    // Categorical distinctness between R1 and R2 attributes
    for mode in [
        ColorBy::Story,
        ColorBy::Zone,
        ColorBy::ProgramType,
        ColorBy::ConstructionSet,
        ColorBy::Hvac,
    ] {
        assert_ne!(color_for_object(wall, mode), color_for_object(r2_wall, mode));
        // Unassigned shade gets neutral gray while keeping alpha=1
        assert_eq!(color_for_object(shade, mode)[3], 1.0);
        // Aperture keeps translucency across all categorical modes
        assert!((color_for_object(ap, mode)[3] - 0.42).abs() < 1e-6);
    }

    // WWR blue -> yellow -> red ramp
    let c_zero = color_for_object(wall, ColorBy::Wwr);
    let c_half = color_for_object(half_wall, ColorBy::Wwr);
    let c_high = color_for_object(r2_wall, ColorBy::Wwr);
    assert!(c_zero[2] > c_zero[0], "0% WWR should be blue-dominant: {c_zero:?}");
    assert!(c_half[0] > 0.8 && c_half[1] > 0.7 && c_half[2] < 0.3, "50% WWR should be yellow: {c_half:?}");
    assert!(c_high[0] > c_high[2] && c_high[0] > c_high[1], "~89% WWR should be red-dominant: {c_high:?}");

    // Orientation labels
    assert_eq!(orientation_label([0.0, 1.0, 0.0]), "N");
    assert_eq!(orientation_label([1.0, 1.0, 0.0]), "NE");
    assert_eq!(orientation_label([1.0, 0.0, 0.0]), "E");
    assert_eq!(orientation_label([1.0, -1.0, 0.0]), "SE");
    assert_eq!(orientation_label([0.0, -1.0, 0.0]), "S");
    assert_eq!(orientation_label([-1.0, -1.0, 0.0]), "SW");
    assert_eq!(orientation_label([-1.0, 0.0, 0.0]), "W");
    assert_eq!(orientation_label([-1.0, 1.0, 0.0]), "NW");
    assert_eq!(orientation_label([0.0, 0.0, 1.0]), "horizontal_up");
    assert_eq!(orientation_label([0.0, 0.0, -1.0]), "horizontal_down");
    assert_eq!(orientation_label([0.0, 0.0, 0.0]), "horizontal_up");
}

#[test]
fn invalid_model_returns_scene_error() {
    let err = load_hbjson_str("{not valid json", None, None).unwrap_err();
    assert!(matches!(err, SceneError::Json(_)));

    let wrong_type = load_hbjson_str(r#"{"type":"Room","identifier":"R"}"#, None, None).unwrap_err();
    assert!(matches!(wrong_type, SceneError::InvalidModel(_)));

    let missing_file = load_hbjson_file(Path::new("definitely_does_not_exist_12345.hbjson"), None).unwrap_err();
    assert!(matches!(missing_file, SceneError::Io(_)));
}

#[test]
fn loads_real_repository_hbjson_samples_cleanly() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let repo_root = manifest_dir
        .ancestors()
        .nth(3)
        .expect("expected repo root 3 levels above lbt-scene");

    let sample_paths = [
        "resources/honeybee-schema/samples/model/model_complete_holes.hbjson",
        "resources/honeybee-schema/samples/model/model_5vertex_sub_faces.hbjson",
        "resources/honeybee-schema/samples/model/model_complete_multi_zone_office.hbjson",
        "resources/honeybee-schema/samples/model/model_with_shade_mesh.hbjson",
        "resources/honeybee-core/tests/json/bad_geometry_model.hbjson",
        "resources/honeybee-openstudio/tests/assets/single_family_with_zones.hbjson",
        "resources/dragonfly-display/tests/json/openings.hbjson",
    ];

    for rel in sample_paths {
        let full_path = repo_root.join(rel);
        if !full_path.exists() {
            continue;
        }
        let scene = load_hbjson_file(&full_path, Some("sample_garden"))
            .unwrap_or_else(|e| panic!("failed to parse {rel}: {e}"));
        assert_scene_invariants(&scene);
        assert!(!scene.objects.is_empty(), "empty objects for {rel}");
        assert!(!scene.vertices.is_empty(), "empty vertices for {rel}");
        assert!(!scene.indices.is_empty(), "empty indices for {rel}");
    }
}
