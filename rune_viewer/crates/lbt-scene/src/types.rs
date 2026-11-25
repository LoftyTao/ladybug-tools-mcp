//! Shared 3D scene representation and Garden Web View protocol types.

use std::collections::BTreeMap;
use std::fmt;

use bytemuck::{Pod, Zeroable};
use serde::de::{self, Deserializer};
use serde::{Deserialize, Serialize};

/// Current schema version for Garden `tmp/web_view/` protocol JSON files.
pub const PROTOCOL_SCHEMA_VERSION: &str = "1";

fn default_schema_version() -> String {
    PROTOCOL_SCHEMA_VERSION.to_owned()
}

fn default_target_type() -> String {
    "honeybee_object".to_owned()
}

fn default_domain() -> String {
    "honeybee".to_owned()
}

fn default_capture_width() -> u32 {
    1280
}

fn default_capture_height() -> u32 {
    720
}

fn deserialize_null_default<'de, D, T>(deserializer: D) -> Result<T, D::Error>
where
    T: Default + Deserialize<'de>,
    D: Deserializer<'de>,
{
    Ok(Option::<T>::deserialize(deserializer)?.unwrap_or_default())
}

fn deserialize_string_or_vec<'de, D>(deserializer: D) -> Result<Vec<String>, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum OneOrMany {
        One(String),
        Many(Vec<String>),
    }

    match Option::<OneOrMany>::deserialize(deserializer)? {
        None => Ok(Vec::new()),
        Some(OneOrMany::One(value)) => Ok(vec![value]),
        Some(OneOrMany::Many(values)) => Ok(values),
    }
}

/// GPU-ready triangle mesh vertex for Honeybee building surfaces.
#[repr(C)]
#[derive(Copy, Clone, Debug, PartialEq, Pod, Zeroable, Serialize, Deserialize)]
pub struct MeshVertex {
    /// World-space XYZ position in meters (Z-up Honeybee coordinates).
    pub position: [f32; 3],
    /// Outward surface normal vector.
    pub normal: [f32; 3],
    /// Picking and attribute lookup ID matching [`ObjectRecord::object_id`] (0 = background).
    pub object_id: u32,
    /// Encoded [`ObjectKind`] discriminant (`ObjectKind::kind_code`).
    pub kind_code: u32,
}

/// GPU-ready wireframe/crease edge vertex.
#[repr(C)]
#[derive(Copy, Clone, Debug, PartialEq, Pod, Zeroable, Serialize, Deserialize)]
pub struct EdgeVertex {
    /// World-space XYZ position in meters.
    pub position: [f32; 3],
    /// Owning [`ObjectRecord::object_id`] for selection/isolation filtering.
    pub object_id: u32,
}

/// Axis-aligned 3D bounding box in world coordinates.
#[derive(Copy, Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct Bounds3 {
    pub min: [f32; 3],
    pub max: [f32; 3],
}

impl Bounds3 {
    /// Construct bounds directly from min and max corners.
    pub const fn new(min: [f32; 3], max: [f32; 3]) -> Self {
        Self { min, max }
    }

    /// Return inverted sentinel bounds suitable for point accumulation.
    pub const fn empty() -> Self {
        Self {
            min: [f32::INFINITY; 3],
            max: [f32::NEG_INFINITY; 3],
        }
    }

    /// Return whether every axis has finite `min <= max`.
    pub fn is_valid(&self) -> bool {
        (0..3).all(|i| self.min[i].is_finite() && self.max[i].is_finite() && self.min[i] <= self.max[i])
    }

    /// Expand bounds to include a single 3D point.
    pub fn expand_point(&mut self, point: [f32; 3]) {
        for i in 0..3 {
            if point[i] < self.min[i] {
                self.min[i] = point[i];
            }
            if point[i] > self.max[i] {
                self.max[i] = point[i];
            }
        }
    }

    /// Expand bounds to include another [`Bounds3`].
    pub fn merge(&mut self, other: &Self) {
        if other.is_valid() {
            self.expand_point(other.min);
            self.expand_point(other.max);
        }
    }

