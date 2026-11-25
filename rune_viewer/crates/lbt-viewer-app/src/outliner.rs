//! Direct Honeybee Schema outliner tree, ownership lookups, and AI context formatting.

use std::collections::HashMap;

use lbt_scene::{ObjectKind, ObjectRecord, PinStatus, SceneData, SpatialPin, ValidationIssue};

/// Direct Honeybee Schema outliner tree rooted at `Model`:
///
/// ```text
/// - Model
///   -- Room_1
///     --- Face_1
///       ---- Door_1
///       ---- Aperture_1
///         ----- Shade_1
///       ---- Shade_2
///     --- Shade_3
///   -- Room_2
///   -- Shades    (orphaned shades + shade_meshes, when present)
///   -- Faces     (orphaned faces, when present)
///   -- Apertures (orphaned apertures, when present)
///   -- Doors     (orphaned doors, when present)
/// ```
#[derive(Clone, Debug, Default)]
pub struct OutlinerTree {
    /// Model display name from `scene.display_name` / `scene.model_identifier` (`None` -> fallback `"Model"`/`"模型"`).
    pub model_name: Option<String>,
    pub rooms: Vec<RoomNode>,
    pub orphaned_shades: Vec<ShadeNode>,
    pub orphaned_faces: Vec<FaceNode>,
    pub orphaned_apertures: Vec<SubfaceNode>,
    pub orphaned_doors: Vec<SubfaceNode>,
}

impl OutlinerTree {
    /// Return `true` when the tree contains neither rooms nor orphaned geometry.
    pub fn is_empty(&self) -> bool {
        self.rooms.is_empty()
            && self.orphaned_shades.is_empty()
            && self.orphaned_faces.is_empty()
            && self.orphaned_apertures.is_empty()
            && self.orphaned_doors.is_empty()
    }
}

/// Room node whose direct children are `Faces`, then Room `Shades`.
#[derive(Clone, Debug)]
pub struct RoomNode {
    pub object_id: u32,
    pub label: String,
    pub faces: Vec<FaceNode>,
    pub shades: Vec<ShadeNode>,
}

impl RoomNode {
    /// Return `true` when this room has any child faces or shades.
    pub fn has_children(&self) -> bool {
        !self.faces.is_empty() || !self.shades.is_empty()
    }
}

/// Face node whose direct children are `Doors`, then `Apertures`, then `Shades`.
#[derive(Clone, Debug)]
pub struct FaceNode {
    pub object_id: u32,
    pub label: String,
    pub doors: Vec<SubfaceNode>,
    pub apertures: Vec<SubfaceNode>,
    pub shades: Vec<ShadeNode>,
}

impl FaceNode {
    /// Return `true` when this face owns any doors, apertures, or face shades.
    pub fn has_children(&self) -> bool {
        !self.doors.is_empty() || !self.apertures.is_empty() || !self.shades.is_empty()
    }
}

/// Door or Aperture node whose direct children are attached `Shades`.
#[derive(Clone, Debug)]
pub struct SubfaceNode {
    pub object_id: u32,
    pub kind: ObjectKind,
    pub label: String,
    pub shades: Vec<ShadeNode>,
}

impl SubfaceNode {
    /// Return `true` when this door/aperture owns attached shades.
    pub fn has_children(&self) -> bool {
        !self.shades.is_empty()
    }
}

/// Shade or ShadeMesh leaf node.
#[derive(Clone, Debug)]
pub struct ShadeNode {
    pub object_id: u32,
    pub label: String,
}

fn display_label(rec: &ObjectRecord) -> String {
    rec.display_name
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or(&rec.identifier)
        .to_owned()
}

fn make_shade_node(rec: &ObjectRecord) -> ShadeNode {
    ShadeNode {
        object_id: rec.object_id,
        label: display_label(rec),
    }
}

fn build_subface_node(
    rec: &ObjectRecord,
    children_by_parent: &HashMap<u32, Vec<&ObjectRecord>>,
) -> SubfaceNode {
    let shades = children_by_parent
        .get(&rec.object_id)
        .map(|items| {
            items
                .iter()
                .filter(|c| c.kind == ObjectKind::Shade)
                .map(|c| make_shade_node(c))
                .collect()
        })
        .unwrap_or_default();
    SubfaceNode {
        object_id: rec.object_id,
        kind: rec.kind,
        label: display_label(rec),
        shades,
    }
}

