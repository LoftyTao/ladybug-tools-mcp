use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};

use lbt_scene::{
    build_legend, color_for_object, color_for_object_in_scene, load_hbjson_file, load_hbjson_str,
    orientation_label, resolve_scene_colors, ColorBy, ObjectKind, SceneData, SceneError,
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
fn touching_doors_and_adjacent_windows_punch_cleanly_without_overlap() {
    let json = r#"{
      "type": "Model",
      "identifier": "TouchingPunchTest",
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
            },
            {
              "type": "Face",
              "identifier": "Wall_SplitByFullHeightGlass",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [1,0,0], "o": [8,0,0], "x": [0,1,0]},
                "boundary": [[8,0,0],[8,5,0],[8,5,3],[8,0,3]]
              },
              "doors": [
                {
                  "type": "Door",
                  "identifier": "FullHeight_GlassDoor",
                  "is_glass": true,
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[8,2,0],[8,3.5,0],[8,3.5,3],[8,2,3]]
                  }
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "Wall_FullCurtain",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [-1,0,0], "o": [0,0,0], "x": [0,-1,0]},
                "boundary": [[0,5,0],[0,0,0],[0,0,3],[0,5,3]]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Full_Curtain_Glazing",
                  "geometry": {
                    "type": "Face3D",
                    "boundary": [[0,5,0],[0,0,0],[0,0,3],[0,5,3]]
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

    // Wall_TouchingDoor: 8*3 = 24.0 gross, minus door (1.5*2.1 = 3.15) minus window (2*1.5 = 3.0) = 17.85 m2!
    let wall1 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_TouchingDoor")
        .unwrap();
    let wall1_area = mesh_area_for_object(&scene, wall1.object_id);
    assert!(
        (wall1_area - 17.85).abs() < 1e-3,
        "expected cleanly punched wall area 17.85, got {wall1_area}"
    );
    // Door and window sit flush at y = 0.0 (no fallback offset needed!)
    let door = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Bottom_Touching_Door")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == door.object_id) {
        assert!(v.position[1].abs() < 1e-5, "expected flush y=0.0, got y={}", v.position[1]);
    }
    let win = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Neighbor_Win")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == win.object_id) {
        assert!(v.position[1].abs() < 1e-5, "expected flush y=0.0, got y={}", v.position[1]);
    }

    // Wall_TouchingWindows: 8*3 = 24.0 gross minus merged 6*1 = 6.0 window hole = 18.0 m2!
    let wall2 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_TouchingWindows")
        .unwrap();
    let wall2_area = mesh_area_for_object(&scene, wall2.object_id);
    assert!(
        (wall2_area - 18.0).abs() < 1e-3,
        "expected merged-hole punched wall area 18.0, got {wall2_area}"
    );
    let win_l = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Win_Left")
        .unwrap();
    for v in scene.vertices.iter().filter(|v| v.object_id == win_l.object_id) {
        assert!((v.position[1] - 5.0).abs() < 1e-5, "expected flush y=5.0, got y={}", v.position[1]);
    }

    // Wall_SplitByFullHeightGlass: 5*3 = 15.0 gross minus 1.5*3 = 4.5 door = 10.5 m2 (two solid strips)!
    let wall3 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_SplitByFullHeightGlass")
        .unwrap();
    let wall3_area = mesh_area_for_object(&scene, wall3.object_id);
    assert!(
        (wall3_area - 10.5).abs() < 1e-3,
        "expected split wall area 10.5, got {wall3_area}"
    );

    // Wall_FullCurtain: 100% glazed -> zero host wall triangles behind glass!
    let wall4 = scene
        .objects
        .iter()
        .find(|o| o.identifier == "Wall_FullCurtain")
        .unwrap();
    assert_eq!(mesh_area_for_object(&scene, wall4.object_id), 0.0);
    assert!((wall4.area.unwrap() - 15.0).abs() < 1e-4);
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
            assert_eq!(
                table[rec.object_id as usize],
                color_for_object_in_scene(&scene, rec, mode)
            );
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

    let assert_rgba = |actual: [f32; 4], expected_u8: [u8; 4], label: &str| {
        for i in 0..4 {
            let exp = expected_u8[i] as f32 / 255.0;
            assert!(
                (actual[i] - exp).abs() < 1e-5,
                "{label} channel {i}: expected {exp} ({}), got {}",
                expected_u8[i],
                actual[i]
            );
        }
    };

    // Official honeybee-display TYPE_COLORS verification
    assert_rgba(color_for_object(wall, ColorBy::Type), [230, 180, 60, 255], "Wall");
    assert_rgba(color_for_object(int_wall, ColorBy::Type), [230, 215, 150, 255], "Interior Wall");
    assert_rgba(color_for_object(roof, ColorBy::Type), [128, 20, 20, 255], "Roof");
    assert_rgba(color_for_object(floor, ColorBy::Type), [128, 128, 128, 255], "Floor");
    assert_rgba(color_for_object(air, ColorBy::Type), [255, 255, 200, 100], "Air Boundary");
    assert_rgba(color_for_object(ap, ColorBy::Type), [64, 180, 255, 100], "Aperture");
    assert_rgba(color_for_object(shade, ColorBy::Type), [120, 75, 190, 255], "Outdoor Shade");

    // Official honeybee-display BC_COLORS verification
    assert_rgba(color_for_object(wall, ColorBy::BoundaryCondition), [64, 180, 255, 255], "BC Outdoors");
    assert_rgba(color_for_object(int_wall, ColorBy::BoundaryCondition), [0, 128, 0, 255], "BC Surface");
    assert_rgba(color_for_object(floor, ColorBy::BoundaryCondition), [165, 82, 0, 255], "BC Ground");
    assert_rgba(color_for_object(shade, ColorBy::BoundaryCondition), [255, 255, 200, 255], "BC Other (Shade)");
    assert_rgba(color_for_object(ap, ColorBy::BoundaryCondition), [64, 180, 255, 100], "BC Outdoors Aperture");

    // Categorical distinctness between R1 and R2 attributes using official Ladybug Colorset.original()
    assert_eq!(ColorBy::ALL.len(), 7);
    for mode in [
        ColorBy::Story,
        ColorBy::Zone,
        ColorBy::ProgramType,
        ColorBy::ConstructionSet,
        ColorBy::Hvac,
    ] {
        let c1 = color_for_object_in_scene(&scene, wall, mode);
        let c2 = color_for_object_in_scene(&scene, r2_wall, mode);
        assert_ne!(c1, c2);
        // 2-category modes span Ladybug Colorset.original() endpoints: blue (75,107,169) -> red (234,38,0)
        if mode == ColorBy::Story {
            assert_rgba(c1, [75, 107, 169, 255], "Story 1 Colorset.original[0]");
            assert_rgba(c2, [234, 38, 0, 255], "Story 2 Colorset.original[9]");
        }
        // Unassigned shade gets neutral gray while keeping alpha=1
        assert_eq!(color_for_object_in_scene(&scene, shade, mode)[3], 1.0);
        // Aperture keeps official honeybee-display translucency (100/255) across all categorical modes
        assert!((color_for_object_in_scene(&scene, ap, mode)[3] - 100.0 / 255.0).abs() < 1e-6);
    }

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
        "resources/honeybee-display/tests/json/single_family_home.hbjson",
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

        if rel.ends_with("single_family_home.hbjson") {
            // All 12 adjacent interior Room Surface pairs must be cleanly separated by ~4mm (no z-fighting).
            let surface_faces: Vec<_> = scene
                .objects
                .iter()
                .filter(|o| {
                    o.kind == ObjectKind::Face
                        && o.owner_room_id.is_some()
                        && o.boundary_condition.as_deref() == Some("Surface")
                })
                .collect();
            assert_eq!(surface_faces.len(), 24);
            for i in 0..surface_faces.len() {
                for j in (i + 1)..surface_faces.len() {
                    let a = surface_faces[i].centroid;
                    let b = surface_faces[j].centroid;
                    let dist = ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt();
                    assert!(
                        dist > 0.003,
                        "adjacent Surface faces {} and {} remain coincident (dist={dist})",
                        surface_faces[i].identifier,
                        surface_faces[j].identifier
                    );
                }
            }
        }

        if rel.ends_with("bad_geometry_model.hbjson") {
            // Raw JSON has 40 faces including 3 coincident same-type same-normal duplicates -> 37 kept.
            let face_count = scene
                .objects
                .iter()
                .filter(|o| o.kind == ObjectKind::Face)
                .count();
            assert_eq!(face_count, 37);
        }
    }
}