    /// Return the geometric center of the bounds (or origin if invalid).
    pub fn center(&self) -> [f32; 3] {
        if !self.is_valid() {
            return [0.0, 0.0, 0.0];
        }
        [
            0.5 * (self.min[0] + self.max[0]),
            0.5 * (self.min[1] + self.max[1]),
            0.5 * (self.min[2] + self.max[2]),
        ]
    }

    /// Return the per-axis extent `(max - min)` (or zeroes if invalid).
    pub fn size(&self) -> [f32; 3] {
        if !self.is_valid() {
            return [0.0, 0.0, 0.0];
        }
        [
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        ]
    }

    /// Return the Euclidean diagonal length of the bounding box.
    pub fn diagonal(&self) -> f32 {
        let [dx, dy, dz] = self.size();
        (dx * dx + dy * dy + dz * dz).sqrt()
    }
}

/// Honeybee object kind supported by the 3D viewer.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ObjectKind {
    #[serde(alias = "Room")]
    Room,
    #[serde(alias = "Face")]
    Face,
    #[serde(alias = "Aperture")]
    Aperture,
    #[serde(alias = "Door")]
    Door,
    #[serde(alias = "Shade")]
    Shade,
}

impl ObjectKind {
    /// Numeric GPU code matching [`MeshVertex::kind_code`].
    pub const fn kind_code(self) -> u32 {
        match self {
            Self::Room => 0,
            Self::Face => 1,
            Self::Aperture => 2,
            Self::Door => 3,
            Self::Shade => 4,
        }
    }

    /// Decode a numeric GPU [`MeshVertex::kind_code`] back into [`ObjectKind`].
    pub const fn from_kind_code(code: u32) -> Option<Self> {
        match code {
            0 => Some(Self::Room),
            1 => Some(Self::Face),
            2 => Some(Self::Aperture),
            3 => Some(Self::Door),
            4 => Some(Self::Shade),
            _ => None,
        }
    }

    /// Canonical snake_case protocol name.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Room => "room",
            Self::Face => "face",
            Self::Aperture => "aperture",
            Self::Door => "door",
            Self::Shade => "shade",
        }
    }
}

impl fmt::Display for ObjectKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed Garden `BuildingObjectTargetRef` / `HoneybeeObjectTarget` reference.
///
/// Serializes identically to `garden.honeybee_core.targets.make_honeybee_object_target`
/// so targets returned in `interaction_state.json` can be passed straight into MCP tools.
#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ObjectTargetRef {
    #[serde(default = "default_target_type")]
    pub target_type: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    #[serde(default = "default_domain")]
    pub domain: String,
    #[serde(default)]
    pub model_identifier: String,
    pub object_type: ObjectKind,
    pub object_identifier: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub identifier: Option<String>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub parent: BTreeMap<String, String>,
}

impl ObjectTargetRef {
    /// Construct a formal `honeybee_object` target ref.
    pub fn new(
        garden_id: Option<String>,
        model_identifier: impl Into<String>,
        object_type: ObjectKind,
        object_identifier: impl Into<String>,
    ) -> Self {
        let object_identifier = object_identifier.into();
        Self {
            target_type: default_target_type(),
            garden_id,
            domain: default_domain(),
            model_identifier: model_identifier.into(),
            object_type,
            identifier: Some(object_identifier.clone()),
            object_identifier,
            parent: BTreeMap::new(),
        }
    }
}

/// Per-object scene metadata record used for picking, attribute coloring, and inspector display.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ObjectRecord {
    pub object_id: u32,
    pub kind: ObjectKind,
    pub identifier: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    pub target: ObjectTargetRef,
    pub bounds: Bounds3,
    pub centroid: [f32; 3],
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_object_id: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub face_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub boundary_condition: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub story: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub zone: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub program_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub construction_set: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hvac: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub wwr: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub area: Option<f64>,
}

/// Attribute coloring modes supported by the viewer and Garden `present.json`.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ColorBy {
    #[default]
    Type,
    BoundaryCondition,
    Story,
    Zone,
    ProgramType,
    ConstructionSet,
    Hvac,
    Wwr,
}

impl ColorBy {
    /// All supported `ColorBy` variants in UI order.
    pub const ALL: [Self; 8] = [
        Self::Type,
        Self::BoundaryCondition,
        Self::Story,
        Self::Zone,
        Self::ProgramType,
        Self::ConstructionSet,
        Self::Hvac,
        Self::Wwr,
    ];

