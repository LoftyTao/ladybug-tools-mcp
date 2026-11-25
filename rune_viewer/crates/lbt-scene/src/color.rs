//! Official `honeybee-display` RGBA color mapping and Ladybug Tools legend construction.
//!
//! References:
//! - `honeybee_display/model.py` (`TYPE_COLORS`, `BC_COLORS`, type & BC classification rules)
//! - `honeybee/face.py`, `aperture.py`, `door.py`, `shade.py`, `shademesh.py`
//! - `ladybug/color.py` (`Colorset.original`, `Colorset.nuanced`, `ColorRange`)
//! - `ladybug/legend.py` (`Legend`, `LegendParameters`)

use std::collections::{BTreeMap, BTreeSet, HashMap};

use crate::types::{ColorBy, LegendData, LegendEntry, ObjectKind, ObjectRecord, SceneData};

#[inline]
const fn rgba(r: u8, g: u8, b: u8, a: u8) -> [f32; 4] {
    [
        r as f32 / 255.0,
        g as f32 / 255.0,
        b as f32 / 255.0,
        a as f32 / 255.0,
    ]
}

#[inline]
const fn rgb(r: u8, g: u8, b: u8) -> [f32; 4] {
    rgba(r, g, b, 255)
}

/// Official `honeybee-display` translucency alpha (`100 / 255`) for Aperture, Glass Door, and Air Boundary.
pub const TRANSLUCENT_ALPHA: f32 = 100.0 / 255.0;

/// Official `honeybee-display` `TYPE_COLORS` (`honeybee_display/model.py`).
pub const TYPE_COLOR_WALL: [f32; 4] = rgb(230, 180, 60);
pub const TYPE_COLOR_ROOF: [f32; 4] = rgb(128, 20, 20);
pub const TYPE_COLOR_FLOOR: [f32; 4] = rgb(128, 128, 128);
pub const TYPE_COLOR_AIR_BOUNDARY: [f32; 4] = rgba(255, 255, 200, 100);
pub const TYPE_COLOR_INTERIOR_WALL: [f32; 4] = rgb(230, 215, 150);
pub const TYPE_COLOR_CEILING: [f32; 4] = rgb(255, 128, 128);
pub const TYPE_COLOR_INTERIOR_FLOOR: [f32; 4] = rgb(255, 128, 128);
pub const TYPE_COLOR_APERTURE: [f32; 4] = rgba(64, 180, 255, 100);
pub const TYPE_COLOR_DOOR: [f32; 4] = rgb(160, 150, 100);
pub const TYPE_COLOR_GLASS_DOOR: [f32; 4] = rgba(128, 204, 255, 100);
pub const TYPE_COLOR_OUTDOOR_SHADE: [f32; 4] = rgb(120, 75, 190);
pub const TYPE_COLOR_CONTEXT_SHADE: [f32; 4] = rgb(80, 50, 128);
pub const TYPE_COLOR_INDOOR_SHADE: [f32; 4] = rgb(159, 99, 255);

/// Official `honeybee-display` `BC_COLORS` (`honeybee_display/model.py`).
pub const BC_COLOR_OUTDOORS: [f32; 4] = rgb(64, 180, 255);
pub const BC_COLOR_SURFACE: [f32; 4] = rgb(0, 128, 0);
pub const BC_COLOR_GROUND: [f32; 4] = rgb(165, 82, 0);
pub const BC_COLOR_ADIABATIC: [f32; 4] = rgb(255, 128, 128);
pub const BC_COLOR_OTHER: [f32; 4] = rgb(255, 255, 200);

/// Neutral fallback for unassigned categorical attributes.
pub const UNASSIGNED_COLOR: [f32; 4] = [0.64, 0.66, 0.70, 1.0];
const ROOM_NEUTRAL_COLOR: [f32; 4] = [0.78, 0.76, 0.72, 1.0];

