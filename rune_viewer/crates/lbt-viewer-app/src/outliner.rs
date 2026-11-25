//! Model hierarchy outliner, object lookup helpers, and AI context formatting.

use std::collections::{BTreeMap, HashMap};

use lbt_scene::{ObjectKind, ObjectRecord, PinStatus, SceneData, SpatialPin, ValidationIssue};

/// Hierarchical outliner tree grouped as `Story -> Room -> Face -> Sub-faces/Shades`.
#[derive(Clone, Debug, Default)]
pub struct OutlinerTree {
    pub stories: Vec<StoryNode>,
    pub orphaned: Vec<OrphanNode>,
}

/// Story group containing rooms.
#[derive(Clone, Debug)]
pub struct StoryNode {
    pub name: String,
    pub rooms: Vec<RoomNode>,
}

/// Room node containing child faces and room-level shades.
#[derive(Clone, Debug)]
pub struct RoomNode {
    pub object_id: u32,
    pub label: String,
    pub faces: Vec<FaceNode>,
    pub shades: Vec<LeafNode>,
}

/// Face node containing child apertures, doors, and shades.
#[derive(Clone, Debug)]
pub struct FaceNode {
    pub object_id: u32,
    pub label: String,
    pub children: Vec<LeafNode>,
}

/// Leaf node (aperture, door, or shade).
#[derive(Clone, Debug)]
pub struct LeafNode {
    pub object_id: u32,
    pub kind: ObjectKind,
    pub label: String,
}

/// Top-level orphaned object node.
#[derive(Clone, Debug)]
pub struct OrphanNode {
    pub object_id: u32,
    pub kind: ObjectKind,
    pub label: String,
    pub children: Vec<LeafNode>,
}

fn display_label(rec: &ObjectRecord) -> String {
    rec.display_name
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or(&rec.identifier)
        .to_owned()
}

/// Build a deterministic outliner tree from `scene.objects`.
pub fn build_outliner(scene: &SceneData) -> OutlinerTree {
    let mut children_by_parent: HashMap<u32, Vec<&ObjectRecord>> = HashMap::new();
    let mut rooms: Vec<&ObjectRecord> = Vec::new();
    let mut orphan_roots: Vec<&ObjectRecord> = Vec::new();

    for rec in &scene.objects {
        if let Some(pid) = rec.parent_object_id {
            children_by_parent.entry(pid).or_default().push(rec);
        } else if rec.kind == ObjectKind::Room {
            rooms.push(rec);
        } else {
            orphan_roots.push(rec);
        }
    }

    let mut story_map: BTreeMap<String, Vec<RoomNode>> = BTreeMap::new();
    for room in rooms {
        let story = room
            .story
            .as_deref()
            .filter(|s| !s.trim().is_empty())
            .unwrap_or("Unassigned Story")
            .to_owned();
        let mut faces = Vec::new();
        let mut shades = Vec::new();

        if let Some(room_children) = children_by_parent.get(&room.object_id) {
            for &child in room_children {
                match child.kind {
                    ObjectKind::Face => {
                        let sub = children_by_parent
                            .get(&child.object_id)
                            .map(|items| {
                                items
                                    .iter()
                                    .map(|item| LeafNode {
                                        object_id: item.object_id,
                                        kind: item.kind,
                                        label: display_label(item),
                                    })
                                    .collect()
                            })
                            .unwrap_or_default();
                        faces.push(FaceNode {
                            object_id: child.object_id,
                            label: display_label(child),
                            children: sub,
                        });
                    }
                    _ => shades.push(LeafNode {
                        object_id: child.object_id,
                        kind: child.kind,
                        label: display_label(child),
                    }),
                }
            }
        }

        story_map.entry(story).or_default().push(RoomNode {
            object_id: room.object_id,
            label: display_label(room),
            faces,
            shades,
        });
    }

    let mut stories = Vec::new();
    for story_name in &scene.stories {
        if let Some(room_nodes) = story_map.remove(story_name) {
            stories.push(StoryNode {
                name: story_name.clone(),
                rooms: room_nodes,
            });
        }
    }
    for (name, room_nodes) in story_map {
        stories.push(StoryNode {
            name,
            rooms: room_nodes,
        });
    }

    let orphaned = orphan_roots
        .into_iter()
        .map(|rec| {
            let children = children_by_parent
                .get(&rec.object_id)
                .map(|items| {
                    items
                        .iter()
                        .map(|item| LeafNode {
                            object_id: item.object_id,
                            kind: item.kind,
                            label: display_label(item),
                        })
                        .collect()
                })
                .unwrap_or_default();
            OrphanNode {
                object_id: rec.object_id,
                kind: rec.kind,
                label: display_label(rec),
                children,
            }
        })
        .collect();

    OutlinerTree { stories, orphaned }
}