    /// Canonical snake_case protocol value.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Type => "type",
            Self::BoundaryCondition => "boundary_condition",
            Self::Story => "story",
            Self::Zone => "zone",
            Self::ProgramType => "program_type",
            Self::ConstructionSet => "construction_set",
            Self::Hvac => "hvac",
            Self::Wwr => "wwr",
        }
    }
}

impl fmt::Display for ColorBy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Tessellated 3D building scene ready for GPU upload and interactive inspection.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct SceneData {
    pub model_identifier: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_path: Option<String>,
    pub bounds: Bounds3,
    pub vertices: Vec<MeshVertex>,
    pub indices: Vec<u32>,
    pub edge_vertices: Vec<EdgeVertex>,
    pub objects: Vec<ObjectRecord>,
    #[serde(default)]
    pub stories: Vec<String>,
}

impl SceneData {
    /// Look up an object record by its numeric picking ID.
    pub fn object_by_id(&self, object_id: u32) -> Option<&ObjectRecord> {
        if object_id == 0 {
            return None;
        }
        self.objects.iter().find(|record| record.object_id == object_id)
    }

    /// Look up an object record matching a typed target reference.
    pub fn find_by_target(&self, target: &ObjectTargetRef) -> Option<&ObjectRecord> {
        self.objects.iter().find(|record| {
            record.kind == target.object_type && record.identifier == target.object_identifier
        })
    }

    /// Return true when the scene contains no mesh or edge geometry.
    pub fn is_empty(&self) -> bool {
        self.vertices.is_empty() && self.edge_vertices.is_empty()
    }
}

/// How non-highlighted objects are displayed when `highlight_targets` is non-empty.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IsolationMode {
    #[default]
    Highlight,
    GhostContext,
    Isolate,
}

impl IsolationMode {
    /// Canonical snake_case protocol value.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Highlight => "highlight",
            Self::GhostContext => "ghost_context",
            Self::Isolate => "isolate",
        }
    }
}

/// Structured Honeybee validation issue displayed in validation overlays and callouts.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct ValidationIssue {
    #[serde(default, rename = "type", skip_serializing_if = "Option::is_none")]
    pub issue_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub code: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub extension_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub element_type: Option<String>,
    #[serde(default, deserialize_with = "deserialize_string_or_vec")]
    pub element_id: Vec<String>,
    #[serde(default, deserialize_with = "deserialize_string_or_vec")]
    pub element_name: Vec<String>,
    #[serde(default)]
    pub message: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub severity: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<ObjectTargetRef>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub targets: Vec<ObjectTargetRef>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub location: Option<[f32; 3]>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, serde_json::Value>,
}

/// Named camera preset directives supported by `present.json` and `capture_request.json`.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CameraPreset {
    #[default]
    Keep,
    Fit,
    FitHighlights,
    Axon,
    Top,
    North,
    South,
    East,
    West,
}

impl CameraPreset {
    /// Canonical snake_case protocol value.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Keep => "keep",
            Self::Fit => "fit",
            Self::FitHighlights => "fit_highlights",
            Self::Axon => "axon",
            Self::Top => "top",
            Self::North => "north",
            Self::South => "south",
            Self::East => "east",
            Self::West => "west",
        }
    }
}

/// Explicit 3D camera pose in Z-up world coordinates.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CameraPose {
    pub position: [f32; 3],
    pub target: [f32; 3],
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub up: Option<[f32; 3]>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub orthographic: Option<bool>,
}

/// Camera specification accepting either a preset string or an explicit pose object.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum CameraSpec {
    Preset(CameraPreset),
    Pose(CameraPose),
}

impl Default for CameraSpec {
    fn default() -> Self {
        Self::Preset(CameraPreset::Keep)
    }
}

impl CameraSpec {
    pub const fn keep() -> Self {
        Self::Preset(CameraPreset::Keep)
    }

    pub const fn fit() -> Self {
        Self::Preset(CameraPreset::Fit)
    }

