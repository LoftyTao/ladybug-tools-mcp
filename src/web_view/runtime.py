"""In-process Web View runtime for MCP demo mode."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from web_view.local_viewer import (
    NoCacheHTTPRequestHandler,
    _assert_port_available,
    _garden_watched_paths,
    _source_signature,
    build_garden_viewer_workspace,
)
from web_view.session import start_web_view_session, stop_web_view_session


DEFAULT_WEB_VIEW_PORT = 3127


class WebViewHTTPServer(ThreadingHTTPServer):
    """Threaded local preview server with explicit lifecycle management."""

    allow_reuse_address = True
    daemon_threads = True


@dataclass
class WebViewRuntime:
    garden_root: str
    output_dir: str
    host: str
    port: int
    url: str
    server: WebViewHTTPServer
    server_thread: threading.Thread
    watcher_stop: threading.Event
    watcher_thread: threading.Thread


_RUNTIMES: dict[str, WebViewRuntime] = {}
_LOCK = threading.Lock()


def _runtime_key(garden_root: str) -> str:
    return str(Path(garden_root).expanduser().resolve())


def _default_output_dir(garden_root: Path) -> Path:
    return garden_root / "tmp" / "web_view" / "viewer"


def _viewer_summary(runtime: WebViewRuntime) -> dict[str, Any]:
    return {
        "status": "serving",
        "url": runtime.url,
        "host": runtime.host,
        "port": runtime.port,
        "output_dir": runtime.output_dir,
        "browser_opening": "host_required",
    }


def _start_server_thread(*, output_dir: Path, host: str, port: int) -> tuple[
    WebViewHTTPServer,
    threading.Thread,
    int,
]:
    handler = partial(NoCacheHTTPRequestHandler, directory=str(output_dir))
    server = WebViewHTTPServer((host, port), handler)
    actual_port = int(server.server_address[1])
    thread = threading.Thread(
        target=server.serve_forever,
        name=f"web-view-server-{actual_port}",
        daemon=True,
    )
    thread.start()
    return server, thread, actual_port


def _start_watcher_thread(
    *,
    garden_root: Path,
    output_dir: Path,
    title: str,
    interval_seconds: float,
    stop_event: threading.Event,
) -> threading.Thread:
    def _watch() -> None:
        last_signature = _source_signature(_garden_watched_paths(garden_root))
        while not stop_event.wait(interval_seconds):
            try:
                watched_paths = _garden_watched_paths(garden_root)
                next_signature = _source_signature(watched_paths)
            except OSError:
                continue
            if next_signature == last_signature:
                continue
            try:
                build_garden_viewer_workspace(
                    garden_root=str(garden_root),
                    output_dir=str(output_dir),
                    title=title,
                )
                last_signature = next_signature
            except Exception:
                continue

    thread = threading.Thread(
        target=_watch,
        name="web-view-runtime-watch",
        daemon=True,
    )
    thread.start()
    return thread


def stop_web_view_runtime(*, garden_root: str) -> dict[str, Any] | None:
    """Stop the in-process viewer server for one Garden, if present."""
    key = _runtime_key(garden_root)
    with _LOCK:
        runtime = _RUNTIMES.pop(key, None)
    if runtime is None:
        return None

    runtime.watcher_stop.set()
    runtime.server.shutdown()
    runtime.server.server_close()
    runtime.watcher_thread.join(timeout=2)
    runtime.server_thread.join(timeout=2)
    return {
        "status": "stopped",
        "url": runtime.url,
        "host": runtime.host,
        "port": runtime.port,
        "output_dir": runtime.output_dir,
    }


def start_web_view_runtime(
    *,
    garden_root: str,
    name: str,
    host: str = "127.0.0.1",
    port: int = DEFAULT_WEB_VIEW_PORT,
    output_dir: str | None = None,
    watch_interval_seconds: float = 0.5,
) -> dict[str, Any]:
    """Start Web View Mode and its local preview server for one Garden."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    key = str(garden_root_path)
    output_dir_path = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else _default_output_dir(garden_root_path)
    )

    with _LOCK:
        existing = _RUNTIMES.get(key)
    if existing is not None:
        stop_web_view_runtime(garden_root=key)

    if port != 0:
        _assert_port_available(host, port)

    session_result = start_web_view_session(garden_root=key, name=name)
    try:
        workspace = build_garden_viewer_workspace(
            garden_root=key,
            output_dir=str(output_dir_path),
            title=name,
        )
        server, server_thread, actual_port = _start_server_thread(
            output_dir=output_dir_path,
            host=host,
            port=port,
        )
        watcher_stop = threading.Event()
        watcher_thread = _start_watcher_thread(
            garden_root=garden_root_path,
            output_dir=output_dir_path,
            title=name,
            interval_seconds=watch_interval_seconds,
            stop_event=watcher_stop,
        )
    except Exception:
        stop_web_view_session(garden_root=key)
        raise

    runtime = WebViewRuntime(
        garden_root=key,
        output_dir=str(output_dir_path),
        host=host,
        port=actual_port,
        url=f"http://{host}:{actual_port}",
        server=server,
        server_thread=server_thread,
        watcher_stop=watcher_stop,
        watcher_thread=watcher_thread,
    )
    with _LOCK:
        _RUNTIMES[key] = runtime

    return {
        **session_result,
        "viewer": _viewer_summary(runtime),
        "workspace": workspace,
    }
