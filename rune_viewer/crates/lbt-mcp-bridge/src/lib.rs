//! File-based MCP bridge for `<garden>/tmp/web_view/` protocol synchronization.

use std::path::{Path, PathBuf};

use lbt_scene::{CaptureReceipt, CaptureRequest, InteractionState, PresentCommand};

/// Relative directory inside a Garden where Web View protocol files live.
pub const WEB_VIEW_DIR_REL: &str = "tmp/web_view";

/// Resolve `<garden>/tmp/web_view/`.
pub fn web_view_dir(garden_root: &Path) -> PathBuf {
    garden_root.join("tmp").join("web_view")
}

/// Resolve `<garden>/tmp/web_view/present.json`.
pub fn present_path(garden_root: &Path) -> PathBuf {
    web_view_dir(garden_root).join("present.json")
}

/// Resolve `<garden>/tmp/web_view/interaction_state.json`.
pub fn interaction_state_path(garden_root: &Path) -> PathBuf {
    web_view_dir(garden_root).join("interaction_state.json")
}

/// Resolve `<garden>/tmp/web_view/capture_request.json`.
pub fn capture_request_path(garden_root: &Path) -> PathBuf {
    web_view_dir(garden_root).join("capture_request.json")
}

/// Placeholder bridge handle until full atomic watcher/writer logic lands.
#[derive(Clone, Debug)]
pub struct GardenBridgeStub {
    pub garden_root: PathBuf,
    pub last_present: Option<PresentCommand>,
    pub interaction_state: InteractionState,
    pub pending_capture: Option<(CaptureRequest, Option<CaptureReceipt>)>,
}

impl GardenBridgeStub {
    /// Construct a bridge stub rooted at `garden_root`.
    pub fn new(garden_root: impl Into<PathBuf>) -> Self {
        Self {
            garden_root: garden_root.into(),
            last_present: None,
            interaction_state: InteractionState::default(),
            pending_capture: None,
        }
    }
}
