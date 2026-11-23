"""Simulation subprocess runner that backports OpenStudio OSM files when needed.

When Python ``openstudio`` (bundled with ``honeybee-openstudio``) is newer than
the locally installed OpenStudio CLI / C# bindings (used by external
``Ironbug.Console.exe`` and ``openstudio.exe``), temporary OSM files are
automatically backported in-place via ``openstudiobackporter`` immediately
before invoking external executables.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


def _parse_version_tuple(version_str: str) -> tuple[int, int, int] | None:
    """Parse a semantic version string such as '3.11.0+abc' into a 3-tuple."""
    core = str(version_str or "").strip().split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return (major, minor, patch)


def _resolve_backport_target() -> str | None:
    """Return target X.Y.0 OpenStudio version string if desktop OS is older than Python SDK."""
    import openstudio
    from honeybee_energy.config import folders as hbe_folders
    from openstudiobackporter.backporter import KNOWN_TO_VERSIONS

    py_ver = _parse_version_tuple(openstudio.openStudioVersion())
    cli_ver = getattr(hbe_folders, "openstudio_version", None)
    if py_ver is None or not cli_ver or len(cli_ver) < 2:
        return None

    cli_tuple = (int(cli_ver[0]), int(cli_ver[1]), int(cli_ver[2]) if len(cli_ver) > 2 else 0)
    if py_ver <= cli_tuple:
        return None

    candidate = f"{cli_tuple[0]}.{cli_tuple[1]}.0"
    return candidate if candidate in KNOWN_TO_VERSIONS else None


def _backport_osm_inplace(osm_path: Path, target_version: str) -> bool:
    """Backport *osm_path* in place if its file version exceeds *target_version*."""
    if not osm_path.is_file():
        return False

    import openstudio
    from openstudiobackporter.backporter import Backporter

    ver = openstudio.IdfFile.loadVersionOnly(osm_path)
    if not ver.is_initialized():
        return False
    if ver.get() <= openstudio.VersionString(target_version):
        return False

    backporter = Backporter(to_version=target_version, save_intermediate=False)
    with redirect_stdout(sys.stderr):
        idf_file = backporter.backport_file(osm_path)
    idf_file.save(osm_path, True)
    return True


def backport_osm_if_needed(osm_path: Path | str) -> dict[str, Any]:
    """Backport *osm_path* in place when Python OpenStudio exceeds CLI version."""
    path = Path(osm_path)
    if not path.is_file() or path.suffix.lower() != ".osm":
        return {"backported": False, "target_version": None, "warning": None}

    try:
        target = _resolve_backport_target()
    except Exception as exc:
        return {
            "backported": False,
            "target_version": None,
            "warning": f"Skipped OSM backport target resolution: {exc}",
        }

    if target is None:
        return {"backported": False, "target_version": None, "warning": None}

    try:
        changed = _backport_osm_inplace(path, target)
    except Exception as exc:
        return {
            "backported": False,
            "target_version": target,
            "warning": f"Failed to backport OSM {path.name} to OpenStudio {target}: {exc}",
        }

    return {"backported": changed, "target_version": target, "warning": None}


def _extract_tokens(args: Any) -> list[str]:
    if isinstance(args, (list, tuple)):
        return [str(part) for part in args]
    if isinstance(args, str):
        try:
            return shlex.split(args, posix=False)
        except ValueError:
            return args.split()
    return []


def _is_ironbug_osm_invocation(tokens: list[str], ironbug_exe: str | None) -> bool:
    if len(tokens) < 2:
        return False
    exe_token = tokens[0].strip().strip('"').strip("'")
    osm_token = tokens[1].strip().strip('"').strip("'")
    if not osm_token.lower().endswith(".osm"):
        return False
    if "ironbug" in Path(exe_token).name.lower():
        return True
    if ironbug_exe:
        try:
            return Path(exe_token).resolve() == Path(ironbug_exe).resolve()
        except OSError:
            return exe_token.lower() == str(ironbug_exe).lower()
    return False


class _WriterSubprocessProxy:
    """Proxy for ``honeybee_openstudio.writer.subprocess`` that backports OSM inputs."""

    def __init__(self, target_version: str, ironbug_exe: str | None) -> None:
        self._target_version = target_version
        self._ironbug_exe = ironbug_exe

    def _maybe_backport_args(self, args: Any) -> None:
        tokens = _extract_tokens(args)
        if _is_ironbug_osm_invocation(tokens, self._ironbug_exe):
            osm_arg = tokens[1].strip().strip('"').strip("'")
            _backport_osm_inplace(Path(osm_arg), self._target_version)

    def Popen(self, args: Any, *pargs: Any, **kwargs: Any) -> subprocess.Popen[Any]:
        self._maybe_backport_args(args)
        return subprocess.Popen(args, *pargs, **kwargs)

    def run(
        self, args: Any, *pargs: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[Any]:
        self._maybe_backport_args(args)
        return subprocess.run(args, *pargs, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(subprocess, name)


def _install_backport_hooks(target_version: str) -> None:
    """Patch Ironbug and OpenStudio CLI callers in this simulation subprocess."""
    from honeybee_energy import run as hb_run
    from honeybee_energy.cli import simulate as hb_simulate
    from honeybee_energy.config import folders as hbe_folders
    from honeybee_openstudio import writer as hb_writer

    hb_writer.subprocess = _WriterSubprocessProxy(
        target_version=target_version,
        ironbug_exe=getattr(hbe_folders, "ironbug_exe", None),
    )

    orig_run_osw = hb_run.run_osw

    def wrapped_run_osw(osw_json: str, *pargs: Any, **kwargs: Any) -> Any:
        try:
            osw_path = Path(osw_json)
            if osw_path.is_file():
                osw_data = json.loads(osw_path.read_text(encoding="utf-8"))
                seed_file = osw_data.get("seed_file")
                if isinstance(seed_file, str) and seed_file.strip():
                    seed_path = Path(seed_file.strip())
                    if not seed_path.is_absolute():
                        seed_path = osw_path.parent / seed_path
                    if seed_path.suffix.lower() == ".osm":
                        _backport_osm_inplace(seed_path, target_version)
        except Exception:
            # Fall back to upstream run_osw error reporting if OSW inspection fails.
            pass
        return orig_run_osw(osw_json, *pargs, **kwargs)

    hb_run.run_osw = wrapped_run_osw
    hb_simulate.run_osw = wrapped_run_osw


def main(argv: list[str] | None = None) -> int:
    """Run ``honeybee_energy.cli.simulate.simulate_model_cli`` with OSM backporting."""
    from honeybee_energy.cli.simulate import simulate_model_cli

    target = _resolve_backport_target()
    if target is not None:
        _install_backport_hooks(target)

    cli_args = list(sys.argv[1:] if argv is None else argv)
    simulate_model_cli.main(args=cli_args, standalone_mode=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