/// Official Ladybug `Colorset.original()` (`ladybug/color.py`, index 0, 10 stops).
pub const LADYBUG_ORIGINAL: [[u8; 3]; 10] = [
    [75, 107, 169],
    [115, 147, 202],
    [170, 200, 247],
    [193, 213, 208],
    [245, 239, 103],
    [252, 230, 74],
    [239, 156, 21],
    [234, 123, 0],
    [234, 74, 0],
    [234, 38, 0],
];

/// Official Ladybug `Colorset.nuanced()` (`ladybug/color.py`, index 1, 11 stops).
pub const LADYBUG_NUANCED: [[u8; 3]; 11] = [
    [49, 54, 149],
    [69, 117, 180],
    [116, 173, 209],
    [171, 217, 233],
    [224, 243, 248],
    [255, 255, 191],
    [254, 224, 144],
    [253, 174, 97],
    [244, 109, 67],
    [215, 48, 39],
    [165, 0, 38],
];

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash)]
enum DisplayTypeCategory {
    Wall,
    Roof,
    Floor,
    AirBoundary,
    InteriorWall,
    Ceiling,
    InteriorFloor,
    Aperture,
    Door,
    GlassDoor,
    OutdoorShade,
    ContextShade,
    IndoorShade,
}

impl DisplayTypeCategory {
    /// Canonical `honeybee_display/model.py` `TYPE_COLORS` ordering.
    const ALL: [Self; 13] = [
        Self::Wall,
        Self::Roof,
        Self::Floor,
        Self::AirBoundary,
        Self::InteriorWall,
        Self::Ceiling,
        Self::InteriorFloor,
        Self::Aperture,
        Self::Door,
        Self::GlassDoor,
        Self::OutdoorShade,
        Self::ContextShade,
        Self::IndoorShade,
    ];

    const fn key(self) -> &'static str {
        match self {
            Self::Wall => "wall",
            Self::Roof => "roof",
            Self::Floor => "floor",
            Self::AirBoundary => "air_boundary",
            Self::InteriorWall => "interior_wall",
            Self::Ceiling => "ceiling",
            Self::InteriorFloor => "interior_floor",
            Self::Aperture => "aperture",
            Self::Door => "door",
            Self::GlassDoor => "glass_door",
            Self::OutdoorShade => "outdoor_shade",
            Self::ContextShade => "context_shade",
            Self::IndoorShade => "indoor_shade",
        }
    }

    const fn label(self) -> &'static str {
        match self {
            Self::Wall => "Wall",
            Self::Roof => "Roof",
            Self::Floor => "Floor",
            Self::AirBoundary => "Air Boundary",
            Self::InteriorWall => "Interior Wall",
            Self::Ceiling => "Ceiling",
            Self::InteriorFloor => "Interior Floor",
            Self::Aperture => "Aperture",
            Self::Door => "Door",
            Self::GlassDoor => "Glass Door",
            Self::OutdoorShade => "Outdoor Shade",
            Self::ContextShade => "Context Shade",
            Self::IndoorShade => "Indoor Shade",
        }
    }

    const fn color(self) -> [f32; 4] {
        match self {
            Self::Wall => TYPE_COLOR_WALL,
            Self::Roof => TYPE_COLOR_ROOF,
            Self::Floor => TYPE_COLOR_FLOOR,
            Self::AirBoundary => TYPE_COLOR_AIR_BOUNDARY,
            Self::InteriorWall => TYPE_COLOR_INTERIOR_WALL,
            Self::Ceiling => TYPE_COLOR_CEILING,
            Self::InteriorFloor => TYPE_COLOR_INTERIOR_FLOOR,
            Self::Aperture => TYPE_COLOR_APERTURE,
            Self::Door => TYPE_COLOR_DOOR,
            Self::GlassDoor => TYPE_COLOR_GLASS_DOOR,
            Self::OutdoorShade => TYPE_COLOR_OUTDOOR_SHADE,
            Self::ContextShade => TYPE_COLOR_CONTEXT_SHADE,
            Self::IndoorShade => TYPE_COLOR_INDOOR_SHADE,
        }
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash)]
enum DisplayBcCategory {
    Outdoors,
    Surface,
    Ground,
    Adiabatic,
    Other,
}

