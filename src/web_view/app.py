"""FastMCP Custom HTML App support for Garden-backed vtk.js previews."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

from web_view.session import (
    get_web_view_config,
    start_web_view_session,
)

APP_NAME = "ladybug-tools-vtk-preview"
VIEW_RESOURCE_URI = "ui://web_view/ladybug-tools/vtkjs-preview.html"
UNMOUNTED_VIEW_RESOURCE_URI = "ui://ladybug-tools/vtkjs-preview.html"
POLL_INTERVAL_MS = 1500
APP_RESOURCE_DOMAINS = (
    "https://unpkg.com",
)
PREVIEW_STATE_TOOL = "preview_state"
PREVIEW_ARTIFACT_TOOL = "preview_artifact"


def app_tool_hash(tool_name: str) -> str:
    """Return FastMCP's deterministic backend-tool hash."""
    payload = f"{APP_NAME}\x00{tool_name}".encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def app_backend_tool_name(tool_name: str) -> str:
    """Return the MCP-callable hashed backend tool name for this App."""
    return f"{app_tool_hash(tool_name)}_{tool_name}"


def app_meta(tool_name: str | None = None) -> dict[str, dict[str, str]]:
    """Return FastMCP app routing metadata."""
    fastmcp_meta = {"app": APP_NAME}
    if tool_name:
        fastmcp_meta["_tool_hash"] = app_tool_hash(tool_name)
    return {"fastmcp": fastmcp_meta}


