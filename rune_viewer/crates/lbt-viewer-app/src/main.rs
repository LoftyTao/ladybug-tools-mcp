//! Native GPU desktop and headless HBJSON/Garden viewer powered by Rune and wgpu.

#![forbid(unsafe_code)]

#[cfg(target_arch = "wasm32")]
fn main() {}

#[cfg(not(target_arch = "wasm32"))]
mod cli;

#[cfg(not(target_arch = "wasm32"))]
use std::path::{Path, PathBuf};
#[cfg(not(target_arch = "wasm32"))]
use std::process::ExitCode;
#[cfg(not(target_arch = "wasm32"))]
use std::sync::Arc;
#[cfg(not(target_arch = "wasm32"))]
use std::sync::atomic::{AtomicBool, Ordering};
#[cfg(not(target_arch = "wasm32"))]
use std::time::{Duration, SystemTime};

#[cfg(not(target_arch = "wasm32"))]
use lbt_mcp_bridge::{
    GardenBridge, GardenWatcher, capture_request_path, present_path, run_default_mcp_stdio,
    write_bytes_atomic,
};
#[cfg(not(target_arch = "wasm32"))]
use lbt_scene::{
    CameraPreset, PROTOCOL_SCHEMA_VERSION, SceneData, SectionAxis, SectionSpec, load_hbjson_file,
};
#[cfg(not(target_arch = "wasm32"))]
use lbt_viewer_app::compositor::BuildingCompositor;
#[cfg(not(target_arch = "wasm32"))]
use lbt_viewer_app::engine::{SceneCameraBackend, WgpuViewerRenderer};
#[cfg(not(target_arch = "wasm32"))]
use lbt_viewer_app::state::{self, ViewerState};
#[cfg(not(target_arch = "wasm32"))]
use lbt_viewer_app::ui;
#[cfg(not(target_arch = "wasm32"))]
use rune::tooling::AppSpec;
#[cfg(not(target_arch = "wasm32"))]
use rune::{App, ColorScheme, Tx, Waker};

#[cfg(not(target_arch = "wasm32"))]
use crate::cli::{CliArgs, parse_args, usage_text};

#[cfg(not(target_arch = "wasm32"))]
fn load_hbjson_model(path: &Path, garden_id: Option<&str>) -> Result<SceneData, String> {
    load_hbjson_file(path, garden_id).map_err(|e| format!("Failed loading {}: {e}", path.display()))
}

#[cfg(not(target_arch = "wasm32"))]
fn file_stamp(path: &Path) -> Option<(SystemTime, u64)> {
    let meta = std::fs::metadata(path).ok()?;
    let modified = meta.modified().unwrap_or(SystemTime::UNIX_EPOCH);
    Some((modified, meta.len()))
}