impl DisplayBcCategory {
    /// Canonical `honeybee_display/model.py` `BC_COLORS` ordering.
    const ALL: [Self; 5] = [
        Self::Outdoors,
        Self::Surface,
        Self::Ground,
        Self::Adiabatic,
        Self::Other,
    ];

    const fn key(self) -> &'static str {
        match self {
            Self::Outdoors => "outdoors",
            Self::Surface => "surface",
            Self::Ground => "ground",
            Self::Adiabatic => "adiabatic",
            Self::Other => "other",
        }
    }

    const fn label(self) -> &'static str {
        match self {
            Self::Outdoors => "Outdoors",
            Self::Surface => "Surface",
            Self::Ground => "Ground",
            Self::Adiabatic => "Adiabatic",
            Self::Other => "Other",
        }
    }

    const fn color(self) -> [f32; 4] {
        match self {
            Self::Outdoors => BC_COLOR_OUTDOORS,
            Self::Surface => BC_COLOR_SURFACE,
            Self::Ground => BC_COLOR_GROUND,
            Self::Adiabatic => BC_COLOR_ADIABATIC,
            Self::Other => BC_COLOR_OTHER,
        }
    }
}

/// Return `true` when `record` is a glazed `Door`.
fn is_glass_door(record: &ObjectRecord) -> bool {
    record.kind == ObjectKind::Door
        && (record.is_glass
            || record.face_type.as_deref().is_some_and(|ft| {
                ft.eq_ignore_ascii_case("GlassDoor") || ft.eq_ignore_ascii_case("glass_door")
            }))
}

/// Return `true` when `record` is an `AirBoundary` face.
fn is_air_boundary(record: &ObjectRecord) -> bool {
    record.kind == ObjectKind::Face
        && record.face_type.as_deref().is_some_and(|ft| {
            let norm = ft.trim();
            norm.eq_ignore_ascii_case("AirBoundary")
                || norm.eq_ignore_ascii_case("air_boundary")
                || norm.eq_ignore_ascii_case("air boundary")
        })
}

/// Return `true` when the object should render as translucent glazing or air boundary.
fn is_translucent_surface(record: &ObjectRecord) -> bool {
    match record.kind {
        ObjectKind::Aperture => true,
        ObjectKind::Door => is_glass_door(record),
        ObjectKind::Face => is_air_boundary(record),
        _ => false,
    }
}

/// Per `honeybee_display/model.py` lines 161-174 & `honeybee/face.py` line 516:
/// `Outdoors` and `Ground` use exterior type classification (`Wall`, `Roof`, `Floor`);
/// all other boundary conditions (`Surface`, `Adiabatic`, `OtherSideTemperature`, etc.)
/// use interior classification (`Interior Wall`, `Ceiling`, `Interior Floor`).
fn is_exterior_boundary(bc: Option<&str>) -> bool {
    match bc.map(|s| s.trim().to_ascii_lowercase()).as_deref() {
        Some("outdoors") | Some("ground") | None => true,
        Some(_) => false,
    }
}

