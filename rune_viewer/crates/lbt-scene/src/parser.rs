//! HBJSON parser converting Honeybee `Model` files into [`SceneData`].

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::path::Path;

use glam::DVec3;
use serde::de::Deserializer;
use serde::Deserialize;

use crate::triangulate::{
    append_deduplicated_edges, infer_face_type_from_normal, offset_geometry, triangulate_face3d,
    triangulate_host_face, PlaneInput, TriangulatedGeometry,
};
use crate::types::{
    Bounds3, EdgeVertex, MeshVertex, ObjectKind, ObjectRecord, ObjectTargetRef, SceneData,
};

/// Errors produced when reading or parsing a Honeybee `.hbjson` model.
#[derive(Debug)]
pub enum SceneError {
    Io(std::io::Error),
    Json(serde_json::Error),
    InvalidModel(String),
}

impl fmt::Display for SceneError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(err) => write!(f, "Failed to read HBJSON file: {err}"),
            Self::Json(err) => write!(f, "Failed to parse HBJSON: {err}"),
            Self::InvalidModel(msg) => write!(f, "Invalid Honeybee model: {msg}"),
        }
    }
}

impl std::error::Error for SceneError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(err) => Some(err),
            Self::Json(err) => Some(err),
            Self::InvalidModel(_) => None,
        }
    }
}

impl From<std::io::Error> for SceneError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for SceneError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

fn deserialize_null_default<'de, D, T>(deserializer: D) -> Result<T, D::Error>
where
    T: Default + Deserialize<'de>,
    D: Deserializer<'de>,
{
    Ok(Option::<T>::deserialize(deserializer)?.unwrap_or_default())
}

#[derive(Deserialize)]
#[serde(untagged)]
enum RawPoint3D {
    Array([f64; 3]),
    Object { x: f64, y: f64, z: f64 },
}

