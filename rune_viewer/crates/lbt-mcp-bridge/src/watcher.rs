//! Garden `<garden>/tmp/web_view/` watcher, interaction writer, and capture responder.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use lbt_scene::{
    CaptureReceipt, CaptureRequest, InteractionState, ObjectTargetRef, PROTOCOL_SCHEMA_VERSION,
    PendingIntent, PinStatus, PresentCommand, SpatialPin, ViewportSnapshot,
};

use crate::atomic::{
    BridgeError, read_json_if_exists, resolve_contained_path, utc_now_iso, write_bytes_atomic,
    write_json_atomic,
};

static PIN_COUNTER: AtomicU64 = AtomicU64::new(1);

/// Relative directory inside a Garden where Web View protocol files live.
pub const WEB_VIEW_DIR_REL: &str = "tmp/web_view";

/// Relative directory inside a Garden where capture receipts and PNGs live.
pub const CAPTURES_DIR_REL: &str = "tmp/web_view/captures";

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

/// Resolve `<garden>/tmp/web_view/captures/`.
pub fn captures_dir(garden_root: &Path) -> PathBuf {
    web_view_dir(garden_root).join("captures")
}

/// Polls `<garden>/tmp/web_view/present.json` and `capture_request.json` for agent updates.
#[derive(Clone, Debug)]
pub struct GardenWatcher {
    garden_root: PathBuf,
    last_present_revision: Option<u64>,
    last_present: Option<PresentCommand>,
    last_capture_request_id: Option<String>,
}

impl GardenWatcher {
    /// Create a watcher bound to `garden_root`.
    pub fn new(garden_root: impl Into<PathBuf>) -> Self {
        Self {
            garden_root: garden_root.into(),
            last_present_revision: None,
            last_present: None,
            last_capture_request_id: None,
        }
    }

    /// Return the Garden root path.
    pub fn garden_root(&self) -> &Path {
        &self.garden_root
    }

    /// Return the most recently observed `present.json` command, if any.
    pub fn last_present(&self) -> Option<&PresentCommand> {
        self.last_present.as_ref()
    }

    /// Return the last seen `present.json` revision, if any.
    pub fn last_revision(&self) -> Option<u64> {
        self.last_present_revision
    }

    /// Read `<garden>/tmp/web_view/present.json` without advancing watcher state.
    pub fn read_present(&self) -> Result<Option<PresentCommand>, BridgeError> {
        read_json_if_exists(&present_path(&self.garden_root))
    }

    /// Check `present.json` and return `Some(cmd)` whenever a new revision arrives.
    pub fn poll_present(&mut self) -> Result<Option<PresentCommand>, BridgeError> {
        let Some(present) = self.read_present()? else {
            return Ok(None);
        };
        let changed = match self.last_present_revision {
            None => true,
            Some(prev) => present.revision != prev,
        };
        if changed {
            self.last_present_revision = Some(present.revision);
            self.last_present = Some(present.clone());
            return Ok(Some(present));
        }
        Ok(None)
    }

    /// Resolve the Garden-contained `.hbjson` path referenced by `present.model_path`.
    pub fn resolve_model_path(&self, present: &PresentCommand) -> Result<Option<PathBuf>, BridgeError> {
        let Some(rel) = present.model_path.as_deref() else {
            return Ok(None);
        };
        if rel.trim().is_empty() {
            return Ok(None);
        }
        Ok(Some(resolve_contained_path(&self.garden_root, rel)?))
    }

    /// Check `capture_request.json` and return `Some(req)` if an unanswered capture request is pending.
    pub fn poll_capture_request(&mut self) -> Result<Option<CaptureRequest>, BridgeError> {
        let Some(req) = read_json_if_exists::<CaptureRequest>(&capture_request_path(&self.garden_root))? else {
            return Ok(None);
        };
        if req.request_id.trim().is_empty() {
            return Ok(None);
        }
        if self.last_capture_request_id.as_deref() == Some(req.request_id.as_str()) {
            return Ok(None);
        }
        let (_, receipt_file) = self.resolve_capture_paths(&req)?;
        if receipt_file.is_file() {
            self.last_capture_request_id = Some(req.request_id.clone());
            return Ok(None);
        }
        Ok(Some(req))
    }