/// Classify a non-Room object into its canonical `honeybee-display` type category.
fn classify_display_type(record: &ObjectRecord) -> Option<DisplayTypeCategory> {
    match record.kind {
        ObjectKind::Room => None,
        ObjectKind::Aperture => Some(DisplayTypeCategory::Aperture),
        ObjectKind::Door => {
            if is_glass_door(record) {
                Some(DisplayTypeCategory::GlassDoor)
            } else {
                Some(DisplayTypeCategory::Door)
            }
        }
        ObjectKind::Shade => {
            if record.is_indoor_shade {
                return Some(DisplayTypeCategory::IndoorShade);
            }
            if record.is_detached_shade {
                return Some(DisplayTypeCategory::ContextShade);
            }
            match record
                .face_type
                .as_deref()
                .map(|s| s.trim().to_ascii_lowercase())
                .as_deref()
            {
                Some("indoorshade") | Some("indoor_shade") | Some("indoor shade") => {
                    Some(DisplayTypeCategory::IndoorShade)
                }
                Some("contextshade") | Some("context_shade") | Some("context shade") => {
                    Some(DisplayTypeCategory::ContextShade)
                }
                _ => Some(DisplayTypeCategory::OutdoorShade),
            }
        }
        ObjectKind::Face => {
            let exterior = is_exterior_boundary(record.boundary_condition.as_deref());
            match record
                .face_type
                .as_deref()
                .map(|s| s.trim().to_ascii_lowercase())
                .as_deref()
            {
                Some("airboundary") | Some("air_boundary") | Some("air boundary") => {
                    Some(DisplayTypeCategory::AirBoundary)
                }
                Some("wall") => Some(if exterior {
                    DisplayTypeCategory::Wall
                } else {
                    DisplayTypeCategory::InteriorWall
                }),
                Some("interiorwall") | Some("interior_wall") | Some("interior wall") => {
                    Some(DisplayTypeCategory::InteriorWall)
                }
                Some("roofceiling") | Some("roof_ceiling") => Some(if exterior {
                    DisplayTypeCategory::Roof
                } else {
                    DisplayTypeCategory::Ceiling
                }),
                Some("roof") => Some(DisplayTypeCategory::Roof),
                Some("ceiling") => Some(DisplayTypeCategory::Ceiling),
                Some("floor") => Some(if exterior {
                    DisplayTypeCategory::Floor
                } else {
                    DisplayTypeCategory::InteriorFloor
                }),
                Some("interiorfloor") | Some("interior_floor") | Some("interior floor") => {
                    Some(DisplayTypeCategory::InteriorFloor)
                }
                _ => Some(if exterior {
                    DisplayTypeCategory::Wall
                } else {
                    DisplayTypeCategory::InteriorWall
                }),
            }
        }
    }
}

/// Classify a non-Room object into its canonical `honeybee-display` boundary condition category.
fn classify_display_bc(record: &ObjectRecord) -> Option<DisplayBcCategory> {
    if record.kind == ObjectKind::Room {
        return None;
    }
    if record.kind == ObjectKind::Shade {
        return Some(DisplayBcCategory::Other);
    }
    match record
        .boundary_condition
        .as_deref()
        .map(|s| s.trim().to_ascii_lowercase())
        .as_deref()
    {
        Some("outdoors") => Some(DisplayBcCategory::Outdoors),
        Some("surface") => Some(DisplayBcCategory::Surface),
        Some("ground") => Some(DisplayBcCategory::Ground),
        Some("adiabatic") => Some(DisplayBcCategory::Adiabatic),
        _ => Some(DisplayBcCategory::Other),
    }
}

/// Linearly interpolate along a Ladybug `Colorset` palette over `t` in `[0.0, 1.0]`,
/// matching `ladybug.color.ColorRange._cal_color`.
pub fn sample_ladybug_colorset(palette: &[[u8; 3]], t: f32, alpha: f32) -> [f32; 4] {
    if palette.is_empty() {
        return [UNASSIGNED_COLOR[0], UNASSIGNED_COLOR[1], UNASSIGNED_COLOR[2], alpha];
    }
    let t = if t.is_finite() { t.clamp(0.0, 1.0) } else { 0.0 };
    if palette.len() == 1 || t <= 0.0 {
        let c = palette[0];
        return [c[0] as f32 / 255.0, c[1] as f32 / 255.0, c[2] as f32 / 255.0, alpha];
    }
    if t >= 1.0 {
        let c = palette[palette.len() - 1];
        return [c[0] as f32 / 255.0, c[1] as f32 / 255.0, c[2] as f32 / 255.0, alpha];
    }
    let scaled = t * (palette.len() - 1) as f32;
    let idx = (scaled.floor() as usize).min(palette.len() - 2);
    let frac = scaled - idx as f32;
    let a = palette[idx];
    let b = palette[idx + 1];
    let r = (a[0] as f32 + (b[0] as f32 - a[0] as f32) * frac) / 255.0;
    let g = (a[1] as f32 + (b[1] as f32 - a[1] as f32) * frac) / 255.0;
    let bl = (a[2] as f32 + (b[2] as f32 - a[2] as f32) * frac) / 255.0;
    [r.clamp(0.0, 1.0), g.clamp(0.0, 1.0), bl.clamp(0.0, 1.0), alpha]
}

