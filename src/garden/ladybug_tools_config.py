"""Ladybug Tools SDK runtime configuration services."""

from __future__ import annotations

import glob
import os
from pathlib import Path
import re
from typing import Any

from dragonfly_energy.config import folders as dragonfly_energy_folders
from garden.fairyfly.availability import therm_engine_config
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


def _path_record(value: str | Path | None) -> dict[str, Any]:
    path = str(value) if value else None
    return _existing_path(path)


def _existing_dirs(values: list[Path]) -> list[str]:
    return [str(value) for value in values if value.is_dir()]


def _first_existing_glob(pattern: str) -> Path | None:
    matches = [Path(path) for path in glob.glob(pattern) if Path(path).exists()]
    return matches[0] if matches else None


def _version_from_urbanopt_cli_folder(path: str | None) -> str | None:
    if not path:
        return None
    match = re.search(r"URBANopt-cli-(\d+(?:\.\d+)+)", str(path), re.IGNORECASE)
    return match.group(1) if match else None


def _urbanopt_setup_candidates(cli_path: str | None) -> list[dict[str, Any]]:
    if not cli_path:
        return []
    base = Path(cli_path)
    return [
        _path_record(base / "setup-env.bat"),
        _path_record(base / "setup-env.ps1"),
        _path_record(base / "setup-env.sh"),
    ]


def _urbanopt_path_updates(cli_path: str | None) -> dict[str, Any]:
    if not cli_path:
        return {"prepend": [], "env": {}}
    base = Path(cli_path)
    ruby_bin = base / "ruby" / "bin"
    gem_bin = _first_existing_glob(str(base / "gems" / "ruby" / "*" / "bin"))
    prepend = _existing_dirs([ruby_bin, *([gem_bin] if gem_bin else [])])
    gem_home = gem_bin.parent if gem_bin else None
    openstudio_ruby = base / "OpenStudio" / "Ruby"
    env = {
        "PATH": os.pathsep.join(prepend),
    }
    if gem_home and gem_home.is_dir():
        env["GEM_HOME"] = str(gem_home)
        env["GEM_PATH"] = str(gem_home)
    runtime_gemfile = base / "openstudio-runtime-gems" / "Gemfile"
    if runtime_gemfile.is_file():
        env["UO_GEMFILE_PATH"] = str(runtime_gemfile)
    runtime_gems = base / "openstudio-runtime-gems"
    if runtime_gems.is_dir():
        env["UO_BUNDLE_INSTALL_PATH"] = str(runtime_gems)
    if openstudio_ruby.is_dir():
        env["RUBYLIB"] = str(openstudio_ruby)
        env["RUBY_DLL_PATH"] = str(openstudio_ruby)
    return {"prepend": prepend, "env": env}


def _urbanopt_config() -> dict[str, Any]:
    folders = dragonfly_energy_folders
    cli_path = folders.urbanopt_cli_path
    gemfile_path = folders.urbanopt_gemfile_path
    env_path = folders.urbanopt_env_path
    required_version = ".".join(str(item) for item in folders.URBANOPT_VERSION)
    cached_version = getattr(folders, "_urbanopt_version_str", None)
    detected_version = cached_version or _version_from_urbanopt_cli_folder(cli_path)
    cli = _path_record(cli_path)
    gemfile = _path_record(gemfile_path)
    path_updates = _urbanopt_path_updates(cli_path)
    return {
        "name": "urbanopt",
        "kind": "urbanopt_runtime",
        "available": bool(
            cli_path
            and Path(cli_path).expanduser().is_dir()
            and gemfile_path
            and Path(gemfile_path).expanduser().is_file()
        ),
        "path": cli["path"],
        "path_exists": cli["exists"],
        "required_version": required_version,
        "detected_version": detected_version,
        "version": detected_version,
        "version_source": "sdk_cache_or_cli_folder_name",
        "cli": cli,
        "gemfile": gemfile,
        "setup_env": {
            "configured": _path_record(env_path),
            "candidates": _urbanopt_setup_candidates(cli_path),
        },
        "path_updates": path_updates,
        "note": (
            "URBANopt is a Dragonfly Energy runtime workflow for district-scale "
            "EnergyPlus/OpenStudio runs from URBANopt-compatible geoJSON. This "
            "config report is read-only and does not run setup-env."
        ),
    }


def _path_prepend_values(engines: dict[str, dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for engine in engines.values():
        path_updates = engine.get("path_updates")
        if isinstance(path_updates, dict) and isinstance(path_updates.get("prepend"), list):
            for value in path_updates["prepend"]:
                if (
                    isinstance(value, str)
                    and value
                    and Path(value).expanduser().is_dir()
                    and value not in values
                ):
                    values.append(value)
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
        "urbanopt": _urbanopt_config(),
        "therm": therm_engine_config(),
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
