//! Color space conversion helpers and re-exports of `lbt_scene` architectural palettes.

pub use lbt_scene::{color_for_object, resolve_scene_colors};

/// Convert an sRGB component `[0, 1]` to linear space.
#[inline]
pub fn srgb_channel_to_linear(c: f32) -> f32 {
    let c = c.clamp(0.0, 1.0);
    if c <= 0.04045 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}

/// Convert an sRGB `[R, G, B, A]` color to linear `[R, G, B, A]` (preserving alpha).
#[inline]
pub fn srgb_to_linear(rgba: [f32; 4]) -> [f32; 4] {
    [
        srgb_channel_to_linear(rgba[0]),
        srgb_channel_to_linear(rgba[1]),
        srgb_channel_to_linear(rgba[2]),
        rgba[3].clamp(0.0, 1.0),
    ]
}
