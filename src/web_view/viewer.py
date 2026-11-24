"""Garden-local vtk.js sidebar viewer workbench and loopback fallback server."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from garden.manifest import GardenManifest

POLL_INTERVAL_MS = 1500
VENDOR_VTKJS_PATH = Path(__file__).resolve().parent / "vendor" / "vtk.js"


@dataclass
class _FallbackServerHandle:
    garden_root: Path
    name: str
    server: ThreadingHTTPServer
    thread: threading.Thread
    url: str

    def as_dict(self) -> dict[str, Any]:
        host, port = self.server.server_address[:2]
        return {
            "ui": "Fallback URL",
            "library": "vtk.js",
            "mode": "local_url_preview",
            "url": self.url,
            "host": host,
            "port": port,
            "local_only": True,
            "poll_interval_ms": POLL_INTERVAL_MS,
            "vendor_url": "/vendor/vtk.js",
        }


class _FallbackHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # Windows SO_REUSEADDR allows binding an actively listening port; disable on Windows
    # so explicit port conflicts fail cleanly instead of shadowing an active viewer.
    allow_reuse_address = os.name != "nt"

    def server_bind(self) -> None:
        # HTTPServer reverse-resolves its address; local preview needs no DNS.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


_SERVERS: dict[str, _FallbackServerHandle] = {}
_SERVERS_LOCK = threading.Lock()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def fallback_viewer_html() -> str:
    """Return the standalone offline HTML workbench served by the local URL fallback."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Ladybug Tools vtk.js Preview</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7f4;
      color: #1d2528;
    }}
    html, body, #app {{
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
    }}
    body {{
      background: #f5f7f4;
    }}
    .shell {{
      display: grid;
      grid-template-rows: auto 1fr auto;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px 12px;
      padding: 8px 12px;
      border-bottom: 1px solid rgba(29, 37, 40, 0.14);
      background: rgba(255, 255, 255, 0.96);
      min-width: 0;
    }}
    .title {{
      min-width: 160px;
      flex: 1 1 200px;
    }}
    h1, p {{
      margin: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    h1 {{
      font-size: 15px;
      font-weight: 680;
    }}
    p {{
      margin-top: 2px;
      font-size: 12px;
      color: #607071;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }}
    .btn-group {{
      display: flex;
      gap: 4px;
      flex: 0 0 auto;
    }}
    button {{
      height: 30px;
      min-width: 34px;
      padding: 0 8px;
      border: 1px solid rgba(29, 37, 40, 0.18);
      background: #ffffff;
      color: #1d2528;
      cursor: pointer;
      font-size: 12px;
      border-radius: 4px;
    }}
    button:hover {{
      background: #edf2ee;
    }}
    button.active {{
      background: #1f5f5b;
      color: #ffffff;
      border-color: #1f5f5b;
    }}
    .stage {{
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }}
    .pane {{
      position: absolute;
      inset: 0;
      display: none;
    }}
    .pane.active {{
      display: block;
    }}
    #viewer {{
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }}
    #viewer canvas {{
      display: block;
    }}
    #layers-panel {{
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 5;
      width: 220px;
      max-height: calc(100% - 24px);
      overflow: auto;
      padding: 10px;
      border: 1px solid rgba(29, 37, 40, 0.16);
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.94);
      font-size: 12px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
      display: none;
    }}
    #layers-panel.open {{
      display: block;
    }}
    .layers-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      font-weight: 600;
    }}
    .layer-item {{
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 3px 0;
      cursor: pointer;
    }}
    .layer-swatch {{
      width: 10px;
      height: 10px;
      border-radius: 2px;
      border: 1px solid rgba(0,0,0,0.2);
      flex: 0 0 auto;
    }}
    #legend-overlay {{
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 4;
      min-width: 110px;
      max-width: 210px;
      padding: 8px 10px;
      border: 1px solid rgba(29, 37, 40, 0.16);
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.92);
      font-size: 11px;
      display: none;
    }}
    #legend-title {{
      font-weight: 600;
      margin-bottom: 6px;
      word-break: break-word;
    }}
    .legend-body {{
      display: flex;
      align-items: stretch;
      gap: 8px;
    }}
    .legend-bar {{
      width: 16px;
      min-height: 110px;
      border: 1px solid rgba(29, 37, 40, 0.25);
      border-radius: 2px;
    }}
    .legend-ticks {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      font-variant-numeric: tabular-nums;
    }}
    .notice {{
      position: absolute;
      left: 14px;
      right: 14px;
      bottom: 14px;
      z-index: 6;
      max-height: 36%;
      overflow: auto;
      padding: 10px 12px;
      border: 1px solid rgba(29, 37, 40, 0.16);
      background: rgba(255, 255, 255, 0.94);
      color: #29383b;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      border-radius: 4px;
    }}
    .notice.error {{
      border-color: #ffc9c2;
      background: #fff2f0;
      color: #9a1f12;
    }}
    #pane-docs {{
      background: #ffffff;
    }}
    .docs-shell {{
      display: grid;
      grid-template-rows: 42px 1fr;
      width: 100%;
      height: 100%;
    }}
    .docs-bar {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-bottom: 1px solid rgba(29, 37, 40, 0.12);
      background: #f8faf8;
      font-size: 12px;
    }}
    #doc-select {{
      flex: 1 1 auto;
      max-width: 480px;
      height: 28px;
      padding: 0 6px;
      font-size: 12px;
    }}
    #doc-frame {{
      width: 100%;
      height: 100%;
      border: 0;
      background: #ffffff;
    }}
    .timeline {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-top: 1px solid rgba(29, 37, 40, 0.14);
      background: rgba(255, 255, 255, 0.96);
      font-size: 12px;
    }}
    #step-slider {{
      flex: 1 1 160px;
      min-width: 80px;
    }}
    #step-label {{
      min-width: 180px;
      max-width: 340px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #364547;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header class="toolbar">
      <div class="title">
        <h1 id="title">Ladybug Tools vtk.js Preview</h1>
        <p id="status">Connecting to local preview URL</p>
      </div>
      <div class="controls">
        <div class="btn-group" role="tablist" aria-label="Workbench mode">
          <button type="button" id="tab-3d" class="active" role="tab" aria-selected="true">3D Viewport</button>
          <button type="button" id="tab-docs" role="tab" aria-selected="false">HTML / SVG (0)</button>
        </div>
        <div class="btn-group" aria-label="Camera controls">
          <button type="button" id="axon" title="Axonometric view">Ax</button>
          <button type="button" id="top" title="Top view">Top</button>
          <button type="button" id="front" title="Front view">Front</button>
          <button type="button" id="back" title="Back view">Back</button>
          <button type="button" id="left" title="Left view">Left</button>
          <button type="button" id="right" title="Right view">Right</button>
          <button type="button" id="fit" title="Fit scene">Fit</button>
        </div>
        <button type="button" id="toggle-layers" title="Toggle actor/layer visibility">Layers</button>
      </div>
    </header>

    <section class="stage">
      <div id="pane-3d" class="pane active">
        <section id="viewer" aria-label="vtk.js preview canvas">
          <aside id="layers-panel" aria-label="Actor visibility">
            <div class="layers-header">
              <span>Layers</span>
              <div class="btn-group">
                <button type="button" id="layers-all">All</button>
                <button type="button" id="layers-none">None</button>
              </div>
            </div>
            <div id="layers-list"></div>
          </aside>
          <aside id="legend-overlay" aria-label="2D colorbar legend">
            <div id="legend-title"></div>
            <div class="legend-body">
              <div id="legend-bar" class="legend-bar"></div>
              <div id="legend-ticks" class="legend-ticks"></div>
            </div>
          </aside>
          <div id="notice" class="notice">Waiting for a Garden preview session.</div>
        </section>
      </div>

      <div id="pane-docs" class="pane">
        <div class="docs-shell">
          <div class="docs-bar">
            <label for="doc-select">Artifact:</label>
            <select id="doc-select"></select>
            <button type="button" id="doc-reload">Reload</button>
          </div>
          <iframe id="doc-frame" title="HTML and SVG artifact preview"></iframe>
        </div>
      </div>
    </section>

    <footer class="timeline" aria-label="Session steps timeline">
      <button type="button" id="step-prev" title="Previous step">&lt;</button>
      <input type="range" id="step-slider" min="0" max="0" value="0" disabled aria-label="Step timeline scrubber">
      <button type="button" id="step-next" title="Next step">&gt;</button>
      <button type="button" id="step-live" class="active" title="Follow latest preview step">Live</button>
      <span id="step-label">No steps recorded</span>
    </footer>
  </main>

  <script src="/vendor/vtk.js"></script>
  <script>
    const vtkRuntime = window.vtk;
    if (!vtkRuntime) {{
      throw new Error("Local vtk.js bundle failed to load.");
    }}
    const DataAccessHelper = vtkRuntime.IO.Core.DataAccessHelper;
    const vtkHttpSceneLoader = vtkRuntime.IO.Core.vtkHttpSceneLoader;
    const vtkGenericRenderWindow = vtkRuntime.Rendering.Misc.vtkGenericRenderWindow;

    const state = {{
      lastArtifactKey: "",
      context: null,
      cameraState: null,
      timer: null,
      steps: [],
      selectedStepIndex: -1,
      followLatest: true,
      hiddenLayers: new Set(),
      docs: [],
      activeDocPath: "",
      activeTab: "3d",
    }};

    const title = document.getElementById("title");
    const status = document.getElementById("status");
    const notice = document.getElementById("notice");
    const viewer = document.getElementById("viewer");
    const layersPanel = document.getElementById("layers-panel");
    const layersList = document.getElementById("layers-list");
    const legendOverlay = document.getElementById("legend-overlay");
    const legendTitle = document.getElementById("legend-title");
    const legendBar = document.getElementById("legend-bar");
    const legendTicks = document.getElementById("legend-ticks");
    const stepSlider = document.getElementById("step-slider");
    const stepLabel = document.getElementById("step-label");
    const stepLive = document.getElementById("step-live");
    const tab3d = document.getElementById("tab-3d");
    const tabDocs = document.getElementById("tab-docs");
    const pane3d = document.getElementById("pane-3d");
    const paneDocs = document.getElementById("pane-docs");
    const docSelect = document.getElementById("doc-select");
    const docFrame = document.getElementById("doc-frame");

    const showNotice = (message, error = false) => {{
      notice.textContent = message;
      notice.className = error ? "notice error" : "notice";
      notice.style.display = message ? "block" : "none";
    }};

    const setStatus = (message) => {{
      status.textContent = message;
    }};

    const getJson = async (url) => {{
      const response = await fetch(url, {{ cache: "no-store" }});
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload.error || `Request failed: ${{response.status}}`);
      }}
      return payload;
    }};

    const decodeBase64 = (payload) => {{
      const binary = atob(payload);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {{
        bytes[i] = binary.charCodeAt(i);
      }}
      return bytes.buffer;
    }};

    const boundsCenter = (bounds) => [
      (bounds[0] + bounds[1]) / 2,
      (bounds[2] + bounds[3]) / 2,
      (bounds[4] + bounds[5]) / 2,
    ];

    const boundsRadius = (bounds) => {{
      const dx = bounds[1] - bounds[0];
      const dy = bounds[3] - bounds[2];
      const dz = bounds[5] - bounds[4];
      return Math.max(dx, dy, dz) || 1;
    }};

    const captureCamera = () => {{
      const camera = state.context?.renderer?.getActiveCamera?.();
      if (!camera) return null;
      return {{
        position: [...camera.getPosition()],
        focalPoint: [...camera.getFocalPoint()],
        viewUp: [...camera.getViewUp()],
        clippingRange: [...camera.getClippingRange()],
        parallelProjection: camera.getParallelProjection?.() ?? false,
        parallelScale: camera.getParallelScale?.() ?? null,
      }};
    }};

    const restoreCamera = () => {{
      if (!state.context || !state.cameraState) return false;
      const camera = state.context.renderer.getActiveCamera();
      camera.setFocalPoint(...state.cameraState.focalPoint);
      camera.setPosition(...state.cameraState.position);
      camera.setViewUp(...state.cameraState.viewUp);
      camera.setClippingRange(...state.cameraState.clippingRange);
      camera.setParallelProjection?.(state.cameraState.parallelProjection);
      if (Number.isFinite(state.cameraState.parallelScale)) {{
        camera.setParallelScale?.(state.cameraState.parallelScale);
      }}
      state.context.renderer.resetCameraClippingRange();
      state.context.renderWindow.render();
      return true;
    }};

    const ensureContext = () => {{
      if (state.context?.genericRenderWindow) {{
        state.context.genericRenderWindow.resize();
        return state.context;
      }}
      const genericRenderWindow = vtkGenericRenderWindow.newInstance({{
        background: [0.965, 0.965, 0.93],
        listenWindowResize: true,
      }});
      genericRenderWindow.setContainer(viewer);
      genericRenderWindow.resize();
      state.context = {{
        genericRenderWindow,
        renderer: genericRenderWindow.getRenderer(),
        renderWindow: genericRenderWindow.getRenderWindow(),
        sceneImporter: null,
        center: null,
        radius: null,
        bounds: null,
      }};
      return state.context;
    }};

    const clearScene = (context) => {{
      context.sceneImporter?.delete?.();
      context.sceneImporter = null;
      context.renderer.removeAllViewProps?.();
      context.renderer.removeAllActors?.();
      context.renderer.removeAllVolumes?.();
      context.renderWindow.render();
    }};

    const setCamera = (mode) => {{
      if (!state.context?.renderer) return;
      const {{ renderer, renderWindow, center, radius, bounds }} = state.context;
      if (mode === "fit") {{
        if (bounds && bounds.every(Number.isFinite)) {{
          renderer.resetCamera(bounds);
        }} else {{
          renderer.resetCamera();
        }}
        renderer.resetCameraClippingRange();
        renderWindow.render();
        state.cameraState = captureCamera();
        return;
      }}
      if (!center || !radius) return;
      const camera = renderer.getActiveCamera();
      const views = {{
        axon: {{
          pos: [center[0] + radius * 1.1, center[1] - radius * 1.0, center[2] + radius * 0.72],
          up: [0, 0, 1],
        }},
        top: {{ pos: [center[0], center[1], center[2] + radius * 1.45], up: [0, 1, 0] }},
        front: {{ pos: [center[0], center[1] - radius * 1.45, center[2]], up: [0, 0, 1] }},
        back: {{ pos: [center[0], center[1] + radius * 1.45, center[2]], up: [0, 0, 1] }},
        left: {{ pos: [center[0] - radius * 1.45, center[1], center[2]], up: [0, 0, 1] }},
        right: {{ pos: [center[0] + radius * 1.45, center[1], center[2]], up: [0, 0, 1] }},
      }};
      const cfg = views[mode] || views.axon;
      camera.setFocalPoint(center[0], center[1], center[2]);
      camera.setPosition(...cfg.pos);
      camera.setViewUp(...cfg.up);
      camera.setClippingRange(0.01, radius * 10);
      renderer.resetCameraClippingRange();
      renderWindow.render();
      state.cameraState = captureCamera();
    }};

    const renderLayers = (sceneItems, metaItems) => {{
      layersList.innerHTML = "";
      const metaByName = new Map((metaItems || []).map((m) => [m.name, m]));
      if (!sceneItems || !sceneItems.length) {{
        layersList.textContent = "No scene actors";
        return;
      }}
      sceneItems.forEach((entry, idx) => {{
        const name = entry.name || `Layer ${{idx + 1}}`;
        const row = document.createElement("label");
        row.className = "layer-item";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        const visible = !state.hiddenLayers.has(name);
        cb.checked = visible;
        if (entry.actor?.setVisibility) {{
          entry.actor.setVisibility(visible);
        }}
        cb.addEventListener("change", () => {{
          if (cb.checked) state.hiddenLayers.delete(name);
          else state.hiddenLayers.add(name);
          entry.actor?.setVisibility?.(cb.checked);
          state.context?.renderWindow?.render();
        }});
        const swatch = document.createElement("span");
        swatch.className = "layer-swatch";
        const dc = entry.property?.diffuseColor || metaByName.get(name)?.diffuseColor;
        if (Array.isArray(dc) && dc.length >= 3) {{
          swatch.style.background = `rgb(${{Math.round(dc[0] * 255)}}, ${{Math.round(dc[1] * 255)}}, ${{Math.round(dc[2] * 255)}})`;
        }}
        const text = document.createElement("span");
        text.textContent = name;
        row.append(cb, swatch, text);
        layersList.appendChild(row);
      }});
      state.context?.renderWindow?.render();
    }};

    const colorToCss = (c) => {{
      if (Array.isArray(c) && c.length >= 3) {{
        const scale = c.every((v) => v <= 1) ? 255 : 1;
        return `rgb(${{Math.round(c[0] * scale)}}, ${{Math.round(c[1] * scale)}}, ${{Math.round(c[2] * scale)}})`;
      }}
      if (c && typeof c === "object" && "r" in c) {{
        return `rgb(${{c.r}}, ${{c.g}}, ${{c.b}})`;
      }}
      return "#3b82f6";
    }};

    const renderLegend = (sceneMetadata, importerMeta) => {{
      let legend = sceneMetadata?.legends?.[0] || null;
      if (!legend && importerMeta?.scene) {{
        for (const item of importerMeta.scene) {{
          const m = item?.metadata?.[0];
          if (m?.legend_parameters) {{
            legend = {{
              title: m.legend_parameters.title || m.unit || item.name,
              min: m.legend_parameters.min,
              max: m.legend_parameters.max,
              decimal_count: m.legend_parameters.decimal_count ?? 2,
              colors: m.legend_parameters.colors,
            }};
            break;
          }}
        }}
      }}
      if (!legend) {{
        legendOverlay.style.display = "none";
        return;
      }}
      legendOverlay.style.display = "block";
      legendTitle.textContent = legend.title || "Legend";
      const colors = Array.isArray(legend.colors) && legend.colors.length
        ? legend.colors.map(colorToCss)
        : ["#313695", "#4575b4", "#74add1", "#fee090", "#f46d43", "#a50026"];
      const topToBottom = [...colors].reverse();
      legendBar.style.background = `linear-gradient(to bottom, ${{topToBottom.join(", ")}})`;
      const dec = Number.isInteger(legend.decimal_count) ? legend.decimal_count : 2;
      const fmt = (v) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(dec) : "--");
      const minV = legend.min;
      const maxV = legend.max;
      const midV = (typeof minV === "number" && typeof maxV === "number") ? (minV + maxV) / 2 : null;
      legendTicks.innerHTML = `<span>${{fmt(maxV)}}</span><span>${{fmt(midV)}}</span><span>${{fmt(minV)}}</span>`;
    }};

    const loadArtifact = async (artifact) => {{
      setStatus(`Loading ${{artifact.name || artifact.path}}`);
      showNotice("");
      state.cameraState = captureCamera() || state.cameraState;
      const payload = await getJson(`/api/artifact?path=${{encodeURIComponent(artifact.path)}}&revision=${{encodeURIComponent(artifact.revision)}}`);
      const zipContent = decodeBase64(payload.payload_base64);
      const context = ensureContext();
      clearScene(context);
      const dataAccessHelper = DataAccessHelper.get("zip", {{
        zipContent,
        callback: () => {{
          const sceneImporter = vtkHttpSceneLoader.newInstance({{
            renderer: context.renderer,
            dataAccessHelper,
          }});
          context.sceneImporter = sceneImporter;
          sceneImporter.onReady(() => {{
            const bounds = context.renderer.computeVisiblePropBounds();
            context.bounds = bounds;
            context.center = boundsCenter(bounds);
            context.radius = boundsRadius(bounds) * 2.7;
            renderLayers(sceneImporter.getScene?.() || [], payload.scene_metadata?.scene_items);
            renderLegend(payload.scene_metadata, sceneImporter.getMetadata?.());
            if (!restoreCamera()) {{
              setCamera("axon");
            }}
            setStatus(`Loaded ${{artifact.name || artifact.path}}`);
          }});
          sceneImporter.setUrl("index.json");
        }},
      }});
    }};

    const updateTimeline = (steps) => {{
      state.steps = steps || [];
      if (!state.steps.length) {{
        stepSlider.disabled = true;
        stepSlider.min = 0;
        stepSlider.max = 0;
        stepSlider.value = 0;
        stepLabel.textContent = "No steps recorded";
        return;
      }}
      stepSlider.disabled = false;
      stepSlider.min = 0;
      stepSlider.max = String(state.steps.length - 1);
      if (state.followLatest || state.selectedStepIndex < 0 || state.selectedStepIndex >= state.steps.length) {{
        state.selectedStepIndex = state.steps.length - 1;
      }}
      stepSlider.value = String(state.selectedStepIndex);
      stepLive.classList.toggle("active", state.followLatest);
      const cur = state.steps[state.selectedStepIndex];
      const toolInfo = cur?.source_tool ? ` [${{cur.source_tool}}]` : "";
      const errInfo = cur?.status === "failed" ? ` (FAILED: ${{cur.error || "error"}})` : "";
      stepLabel.textContent = `${{state.selectedStepIndex + 1}}/${{state.steps.length}}: ${{cur?.label || cur?.id || "step"}}${{toolInfo}}${{errInfo}}`;
    }};

    const updateDocs = (docs) => {{
      state.docs = docs || [];
      tabDocs.textContent = `HTML / SVG (${{state.docs.length}})`;
      const prev = docSelect.value || state.activeDocPath;
      docSelect.innerHTML = "";
      if (!state.docs.length) {{
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No HTML or SVG artifacts registered";
        docSelect.appendChild(opt);
        docFrame.removeAttribute("src");
        state.activeDocPath = "";
        return;
      }}
      state.docs.forEach((doc) => {{
        const opt = document.createElement("option");
        opt.value = doc.path;
        opt.textContent = `${{doc.name}} (${{doc.format.toUpperCase()}}) - ${{doc.path}}`;
        docSelect.appendChild(opt);
      }});
      const chosen = state.docs.some((d) => d.path === prev) ? prev : state.docs[0].path;
      docSelect.value = chosen;
      if (state.activeTab === "docs" && state.activeDocPath !== chosen) {{
        state.activeDocPath = chosen;
        docFrame.src = `/api/document?path=${{encodeURIComponent(chosen)}}`;
      }}
    }};

    const selectStep = async (index, followLatest = false) => {{
      if (!state.steps.length) return;
      const clamped = Math.max(0, Math.min(index, state.steps.length - 1));
      state.selectedStepIndex = clamped;
      state.followLatest = followLatest;
      updateTimeline(state.steps);
      const step = state.steps[clamped];
      if (step?.status === "failed") {{
        showNotice(`Step ${{step.id}} failed: ${{step.error || "Unknown error"}}`, true);
        return;
      }}
      const art = step?.artifact;
      if (!art) return;
      const key = `${{art.path}}|${{art.revision}}`;
      if (key !== state.lastArtifactKey) {{
        state.lastArtifactKey = key;
        await loadArtifact(art);
      }}
    }};

    const refresh = async () => {{
      const preview = await getJson("/api/state");
      title.textContent = preview?.garden?.name || "Ladybug Tools Garden";
      updateTimeline(preview?.steps || []);
      updateDocs(preview?.html_svg_artifacts || []);
      let artifact = preview?.artifact;
      if (!state.followLatest && state.steps[state.selectedStepIndex]) {{
        const chosenStep = state.steps[state.selectedStepIndex];
        if (chosenStep.status === "failed") {{
          showNotice(`Step ${{chosenStep.id}} failed: ${{chosenStep.error || "Unknown error"}}`, true);
          return;
        }}
        artifact = chosenStep.artifact || artifact;
      }}
      if (!artifact) {{
        setStatus(preview?.report?.message || "Waiting for vtk.js preview");
        showNotice(preview?.report?.message || "Waiting for vtk.js preview");
        return;
      }}
      const artifactKey = `${{artifact.path}}|${{artifact.revision}}`;
      setStatus(`${{artifact.name || "vtk.js"}} - ${{artifact.revision.slice(0, 8)}}`);
      if (artifactKey === state.lastArtifactKey) return;
      state.lastArtifactKey = artifactKey;
      await loadArtifact(artifact);
    }};

    const setTab = (tab) => {{
      state.activeTab = tab;
      const is3d = tab === "3d";
      tab3d.classList.toggle("active", is3d);
      tabDocs.classList.toggle("active", !is3d);
      tab3d.setAttribute("aria-selected", String(is3d));
      tabDocs.setAttribute("aria-selected", String(!is3d));
      pane3d.classList.toggle("active", is3d);
      paneDocs.classList.toggle("active", !is3d);
      if (!is3d && docSelect.value) {{
        state.activeDocPath = docSelect.value;
        docFrame.src = `/api/document?path=${{encodeURIComponent(docSelect.value)}}`;
      }} else if (is3d) {{
        state.context?.genericRenderWindow?.resize?.();
      }}
    }};

    ["axon", "top", "front", "back", "left", "right", "fit"].forEach((viewId) => {{
      document.getElementById(viewId).addEventListener("click", () => setCamera(viewId));
    }});
    document.getElementById("toggle-layers").addEventListener("click", () => {{
      layersPanel.classList.toggle("open");
    }});
    document.getElementById("layers-all").addEventListener("click", () => {{
      state.hiddenLayers.clear();
      layersList.querySelectorAll("input[type=checkbox]").forEach((cb) => {{
        if (!cb.checked) cb.click();
      }});
    }});
    document.getElementById("layers-none").addEventListener("click", () => {{
      layersList.querySelectorAll("input[type=checkbox]").forEach((cb) => {{
        if (cb.checked) cb.click();
      }});
    }});
    tab3d.addEventListener("click", () => setTab("3d"));
    tabDocs.addEventListener("click", () => setTab("docs"));
    docSelect.addEventListener("change", () => {{
      if (docSelect.value) {{
        state.activeDocPath = docSelect.value;
        docFrame.src = `/api/document?path=${{encodeURIComponent(docSelect.value)}}`;
      }}
    }});
    document.getElementById("doc-reload").addEventListener("click", () => {{
      if (docSelect.value) {{
        docFrame.src = `/api/document?path=${{encodeURIComponent(docSelect.value)}}&t=${{Date.now()}}`;
      }}
    }});
    stepSlider.addEventListener("input", () => {{
      const idx = Number.parseInt(stepSlider.value, 10);
      selectStep(idx, idx === state.steps.length - 1).catch((reason) => showNotice(String(reason), true));
    }});
    document.getElementById("step-prev").addEventListener("click", () => {{
      selectStep(state.selectedStepIndex - 1, false).catch((reason) => showNotice(String(reason), true));
    }});
    document.getElementById("step-next").addEventListener("click", () => {{
      const next = state.selectedStepIndex + 1;
      selectStep(next, next >= state.steps.length - 1).catch((reason) => showNotice(String(reason), true));
    }});
    stepLive.addEventListener("click", () => {{
      selectStep(state.steps.length - 1, true).catch((reason) => showNotice(String(reason), true));
    }});

    refresh().catch((reason) => {{
      showNotice(reason instanceof Error ? reason.message : String(reason), true);
      setStatus("Preview failed");
    }});
    state.timer = window.setInterval(() => {{
      refresh().catch((reason) => {{
        showNotice(reason instanceof Error ? reason.message : String(reason), true);
        setStatus("Preview failed");
      }});
    }}, {POLL_INTERVAL_MS});
  </script>