    /// Resolve contained `(png_path, receipt_json_path)` for a `CaptureRequest`.
    pub fn resolve_capture_paths(&self, req: &CaptureRequest) -> Result<(PathBuf, PathBuf), BridgeError> {
        let id = req.request_id.trim();
        if id.is_empty() || id.contains(['/', '\\']) || id.contains("..") {
            return Err(BridgeError::InvalidPath(format!(
                "invalid capture request_id: {:?}",
                req.request_id
            )));
        }
        let png_rel = req
            .output_png_path
            .clone()
            .unwrap_or_else(|| format!("{CAPTURES_DIR_REL}/{id}.png"));
        let receipt_rel = req
            .receipt_path
            .clone()
            .unwrap_or_else(|| format!("{CAPTURES_DIR_REL}/{id}.json"));
        let png_abs = resolve_contained_path(&self.garden_root, &png_rel)?;
        let receipt_abs = resolve_contained_path(&self.garden_root, &receipt_rel)?;
        Ok((png_abs, receipt_abs))
    }

    /// Atomically write the captured PNG first, then write `captures/<request_id>.json` (`CaptureReceipt`).
    pub fn write_capture_result(
        &mut self,
        req: &CaptureRequest,
        png_bytes: &[u8],
        width: u32,
        height: u32,
        model_path: Option<String>,
        revision: Option<u64>,
    ) -> Result<CaptureReceipt, BridgeError> {
        if png_bytes.is_empty() {
            return Err(BridgeError::Protocol("cannot write empty PNG capture".to_owned()));
        }
        let (png_abs, receipt_abs) = self.resolve_capture_paths(req)?;
        let image_rel = req
            .output_png_path
            .clone()
            .unwrap_or_else(|| format!("{CAPTURES_DIR_REL}/{}.png", req.request_id.trim()));

        write_bytes_atomic(&png_abs, png_bytes)?;

        let receipt = CaptureReceipt {
            schema_version: PROTOCOL_SCHEMA_VERSION.to_owned(),
            request_id: req.request_id.clone(),
            status: "ok".to_owned(),
            image_path: image_rel,
            absolute_path: Some(png_abs.to_string_lossy().into_owned()),
            width,
            height,
            model_path,
            revision,
            error: None,
            captured_at: Some(utc_now_iso()),
        };
        write_json_atomic(&receipt_abs, &receipt)?;
        self.last_capture_request_id = Some(req.request_id.clone());
        Ok(receipt)
    }

    /// Atomically write an error `CaptureReceipt` so the waiting MCP caller fails fast instead of timing out.
    pub fn write_capture_error(
        &mut self,
        req: &CaptureRequest,
        error_message: impl Into<String>,
    ) -> Result<CaptureReceipt, BridgeError> {
        let (_, receipt_abs) = self.resolve_capture_paths(req)?;
        let image_rel = req
            .output_png_path
            .clone()
            .unwrap_or_else(|| format!("{CAPTURES_DIR_REL}/{}.png", req.request_id.trim()));
        let receipt = CaptureReceipt {
            schema_version: PROTOCOL_SCHEMA_VERSION.to_owned(),
            request_id: req.request_id.clone(),
            status: "error".to_owned(),
            image_path: image_rel,
            absolute_path: None,
            width: 0,
            height: 0,
            model_path: None,
            revision: None,
            error: Some(error_message.into()),
            captured_at: Some(utc_now_iso()),
        };
        write_json_atomic(&receipt_abs, &receipt)?;
        self.last_capture_request_id = Some(req.request_id.clone());
        Ok(receipt)
    }
}

/// Viewer -> Agent bidirectional writer for `<garden>/tmp/web_view/interaction_state.json`.
#[derive(Clone, Debug)]
pub struct GardenBridge {
    garden_root: PathBuf,
    garden_id: Option<String>,
}

impl GardenBridge {
    /// Construct a Garden bridge rooted at `garden_root`.
    pub fn new(garden_root: impl Into<PathBuf>) -> Self {
        Self {
            garden_root: garden_root.into(),
            garden_id: None,
        }
    }

    /// Construct a Garden bridge with an explicit `garden_id` fallback.
    pub fn with_garden_id(garden_root: impl Into<PathBuf>, garden_id: impl Into<String>) -> Self {
        Self {
            garden_root: garden_root.into(),
            garden_id: Some(garden_id.into()),
        }
    }

