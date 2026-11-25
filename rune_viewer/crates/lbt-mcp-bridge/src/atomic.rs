//! Atomic file I/O, Garden path containment, and UTC timestamps.

use std::fmt;
use std::fs;
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use serde::de::DeserializeOwned;

static TMP_COUNTER: AtomicU64 = AtomicU64::new(1);

/// Errors returned by atomic Garden bridge file operations.
#[derive(Debug)]
pub enum BridgeError {
    Io(io::Error),
    Json(serde_json::Error),
    InvalidPath(String),
    Protocol(String),
}

impl fmt::Display for BridgeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(err) => write!(f, "I/O error: {err}"),
            Self::Json(err) => write!(f, "JSON error: {err}"),
            Self::InvalidPath(msg) => write!(f, "Invalid Garden path: {msg}"),
            Self::Protocol(msg) => write!(f, "Protocol error: {msg}"),
        }
    }
}

impl std::error::Error for BridgeError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(err) => Some(err),
            Self::Json(err) => Some(err),
            Self::InvalidPath(_) | Self::Protocol(_) => None,
        }
    }
}

impl From<io::Error> for BridgeError {
    fn from(err: io::Error) -> Self {
        Self::Io(err)
    }
}

impl From<serde_json::Error> for BridgeError {
    fn from(err: serde_json::Error) -> Self {
        Self::Json(err)
    }
}

/// Format current UTC wall-clock time as compact ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
pub fn utc_now_iso() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    format_unix_seconds_iso(secs)
}

/// Format a UNIX epoch timestamp in seconds as `YYYY-MM-DDTHH:MM:SSZ`.
pub fn format_unix_seconds_iso(secs: u64) -> String {
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let hour = rem / 3_600;
    let minute = (rem % 3_600) / 60;
    let second = rem % 60;

    // Howard Hinnant's civil-from-days algorithm in UTC.
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = y + i64::from(m <= 2);

    format!("{year:04}-{m:02}-{d:02}T{hour:02}:{minute:02}:{second:02}Z")
}

/// Resolve a Garden-relative POSIX/native path and guarantee it remains inside `garden_root`.
pub fn resolve_contained_path(garden_root: &Path, relative_path: &str) -> Result<PathBuf, BridgeError> {
    let trimmed = relative_path.trim();
    if trimmed.is_empty() {
        return Err(BridgeError::InvalidPath("path must not be empty".to_owned()));
    }
    let normalized = trimmed.replace('\\', "/");
    if normalized.starts_with('/') || normalized.starts_with("//") {
        return Err(BridgeError::InvalidPath(format!(
            "path must be Garden-relative, got {relative_path:?}"
        )));
    }
    if normalized.as_bytes().get(1) == Some(&b':') {
        return Err(BridgeError::InvalidPath(format!(
            "drive-prefixed paths are forbidden: {relative_path:?}"
        )));
    }

    let mut rel = PathBuf::new();
    for segment in normalized.split('/') {
        if segment.is_empty() || segment == "." || segment == ".." {
            return Err(BridgeError::InvalidPath(format!(
                "path contains invalid component {segment:?} in {relative_path:?}"
            )));
        }
        rel.push(segment);
    }

    let candidate = garden_root.join(&rel);
    for comp in rel.components() {
        if !matches!(comp, Component::Normal(_)) {
            return Err(BridgeError::InvalidPath(format!(
                "non-normal path component in {relative_path:?}"
            )));
        }
    }
    if let (Ok(canon_root), Ok(canon_cand)) = (garden_root.canonicalize(), candidate.canonicalize()) {
        if !canon_cand.starts_with(&canon_root) {
            return Err(BridgeError::InvalidPath(format!(
                "resolved path escapes Garden root: {relative_path:?}"
            )));
        }
    }
    Ok(candidate)
}

/// Atomically write raw bytes via a sibling temp file and rename/replace with Windows retry.
pub fn write_bytes_atomic(path: &Path, bytes: &[u8]) -> Result<(), BridgeError> {
    let parent = path.parent().ok_or_else(|| {
        BridgeError::InvalidPath(format!("target path has no parent directory: {}", path.display()))
    })?;
    fs::create_dir_all(parent)?;

    let seq = TMP_COUNTER.fetch_add(1, Ordering::Relaxed);
    let tmp_name = format!(".lbt-{}-{seq}.tmp", std::process::id());
    let tmp_path = parent.join(tmp_name);

    let write_res = (|| -> io::Result<()> {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp_path)?;
        file.write_all(bytes)?;
        file.flush()?;
        drop(file);

        for attempt in 0..6 {
            match fs::rename(&tmp_path, path) {
                Ok(()) => return Ok(()),
                Err(err) if cfg!(windows) && attempt < 5 && err.kind() == io::ErrorKind::PermissionDenied => {
                    thread::sleep(Duration::from_millis(15 * (attempt + 1) as u64));
                }
                Err(err) if cfg!(windows) && err.kind() == io::ErrorKind::AlreadyExists => {
                    // On older/certain Windows filesystems rename may report AlreadyExists.
                    let _ = fs::remove_file(path);
                }
                Err(err) => return Err(err),
            }
        }
        fs::rename(&tmp_path, path)
    })();

    if let Err(err) = write_res {
        let _ = fs::remove_file(&tmp_path);
        return Err(BridgeError::Io(err));
    }
    Ok(())
}

/// Atomically serialize `value` as pretty UTF-8 JSON with a trailing newline.
pub fn write_json_atomic<T: Serialize>(path: &Path, value: &T) -> Result<(), BridgeError> {
    let mut bytes = serde_json::to_vec_pretty(value)?;
    bytes.push(b'\n');
    write_bytes_atomic(path, &bytes)
}

/// Read and deserialize a JSON file if it exists, retrying briefly on transient atomic-replace races.
pub fn read_json_if_exists<T: DeserializeOwned>(path: &Path) -> Result<Option<T>, BridgeError> {
    for attempt in 0..4 {
        let raw = match fs::read(path) {
            Ok(data) => data,
            Err(err) if err.kind() == io::ErrorKind::NotFound => return Ok(None),
            Err(err) if cfg!(windows) && attempt < 3 && err.kind() == io::ErrorKind::PermissionDenied => {
                thread::sleep(Duration::from_millis(15 * (attempt + 1) as u64));
                continue;
            }
            Err(err) => return Err(BridgeError::Io(err)),
        };

        if raw.is_empty() && attempt < 3 {
            thread::sleep(Duration::from_millis(15 * (attempt + 1) as u64));
            continue;
        }
        match serde_json::from_slice::<T>(&raw) {
            Ok(parsed) => return Ok(Some(parsed)),
            Err(_) if attempt < 3 => {
                thread::sleep(Duration::from_millis(15 * (attempt + 1) as u64));
            }
            Err(err) => return Err(BridgeError::Json(err)),
        }
    }
    Ok(None)
}