impl RawPoint3D {
    fn into_dvec3(self, scale: f64) -> DVec3 {
        match self {
            Self::Array([x, y, z]) => DVec3::new(x * scale, y * scale, z * scale),
            Self::Object { x, y, z } => DVec3::new(x * scale, y * scale, z * scale),
        }
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
enum IdentifierRef {
    Name(String),
    Object {
        #[serde(default)]
        identifier: Option<String>,
    },
}

impl IdentifierRef {
    fn into_option(self) -> Option<String> {
        match self {
            Self::Name(s) => {
                let t = s.trim();
                if t.is_empty() {
                    None
                } else {
                    Some(t.to_owned())
                }
            }
            Self::Object { identifier } => identifier.and_then(|s| {
                let t = s.trim();
                if t.is_empty() {
                    None
                } else {
                    Some(t.to_owned())
                }
            }),
        }
    }
}

fn deserialize_identifier_ref<'de, D>(deserializer: D) -> Result<Option<String>, D::Error>
where
    D: Deserializer<'de>,
{
    Ok(Option::<IdentifierRef>::deserialize(deserializer)?.and_then(IdentifierRef::into_option))
}

#[derive(Deserialize)]
struct RawPlane {
    n: RawPoint3D,
    #[serde(default)]
    o: Option<RawPoint3D>,
    #[serde(default)]
    x: Option<RawPoint3D>,
}

impl RawPlane {
    fn into_plane_input(self, scale: f64) -> PlaneInput {
        let normal = self.n.into_dvec3(1.0);
        let origin = self
            .o
            .map(|p| p.into_dvec3(scale))
            .unwrap_or(DVec3::splat(f64::NAN));
        let x_axis = self.x.map(|p| p.into_dvec3(1.0));
        PlaneInput {
            origin,
            normal,
            x_axis,
        }
    }
}

#[derive(Default, Deserialize)]
struct RawFace3D {
    #[serde(default, deserialize_with = "deserialize_null_default")]
    boundary: Vec<RawPoint3D>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    holes: Vec<Vec<RawPoint3D>>,
    #[serde(default)]
    plane: Option<RawPlane>,
}

#[derive(Deserialize)]
struct RawMesh3D {
    #[serde(default, deserialize_with = "deserialize_null_default")]
    vertices: Vec<RawPoint3D>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    faces: Vec<Vec<usize>>,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum RawBoundaryCondition {
    Name(String),
    Object {
        #[serde(rename = "type")]
        bc_type: Option<String>,
    },
}

impl RawBoundaryCondition {
    fn into_name(self) -> Option<String> {
        match self {
            Self::Name(s) => (!s.trim().is_empty()).then(|| s.trim().to_owned()),
            Self::Object { bc_type } => bc_type.filter(|s| !s.trim().is_empty()),
        }
    }
}

#[derive(Default, Deserialize)]
struct RawRoomEnergyProps {
    #[serde(default, deserialize_with = "deserialize_identifier_ref")]
    program_type: Option<String>,
    #[serde(default, deserialize_with = "deserialize_identifier_ref")]
    construction_set: Option<String>,
    #[serde(default, deserialize_with = "deserialize_identifier_ref")]
    hvac: Option<String>,
    #[serde(default)]
    story: Option<String>,
    #[serde(default)]
    zone: Option<String>,
}

#[derive(Default, Deserialize)]
struct RawRoomProperties {
    #[serde(default)]
    energy: Option<RawRoomEnergyProps>,
}

#[derive(Deserialize)]
struct RawShade {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    geometry: RawFace3D,
    #[serde(default)]
    is_detached: Option<bool>,
}

#[derive(Deserialize)]
struct RawShadeMesh {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    geometry: RawMesh3D,
    #[serde(default)]
    is_detached: Option<bool>,
}

#[derive(Deserialize)]
struct RawAperture {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    geometry: RawFace3D,
    #[serde(default)]
    boundary_condition: Option<RawBoundaryCondition>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    indoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    outdoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    shades: Vec<RawShade>,
}

#[derive(Deserialize)]
struct RawDoor {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    geometry: RawFace3D,
    #[serde(default)]
    boundary_condition: Option<RawBoundaryCondition>,
    #[serde(default)]
    is_glass: Option<bool>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    indoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    outdoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    shades: Vec<RawShade>,
}

#[derive(Deserialize)]
struct RawFace {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    geometry: RawFace3D,
    #[serde(default)]
    face_type: Option<String>,
    #[serde(default)]
    boundary_condition: Option<RawBoundaryCondition>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    apertures: Vec<RawAperture>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    doors: Vec<RawDoor>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    indoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    outdoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    shades: Vec<RawShade>,
}

#[derive(Deserialize)]
struct RawRoom {
    identifier: String,
    #[serde(default)]
    display_name: Option<String>,
    #[serde(default)]
    story: Option<String>,
    #[serde(default)]
    zone: Option<String>,
    #[serde(default)]
    properties: Option<RawRoomProperties>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    faces: Vec<RawFace>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    indoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    outdoor_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    shades: Vec<RawShade>,
}

#[derive(Deserialize)]
struct RawModel {
    #[serde(rename = "type", default)]
    model_type: Option<String>,
    #[serde(default)]
    identifier: Option<String>,
    #[serde(default)]
    display_name: Option<String>,
    #[serde(default)]
    units: Option<String>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    rooms: Vec<RawRoom>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    orphaned_faces: Vec<RawFace>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    orphaned_apertures: Vec<RawAperture>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    orphaned_doors: Vec<RawDoor>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    orphaned_shades: Vec<RawShade>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    shade_meshes: Vec<RawShadeMesh>,
}

fn unit_scale_to_meters(units: Option<&str>) -> Result<f64, SceneError> {
    let Some(raw) = units.map(str::trim).filter(|s| !s.is_empty()) else {
        return Ok(1.0);
    };
    match raw.to_ascii_lowercase().as_str() {
        "meters" | "meter" | "m" => Ok(1.0),
        "millimeters" | "millimeter" | "mm" => Ok(0.001),
        "centimeters" | "centimeter" | "cm" => Ok(0.01),
        "feet" | "foot" | "ft" => Ok(0.3048),
        "inches" | "inch" | "in" => Ok(0.0254),
        other => Err(SceneError::InvalidModel(format!(
            "Unsupported Honeybee units: {other}"
        ))),
    }
}

#[derive(Clone, Default)]
struct RoomMetadata {
    story: Option<String>,
    zone: Option<String>,
    program_type: Option<String>,
    construction_set: Option<String>,
    hvac: Option<String>,
}

struct ParsedFace3D {
    boundary: Vec<DVec3>,
    holes: Vec<Vec<DVec3>>,
    plane: Option<PlaneInput>,
}

fn convert_face3d(raw: RawFace3D, scale: f64) -> ParsedFace3D {
    let boundary = raw
        .boundary
        .into_iter()
        .map(|p| p.into_dvec3(scale))
        .collect();
    let holes = raw
        .holes
        .into_iter()
        .map(|hole| hole.into_iter().map(|p| p.into_dvec3(scale)).collect())
        .collect();
    let plane = raw.plane.map(|p| p.into_plane_input(scale));
    ParsedFace3D {
        boundary,
        holes,
        plane,
    }
}

fn build_target(
    garden_id: Option<&str>,
    model_identifier: &str,
    object_type: ObjectKind,
    object_identifier: &str,
    parent: BTreeMap<String, String>,
) -> ObjectTargetRef {
    let mut target = ObjectTargetRef::new(
        garden_id.map(str::to_owned),
        model_identifier,
        object_type,
        object_identifier,
    );
    target.parent = parent;
    target
}

struct SceneBuilder {
    garden_id: Option<String>,
    model_identifier: String,
    unit_scale: f64,
    next_id: u32,
    scene_bounds: Bounds3,
    vertices: Vec<MeshVertex>,
    indices: Vec<u32>,
    edge_vertices: Vec<EdgeVertex>,
    objects: Vec<ObjectRecord>,
}

impl SceneBuilder {
    fn new(garden_id: Option<&str>, model_identifier: String, unit_scale: f64) -> Self {
        Self {
            garden_id: garden_id.map(str::to_owned),
            model_identifier,
            unit_scale,
            next_id: 1,
            scene_bounds: Bounds3::empty(),
            vertices: Vec::new(),
            indices: Vec::new(),
            edge_vertices: Vec::new(),
            objects: Vec::new(),
        }
    }

    fn alloc_id(&mut self) -> u32 {
        let id = self.next_id;
        self.next_id = self.next_id.saturating_add(1);
        id
    }

    fn push_triangulated_geometry(&mut self, geom: &TriangulatedGeometry, object_id: u32) {
        if !geom.vertices.is_empty() && !geom.indices.is_empty() {
            let base_vertex = self.vertices.len() as u32;
            self.vertices.extend_from_slice(&geom.vertices);
            self.indices
                .extend(geom.indices.iter().map(|&idx| base_vertex + idx));
        }
        append_deduplicated_edges(&geom.edge_loops, object_id, &mut self.edge_vertices);
        self.scene_bounds.merge(&geom.bounds);
    }

    fn add_shade(
        &mut self,
        raw: RawShade,
        is_indoor: bool,
        parent_object_id: Option<u32>,
        parent_map: BTreeMap<String, String>,
        room_meta: &RoomMetadata,
    ) {
        let object_id = self.alloc_id();
        let face3d = convert_face3d(raw.geometry, self.unit_scale);
        let geom = triangulate_face3d(
            &face3d.boundary,
            &face3d.holes,
            face3d.plane,
            object_id,
            ObjectKind::Shade,
        );
        self.push_triangulated_geometry(&geom, object_id);

        let shade_subtype = if is_indoor {
            "IndoorShade"
        } else if raw.is_detached.unwrap_or(false) {
            "ContextShade"
        } else {
            "OutdoorShade"
        };

        let target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Shade,
            &raw.identifier,
            parent_map,
        );
        self.objects.push(ObjectRecord {
            object_id,
            kind: ObjectKind::Shade,
            identifier: raw.identifier,
            display_name: raw.display_name,
            target,
            bounds: geom.bounds,
            centroid: geom.centroid,
            parent_object_id,
            face_type: Some(shade_subtype.to_owned()),
            boundary_condition: None,
            story: room_meta.story.clone(),
            zone: room_meta.zone.clone(),
            program_type: room_meta.program_type.clone(),
            construction_set: room_meta.construction_set.clone(),
            hvac: room_meta.hvac.clone(),
            wwr: None,
            area: Some(geom.area),
        });
    }

    fn add_shade_mesh(&mut self, raw: RawShadeMesh) {
        let object_id = self.alloc_id();
        let verts: Vec<DVec3> = raw
            .geometry
            .vertices
            .into_iter()
            .map(|p| p.into_dvec3(self.unit_scale))
            .collect();

        let mut total_area = 0.0_f64;
        let mut weighted_centroid = DVec3::ZERO;
        let mut mesh_bounds = Bounds3::empty();
        let mut all_edge_loops: Vec<Vec<[f32; 3]>> = Vec::new();

        for face_indices in raw.geometry.faces {
            let poly: Vec<DVec3> = face_indices
                .into_iter()
                .filter_map(|idx| verts.get(idx).copied())
                .collect();
            if poly.len() < 3 {
                continue;
            }
            let geom = triangulate_face3d(&poly, &[], None, object_id, ObjectKind::Shade);
            if !geom.vertices.is_empty() && !geom.indices.is_empty() {
                let base_vertex = self.vertices.len() as u32;
                self.vertices.extend_from_slice(&geom.vertices);
                self.indices
                    .extend(geom.indices.iter().map(|&idx| base_vertex + idx));
            }
            mesh_bounds.merge(&geom.bounds);
            all_edge_loops.extend(geom.edge_loops);
            total_area += geom.area;
            weighted_centroid += DVec3::new(
                f64::from(geom.centroid[0]),
                f64::from(geom.centroid[1]),
                f64::from(geom.centroid[2]),
            ) * geom.area;
        }

        append_deduplicated_edges(&all_edge_loops, object_id, &mut self.edge_vertices);
        self.scene_bounds.merge(&mesh_bounds);

        let centroid = if total_area > 1e-12 {
            let c = weighted_centroid / total_area;
            [c.x as f32, c.y as f32, c.z as f32]
        } else {
            mesh_bounds.center()
        };

        let shade_subtype = if raw.is_detached.unwrap_or(false) {
            "ContextShade"
        } else {
            "OutdoorShade"
        };

        let target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Shade,
            &raw.identifier,
            BTreeMap::new(),
        );
        self.objects.push(ObjectRecord {
            object_id,
            kind: ObjectKind::Shade,
            identifier: raw.identifier,
            display_name: raw.display_name,
            target,
            bounds: mesh_bounds,
            centroid,
            parent_object_id: None,
            face_type: Some(shade_subtype.to_owned()),
            boundary_condition: None,
            story: None,
            zone: None,
            program_type: None,
            construction_set: None,
            hvac: None,
            wwr: None,
            area: Some(total_area),
        });
    }

    fn add_aperture(
        &mut self,
        raw: RawAperture,
        parsed_geom: ParsedFace3D,
        normal_offset: [f32; 3],
        parent_object_id: Option<u32>,
        parent_map: BTreeMap<String, String>,
        room_meta: &RoomMetadata,
    ) -> f64 {
        let object_id = self.alloc_id();
        let mut geom = triangulate_face3d(
            &parsed_geom.boundary,
            &parsed_geom.holes,
            parsed_geom.plane,
            object_id,
            ObjectKind::Aperture,
        );
        offset_geometry(&mut geom, normal_offset);
        self.push_triangulated_geometry(&geom, object_id);

        let bc = raw
            .boundary_condition
            .and_then(RawBoundaryCondition::into_name)
            .or_else(|| Some("Outdoors".to_owned()));

        let mut shade_parent = parent_map.clone();
        shade_parent.insert("aperture_identifier".to_owned(), raw.identifier.clone());

        let target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Aperture,
            &raw.identifier,
            parent_map,
        );
        let area = geom.area;
        self.objects.push(ObjectRecord {
            object_id,
            kind: ObjectKind::Aperture,
            identifier: raw.identifier,
            display_name: raw.display_name,
            target,
            bounds: geom.bounds,
            centroid: geom.centroid,
            parent_object_id,
            face_type: None,
            boundary_condition: bc,
            story: room_meta.story.clone(),
            zone: room_meta.zone.clone(),
            program_type: room_meta.program_type.clone(),
            construction_set: room_meta.construction_set.clone(),
            hvac: room_meta.hvac.clone(),
            wwr: None,
            area: Some(area),
        });

        for shade in raw.indoor_shades {
            self.add_shade(
                shade,
                true,
                Some(object_id),
                shade_parent.clone(),
                room_meta,
            );
        }
        for shade in raw.outdoor_shades.into_iter().chain(raw.shades) {
            self.add_shade(
                shade,
                false,
                Some(object_id),
                shade_parent.clone(),
                room_meta,
            );
        }
        area
    }