def _resolve_garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_file(*, garden_root: Path, artifact_path: str) -> Path:
    normalized = artifact_path.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Preview artifact path must be a non-empty Garden-relative path.")
    path = (garden_root / normalized).resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("Preview artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() != ".vtkjs":
        raise ValueError(f"Preview artifact must be a .vtkjs file; got {normalized!r}.")
    if not path.is_file():
        raise ValueError(f"Preview artifact file was not found: {normalized}.")
    return path


def _artifact_from_source(
    *,
    garden_root: Path,
    source: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not source:
        return None
    artifact_path = source.get("artifact_path")
    if not isinstance(artifact_path, str) or not artifact_path:
        return None
    path = _resolve_artifact_file(garden_root=garden_root, artifact_path=artifact_path)
    return {
        "name": source.get("artifact_name") or path.stem,
        "path": artifact_path.replace("\\", "/"),
        "kind": source.get("kind") or "vtkjs_artifact",
        "artifact_type": source.get("artifact_type"),
        "source": source.get("source", {}),
        "revision": _hash_file(path),
        "size_bytes": path.stat().st_size,
    }


def _active_artifact(config: dict[str, Any], garden_root: Path) -> dict[str, Any] | None:
    active_step = config.get("active_step")
    if isinstance(active_step, dict):
        artifact = _artifact_from_source(
            garden_root=garden_root,
            source=active_step.get("viewer_source"),
        )
        if artifact:
            return artifact
    latest = config.get("latest_vtkjs_artifact")
    if isinstance(latest, dict):
        return _artifact_from_source(garden_root=garden_root, source=latest)
    return None


def start_preview_app_session(
    *,
    garden_root: str,
    name: str = "Code Mode vtk.js Preview",
    preview_kinds: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Start the Garden preview session used by the FastMCP App."""
    result = start_web_view_session(
        garden_root=garden_root,
        name=name,
        preview_kinds=preview_kinds,
    )
    state = read_preview_state(garden_root=garden_root)
    return {
        **result,
        "app": {
            "name": APP_NAME,
            "resource_uri": VIEW_RESOURCE_URI,
            "poll_interval_ms": POLL_INTERVAL_MS,
        },
        "viewer": state["viewer"],
        "summary_view": {
            **result["summary_view"],
            "app": "FastMCP Custom HTML App",
            "poll_interval_ms": POLL_INTERVAL_MS,
        },
    }


def read_preview_state(*, garden_root: str) -> dict[str, Any]:
    """Return compact state for the vtk.js preview App."""
    root = _resolve_garden_root(garden_root)
    config = get_web_view_config(garden_root=str(root))
    artifact = _active_artifact(config, root)
    active_step = config.get("active_step")
    return {
        "schema_version": "1",
        "active": bool(config.get("active", False)),
        "garden": config.get("garden", {}),
        "viewer": {
            "ui": "FastMCP App",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
        },
        "poll_interval_ms": POLL_INTERVAL_MS,
        "preview_kinds": config.get("preview_kinds", []),
        "active_step": active_step,
        "artifact": artifact,
        "report": {
            "status": "ready" if artifact else "waiting_for_vtkjs",
            "message": (
                "A vtk.js preview is available."
                if artifact
                else "No vtk.js preview has been recorded for this Garden yet."
            ),
        },
    }


def read_preview_artifact(
    *,
    garden_root: str,
    artifact_path: str,
    revision: str | None = None,
) -> dict[str, Any]:
    """Return a Garden-local `.vtkjs` preview payload for the FastMCP App."""
    root = _resolve_garden_root(garden_root)
    path = _resolve_artifact_file(garden_root=root, artifact_path=artifact_path)
    actual_revision = _hash_file(path)
    if revision and revision != actual_revision:
        raise ValueError(
            "Preview artifact revision changed; refresh preview state before loading it."
        )
    return {
        "schema_version": "1",
        "path": artifact_path.replace("\\", "/"),
        "revision": actual_revision,
        "size_bytes": path.stat().st_size,
        "mime_type": "application/vnd.vtkjs",
        "encoding": "base64",
        "payload_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def viewer_html() -> str:
    """Return the custom HTML App resource."""
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
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: transparent;
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
        <p id="status">Connecting to FastMCP App host</p>
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
  <script type="module">
    import {{ App }} from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";

    const vtkRuntime = window.vtk;
    if (!vtkRuntime) {{
      throw new Error("vtk.js failed to load.");
    }}
    const DataAccessHelper = vtkRuntime.IO.Core.DataAccessHelper;
    const vtkHttpSceneLoader = vtkRuntime.IO.Core.vtkHttpSceneLoader;
    const vtkGenericRenderWindow = vtkRuntime.Rendering.Misc.vtkGenericRenderWindow;

    const app = new App({{ name: "Ladybug Tools vtk.js Preview", version: "1.1.0" }});
    const state = {{
      gardenRoot: null,
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

    const callTool = async (name, args) => {{
      const result = await app.callServerTool({{ name, arguments: args }});
      return result?.structuredContent ?? result?.structured_content ?? result;
    }};

    const refresh = async () => {{
      if (!state.gardenRoot) return;
      const preview = await callTool("{app_backend_tool_name(PREVIEW_STATE_TOOL)}", {{ garden_root: state.gardenRoot }});
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

    const loadArtifact = async (artifact) => {{
      setStatus(`Loading ${{artifact.name || artifact.path}}`);
      showNotice("");
      state.cameraState = captureCamera() || state.cameraState;
      const payload = await callTool("{app_backend_tool_name(PREVIEW_ARTIFACT_TOOL)}", {{
        garden_root: state.gardenRoot,
        artifact_path: artifact.path,
        revision: artifact.revision,
      }});
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

    app.ontoolresult = (result) => {{
      const content = result?.structuredContent ?? result?.structured_content ?? result;
      state.gardenRoot =
        content?.garden_root ||
        content?.session?.garden?.garden_root ||
        content?.garden?.garden_root ||
        state.gardenRoot;
      if (state.gardenRoot) {{
        refresh().catch((reason) => {{
          showNotice(reason instanceof Error ? reason.message : String(reason), true);
          setStatus("Preview failed");
        }});
      }}
    }};

    document.getElementById("axon").addEventListener("click", () => setCamera("axon"));
    document.getElementById("top").addEventListener("click", () => setCamera("top"));
    await app.connect();
    state.timer = window.setInterval(() => {{
      refresh().catch((reason) => {{
        showNotice(reason instanceof Error ? reason.message : String(reason), true);
        setStatus("Preview failed");
      }});
    }}, {POLL_INTERVAL_MS});
  </script>
</body>
</html>"""