fn build_face_node(
    rec: &ObjectRecord,
    children_by_parent: &HashMap<u32, Vec<&ObjectRecord>>,
) -> FaceNode {
    let mut doors = Vec::new();
    let mut apertures = Vec::new();
    let mut shades = Vec::new();
    if let Some(items) = children_by_parent.get(&rec.object_id) {
        for &child in items {
            match child.kind {
                ObjectKind::Door => doors.push(build_subface_node(child, children_by_parent)),
                ObjectKind::Aperture => {
                    apertures.push(build_subface_node(child, children_by_parent))
                }
                ObjectKind::Shade => shades.push(make_shade_node(child)),
                _ => {}
            }
        }
    }
    FaceNode {
        object_id: rec.object_id,
        label: display_label(rec),
        doors,
        apertures,
        shades,
    }
}

/// Build the direct Honeybee Schema outliner tree from `scene.objects` with zero synthetic folders.
pub fn build_outliner(scene: &SceneData) -> OutlinerTree {
    let mut children_by_parent: HashMap<u32, Vec<&ObjectRecord>> = HashMap::new();
    let mut room_records: Vec<&ObjectRecord> = Vec::new();
    let mut orphan_roots: Vec<&ObjectRecord> = Vec::new();

    for rec in &scene.objects {
        if let Some(pid) = rec.parent_object_id {
            children_by_parent.entry(pid).or_default().push(rec);
        } else if rec.kind == ObjectKind::Room {
            room_records.push(rec);
        } else {
            orphan_roots.push(rec);
        }
    }

    let rooms = room_records
        .into_iter()
        .map(|room| {
            let mut faces = Vec::new();
            let mut shades = Vec::new();
            if let Some(room_children) = children_by_parent.get(&room.object_id) {
                for &child in room_children {
                    match child.kind {
                        ObjectKind::Face => {
                            faces.push(build_face_node(child, &children_by_parent));
                        }
                        ObjectKind::Shade => {
                            shades.push(make_shade_node(child));
                        }
                        _ => {}
                    }
                }
            }
            RoomNode {
                object_id: room.object_id,
                label: display_label(room),
                faces,
                shades,
            }
        })
        .collect();

    let mut orphaned_shades = Vec::new();
    let mut orphaned_faces = Vec::new();
    let mut orphaned_apertures = Vec::new();
    let mut orphaned_doors = Vec::new();

    for rec in orphan_roots {
        match rec.kind {
            ObjectKind::Shade => orphaned_shades.push(make_shade_node(rec)),
            ObjectKind::Face => orphaned_faces.push(build_face_node(rec, &children_by_parent)),
            ObjectKind::Aperture => {
                orphaned_apertures.push(build_subface_node(rec, &children_by_parent))
            }
            ObjectKind::Door => orphaned_doors.push(build_subface_node(rec, &children_by_parent)),
            ObjectKind::Room => {}
        }
    }

    let model_name = scene
        .display_name
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .or_else(|| {
            let id = scene.model_identifier.trim();
            (!id.is_empty()).then_some(id)
        })
        .map(str::to_owned);

    OutlinerTree {
        model_name,
        rooms,
        orphaned_shades,
        orphaned_faces,
        orphaned_apertures,
        orphaned_doors,
    }
}

/// Resolve the owning `Room` ID for `object_id`, returning `None` for orphaned geometry or `ShadeMesh`es.
pub fn find_owner_room_id(scene: &SceneData, object_id: u32) -> Option<u32> {
    let rec = scene.object_by_id(object_id)?;
    if let Some(rid) = rec.owner_room_id {
        return Some(rid);
    }
    if rec.is_orphaned {
        return None;
    }
    find_parent_room(scene, rec).map(|room| room.object_id)
}

