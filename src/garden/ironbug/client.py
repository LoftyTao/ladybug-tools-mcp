"""Persistent JSON-Lines RPC client for the .NET 8 IronbugBridge sidecar."""

from __future__ import annotations

import atexit
from collections import deque
import json
import os
import queue
import subprocess
from threading import Lock, RLock, Thread, current_thread
import time
from typing import Any
from uuid import uuid4

from garden.ironbug.runtime import IronbugRuntimePaths, resolve_runtime_paths

DEFAULT_CALL_TIMEOUT = 30.0
VALIDATE_CALL_TIMEOUT = 60.0
_STDERR_RING_MAXLEN = 200
_STDERR_TAIL_LINES = 20


class IronbugBridgeError(RuntimeError):
    """Raised when the .NET IronbugBridge returns an error response."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def _drain_stderr(stream: Any, ring: deque[str], lock: Lock) -> None:
    """Continuously drain worker stderr into a bounded ring buffer to prevent pipe deadlocks."""
    try:
        for raw_line in iter(stream.readline, ""):
            line = raw_line.rstrip("\r\n")
            with lock:
                ring.append(line)
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _read_stdout(stream: Any, out_queue: queue.Queue[str | None]) -> None:
    """Read JSON-Lines responses from worker stdout into a queue, signaling EOF with None."""
    try:
        for line in iter(stream.readline, ""):
            out_queue.put(line)
    except (OSError, ValueError):
        pass
    finally:
        out_queue.put(None)
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _format_stderr_tail(
    ring: deque[str] | None,
    lock: Lock | None,
    max_lines: int = _STDERR_TAIL_LINES,
) -> str:
    """Return the last `max_lines` lines from the stderr ring buffer."""
    if ring is None or lock is None:
        return ""
    with lock:
        tail = list(ring)[-max_lines:]
    return "\n".join(tail).strip()


class IronbugBridgeClient:
    """Thread-safe persistent worker client talking to IronbugBridge.dll."""

    def __init__(self, paths: IronbugRuntimePaths) -> None:
        self._paths = paths
        self._lock = RLock()
        self._proc: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str | None] | None = None
        self._stderr_ring: deque[str] | None = None
        self._stderr_lock: Lock | None = None
        self._stderr_thread: Thread | None = None
        self._stdout_thread: Thread | None = None

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        prepend: list[str] = []
        if self._paths.openstudio_csharp_dir:
            prepend.append(str(self._paths.openstudio_csharp_dir))
            os_bin = self._paths.openstudio_csharp_dir.parent.parent / "bin"
            if os_bin.is_dir():
                prepend.append(str(os_bin))
        prepend.append(str(self._paths.ironbug_dir))
        existing_path = env.get("PATH", "")
        env["PATH"] = os.pathsep.join([*prepend, existing_path]) if existing_path else os.pathsep.join(prepend)
        if os.name != "nt":
            for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
                prev = env.get(var, "")
                env[var] = os.pathsep.join([*prepend, prev]) if prev else os.pathsep.join(prepend)
        return env

    def _ensure_started(
        self,
    ) -> tuple[
        subprocess.Popen[str],
        queue.Queue[str | None],
        deque[str],
        Lock,
    ]:
        if (
            self._proc is not None
            and self._proc.poll() is None
            and self._stdout_queue is not None
            and self._stderr_ring is not None
            and self._stderr_lock is not None
        ):
            return self._proc, self._stdout_queue, self._stderr_ring, self._stderr_lock

        if self._proc is not None:
            self.close(force=True)

        if self._paths.is_self_contained and self._paths.bridge_exe is not None:
            cmd = [
                str(self._paths.bridge_exe),
                "--ironbug-dir",
                str(self._paths.ironbug_dir),
                "--serve",
            ]
        else:
            if not self._paths.dotnet_exe:
                raise RuntimeError("dotnet executable is required when IronbugBridge is not self-contained.")
            cmd = [
                self._paths.dotnet_exe,
                "--roll-forward",
                "Major",
                str(self._paths.bridge_dll),
                "--ironbug-dir",
                str(self._paths.ironbug_dir),
                "--serve",
            ]
        if self._paths.openstudio_csharp_dir:
            cmd.extend(["--openstudio-csharp-dir", str(self._paths.openstudio_csharp_dir)])

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._build_env(),
        )
        assert proc.stdout is not None and proc.stderr is not None

        stderr_ring: deque[str] = deque(maxlen=_STDERR_RING_MAXLEN)
        stderr_lock = Lock()
        stdout_queue: queue.Queue[str | None] = queue.Queue()

        stderr_thread = Thread(
            target=_drain_stderr,
            args=(proc.stderr, stderr_ring, stderr_lock),
            name="ironbug-bridge-stderr",
            daemon=True,
        )
        stdout_thread = Thread(
            target=_read_stdout,
            args=(proc.stdout, stdout_queue),
            name="ironbug-bridge-stdout",
            daemon=True,
        )
        stderr_thread.start()
        stdout_thread.start()

        self._proc = proc
        self._stdout_queue = stdout_queue
        self._stderr_ring = stderr_ring
        self._stderr_lock = stderr_lock
        self._stderr_thread = stderr_thread
        self._stdout_thread = stdout_thread
        return proc, stdout_queue, stderr_ring, stderr_lock

    def close(self, *, force: bool = False) -> None:
        with self._lock:
            proc = self._proc
            stderr_thread = self._stderr_thread
            stdout_thread = self._stdout_thread
            self._proc = None
            self._stdout_queue = None
            self._stderr_ring = None
            self._stderr_lock = None
            self._stderr_thread = None
            self._stdout_thread = None

            if proc is None:
                return
            try:
                if proc.stdin:
                    proc.stdin.close()
            except OSError:
                pass

            if force:
                try:
                    proc.kill()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            else:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except OSError:
                        pass
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass

            me = current_thread()
            for t in (stderr_thread, stdout_thread):
                if t is not None and t is not me and t.is_alive():
                    t.join(timeout=0.3)

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        effective_timeout = (
            float(timeout)
            if timeout is not None
            else (VALIDATE_CALL_TIMEOUT if method == "validate" else DEFAULT_CALL_TIMEOUT)
        )
        if effective_timeout <= 0:
            raise ValueError(f"timeout must be > 0, got {effective_timeout}")

        with self._lock:
            proc, out_queue, stderr_ring, stderr_lock = self._ensure_started()
            assert proc.stdin is not None
            req_id = uuid4().hex[:12]
            payload = json.dumps(
                {"id": req_id, "method": method, "params": params or {}},
                ensure_ascii=False,
            )
            try:
                proc.stdin.write(payload + "\n")
                proc.stdin.flush()
            except OSError:
                # Restart once if the worker died unexpectedly before receiving the request.
                self.close(force=True)
                proc, out_queue, stderr_ring, stderr_lock = self._ensure_started()
                assert proc.stdin is not None
                proc.stdin.write(payload + "\n")
                proc.stdin.flush()

            deadline = time.monotonic() + effective_timeout
            line: str | None = None
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.close(force=True)
                    stderr_tail = _format_stderr_tail(stderr_ring, stderr_lock)
                    detail = f" Recent stderr:\n{stderr_tail}" if stderr_tail else ""
                    raise IronbugBridgeError(
                        "TimeoutError",
                        f"IronbugBridge call '{method}' timed out after {effective_timeout:.1f}s.{detail}",
                    )
                try:
                    item = out_queue.get(timeout=remaining)
                except queue.Empty:
                    self.close(force=True)
                    stderr_tail = _format_stderr_tail(stderr_ring, stderr_lock)
                    detail = f" Recent stderr:\n{stderr_tail}" if stderr_tail else ""
                    raise IronbugBridgeError(
                        "TimeoutError",
                        f"IronbugBridge call '{method}' timed out after {effective_timeout:.1f}s.{detail}",
                    ) from None

                if item is None:
                    # Wait briefly so the stderr drainer catches any final crash output before closing.
                    stderr_thread = self._stderr_thread
                    if stderr_thread is not None and stderr_thread.is_alive():
                        stderr_thread.join(timeout=0.2)
                    stderr_tail = _format_stderr_tail(stderr_ring, stderr_lock)
                    self.close()
                    detail = f" Recent stderr:\n{stderr_tail}" if stderr_tail else ""
                    raise RuntimeError(
                        f"IronbugBridge process terminated unexpectedly during '{method}'.{detail}"
                    )

                if item.strip():
                    line = item
                    break

            response = json.loads(line)
            if not response.get("ok"):
                err = response.get("error") or {}
                if response.get("id") == "init":
                    self.close()
                raise IronbugBridgeError(
                    str(err.get("type") or "BridgeError"),
                    str(err.get("message") or "IronbugBridge operation failed."),
                )
            result = response.get("result")
            return dict(result) if isinstance(result, dict) else {"value": result}


_CLIENT_LOCK = RLock()
_CLIENT_KEY: IronbugRuntimePaths | None = None
_CLIENT_INSTANCE: IronbugBridgeClient | None = None


def get_bridge_client(*, require_openstudio: bool = True) -> IronbugBridgeClient:
    """Return a shared persistent IronbugBridgeClient for the active external runtime."""
    global _CLIENT_KEY, _CLIENT_INSTANCE
    paths = resolve_runtime_paths(require_openstudio=require_openstudio)
    with _CLIENT_LOCK:
        if _CLIENT_INSTANCE is not None and _CLIENT_KEY is not None:
            if _CLIENT_KEY == paths:
                return _CLIENT_INSTANCE
            if (
                not require_openstudio
                and _CLIENT_KEY.openstudio_csharp_dir is not None
                and (
                    _CLIENT_KEY.ironbug_dir,
                    _CLIENT_KEY.dotnet_exe,
                    _CLIENT_KEY.bridge_dll,
                    _CLIENT_KEY.bridge_exe,
                    _CLIENT_KEY.is_self_contained,
                )
                == (
                    paths.ironbug_dir,
                    paths.dotnet_exe,
                    paths.bridge_dll,
                    paths.bridge_exe,
                    paths.is_self_contained,
                )
            ):
                return _CLIENT_INSTANCE
        if _CLIENT_INSTANCE is not None:
            _CLIENT_INSTANCE.close()
        _CLIENT_KEY = paths
        _CLIENT_INSTANCE = IronbugBridgeClient(paths)
        return _CLIENT_INSTANCE


def _shutdown_bridge_client() -> None:
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is not None:
        _CLIENT_INSTANCE.close()
        _CLIENT_INSTANCE = None


atexit.register(_shutdown_bridge_client)
