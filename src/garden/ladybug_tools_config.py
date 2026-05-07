"""Ladybug Tools SDK runtime configuration services."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from honeybee_energy.config import folders as energy_folders
from honeybee_radiance.config import folders as radiance_folders
from ladybug_tools_mcp.contracts.report import make_report


def _existing_path(value: str | None) -> dict[str, Any]:
    exists = bool(value and Path(value).expanduser().exists())
    return {"path": value, "exists": exists}


def _version_value(getter) -> str | None:
    try:
        return getter()
    except Exception:
        return None


def _engine_record(
    name: str,
    *,
    path: str | None,
    exe: str | None = None,
    version_getter=None,
    bin_path: str | None = None,
    lib_path: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": name,
        "path": path,
        "path_exists": bool(path and Path(path).expanduser().is_dir()),
    }
    if exe is not None:
        record["exe"] = exe
        record["exe_exists"] = bool(exe and Path(exe).expanduser().is_file())
    if bin_path is not None:
        record["bin_path"] = bin_path
        record["bin_path_exists"] = bool(bin_path and Path(bin_path).expanduser().is_dir())
    if lib_path is not None:
        record["lib_path"] = lib_path
        record["lib_path_exists"] = bool(lib_path and Path(lib_path).expanduser().is_dir())
    if version_getter is not None:
        version = _version_value(version_getter)
        if version:
            record["version"] = version
    return record


def _path_prepend_values(engines: dict[str, dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for engine in engines.values():
        for key in ("bin_path", "path"):
            value = engine.get(key)
            if (
                isinstance(value, str)
                and value
                and Path(value).expanduser().is_dir()
                and value not in values
            ):
                values.append(value)
                break
    return values


def get_ladybug_tools_config() -> dict[str, Any]:
    """Return compact SDK runtime configuration for Ladybug Tools engines."""
    engines = {
        "radiance": _engine_record(
            "radiance",
            path=radiance_folders.radiance_path,
            bin_path=radiance_folders.radbin_path,
            lib_path=radiance_folders.radlib_path,
            version_getter=lambda: radiance_folders.radiance_version_str,
        ),
        "openstudio": _engine_record(
            "openstudio",
            path=energy_folders.openstudio_path,
            exe=energy_folders.openstudio_exe,
            version_getter=lambda: energy_folders.openstudio_version_str,
        ),
        "energyplus": _engine_record(
            "energyplus",
            path=energy_folders.energyplus_path,
            exe=energy_folders.energyplus_exe,
            version_getter=lambda: energy_folders.energyplus_version_str,
        ),
    }
    measures = {
        "lbt_measures_path": _existing_path(energy_folders.lbt_measures_path),
        "openstudio_results_measure_path": _existing_path(
            energy_folders.openstudio_results_measure_path
        ),
        "honeybee_openstudio_gem_path": _existing_path(
            energy_folders.honeybee_openstudio_gem_path
        ),
    }
    prepend = _path_prepend_values(engines)
    path_updates = {
        "prepend": prepend,
        "env": {
            "PATH": os.pathsep.join(prepend),
        },
    }
    missing = [
        name
        for name, engine in engines.items()
        if not engine.get("path_exists")
        or ("exe_exists" in engine and not engine.get("exe_exists"))
        or ("bin_path_exists" in engine and not engine.get("bin_path_exists"))
    ]
    status = "warning" if missing else "ok"
    return {
        "summary_view": {
            "engines": engines,
            "measures": measures,
            "path_updates": path_updates,
            "missing_engines": missing,
        },
        "report": make_report(
            status=status,
            message="Ladybug Tools SDK runtime configuration returned.",
            warnings=[
                "Some configured Ladybug Tools engines or executable paths are missing: "
                + ", ".join(missing)
            ]
            if missing
            else [],
        ),
    }


def apply_ladybug_tools_runtime_to_path() -> list[str]:
    """Prepend SDK-discovered engine paths to the current process PATH."""
    config = get_ladybug_tools_config()
    prepend = list(config["summary_view"]["path_updates"]["prepend"])
    if not prepend:
        return []
    current_parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    normalized_current = {str(Path(part)).lower() for part in current_parts}
    new_parts = [
        part for part in prepend if str(Path(part)).lower() not in normalized_current
    ]
    if new_parts:
        os.environ["PATH"] = os.pathsep.join([*new_parts, *current_parts])
    return prepend