/// Walk ownership / `parent_object_id` upward to find the owning `Room` record, if any.
pub fn find_parent_room<'a>(scene: &'a SceneData, rec: &'a ObjectRecord) -> Option<&'a ObjectRecord> {
    if let Some(rid) = rec.owner_room_id {
        return scene.object_by_id(rid);
    }
    if rec.kind == ObjectKind::Room {
        return Some(rec);
    }
    if rec.is_orphaned {
        return None;
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

/// Escalate a picked `object_id` to its owning `Room` id (or keep `object_id` if orphaned).
pub fn escalate_to_room_id(scene: &SceneData, object_id: u32) -> u32 {
    find_owner_room_id(scene, object_id).unwrap_or(object_id)
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
                ObjectKind::Door => {
                    cand.is_glass == anchor.is_glass
                        && (anchor.boundary_condition.is_none()
                            || cand.boundary_condition == anchor.boundary_condition)
                }
                ObjectKind::Aperture => {
                    anchor.boundary_condition.is_none()
                        || cand.boundary_condition == anchor.boundary_condition
                }
                ObjectKind::Shade => {
                    cand.is_indoor_shade == anchor.is_indoor_shade
                        && cand.is_detached_shade == anchor.is_detached_shade
                        && cand.is_shade_mesh == anchor.is_shade_mesh
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
                if find_owner_room_id(scene, obj.object_id) == Some(id) {
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

    fn make_record(
        id: u32,
        kind: ObjectKind,
        name: &str,
        parent: Option<u32>,
        owner_room: Option<u32>,
        story: Option<&str>,
    ) -> ObjectRecord {
        ObjectRecord {
            object_id: id,
            kind,
            identifier: name.to_owned(),
            display_name: None,
            target: ObjectTargetRef::new(None, "TestModel", kind, name),
            bounds: Bounds3::new([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]),
            centroid: [0.5, 0.5, 0.5],
            parent_object_id: parent,
            owner_room_id: owner_room,
            is_orphaned: owner_room.is_none() && kind != ObjectKind::Room,
            is_glass: false,
            is_indoor_shade: false,
            is_detached_shade: false,
            is_shade_mesh: false,
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
    fn builds_direct_honeybee_hierarchy_combining_orphaned_shades_and_shade_meshes() {
        let mut glass_door =
            make_record(4, ObjectKind::Door, "Patio_Door", Some(2), Some(1), Some("Level_1"));
        glass_door.is_glass = true;
        let ap_shade =
            make_record(5, ObjectKind::Shade, "Win_Overhang", Some(3), Some(1), Some("Level_1"));
        let mut room_shade = make_record(
            6,
            ObjectKind::Shade,
            "Room_Partition",
            Some(1),
            Some(1),
            Some("Level_1"),
        );
        room_shade.is_indoor_shade = true;
        let mut ctx_shade = make_record(7, ObjectKind::Shade, "Neighbor_Bldg", None, None, None);
        ctx_shade.is_detached_shade = true;
        let mut shade_mesh = make_record(8, ObjectKind::Shade, "Tree_Canopy", None, None, None);
        shade_mesh.is_detached_shade = true;
        shade_mesh.is_shade_mesh = true;

        let scene = SceneData {
            model_identifier: "Office".to_owned(),
            stories: vec!["Level_1".to_owned()],
            objects: vec![
                make_record(1, ObjectKind::Room, "Room_A", None, Some(1), Some("Level_1")),
                make_record(2, ObjectKind::Face, "Face_South", Some(1), Some(1), Some("Level_1")),
                make_record(3, ObjectKind::Aperture, "Win_1", Some(2), Some(1), Some("Level_1")),
                glass_door,
                ap_shade,
                room_shade,
                ctx_shade,
                shade_mesh,
            ],
            ..Default::default()
        };

        let tree = build_outliner(&scene);
        assert_eq!(tree.model_name.as_deref(), Some("Office"));
        assert_eq!(tree.rooms.len(), 1);
        let room = &tree.rooms[0];
        assert_eq!(room.faces.len(), 1);
        assert_eq!(room.faces[0].doors.len(), 1);
        assert_eq!(room.faces[0].apertures.len(), 1);
        assert_eq!(room.faces[0].apertures[0].shades.len(), 1);
        assert_eq!(room.faces[0].apertures[0].shades[0].object_id, 5);
        assert_eq!(room.shades.len(), 1);
        assert_eq!(room.shades[0].object_id, 6);

        // Orphaned shades + shade meshes combined directly under orphaned_shades
        assert_eq!(tree.orphaned_shades.len(), 2);
        assert_eq!(tree.orphaned_shades[0].object_id, 7);
        assert_eq!(tree.orphaned_shades[1].object_id, 8);

        assert_eq!(find_owner_room_id(&scene, 5), Some(1));
        assert_eq!(find_owner_room_id(&scene, 7), None);
        assert_eq!(escalate_to_room_id(&scene, 3), 1);
        assert_eq!(escalate_to_room_id(&scene, 7), 7);
        assert_eq!(expand_render_ids(&scene, &[1]), vec![1, 2, 3, 4, 5, 6]);

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
