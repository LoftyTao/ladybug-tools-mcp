"""Build and serve a minimal local React + vtk.js viewer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from web_view.session import SESSION_RELATIVE_PATH, get_web_view_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
WEB_VIEW_NODE_MODULES = Path(__file__).resolve().parent / "node_modules"
REMOTION_NODE_MODULES = PROJECT_ROOT / "remotion" / "node_modules"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tests" / ".artifacts" / "web_view" / "viewer"
CONFIG_POLL_INTERVAL_MS = 1500


def _viewer_node_modules_dir() -> Path | None:
    for candidate in (WEB_VIEW_NODE_MODULES, REMOTION_NODE_MODULES):
        if candidate.is_dir():
            return candidate
    return None


def _esbuild_exe(node_modules_dir: Path) -> Path:
    return node_modules_dir / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")


def _validate_vtkjs_path(vtkjs_path: str) -> Path:
    path = Path(vtkjs_path).expanduser().resolve()
    if path.suffix.lower() != ".vtkjs":
        raise ValueError(f"Web View local viewer expects a .vtkjs file; got {path}")
    if not path.is_file():
        raise ValueError(f"vtkjs file was not found: {path}")
    return path


def _validate_model_path(model_path: str) -> Path:
    path = Path(model_path).expanduser().resolve()
    if path.suffix.lower() not in {".hbjson", ".json"}:
        raise ValueError(f"Web View local viewer expects an HBJSON model; got {path}")
    if not path.is_file():
        raise ValueError(f"Honeybee model file was not found: {path}")
    return path


def _copy_static_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STATIC_DIR / "index.html", output_dir / "index.html")


def _bundle_viewer(output_dir: Path) -> Path:
    node_modules_dir = _viewer_node_modules_dir()
    if node_modules_dir is None or not _esbuild_exe(node_modules_dir).is_file():
        raise ValueError(
            "Local Web View bundling requires frontend dependencies. "
            "Run npm install in src/web_view first."
        )
    bundle_path = output_dir / "viewer.bundle.js"
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules_dir)
    result = subprocess.run(
        [
            str(_esbuild_exe(node_modules_dir)),
            str(STATIC_DIR / "viewer-entry.js"),
            "--bundle",
            "--format=esm",
            "--platform=browser",
            "--target=es2020",
            f"--outfile={bundle_path}",
        ],
        cwd=str(node_modules_dir.parent),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Failed to bundle local vtk.js viewer: {message}")
    return bundle_path


def _source_revision(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _source_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (str(path), path.stat().st_mtime_ns, path.stat().st_size)
        for path in paths
        if path.is_file()
    )


def _selected_viewer_source(web_view_config: dict[str, Any]) -> dict[str, Any]:
    active_step = web_view_config.get("active_step")
    if isinstance(active_step, dict):
        viewer_source = active_step.get("viewer_source")
        if isinstance(viewer_source, dict):
            return viewer_source

    latest_artifact = web_view_config.get("latest_vtkjs_artifact")
    if isinstance(latest_artifact, dict):
        return latest_artifact

    raise ValueError(
        "Garden Web View requires a visualization_vtkjs artifact. "
        "Export a VisualizationSet with visualization_set_to_vtkjs first."
    )


def _optional_viewer_source(web_view_config: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return _selected_viewer_source(web_view_config)
    except ValueError:
        return None


def _copy_viewer_source_artifact(
    *,
    viewer_root: Path,
    viewer_source: dict[str, Any],
) -> Path:
    source_path = _validate_vtkjs_path(str(viewer_source.get("absolute_path") or ""))
    artifact_path = viewer_root / "artifacts" / source_path.name
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, artifact_path)
    return artifact_path


def _garden_watched_paths(garden_root: Path) -> list[Path]:
    paths = [garden_root / "garden.json", garden_root / SESSION_RELATIVE_PATH]
    try:
        viewer_source = _selected_viewer_source(
            get_web_view_config(garden_root=str(garden_root))
        )
    except ValueError:
        return [path for path in paths if path.is_file()]

    artifact_path = Path(str(viewer_source.get("absolute_path") or "")).resolve()
    paths.append(artifact_path)
    return [path for path in paths if path.is_file()]


def build_vtkjs_viewer_workspace(
    *,
    vtkjs_path: str,
    output_dir: str | None = None,
    title: str = "Ladybug Tools Web View",
    model_path: str | None = None,
) -> dict[str, Any]:
    """Build a static local viewer workspace for one native `.vtkjs` file."""
    source_path = _validate_vtkjs_path(vtkjs_path)
    viewer_root = Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_OUTPUT_DIR
    artifacts_dir = viewer_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    _copy_static_files(viewer_root)

    artifact_path = artifacts_dir / source_path.name
    shutil.copy2(source_path, artifact_path)
    source_files = [source_path]
    config = {
        "title": title,
        "revision": "",
        "artifact": {
            "name": source_path.name,
            "path": f"artifacts/{source_path.name}",
            "source_path": str(source_path),
        },
        "policy": {
            "local_only": True,
            "geometry_source": "Ladybug Tools SDK/MCP native vtkjs artifact",
            "viewer": "React + vtk.js",
            "visual_effects": "Loaded from SDK/MCP-exported vtkjs files only",
        },
        "hot_reload": {
            "enabled": True,
            "config_poll_interval_ms": CONFIG_POLL_INTERVAL_MS,
        },
        "model": None,
    }
    model_artifact_path = None
    if model_path:
        source_model_path = _validate_model_path(model_path)
        model_artifact_path = artifacts_dir / source_model_path.name
        shutil.copy2(source_model_path, model_artifact_path)
        source_files.append(source_model_path)
        config["model"] = {
            "name": source_model_path.name,
            "path": f"artifacts/{source_model_path.name}",
            "source_path": str(source_model_path),
        }
    config["revision"] = _source_revision(source_files)
    config_path = viewer_root / "config.json"
    with config_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")

    bundle_path = _bundle_viewer(viewer_root)
    return {
        "viewer_root": str(viewer_root),
        "index_path": str(viewer_root / "index.html"),
        "config_path": str(config_path),
        "bundle_path": str(bundle_path),
        "artifact_path": str(artifact_path),
        "artifact_name": source_path.name,
        "model_path": str(model_artifact_path) if model_artifact_path else None,
    }


def build_garden_viewer_workspace(
    *,
    garden_root: str,
    output_dir: str | None = None,
    title: str = "Ladybug Tools Web View",
) -> dict[str, Any]:
    """Build a static local viewer workspace that follows a Garden Web View session."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    web_view_config = get_web_view_config(garden_root=str(garden_root_path))
    viewer_source = _optional_viewer_source(web_view_config)
    viewer_root = (
        Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_OUTPUT_DIR
    )
    viewer_root.mkdir(parents=True, exist_ok=True)
    _copy_static_files(viewer_root)

    revision_paths = _garden_watched_paths(garden_root_path)
    artifact_path = None
    artifact_config = None
    if viewer_source is not None:
        artifact_path = _copy_viewer_source_artifact(
            viewer_root=viewer_root,
            viewer_source=viewer_source,
        )
    if artifact_path is not None and artifact_path not in revision_paths:
        revision_paths.append(artifact_path)
    if artifact_path is not None and viewer_source is not None:
        artifact_config = {
            "name": artifact_path.name,
            "path": f"artifacts/{artifact_path.name}",
            "source_path": str(viewer_source["absolute_path"]),
            "garden_artifact_path": viewer_source["artifact_path"],
            "garden_artifact_name": viewer_source.get("artifact_name"),
        }
    config = {
        "title": title,
        "revision": _source_revision(revision_paths),
        "artifact": artifact_config,
        "policy": {
            "local_only": True,
            "geometry_source": "Garden visualization_vtkjs artifact",
            "viewer": "React + vtk.js",
            "visual_effects": "Loaded from SDK/MCP-exported vtkjs files only",
        },
        "hot_reload": {
            "enabled": True,
            "config_poll_interval_ms": CONFIG_POLL_INTERVAL_MS,
        },
        "model": None,
        "garden": web_view_config["garden"],
        "active_step": web_view_config.get("active_step"),
        "preview_kinds": web_view_config.get("preview_kinds", []),
        "latest_vtkjs_artifact": web_view_config.get("latest_vtkjs_artifact"),
    }
    config_path = viewer_root / "config.json"
    with config_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")

    bundle_path = _bundle_viewer(viewer_root)
    return {
        "viewer_root": str(viewer_root),
        "index_path": str(viewer_root / "index.html"),
        "config_path": str(config_path),
        "bundle_path": str(bundle_path),
        "artifact_path": str(artifact_path) if artifact_path else None,
        "artifact_name": artifact_path.name if artifact_path else None,
        "garden_root": str(garden_root_path),
        "active_step_id": (web_view_config.get("active_step") or {}).get("id"),
    }


class NoCacheHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Serve local viewer files without browser cache during preview sessions."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def _assert_port_available(host: str, port: int) -> None:
    """Fail early with a clear message when a preview port is already occupied."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
    except OSError as exc:
        raise RuntimeError(
            f"Web View local server port is already in use: {host}:{port}. "
            "Stop the existing Web View server or choose another port."
        ) from exc


def start_workspace_watcher(
    *,
    vtkjs_path: str,
    output_dir: str,
    title: str,
    model_path: str | None = None,
    interval_seconds: float = 1.0,
) -> threading.Thread:
    """Start a background watcher that rebuilds the viewer workspace on source changes."""
    source_path = _validate_vtkjs_path(vtkjs_path)
    watched_paths = [source_path]
    if model_path:
        watched_paths.append(_validate_model_path(model_path))

    def _watch() -> None:
        last_signature = _source_signature(watched_paths)
        while True:
            time.sleep(interval_seconds)
            try:
                next_signature = _source_signature(watched_paths)
            except OSError as exc:
                print(f"Web View watch skipped: {exc}", file=sys.stderr)
                continue
            if next_signature == last_signature:
                continue
            try:
                build_vtkjs_viewer_workspace(
                    vtkjs_path=str(source_path),
                    output_dir=output_dir,
                    title=title,
                    model_path=model_path,
                )
                last_signature = next_signature
                print("Web View workspace rebuilt after source change.")
            except Exception as exc:  # pragma: no cover - manual preview resilience
                print(f"Web View watch rebuild failed: {exc}", file=sys.stderr)

    thread = threading.Thread(target=_watch, name="web-view-watch", daemon=True)
    thread.start()
    return thread


def start_garden_workspace_watcher(
    *,
    garden_root: str,
    output_dir: str,
    title: str,
    interval_seconds: float = 1.0,
) -> threading.Thread:
    """Start a watcher that rebuilds the viewer when Garden preview state changes."""
    garden_root_path = Path(garden_root).expanduser().resolve()

    def _watch() -> None:
        last_signature = _source_signature(_garden_watched_paths(garden_root_path))
        while True:
            time.sleep(interval_seconds)
            try:
                watched_paths = _garden_watched_paths(garden_root_path)
                next_signature = _source_signature(watched_paths)
            except OSError as exc:
                print(f"Garden Web View watch skipped: {exc}", file=sys.stderr)
                continue
            if next_signature == last_signature:
                continue
            try:
                build_garden_viewer_workspace(
                    garden_root=str(garden_root_path),
                    output_dir=output_dir,
                    title=title,
                )
                last_signature = next_signature
                print("Garden Web View workspace rebuilt after preview change.")
            except Exception as exc:  # pragma: no cover - manual preview resilience
                print(f"Garden Web View watch rebuild failed: {exc}", file=sys.stderr)

    thread = threading.Thread(target=_watch, name="garden-web-view-watch", daemon=True)
    thread.start()
    return thread


def serve_directory(*, directory: str, host: str = "127.0.0.1", port: int = 3110) -> None:
    """Serve a built local viewer workspace."""
    root = Path(directory).expanduser().resolve()
    _assert_port_available(host, port)
    handler = partial(NoCacheHTTPRequestHandler, directory=str(root))
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Serving Ladybug Tools Web View at http://{host}:{port}")
    print(f"Viewer root: {root}")
    httpd.serve_forever()


def main() -> None:
    """Command-line entry point for local manual preview."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "vtkjs_path",
        nargs="?",
        help="Path to a local .vtkjs artifact.",
    )
    parser.add_argument(
        "--garden-root",
        default=None,
        help="Garden root whose Web View session should drive the preview.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--title", default="Ladybug Tools Web View")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3110)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Rebuild the local viewer workspace when source files change.",
    )
    parser.add_argument("--watch-interval", type=float, default=1.0)
    args = parser.parse_args()
    if args.garden_root and args.vtkjs_path:
        parser.error("Use either vtkjs_path or --garden-root, not both.")
    if args.garden_root:
        result = build_garden_viewer_workspace(
            garden_root=args.garden_root,
            output_dir=args.output_dir,
            title=args.title,
        )
    elif args.vtkjs_path:
        result = build_vtkjs_viewer_workspace(
            vtkjs_path=args.vtkjs_path,
            output_dir=args.output_dir,
            title=args.title,
            model_path=args.model_path,
        )
    else:
        parser.error("Either vtkjs_path or --garden-root is required.")
    print(json.dumps(result, indent=2))
    if args.watch:
        if args.garden_root:
            start_garden_workspace_watcher(
                garden_root=args.garden_root,
                output_dir=args.output_dir,
                title=args.title,
                interval_seconds=args.watch_interval,
            )
        else:
            start_workspace_watcher(
                vtkjs_path=args.vtkjs_path,
                output_dir=args.output_dir,
                title=args.title,
                model_path=args.model_path,
                interval_seconds=args.watch_interval,
            )
    serve_directory(directory=result["viewer_root"], host=args.host, port=args.port)


if __name__ == "__main__":
    main()