    fn add_door(
        &mut self,
        raw: RawDoor,
        parsed_geom: ParsedFace3D,
        normal_offset: [f32; 3],
        parent_object_id: Option<u32>,
        parent_map: BTreeMap<String, String>,
        room_meta: &RoomMetadata,
    ) {
        let object_id = self.alloc_id();
        let mut geom = triangulate_face3d(
            &parsed_geom.boundary,
            &parsed_geom.holes,
            parsed_geom.plane,
            object_id,
            ObjectKind::Door,
        );
        offset_geometry(&mut geom, normal_offset);
        self.push_triangulated_geometry(&geom, object_id);

        let bc = raw
            .boundary_condition
            .and_then(RawBoundaryCondition::into_name)
            .or_else(|| Some("Outdoors".to_owned()));
        let door_type = if raw.is_glass.unwrap_or(false) {
            Some("GlassDoor".to_owned())
        } else {
            Some("Door".to_owned())
        };

        let mut shade_parent = parent_map.clone();
        shade_parent.insert("door_identifier".to_owned(), raw.identifier.clone());

        let target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Door,
            &raw.identifier,
            parent_map,
        );
        self.objects.push(ObjectRecord {
            object_id,
            kind: ObjectKind::Door,
            identifier: raw.identifier,
            display_name: raw.display_name,
            target,
            bounds: geom.bounds,
            centroid: geom.centroid,
            parent_object_id,
            face_type: door_type,
            boundary_condition: bc,
            story: room_meta.story.clone(),
            zone: room_meta.zone.clone(),
            program_type: room_meta.program_type.clone(),
            construction_set: room_meta.construction_set.clone(),
            hvac: room_meta.hvac.clone(),
            wwr: None,
            area: Some(geom.area),
        });

