"""Host-side worker process helpers for Flowerpot platform adapters."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from flowerpot.installation import read_installation


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
        cwd=str(_src_root()),
        input=json.dumps(request, ensure_ascii=True),
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
    return Path(__file__).resolve().parent.parent


def _worker_python_executable() -> Path:
    """Return the external Python executable used for bridge worker calls."""
    candidates = _worker_python_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates) or "<none>"
    raise RuntimeError(
        "Flowerpot worker Python was not found. "
        "Run the Ladybug Tools MCP installer with the Grasshopper option. "
        f"Searched: {searched}"
    )


def _worker_python_candidates() -> list[Path]:
    root = _repository_root()
    candidates = [
        Path(value) for value in (
            os.environ.get("LADYBUG_TOOLS_MCP_PYTHON"),
            read_installation().get("python"),
        ) if value
    ]
    candidates.extend((root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"))
    if root.parent.name == ".worktrees":
        candidates.append(root.parent.parent / ".venv" / "Scripts" / "python.exe")
    src_root = os.environ.get("LADYBUG_TOOLS_MCP_SRC")
    if src_root:
        candidates.append(Path(src_root).expanduser().resolve().parent / ".venv" / "Scripts" / "python.exe")
    executable = Path(sys.executable)
    if executable.name.lower().startswith("python"):
        candidates.append(executable)

    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser().absolute()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def _worker_environment() -> dict[str, str]:
    """Return environment variables for worker subprocess execution."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    settings = read_installation()
    if settings:
        env["LADYBUG_TOOLS_GARDENS_ROOT"] = settings["gardens_root"]
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
