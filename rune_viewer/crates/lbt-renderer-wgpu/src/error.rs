//! Error types for the wgpu 3D building renderer.

use std::fmt;

/// Errors produced during GPU initialization, offscreen rendering, PNG encoding, or picking.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RendererError {
    /// No compatible GPU or software fallback adapter was available.
    NoAdapter(String),
    /// Device creation on the chosen adapter failed.
    DeviceRequest(String),
    /// Requested viewport width or height was zero or exceeded GPU texture limits.
    InvalidDimensions { width: u32, height: u32 },
    /// GPU readback buffer mapping failed.
    BufferMap(String),
    /// Device polling failed while waiting for GPU work.
    Poll(String),
    /// Encoding rendered RGBA bytes into a PNG image failed.
    PngEncode(String),
}

impl fmt::Display for RendererError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoAdapter(msg) => write!(f, "no compatible wgpu adapter found: {msg}"),
            Self::DeviceRequest(msg) => write!(f, "failed to create wgpu device: {msg}"),
            Self::InvalidDimensions { width, height } => {
                write!(f, "invalid render dimensions {width}x{height}")
            }
            Self::BufferMap(msg) => write!(f, "failed to map GPU readback buffer: {msg}"),
            Self::Poll(msg) => write!(f, "wgpu device poll failed: {msg}"),
            Self::PngEncode(msg) => write!(f, "failed to encode PNG image: {msg}"),
        }
    }
}

impl std::error::Error for RendererError {}
