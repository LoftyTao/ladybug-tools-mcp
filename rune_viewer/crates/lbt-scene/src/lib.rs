//! Shared 3D scene, HBJSON parser, triangulation, color mapping, and Garden Web View protocol
//! types for `lbt-rune-viewer`.

pub mod color;
pub mod parser;
pub mod triangulate;
pub mod types;

pub use color::{color_for_object, resolve_scene_colors};
pub use parser::{load_hbjson_file, load_hbjson_str, SceneError};
pub use triangulate::orientation_label;
pub use types::*;
