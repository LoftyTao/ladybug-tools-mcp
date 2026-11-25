"""Process discovery, GUI lifecycle, and headless snap runner for lbt-rune-viewer."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from garden.paths import windows_path_key
from web_view.protocol import (
    ensure_initial_interaction_state,
    read_interaction_state,
    write_interaction_state,
)

_VIEWER_PROCESSES: dict[str, subprocess.Popen[Any]] = {}
_PROCESS_LOCK = threading.Lock()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def discover_rune_viewer_binary() -> Path | None:
    """Discover ``lbt-rune-viewer`` via env var, workspace target dirs, packaged resources, or PATH."""
    exe_name = "lbt-rune-viewer.exe" if os.name == "nt" else "lbt-rune-viewer"
    candidates: list[Path] = []

    env_override = os.environ.get("LBT_RUNE_VIEWER_BIN")
    if env_override and env_override.strip():
        env_path = Path(env_override.strip()).expanduser()
        if env_path.is_file():
            return env_path.resolve()
        which_env = shutil.which(env_override.strip())
        if which_env:
            return Path(which_env).resolve()

    candidates.extend(
        [
            _REPO_ROOT / "rune_viewer" / "target" / "release" / exe_name,
            _REPO_ROOT / "rune_viewer" / "target" / "debug" / exe_name,
            _PACKAGE_ROOT / "ladybug_tools_mcp" / "resources" / "rune_viewer" / exe_name,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    for cmd_name in (exe_name, "lbt-rune-viewer"):
        found = shutil.which(cmd_name)
        if found:
            return Path(found).resolve()
    return None


def discover_rune_web_bundle_dir() -> Path | None:
    """Discover the built browser WASM bundle directory containing index.html, app.js, app_bg.wasm."""
    candidates: list[Path] = []
    env_override = os.environ.get("LBT_RUNE_WEB_DIR")
    if env_override and env_override.strip():
        candidates.append(Path(env_override.strip()).expanduser())

    candidates.extend(
        [
            _REPO_ROOT / "rune_viewer" / "target" / "web",
            _PACKAGE_ROOT / "ladybug_tools_mcp" / "resources" / "rune_viewer" / "web",
        ]
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if (
            (resolved / "index.html").is_file()
            and (resolved / "app.js").is_file()
            and (resolved / "app_bg.wasm").is_file()
        ):
            return resolved
    return None


def can_open_rune_window() -> tuple[bool, str | None]:
    """Return whether launching a desktop GUI window is supported in the current environment."""
    if os.environ.get("LBT_RUNE_VIEWER_NO_WINDOW", "").strip().lower() in {"1", "true", "yes"}:
        return False, "GUI window launch disabled by LBT_RUNE_VIEWER_NO_WINDOW."
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        return (
            False,
            "No DISPLAY or WAYLAND_DISPLAY environment variable detected (headless Linux).",
        )
    return True, None


def _is_pid_alive(pid: int | None) -> bool:
    if pid is None or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def is_rune_viewer_running(garden_root: str | Path) -> bool:
    """Return whether a live ``lbt-rune-viewer`` process is active for this Garden."""
    root = Path(garden_root).expanduser().resolve()
    key = windows_path_key(root)
    with _PROCESS_LOCK:
        proc = _VIEWER_PROCESSES.get(key)
        if proc is not None:
            if proc.poll() is None:
                return True
            _VIEWER_PROCESSES.pop(key, None)

    try:
        state = read_interaction_state(root)
    except Exception:
        return False
    return _is_pid_alive(state.get("viewer_pid"))


def launch_rune_viewer(
    *,
    garden_root: str | Path,
    binary_path: Path | None = None,
) -> dict[str, Any]:
    """Spawn or reuse a ``lbt-rune-viewer --garden <root>`` GUI process."""
    root = Path(garden_root).expanduser().resolve()
    key = windows_path_key(root)

    with _PROCESS_LOCK:
        existing = _VIEWER_PROCESSES.get(key)
        if existing is not None and existing.poll() is None:
            return {
                "status": "already_running",
                "pid": existing.pid,
                "binary_path": str(binary_path or discover_rune_viewer_binary() or ""),
                "garden_root": str(root),
            }
        _VIEWER_PROCESSES.pop(key, None)

    state = ensure_initial_interaction_state(root)
    state_pid = state.get("viewer_pid")
    if _is_pid_alive(state_pid):
        return {
            "status": "already_running",
            "pid": state_pid,
            "binary_path": str(binary_path or discover_rune_viewer_binary() or ""),
            "garden_root": str(root),
        }

    exe = binary_path or discover_rune_viewer_binary()
    if exe is None:
        raise FileNotFoundError(
            "lbt-rune-viewer binary not found. Set LBT_RUNE_VIEWER_BIN or build rune_viewer first."
        )

    popen_kwargs: dict[str, Any] = {
        "cwd": str(root),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen([str(exe), "--garden", str(root)], **popen_kwargs)
    with _PROCESS_LOCK:
        _VIEWER_PROCESSES[key] = proc

    state["viewer_pid"] = proc.pid
    write_interaction_state(root, state)
    return {
        "status": "started",
        "pid": proc.pid,
        "binary_path": str(exe),
        "garden_root": str(root),
    }


def stop_rune_viewer(*, garden_root: str | Path) -> dict[str, Any]:
    """Stop a tracked ``lbt-rune-viewer`` process for one Garden if running."""
    root = Path(garden_root).expanduser().resolve()
    key = windows_path_key(root)
    with _PROCESS_LOCK:
        proc = _VIEWER_PROCESSES.pop(key, None)

    stopped_pid: int | None = None
    status = "not_running"
    if proc is not None:
        stopped_pid = proc.pid
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
            status = "stopped"
        else:
            status = "already_exited"

    try:
        state = read_interaction_state(root)
    except Exception:
        state = None

    if isinstance(state, dict) and state.get("viewer_pid") is not None:
        if stopped_pid == state.get("viewer_pid") or not _is_pid_alive(state.get("viewer_pid")):
            state["viewer_pid"] = None
            write_interaction_state(root, state)

    return {
        "status": status,
        "pid": stopped_pid,
        "garden_root": str(root),
    }


def _snap_view_arg(view: str | dict[str, Any] | None) -> str | None:
    if view is None:
        return None
    if isinstance(view, str):
        cleaned = view.strip().lower()
        alias_map = {
            "front": "south",
            "back": "north",
            "left": "west",
            "right": "east",
            "ne": "axon",
            "nw": "axon",
            "se": "axon",
            "sw": "axon",
        }
        return alias_map.get(cleaned, cleaned) or None
    if isinstance(view, dict):
        pos = view.get("position")
        tgt = view.get("target")
        if isinstance(pos, (list, tuple)) and isinstance(tgt, (list, tuple)) and len(pos) == 3 and len(tgt) == 3:
            dx = float(pos[0]) - float(tgt[0])
            dy = float(pos[1]) - float(tgt[1])
            dz = float(pos[2]) - float(tgt[2])
            if abs(dz) >= max(abs(dx), abs(dy)) * 2.0 and dz > 0:
                return "top"
            if abs(dx) >= abs(dy) * 2.0:
                return "east" if dx >= 0 else "west"
            if abs(dy) >= abs(dx) * 2.0:
                return "north" if dy >= 0 else "south"
        return "axon"
    return None


def run_headless_snap(
    *,
    garden_root: str | Path,
    output_png_path: str | Path,
    hbjson_path: str | Path | None = None,
    view: str | dict[str, Any] | None = None,
    color_by: str | None = None,
    width: int = 1280,
    height: int = 720,
    timeout_secs: float = 30.0,
    binary_path: Path | None = None,
) -> dict[str, Any]:
    """Run ``lbt-rune-viewer`` in headless ``--snap`` mode to render a PNG."""
    exe = binary_path or discover_rune_viewer_binary()
    if exe is None:
        return {"status": "unavailable", "reason": "lbt-rune-viewer binary not found"}

    root = Path(garden_root).expanduser().resolve()
    out_path = Path(output_png_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if hbjson_path is not None:
        cmd = [str(exe), "--hbjson", str(Path(hbjson_path).expanduser().resolve()), "--snap", str(out_path)]
        if color_by:
            cmd.extend(["--color-by", str(color_by).strip().lower()])
    else:
        cmd = [str(exe), "--garden", str(root), "--snap", str(out_path)]

    view_arg = _snap_view_arg(view)
    if view_arg:
        cmd.extend(["--view", view_arg])
    cmd.extend(["--width", str(int(width)), "--height", str(int(height))])

    try:
        res = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=max(1.0, float(timeout_secs)),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "failed", "reason": str(exc), "binary_path": str(exe)}

    if res.returncode == 0 and out_path.is_file() and out_path.stat().st_size > 0:
        return {
            "status": "ok",
            "png_path": str(out_path),
            "binary_path": str(exe),
            "width": width,
            "height": height,
        }
    return {
        "status": "failed",
        "returncode": res.returncode,
        "stderr": (res.stderr or "")[:500],
        "stdout": (res.stdout or "")[:500],
        "binary_path": str(exe),
    }