/// Walk `parent_object_id` upward to find the owning Room record, if any.
pub fn find_parent_room<'a>(scene: &'a SceneData, rec: &'a ObjectRecord) -> Option<&'a ObjectRecord> {
    if rec.kind == ObjectKind::Room {
        return Some(rec);
    }
    let mut cur = rec.parent_object_id;
    for _ in 0..8 {
        let pid = cur?;
        let parent = scene.object_by_id(pid)?;
        if parent.kind == ObjectKind::Room {
            return Some(parent);
        }
        cur = parent.parent_object_id;
    }
    None
}

/// Escalate a picked `object_id` to its parent `Room` id (for double-click escalation).
pub fn escalate_to_room_id(scene: &SceneData, object_id: u32) -> u32 {
    let Some(rec) = scene.object_by_id(object_id) else {
        return object_id;
    };
    find_parent_room(scene, rec)
        .map(|room| room.object_id)
        .unwrap_or(object_id)
}

/// Compute an average surface normal for `object_id` directly from `scene.vertices`.
pub fn average_object_normal(scene: &SceneData, object_id: u32) -> Option<[f32; 3]> {
    let mut sum = [0.0_f32; 3];
    let mut count = 0usize;
    for v in &scene.vertices {
        if v.object_id == object_id {
            sum[0] += v.normal[0];
            sum[1] += v.normal[1];
            sum[2] += v.normal[2];
            count += 1;
        }
    }
    if count == 0 {
        return None;
    }
    let len = (sum[0] * sum[0] + sum[1] * sum[1] + sum[2] * sum[2]).sqrt();
    if len <= 1e-6 {
        return None;
    }
    Some([sum[0] / len, sum[1] / len, sum[2] / len])
}

/// Format an orientation cardinal/tilt string from a unit normal (Z-up, +Y = North, +X = East).
pub fn orientation_from_normal(normal: [f32; 3]) -> &'static str {
    let [nx, ny, nz] = normal;
    if nz >= 0.85 {
        return "Horizontal Up";
    }
    if nz <= -0.85 {
        return "Horizontal Down";
    }
    let deg = nx.atan2(ny).to_degrees().rem_euclid(360.0);
    if !(22.5..337.5).contains(&deg) {
        "N"
    } else if deg < 67.5 {
        "NE"
    } else if deg < 112.5 {
        "E"
    } else if deg < 157.5 {
        "SE"
    } else if deg < 202.5 {
        "S"
    } else if deg < 247.5 {
        "SW"
    } else if deg < 292.5 {
        "W"
    } else {
        "NW"
    }
}

/// Return all object IDs matching `anchor` in kind and primary semantic attributes.
pub fn select_similar_ids(scene: &SceneData, anchor: &ObjectRecord) -> Vec<u32> {
    scene
        .objects
        .iter()
        .filter(|cand| {
            if cand.kind != anchor.kind {
                return false;
            }
            match anchor.kind {
                ObjectKind::Room => {
                    if anchor.program_type.is_some() {
                        cand.program_type == anchor.program_type
                    } else if anchor.story.is_some() {
                        cand.story == anchor.story
                    } else {
                        true
                    }
                }
                ObjectKind::Face => {
                    cand.face_type == anchor.face_type
                        && cand.boundary_condition == anchor.boundary_condition
                }
                ObjectKind::Aperture | ObjectKind::Door | ObjectKind::Shade => {
                    if anchor.boundary_condition.is_some() {
                        cand.boundary_condition == anchor.boundary_condition
                    } else {
                        true
                    }
                }
            }
        })
        .map(|cand| cand.object_id)
        .collect()
}

/// Expand any `Room` object IDs into their renderable descendant mesh IDs (for GPU highlight/isolation).
pub fn expand_render_ids(scene: &SceneData, selected_ids: &[u32]) -> Vec<u32> {
    let mut out = Vec::new();
    let mut push_unique = |id: u32| {
        if id != 0 && !out.contains(&id) {
            out.push(id);
        }
    };
    for &id in selected_ids {
        let Some(rec) = scene.object_by_id(id) else {
            continue;
        };
        push_unique(id);
        if rec.kind == ObjectKind::Room {
            for obj in &scene.objects {
                if find_parent_room(scene, obj).is_some_and(|r| r.object_id == id) {
                    push_unique(obj.object_id);
                }
            }
        }
    }
    out
}

/// Resolve a `ValidationIssue` to matching `object_id`s in `scene`.
pub fn issue_object_ids(scene: &SceneData, issue: &ValidationIssue) -> Vec<u32> {
    let mut ids = Vec::new();
    if let Some(target) = &issue.target
        && let Some(rec) = scene.find_by_target(target)
    {
        ids.push(rec.object_id);
    }
    for target in &issue.targets {
        if let Some(rec) = scene.find_by_target(target)
            && !ids.contains(&rec.object_id)
        {
            ids.push(rec.object_id);
        }
    }
    for elem_id in &issue.element_id {
        for rec in &scene.objects {
            if rec.identifier == *elem_id && !ids.contains(&rec.object_id) {
                ids.push(rec.object_id);
            }
        }
    }
    ids
}

