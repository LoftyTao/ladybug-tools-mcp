"""Host-side worker process helpers for Flowerpot platform adapters."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any


def run_worker(action: str, request: dict[str, Any]) -> dict[str, Any]:
    """Run the external bridge worker and return its JSON response."""
    command = [
        str(_worker_python_executable()),
        "-m",
        "flowerpot.worker_cli",
        action,
    ]
    completed = subprocess.run(
        command,
        cwd=str(_repository_root()),
        input=json.dumps(request, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=_worker_environment(),
        **_worker_subprocess_flags(),
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or (
            f"Worker exited with code {completed.returncode}."
        )
        raise RuntimeError(message)
    if not completed.stdout.strip():
        raise RuntimeError("Worker returned an empty response.")
    response = json.loads(completed.stdout)
    if "error" in response:
        raise RuntimeError(str(response["error"]))
    return response


def _repository_root() -> Path:
    """Return the repository root resolved from this module location."""
    return Path(__file__).resolve().parents[2]


def _src_root() -> Path:
    return _repository_root() / "src"


def _worker_python_executable() -> Path:
    """Return the external Python executable used for bridge worker calls."""
    candidate = _repository_root() / ".venv" / "Scripts" / "python.exe"
    if not candidate.is_file():
        raise RuntimeError(
            f"Flowerpot worker Python was not found at {candidate}. "
            "Create the project .venv before using Grasshopper components."
        )
    return candidate


def _worker_environment() -> dict[str, str]:
    """Return environment variables for worker subprocess execution."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    existing_pythonpath = env.get("PYTHONPATH")
    src_root = str(_src_root())
    env["PYTHONPATH"] = (
        src_root if not existing_pythonpath else src_root + os.pathsep + existing_pythonpath
    )
    for variable_name in ("PYTHONHOME", "IRONPYTHONPATH"):
        env.pop(variable_name, None)
    return env


def _worker_subprocess_flags() -> dict[str, Any]:
    """Return Windows subprocess flags that avoid flashing a console window."""
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        "startupinfo": startupinfo,
    }