    /// Return the Garden root path.
    pub fn garden_root(&self) -> &Path {
        &self.garden_root
    }

    /// Read `<garden>/tmp/web_view/interaction_state.json` if it exists.
    pub fn read_interaction_state(&self) -> Result<Option<InteractionState>, BridgeError> {
        read_json_if_exists(&interaction_state_path(&self.garden_root))
    }

    /// Atomically write `interaction_state.json`, refreshing `schema_version` and `updated_at`.
    pub fn write_interaction_state(&self, mut state: InteractionState) -> Result<InteractionState, BridgeError> {
        state.schema_version = PROTOCOL_SCHEMA_VERSION.to_owned();
        if state.garden_id.is_none() {
            state.garden_id = self.garden_id.clone();
        }
        state.updated_at = Some(utc_now_iso());
        write_json_atomic(&interaction_state_path(&self.garden_root), &state)?;
        Ok(state)
    }

    /// Read-modify-write `interaction_state.json` atomically, preserving existing pins and fields.
    pub fn update_interaction_state<F>(&self, mutate: F) -> Result<InteractionState, BridgeError>
    where
        F: FnOnce(&mut InteractionState),
    {
        let mut state = self.read_interaction_state()?.unwrap_or_else(|| InteractionState {
            garden_id: self.garden_id.clone(),
            ..Default::default()
        });
        if state.garden_id.is_none() {
            state.garden_id = self.garden_id.clone();
        }
        mutate(&mut state);
        self.write_interaction_state(state)
    }

    /// Record the live viewer PID in `interaction_state.json` (passing `None` clears it).
    pub fn set_viewer_pid(&self, pid: Option<u32>) -> Result<InteractionState, BridgeError> {
        self.update_interaction_state(|state| {
            state.viewer_pid = pid;
        })
    }

    /// Replace `selected_targets` in `interaction_state.json`.
    pub fn set_selected_targets(&self, targets: Vec<ObjectTargetRef>) -> Result<InteractionState, BridgeError> {
        self.update_interaction_state(|state| {
            state.selected_targets = targets;
        })
    }

    /// Append a new spatial annotation pin (or update an existing pin with the same `id`).
    pub fn upsert_spatial_pin(&self, mut pin: SpatialPin) -> Result<(InteractionState, SpatialPin), BridgeError> {
        let now = utc_now_iso();
        if pin.id.trim().is_empty() {
            let seq = PIN_COUNTER.fetch_add(1, Ordering::Relaxed);
            pin.id = format!("pin_{}_{seq}", std::process::id());
        }
        if pin.created_at.is_none() {
            pin.created_at = Some(now.clone());
        }
        pin.updated_at = Some(now);
        let stored_pin = pin.clone();
        let state = self.update_interaction_state(|state| {
            if let Some(existing) = state.annotations.iter_mut().find(|p| p.id == pin.id) {
                *existing = pin;
            } else {
                state.annotations.push(pin);
            }
        })?;
        Ok((state, stored_pin))
    }

    /// Mark an annotation pin resolved locally with an optional resolution note.
    pub fn resolve_spatial_pin(
        &self,
        pin_id: &str,
        resolution_note: Option<String>,
    ) -> Result<InteractionState, BridgeError> {
        let now = utc_now_iso();
        self.update_interaction_state(|state| {
            if let Some(pin) = state.annotations.iter_mut().find(|p| p.id == pin_id) {
                pin.status = PinStatus::Resolved;
                if resolution_note.is_some() {
                    pin.resolution_note = resolution_note;
                }
                pin.updated_at = Some(now);
            }
        })
    }

    /// Update the live viewport snapshot (`model_path`, `color_by`, `camera`, `section`).
    pub fn update_viewport(&self, viewport: ViewportSnapshot) -> Result<InteractionState, BridgeError> {
        self.update_interaction_state(|state| {
            state.viewport = Some(viewport);
        })
    }

    /// Append a UI action intent to `pending_intents`.
    pub fn push_pending_intent(&self, mut intent: PendingIntent) -> Result<InteractionState, BridgeError> {
        if intent.created_at.is_none() {
            intent.created_at = Some(utc_now_iso());
        }
        self.update_interaction_state(|state| {
            state.pending_intents.push(intent);
        })
    }
}

/// Backward-compatible placeholder wrapper kept for skeleton callers.
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