#[cfg(not(target_arch = "wasm32"))]
fn run_headless_snap(cli: &CliArgs, snap_path: &Path) -> Result<(), String> {
    let gpu = WgpuViewerRenderer::new()?;
    let mut state = ViewerState::new(SceneData::default(), "Snapshot", Some(Box::new(gpu)));

    if let Some(hbjson_path) = &cli.hbjson {
        let scene = load_hbjson_model(hbjson_path, None)?;
        let label = scene
            .display_name
            .clone()
            .unwrap_or_else(|| scene.model_identifier.clone());
        state.model_label = label;
        state.model_path = Some(hbjson_path.to_string_lossy().into_owned());
        state.model_fingerprint = crate::state::file_fingerprint(hbjson_path);
        state.scene = scene;
        state.rebuild_scene_derived(true);
    } else if let Some(garden_root) = &cli.garden {
        let watcher = GardenWatcher::new(garden_root);
        let bridge = GardenBridge::new(garden_root);
        state.garden_root = Some(garden_root.clone());
        state.watcher = Some(watcher);
        state.bridge = Some(bridge);
        state.model_label = garden_root
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("Garden")
            .to_owned();

        if let Some(present) = state
            .watcher
            .as_ref()
            .expect("watcher")
            .read_present()
            .map_err(|e| format!("Failed reading present.json: {e}"))?
        {
            let gid = present.garden_id.clone();
            state.apply_present_command(&present, |p| load_hbjson_model(p, gid.as_deref()));
            state.load_initial_interaction_state();
        } else {
            state.load_initial_interaction_state();
            if let Some(model_path_str) = state.model_path.clone() {
                let candidate = PathBuf::from(&model_path_str);
                let resolved = if candidate.is_absolute() {
                    candidate
                } else {
                    garden_root.join(candidate)
                };
                if resolved.is_file() {
                    state.scene = load_hbjson_model(&resolved, state.garden_id.as_deref())?;
                    state.model_fingerprint = crate::state::file_fingerprint(&resolved);
                    state.rebuild_scene_derived(true);
                }
            }
        }
    }

    if let Some(color_by) = cli.color_by {
        state.color_by = color_by;
    }
    if let Some(z) = cli.section_z {
        state.section = SectionSpec {
            enabled: true,
            axis: SectionAxis::Z,
            value: Some(z),
            story: None,
            invert: false,
        };
    }
    state.sync_render_state();

    if let Some(preset) = cli.view {
        let hi_bounds = state.active_highlight_bounds();
        state
            .renderer
            .apply_camera_preset(preset, state.scene.bounds, hi_bounds);
    } else if cli.hbjson.is_some() {
        state
            .renderer
            .apply_camera_preset(CameraPreset::Axon, state.scene.bounds, None);
    }

    let png_bytes = state.renderer.render_png(cli.width, cli.height)?;
    write_bytes_atomic(snap_path, &png_bytes)
        .map_err(|e| format!("Failed writing snapshot {}: {e}", snap_path.display()))?;
    Ok(())
}

#[cfg(not(target_arch = "wasm32"))]
fn build_initial_gui_state(cli: &CliArgs) -> Result<ViewerState, String> {
    let gpu = SceneCameraBackend::new();

    if let Some(hbjson_path) = &cli.hbjson {
        let scene = load_hbjson_model(hbjson_path, None)?;
        let label = scene
            .display_name
            .clone()
            .unwrap_or_else(|| scene.model_identifier.clone());
        let mut state = ViewerState::new(scene, label, Some(Box::new(gpu)));
        state.use_compositor = true;
        state.model_path = Some(hbjson_path.to_string_lossy().into_owned());
        state.model_fingerprint = state::file_fingerprint(hbjson_path);
        if let Some(cb) = cli.color_by {
            state.color_by = cb;
        }
        if let Some(z) = cli.section_z {
            state.section = SectionSpec {
                enabled: true,
                axis: SectionAxis::Z,
                value: Some(z),
                story: None,
                invert: false,
            };
        }
        state.sync_render_state();
        if let Some(preset) = cli.view {
            state.apply_camera_preset(preset);
        } else {
            state.render_viewport_now();
        }
        return Ok(state);
    }

    if let Some(garden_root) = &cli.garden {
        let mut watcher = GardenWatcher::new(garden_root);
        let bridge = GardenBridge::new(garden_root);
        let _ = bridge.set_viewer_pid(Some(std::process::id()));
        let garden_label = garden_root
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("Garden")
            .to_owned();

        let mut state = ViewerState::new(SceneData::default(), garden_label, Some(Box::new(gpu)));
        state.use_compositor = true;
        state.garden_root = Some(garden_root.clone());
        state.bridge = Some(bridge);

        let initial_present = watcher.poll_present().ok().flatten();
        state.watcher = Some(watcher);
        if let Some(cmd) = initial_present {
            let gid = cmd.garden_id.clone();
            state.apply_present_command(&cmd, |p| load_hbjson_model(p, gid.as_deref()));
        }
        state.load_initial_interaction_state();

        if let Some(cb) = cli.color_by {
            state.color_by = cb;
        }
        if let Some(z) = cli.section_z {
            state.section = SectionSpec {
                enabled: true,
                axis: SectionAxis::Z,
                value: Some(z),
                story: None,
                invert: false,
            };
        }
        state.sync_render_state();
        if let Some(preset) = cli.view {
            state.apply_camera_preset(preset);
        } else {
            state.render_viewport_now();
        }
        return Ok(state);
    }

    let mut state = ViewerState::new(
        SceneData::default(),
        "Honeybee 3D Viewer",
        Some(Box::new(gpu)),
    );
    state.use_compositor = true;
    Ok(state)
}