#[test]
fn schema_tree_ownership_and_flags_cover_all_honeybee_types() {
    let json = r#"{
      "type": "Model",
      "identifier": "SchemaTreeModel",
      "rooms": [
        {
          "type": "Room",
          "identifier": "RoomA",
          "story": "L1",
          "indoor_shades": [
            {
              "type": "Shade",
              "identifier": "RoomA_InShd",
              "is_detached": true,
              "geometry": {"type": "Face3D", "boundary": [[1,1,2.2],[2,1,2.2],[2,2,2.2],[1,2,2.2]]}
            }
          ],
          "outdoor_shades": [
            {
              "type": "Shade",
              "identifier": "RoomA_OutShd",
              "geometry": {"type": "Face3D", "boundary": [[0,-1,3],[4,-1,3],[4,-2,3],[0,-2,3]]}
            }
          ],
          "faces": [
            {
              "type": "Face",
              "identifier": "RoomA_SouthWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [0,0,0], "x": [1,0,0]},
                "boundary": [[0,0,0],[6,0,0],[6,0,3],[0,0,3]]
              },
              "indoor_shades": [
                {
                  "type": "Shade",
                  "identifier": "Wall_InShd",
                  "geometry": {"type": "Face3D", "boundary": [[0.2,0.1,2.6],[1.2,0.1,2.6],[1.2,0.4,2.6],[0.2,0.4,2.6]]}
                }
              ],
              "outdoor_shades": [
                {
                  "type": "Shade",
                  "identifier": "Wall_OutShd",
                  "geometry": {"type": "Face3D", "boundary": [[0,0,2.9],[6,0,2.9],[6,-0.5,2.9],[0,-0.5,2.9]]}
                }
              ],
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "RoomA_Win",
                  "geometry": {"type": "Face3D", "boundary": [[0.5,0,1],[2.5,0,1],[2.5,0,2.2],[0.5,0,2.2]]},
                  "indoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Win_InBlind",
                      "geometry": {"type": "Face3D", "boundary": [[0.5,0.05,2.1],[2.5,0.05,2.1],[2.5,0.2,2.1],[0.5,0.2,2.1]]}
                    }
                  ],
                  "outdoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Win_OutFin",
                      "geometry": {"type": "Face3D", "boundary": [[0.5,0,1],[0.5,-0.3,1],[0.5,-0.3,2.2],[0.5,0,2.2]]}
                    }
                  ]
                }
              ],
              "doors": [
                {
                  "type": "Door",
                  "identifier": "RoomA_GlassDoor",
                  "is_glass": true,
                  "geometry": {"type": "Face3D", "boundary": [[3.5,0,0],[5.0,0,0],[5.0,0,2.2],[3.5,0,2.2]]},
                  "indoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Door_InShd",
                      "geometry": {"type": "Face3D", "boundary": [[3.5,0.1,2.2],[5.0,0.1,2.2],[5.0,0.3,2.2],[3.5,0.3,2.2]]}
                    }
                  ],
                  "outdoor_shades": [
                    {
                      "type": "Shade",
                      "identifier": "Door_Awning",
                      "geometry": {"type": "Face3D", "boundary": [[3.5,0,2.2],[5.0,0,2.2],[5.0,-0.8,2.2],[3.5,-0.8,2.2]]}
                    }
                  ]
                }
              ]
            }
          ]
        }
      ],
      "orphaned_faces": [
        {
          "type": "Face",
          "identifier": "Orph_Face",
          "face_type": "Wall",
          "boundary_condition": {"type": "Outdoors"},
          "geometry": {"type": "Face3D", "boundary": [[10,0,0],[14,0,0],[14,0,3],[10,0,3]]},
          "apertures": [
            {
              "type": "Aperture",
              "identifier": "Orph_Face_Ap",
              "geometry": {"type": "Face3D", "boundary": [[11,0,1],[13,0,1],[13,0,2],[11,0,2]]}
            }
          ],
          "outdoor_shades": [
            {
              "type": "Shade",
              "identifier": "Orph_Face_Shd",
              "geometry": {"type": "Face3D", "boundary": [[10,0,2.8],[14,0,2.8],[14,-0.5,2.8],[10,-0.5,2.8]]}
            }
          ]
        }
      ],
      "orphaned_apertures": [
        {
          "type": "Aperture",
          "identifier": "Orph_Ap",
          "geometry": {"type": "Face3D", "boundary": [[16,0,1],[17,0,1],[17,0,2],[16,0,2]]}
        }
      ],
      "orphaned_doors": [
        {
          "type": "Door",
          "identifier": "Orph_Door_Opaque",
          "is_glass": false,
          "geometry": {"type": "Face3D", "boundary": [[18,0,0],[19,0,0],[19,0,2],[18,0,2]]}
        }
      ],
      "orphaned_shades": [
        {
          "type": "Shade",
          "identifier": "Orph_OutdoorShd",
          "is_detached": false,
          "geometry": {"type": "Face3D", "boundary": [[20,0,0],[22,0,0],[22,2,0],[20,2,0]]}
        },
        {
          "type": "Shade",
          "identifier": "Orph_ContextShd",
          "is_detached": true,
          "geometry": {"type": "Face3D", "boundary": [[25,0,0],[28,0,0],[28,0,5],[25,0,5]]}
        }
      ],
      "shade_meshes": [
        {
          "type": "ShadeMesh",
          "identifier": "DefaultDetachedMesh",
          "geometry": {
            "type": "Mesh3D",
            "vertices": [[30,0,0],[32,0,0],[32,2,0],[30,2,0]],
            "faces": [[0,1,2,3]]
          }
        },
        {
          "type": "ShadeMesh",
          "identifier": "AttachedStyleMesh",
          "is_detached": false,
          "geometry": {
            "type": "Mesh3D",
            "vertices": [[34,0,0],[36,0,0],[36,2,0],[34,2,0]],
            "faces": [[0,1,2,3]]
          }
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    let find = |id: &str| {
        scene
            .objects
            .iter()
            .find(|o| o.identifier == id)
            .unwrap_or_else(|| panic!("missing {id}"))
    };

    let room = find("RoomA");
    assert_eq!(room.parent_object_id, None);
    assert_eq!(room.owner_room_id, Some(room.object_id));
    assert!(!room.is_orphaned);

    // Room shades: parented to Room, owned by Room, never detached even if JSON had is_detached=true
    let rm_in = find("RoomA_InShd");
    assert_eq!(rm_in.parent_object_id, Some(room.object_id));
    assert_eq!(rm_in.owner_room_id, Some(room.object_id));
    assert!(!rm_in.is_orphaned);
    assert!(rm_in.is_indoor_shade);
    assert!(!rm_in.is_detached_shade);
    assert_eq!(color_for_object(rm_in, ColorBy::Type), [159.0 / 255.0, 99.0 / 255.0, 1.0, 1.0]);

    let rm_out = find("RoomA_OutShd");
    assert_eq!(rm_out.parent_object_id, Some(room.object_id));
    assert_eq!(rm_out.owner_room_id, Some(room.object_id));
    assert!(!rm_out.is_indoor_shade);
    assert!(!rm_out.is_detached_shade);

    // Face -> Subfaces -> Subface Shades chain
    let wall = find("RoomA_SouthWall");
    assert_eq!(wall.parent_object_id, Some(room.object_id));
    assert_eq!(wall.owner_room_id, Some(room.object_id));
    assert!(!wall.is_orphaned);

    let wall_in = find("Wall_InShd");
    assert_eq!(wall_in.parent_object_id, Some(wall.object_id));
    assert_eq!(wall_in.owner_room_id, Some(room.object_id));
    assert!(wall_in.is_indoor_shade);

    let wall_out = find("Wall_OutShd");
    assert_eq!(wall_out.parent_object_id, Some(wall.object_id));
    assert_eq!(wall_out.owner_room_id, Some(room.object_id));
    assert!(!wall_out.is_indoor_shade);

    let win = find("RoomA_Win");
    assert_eq!(win.parent_object_id, Some(wall.object_id));
    assert_eq!(win.owner_room_id, Some(room.object_id));
    assert_eq!(scene.owner_room(win.object_id).map(|r| r.object_id), Some(room.object_id));

    let win_in = find("Win_InBlind");
    assert_eq!(win_in.parent_object_id, Some(win.object_id));
    assert_eq!(win_in.owner_room_id, Some(room.object_id));
    assert!(win_in.is_indoor_shade);

    let win_out = find("Win_OutFin");
    assert_eq!(win_out.parent_object_id, Some(win.object_id));
    assert_eq!(win_out.owner_room_id, Some(room.object_id));
    assert!(!win_out.is_indoor_shade);

    let gdoor = find("RoomA_GlassDoor");
    assert_eq!(gdoor.parent_object_id, Some(wall.object_id));
    assert_eq!(gdoor.owner_room_id, Some(room.object_id));
    assert!(gdoor.is_glass);
    assert_eq!(
        color_for_object(gdoor, ColorBy::Type),
        [128.0 / 255.0, 204.0 / 255.0, 1.0, 100.0 / 255.0]
    );

    let door_in = find("Door_InShd");
    assert_eq!(door_in.parent_object_id, Some(gdoor.object_id));
    assert_eq!(door_in.owner_room_id, Some(room.object_id));
    assert!(door_in.is_indoor_shade);

    let door_out = find("Door_Awning");
    assert_eq!(door_out.parent_object_id, Some(gdoor.object_id));
    assert_eq!(door_out.owner_room_id, Some(room.object_id));
    assert!(!door_out.is_indoor_shade);

    // Orphaned geometry and its descendants
    let oface = find("Orph_Face");
    assert_eq!(oface.parent_object_id, None);
    assert_eq!(oface.owner_room_id, None);
    assert!(oface.is_orphaned);

    let oface_ap = find("Orph_Face_Ap");
    assert_eq!(oface_ap.parent_object_id, Some(oface.object_id));
    assert_eq!(oface_ap.owner_room_id, None);
    assert!(oface_ap.is_orphaned);

    let oface_shd = find("Orph_Face_Shd");
    assert_eq!(oface_shd.parent_object_id, Some(oface.object_id));
    assert_eq!(oface_shd.owner_room_id, None);
    assert!(oface_shd.is_orphaned);

    let oap = find("Orph_Ap");
    assert_eq!(oap.parent_object_id, None);
    assert_eq!(oap.owner_room_id, None);
    assert!(oap.is_orphaned);

    let odoor = find("Orph_Door_Opaque");
    assert_eq!(odoor.parent_object_id, None);
    assert_eq!(odoor.owner_room_id, None);
    assert!(odoor.is_orphaned);
    assert!(!odoor.is_glass);
    assert_eq!(
        color_for_object(odoor, ColorBy::Type),
        [160.0 / 255.0, 150.0 / 255.0, 100.0 / 255.0, 1.0]
    );

    let oshd_out = find("Orph_OutdoorShd");
    assert_eq!(oshd_out.parent_object_id, None);
    assert_eq!(oshd_out.owner_room_id, None);
    assert!(oshd_out.is_orphaned);
    assert!(!oshd_out.is_detached_shade);
    assert!(!oshd_out.is_shade_mesh);
    assert_eq!(
        color_for_object(oshd_out, ColorBy::Type),
        [120.0 / 255.0, 75.0 / 255.0, 190.0 / 255.0, 1.0]
    );

    let oshd_ctx = find("Orph_ContextShd");
    assert!(oshd_ctx.is_orphaned);
    assert!(oshd_ctx.is_detached_shade);
    assert_eq!(
        color_for_object(oshd_ctx, ColorBy::Type),
        [80.0 / 255.0, 50.0 / 255.0, 128.0 / 255.0, 1.0]
    );

    // ShadeMesh defaults to is_detached = true per honeybee-schema
    let sm_default = find("DefaultDetachedMesh");
    assert_eq!(sm_default.parent_object_id, None);
    assert_eq!(sm_default.owner_room_id, None);
    assert!(sm_default.is_orphaned);
    assert!(sm_default.is_detached_shade);
    assert!(sm_default.is_shade_mesh);
    assert_eq!(
        color_for_object(sm_default, ColorBy::Type),
        [80.0 / 255.0, 50.0 / 255.0, 128.0 / 255.0, 1.0]
    );

    let sm_attached = find("AttachedStyleMesh");
    assert!(sm_attached.is_orphaned);
    assert!(!sm_attached.is_detached_shade);
    assert!(sm_attached.is_shade_mesh);
    assert_eq!(
        color_for_object(sm_attached, ColorBy::Type),
        [120.0 / 255.0, 75.0 / 255.0, 190.0 / 255.0, 1.0]
    );
}

#[test]
fn build_legend_returns_authentic_ladybug_legends_for_all_modes() {
    let json = r#"{
      "type": "Model",
      "identifier": "LegendModel",
      "rooms": [
        {
          "type": "Room",
          "identifier": "R1",
          "story": "Ground",
          "zone": "Zone_A",
          "properties": {"energy": {"program_type": "Office", "construction_set": "CS_A", "hvac": "VAV"}},
          "faces": [
            {
              "type": "Face",
              "identifier": "W1",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,0],[4,0,0],[4,0,3],[0,0,3]]},
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "A1",
                  "geometry": {"type": "Face3D", "boundary": [[1,0,1],[3,0,1],[3,0,2.5],[1,0,2.5]]}
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "Ceil1",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Adiabatic"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,3],[4,0,3],[4,4,3],[0,4,3]]}
            },
            {
              "type": "Face",
              "identifier": "Flr1",
              "face_type": "Floor",
              "boundary_condition": {"type": "Ground"},
              "geometry": {"type": "Face3D", "boundary": [[0,4,0],[4,4,0],[4,0,0],[0,0,0]]}
            }
          ]
        },
        {
          "type": "Room",
          "identifier": "R2",
          "story": "Upper",
          "faces": [
            {
              "type": "Face",
              "identifier": "Roof2",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {"type": "Face3D", "boundary": [[0,0,6],[4,0,6],[4,4,6],[0,4,6]]}
            },
            {
              "type": "Face",
              "identifier": "IntFlr2",
              "face_type": "Floor",
              "boundary_condition": {"type": "Surface"},
              "geometry": {"type": "Face3D", "boundary": [[0,4,3],[4,4,3],[4,0,3],[0,0,3]]}
            }
          ]
        }
      ],
      "orphaned_shades": [
        {
          "type": "Shade",
          "identifier": "Ctx1",
          "is_detached": true,
          "geometry": {"type": "Face3D", "boundary": [[-5,0,0],[-3,0,0],[-3,0,4],[-5,0,4]]}
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();

    // 1. Type legend: exact honeybee-display keys, labels, colors, counts & canonical order
    let leg_type = build_legend(&scene, ColorBy::Type);
    assert_eq!(leg_type.key, "type");
    assert!(!leg_type.is_continuous);
    assert_eq!(leg_type.min_val, None);
    let keys: Vec<&str> = leg_type.entries.iter().map(|e| e.key.as_str()).collect();
    assert_eq!(
        keys,
        vec!["wall", "roof", "floor", "ceiling", "interior_floor", "aperture", "context_shade"]
    );
    let ceil_entry = leg_type.entries.iter().find(|e| e.key == "ceiling").unwrap();
    assert_eq!(ceil_entry.label, "Ceiling");
    assert_eq!(ceil_entry.color_srgb, [1.0, 128.0 / 255.0, 128.0 / 255.0, 1.0]);
    assert_eq!(ceil_entry.count, 1);

    // 2. BoundaryCondition legend
    let leg_bc = build_legend(&scene, ColorBy::BoundaryCondition);
    assert_eq!(leg_bc.key, "boundary_condition");
    assert!(!leg_bc.is_continuous);
    let bc_keys: Vec<&str> = leg_bc.entries.iter().map(|e| e.key.as_str()).collect();
    assert_eq!(bc_keys, vec!["outdoors", "surface", "ground", "adiabatic", "other"]);
    assert_eq!(leg_bc.entries.iter().find(|e| e.key == "outdoors").unwrap().count, 3); // W1, A1, Roof2
    assert_eq!(leg_bc.entries.iter().find(|e| e.key == "other").unwrap().count, 1); // Ctx1

    // 3. Story legend: preserves elevation order & uses Ladybug Colorset.original() matching resolve_scene_colors 100%
    let leg_story = build_legend(&scene, ColorBy::Story);
    assert_eq!(leg_story.key, "story");
    assert!(!leg_story.is_continuous);
    let story_labels: Vec<&str> = leg_story.entries.iter().map(|e| e.label.as_str()).collect();
    assert_eq!(story_labels, vec!["Ground", "Upper"]);
    let story_table = resolve_scene_colors(&scene, ColorBy::Story);
    let r1 = scene.objects.iter().find(|o| o.identifier == "R1").unwrap();
    let r2 = scene.objects.iter().find(|o| o.identifier == "R2").unwrap();
    assert_eq!(leg_story.entries[0].color_srgb, story_table[r1.object_id as usize]);
    assert_eq!(leg_story.entries[1].color_srgb, story_table[r2.object_id as usize]);
    assert_eq!(leg_story.entries[0].color_srgb, [75.0 / 255.0, 107.0 / 255.0, 169.0 / 255.0, 1.0]);
    assert_eq!(leg_story.entries[1].color_srgb, [234.0 / 255.0, 38.0 / 255.0, 0.0, 1.0]);

    // 4. ProgramType legend formats unassigned rooms as label "None" (key "unassigned")
    let leg_prog = build_legend(&scene, ColorBy::ProgramType);
    assert_eq!(leg_prog.entries.len(), 2);
    assert_eq!(leg_prog.entries[0].key, "Office");
    assert_eq!(leg_prog.entries[0].count, 1);
    assert_eq!(leg_prog.entries[1].key, "unassigned");
    assert_eq!(leg_prog.entries[1].label, "None");
    assert_eq!(leg_prog.entries[1].count, 1);

    // 5. Verify Zone, ConstructionSet, Hvac legends all use non-continuous categorical entries
    for mode in [ColorBy::Zone, ColorBy::ConstructionSet, ColorBy::Hvac] {
        let leg = build_legend(&scene, mode);
        assert_eq!(leg.key, mode.as_str());
        assert!(!leg.is_continuous);
        assert_eq!(leg.entries.len(), 2);
        assert_eq!(leg.entries[1].key, "unassigned");
        assert_eq!(leg.entries[1].label, "None");
    }
}

#[test]
fn adjacent_room_surface_faces_inset_inward_with_coplanar_subfaces() {
    let json = r#"{
      "type": "Model",
      "identifier": "AdjacentRoomsInset",
      "rooms": [
        {
          "type": "Room",
          "identifier": "RoomLeft",
          "faces": [
            {
              "type": "Face",
              "identifier": "Left_ExtWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [-1,0,0], "o": [0,0,0], "x": [0,-1,0]},
                "boundary": [[0,4,0],[0,0,0],[0,0,3],[0,4,3]]
              }
            },
            {
              "type": "Face",
              "identifier": "Left_SharedWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["Right_SharedWall", "RoomRight"]},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [1,0,0], "o": [5,0,0], "x": [0,1,0]},
                "boundary": [[5,0,0],[5,4,0],[5,4,3],[5,0,3]]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Left_IntWin",
                  "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["Right_IntWin", "Right_SharedWall", "RoomRight"]},
                  "geometry": {
                    "type": "Face3D",
                    "plane": {"n": [1,0,0], "o": [5,1,1], "x": [0,1,0]},
                    "boundary": [[5,1,1],[5,3,1],[5,3,2.2],[5,1,2.2]]
                  }
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "Left_Ceiling",
              "face_type": "RoofCeiling",
              "boundary_condition": {"type": "Surface"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,0,1], "o": [0,0,3], "x": [1,0,0]},
                "boundary": [[0,0,3],[5,0,3],[5,4,3],[0,4,3]]
              }
            }
          ]
        },
        {
          "type": "Room",
          "identifier": "RoomRight",
          "faces": [
            {
              "type": "Face",
              "identifier": "Right_SharedWall",
              "face_type": "Wall",
              "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["Left_SharedWall", "RoomLeft"]},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [-1,0,0], "o": [5,4,0], "x": [0,-1,0]},
                "boundary": [[5,4,0],[5,0,0],[5,0,3],[5,4,3]]
              },
              "apertures": [
                {
                  "type": "Aperture",
                  "identifier": "Right_IntWin",
                  "boundary_condition": {"type": "Surface", "boundary_condition_objects": ["Left_IntWin", "Left_SharedWall", "RoomLeft"]},
                  "geometry": {
                    "type": "Face3D",
                    "plane": {"n": [-1,0,0], "o": [5,3,1], "x": [0,-1,0]},
                    "boundary": [[5,3,1],[5,1,1],[5,1,2.2],[5,3,2.2]]
                  }
                }
              ]
            },
            {
              "type": "Face",
              "identifier": "Upper_Floor",
              "face_type": "Floor",
              "boundary_condition": {"type": "Surface"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,0,-1], "o": [0,4,3], "x": [1,0,0]},
                "boundary": [[0,4,3],[5,4,3],[5,0,3],[0,0,3]]
              }
            }
          ]
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    let find = |id: &str| scene.objects.iter().find(|o| o.identifier == id).unwrap();
    let ext_wall = find("Left_ExtWall");
    let left_wall = find("Left_SharedWall");
    let left_win = find("Left_IntWin");
    let right_wall = find("Right_SharedWall");
    let right_win = find("Right_IntWin");
    let left_ceil = find("Left_Ceiling");
    let upper_floor = find("Upper_Floor");

    // Exterior Outdoors wall stays at exact x = 0.0
    for v in scene.vertices.iter().filter(|v| v.object_id == ext_wall.object_id) {
        assert!(v.position[0].abs() < 1e-5);
    }
    // Left Room's Surface wall (+X normal) and its interior window inset inward to x = 4.998
    for v in scene.vertices.iter().filter(|v| v.object_id == left_wall.object_id) {
        assert!((v.position[0] - 4.998).abs() < 1e-5, "got x={}", v.position[0]);
    }
    for v in scene.vertices.iter().filter(|v| v.object_id == left_win.object_id) {
        assert!((v.position[0] - 4.998).abs() < 1e-5, "got x={}", v.position[0]);
    }
    // Right Room's Surface wall (-X normal) and its interior window inset inward to x = 5.002
    for v in scene.vertices.iter().filter(|v| v.object_id == right_wall.object_id) {
        assert!((v.position[0] - 5.002).abs() < 1e-5, "got x={}", v.position[0]);
    }
    for v in scene.vertices.iter().filter(|v| v.object_id == right_win.object_id) {
        assert!((v.position[0] - 5.002).abs() < 1e-5, "got x={}", v.position[0]);
    }
    // Ceiling (+Z normal) insets down to z = 2.998, Floor (-Z normal) insets up to z = 3.002
    for v in scene.vertices.iter().filter(|v| v.object_id == left_ceil.object_id) {
        assert!((v.position[2] - 2.998).abs() < 1e-5, "got z={}", v.position[2]);
    }
    for v in scene.vertices.iter().filter(|v| v.object_id == upper_floor.object_id) {
        assert!((v.position[2] - 3.002).abs() < 1e-5, "got z={}", v.position[2]);
    }
    // Both rooms retain independent ownership for Room Edit Mode picking
    assert_ne!(left_wall.owner_room_id, right_wall.owner_room_id);
}

