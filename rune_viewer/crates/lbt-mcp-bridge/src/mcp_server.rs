//! Standalone stdio JSON-RPC 2.0 MCP server for headless `lbt-rune-viewer --mcp`.

use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::atomic::{utc_now_iso, write_bytes_atomic};

/// Supported MCP JSON-RPC protocol version advertised in `initialize`.
pub const MCP_PROTOCOL_VERSION: &str = "2024-11-05";

/// Parameters passed to `viewer_capture` / `viewer_set_camera`.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct McpCaptureOptions {
    #[serde(default)]
    pub output_path: Option<String>,
    #[serde(default)]
    pub view: Option<Value>,
    #[serde(default)]
    pub color_by: Option<String>,
    #[serde(default)]
    pub section_z: Option<f32>,
    #[serde(default)]
    pub width: Option<u32>,
    #[serde(default)]
    pub height: Option<u32>,
}

/// PNG capture output returned by [`McpViewerBackend::capture_png`].
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct McpCapturedPng {
    pub png_bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub view_label: String,
    pub color_by: String,
}

/// Scene summary returned by [`McpViewerBackend::load_hbjson`] and `inspect_scene`.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct McpSceneSummary {
    pub model_identifier: String,
    pub source_path: Option<String>,
    pub units: Option<String>,
    pub object_count: usize,
    pub vertex_count: usize,
    pub edge_vertex_count: usize,
    pub bounds_min: [f32; 3],
    pub bounds_max: [f32; 3],
    pub stories: Vec<String>,
}

/// Abstract viewer backend allowing standalone stdio MCP tests with or without GPU rendering.
pub trait McpViewerBackend {
    fn load_hbjson(&mut self, path: &Path) -> Result<McpSceneSummary, String>;
    fn inspect_scene(&self) -> Result<Value, String>;
    fn set_view_state(&mut self, opts: &McpCaptureOptions) -> Result<Value, String>;
    fn capture_png(&mut self, opts: &McpCaptureOptions) -> Result<McpCapturedPng, String>;
}

/// Stateless/in-memory JSON-RPC 2.0 MCP server around any [`McpViewerBackend`].
pub struct McpServer<B: McpViewerBackend> {
    backend: B,
    server_name: String,
    server_version: String,
}

impl<B: McpViewerBackend> McpServer<B> {
    /// Construct an MCP server wrapping `backend`.
    pub fn new(backend: B) -> Self {
        Self {
            backend,
            server_name: "lbt-rune-viewer".to_owned(),
            server_version: env!("CARGO_PKG_VERSION").to_owned(),
        }
    }

    /// Borrow the underlying backend.
    pub fn backend(&self) -> &B {
        &self.backend
    }

    /// Mutably borrow the underlying backend.
    pub fn backend_mut(&mut self) -> &mut B {
        &mut self.backend
    }