    pub const fn fit_highlights() -> Self {
        Self::Preset(CameraPreset::FitHighlights)
    }

    pub const fn axon() -> Self {
        Self::Preset(CameraPreset::Axon)
    }

    pub const fn pose(position: [f32; 3], target: [f32; 3]) -> Self {
        Self::Pose(CameraPose {
            position,
            target,
            up: None,
            orthographic: None,
        })
    }
}

/// Clipping plane axis for [`SectionSpec`].
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SectionAxis {
    #[serde(alias = "X")]
    X,
    #[serde(alias = "Y")]
    Y,
    #[default]
    #[serde(alias = "Z")]
    Z,
}

/// Interactive section-cut configuration.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct SectionSpec {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub axis: SectionAxis,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub value: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub story: Option<String>,
    #[serde(default)]
    pub invert: bool,
}

/// 3D viewport callout label attached to an object target or world coordinate.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct Callout {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<ObjectTargetRef>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub world_point: Option<[f32; 3]>,
    #[serde(default, alias = "text")]
    pub label: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub severity: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<String>,
}

/// Active view mode directed by `<garden>/tmp/web_view/present.json`.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ViewType {
    #[default]
    Model,
    Highlight,
    Validation,
    Analysis,
    Document,
    Diff,
    Split,
}

/// Typed reference to the active Honeybee/Dragonfly/Fairyfly model in `present.json`.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct ModelTargetRef {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_identifier: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, serde_json::Value>,
}

/// Agent -> Viewer directive payload persisted at `<garden>/tmp/web_view/present.json`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PresentCommand {
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    #[serde(default)]
    pub revision: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_root: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub view_type: ViewType,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_target: Option<ModelTargetRef>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub color_by: ColorBy,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub highlight_targets: Vec<ObjectTargetRef>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub isolation_mode: IsolationMode,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub validation_issues: Vec<ValidationIssue>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub camera: CameraSpec,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub section: Option<SectionSpec>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub callouts: Vec<Callout>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<String>,
}

impl Default for PresentCommand {
    fn default() -> Self {
        Self {
            schema_version: default_schema_version(),
            revision: 0,
            garden_root: None,
            garden_id: None,
            view_type: ViewType::default(),
            model_path: None,
            model_target: None,
            color_by: ColorBy::default(),
            highlight_targets: Vec::new(),
            isolation_mode: IsolationMode::default(),
            validation_issues: Vec::new(),
            camera: CameraSpec::default(),
            section: None,
            callouts: Vec::new(),
            title: None,
            note: None,
            updated_at: None,
        }
    }
}

/// Resolution lifecycle status of a user-placed spatial pin.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PinStatus {
    #[default]
    Open,
    Resolved,
}

/// User-authored 3D annotation pin stored in `interaction_state.json`.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct SpatialPin {
    pub id: String,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub status: PinStatus,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<ObjectTargetRef>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub world_point: Option<[f32; 3]>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub comment: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resolution_note: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub camera_bookmark: Option<CameraSpec>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<String>,
}

/// Snapshot of the viewer's current viewport state reported in `interaction_state.json`.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct ViewportSnapshot {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color_by: Option<ColorBy>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub camera: Option<CameraSpec>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub section: Option<SectionSpec>,
}

/// Queued user UI action intent surfaced to the agent via `GD_Web_View_Get_Context`.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct PendingIntent {
    pub id: String,
    pub kind: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub targets: Vec<ObjectTargetRef>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
}

/// Viewer -> Agent spatial context persisted at `<garden>/tmp/web_view/interaction_state.json`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InteractionState {
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub selected_targets: Vec<ObjectTargetRef>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub annotations: Vec<SpatialPin>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub viewport: Option<ViewportSnapshot>,
    #[serde(default, deserialize_with = "deserialize_null_default")]
    pub pending_intents: Vec<PendingIntent>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub viewer_pid: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<String>,
}

impl Default for InteractionState {
    fn default() -> Self {
        Self {
            schema_version: default_schema_version(),
            garden_id: None,
            selected_targets: Vec::new(),
            annotations: Vec::new(),
            viewport: None,
            pending_intents: Vec::new(),
            viewer_pid: None,
            updated_at: None,
        }
    }
}