#[test]
fn coincident_same_type_same_normal_faces_and_shades_are_deduplicated() {
    let json = r#"{
      "type": "Model",
      "identifier": "DedupModel",
      "rooms": [
        {
          "type": "Room",
          "identifier": "R1",
          "faces": [
            {
              "type": "Face",
              "identifier": "Wall_Original",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [0,0,0], "x": [1,0,0]},
                "boundary": [[0,0,0],[4,0,0],[4,0,3],[0,0,3]]
              }
            },
            {
              "type": "Face",
              "identifier": "Wall_Duplicate",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [0,0.0002,0], "x": [1,0,0]},
                "boundary": [[0,0.0002,0],[4,0.0002,0],[4,0.0002,3],[0,0.0002,3]]
              }
            },
            {
              "type": "Face",
              "identifier": "Wall_AdjacentSibling",
              "face_type": "Wall",
              "boundary_condition": {"type": "Outdoors"},
              "geometry": {
                "type": "Face3D",
                "plane": {"n": [0,-1,0], "o": [4,0,0], "x": [1,0,0]},
                "boundary": [[4,0,0],[8,0,0],[8,0,3],[4,0,3]]
              }
            }
          ]
        }
      ],
      "orphaned_shades": [
        {
          "type": "Shade",
          "identifier": "Shade_Orig",
          "is_detached": true,
          "geometry": {"type": "Face3D", "boundary": [[0,-2,0],[3,-2,0],[3,-2,2],[0,-2,2]]}
        },
        {
          "type": "Shade",
          "identifier": "Shade_Dup",
          "is_detached": true,
          "geometry": {"type": "Face3D", "boundary": [[0,-2.0003,0],[3,-2.0003,0],[3,-2.0003,2],[0,-2.0003,2]]}
        }
      ],
      "shade_meshes": [
        {
          "type": "ShadeMesh",
          "identifier": "MeshWithInternalDup",
          "geometry": {
            "type": "Mesh3D",
            "vertices": [[10,0,0],[12,0,0],[12,2,0],[10,2,0]],
            "faces": [[0,1,2,3],[0,1,2,3]]
          }
        }
      ]
    }"#;

    let scene = load_hbjson_str(json, None, None).unwrap();
    assert_scene_invariants(&scene);

    // Wall_Original & Wall_AdjacentSibling kept; Wall_Duplicate rejected!
    assert!(scene.objects.iter().any(|o| o.identifier == "Wall_Original"));
    assert!(scene.objects.iter().any(|o| o.identifier == "Wall_AdjacentSibling"));
    assert!(!scene.objects.iter().any(|o| o.identifier == "Wall_Duplicate"));

    // Shade_Orig kept; Shade_Dup rejected!
    assert!(scene.objects.iter().any(|o| o.identifier == "Shade_Orig"));
    assert!(!scene.objects.iter().any(|o| o.identifier == "Shade_Dup"));

    // MeshWithInternalDup kept once with area 4.0 (NOT 8.0)!
    let mesh = scene
        .objects
        .iter()
        .find(|o| o.identifier == "MeshWithInternalDup")
        .unwrap();
    assert!((mesh.area.unwrap() - 4.0).abs() < 1e-4);
    assert!((mesh_area_for_object(&scene, mesh.object_id) - 4.0).abs() < 1e-4);
}