    /// Handle a single parsed JSON-RPC 2.0 message, returning `None` for notifications.
    pub fn handle_message(&mut self, msg: &Value) -> Option<Value> {
        let id = msg.get("id").cloned();
        let method = match msg.get("method").and_then(Value::as_str) {
            Some(m) => m,
            None => {
                return id.map(|req_id| json_rpc_error(req_id, -32600, "Missing JSON-RPC 'method'"));
            }
        };

        // Notifications have no `id` and expect no reply.
        if id.is_none() || id.as_ref() == Some(&Value::Null) {
            if method == "notifications/initialized" || method == "initialized" {
                return None;
            }
            return None;
        }
        let req_id = id.unwrap_or(Value::Null);
        let params = msg.get("params").cloned().unwrap_or_else(|| json!({}));

        match method {
            "initialize" => Some(json_rpc_ok(
                req_id,
                json!({
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": { "listChanged": false }
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.server_version,
                    }
                }),
            )),
            "ping" => Some(json_rpc_ok(req_id, json!({}))),
            "tools/list" => Some(json_rpc_ok(req_id, json!({ "tools": mcp_tool_definitions() }))),
            "tools/call" => {
                let Some(tool_name) = params.get("name").and_then(Value::as_str) else {
                    return Some(json_rpc_error(req_id, -32602, "tools/call requires params.name"));
                };
                let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));
                let call_result = self.call_tool(tool_name, &args);
                Some(json_rpc_ok(req_id, call_result))
            }
            other => Some(json_rpc_error(
                req_id,
                -32601,
                &format!("Method not found: {other}"),
            )),
        }
    }

    fn call_tool(&mut self, tool_name: &str, args: &Value) -> Value {
        match tool_name {
            "viewer_load_hbjson" => {
                let Some(raw_path) = args.get("path").and_then(Value::as_str) else {
                    return tool_error("viewer_load_hbjson requires 'path' string");
                };
                match self.backend.load_hbjson(Path::new(raw_path)) {
                    Ok(summary) => tool_json_ok(&json!({
                        "status": "ok",
                        "loaded": summary,
                    })),
                    Err(err) => tool_error(&err),
                }
            }
            "viewer_inspect" => match self.backend.inspect_scene() {
                Ok(info) => tool_json_ok(&info),
                Err(err) => tool_error(&err),
            },
            "viewer_set_camera" => {
                let opts = match serde_json::from_value::<McpCaptureOptions>(args.clone()) {
                    Ok(v) => v,
                    Err(err) => return tool_error(&format!("Invalid camera/view parameters: {err}")),
                };
                match self.backend.set_view_state(&opts) {
                    Ok(state) => tool_json_ok(&state),
                    Err(err) => tool_error(&err),
                }
            }
            "viewer_capture" => {
                let opts = match serde_json::from_value::<McpCaptureOptions>(args.clone()) {
                    Ok(v) => v,
                    Err(err) => return tool_error(&format!("Invalid capture parameters: {err}")),
                };
                match self.backend.capture_png(&opts) {
                    Ok(captured) => {
                        let written_path = if let Some(ref out_rel) = opts.output_path {
                            let out_path = PathBuf::from(out_rel);
                            if let Err(err) = write_bytes_atomic(&out_path, &captured.png_bytes) {
                                return tool_error(&format!("Failed writing capture PNG: {err}"));
                            }
                            Some(out_path.to_string_lossy().into_owned())
                        } else {
                            None
                        };
                        let meta = json!({
                            "status": "ok",
                            "width": captured.width,
                            "height": captured.height,
                            "view": captured.view_label,
                            "color_by": captured.color_by,
                            "bytes": captured.png_bytes.len(),
                            "output_path": written_path,
                            "captured_at": utc_now_iso(),
                        });
                        let b64 = encode_base64(&captured.png_bytes);
                        json!({
                            "isError": false,
                            "content": [
                                {
                                    "type": "text",
                                    "text": serde_json::to_string_pretty(&meta).unwrap_or_default()
                                },
                                {
                                    "type": "image",
                                    "data": b64,
                                    "mimeType": "image/png"
                                }
                            ]
                        })
                    }
                    Err(err) => tool_error(&err),
                }
            }
            other => tool_error(&format!("Unknown viewer MCP tool: {other}")),
        }
    }

    /// Run blocking stdio JSON-RPC loop supporting both newline-delimited JSON and `Content-Length` framing.
    pub fn serve_stdio(&mut self) -> io::Result<()> {
        let stdin = io::stdin();
        let stdout = io::stdout();
        let mut reader = BufReader::new(stdin.lock());
        let mut writer = io::BufWriter::new(stdout.lock());
        self.serve_streams(&mut reader, &mut writer)
    }

    /// Run JSON-RPC loop over arbitrary buffered streams (used in unit tests).
    pub fn serve_streams<R: BufRead, W: Write>(&mut self, reader: &mut R, writer: &mut W) -> io::Result<()> {
        while let Some((raw_msg, use_content_length)) = read_stdio_frame(reader)? {
            let reply = match serde_json::from_slice::<Value>(&raw_msg) {
                Ok(val) => self.handle_message(&val),
                Err(err) => Some(json_rpc_error(
                    Value::Null,
                    -32700,
                    &format!("JSON parse error: {err}"),
                )),
            };
            if let Some(resp) = reply {
                let encoded = serde_json::to_vec(&resp).unwrap_or_else(|_| b"{}".to_vec());
                if use_content_length {
                    write!(writer, "Content-Length: {}\r\n\r\n", encoded.len())?;
                    writer.write_all(&encoded)?;
                } else {
                    writer.write_all(&encoded)?;
                    writer.write_all(b"\n")?;
                }
                writer.flush()?;
            }
        }
        Ok(())
    }
}

