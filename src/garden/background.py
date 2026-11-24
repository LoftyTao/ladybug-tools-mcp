"""Generic helpers and CLI runner for Garden background work."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import errno
from importlib import import_module
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Thread
import time
from typing import Any, Callable, Iterator


@contextmanager
def capture_recipe_stdio(run_dir: Path, log_name: str = "recipe_stdio.log") -> Iterator[Path]:
    """Keep synchronous recipe logs out of stdio-based MCP JSON-RPC."""
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / log_name
    previous_streams: list[tuple[logging.StreamHandler, Any]] = []
    saved_fds: list[tuple[int, int]] = []
    with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            try:
                stream.flush()
            except Exception:
                pass
        for fd in (1, 2):
            try:
                saved_fd = os.dup(fd)
                os.dup2(log_file.fileno(), fd)
            except OSError:
                continue
            saved_fds.append((fd, saved_fd))
        for logger in [
            logging.getLogger(),
            *(
                item
                for item in logging.Logger.manager.loggerDict.values()
                if isinstance(item, logging.Logger)
            ),
        ]:
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream in {
                    sys.stdout,
                    sys.stderr,
                    sys.__stdout__,
                    sys.__stderr__,
                }:
                    previous_streams.append((handler, handler.stream))
                    handler.setStream(log_file)
        try:
            with redirect_stdout(log_file), redirect_stderr(log_file):
                yield log_path
        finally:
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except Exception:
                    pass
            log_file.flush()
            for fd, saved_fd in reversed(saved_fds):
                try:
                    os.dup2(saved_fd, fd)
                finally:
                    os.close(saved_fd)
            for handler, stream in previous_streams:
                handler.setStream(stream)


def submit_daemon(fn: Callable[..., Any], *, name: str, **kwargs: Any) -> Thread:
    """Submit work without keeping the stdio MCP process alive."""
    thread = Thread(target=fn, kwargs=kwargs, name=name, daemon=True)
    thread.start()
    return thread


def submit_worker_process(
    *,
    garden_root: Path,
    run_dir: Path,
    worker_module: str,
    request: dict[str, Any],
    cwd: Path,
    environment: dict[str, str],
) -> subprocess.Popen:
    """Serialize one request and run its worker outside the MCP process."""
    garden_root = garden_root.resolve()
    run_dir = run_dir.resolve()
    run_dir.relative_to(garden_root)
    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "background_request.json"
    request_path.write_text(
        json.dumps(request, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    command = (
        [sys.executable, "-m", "garden.background", worker_module, str(request_path)]
        if ":" in worker_module
        else [sys.executable, "-m", worker_module, str(request_path)]
    )
    log_path = run_dir / "background_stdio.log"
    with log_path.open("ab") as log_file:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
    (run_dir / "worker.pid").write_text(f"{proc.pid}\n", encoding="utf-8")
    return proc


def terminate_pid(pid: int) -> dict[str, Any]:
    """Terminate a background worker process (and process tree on Windows)."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer.")

    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=15,
                check=False,
            )
            output = f"{completed.stdout or ''}\n{completed.stderr or ''}".lower()
            if completed.returncode == 0:
                return {
                    "pid": pid,
                    "terminated": True,
                    "already_exited": False,
                    "method": "taskkill",
                    "message": f"Terminated process tree for PID {pid}.",
                }
            if (
                completed.returncode == 128
                or "not found" in output
                or "no running instance" in output
            ):
                return {
                    "pid": pid,
                    "terminated": False,
                    "already_exited": True,
                    "method": "taskkill",
                    "message": f"Process {pid} had already exited.",
                }
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass

        try:
            os.kill(pid, signal.SIGTERM)
            return {
                "pid": pid,
                "terminated": True,
                "already_exited": False,
                "method": "os.kill",
                "message": f"Terminated process {pid} via os.kill fallback.",
            }
        except ProcessLookupError:
            return {
                "pid": pid,
                "terminated": False,
                "already_exited": True,
                "method": "os.kill",
                "message": f"Process {pid} had already exited.",
            }
        except OSError as exc:
            if getattr(exc, "winerror", None) == 87 or exc.errno == errno.ESRCH:
                return {
                    "pid": pid,
                    "terminated": False,
                    "already_exited": True,
                    "method": "os.kill",
                    "message": f"Process {pid} had already exited.",
                }
            return {
                "pid": pid,
                "terminated": False,
                "already_exited": False,
                "method": "os.kill",
                "error": str(exc),
                "message": f"Failed to terminate process {pid}: {exc}",
            }

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {
            "pid": pid,
            "terminated": False,
            "already_exited": True,
            "method": "SIGTERM",
            "message": f"Process {pid} had already exited.",
        }
    except OSError as exc:
        return {
            "pid": pid,
            "terminated": False,
            "already_exited": False,
            "method": "SIGTERM",
            "error": str(exc),
            "message": f"Failed to terminate process {pid}: {exc}",
        }

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        time.sleep(0.1)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return {
                "pid": pid,
                "terminated": True,
                "already_exited": False,
                "method": "SIGTERM",
                "message": f"Terminated process {pid} with SIGTERM.",
            }
        except OSError:
            break

    sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
    try:
        os.kill(pid, sigkill)
    except ProcessLookupError:
        return {
            "pid": pid,
            "terminated": True,
            "already_exited": False,
            "method": "SIGTERM",
            "message": f"Terminated process {pid} with SIGTERM.",
        }
    except OSError as exc:
        return {
            "pid": pid,
            "terminated": False,
            "already_exited": False,
            "method": "SIGKILL",
            "error": str(exc),
            "message": f"Failed to terminate process {pid}: {exc}",
        }
    return {
        "pid": pid,
        "terminated": True,
        "already_exited": False,
        "method": "SIGKILL",
        "message": f"Terminated process {pid} with SIGKILL.",
    }


def read_tail_lines(path: Path, tail_lines: int = 100) -> str:
    """Read the last ``tail_lines`` lines from a text log file safely."""
    path = Path(path)
    if tail_lines <= 0 or not path.is_file():
        return ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        tail = deque(handle, maxlen=int(tail_lines))
    return "".join(tail)


def main(argv: list[str] | None = None) -> int:
    """Run one serialized worker request for ``<module:func> <request_json>``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or ":" not in args[0]:
        raise SystemExit(
            "Usage: python -m garden.background <module:func> <request_json>"
        )
    module_name, func_name = args[0].split(":", 1)
    request_path = Path(args[1]).expanduser().resolve()
    kwargs = json.loads(request_path.read_text(encoding="utf-8"))
    target = getattr(import_module(module_name), func_name)
    target(**kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