#[cfg(not(target_arch = "wasm32"))]
fn setup_garden_watcher(s: &mut ViewerState, waker: Waker) {
    let Some(root) = s.garden_root.clone() else {
        return;
    };
    let stop = Arc::new(AtomicBool::new(false));
    s.garden_stop = Some(stop.clone());

    let present_file = present_path(&root);
    let capture_file = capture_request_path(&root);
    let _ = std::thread::Builder::new()
        .name("lbt-garden-watch".to_owned())
        .spawn(move || {
            let mut last_present = file_stamp(&present_file);
            let mut last_capture = file_stamp(&capture_file);
            while !stop.load(Ordering::Relaxed) {
                std::thread::sleep(Duration::from_millis(120));
                if stop.load(Ordering::Relaxed) {
                    break;
                }
                let cur_present = file_stamp(&present_file);
                let cur_capture = file_stamp(&capture_file);
                if cur_present != last_present || cur_capture != last_capture {
                    last_present = cur_present;
                    last_capture = cur_capture;
                    (waker)();
                }
            }
        });
}

#[cfg(not(target_arch = "wasm32"))]
fn poll_viewer(s: &mut ViewerState, now_secs: f64, tx: &mut Tx) -> bool {
    let mut ui_changed = false;

    if let Some(due) = s.camera_flush_due {
        if due == 0.0 {
            s.camera_flush_due = Some(now_secs + 0.25);
            tx.wake_after(Duration::from_millis(260));
        } else if now_secs >= due {
            s.flush_interaction_state();
        }
    }

    if let Some(mut watcher) = s.watcher.take() {
        let next_present = watcher.poll_present().ok().flatten();
        s.watcher = Some(watcher);
        if let Some(cmd) = next_present {
            let gid = cmd.garden_id.clone();
            s.apply_present_command(&cmd, |p| load_hbjson_model(p, gid.as_deref()));
            ui_changed = true;
        }
    }

    if let Some(mut watcher) = s.watcher.take() {
        let cap_req = watcher.poll_capture_request().ok().flatten();
        s.watcher = Some(watcher);
        if let Some(req) = cap_req {
            s.answer_capture_request(&req);
        }
    }

    ui_changed
}

#[cfg(not(target_arch = "wasm32"))]
fn dummy_init() -> ViewerState {
    ViewerState::new(SceneData::default(), "Honeybee 3D Viewer", None)
}

#[cfg(not(target_arch = "wasm32"))]
fn run_gui(cli: &CliArgs) -> Result<(), String> {
    let initial = build_initial_gui_state(cli)?;

    let spec = AppSpec {
        setup: Some(setup_garden_watcher),
        poll: Some(poll_viewer),
        on_key: Some(ui::on_window_key),
        ..AppSpec::new("Honeybee 3D Viewer", (1280.0, 800.0), dummy_init, ui::view)
    };

    let mut app = App::new(spec)
        .init(move || initial)
        .color_scheme(ColorScheme::Dark)
        .compositor(BuildingCompositor::new())
        .on_close(|s, _| s.shutdown_garden())
        .on_quit(|s, _| s.shutdown_garden());

    if !cli.rune_args.is_empty() {
        app = app.args(cli.rune_args.clone());
    }

    app.run();
    Ok(())
}

