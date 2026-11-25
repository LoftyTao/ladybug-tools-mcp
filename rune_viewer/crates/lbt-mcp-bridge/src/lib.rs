//! File-based MCP bridge (`<garden>/tmp/web_view/`) and standalone stdio MCP server.

pub mod atomic;
pub mod mcp_server;
pub mod watcher;
pub mod wgpu_backend;

pub use atomic::{
    BridgeError, format_unix_seconds_iso, read_json_if_exists, resolve_contained_path, utc_now_iso,
    write_bytes_atomic, write_json_atomic,
};
pub use mcp_server::{
    MCP_PROTOCOL_VERSION, McpCaptureOptions, McpCapturedPng, McpSceneSummary, McpServer,
    McpViewerBackend, encode_base64, mcp_tool_definitions,
};
pub use watcher::{
    CAPTURES_DIR_REL, GardenBridge, GardenBridgeStub, GardenWatcher, WEB_VIEW_DIR_REL,
    capture_request_path, captures_dir, interaction_state_path, present_path, web_view_dir,
};
pub use wgpu_backend::{WgpuMcpBackend, run_default_mcp_stdio};

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::io::Cursor;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    use lbt_scene::{
        CameraSpec, CaptureRequest, ColorBy, InteractionState, ObjectKind, ObjectTargetRef,
        PresentCommand, SpatialPin, ViewType,
    };
    use serde_json::{Value, json};

    use super::*;

    fn temp_test_dir(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("lbt_mcp_bridge_{tag}_{}_{nanos}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn rejects_escaping_garden_paths() {
        let root = temp_test_dir("paths");
        assert!(resolve_contained_path(&root, "../secret.json").is_err());
        assert!(resolve_contained_path(&root, "/etc/passwd").is_err());
        assert!(resolve_contained_path(&root, "C:\\temp\\bad.json").is_err());
        assert!(resolve_contained_path(&root, "").is_err());
        let ok = resolve_contained_path(&root, "models/honeybee/test.hbjson").unwrap();
        assert!(ok.ends_with(PathBuf::from("models").join("honeybee").join("test.hbjson")));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn watcher_polls_present_revisions_and_answers_capture_handshake() {
        let root = temp_test_dir("watcher");
        let mut watcher = GardenWatcher::new(&root);

        assert!(watcher.poll_present().unwrap().is_none());

        let present1 = PresentCommand {
            revision: 1,
            garden_id: Some("g1".into()),
            view_type: ViewType::Model,
            model_path: Some("models/honeybee/m.hbjson".into()),
            color_by: ColorBy::Type,
            camera: CameraSpec::fit(),
            ..Default::default()
        };
        write_json_atomic(&present_path(&root), &present1).unwrap();

        let seen1 = watcher.poll_present().unwrap().expect("revision 1 should arrive");
        assert_eq!(seen1.revision, 1);
        assert_eq!(
            watcher.resolve_model_path(&seen1).unwrap().unwrap(),
            root.join("models").join("honeybee").join("m.hbjson")
        );
        // Polling again without a revision bump returns None.
        assert!(watcher.poll_present().unwrap().is_none());

        let mut present2 = present1.clone();
        present2.revision = 2;
        present2.color_by = ColorBy::Wwr;
        write_json_atomic(&present_path(&root), &present2).unwrap();
        let seen2 = watcher.poll_present().unwrap().expect("revision 2 should arrive");
        assert_eq!(seen2.color_by, ColorBy::Wwr);

        // Capture handshake: write capture_request.json -> watcher polls -> writes PNG + CaptureReceipt.
        let req = CaptureRequest {
            request_id: "cap_test_01".into(),
            output_png_path: Some("tmp/web_view/captures/cap_test_01.png".into()),
            receipt_path: Some("tmp/web_view/captures/cap_test_01.json".into()),
            width: 320,
            height: 240,
            ..Default::default()
        };
        write_json_atomic(&capture_request_path(&root), &req).unwrap();

        let polled_req = watcher.poll_capture_request().unwrap().expect("capture request should arrive");
        assert_eq!(polled_req.request_id, "cap_test_01");

        let fake_png = [137u8, 80, 78, 71, 13, 10, 26, 10];
        let receipt = watcher
            .write_capture_result(
                &polled_req,
                &fake_png,
                320,
                240,
                Some("models/honeybee/m.hbjson".into()),
                Some(2),
            )
            .unwrap();
        assert_eq!(receipt.status, "ok");
        assert!(root.join("tmp/web_view/captures/cap_test_01.png").is_file());
        assert!(root.join("tmp/web_view/captures/cap_test_01.json").is_file());
        // Already answered request must not fire a second time.
        assert!(watcher.poll_capture_request().unwrap().is_none());

        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn garden_bridge_updates_interaction_state_atomically() {
        let root = temp_test_dir("bridge");
        let bridge = GardenBridge::with_garden_id(&root, "g_test");

        bridge.set_viewer_pid(Some(12345)).unwrap();
        let target = ObjectTargetRef::new(Some("g_test".into()), "office", ObjectKind::Aperture, "Ap_South");
        bridge.set_selected_targets(vec![target.clone()]).unwrap();
        let (_, pin) = bridge
            .upsert_spatial_pin(SpatialPin {
                id: "pin_1".into(),
                target: Some(target.clone()),
                world_point: Some([1.0, 2.0, 3.0]),
                comment: "Add louver".into(),
                ..Default::default()
            })
            .unwrap();
        assert_eq!(pin.id, "pin_1");

        let state: InteractionState = bridge.read_interaction_state().unwrap().unwrap();
        assert_eq!(state.garden_id.as_deref(), Some("g_test"));
        assert_eq!(state.viewer_pid, Some(12345));
        assert_eq!(state.selected_targets, vec![target]);
        assert_eq!(state.annotations.len(), 1);
        assert_eq!(state.annotations[0].comment, "Add louver");

        bridge
            .resolve_spatial_pin("pin_1", Some("Resolved in test".into()))
            .unwrap();
        let after = bridge.read_interaction_state().unwrap().unwrap();
        assert_eq!(after.annotations[0].status, lbt_scene::PinStatus::Resolved);
        assert_eq!(after.annotations[0].resolution_note.as_deref(), Some("Resolved in test"));

        let _ = std::fs::remove_dir_all(&root);
    }

    struct MockMcpBackend {
        loaded: Option<McpSceneSummary>,
        view_state: BTreeMap<String, Value>,
    }

    impl McpViewerBackend for MockMcpBackend {
        fn load_hbjson(&mut self, path: &Path) -> Result<McpSceneSummary, String> {
            let summary = McpSceneSummary {
                model_identifier: "mock_model".into(),
                source_path: Some(path.to_string_lossy().into_owned()),
                units: Some("Meters".into()),
                object_count: 12,
                vertex_count: 48,
                edge_vertex_count: 24,
                bounds_min: [0.0, 0.0, 0.0],
                bounds_max: [6.0, 5.0, 3.0],
                stories: vec!["Ground".into()],
            };
            self.loaded = Some(summary.clone());
            Ok(summary)
        }

        fn inspect_scene(&self) -> Result<Value, String> {
            let summary = self.loaded.as_ref().ok_or_else(|| "No scene loaded".to_owned())?;
            Ok(json!({ "loaded": summary, "view_state": self.view_state }))
        }

        fn set_view_state(&mut self, opts: &McpCaptureOptions) -> Result<Value, String> {
            if let Some(ref view) = opts.view {
                self.view_state.insert("view".into(), view.clone());
            }
            if let Some(ref color_by) = opts.color_by {
                self.view_state.insert("color_by".into(), json!(color_by));
            }
            Ok(json!({ "status": "ok", "view_state": self.view_state }))
        }

        fn capture_png(&mut self, opts: &McpCaptureOptions) -> Result<McpCapturedPng, String> {
            if self.loaded.is_none() {
                return Err("No model loaded".to_owned());
            }
            Ok(McpCapturedPng {
                png_bytes: vec![137, 80, 78, 71, 13, 10, 26, 10],
                width: opts.width.unwrap_or(1280),
                height: opts.height.unwrap_or(720),
                view_label: "axon".into(),
                color_by: opts.color_by.clone().unwrap_or_else(|| "type".into()),
            })
        }
    }

    #[test]
    fn mcp_stdio_server_handles_initialize_list_load_and_capture() {
        let root = temp_test_dir("mcp_stdio");
        let out_png = root.join("shot.png");
        let input_lines = [
            json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).to_string(),
            json!({"jsonrpc": "2.0", "method": "notifications/initialized"}).to_string(),
            json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).to_string(),
            json!({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "viewer_load_hbjson", "arguments": {"path": "sample.hbjson"}}
            })
            .to_string(),
            json!({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "viewer_capture",
                    "arguments": {"output_path": out_png.to_string_lossy(), "width": 640, "height": 480}
                }
            })
            .to_string(),
        ]
        .join("\n")
            + "\n";

        let mut reader = Cursor::new(input_lines.as_bytes());
        let mut out_buf = Vec::new();
        let mut server = McpServer::new(MockMcpBackend {
            loaded: None,
            view_state: BTreeMap::new(),
        });
        server.serve_streams(&mut reader, &mut out_buf).unwrap();

        let output = String::from_utf8(out_buf).unwrap();
        let responses: Vec<Value> = output
            .lines()
            .filter(|line| !line.trim().is_empty())
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(responses.len(), 4);
        assert_eq!(responses[0]["id"], 1);
        assert_eq!(responses[0]["result"]["protocolVersion"], MCP_PROTOCOL_VERSION);
        assert_eq!(responses[1]["id"], 2);
        let tools = responses[1]["result"]["tools"].as_array().unwrap();
        assert!(tools.iter().any(|t| t["name"] == "viewer_load_hbjson"));
        assert!(tools.iter().any(|t| t["name"] == "viewer_capture"));
        assert_eq!(responses[2]["id"], 3);
        assert_eq!(responses[2]["result"]["isError"], false);
        assert_eq!(responses[3]["id"], 4);
        assert_eq!(responses[3]["result"]["isError"], false);
        assert!(out_png.is_file());

        // Also verify Content-Length LSP-style stdio framing works.
        let ping = json!({"jsonrpc": "2.0", "id": 9, "method": "ping"}).to_string();
        let framed = format!("Content-Length: {}\r\n\r\n{}", ping.len(), ping);
        let mut framed_reader = Cursor::new(framed.as_bytes());
        let mut framed_out = Vec::new();
        server.serve_streams(&mut framed_reader, &mut framed_out).unwrap();
        let framed_text = String::from_utf8(framed_out).unwrap();
        assert!(framed_text.starts_with("Content-Length: "));
        assert!(framed_text.contains("\"id\":9"));

        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn wgpu_mcp_backend_loads_real_hbjson_and_captures_valid_png() {
        let repo_root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .parent()
            .unwrap();
        let sample = repo_root
            .join("resources")
            .join("honeybee-core")
            .join("tests")
            .join("json")
            .join("single_family_home.hbjson");
        assert!(sample.is_file(), "Missing sample HBJSON: {}", sample.display());

        let root = temp_test_dir("wgpu_mcp");
        let out_png = root.join("home_axon.png");
        let msgs = [
            json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).to_string(),
            json!({"jsonrpc": "2.0", "method": "notifications/initialized"}).to_string(),
            json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).to_string(),
            json!({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "viewer_load_hbjson",
                    "arguments": {"path": sample.to_string_lossy()}
                }
            })
            .to_string(),
            json!({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "viewer_capture",
                    "arguments": {
                        "output_path": out_png.to_string_lossy(),
                        "view": "axon",
                        "color_by": "boundary_condition",
                        "width": 320,
                        "height": 240
                    }
                }
            })
            .to_string(),
        ]
        .join("\n")
            + "\n";

        let mut reader = Cursor::new(msgs.as_bytes());
        let mut out_buf = Vec::new();
        let mut server = McpServer::new(WgpuMcpBackend::new());
        server.serve_streams(&mut reader, &mut out_buf).unwrap();

        let output = String::from_utf8(out_buf).unwrap();
        let responses: Vec<Value> = output
            .lines()
            .filter(|line| !line.trim().is_empty())
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(responses.len(), 4);
        assert_eq!(responses[2]["result"]["isError"], false);
        assert_eq!(responses[3]["result"]["isError"], false);
        assert!(out_png.is_file());
        let png_bytes = std::fs::read(&out_png).unwrap();
        assert!(png_bytes.starts_with(&[137, 80, 78, 71, 13, 10, 26, 10]));
        assert!(png_bytes.len() > 1024);

        let _ = std::fs::remove_dir_all(&root);
    }
}
