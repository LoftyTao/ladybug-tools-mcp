//! Browser HTTP sync client (`wasm32`) connecting Rune Web View to `/api/*` endpoints.

use std::sync::atomic::{AtomicU64, Ordering};

use lbt_scene::{
    InteractionState, ObjectTargetRef, PresentCommand, SpatialPin, ViewportSnapshot,
    load_hbjson_str,
};
use rune::AppHandle;
use serde::{Deserialize, Serialize};
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::{JsFuture, spawn_local};

use crate::state::ViewerState;

static INTERACTION_POST_SEQ: AtomicU64 = AtomicU64::new(0);

#[derive(Debug, Deserialize)]
pub struct BootstrapPayload {
    pub garden_id: Option<String>,
    pub model_path: Option<String>,
    pub model_label: Option<String>,
    pub model_mtime_ns: Option<u64>,
    pub present_mtime_ns: Option<u64>,
    pub present: Option<PresentCommand>,
    pub interaction_state: Option<InteractionState>,
}

#[derive(Debug, Deserialize)]
pub struct StatusPayload {
    pub present_revision: u64,
    pub present_mtime_ns: Option<u64>,
    pub model_path: Option<String>,
    pub model_mtime_ns: Option<u64>,
}

#[derive(Debug, Serialize)]
pub struct InteractionUpdatePayload {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub garden_id: Option<String>,
    pub selected_targets: Vec<ObjectTargetRef>,
    pub annotations: Vec<SpatialPin>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub viewport: Option<ViewportSnapshot>,
}

fn percent_encode_component(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    for &b in raw.as_bytes() {
        let safe = matches!(
            b,
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~'
        );
        if safe {
            out.push(b as char);
        } else {
            out.push('%');
            let hi = (b >> 4) & 0xf;
            let lo = b & 0xf;
            out.push(char::from_digit(u32::from(hi), 16).unwrap_or('0').to_ascii_uppercase());
            out.push(char::from_digit(u32::from(lo), 16).unwrap_or('0').to_ascii_uppercase());
        }
    }
    out
}

async fn sleep_ms(ms: i32) {
    let promise = js_sys::Promise::new(&mut |resolve, _reject| {
        if let Some(window) = web_sys::window() {
            let _ = window.set_timeout_with_callback_and_timeout_and_arguments_0(&resolve, ms);
        } else {
            let _ = resolve.call0(&wasm_bindgen::JsValue::UNDEFINED);
        }
    });
    let _ = JsFuture::from(promise).await;
}

async fn fetch_text(url: &str) -> Result<String, String> {
    let window = web_sys::window().ok_or_else(|| "No browser window".to_owned())?;
    let headers = web_sys::Headers::new().map_err(|e| format!("{e:?}"))?;
    headers
        .set("Accept", "application/json")
        .map_err(|e| format!("{e:?}"))?;
    let init = web_sys::RequestInit::new();
    init.set_method("GET");
    init.set_headers(&headers);
    let promise: js_sys::Promise = window.fetch_with_str_and_init(url, &init);
    let resp: web_sys::Response = JsFuture::from(promise)
        .await
        .map_err(|e| format!("Fetch failed: {e:?}"))?
        .dyn_into()
        .map_err(|_| "Unexpected fetch response".to_owned())?;
    if !resp.ok() {
        return Err(format!("HTTP {} for {url}", resp.status()));
    }
    let text_promise = resp.text().map_err(|e| format!("Read failed: {e:?}"))?;
    JsFuture::from(text_promise)
        .await
        .map_err(|e| format!("Body failed: {e:?}"))?
        .as_string()
        .ok_or_else(|| "Non-string response body".to_owned())
}

async fn fetch_json<T: serde::de::DeserializeOwned>(url: &str) -> Result<T, String> {
    let raw = fetch_text(url).await?;
    serde_json::from_str::<T>(&raw).map_err(|e| format!("Invalid JSON from {url}: {e}"))
}

async fn post_json<T: Serialize>(url: &str, payload: &T) -> Result<(), String> {
    let window = web_sys::window().ok_or_else(|| "No browser window".to_owned())?;
    let body = serde_json::to_string(payload).map_err(|e| e.to_string())?;
    let headers = web_sys::Headers::new().map_err(|e| format!("{e:?}"))?;
    headers
        .set("Content-Type", "application/json")
        .map_err(|e| format!("{e:?}"))?;
    let init = web_sys::RequestInit::new();
    init.set_method("POST");
    init.set_headers(&headers);
    init.set_body(&wasm_bindgen::JsValue::from_str(&body));
    let promise: js_sys::Promise = window.fetch_with_str_and_init(url, &init);
    let resp: web_sys::Response = JsFuture::from(promise)
        .await
        .map_err(|e| format!("POST failed: {e:?}"))?
        .dyn_into()
        .map_err(|_| "Unexpected POST response".to_owned())?;
    if !resp.ok() {
        return Err(format!("HTTP {} for POST {url}", resp.status()));
    }
    Ok(())
}

/// Trigger non-blocking `POST /api/interaction` from browser UI actions.
pub fn queue_interaction_post(payload: InteractionUpdatePayload) {
    let seq = INTERACTION_POST_SEQ.fetch_add(1, Ordering::Relaxed) + 1;
    spawn_local(async move {
        if seq != INTERACTION_POST_SEQ.load(Ordering::Relaxed) {
            return;
        }
        let _ = post_json("/api/interaction", &payload).await;
    });
}