#[cfg(not(target_arch = "wasm32"))]
fn main() -> ExitCode {
    let raw_args: Vec<String> = std::env::args().skip(1).collect();
    let cli = match parse_args(&raw_args) {
        Ok(args) => args,
        Err(err) => {
            eprintln!("error: {err}");
            return ExitCode::from(2);
        }
    };

    if cli.show_version {
        println!(
            "lbt-rune-viewer {} (protocol v{})",
            env!("CARGO_PKG_VERSION"),
            PROTOCOL_SCHEMA_VERSION
        );
        return ExitCode::SUCCESS;
    }

    if cli.show_help {
        println!("{}", usage_text());
        return ExitCode::SUCCESS;
    }

    let result = if cli.mcp_mode {
        run_default_mcp_stdio(cli.hbjson.as_deref())
    } else if let Some(snap_path) = &cli.snap {
        run_headless_snap(&cli, snap_path)
    } else {
        run_gui(&cli)
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("lbt-rune-viewer error: {err}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use lbt_mcp_bridge::{capture_request_path, interaction_state_path, present_path, write_json_atomic};
    use lbt_scene::{CaptureRequest, ColorBy, IsolationMode, PresentCommand};
    use rune::{Env, Runtime};

    use super::*;

    fn temp_garden(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("lbt_viewer_app_{tag}_{}_{nanos}", std::process::id()));
        std::fs::create_dir_all(dir.join("models")).unwrap();
        dir
    }

    #[test]
    fn garden_poll_handles_present_capture_request_and_interaction_flush() {
        let root = temp_garden("sync");
        let sample_hbjson = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("..")
            .join("resources")
            .join("honeybee-core")
            .join("tests")
            .join("json")
            .join("single_family_home.hbjson");
        let model_rel = "models/single_family_home.hbjson";
        std::fs::copy(&sample_hbjson, root.join(model_rel)).unwrap();

        let present = PresentCommand {
            revision: 7,
            garden_id: Some("test_garden".to_owned()),
            model_path: Some(model_rel.to_owned()),
            color_by: ColorBy::Story,
            isolation_mode: IsolationMode::GhostContext,
            title: Some("Inspection".to_owned()),
            ..Default::default()
        };
        write_json_atomic(&present_path(&root), &present).unwrap();

        let mut state = ViewerState::new(SceneData::default(), "Garden", None);
        state.garden_root = Some(root.clone());
        state.watcher = Some(GardenWatcher::new(&root));
        let bridge = GardenBridge::new(&root);
        let _ = bridge.set_viewer_pid(Some(std::process::id()));
        state.bridge = Some(bridge);

        let mut rt = Runtime::new(state, ui::view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.poll = Some(poll_viewer);
        rt.frame(0.0);
        rt.frame(0.0);

        assert_eq!(rt.state.present_revision, 7);
        assert_eq!(rt.state.color_by, ColorBy::Story);
        assert_eq!(rt.state.isolation_mode, IsolationMode::GhostContext);
        assert!(!rt.state.scene.objects.is_empty());

        // Trigger selection flush & capture_request handshake
        let first_id = rt.state.scene.objects[0].object_id;
        rt.update(|s, _| s.select_object(first_id, false, false));
        rt.frame(0.0);

        let saved_interaction = lbt_mcp_bridge::read_json_if_exists::<lbt_scene::InteractionState>(
            &interaction_state_path(&root),
        )
        .unwrap()
        .expect("interaction_state.json written");
        assert_eq!(saved_interaction.selected_targets.len(), 1);

        let req = CaptureRequest {
            request_id: "cap_ui_1".to_owned(),
            output_png_path: Some("tmp/web_view/captures/cap_ui_1.png".to_owned()),
            receipt_path: Some("tmp/web_view/captures/cap_ui_1.json".to_owned()),
            width: 320,
            height: 240,
            ..Default::default()
        };
        write_json_atomic(&capture_request_path(&root), &req).unwrap();
        rt.frame(0.1);

        assert!(root.join("tmp/web_view/captures/cap_ui_1.png").is_file());
        let receipt = lbt_mcp_bridge::read_json_if_exists::<lbt_scene::CaptureReceipt>(
            &root.join("tmp/web_view/captures/cap_ui_1.json"),
        )
        .unwrap()
        .expect("receipt written");
        assert_eq!(receipt.status, "ok");

        rt.update(|s, _| s.shutdown_garden());
        let final_interaction = lbt_mcp_bridge::read_json_if_exists::<lbt_scene::InteractionState>(
            &interaction_state_path(&root),
        )
        .unwrap()
        .unwrap();
        assert_eq!(final_interaction.viewer_pid, None);

        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn garden_poll_reloads_modified_hbjson_in_place_and_keeps_camera() {
        let root = temp_garden("inplace_reload");
        let json_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("..")
            .join("resources")
            .join("honeybee-core")
            .join("tests")
            .join("json");
        let model_v1 = json_dir.join("room_for_envelope_edges.hbjson");
        let model_v2 = json_dir.join("single_family_home.hbjson");
        let model_rel = "models/model.hbjson";
        let model_abs = root.join(model_rel);
        std::fs::copy(&model_v1, &model_abs).unwrap();

        let present1 = PresentCommand {
            revision: 1,
            garden_id: Some("test_garden".to_owned()),
            model_path: Some(model_rel.to_owned()),
            camera: lbt_scene::CameraSpec::fit(),
            ..Default::default()
        };
        write_json_atomic(&present_path(&root), &present1).unwrap();

        let mut state = ViewerState::new(SceneData::default(), "Garden", None);
        state.garden_root = Some(root.clone());
        state.watcher = Some(GardenWatcher::new(&root));
        state.bridge = Some(GardenBridge::new(&root));

        let mut rt = Runtime::new(state, ui::view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.poll = Some(poll_viewer);
        rt.frame(0.0);
        rt.frame(0.0);

        let initial_objects = rt.state.scene.objects.len();
        assert!(initial_objects > 0);
        assert_eq!(
            rt.state.model_fingerprint,
            state::file_fingerprint(&model_abs)
        );

        // User orbits/zooms camera manually before the agent edits the same file in place.
        rt.update(|s, _| {
            s.renderer.orbit_pixels(45.0, -20.0, 0.01);
            s.renderer.zoom_factor(0.7);
        });
        let pose_before = rt.state.renderer.camera_pose();

        std::fs::copy(&model_v2, &model_abs).unwrap();
        let present2 = PresentCommand {
            revision: 2,
            garden_id: Some("test_garden".to_owned()),
            model_path: Some(model_rel.to_owned()),
            camera: lbt_scene::CameraSpec::keep(),
            ..Default::default()
        };
        write_json_atomic(&present_path(&root), &present2).unwrap();
        rt.frame(0.0);

        assert_eq!(rt.state.present_revision, 2);
        assert_ne!(rt.state.scene.objects.len(), initial_objects);
        assert_eq!(
            rt.state.model_fingerprint,
            state::file_fingerprint(&model_abs)
        );

        let pose_after = rt.state.renderer.camera_pose();
        for i in 0..3 {
            assert!(
                (pose_after.position[i] - pose_before.position[i]).abs() < 1e-4,
                "camera position[{i}] changed on in-place reload: {pose_before:?} vs {pose_after:?}"
            );
            assert!(
                (pose_after.target[i] - pose_before.target[i]).abs() < 1e-4,
                "camera target[{i}] changed on in-place reload: {pose_before:?} vs {pose_after:?}"
            );
        }

        let _ = std::fs::remove_dir_all(&root);
    }
}
