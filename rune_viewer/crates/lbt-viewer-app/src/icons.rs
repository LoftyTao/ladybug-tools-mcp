//! Lean embedded official Ladybug Tools Artwork icon registry.
//!
//! Only the 9 essential official Ladybug Tools assets are embedded at compile time via
//! `include_bytes!` and rasterized once into static `OnceLock<Pixels>` slots using Rune's
//! built-in `png_rgba8` + `downsample_rgba` and `resvg` (`svg_rgba`) pipeline. All standard
//! UI controls use `rune-kit`'s native glyphs and text-first components.

use std::sync::OnceLock;

use lbt_scene::{ObjectKind, ObjectRecord};
use rune::{Color, El, Pixels, SurfaceFit, el};

const SVG_RASTER_PX: u32 = 48;
const PNG_RASTER_PX: u32 = 64;

/// Essential official Ladybug Tools Artwork icons embedded in `lbt-viewer-app`.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash)]
#[repr(usize)]
pub enum StudioIcon {
    /// Toolbar brand identity.
    LbtHoneybee = 0,
    /// Honeybee Schema: Model root & Room Edit breadcrumb.
    LbtModel,
    /// Honeybee Schema: Room.
    LbtRoom,
    /// Honeybee Schema: Face.
    LbtFace,
    /// Honeybee Schema: Aperture.
    LbtAperture,
    /// Honeybee Schema: Door.
    LbtDoor,
    /// Honeybee Schema: Attached Shade.
    LbtShade,
    /// Honeybee Schema: Context / Orphaned Shade & ShadeMesh.
    LbtContextShade,
    /// Subtle Axis HUD compass watermark.
    LbtCompass,
}

impl StudioIcon {
    pub const COUNT: usize = 9;

    /// All embedded icons in enum order (used by asset integrity tests).
    pub const ALL: [Self; Self::COUNT] = [
        Self::LbtHoneybee,
        Self::LbtModel,
        Self::LbtRoom,
        Self::LbtFace,
        Self::LbtAperture,
        Self::LbtDoor,
        Self::LbtShade,
        Self::LbtContextShade,
        Self::LbtCompass,
    ];

    fn raw_bytes(self) -> (&'static [u8], bool) {
        match self {
            // (bytes, is_png)
            Self::LbtHoneybee => (include_bytes!("../assets/icons/lbt/honeybee.png"), true),
            Self::LbtModel => (include_bytes!("../assets/icons/lbt/model.png"), true),
            Self::LbtRoom => (include_bytes!("../assets/icons/lbt/room.png"), true),
            Self::LbtFace => (include_bytes!("../assets/icons/lbt/face.png"), true),
            Self::LbtAperture => (include_bytes!("../assets/icons/lbt/aperture.png"), true),
            Self::LbtDoor => (include_bytes!("../assets/icons/lbt/door.png"), true),
            Self::LbtShade => (include_bytes!("../assets/icons/lbt/shade.png"), true),
            Self::LbtContextShade => (include_bytes!("../assets/icons/lbt/context_shade.png"), true),
            Self::LbtCompass => (include_bytes!("../assets/icons/lbt/compass.svg"), false),
        }
    }
}

static ICON_CACHE: [OnceLock<Pixels>; StudioIcon::COUNT] =
    [const { OnceLock::new() }; StudioIcon::COUNT];

fn decode_icon_pixels(icon: StudioIcon) -> Pixels {
    let pixels = Pixels::new();
    let (bytes, is_png) = icon.raw_bytes();
    if is_png {
        if let Ok(rgba_img) = rune::image::png_rgba8(bytes) {
            let w = rgba_img.width();
            let h = rgba_img.height();
            let raw = rgba_img.into_raw();
            let (tw, th) = rune::image::scaled_dimensions(w, h, PNG_RASTER_PX);
            if let Ok((dw, dh, down)) = rune::image::downsample_rgba(w, h, raw, tw, th) {
                pixels.set(dw, dh, down);
            }
        }
    } else if let Ok((w, h, rgba)) = rune::image::svg_rgba(bytes, SVG_RASTER_PX) {
        pixels.set(w, h, rgba);
    }
    pixels
}

/// Get the lazily cached `Pixels` handle for `icon`.
pub fn icon_pixels(icon: StudioIcon) -> &'static Pixels {
    ICON_CACHE[icon as usize].get_or_init(|| decode_icon_pixels(icon))
}

/// Build a full-color icon element sized at `size_pt × size_pt`.
pub fn icon_el(icon: StudioIcon, size_pt: f32) -> El {
    el().size(size_pt, size_pt)
        .pixels_fit(icon_pixels(icon), SurfaceFit::Fit)
}

/// Build a tinted icon element sized at `size_pt × size_pt` (used for the subtle Compass watermark).
pub fn tinted_icon_el(icon: StudioIcon, size_pt: f32, color: Color) -> El {
    el().size(size_pt, size_pt)
        .pixels_fit(icon_pixels(icon), SurfaceFit::Fit)
        .pixels_tint(color)
}

/// Official Ladybug Tools Artwork icon for any Honeybee `ObjectKind`.
pub const fn lbt_object_icon(kind: ObjectKind) -> StudioIcon {
    match kind {
        ObjectKind::Room => StudioIcon::LbtRoom,
        ObjectKind::Face => StudioIcon::LbtFace,
        ObjectKind::Aperture => StudioIcon::LbtAperture,
        ObjectKind::Door => StudioIcon::LbtDoor,
        ObjectKind::Shade => StudioIcon::LbtShade,
    }
}

/// Official Ladybug Tools Artwork icon for a specific `ObjectRecord` (distinguishing Context Shades).
pub const fn lbt_record_icon(rec: &ObjectRecord) -> StudioIcon {
    if matches!(rec.kind, ObjectKind::Shade) && (rec.is_detached_shade || rec.is_orphaned) {
        StudioIcon::LbtContextShade
    } else {
        lbt_object_icon(rec.kind)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_embedded_icons_decode_with_nonzero_dimensions() {
        assert_eq!(StudioIcon::COUNT, 9);
        for icon in StudioIcon::ALL {
            let px = icon_pixels(icon);
            let (w, h) = px.size();
            assert!(w > 0 && h > 0, "icon {icon:?} failed to decode ({w}x{h})");
            assert!(
                w <= PNG_RASTER_PX && h <= PNG_RASTER_PX,
                "icon {icon:?} exceeded raster bound: {w}x{h}"
            );
        }
    }
}
