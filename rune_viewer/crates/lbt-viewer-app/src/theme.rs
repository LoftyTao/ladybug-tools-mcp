//! Studio color tokens and labels for the AEC viewer UI.

use lbt_scene::{CameraPreset, ColorBy, ObjectKind};
use rune::{Color, oklch, oklcha};

/// Dark Studio (default) and Light Studio UI palette.
#[derive(Clone, Copy, Debug)]
pub struct StudioTheme {
    pub bg: Color,
    pub topbar: Color,
    pub panel: Color,
    pub card: Color,
    pub card_elevated: Color,
    pub border: Color,
    pub border_strong: Color,
    pub text: Color,
    pub text_muted: Color,
    pub text_dim: Color,
    pub accent: Color,
    pub accent_soft: Color,
    pub accent_text: Color,
    pub hover: Color,
    pub press: Color,
    pub viewport_bg: Color,
    pub badge_bg: Color,
    pub live_dot: Color,
    pub offline_dot: Color,
    pub pin_color: Color,
    pub warning_color: Color,
    pub error_color: Color,
    pub info_color: Color,
    pub hairline: f32,
}

/// Build the studio theme for `dark` mode and display `scale`.
pub fn studio_theme(dark: bool, scale: f32) -> StudioTheme {
    let hair = 1.0 / scale.max(1.0);
    if dark {
        StudioTheme {
            bg: oklch(0.16, 0.006, 255.0),
            topbar: oklch(0.19, 0.007, 255.0),
            panel: oklch(0.20, 0.007, 255.0),
            card: oklch(0.235, 0.008, 255.0),
            card_elevated: oklch(0.27, 0.009, 255.0),
            border: oklcha(1.0, 0.0, 0.0, 0.12),
            border_strong: oklcha(1.0, 0.0, 0.0, 0.22),
            text: oklch(0.95, 0.004, 255.0),
            text_muted: oklch(0.75, 0.008, 255.0),
            text_dim: oklch(0.58, 0.008, 255.0),
            accent: oklch(0.68, 0.16, 248.0),
            accent_soft: oklcha(0.68, 0.16, 248.0, 0.22),
            accent_text: oklch(0.98, 0.004, 255.0),
            hover: oklcha(1.0, 0.0, 0.0, 0.07),
            press: oklcha(1.0, 0.0, 0.0, 0.13),
            viewport_bg: oklch(0.145, 0.005, 255.0),
            badge_bg: oklcha(0.17, 0.008, 255.0, 0.90),
            live_dot: oklch(0.74, 0.17, 152.0),
            offline_dot: oklch(0.58, 0.01, 255.0),
            pin_color: oklch(0.77, 0.16, 65.0),
            warning_color: oklch(0.78, 0.16, 75.0),
            error_color: oklch(0.66, 0.20, 26.0),
            info_color: oklch(0.72, 0.15, 232.0),
            hairline: hair,
        }
    } else {
        StudioTheme {
            bg: oklch(0.955, 0.004, 255.0),
            topbar: oklch(0.985, 0.003, 255.0),
            panel: oklch(0.975, 0.003, 255.0),
            card: Color::WHITE,
            card_elevated: oklch(0.99, 0.002, 255.0),
            border: oklcha(0.15, 0.01, 255.0, 0.12),
            border_strong: oklcha(0.15, 0.01, 255.0, 0.24),
            text: oklch(0.21, 0.008, 255.0),
            text_muted: oklch(0.45, 0.01, 255.0),
            text_dim: oklch(0.60, 0.01, 255.0),
            accent: oklch(0.56, 0.17, 252.0),
            accent_soft: oklcha(0.56, 0.17, 252.0, 0.14),
            accent_text: Color::WHITE,
            hover: oklcha(0.15, 0.01, 255.0, 0.06),
            press: oklcha(0.15, 0.01, 255.0, 0.12),
            viewport_bg: oklch(0.92, 0.006, 255.0),
            badge_bg: oklcha(0.99, 0.004, 255.0, 0.92),
            live_dot: oklch(0.62, 0.18, 152.0),
            offline_dot: oklch(0.62, 0.01, 255.0),
            pin_color: oklch(0.66, 0.18, 55.0),
            warning_color: oklch(0.66, 0.17, 72.0),
            error_color: oklch(0.58, 0.22, 26.0),
            info_color: oklch(0.58, 0.16, 236.0),
            hairline: hair,
        }
    }
}

/// Short top-bar label for a `ColorBy` mode.
pub fn color_by_short_label(mode: ColorBy) -> &'static str {
    match mode {
        ColorBy::Type => "Type",
        ColorBy::BoundaryCondition => "BC",
        ColorBy::Story => "Story",
        ColorBy::Zone => "Zone",
        ColorBy::ProgramType => "Program",
        ColorBy::ConstructionSet => "Constr",
        ColorBy::Hvac => "HVAC",
        ColorBy::Wwr => "WWR",
    }
}

/// Full human-readable label for a `ColorBy` mode.
pub fn color_by_full_label(mode: ColorBy) -> &'static str {
    match mode {
        ColorBy::Type => "Face Type",
        ColorBy::BoundaryCondition => "Boundary Condition",
        ColorBy::Story => "Story",
        ColorBy::Zone => "Zone",
        ColorBy::ProgramType => "Program Type",
        ColorBy::ConstructionSet => "Construction Set",
        ColorBy::Hvac => "HVAC",
        ColorBy::Wwr => "Window-Wall Ratio",
    }
}

/// Top-bar buttons for quick camera presets.
pub const CAMERA_BUTTONS: [(CameraPreset, &str, &str); 7] = [
    (CameraPreset::Axon, "Ax", "cam-axon"),
    (CameraPreset::Top, "Top", "cam-top"),
    (CameraPreset::North, "N", "cam-north"),
    (CameraPreset::South, "S", "cam-south"),
    (CameraPreset::East, "E", "cam-east"),
    (CameraPreset::West, "W", "cam-west"),
    (CameraPreset::Fit, "Fit", "cam-fit"),
];

/// Short badge label for an `ObjectKind`.
pub fn kind_badge(kind: ObjectKind) -> &'static str {
    match kind {
        ObjectKind::Room => "RM",
        ObjectKind::Face => "FC",
        ObjectKind::Aperture => "AP",
        ObjectKind::Door => "DR",
        ObjectKind::Shade => "SH",
    }
}