        for shade in raw.indoor_shades {
            self.add_shade(
                shade,
                true,
                Some(object_id),
                shade_parent.clone(),
                room_meta,
            );
        }
        for shade in raw.outdoor_shades.into_iter().chain(raw.shades) {
            self.add_shade(
                shade,
                false,
                Some(object_id),
                shade_parent.clone(),
                room_meta,
            );
        }
    }

    fn add_face(
        &mut self,
        raw: RawFace,
        parent_object_id: Option<u32>,
        room_identifier: Option<&str>,
        room_meta: &RoomMetadata,
    ) -> FaceStats {
        let face_id = self.alloc_id();
        let host_face3d = convert_face3d(raw.geometry, self.unit_scale);

        let mut parsed_apertures: Vec<(RawAperture, ParsedFace3D)> =
            Vec::with_capacity(raw.apertures.len());
        let mut subface_loops: Vec<Vec<DVec3>> =
            Vec::with_capacity(raw.apertures.len() + raw.doors.len());

        for mut ap in raw.apertures {
            let fg = convert_face3d(std::mem::take(&mut ap.geometry), self.unit_scale);
            subface_loops.push(fg.boundary.clone());
            parsed_apertures.push((ap, fg));
        }

        let mut parsed_doors: Vec<(RawDoor, ParsedFace3D)> = Vec::with_capacity(raw.doors.len());
        for mut dr in raw.doors {
            let fg = convert_face3d(std::mem::take(&mut dr.geometry), self.unit_scale);
            subface_loops.push(fg.boundary.clone());
            parsed_doors.push((dr, fg));
        }

        let host_tri = triangulate_host_face(
            &host_face3d.boundary,
            &host_face3d.holes,
            &subface_loops,
            host_face3d.plane,
            face_id,
        );
        self.push_triangulated_geometry(&host_tri.geometry, face_id);

        let face_type = raw
            .face_type
            .filter(|s| !s.trim().is_empty())
            .unwrap_or_else(|| infer_face_type_from_normal(host_tri.geometry.normal).to_owned());

        let boundary_condition = raw
            .boundary_condition
            .and_then(RawBoundaryCondition::into_name)
            .unwrap_or_else(|| {
                if !host_face3d.boundary.is_empty()
                    && host_face3d.boundary.iter().all(|p| p.z <= 0.0)
                {
                    "Ground".to_owned()
                } else {
                    "Outdoors".to_owned()
                }
            });

        let mut face_parent_map = BTreeMap::new();
        if let Some(room_id) = room_identifier {
            face_parent_map.insert("room_identifier".to_owned(), room_id.to_owned());
        }

        let face_record_idx = self.objects.len();
        let face_target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Face,
            &raw.identifier,
            face_parent_map.clone(),
        );
        self.objects.push(ObjectRecord {
            object_id: face_id,
            kind: ObjectKind::Face,
            identifier: raw.identifier.clone(),
            display_name: raw.display_name,
            target: face_target,
            bounds: host_tri.geometry.bounds,
            centroid: host_tri.geometry.centroid,
            parent_object_id,
            face_type: Some(face_type.clone()),
            boundary_condition: Some(boundary_condition.clone()),
            story: room_meta.story.clone(),
            zone: room_meta.zone.clone(),
            program_type: room_meta.program_type.clone(),
            construction_set: room_meta.construction_set.clone(),
            hvac: room_meta.hvac.clone(),
            wwr: None,
            area: Some(host_tri.gross_area),
        });

        let subface_offset = [
            host_tri.geometry.normal[0] * host_tri.subface_offset_m as f32,
            host_tri.geometry.normal[1] * host_tri.subface_offset_m as f32,
            host_tri.geometry.normal[2] * host_tri.subface_offset_m as f32,
        ];

        let mut child_parent_map = face_parent_map;
        child_parent_map.insert("face_identifier".to_owned(), raw.identifier);

        let mut ap_area_sum = 0.0_f64;
        for (ap, fg) in parsed_apertures {
            ap_area_sum += self.add_aperture(
                ap,
                fg,
                subface_offset,
                Some(face_id),
                child_parent_map.clone(),
                room_meta,
            );
        }
        for (dr, fg) in parsed_doors {
            self.add_door(
                dr,
                fg,
                subface_offset,
                Some(face_id),
                child_parent_map.clone(),
                room_meta,
            );
        }
        for shade in raw.indoor_shades {
            self.add_shade(
                shade,
                true,
                Some(face_id),
                child_parent_map.clone(),
                room_meta,
            );
        }
        for shade in raw.outdoor_shades.into_iter().chain(raw.shades) {
            self.add_shade(
                shade,
                false,
                Some(face_id),
                child_parent_map.clone(),
                room_meta,
            );
        }

        let is_wall = face_type.eq_ignore_ascii_case("Wall");
        let is_outdoors = boundary_condition.eq_ignore_ascii_case("Outdoors");
        if host_tri.gross_area > 1e-8 && ((is_wall && is_outdoors) || ap_area_sum > 0.0) {
            self.objects[face_record_idx].wwr =
                Some((ap_area_sum / host_tri.gross_area).clamp(0.0, 1.0) as f32);
        }

        FaceStats {
            bounds: host_tri.geometry.bounds,
            centroid: host_tri.geometry.centroid,
            gross_area: host_tri.gross_area,
            aperture_area: ap_area_sum,
            is_wall,
            is_floor: face_type.eq_ignore_ascii_case("Floor"),
            is_outdoors,
        }
    }

    fn add_room(&mut self, raw: RawRoom) -> Option<(f32, String)> {
        let room_id = self.alloc_id();
        let energy = raw.properties.unwrap_or_default().energy.unwrap_or_default();
        let story = raw
            .story
            .or(energy.story)
            .and_then(|s| (!s.trim().is_empty()).then(|| s.trim().to_owned()));
        let zone = raw
            .zone
            .or(energy.zone)
            .and_then(|s| (!s.trim().is_empty()).then(|| s.trim().to_owned()));

        let room_meta = RoomMetadata {
            story: story.clone(),
            zone,
            program_type: energy.program_type,
            construction_set: energy.construction_set,
            hvac: energy.hvac,
        };

        let room_record_idx = self.objects.len();
        let room_target = build_target(
            self.garden_id.as_deref(),
            &self.model_identifier,
            ObjectKind::Room,
            &raw.identifier,
            BTreeMap::new(),
        );
        self.objects.push(ObjectRecord {
            object_id: room_id,
            kind: ObjectKind::Room,
            identifier: raw.identifier.clone(),
            display_name: raw.display_name,
            target: room_target,
            bounds: Bounds3::empty(),
            centroid: [0.0, 0.0, 0.0],
            parent_object_id: None,
            face_type: None,
            boundary_condition: None,
            story: room_meta.story.clone(),
            zone: room_meta.zone.clone(),
            program_type: room_meta.program_type.clone(),
            construction_set: room_meta.construction_set.clone(),
            hvac: room_meta.hvac.clone(),
            wwr: None,
            area: None,
        });

        let mut room_bounds = Bounds3::empty();
        let mut face_area_sum = 0.0_f64;
        let mut weighted_centroid = DVec3::ZERO;
        let mut floor_area = 0.0_f64;
        let mut ext_wall_area = 0.0_f64;
        let mut ext_wall_ap_area = 0.0_f64;
        let mut all_wall_area = 0.0_f64;
        let mut all_wall_ap_area = 0.0_f64;

        for face in raw.faces {
            let stats = self.add_face(face, Some(room_id), Some(&raw.identifier), &room_meta);
            room_bounds.merge(&stats.bounds);
            face_area_sum += stats.gross_area;
            weighted_centroid += DVec3::new(
                f64::from(stats.centroid[0]),
                f64::from(stats.centroid[1]),
                f64::from(stats.centroid[2]),
            ) * stats.gross_area;
            if stats.is_floor {
                floor_area += stats.gross_area;
            }
            if stats.is_wall {
                all_wall_area += stats.gross_area;
                all_wall_ap_area += stats.aperture_area;
                if stats.is_outdoors {
                    ext_wall_area += stats.gross_area;
                    ext_wall_ap_area += stats.aperture_area;
                }
            }
        }

        let mut room_shade_parent = BTreeMap::new();
        room_shade_parent.insert("room_identifier".to_owned(), raw.identifier);

        for shade in raw.indoor_shades {
            let shade_start = self.objects.len();
            self.add_shade(
                shade,
                true,
                Some(room_id),
                room_shade_parent.clone(),
                &room_meta,
            );
            if !room_bounds.is_valid() {
                if let Some(rec) = self.objects.get(shade_start) {
                    room_bounds.merge(&rec.bounds);
                }
            }
        }
        for shade in raw.outdoor_shades.into_iter().chain(raw.shades) {
            let shade_start = self.objects.len();
            self.add_shade(
                shade,
                false,
                Some(room_id),
                room_shade_parent.clone(),
                &room_meta,
            );
            if !room_bounds.is_valid() {
                if let Some(rec) = self.objects.get(shade_start) {
                    room_bounds.merge(&rec.bounds);
                }
            }
        }

        let centroid = if face_area_sum > 1e-12 {
            let c = weighted_centroid / face_area_sum;
            [c.x as f32, c.y as f32, c.z as f32]
        } else {
            room_bounds.center()
        };

        let room_wwr = if ext_wall_area > 1e-8 {
            Some((ext_wall_ap_area / ext_wall_area).clamp(0.0, 1.0) as f32)
        } else if all_wall_area > 1e-8 && all_wall_ap_area > 0.0 {
            Some((all_wall_ap_area / all_wall_area).clamp(0.0, 1.0) as f32)
        } else {
            None
        };

        let room_rec = &mut self.objects[room_record_idx];
        room_rec.bounds = room_bounds;
        room_rec.centroid = centroid;
        room_rec.area = Some(floor_area);
        room_rec.wwr = room_wwr;

        story.map(|s| {
            let min_z = if room_bounds.is_valid() {
                room_bounds.min[2]
            } else {
                0.0
            };
            (min_z, s)
        })
    }
}