/// FNV-1a 64-bit hash + SplitMix64 finalizer for standalone single-record categorical color lookup.
fn hash_label(label: &str) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in label.as_bytes() {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x100000001b3);
    }
    h ^= h >> 30;
    h = h.wrapping_mul(0xbf58476d1ce4e5b9);
    h ^= h >> 27;
    h = h.wrapping_mul(0x94d049bb133111eb);
    h ^ (h >> 31)
}

/// Standalone categorical fallback using Ladybug `Colorset.original()` when no `SceneData` is provided.
fn standalone_categorical_color(label: Option<&str>, alpha: f32) -> [f32; 4] {
    let Some(text) = label.map(str::trim).filter(|s| !s.is_empty()) else {
        return [
            UNASSIGNED_COLOR[0],
            UNASSIGNED_COLOR[1],
            UNASSIGNED_COLOR[2],
            alpha,
        ];
    };
    let hash = hash_label(text);
    let t = (hash & 0xffff) as f32 / 65535.0;
    sample_ladybug_colorset(&LADYBUG_ORIGINAL, t, alpha)
}

/// Extract the trimmed categorical attribute string for room-level `ColorBy` modes.
fn categorical_attr(record: &ObjectRecord, color_by: ColorBy) -> Option<&str> {
    let raw = match color_by {
        ColorBy::Story => record.story.as_deref(),
        ColorBy::Zone => record.zone.as_deref(),
        ColorBy::ProgramType => record.program_type.as_deref(),
        ColorBy::ConstructionSet => record.construction_set.as_deref(),
        ColorBy::Hvac => record.hvac.as_deref(),
        _ => None,
    };
    raw.map(str::trim).filter(|s| !s.is_empty())
}

/// Collect ordered unique category labels and their Ladybug `Colorset.original()` colors for a scene.
///
/// Mirrors official Honeybee SDK `honeybee.colorobj.ColorRoom` + `ladybug.legend.LegendParameters`
/// (`Colorset.original()`):
/// - `Story` preserves ascending elevation order from `scene.stories`, followed by any extra labels.
/// - `Zone`, `ProgramType`, `ConstructionSet`, `Hvac` are sorted lexicographically.
fn scene_category_palette(scene: &SceneData, color_by: ColorBy) -> Vec<(String, [f32; 4])> {
    let mut unique: BTreeSet<String> = BTreeSet::new();
    for rec in &scene.objects {
        if let Some(val) = categorical_attr(rec, color_by) {
            unique.insert(val.to_owned());
        }
    }

    let mut ordered: Vec<String> = Vec::with_capacity(unique.len());
    if color_by == ColorBy::Story {
        for story in &scene.stories {
            let trimmed = story.trim();
            if unique.remove(trimmed) {
                ordered.push(trimmed.to_owned());
            }
        }
    }
    ordered.extend(unique);

    let count = ordered.len();
    ordered
        .into_iter()
        .enumerate()
        .map(|(i, label)| {
            let t = if count <= 1 {
                0.0
            } else {
                i as f32 / (count - 1) as f32
            };
            let col = sample_ladybug_colorset(&LADYBUG_ORIGINAL, t, 1.0);
            (label, col)
        })
        .collect()
}