/// Build a compact AI context prompt referencing current selection, open spatial pins, and `GD_Web_View_Get_Context`.
pub fn format_ai_context_prompt(
    model_label: &str,
    garden_root: Option<&str>,
    selected: &[&ObjectRecord],
    annotations: &[SpatialPin],
    validation_issues: &[ValidationIssue],
) -> String {
    let open_pins: Vec<&SpatialPin> = annotations
        .iter()
        .filter(|p| p.status == PinStatus::Open)
        .collect();

    let mut lines = Vec::new();
    match garden_root {
        Some(root) => lines.push(format!(
            "[Honeybee 3D Viewer Context] Model: {model_label} | Garden: {root}"
        )),
        None => lines.push(format!("[Honeybee 3D Viewer Context] Model: {model_label}")),
    }

    if selected.is_empty() {
        lines.push("Selected: none".to_owned());
    } else {
        let names: Vec<String> = selected
            .iter()
            .take(6)
            .map(|rec| format!("{}:{}", rec.kind.as_str(), rec.identifier))
            .collect();
        let extra = if selected.len() > 6 {
            format!(" (+{} more)", selected.len() - 6)
        } else {
            String::new()
        };
        lines.push(format!("Selected ({}): {}{extra}", selected.len(), names.join(", ")));
    }

    if open_pins.is_empty() {
        lines.push("Open Pins: 0".to_owned());
    } else {
        let pin_summaries: Vec<String> = open_pins
            .iter()
            .take(5)
            .map(|pin| {
                let target_txt = pin
                    .target
                    .as_ref()
                    .map(|t| format!("{}:{}", t.object_type.as_str(), t.object_identifier))
                    .unwrap_or_else(|| "point".to_owned());
                let comment = if pin.comment.trim().is_empty() {
                    "(no comment)"
                } else {
                    pin.comment.trim()
                };
                format!("{} [{}]: {}", pin.id, target_txt, comment)
            })
            .collect();
        lines.push(format!(
            "Open Pins ({}): {}",
            open_pins.len(),
            pin_summaries.join(" | ")
        ));
    }

    if !validation_issues.is_empty() {
        lines.push(format!("Validation Issues: {}", validation_issues.len()));
    }

    lines.push("Call GD_Web_View_Get_Context to inspect structured targets, world_point coordinates, and resolve pins.".to_owned());
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use lbt_scene::{Bounds3, ObjectTargetRef};

    fn make_record(id: u32, kind: ObjectKind, name: &str, parent: Option<u32>, story: Option<&str>) -> ObjectRecord {
        ObjectRecord {
            object_id: id,
            kind,
            identifier: name.to_owned(),
            display_name: None,
            target: ObjectTargetRef::new(None, "TestModel", kind, name),
            bounds: Bounds3::new([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]),
            centroid: [0.5, 0.5, 0.5],
            parent_object_id: parent,
            face_type: (kind == ObjectKind::Face).then(|| "Wall".to_owned()),
            boundary_condition: (kind == ObjectKind::Face).then(|| "Outdoors".to_owned()),
            story: story.map(str::to_owned),
            zone: None,
            program_type: None,
            construction_set: None,
            hvac: None,
            wwr: None,
            area: Some(10.0),
        }
    }

    #[test]
    fn builds_hierarchy_escalates_room_and_formats_ai_context() {
        let scene = SceneData {
            model_identifier: "Office".to_owned(),
            stories: vec!["Level_1".to_owned()],
            objects: vec![
                make_record(1, ObjectKind::Room, "Room_A", None, Some("Level_1")),
                make_record(2, ObjectKind::Face, "Face_South", Some(1), Some("Level_1")),
                make_record(3, ObjectKind::Aperture, "Win_1", Some(2), Some("Level_1")),
            ],
            ..Default::default()
        };

        let tree = build_outliner(&scene);
        assert_eq!(tree.stories.len(), 1);
        assert_eq!(tree.stories[0].rooms[0].faces[0].children[0].object_id, 3);
        assert_eq!(escalate_to_room_id(&scene, 3), 1);
        assert_eq!(expand_render_ids(&scene, &[1]), vec![1, 2, 3]);

        let pin = SpatialPin {
            id: "pin_1".to_owned(),
            status: PinStatus::Open,
            target: Some(scene.objects[1].target.clone()),
            world_point: Some([1.0, 2.0, 3.0]),
            comment: "Add overhang".to_owned(),
            ..Default::default()
        };
        let prompt = format_ai_context_prompt(
            "Office",
            Some("/tmp/garden"),
            &[&scene.objects[1]],
            &[pin],
            &[],
        );
        assert!(prompt.contains("face:Face_South"));
        assert!(prompt.contains("Add overhang"));
        assert!(prompt.contains("GD_Web_View_Get_Context"));
    }
}
