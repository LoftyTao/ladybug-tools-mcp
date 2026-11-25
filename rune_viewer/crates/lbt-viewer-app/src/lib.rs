//! Library root for `lbt-viewer-app`: exports bilingual studio UI, embedded Ladybug Tools
//! icon system, zero-readback Rune `Compositor`, and browser WASM entry point (`start`).

#![forbid(unsafe_code)]

pub mod compositor;
pub mod engine;
pub mod i18n;
pub mod icons;
pub mod outliner;
pub mod state;
pub mod theme;
pub mod ui;
#[cfg(target_arch = "wasm32")]
pub mod web_sync;

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console, js_name = error)]
    fn web_console_error(msg: &str);
}

#[cfg(target_arch = "wasm32")]
fn web_initial_state() -> state::ViewerState {
    let locale = i18n::detect_browser_locale();
    let tr = i18n::tr(locale);
    let mut st = state::ViewerState::new_compositor(lbt_scene::SceneData::default(), tr.app_title);
    st.set_locale(locale);
    st
}

#[cfg(target_arch = "wasm32")]
fn web_poll(s: &mut state::ViewerState, now_secs: f64, tx: &mut rune::Tx) -> bool {
    if let Some(due) = s.camera_flush_due {
        if due == 0.0 {
            s.camera_flush_due = Some(now_secs + 0.25);
            tx.wake_after(std::time::Duration::from_millis(260));
        } else if now_secs >= due {
            s.flush_interaction_state();
        }
    }
    false
}

/// Browser WASM entry point mounting Rune's WebGPU/WebGL2 Web View onto the page.
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let mut spec = rune::AppSpec::new(
        "Honeybee 3D Viewer",
        (1280.0, 800.0),
        web_initial_state,
        ui::view,
    );
    spec.poll = Some(web_poll);
    spec.on_key = Some(ui::on_window_key);

    let app = rune::App::new(spec)
        .color_scheme(rune::ColorScheme::Dark)
        .cpu_first(rune::CpuFirst::Off)
        .compositor(compositor::BuildingCompositor::new());
    let handle = app.handle();
    if let Err(err) = app
        .on_ready(move |_| web_sync::start_web_sync(handle.clone()))
        .try_run()
    {
        web_console_error(&format!("Rune Web View failed to start: {err}"));
    }
}