/// Offscreen/live capture request written to `<garden>/tmp/web_view/capture_request.json`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CaptureRequest {
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    pub request_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_root: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub view: Option<CameraSpec>,
    #[serde(default = "default_capture_width")]
    pub width: u32,
    #[serde(default = "default_capture_height")]
    pub height: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub output_png_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub receipt_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub requested_at: Option<String>,
}

impl Default for CaptureRequest {
    fn default() -> Self {
        Self {
            schema_version: default_schema_version(),
            request_id: String::new(),
            garden_root: None,
            garden_id: None,
            view: None,
            width: default_capture_width(),
            height: default_capture_height(),
            output_png_path: None,
            receipt_path: None,
            requested_at: None,
        }
    }
}

/// Capture completion receipt written to `<garden>/tmp/web_view/captures/<request_id>.json`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CaptureReceipt {
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    pub request_id: String,
    pub status: String,
    pub image_path: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub absolute_path: Option<String>,
    pub width: u32,
    pub height: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub revision: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub captured_at: Option<String>,
}

impl Default for CaptureReceipt {
    fn default() -> Self {
        Self {
            schema_version: default_schema_version(),
            request_id: String::new(),
            status: String::new(),
            image_path: String::new(),
            absolute_path: None,
            width: 0,
            height: 0,
            model_path: None,
            revision: None,
            error: None,
            captured_at: None,
        }
    }
}