struct FaceStats {
    bounds: Bounds3,
    centroid: [f32; 3],
    gross_area: f64,
    aperture_area: f64,
    is_wall: bool,
    is_floor: bool,
    is_outdoors: bool,
}

/// Load and triangulate a Honeybee `.hbjson` model file from disk.
pub fn load_hbjson_file(path: &Path, garden_id: Option<&str>) -> Result<SceneData, SceneError> {
    let contents = fs::read_to_string(path)?;
    load_hbjson_str(&contents, garden_id, Some(path.to_string_lossy().into_owned()))
}

/// Parse and triangulate a Honeybee `.hbjson` model from an in-memory JSON string.
pub fn load_hbjson_str(
    json_str: &str,
    garden_id: Option<&str>,
    source_path: Option<String>,
) -> Result<SceneData, SceneError> {
    let raw: RawModel = serde_json::from_str(json_str)?;
    if let Some(model_type) = raw.model_type.as_deref() {
        if model_type != "Model" {
            return Err(SceneError::InvalidModel(format!(
                "Expected type 'Model', got '{model_type}'"
            )));
        }
    }
    let model_identifier = raw
        .identifier
        .map(|s| s.trim().to_owned())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| SceneError::InvalidModel("Model is missing a non-empty identifier".into()))?;

    let unit_scale = unit_scale_to_meters(raw.units.as_deref())?;
    let mut builder = SceneBuilder::new(garden_id, model_identifier.clone(), unit_scale);
    let mut story_elevations: BTreeMap<String, f32> = BTreeMap::new();

    for room in raw.rooms {
        if let Some((min_z, story_name)) = builder.add_room(room) {
            story_elevations
                .entry(story_name)
                .and_modify(|prev| {
                    if min_z < *prev {
                        *prev = min_z;
                    }
                })
                .or_insert(min_z);
        }
    }

    let empty_meta = RoomMetadata::default();
    for face in raw.orphaned_faces {
        builder.add_face(face, None, None, &empty_meta);
    }
    for mut ap in raw.orphaned_apertures {
        let fg = convert_face3d(std::mem::take(&mut ap.geometry), builder.unit_scale);
        builder.add_aperture(ap, fg, [0.0, 0.0, 0.0], None, BTreeMap::new(), &empty_meta);
    }
    for mut dr in raw.orphaned_doors {
        let fg = convert_face3d(std::mem::take(&mut dr.geometry), builder.unit_scale);
        builder.add_door(dr, fg, [0.0, 0.0, 0.0], None, BTreeMap::new(), &empty_meta);
    }
    for shade in raw.orphaned_shades {
        builder.add_shade(shade, false, None, BTreeMap::new(), &empty_meta);
    }
    for shade_mesh in raw.shade_meshes {
        builder.add_shade_mesh(shade_mesh);
    }

    let mut story_pairs: Vec<(f32, String)> = story_elevations
        .into_iter()
        .map(|(name, min_z)| (min_z, name))
        .collect();
    story_pairs.sort_by(|a, b| a.0.total_cmp(&b.0).then_with(|| a.1.cmp(&b.1)));
    let stories: Vec<String> = story_pairs.into_iter().map(|(_, name)| name).collect();

    Ok(SceneData {
        model_identifier,
        display_name: raw.display_name,
        units: raw.units,
        source_path,
        bounds: builder.scene_bounds,
        vertices: builder.vertices,
        indices: builder.indices,
        edge_vertices: builder.edge_vertices,
        objects: builder.objects,
        stories,
    })
}