/// Tool schema definitions exposed by `tools/list` in standalone `--mcp` mode.
pub fn mcp_tool_definitions() -> Value {
    json!([
        {
            "name": "viewer_load_hbjson",
            "description": "Load a Honeybee Model .hbjson file into the standalone Rune viewer scene.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": { "type": "string", "description": "Path to a Honeybee Model .hbjson file." }
                },
                "required": ["path"]
            }
        },
        {
            "name": "viewer_inspect",
            "description": "Inspect the currently loaded Honeybee scene summary (identifier, bounds, counts, stories).",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "viewer_set_camera",
            "description": "Set camera preset/pose, color_by attribute, or horizontal section cut height for subsequent captures.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "view": { "description": "Camera preset string (axon, top, north, south, east, west, fit) or {position, target} object." },
                    "color_by": { "type": "string", "description": "ColorBy mode (type, boundary_condition, story, zone, program_type, construction_set, hvac, wwr)." },
                    "section_z": { "type": "number", "description": "Optional horizontal Z section cut plane elevation in model units." }
                }
            }
        },
        {
            "name": "viewer_capture",
            "description": "Render an offscreen PNG snapshot of the currently loaded HBJSON scene and return metadata + image.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "output_path": { "type": "string", "description": "Optional path to write the rendered PNG file." },
                    "view": { "description": "Optional camera preset or {position, target} override." },
                    "color_by": { "type": "string", "description": "Optional ColorBy override." },
                    "section_z": { "type": "number", "description": "Optional Z section cut height override." },
                    "width": { "type": "integer", "minimum": 64, "maximum": 4096, "description": "Output PNG width in pixels (default 1280)." },
                    "height": { "type": "integer", "minimum": 64, "maximum": 4096, "description": "Output PNG height in pixels (default 720)." }
                }
            }
        }
    ])
}

fn json_rpc_ok(id: Value, result: Value) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result,
    })
}

fn json_rpc_error(id: Value, code: i32, message: &str) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message,
        }
    })
}

fn tool_json_ok(payload: &Value) -> Value {
    json!({
        "isError": false,
        "content": [
            {
                "type": "text",
                "text": serde_json::to_string_pretty(payload).unwrap_or_default()
            }
        ]
    })
}

fn tool_error(message: &str) -> Value {
    json!({
        "isError": true,
        "content": [
            {
                "type": "text",
                "text": message
            }
        ]
    })
}

fn read_stdio_frame<R: BufRead>(reader: &mut R) -> io::Result<Option<(Vec<u8>, bool)>> {
    let mut line = String::new();
    loop {
        line.clear();
        let n = reader.read_line(&mut line)?;
        if n == 0 {
            return Ok(None);
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Some(len_str) = trimmed
            .strip_prefix("Content-Length:")
            .or_else(|| trimmed.strip_prefix("content-length:"))
        {
            let content_len: usize = len_str.trim().parse().map_err(|err| {
                io::Error::new(io::ErrorKind::InvalidData, format!("Invalid Content-Length: {err}"))
            })?;
            // Drain remaining headers until blank line.
            loop {
                line.clear();
                let header_n = reader.read_line(&mut line)?;
                if header_n == 0 || line.trim().is_empty() {
                    break;
                }
            }
            let mut buf = vec![0u8; content_len];
            reader.read_exact(&mut buf)?;
            return Ok(Some((buf, true)));
        }
        return Ok(Some((trimmed.as_bytes().to_vec(), false)));
    }
}

/// Encode bytes into standard base64 without adding external crate dependencies.
pub fn encode_base64(input: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(input.len().div_ceil(3) * 4);
    for chunk in input.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = *chunk.get(1).unwrap_or(&0) as u32;
        let b2 = *chunk.get(2).unwrap_or(&0) as u32;
        let triple = (b0 << 16) | (b1 << 8) | b2;

        out.push(TABLE[((triple >> 18) & 0x3f) as usize] as char);
        out.push(TABLE[((triple >> 12) & 0x3f) as usize] as char);
        if chunk.len() > 1 {
            out.push(TABLE[((triple >> 6) & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(TABLE[(triple & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}