// Keep unused-import lints silent if helper traits are referenced only via serde macros.
#[allow(dead_code)]
fn _ensure_de_error<E: de::Error>() {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::mem::{align_of, size_of};

    #[test]
    fn vertex_layouts_are_tightly_packed() {
        assert_eq!(size_of::<MeshVertex>(), 32);
        assert_eq!(align_of::<MeshVertex>(), 4);
        assert_eq!(size_of::<EdgeVertex>(), 16);
        assert_eq!(align_of::<EdgeVertex>(), 4);
    }

    #[test]
    fn bounds3_accumulates_and_computes_center_and_diagonal() {
        let mut bounds = Bounds3::empty();
        assert!(!bounds.is_valid());
        bounds.expand_point([-2.0, 0.0, 1.0]);
        bounds.expand_point([4.0, 6.0, 5.0]);
        assert!(bounds.is_valid());
        assert_eq!(bounds.center(), [1.0, 3.0, 3.0]);
        assert_eq!(bounds.size(), [6.0, 6.0, 4.0]);
        assert!((bounds.diagonal() - (88.0_f32).sqrt()).abs() < 1e-5);
    }

    #[test]
    fn camera_spec_roundtrips_preset_and_pose() {
        let preset: CameraSpec = serde_json::from_str("\"fit_highlights\"").unwrap();
        assert_eq!(preset, CameraSpec::Preset(CameraPreset::FitHighlights));
        assert_eq!(serde_json::to_string(&preset).unwrap(), "\"fit_highlights\"");

        let pose_json = r#"{"position":[10.0,-10.0,8.0],"target":[0.0,0.0,2.0],"orthographic":true}"#;
        let pose: CameraSpec = serde_json::from_str(pose_json).unwrap();
        assert_eq!(
            pose,
            CameraSpec::Pose(CameraPose {
                position: [10.0, -10.0, 8.0],
                target: [0.0, 0.0, 2.0],
                up: None,
                orthographic: Some(true),
            })
        );
    }

    #[test]
    fn present_and_interaction_roundtrip_snake_case() {
        let target = ObjectTargetRef::new(Some("g1".into()), "Model1", ObjectKind::Face, "Face_South");
        let cmd = PresentCommand {
            revision: 3,
            garden_id: Some("g1".into()),
            view_type: ViewType::Highlight,
            color_by: ColorBy::BoundaryCondition,
            highlight_targets: vec![target.clone()],
            isolation_mode: IsolationMode::GhostContext,
            camera: CameraSpec::fit_highlights(),
            section: Some(SectionSpec {
                enabled: true,
                axis: SectionAxis::Z,
                value: Some(3.2),
                story: Some("Level_1".into()),
                invert: false,
            }),
            ..Default::default()
        };

        let encoded = serde_json::to_value(&cmd).unwrap();
        assert_eq!(encoded["schema_version"], "1");
        assert_eq!(encoded["view_type"], "highlight");
        assert_eq!(encoded["color_by"], "boundary_condition");
        assert_eq!(encoded["isolation_mode"], "ghost_context");
        assert_eq!(encoded["camera"], "fit_highlights");
        assert_eq!(encoded["highlight_targets"][0]["target_type"], "honeybee_object");
        assert_eq!(encoded["highlight_targets"][0]["object_type"], "face");

        let decoded: PresentCommand = serde_json::from_value(encoded).unwrap();
        assert_eq!(decoded, cmd);

        let state = InteractionState {
            garden_id: Some("g1".into()),
            selected_targets: vec![target.clone()],
            annotations: vec![SpatialPin {
                id: "ann_1".into(),
                status: PinStatus::Open,
                target: Some(target),
                world_point: Some([1.0, 2.0, 3.0]),
                comment: "Add overhang".into(),
                ..Default::default()
            }],
            viewport: Some(ViewportSnapshot {
                model_path: Some("models/base.hbjson".into()),
                color_by: Some(ColorBy::Type),
                camera: Some(CameraSpec::axon()),
                section: None,
            }),
            pending_intents: vec![PendingIntent {
                id: "int_1".into(),
                kind: "create_shades".into(),
                ..Default::default()
            }],
            viewer_pid: Some(4242),
            updated_at: Some("2026-11-25T12:00:00Z".into()),
            ..Default::default()
        };
        let state_json = serde_json::to_value(&state).unwrap();
        assert_eq!(state_json["schema_version"], "1");
        assert_eq!(state_json["annotations"][0]["status"], "open");
        let decoded_state: InteractionState = serde_json::from_value(state_json).unwrap();
        assert_eq!(decoded_state, state);
    }

    #[test]
    fn protocol_handles_nulls_and_validation_and_capture_structs() {
        let null_present = r#"{
            "revision": 1,
            "view_type": null,
            "color_by": null,
            "highlight_targets": null,
            "isolation_mode": null,
            "validation_issues": [
                {
                    "type": "ValidationError",
                    "code": "000101",
                    "error_type": "Non-Planar Geometry",
                    "element_type": "Face",
                    "element_id": "Face_1",
                    "message": "Face is not planar."
                }
            ],
            "camera": null,
            "callouts": null
        }"#;
        let present: PresentCommand = serde_json::from_str(null_present).unwrap();
        assert_eq!(present.schema_version, "1");
        assert_eq!(present.view_type, ViewType::Model);
        assert_eq!(present.color_by, ColorBy::Type);
        assert_eq!(present.camera, CameraSpec::Preset(CameraPreset::Keep));
        assert_eq!(present.validation_issues[0].element_id, vec!["Face_1"]);

        let cap_req = CaptureRequest {
            request_id: "cap_abc123".into(),
            garden_root: Some("/garden".into()),
            garden_id: Some("g1".into()),
            view: Some(CameraSpec::axon()),
            output_png_path: Some("tmp/web_view/captures/cap_abc123.png".into()),
            receipt_path: Some("tmp/web_view/captures/cap_abc123.json".into()),
            ..Default::default()
        };
        let req_val = serde_json::to_value(&cap_req).unwrap();
        assert_eq!(req_val["schema_version"], "1");
        assert_eq!(req_val["width"], 1280);
        assert_eq!(req_val["height"], 720);
        let decoded_req: CaptureRequest = serde_json::from_value(req_val).unwrap();
        assert_eq!(decoded_req, cap_req);

        let receipt = CaptureReceipt {
            request_id: "cap_abc123".into(),
            status: "ok".into(),
            image_path: "tmp/web_view/captures/cap_abc123.png".into(),
            width: 1280,
            height: 720,
            ..Default::default()
        };
        let receipt_val = serde_json::to_value(&receipt).unwrap();
        assert_eq!(receipt_val["schema_version"], "1");
        let decoded_receipt: CaptureReceipt = serde_json::from_value(receipt_val).unwrap();
        assert_eq!(decoded_receipt, receipt);
    }
}
