"""Small helpers for Garden background work."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from typing import Any, Callable


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
    log_path = run_dir / "background_stdio.log"
    with log_path.open("ab") as log_file:
        return subprocess.Popen(
            [sys.executable, "-m", worker_module, str(request_path)],
            cwd=str(cwd),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
