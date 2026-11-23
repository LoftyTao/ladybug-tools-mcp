"""Generic helpers and CLI runner for Garden background work."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from importlib import import_module
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
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
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )


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
