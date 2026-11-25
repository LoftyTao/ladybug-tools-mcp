//! Zero-readback Rune `Compositor` embedding the 3D WebGPU/WebGL2 building viewport.

use lbt_renderer_wgpu::EmbeddedSceneRenderer;
use rune::compose::DeviceKey;
use rune::render::KIND_EFFECT;
use rune::{Compositor, Frame};

use crate::engine::to_wgpu_render_state;
use crate::state::ViewerState;

/// Effect slot tag marking the main 3D viewport element in `ui::viewport_pane`.
pub const VIEWPORT_EFFECT_MARK: u32 = 1;

struct CachedEngine {
    device_key: DeviceKey,
    engine: EmbeddedSceneRenderer,
}

/// Rune compositor drawing passes 0..3 into an offscreen resolve texture and compositing it
/// seamlessly beneath all Rune HUD overlays, pins, and callouts.
#[derive(Default)]
pub struct BuildingCompositor {
    cached: Option<CachedEngine>,
    rendered_own: bool,
}

impl BuildingCompositor {
    pub fn new() -> Self {
        Self::default()
    }
}

impl Compositor<ViewerState> for BuildingCompositor {
    fn animating(&self) -> bool {
        false
    }

    fn draws_own(&self) -> bool {
        self.rendered_own
    }

    fn release_gpu(&mut self) {
        self.cached = None;
    }

    fn render(&mut self, f: &mut Frame<'_, ViewerState>) {
        let key = f.device_key();
        if self.cached.as_ref().is_none_or(|c| c.device_key != key) {
            self.cached = None;
            let engine = EmbeddedSceneRenderer::new(
                f.adapter(),
                f.device.clone(),
                f.queue.clone(),
            );
            f.restore_device_callbacks();
            self.cached = Some(CachedEngine {
                device_key: key,
                engine,
            });
        }

        let mut viewport_px: Option<(u32, u32)> = None;
        for (idx, inst) in f.rt.instances.iter().enumerate() {
            if inst.params[1] == KIND_EFFECT
                && f.rt.marks.get(idx).copied() == Some(VIEWPORT_EFFECT_MARK)
            {
                let w = inst.rect[2].round().max(1.0) as u32;
                let h = inst.rect[3].round().max(1.0) as u32;
                viewport_px = Some((w, h));
                break;
            }
        }

        let Some(cache) = self.cached.as_mut() else {
            self.rendered_own = false;
            return;
        };

        if let Some((w, h)) = viewport_px {
            let state = &f.rt.state;
            let render_state = to_wgpu_render_state(&state.current_render_state());
            let camera = state.renderer.orbit_camera();
            cache
                .engine
                .sync(&state.scene, state.scene_version, &render_state, &camera);
            if let Err(err) = cache.engine.prepare_viewport(f.encoder, w, h, f.format) {
                f.rt.state.status_banner = Some(format!("3D render error: {err}"));
                self.rendered_own = false;
            } else {
                self.rendered_own = true;
            }
        } else {
            self.rendered_own = false;
        }

        let clear = f.rt.clear_color();
        f.ui.set_fade_stops(f.rt.fade_stops());
        f.ui.prepare(
            f.device,
            f.queue,
            &mut f.rt.text.atlas,
            &f.rt.instances,
            f.size,
        );
        let engine = &mut cache.engine;
        f.ui.draw_with(f.encoder, f.target, clear, &mut |pass, site| {
            if site.mark == VIEWPORT_EFFECT_MARK {
                engine.draw_blit(
                    pass,
                    site.format,
                    site.size,
                    site.origin,
                    site.instance.rect,
                    site.srgb_blend,
                );
            }
        });
    }
}