/// Spawn the bootstrap loader and 750ms live polling loop for a Garden HTTP session.
pub fn start_web_sync(handle: AppHandle<ViewerState>) {
    spawn_local(async move {
        let mut known_rev: u64 = 0;
        let mut known_present_mtime: Option<u64> = None;
        let mut known_path: Option<String> = None;
        let mut known_mtime: Option<u64> = None;
        let mut known_garden_id: Option<String> = None;

        match fetch_json::<BootstrapPayload>("/api/bootstrap").await {
            Ok(boot) => {
                known_garden_id = boot.garden_id.clone();
                known_rev = boot.present.as_ref().map_or(0, |p| p.revision);
                known_present_mtime = boot.present_mtime_ns;
                let target_path = boot
                    .present
                    .as_ref()
                    .and_then(|p| p.model_path.clone())
                    .or_else(|| boot.model_path.clone())
                    .or_else(|| {
                        boot.interaction_state
                            .as_ref()
                            .and_then(|i| i.viewport.as_ref())
                            .and_then(|v| v.model_path.clone())
                    });

                let model_res = if let Some(rel) = target_path.as_deref() {
                    let url = format!("/api/model?path={}", percent_encode_component(rel));
                    match fetch_text(&url).await {
                        Ok(json_text) => load_hbjson_str(
                            &json_text,
                            known_garden_id.as_deref(),
                            Some(rel.to_owned()),
                        )
                        .map(|scene| Some((scene, rel.to_owned())))
                        .map_err(|e| format!("Failed parsing {rel}: {e}")),
                        Err(err) => Err(err),
                    }
                } else {
                    Ok(None)
                };

                known_path = target_path;
                known_mtime = boot.model_mtime_ns;

                handle.update(move |s, tx| {
                    s.web_connected = true;
                    if boot.garden_id.is_some() {
                        s.garden_id = boot.garden_id;
                    }
                    if let Some(label) = boot.model_label {
                        s.model_label = label;
                    }
                    match model_res {
                        Ok(Some((scene, rel_path))) => {
                            s.status_banner = None;
                            s.apply_web_scene_and_state(
                                Some(scene),
                                Some(rel_path),
                                boot.present.as_ref(),
                                boot.interaction_state.as_ref(),
                            );
                        }
                        Ok(None) => {
                            s.status_banner = None;
                            s.apply_web_scene_and_state(
                                None,
                                None,
                                boot.present.as_ref(),
                                boot.interaction_state.as_ref(),
                            );
                        }
                        Err(err) => {
                            s.status_banner = Some(err);
                            s.apply_web_scene_and_state(
                                None,
                                None,
                                boot.present.as_ref(),
                                boot.interaction_state.as_ref(),
                            );
                        }
                    }
                    tx.instant();
                });
            }
            Err(_) => {
                handle.update(move |s, _tx| {
                    s.web_connected = false;
                });
            }
        }

        loop {
            sleep_ms(750).await;
            let status = match fetch_json::<StatusPayload>("/api/status").await {
                Ok(st) => st,
                Err(_) => {
                    handle.update_if(|s, _| {
                        if !s.web_connected {
                            return false;
                        }
                        s.web_connected = false;
                        true
                    });
                    continue;
                }
            };

            let rev_changed = status.present_revision != known_rev
                || (status.present_mtime_ns.is_some()
                    && status.present_mtime_ns != known_present_mtime);
            let next_present = if rev_changed {
                fetch_json::<Option<PresentCommand>>("/api/present")
                    .await
                    .ok()
                    .flatten()
            } else {
                None
            };

            let desired_path = next_present
                .as_ref()
                .and_then(|p| p.model_path.clone())
                .or_else(|| status.model_path.clone());
            let path_changed = desired_path != known_path;
            let mtime_changed =
                status.model_mtime_ns.is_some() && status.model_mtime_ns != known_mtime;

            let loaded_scene = if (path_changed || mtime_changed)
                && let Some(rel) = desired_path.as_deref()
            {
                let url = format!("/api/model?path={}", percent_encode_component(rel));
                fetch_text(&url).await.ok().and_then(|raw| {
                    load_hbjson_str(&raw, known_garden_id.as_deref(), Some(rel.to_owned()))
                        .ok()
                        .map(|scene| (scene, rel.to_owned()))
                })
            } else {
                None
            };

            if rev_changed {
                known_rev = status.present_revision;
            }
            if status.present_mtime_ns.is_some() {
                known_present_mtime = status.present_mtime_ns;
            }
            if let Some(p) = &desired_path {
                known_path = Some(p.clone());
            }
            if status.model_mtime_ns.is_some() {
                known_mtime = status.model_mtime_ns;
            }

            let any_update = rev_changed || loaded_scene.is_some();
            handle.update_if(move |s, _tx| {
                if !any_update {
                    if !s.web_connected {
                        s.web_connected = true;
                        return true;
                    }
                    return false;
                }
                s.web_connected = true;
                let (next_scene, next_rel) = match loaded_scene {
                    Some((sc, p)) => (Some(sc), Some(p)),
                    None => (None, None),
                };
                s.apply_web_scene_and_state(next_scene, next_rel, next_present.as_ref(), None);
                true
            });
        }
    });
}
