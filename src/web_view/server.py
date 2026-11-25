"""Local loopback HTTP server serving the Rune Web View WASM app and /api/* Garden endpoints."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest, garden_lock, utc_now_iso
from garden.paths import resolve_contained_path, windows_path_key
from web_view.launcher import discover_rune_web_bundle_dir
from web_view.protocol import (
    ensure_initial_interaction_state,
    interaction_state_file_path,
    present_file_path,
    read_interaction_state,
    read_present,
    write_interaction_state,
)

_MAX_INTERACTION_BYTES = 4 * 1024 * 1024
_STATIC_MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".wasm": "application/wasm",
    ".ttf": "font/ttf",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _stat_mtime_ns(path: Path | None) -> int | None:
    if path is None:
        return None
    try:
        if path.is_file():
            return path.stat().st_mtime_ns
    except OSError:
        return None
    return None


def _is_loopback_host(host: str) -> bool:
    return host.strip().lower() in {"127.0.0.1", "::1", "localhost"}


class _RuneWebServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls: type[BaseHTTPRequestHandler],
        *,
        bundle_dir: Path,
        garden_root: Path | None = None,
        hbjson_path: Path | None = None,
    ) -> None:
        self.bundle_dir = bundle_dir.resolve()
        self.garden_root = garden_root.resolve() if garden_root is not None else None
        self.hbjson_path = hbjson_path.resolve() if hbjson_path is not None else None
        self._standalone_lock = threading.Lock()
        self._standalone_interaction: dict[str, Any] = {
            "schema_version": "1",
            "garden_id": "standalone",
            "selected_targets": [],
            "annotations": [],
            "viewport": {
                "model_path": self.hbjson_path.name if self.hbjson_path is not None else None,
            },
            "pending_intents": [],
            "viewer_pid": None,
            "updated_at": utc_now_iso(),
        }
        super().__init__(server_address, handler_cls)

    def read_garden_id(self) -> str | None:
        if self.garden_root is None:
            return "standalone"
        try:
            return GardenManifest.read(self.garden_root).garden_id
        except Exception:
            return self.garden_root.name

    def read_present_payload(self) -> tuple[dict[str, Any] | None, int | None]:
        if self.garden_root is None:
            if self.hbjson_path is None:
                return None, None
            return (
                {
                    "schema_version": "1",
                    "revision": 1,
                    "garden_id": "standalone",
                    "view_type": "model",
                    "model_path": self.hbjson_path.name,
                    "color_by": "type",
                    "highlight_targets": [],
                    "isolation_mode": "highlight",
                    "validation_issues": [],
                    "camera": "axon",
                    "section": None,
                    "callouts": [],
                    "title": self.hbjson_path.stem,
                    "note": None,
                    "updated_at": utc_now_iso(),
                },
                _stat_mtime_ns(self.hbjson_path),
            )
        p_path = present_file_path(self.garden_root)
        return read_present(self.garden_root), _stat_mtime_ns(p_path)

    def read_interaction_payload(self) -> dict[str, Any]:
        if self.garden_root is None:
            with self._standalone_lock:
                return dict(self._standalone_interaction)
        try:
            return read_interaction_state(self.garden_root)
        except FileNotFoundError:
            return ensure_initial_interaction_state(self.garden_root)

    def update_interaction_payload(self, incoming: dict[str, Any]) -> dict[str, Any]:
        if self.garden_root is None:
            with self._standalone_lock:
                cur = self._standalone_interaction
                if isinstance(incoming.get("selected_targets"), list):
                    cur["selected_targets"] = incoming["selected_targets"]
                if isinstance(incoming.get("annotations"), list):
                    cur["annotations"] = incoming["annotations"]
                if isinstance(incoming.get("viewport"), dict):
                    cur["viewport"] = incoming["viewport"]
                cur["updated_at"] = utc_now_iso()
                return dict(cur)

        with garden_lock(self.garden_root):
            i_path = interaction_state_file_path(self.garden_root)
            if i_path.is_file():
                current = read_interaction_state(self.garden_root)
            else:
                current = ensure_initial_interaction_state(self.garden_root)
            if not current.get("garden_id") and isinstance(incoming.get("garden_id"), str):
                current["garden_id"] = incoming["garden_id"]
            if isinstance(incoming.get("selected_targets"), list):
                current["selected_targets"] = incoming["selected_targets"]
            if isinstance(incoming.get("annotations"), list):
                current["annotations"] = incoming["annotations"]
            if isinstance(incoming.get("viewport"), dict):
                current["viewport"] = incoming["viewport"]
            write_interaction_state(self.garden_root, current)
            return current

    def read_session_payload(self) -> dict[str, Any]:
        if self.garden_root is None:
            return {"active": True, "mode": "standalone_hbjson"}
        try:
            sess_path = resolve_contained_path(
                self.garden_root, "tmp/web_view/session.json", label="Web View session"
            )
            if sess_path.is_file():
                return json.loads(sess_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def resolve_active_model_rel_and_mtime(
        self,
        present: dict[str, Any] | None,
        interaction: dict[str, Any] | None,
    ) -> tuple[str | None, int | None, str | None]:
        if self.garden_root is None:
            if self.hbjson_path is not None and self.hbjson_path.is_file():
                return (
                    self.hbjson_path.name,
                    _stat_mtime_ns(self.hbjson_path),
                    self.hbjson_path.stem,
                )
            return None, None, None

        rel_path: str | None = None
        if isinstance(present, dict) and isinstance(present.get("model_path"), str):
            rel_path = present["model_path"]
        elif isinstance(interaction, dict):
            vp = interaction.get("viewport")
            if isinstance(vp, dict) and isinstance(vp.get("model_path"), str):
                rel_path = vp["model_path"]

        if rel_path:
            try:
                resolved = resolve_contained_path(self.garden_root, rel_path, label="Model path")
                mtime = _stat_mtime_ns(resolved)
                label = (
                    (present.get("title") if isinstance(present, dict) else None)
                    or resolved.stem
                    or self.garden_root.name
                )
                return rel_path, mtime, str(label)
            except Exception:
                return rel_path, None, self.garden_root.name

        label = (
            (present.get("title") if isinstance(present, dict) else None)
            or self.garden_root.name
        )
        return None, None, str(label)


class _RuneWebRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        cache_control: str = "no-store",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, raw, "application/json; charset=utf-8", cache_control="no-store")

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> bool:
        server: _RuneWebServer = self.server  # type: ignore[assignment]
        if path == "/api/bootstrap":
            present, present_mtime = server.read_present_payload()
            interaction = server.read_interaction_payload()
            model_path, model_mtime, model_label = server.resolve_active_model_rel_and_mtime(
                present, interaction
            )
            self._send_json(
                HTTPStatus.OK,
                {
                    "garden_root": str(server.garden_root) if server.garden_root else None,
                    "garden_id": server.read_garden_id(),
                    "model_path": model_path,
                    "model_label": model_label,
                    "model_mtime_ns": model_mtime,
                    "present_mtime_ns": present_mtime,
                    "present": present,
                    "interaction_state": interaction,
                },
            )
            return True

        if path == "/api/status":
            present, present_mtime = server.read_present_payload()
            rev = int(present.get("revision") or 0) if isinstance(present, dict) else 0
            model_path, model_mtime, _ = server.resolve_active_model_rel_and_mtime(present, None)
            self._send_json(
                HTTPStatus.OK,
                {
                    "present_revision": rev,
                    "present_mtime_ns": present_mtime,
                    "model_path": model_path,
                    "model_mtime_ns": model_mtime,
                },
            )
            return True

        if path == "/api/present":
            present, _ = server.read_present_payload()
            self._send_json(HTTPStatus.OK, present)
            return True

        if path == "/api/interaction":
            self._send_json(HTTPStatus.OK, server.read_interaction_payload())
            return True

        if path == "/api/session":
            self._send_json(HTTPStatus.OK, server.read_session_payload())
            return True

        if path == "/api/model":
            rel_values = query.get("path") or []
            rel = rel_values[0] if rel_values else ""
            if not rel:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "Missing ?path= query parameter")
                return True
            if Path(rel).is_absolute() or os.path.splitdrive(rel)[0]:
                self._send_error_json(HTTPStatus.FORBIDDEN, "Absolute model paths are not allowed")
                return True
            if ".." in Path(rel).parts:
                self._send_error_json(HTTPStatus.FORBIDDEN, "Path traversal is not allowed")
                return True
            if Path(rel).suffix.lower() not in {".hbjson", ".json"}:
                self._send_error_json(HTTPStatus.FORBIDDEN, "Only .hbjson/.json files may be served")
                return True

            if server.garden_root is None:
                if server.hbjson_path is None or rel != server.hbjson_path.name:
                    self._send_error_json(HTTPStatus.FORBIDDEN, "Model outside standalone target")
                    return True
                resolved = server.hbjson_path
            else:
                try:
                    resolved = resolve_contained_path(
                        server.garden_root, rel, label="Model path"
                    )
                except Exception as exc:
                    self._send_error_json(HTTPStatus.FORBIDDEN, str(exc))
                    return True
                if not resolved.is_relative_to(server.garden_root):
                    self._send_error_json(HTTPStatus.FORBIDDEN, "Model escapes garden root")
                    return True

            if not resolved.is_file():
                self._send_error_json(HTTPStatus.NOT_FOUND, f"Model file not found: {rel}")
                return True

            raw = resolved.read_bytes()
            self._send_bytes(
                HTTPStatus.OK,
                raw,
                "application/json; charset=utf-8",
                cache_control="no-store",
            )
            return True

        return False

    def _serve_static(self, path: str) -> None:
        server: _RuneWebServer = self.server  # type: ignore[assignment]
        rel = "index.html" if path in {"", "/"} else path.lstrip("/")
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts or not rel_path.parts:
            self._send_error_json(HTTPStatus.FORBIDDEN, "Invalid static path")
            return
        candidate = (server.bundle_dir / rel_path).resolve()
        if not candidate.is_relative_to(server.bundle_dir):
            self._send_error_json(HTTPStatus.FORBIDDEN, "Static path escapes bundle root")
            return
        if not candidate.is_file():
            self._send_error_json(HTTPStatus.NOT_FOUND, f"Asset not found: {rel}")
            return
        ctype = _STATIC_MIME_TYPES.get(
            candidate.suffix.lower(), "application/octet-stream"
        )
        self._send_bytes(
            HTTPStatus.OK,
            candidate.read_bytes(),
            ctype,
            cache_control="no-cache",
        )

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path.startswith("/api/"):
            if not self._handle_api_get(parsed.path, query):
                self._send_error_json(HTTPStatus.NOT_FOUND, f"Unknown API endpoint: {parsed.path}")
            return
        self._serve_static(parsed.path)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path.startswith("/api/"):
            if not self._handle_api_get(parsed.path, query):
                self._send_error_json(HTTPStatus.NOT_FOUND, f"Unknown API endpoint: {parsed.path}")
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/api/interaction":
            self._send_error_json(HTTPStatus.NOT_FOUND, f"Unknown POST endpoint: {parsed.path}")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
            return
        if length < 0 or length > _MAX_INTERACTION_BYTES:
            self._send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Payload too large")
            return
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, f"Invalid JSON body: {exc}")
            return
        if not isinstance(payload, dict):
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Interaction payload must be a JSON object")
            return
        server: _RuneWebServer = self.server  # type: ignore[assignment]
        updated = server.update_interaction_payload(payload)
        self._send_json(HTTPStatus.OK, {"status": "ok", "interaction_state": updated})


_WEB_SERVERS: dict[str, tuple[_RuneWebServer, threading.Thread, dict[str, Any]]] = {}
_SERVER_LOCK = threading.Lock()


def start_rune_web_server(
    *,
    garden_root: str | Path | None = None,
    hbjson_path: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
    bundle_dir: Path | None = None,
) -> dict[str, Any]:
    """Start (or reuse) a loopback HTTP server hosting the Rune Web View browser app."""
    if not _is_loopback_host(host):
        raise ValueError(f"Refusing non-loopback bind host {host!r}; use 127.0.0.1 or localhost.")
    resolved_bundle = (bundle_dir or discover_rune_web_bundle_dir())
    if resolved_bundle is None:
        raise FileNotFoundError(
            "Rune Web View bundle not found. Run scripts/build_rune_web.py to build rune_viewer/target/web/."
        )
    resolved_bundle = Path(resolved_bundle).expanduser().resolve()

    if garden_root is not None:
        root_path = Path(garden_root).expanduser().resolve()
        key = windows_path_key(root_path)
        standalone_path = None
    elif hbjson_path is not None:
        root_path = None
        standalone_path = Path(hbjson_path).expanduser().resolve()
        key = windows_path_key(standalone_path)
    else:
        raise ValueError("Provide either garden_root or hbjson_path.")

    with _SERVER_LOCK:
        existing = _WEB_SERVERS.get(key)
        if existing is not None:
            srv, thread, info = existing
            if thread.is_alive():
                return {**info, "status": "already_running"}
            _WEB_SERVERS.pop(key, None)

        bind_host = "127.0.0.1" if host.strip().lower() == "localhost" else host.strip()
        httpd = _RuneWebServer(
            (bind_host, int(port)),
            _RuneWebRequestHandler,
            bundle_dir=resolved_bundle,
            garden_root=root_path,
            hbjson_path=standalone_path,
        )
        bound_host, bound_port = httpd.server_address[:2]
        thread = threading.Thread(
            target=httpd.serve_forever,
            kwargs={"poll_interval": 0.25},
            name=f"lbt-rune-web-{bound_port}",
            daemon=True,
        )
        thread.start()
        info = {
            "status": "started",
            "host": str(bound_host),
            "port": int(bound_port),
            "url": f"http://{bound_host}:{bound_port}/",
            "bundle_dir": str(resolved_bundle),
            "garden_root": str(root_path) if root_path is not None else None,
            "hbjson_path": str(standalone_path) if standalone_path is not None else None,
        }
        _WEB_SERVERS[key] = (httpd, thread, info)
        return dict(info)


def get_rune_web_server_info(garden_root: str | Path) -> dict[str, Any] | None:
    """Return running web server metadata for a Garden, if active."""
    root = Path(garden_root).expanduser().resolve()
    key = windows_path_key(root)
    with _SERVER_LOCK:
        entry = _WEB_SERVERS.get(key)
        if entry is None:
            return None
        _, thread, info = entry
        if not thread.is_alive():
            _WEB_SERVERS.pop(key, None)
            return None
        return dict(info)


def stop_rune_web_server(*, garden_root: str | Path) -> dict[str, Any]:
    """Shut down the running HTTP server for a Garden if active."""
    root = Path(garden_root).expanduser().resolve()
    key = windows_path_key(root)
    with _SERVER_LOCK:
        entry = _WEB_SERVERS.pop(key, None)
    if entry is None:
        return {"status": "not_running", "garden_root": str(root)}
    httpd, thread, info = entry
    try:
        httpd.shutdown()
        httpd.server_close()
    except Exception:
        pass
    thread.join(timeout=2.0)
    return {
        "status": "stopped",
        "garden_root": str(root),
        "port": info.get("port"),
        "url": info.get("url"),
    }


def stop_all_rune_web_servers() -> None:
    """Shut down all tracked Rune Web View HTTP servers on interpreter exit."""
    with _SERVER_LOCK:
        entries = list(_WEB_SERVERS.values())
        _WEB_SERVERS.clear()
    for httpd, thread, _ in entries:
        try:
            httpd.shutdown()
            httpd.server_close()
        except Exception:
            pass
        thread.join(timeout=1.0)


atexit.register(stop_all_rune_web_servers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the Rune 3D Web View browser app on loopback HTTP."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--garden", type=Path, help="Garden root directory.")
    target.add_argument("--hbjson", type=Path, help="Standalone Honeybee .hbjson file.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback bind host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765; 0 for ephemeral).")
    parser.add_argument("--open", action="store_true", help="Open the live URL in the default browser.")
    args = parser.parse_args(argv)

    info = start_rune_web_server(
        garden_root=args.garden,
        hbjson_path=args.hbjson,
        host=args.host,
        port=args.port,
    )
    print(f"Rune Web View serving at {info['url']}", flush=True)
    if args.open:
        webbrowser.open(str(info["url"]))

    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if args.garden is not None:
            stop_rune_web_server(garden_root=args.garden)
        else:
            stop_all_rune_web_servers()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
