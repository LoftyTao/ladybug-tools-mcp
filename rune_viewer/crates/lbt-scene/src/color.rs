//! Attribute-based RGBA color mapping for Honeybee scene objects.

use crate::types::{ColorBy, ObjectKind, ObjectRecord, SceneData};

const APERTURE_ALPHA: f32 = 0.42;

/// Return `true` when the object should render as translucent glazing.
fn is_translucent_glazing(record: &ObjectRecord) -> bool {
    match record.kind {
        ObjectKind::Aperture => true,
        ObjectKind::Door => record
            .face_type
            .as_deref()
            .is_some_and(|ft| ft.eq_ignore_ascii_case("GlassDoor") || ft.eq_ignore_ascii_case("glass_door")),
        _ => false,
    }
}

/// Return `true` if `boundary_condition` represents an interior / adiabatic boundary.
fn is_interior_boundary(bc: Option<&str>) -> bool {
    matches!(
        bc.map(|s| s.trim().to_ascii_lowercase()).as_deref(),
        Some("surface") | Some("adiabatic")
    )
}

/// FNV-1a 64-bit hash followed by a SplitMix64 avalanche step for crisp categorical dispersion.
fn hash_label(label: &str) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in label.as_bytes() {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x100000001b3);
    }
    // SplitMix64 finalizer so sequential labels ("Level 1", "Level 2", ...) disperse widely.
    h ^= h >> 30;
    h = h.wrapping_mul(0xbf58476d1ce4e5b9);
    h ^= h >> 27;
    h = h.wrapping_mul(0x94d049bb133111eb);
    h ^ (h >> 31)
}

/// Convert HSL (`h` in `[0, 360)`, `s` in `[0, 1]`, `l` in `[0, 1]`) to `[r, g, b]` in `[0, 1]`.
fn hsl_to_rgb(h: f32, s: f32, l: f32) -> [f32; 3] {
    let c = (1.0 - (2.0 * l - 1.0).abs()) * s;
    let hp = (h.rem_euclid(360.0)) / 60.0;
    let x = c * (1.0 - (hp % 2.0 - 1.0).abs());
    let (r1, g1, b1) = match hp as u32 {
        0 => (c, x, 0.0),
        1 => (x, c, 0.0),
        2 => (0.0, c, x),
        3 => (0.0, x, c),
        4 => (x, 0.0, c),
        _ => (c, 0.0, x),
    };
    let m = l - 0.5 * c;
    [
        (r1 + m).clamp(0.0, 1.0),
        (g1 + m).clamp(0.0, 1.0),
        (b1 + m).clamp(0.0, 1.0),
    ]
}

/// Map an arbitrary categorical attribute string to a deterministic, vivid architectural RGBA color.
fn categorical_color(label: Option<&str>, alpha: f32) -> [f32; 4] {
    let Some(text) = label.map(str::trim).filter(|s| !s.is_empty()) else {
        return [0.64, 0.66, 0.70, alpha];
    };

    // Use a curated 16-anchor vivid architectural hue table combined with SplitMix64 fine offset
    // so both small and large sets remain saturated, readable, and collision-free.
    const BASE_HUES: [f32; 16] = [
        208.0, // cerulean
        24.0,  // warm terracotta-orange
        152.0, // emerald
        336.0, // rose
        44.0,  // ochre gold
        268.0, // violet
        182.0, // teal
        8.0,   // coral red
        96.0,  // chartreuse-sage
        232.0, // cobalt
        304.0, // plum
        166.0, // seafoam
        58.0,  // amber-lime
        352.0, // crimson
        195.0, // cyan-blue
        286.0, // orchid
    ];

    let hash = hash_label(text);
    let anchor = BASE_HUES[(hash & 0x0f) as usize];
    let fine_jitter = (((hash >> 8) & 0xff) as f32 / 255.0 - 0.5) * 14.0;
    let hue = (anchor + fine_jitter).rem_euclid(360.0);
    let sat = 0.66 + (((hash >> 16) & 0x3f) as f32 / 63.0) * 0.14;
    let light = 0.48 + (((hash >> 24) & 0x3f) as f32 / 63.0) * 0.11;
    let [r, g, b] = hsl_to_rgb(hue, sat, light);
    [r, g, b, alpha]
}

fn lerp3(a: [f32; 3], b: [f32; 3], t: f32) -> [f32; 3] {
    [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ]
}

