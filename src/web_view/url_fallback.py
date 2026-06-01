"""Local URL fallback for hosts that cannot render FastMCP Apps."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from garden.manifest import GardenManifest
from web_view.app import POLL_INTERVAL_MS, read_preview_artifact, read_preview_state


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
        }


class _FallbackHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


_SERVERS: dict[str, _FallbackServerHandle] = {}
_SERVERS_LOCK = threading.Lock()


def _resolve_garden_root(garden_root: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    GardenManifest.read(root)
    return root


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def fallback_viewer_html() -> str:
    """Return the standalone HTML viewer served by the local URL fallback."""
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
      grid-template-rows: 56px 1fr;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 12px;
      border-bottom: 1px solid rgba(29, 37, 40, 0.14);
      background: rgba(255, 255, 255, 0.94);
      min-width: 0;
    }}
    .title {{
      min-width: 0;
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
      letter-spacing: 0;
    }}
    p {{
      margin-top: 3px;
      font-size: 12px;
      color: #607071;
    }}
    .buttons {{
      display: flex;
      gap: 6px;
      flex: 0 0 auto;
    }}
    button {{
      width: 36px;
      height: 32px;
      border: 1px solid rgba(29, 37, 40, 0.18);
      background: #ffffff;
      color: #1d2528;
      cursor: pointer;
      font-size: 12px;
      padding: 0;
    }}
    button:hover {{
      background: #edf2ee;
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
    .notice {{
      position: absolute;
      left: 14px;
      right: 14px;
      bottom: 14px;
      max-height: 38%;
      overflow: auto;
      padding: 10px 12px;
      border: 1px solid rgba(29, 37, 40, 0.16);
      background: rgba(255, 255, 255, 0.94);
      color: #29383b;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
    }}
    .notice.error {{
      border-color: #ffc9c2;
      background: #fff2f0;
      color: #9a1f12;
    }}
    @media (max-width: 680px) {{
      .shell {{
        grid-template-rows: 74px 1fr;
      }}
      .toolbar {{
        align-items: flex-start;
        flex-direction: column;
      }}
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
      <div class="buttons" aria-label="Camera controls">
        <button type="button" id="axon" title="Axonometric view">Ax</button>
        <button type="button" id="top" title="Top view">Top</button>
      </div>
    </header>
    <section id="viewer" aria-label="vtk.js preview canvas">
      <div id="notice" class="notice">Waiting for a Garden preview session.</div>
    </section>
  </main>
  <script src="https://unpkg.com/vtk.js@35.14.1"></script>
  <script>
    const vtkRuntime = window.vtk;
    if (!vtkRuntime) {{
      throw new Error("vtk.js failed to load.");
    }}
    const DataAccessHelper = vtkRuntime.IO.Core.DataAccessHelper;
    const vtkHttpSceneLoader = vtkRuntime.IO.Core.vtkHttpSceneLoader;
    const vtkGenericRenderWindow = vtkRuntime.Rendering.Misc.vtkGenericRenderWindow;

    const state = {{
      lastArtifactKey: "",
      context: null,
      cameraState: null,
      timer: null,
    }};
    const title = document.getElementById("title");
    const status = document.getElementById("status");
    const notice = document.getElementById("notice");
    const viewer = document.getElementById("viewer");

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
      const {{ renderer, renderWindow, center, radius }} = state.context;
      if (!center || !radius) return;
      const camera = renderer.getActiveCamera();
      const position = mode === "top"
        ? [center[0], center[1], center[2] + radius * 1.45]
        : [center[0] + radius * 1.1, center[1] - radius * 1.0, center[2] + radius * 0.72];
      const viewUp = mode === "top" ? [0, 1, 0] : [0, 0, 1];
      camera.setFocalPoint(center[0], center[1], center[2]);
      camera.setPosition(position[0], position[1], position[2]);
      camera.setViewUp(viewUp[0], viewUp[1], viewUp[2]);
      camera.setClippingRange(0.01, radius * 10);
      renderer.resetCameraClippingRange();
      renderWindow.render();
      state.cameraState = captureCamera();
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
            context.center = boundsCenter(bounds);
            context.radius = boundsRadius(bounds) * 2.7;
            if (!restoreCamera()) {{
              setCamera("axon");
            }}
            setStatus(`Loaded ${{artifact.name || artifact.path}}`);
          }});
          sceneImporter.setUrl("index.json");
        }},
      }});
    }};

    const refresh = async () => {{
      const preview = await getJson("/api/state");
      const gardenName = preview?.garden?.name || "Ladybug Tools Garden";
      title.textContent = gardenName;
      const artifact = preview?.artifact;
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

    document.getElementById("axon").addEventListener("click", () => setCamera("axon"));
    document.getElementById("top").addEventListener("click", () => setCamera("top"));
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
    class _Handler(BaseHTTPRequestHandler):
        def _send(
            self,
            status: HTTPStatus,
            body: bytes,
            content_type: str,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
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
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"schema_version": "1", "error": f"Unknown preview route: {parsed.path}"},
            )

        def log_message(self, format: str, *args: Any) -> None:
            return

    return _Handler


def _is_running(handle: _FallbackServerHandle) -> bool:
    return handle.thread.is_alive()


def start_preview_url_fallback(
    *,
    garden_root: str,
    name: str = "Code Mode vtk.js Preview",
) -> dict[str, Any]:
    """Start or reuse a local-only URL fallback for one Garden preview session."""
    root = _resolve_garden_root(garden_root)
    key = str(root)
    with _SERVERS_LOCK:
        handle = _SERVERS.get(key)
        if handle and _is_running(handle):
            return handle.as_dict()

        server = _FallbackHTTPServer(("127.0.0.1", 0), _make_handler(root))
        host, port = server.server_address[:2]
        thread = threading.Thread(
            target=server.serve_forever,
            name=f"web-view-url-fallback-{port}",
            daemon=True,
        )
        url = f"http://{host}:{port}/"
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
    root = _resolve_garden_root(garden_root)
    key = str(root)
    with _SERVERS_LOCK:
        handle = _SERVERS.pop(key, None)
    if handle is None:
        return {
            "status": "not_running",
            "mode": "local_url_preview",
            "local_only": True,
        }
    handle.server.shutdown()
    handle.server.server_close()
    handle.thread.join(timeout=2)
    return {
        "status": "stopped",
        "mode": "local_url_preview",
        "url": handle.url,
        "local_only": True,
    }