</body>
</html>"""


def _make_handler(garden_root: Path) -> type[BaseHTTPRequestHandler]:
    from web_view import read_preview_artifact, read_preview_document, read_preview_state

    class _Handler(BaseHTTPRequestHandler):
        def _send(
            self,
            status: HTTPStatus,
            body: bytes,
            content_type: str,
            *,
            cache_control: str = "no-store",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", cache_control)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            self._send(status, _json_bytes(payload), "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler hook
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self._send(
                    HTTPStatus.OK,
                    fallback_viewer_html().encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if parsed.path == "/vendor/vtk.js":
                if not VENDOR_VTKJS_PATH.is_file():
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {"schema_version": "1", "error": "Bundled vtk.js asset not found."},
                    )
                    return
                self._send(
                    HTTPStatus.OK,
                    VENDOR_VTKJS_PATH.read_bytes(),
                    "application/javascript; charset=utf-8",
                    cache_control="public, max-age=3600",
                )
                return
            if parsed.path == "/api/state":
                try:
                    self._send_json(
                        HTTPStatus.OK,
                        read_preview_state(garden_root=str(garden_root)),
                    )
                except Exception as exc:  # pragma: no cover - defensive response path
                    self._send_json(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {"schema_version": "1", "error": str(exc)},
                    )
                return
            if parsed.path == "/api/artifact":
                query = parse_qs(parsed.query)
                artifact_path = (query.get("path") or [""])[0]
                revision = (query.get("revision") or [None])[0]
                try:
                    self._send_json(
                        HTTPStatus.OK,
                        read_preview_artifact(
                            garden_root=str(garden_root),
                            artifact_path=artifact_path,
                            revision=revision,
                        ),
                    )
                except Exception as exc:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"schema_version": "1", "error": str(exc)},
                    )
                return
            if parsed.path == "/api/document":
                query = parse_qs(parsed.query)
                artifact_path = (query.get("path") or [""])[0]
                try:
                    doc = read_preview_document(
                        garden_root=str(garden_root),
                        artifact_path=artifact_path,
                    )
                    self._send(HTTPStatus.OK, doc["body"], doc["mime_type"])
                except Exception as exc:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"schema_version": "1", "error": str(exc)},
                    )
                return
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"schema_version": "1", "error": f"Unknown preview route: {parsed.path}"},
            )

        def log_message(self, format: str, *args: Any) -> None:
            return

    return _Handler


def _validate_port(port: int | None) -> int:
    if port is None:
        return 0
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("port must be an integer between 1 and 65535, or None.")
    if port < 1 or port > 65535:
        raise ValueError(f"port must be between 1 and 65535; got {port}.")
    return port


def _stop_handle(handle: _FallbackServerHandle) -> None:
    handle.server.shutdown()
    handle.server.server_close()
    handle.thread.join(timeout=2)


def start_preview_url_fallback(
    *,
    garden_root: str,
    name: str = "Code Mode vtk.js Preview",
    port: int | None = None,
) -> dict[str, Any]:
    """Start or reuse a local-only URL fallback for one Garden preview session."""
    bind_port = _validate_port(port)
    root = Path(garden_root).expanduser().resolve()
    GardenManifest.read(root)
    key = str(root)
    with _SERVERS_LOCK:
        handle = _SERVERS.get(key)
        if handle and handle.thread.is_alive():
            current_port = handle.server.server_address[1]
            if bind_port == 0 or current_port == bind_port:
                return handle.as_dict()
            _stop_handle(_SERVERS.pop(key))

        try:
            server = _FallbackHTTPServer(("127.0.0.1", bind_port), _make_handler(root))
        except OSError as exc:
            raise RuntimeError(
                f"Web View fallback port {bind_port} on 127.0.0.1 is already in use or unavailable: {exc}"
            ) from exc

        host, bound_port = server.server_address[:2]
        thread = threading.Thread(
            target=server.serve_forever,
            name=f"web-view-url-fallback-{bound_port}",
            daemon=True,
        )
        url = f"http://{host}:{bound_port}/"
        handle = _FallbackServerHandle(
            garden_root=root,
            name=name,
            server=server,
            thread=thread,
            url=url,
        )
        _SERVERS[key] = handle
        thread.start()
        return handle.as_dict()


def stop_preview_url_fallback(*, garden_root: str) -> dict[str, Any]:
    """Stop the local URL fallback for one Garden if it is running."""
    root = Path(garden_root).expanduser().resolve()
    GardenManifest.read(root)
    key = str(root)
    with _SERVERS_LOCK:
        handle = _SERVERS.pop(key, None)
    if handle is None:
        return {
            "status": "not_running",
            "mode": "local_url_preview",
            "local_only": True,
        }
    _stop_handle(handle)
    return {
        "status": "stopped",
        "mode": "local_url_preview",
        "url": handle.url,
        "local_only": True,
    }