/// Compute the official `honeybee-display` / Ladybug RGBA color (`[0.0, 1.0]` sRGB)
/// for a single scene object without scene-wide category indexing.
///
/// For `Type` and `BoundaryCondition`, this matches [`resolve_scene_colors`] identically.
/// For categorical room-attribute modes (`Story`, `Zone`, `ProgramType`, `ConstructionSet`, `Hvac`),
/// prefer [`color_for_object_in_scene`] or [`resolve_scene_colors`] so swatches match [`build_legend`].
pub fn color_for_object(record: &ObjectRecord, color_by: ColorBy) -> [f32; 4] {
    let alpha = if is_translucent_surface(record) {
        TRANSLUCENT_ALPHA
    } else {
        1.0
    };

    match color_by {
        ColorBy::Type => match classify_display_type(record) {
            Some(cat) => cat.color(),
            None => ROOM_NEUTRAL_COLOR,
        },
        ColorBy::BoundaryCondition => match classify_display_bc(record) {
            Some(cat) => {
                let c = cat.color();
                [c[0], c[1], c[2], alpha]
            }
            None => ROOM_NEUTRAL_COLOR,
        },
        ColorBy::Story
        | ColorBy::Zone
        | ColorBy::ProgramType
        | ColorBy::ConstructionSet
        | ColorBy::Hvac => standalone_categorical_color(categorical_attr(record, color_by), alpha),
    }
}

/// Compute the scene-consistent sRGB RGBA color for `record` under `color_by`, guaranteed to match
/// both [`resolve_scene_colors`] and [`build_legend`] across all 8 `ColorBy` modes.
pub fn color_for_object_in_scene(
    scene: &SceneData,
    record: &ObjectRecord,
    color_by: ColorBy,
) -> [f32; 4] {
    match color_by {
        ColorBy::Story
        | ColorBy::Zone
        | ColorBy::ProgramType
        | ColorBy::ConstructionSet
        | ColorBy::Hvac => {
            let alpha = if is_translucent_surface(record) {
                TRANSLUCENT_ALPHA
            } else {
                1.0
            };
            let Some(val) = categorical_attr(record, color_by) else {
                return [
                    UNASSIGNED_COLOR[0],
                    UNASSIGNED_COLOR[1],
                    UNASSIGNED_COLOR[2],
                    alpha,
                ];
            };
            let palette = scene_category_palette(scene, color_by);
            if let Some((_, col)) = palette.iter().find(|(k, _)| k == val) {
                [col[0], col[1], col[2], alpha]
            } else {
                [
                    UNASSIGNED_COLOR[0],
                    UNASSIGNED_COLOR[1],
                    UNASSIGNED_COLOR[2],
                    alpha,
                ]
            }
        }
        _ => color_for_object(record, color_by),
    }
}

/// Resolve a color table of length `max_id + 1`, indexed directly by `object_id`.
///
/// Slot `0` (reserved for background) receives `[0.0, 0.0, 0.0, 0.0]`.
pub fn resolve_scene_colors(scene: &SceneData, color_by: ColorBy) -> Vec<[f32; 4]> {
    let max_id = scene
        .objects
        .iter()
        .map(|record| record.object_id)
        .max()
        .unwrap_or(0) as usize;
    let mut colors = vec![[0.0, 0.0, 0.0, 0.0]; max_id + 1];

    match color_by {
        ColorBy::Story
        | ColorBy::Zone
        | ColorBy::ProgramType
        | ColorBy::ConstructionSet
        | ColorBy::Hvac => {
            let palette_map: HashMap<String, [f32; 4]> =
                scene_category_palette(scene, color_by).into_iter().collect();
            for record in &scene.objects {
                let alpha = if is_translucent_surface(record) {
                    TRANSLUCENT_ALPHA
                } else {
                    1.0
                };
                let rgb_base = categorical_attr(record, color_by)
                    .and_then(|val| palette_map.get(val).copied())
                    .unwrap_or(UNASSIGNED_COLOR);
                colors[record.object_id as usize] = [rgb_base[0], rgb_base[1], rgb_base[2], alpha];
            }
        }
        _ => {
            for record in &scene.objects {
                colors[record.object_id as usize] = color_for_object(record, color_by);
            }
        }
    }
    colors
}

