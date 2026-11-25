//! `rune-kit` theme construction and 3D viewport palette helpers.

use lbt_scene::CameraPreset;
use rune::{Color, oklch};
use rune_kit::Kit;

/// Build the `rune-kit` semantic token kit for Dark or Light studio appearance.
pub fn studio_kit(dark: bool) -> Kit {
    Kit::neutral(dark)
}

/// 3D WebGPU/WebGL2 viewport backdrop matching the renderer clear color.
pub fn viewport_bg(dark: bool) -> Color {
    if dark {
        oklch(0.145, 0.005, 255.0)
    } else {
        oklch(0.92, 0.006, 255.0)
    }
}

/// Primary 3D camera presets shown in the `View` popover: `(preset, key)`.
pub const PRIMARY_CAMERA_BUTTONS: [(CameraPreset, &str); 3] = [
    (CameraPreset::Axon, "cam-axon"),
    (CameraPreset::Top, "cam-top"),
    (CameraPreset::Fit, "cam-fit"),
];

/// Cardinal elevation presets shown in the `View` popover: `(preset, key)`.
pub const CARDINAL_CAMERA_BUTTONS: [(CameraPreset, &str); 4] = [
    (CameraPreset::North, "cam-north"),
    (CameraPreset::South, "cam-south"),
    (CameraPreset::East, "cam-east"),
    (CameraPreset::West, "cam-west"),
];