/// Evaluate the blue-yellow-red WWR color ramp over `[0.0, 1.0]`.
fn wwr_ramp_color(wwr: f32) -> [f32; 4] {
    let t = if wwr.is_finite() {
        wwr.clamp(0.0, 1.0)
    } else {
        0.0
    };
    const BLUE: [f32; 3] = [0.16, 0.42, 0.90];
    const CYAN: [f32; 3] = [0.20, 0.76, 0.74];
    const YELLOW: [f32; 3] = [0.98, 0.86, 0.18];
    const ORANGE: [f32; 3] = [0.95, 0.50, 0.14];
    const RED: [f32; 3] = [0.90, 0.18, 0.16];

    let rgb = if t <= 0.25 {
        lerp3(BLUE, CYAN, t / 0.25)
    } else if t <= 0.50 {
        lerp3(CYAN, YELLOW, (t - 0.25) / 0.25)
    } else if t <= 0.75 {
        lerp3(YELLOW, ORANGE, (t - 0.50) / 0.25)
    } else {
        lerp3(ORANGE, RED, (t - 0.75) / 0.25)
    };
    [rgb[0], rgb[1], rgb[2], 1.0]
}

/// Compute the architectural RGBA color (`[0.0, 1.0]` components) for a single scene object.
pub fn color_for_object(record: &ObjectRecord, color_by: ColorBy) -> [f32; 4] {
    let alpha = if is_translucent_glazing(record) {
        APERTURE_ALPHA
    } else {
        1.0
    };

    match color_by {
        ColorBy::Type => match record.kind {
            ObjectKind::Room => [0.78, 0.76, 0.72, 1.0],
            ObjectKind::Aperture => [0.35, 0.72, 0.94, APERTURE_ALPHA],
            ObjectKind::Door => {
                if is_translucent_glazing(record) {
                    [0.42, 0.76, 0.92, APERTURE_ALPHA]
                } else {
                    [0.60, 0.39, 0.23, 1.0]
                }
            }
            ObjectKind::Shade => match record
                .face_type
                .as_deref()
                .map(|s| s.to_ascii_lowercase())
                .as_deref()
            {
                Some("contextshade") | Some("context_shade") => [0.38, 0.54, 0.50, 1.0],
                Some("indoorshade") | Some("indoor_shade") => [0.48, 0.72, 0.64, 1.0],
                _ => [0.27, 0.61, 0.55, 1.0],
            },
            ObjectKind::Face => {
                let interior = is_interior_boundary(record.boundary_condition.as_deref());
                match record
                    .face_type
                    .as_deref()
                    .map(|s| s.trim().to_ascii_lowercase())
                    .as_deref()
                {
                    Some("airboundary") | Some("air_boundary") => [0.24, 0.82, 0.90, 1.0],
                    Some("wall") => {
                        if interior {
                            [0.89, 0.83, 0.62, 1.0] // pale tan interior wall
                        } else {
                            [0.90, 0.71, 0.26, 1.0] // warm ochre exterior wall
                        }
                    }
                    Some("roofceiling") | Some("roof_ceiling") | Some("roof") | Some("ceiling") => {
                        if interior {
                            [0.83, 0.58, 0.52, 1.0] // soft interior ceiling
                        } else {
                            [0.73, 0.27, 0.21, 1.0] // terracotta roof
                        }
                    }
                    Some("floor") => {
                        if interior {
                            [0.62, 0.65, 0.68, 1.0] // light interior floor
                        } else {
                            [0.45, 0.49, 0.54, 1.0] // slate floor
                        }
                    }
                    _ => [0.75, 0.75, 0.75, 1.0],
                }
            }
        },
        ColorBy::BoundaryCondition => {
            match record
                .boundary_condition
                .as_deref()
                .map(|s| s.trim().to_ascii_lowercase())
                .as_deref()
            {
                Some("outdoors") => [0.28, 0.68, 0.95, alpha],
                Some("surface") => [0.22, 0.68, 0.36, alpha],
                Some("ground") => [0.66, 0.36, 0.16, alpha],
                Some("adiabatic") => [0.92, 0.52, 0.52, alpha],
                Some(_) => [0.88, 0.78, 0.38, alpha],
                None => {
                    if record.kind == ObjectKind::Shade {
                        [0.35, 0.62, 0.56, 1.0]
                    } else {
                        [0.68, 0.70, 0.72, alpha]
                    }
                }
            }
        }
        ColorBy::Story => categorical_color(record.story.as_deref(), alpha),
        ColorBy::Zone => categorical_color(record.zone.as_deref(), alpha),
        ColorBy::ProgramType => categorical_color(record.program_type.as_deref(), alpha),
        ColorBy::ConstructionSet => categorical_color(record.construction_set.as_deref(), alpha),
        ColorBy::Hvac => categorical_color(record.hvac.as_deref(), alpha),
        ColorBy::Wwr => {
            if is_translucent_glazing(record) {
                [0.35, 0.72, 0.94, APERTURE_ALPHA]
            } else if let Some(wwr) = record.wwr {
                wwr_ramp_color(wwr)
            } else {
                [0.58, 0.60, 0.63, 1.0]
            }
        }
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
    for record in &scene.objects {
        colors[record.object_id as usize] = color_for_object(record, color_by);
    }
    colors
}