/// Build a structured Ladybug Tools [`LegendData`] matching `honeybee-display` and `ladybug.legend`
/// for the given scene and [`ColorBy`] mode.
pub fn build_legend(scene: &SceneData, color_by: ColorBy) -> LegendData {
    match color_by {
        ColorBy::Type => {
            let mut counts: HashMap<DisplayTypeCategory, usize> = HashMap::new();
            for rec in &scene.objects {
                if let Some(cat) = classify_display_type(rec) {
                    *counts.entry(cat).or_insert(0) += 1;
                }
            }
            let entries = DisplayTypeCategory::ALL
                .into_iter()
                .filter_map(|cat| {
                    let count = counts.get(&cat).copied().unwrap_or(0);
                    (count > 0).then(|| LegendEntry {
                        key: cat.key().to_owned(),
                        label: cat.label().to_owned(),
                        color_srgb: cat.color(),
                        count,
                    })
                })
                .collect();
            LegendData {
                key: color_by.as_str().to_owned(),
                title: "Face Type".to_owned(),
                is_continuous: false,
                entries,
                min_val: None,
                max_val: None,
                unit: None,
            }
        }
        ColorBy::BoundaryCondition => {
            let mut counts: HashMap<DisplayBcCategory, usize> = HashMap::new();
            for rec in &scene.objects {
                if let Some(cat) = classify_display_bc(rec) {
                    *counts.entry(cat).or_insert(0) += 1;
                }
            }
            let entries = DisplayBcCategory::ALL
                .into_iter()
                .filter_map(|cat| {
                    let count = counts.get(&cat).copied().unwrap_or(0);
                    (count > 0).then(|| LegendEntry {
                        key: cat.key().to_owned(),
                        label: cat.label().to_owned(),
                        color_srgb: cat.color(),
                        count,
                    })
                })
                .collect();
            LegendData {
                key: color_by.as_str().to_owned(),
                title: "Boundary Condition".to_owned(),
                is_continuous: false,
                entries,
                min_val: None,
                max_val: None,
                unit: None,
            }
        }
        ColorBy::Story
        | ColorBy::Zone
        | ColorBy::ProgramType
        | ColorBy::ConstructionSet
        | ColorBy::Hvac => {
            let title = match color_by {
                ColorBy::Story => "Story",
                ColorBy::Zone => "Zone",
                ColorBy::ProgramType => "Program Type",
                ColorBy::ConstructionSet => "Construction Set",
                ColorBy::Hvac => "HVAC",
                _ => "",
            };
            let has_rooms = scene.objects.iter().any(|r| r.kind == ObjectKind::Room);
            let mut counts: BTreeMap<String, usize> = BTreeMap::new();
            let mut unassigned_count = 0_usize;

            for rec in &scene.objects {
                let include = if has_rooms {
                    rec.kind == ObjectKind::Room
                } else {
                    rec.kind != ObjectKind::Room
                };
                if !include {
                    continue;
                }
                if let Some(val) = categorical_attr(rec, color_by) {
                    *counts.entry(val.to_owned()).or_insert(0) += 1;
                } else {
                    unassigned_count += 1;
                }
            }

            let palette = scene_category_palette(scene, color_by);
            let mut entries: Vec<LegendEntry> = palette
                .into_iter()
                .filter_map(|(cat_label, col)| {
                    let count = counts.get(&cat_label).copied().unwrap_or(0);
                    (count > 0).then(|| LegendEntry {
                        key: cat_label.clone(),
                        label: cat_label,
                        color_srgb: col,
                        count,
                    })
                })
                .collect();

            if unassigned_count > 0 {
                entries.push(LegendEntry {
                    key: "unassigned".to_owned(),
                    label: "None".to_owned(),
                    color_srgb: UNASSIGNED_COLOR,
                    count: unassigned_count,
                });
            }

            LegendData {
                key: color_by.as_str().to_owned(),
                title: title.to_owned(),
                is_continuous: false,
                entries,
                min_val: None,
                max_val: None,
                unit: None,
            }
        }
    }
}
