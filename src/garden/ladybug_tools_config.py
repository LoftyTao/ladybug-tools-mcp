"""Ladybug Tools SDK runtime configuration services."""

from __future__ import annotations

import glob
import os
from contextlib import contextmanager
from pathlib import Path
import re
from typing import Any

from dragonfly_energy.config import folders as dragonfly_energy_folders
from garden.fairyfly.availability import therm_engine_config
from honeybee_energy.config import folders as energy_folders
from honeybee_radiance.config import folders as radiance_folders
from ladybug_tools_mcp.contracts.report import make_report


REQUIRED_RUNTIME_VERSIONS: dict[str, str] = {
    "radiance": "5.4",
    "openstudio": "3.10.0",
    "energyplus": "25.1.0",
    "urbanopt": "1.2.0",
    "therm": "8.1.30.0",
    "ironbug_console": "1.22.0.0",
}

OPENSTUDIO_ENERGYPLUS_VERSIONS: dict[str, str] = {
    "3.10.0": "25.1.0",
}

RUNTIME_SEARCH_ROOTS: list[Path] = [
    Path("C:/Program Files/ladybug_tools"),
    Path("C:/Program Files"),
    Path("C:/"),
    Path("C:/Program Files (x86)/lbnl"),
    Path("/Applications"),
    Path("/usr/local"),
]


_ENGINE_HELP: dict[str, dict[str, str | list[str]]] = {
    "radiance": {
        "documentation_url": "https://www.radiance-online.org/download-install",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": (
            "Install the Radiance version listed in the Ladybug Tools runtime "
            "matrix, then make sure honeybee-radiance can read radiance_path, "
            "radbin_path, and radlib_path."
        ),
        "required_for": ["Radiance daylight simulation and Radiance postprocess"],
    },
    "openstudio": {
        "documentation_url": "https://github.com/NREL/OpenStudio/releases",
        "compatibility_url": "https://github.com/NREL/OpenStudio/wiki/OpenStudio-SDK-Version-Compatibility-Matrix",
        "install_hint": (
            "Install the OpenStudio SDK version listed in the Ladybug Tools "
            "runtime matrix. The standard Ladybug Tools/Pollination installer "
            "also places OpenStudio under the Ladybug Tools folder."
        ),
        "required_for": ["Honeybee Energy simulation", "Dragonfly Energy simulation"],
    },
    "energyplus": {
        "documentation_url": "https://energyplus.net/downloads",
        "compatibility_url": "https://github.com/NREL/OpenStudio/wiki/OpenStudio-SDK-Version-Compatibility-Matrix",
        "install_hint": (
            "EnergyPlus is normally bundled with the compatible OpenStudio SDK. "
            "If this path is missing, reinstall or point Honeybee Energy config "
            "to the OpenStudio package that includes EnergyPlus."
        ),
        "required_for": ["EnergyPlus simulation through OpenStudio"],
    },
    "urbanopt": {
        "documentation_url": "https://docs.urbanopt.net/installation/installation.html",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": (
            "Install the URBANopt CLI version listed in the Ladybug Tools runtime "
            "matrix and run its setup-env script in the shell before district "
            "workflow commands when needed."
        ),
        "required_for": ["Dragonfly district-scale URBANopt workflows"],
    },
    "therm": {
        "documentation_url": "https://windows.lbl.gov/therm-software-downloads",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": (
            "Install LBNL THERM on Windows, including the required redistributable "
            "libraries, then make sure fairyfly-therm can read the THERM executable."
        ),
        "required_for": ["Fairyfly THERM workflows"],
    },
    "ironbug_console": {
        "documentation_url": "https://github.com/MingboPeng/Ironbug",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": (
            "Install Ironbug into the Ladybug Tools grasshopper/ironbug folder, "
            "usually through the Pollination/Ladybug Tools installer or the "
            "Ironbug installer, then point Honeybee Energy config to "
            "Ironbug.Console.exe."
        ),
        "required_for": ["Ironbug DetailedHVAC translation to OpenStudio"],
    },
}


def _normalized_path(value: str | Path | None) -> str | None:
    if not value:
        return None
    return str(Path(value).expanduser())


def _version_tuple(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.\-]\d+)+|\d+)", str(value))
    if not match:
        return None
    return tuple(int(item) for item in re.split(r"[.\-]", match.group(1)) if item)


def _version_from_name(value: str) -> str | None:
    parsed = _version_tuple(value)
    return ".".join(str(item) for item in parsed) if parsed else None


def _version_status(version: str | None, required_version: str | None) -> str:
    if not required_version:
        return "not_required"
    current = _version_tuple(version)
    required = _version_tuple(required_version)
    if current is None:
        return "unknown"
    if required is None:
        return "unknown"
    compare_length = len(required)
    current_prefix = current[:compare_length]
    if current_prefix == required:
        return "compatible"
    return "older" if current_prefix < required else "newer"


def _version_requirement(name: str) -> dict[str, Any] | None:
    required = REQUIRED_RUNTIME_VERSIONS.get(name)
    if not required:
        return None
    return {
        "required_version": required,
        "compatibility_policy": "exact_version_for_current_dev_runtime_matrix",
        "compatibility_url": _ENGINE_HELP[name].get("compatibility_url"),
    }


def _apply_runtime_requirement(name: str, record: dict[str, Any]) -> dict[str, Any]:
    required = REQUIRED_RUNTIME_VERSIONS.get(name)
    version = record.get("version") or record.get("detected_version")
    record["version_requirement"] = _version_requirement(name)
    record["version_status"] = _version_status(version, required)
    if required:
        record["required_version"] = required
    return record


def _candidate(
    *,
    name: str,
    path: str | Path | None,
    exe: str | Path | None = None,
    version: str | None = None,
    source: str,
    bin_path: str | Path | None = None,
    lib_path: str | Path | None = None,
) -> dict[str, Any]:
    path_str = _normalized_path(path)
    exe_str = _normalized_path(exe)
    bin_str = _normalized_path(bin_path)
    lib_str = _normalized_path(lib_path)
    required = REQUIRED_RUNTIME_VERSIONS.get(name)
    record: dict[str, Any] = {
        "name": name,
        "source": source,
        "path": path_str,
        "path_exists": bool(path_str and Path(path_str).is_dir()),
        "version": version,
        "version_status": _version_status(version, required),
    }
    if exe is not None:
        record["exe"] = exe_str
        record["exe_exists"] = bool(exe_str and Path(exe_str).is_file())
    if bin_path is not None:
        record["bin_path"] = bin_str
        record["bin_path_exists"] = bool(bin_str and Path(bin_str).is_dir())
    if lib_path is not None:
        record["lib_path"] = lib_str
        record["lib_path_exists"] = bool(lib_str and Path(lib_str).is_dir())
    return record


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.get("path") or candidate.get("bin_path") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _select_candidate(
    candidates: list[dict[str, Any]],
    *,
    configured_path: str | None,
) -> tuple[dict[str, Any] | None, str]:
    for candidate in candidates:
        if candidate.get("version_status") == "compatible":
            return candidate, "compatible_candidate"
    for candidate in candidates:
        if configured_path and candidate.get("path") == configured_path:
            return candidate, "configured_candidate_incompatible"
    for candidate in candidates:
        if candidate.get("path_exists") or candidate.get("bin_path_exists"):
            return candidate, "first_existing_candidate_incompatible"
    return None, "no_candidate"


def _runtime_search_roots() -> list[Path]:
    return [Path(root) for root in RUNTIME_SEARCH_ROOTS if Path(root).exists()]


def _child_dirs(root: Path) -> list[Path]:
    try:
        return [item for item in root.iterdir() if item.is_dir()]
    except OSError:
        return []


def _openstudio_root_from_bin(path: str | None) -> Path | None:
    if not path:
        return None
    path_obj = Path(path)
    return path_obj.parent if path_obj.name.lower() == "bin" else path_obj


def _openstudio_candidates() -> list[dict[str, Any]]:
    exe_name = "openstudio.exe" if os.name == "nt" else "openstudio"
    configured_path = _normalized_path(getattr(energy_folders, "openstudio_path", None))
    configured_exe = _normalized_path(getattr(energy_folders, "openstudio_exe", None))
    configured_version = getattr(energy_folders, "openstudio_version_str", None)
    candidates = [
        _candidate(
            name="openstudio",
            path=configured_path,
            exe=configured_exe,
            version=configured_version,
            source="sdk_config",
        )
    ]
    for root in _runtime_search_roots():
        for folder in _child_dirs(root):
            if not folder.name.lower().startswith("openstudio"):
                continue
            bin_path = folder / "bin"
            exe = bin_path / exe_name
            if exe.is_file():
                candidates.append(
                    _candidate(
                        name="openstudio",
                        path=bin_path,
                        exe=exe,
                        version=_version_from_name(folder.name),
                        source="filesystem_scan",
                    )
                )
    return _dedupe_candidates(candidates)


def _select_openstudio_config() -> dict[str, Any]:
    configured_path = _normalized_path(getattr(energy_folders, "openstudio_path", None))
    candidates = _openstudio_candidates()
    selected, reason = _select_candidate(candidates, configured_path=configured_path)
    if selected is None:
        selected = _candidate(
            name="openstudio",
            path=None,
            exe=None,
            version=None,
            source="not_found",
        )
    record = dict(selected)
    record["configured_path"] = configured_path
    record["configured_exe"] = _normalized_path(getattr(energy_folders, "openstudio_exe", None))
    record["configured_version"] = getattr(energy_folders, "openstudio_version_str", None)
    record["selection_reason"] = reason
    record["version_requirement"] = _version_requirement("openstudio")
    record["candidates"] = candidates
    record.update(_ENGINE_HELP["openstudio"])
    return record


def _energyplus_version_for_openstudio(openstudio: dict[str, Any]) -> str | None:
    version = openstudio.get("version")
    if isinstance(version, str):
        version_key = ".".join(str(item) for item in (_version_tuple(version) or ())[:3])
        return OPENSTUDIO_ENERGYPLUS_VERSIONS.get(version_key)
    return None


def _energyplus_candidates(openstudio: dict[str, Any]) -> list[dict[str, Any]]:
    exe_name = "energyplus.exe" if os.name == "nt" else "energyplus"
    configured_path = _normalized_path(getattr(energy_folders, "energyplus_path", None))
    configured_exe = _normalized_path(getattr(energy_folders, "energyplus_exe", None))
    configured_version = getattr(energy_folders, "energyplus_version_str", None)
    candidates = [
        _candidate(
            name="energyplus",
            path=configured_path,
            exe=configured_exe,
            version=configured_version,
            source="sdk_config",
        )
    ]
    os_root = _openstudio_root_from_bin(openstudio.get("path"))
    if os_root:
        bundled = os_root / "EnergyPlus"
        exe = bundled / exe_name
        if exe.is_file():
            candidates.append(
                _candidate(
                    name="energyplus",
                    path=bundled,
                    exe=exe,
                    version=_energyplus_version_for_openstudio(openstudio),
                    source="selected_openstudio_bundle",
                )
            )
    for root in _runtime_search_roots():
        for folder in _child_dirs(root):
            if not folder.name.lower().startswith("energyplus"):
                continue
            exe = folder / exe_name
            if exe.is_file():
                candidates.append(
                    _candidate(
                        name="energyplus",
                        path=folder,
                        exe=exe,
                        version=_version_from_name(folder.name),
                        source="filesystem_scan",
                    )
                )
    return _dedupe_candidates(candidates)


def _select_energyplus_config(openstudio: dict[str, Any]) -> dict[str, Any]:
    configured_path = _normalized_path(getattr(energy_folders, "energyplus_path", None))
    candidates = _energyplus_candidates(openstudio)
    selected, reason = _select_candidate(candidates, configured_path=configured_path)
    if selected is None:
        selected = _candidate(
            name="energyplus",
            path=None,
            exe=None,
            version=None,
            source="not_found",
        )
    record = dict(selected)
    record["configured_path"] = configured_path
    record["configured_exe"] = _normalized_path(getattr(energy_folders, "energyplus_exe", None))
    record["configured_version"] = getattr(energy_folders, "energyplus_version_str", None)
    record["selection_reason"] = reason
    record["version_requirement"] = _version_requirement("energyplus")
    record["candidates"] = candidates
    record.update(_ENGINE_HELP["energyplus"])
    return record


def _runtime_guidance(name: str, engine: dict[str, Any]) -> dict[str, Any]:
    required = REQUIRED_RUNTIME_VERSIONS.get(name)
    hint = engine.get("install_hint") or _ENGINE_HELP[name].get("install_hint")
    if required and hint:
        hint = f"{hint} Required version for this DEV runtime is {required}."
    return {
        "required_version": required,
        "version_status": engine.get("version_status"),
        "selected_version": engine.get("version"),
        "selected_path": engine.get("path"),
        "documentation_url": engine.get("documentation_url"),
        "compatibility_url": engine.get("compatibility_url"),
        "install_hint": hint,
        "required_for": engine.get("required_for"),
    }


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
    _apply_runtime_requirement(name, record)
    record.update(_ENGINE_HELP.get(name, {}))
    return record


def _path_record(value: str | Path | None) -> dict[str, Any]:
    path = str(value) if value else None
    return _existing_path(path)


def _sourced_path_record(value: str | Path | None, source: str) -> dict[str, Any]:
    record = _path_record(value)
    record["source"] = source
    return record


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


def _urbanopt_candidates() -> list[dict[str, Any]]:
    cli_path = _normalized_path(getattr(dragonfly_energy_folders, "urbanopt_cli_path", None))
    detected_version = (
        getattr(dragonfly_energy_folders, "_urbanopt_version_str", None)
        or _version_from_urbanopt_cli_folder(cli_path)
    )
    candidates = [
        _candidate(
            name="urbanopt",
            path=cli_path,
            version=detected_version,
            source="sdk_config",
        )
    ]
    for root in _runtime_search_roots():
        for folder in _child_dirs(root):
            if not folder.name.lower().startswith("urbanopt-cli"):
                continue
            candidates.append(
                _candidate(
                    name="urbanopt",
                    path=folder,
                    version=_version_from_urbanopt_cli_folder(str(folder)),
                    source="filesystem_scan",
                )
            )
    return _dedupe_candidates(candidates)


def _urbanopt_setup_candidates(cli_path: str | None) -> list[dict[str, Any]]:
    if not cli_path:
        return []
    base = Path(cli_path)
    return [
        _path_record(base / "setup-env.bat"),
        _path_record(base / "setup-env.ps1"),
        _path_record(base / "setup-env.sh"),
    ]


def _urbanopt_cli_runtime_gemfile(cli_path: str | None) -> str | None:
    if not cli_path:
        return None
    return str(Path(cli_path) / "gems" / "Gemfile")


def _urbanopt_openstudio_runtime_gemfile(cli_path: str | None) -> str | None:
    if not cli_path:
        return None
    return str(Path(cli_path) / "openstudio-runtime-gems" / "Gemfile")


def _urbanopt_cli_gem_bundle(cli_path: str | None) -> Path | None:
    if not cli_path:
        return None
    return _first_existing_glob(str(Path(cli_path) / "gems" / "ruby" / "*"))


def _urbanopt_sdk_search() -> dict[str, Any]:
    return {
        "package": "dragonfly_energy",
        "config_class": "dragonfly_energy.config.Folders",
        "config_properties": [
            "urbanopt_cli_path",
            "urbanopt_gemfile_path",
            "urbanopt_env_path",
            "urbanopt_version",
            "urbanopt_version_str",
        ],
        "config_methods": [
            "retrieve_urbanopt_env_path",
            "generate_urbanopt_env_path",
            "check_urbanopt_version",
        ],
        "run_module": "dragonfly_energy.run",
        "run_functions": [
            "prepare_urbanopt_folder",
            "run_urbanopt",
            "run_default_report",
            "set_building_district_loads",
        ],
        "grasshopper_mindset": [
            "Dragonfly Model to geoJSON",
            "Run URBANopt",
            "Run Energy Simulation",
            "Read URBANopt Result",
        ],
    }


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
        env["UO_CLI_GEM_BUNDLE_PATH"] = str(gem_home)
    cli_runtime_gemfile = base / "gems" / "Gemfile"
    if cli_runtime_gemfile.is_file():
        env["BUNDLE_GEMFILE"] = str(cli_runtime_gemfile)
        env["UO_CLI_GEMFILE_PATH"] = str(cli_runtime_gemfile)
    openstudio_runtime_gemfile = base / "openstudio-runtime-gems" / "Gemfile"
    if openstudio_runtime_gemfile.is_file():
        env["UO_OPENSTUDIO_RUNTIME_GEMFILE_PATH"] = str(openstudio_runtime_gemfile)
    runtime_gems = base / "openstudio-runtime-gems"
    if runtime_gems.is_dir():
        env["UO_BUNDLE_INSTALL_PATH"] = str(runtime_gems)
    if openstudio_ruby.is_dir():
        env["RUBYLIB"] = str(openstudio_ruby)
        env["RUBY_DLL_PATH"] = str(openstudio_ruby)
    return {"prepend": prepend, "env": env}


def _urbanopt_config() -> dict[str, Any]:
    folders = dragonfly_energy_folders
    configured_path = _normalized_path(getattr(folders, "urbanopt_cli_path", None))
    candidates = _urbanopt_candidates()
    selected, reason = _select_candidate(candidates, configured_path=configured_path)
    cli_path = selected.get("path") if selected else configured_path
    sdk_gemfile_path = _normalized_path(getattr(folders, "urbanopt_gemfile_path", None))
    cli_runtime_gemfile_path = _urbanopt_cli_runtime_gemfile(cli_path)
    openstudio_runtime_gemfile_path = _urbanopt_openstudio_runtime_gemfile(cli_path)
    cli_gem_bundle = _urbanopt_cli_gem_bundle(cli_path)
    if sdk_gemfile_path and Path(sdk_gemfile_path).expanduser().is_file():
        gemfile_path = sdk_gemfile_path
        gemfile_source = "sdk_config"
    else:
        gemfile_path = cli_runtime_gemfile_path
        gemfile_source = "cli_bundle"
    env_path = getattr(folders, "urbanopt_env_path", None)
    detected_version = selected.get("version") if selected else None
    cli = _path_record(cli_path)
    gemfile = _sourced_path_record(gemfile_path, gemfile_source)
    cli_runtime_gemfile = _sourced_path_record(cli_runtime_gemfile_path, "cli_bundle")
    openstudio_runtime_gemfile = _sourced_path_record(
        openstudio_runtime_gemfile_path,
        "openstudio_runtime",
    )
    setup_candidates = _urbanopt_setup_candidates(cli_path)
    path_updates = _urbanopt_path_updates(cli_path)
    record = {
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
        "configured_path": configured_path,
        "selection_reason": reason,
        "detected_version": detected_version,
        "version": detected_version,
        "version_source": "sdk_config_or_cli_folder_name",
        "candidates": candidates,
        "cli": cli,
        "gemfile": gemfile,
        "cli_runtime_gemfile": cli_runtime_gemfile,
        "openstudio_runtime_gemfile": openstudio_runtime_gemfile,
        "cli_gem_bundle": _sourced_path_record(cli_gem_bundle, "cli_runtime"),
        "setup_env": {
            "configured": _path_record(env_path),
            "candidates": setup_candidates,
            "generatable": any(candidate.get("exists") for candidate in setup_candidates),
        },
        "sdk_search": _urbanopt_sdk_search(),
        "path_updates": path_updates,
        "note": (
            "URBANopt is a Dragonfly Energy runtime workflow for district-scale "
            "EnergyPlus/OpenStudio runs from URBANopt-compatible geoJSON. The "
            "Dragonfly Energy SDK uses urbanopt_gemfile_path for project "
            "preparation and can generate an env script from setup-env when "
            "needed. This config report is read-only and does not run setup-env."
        ),
    }
    _apply_runtime_requirement("urbanopt", record)
    record.update(_ENGINE_HELP["urbanopt"])
    return record


def _ironbug_console_config() -> dict[str, Any]:
    exe = getattr(energy_folders, "ironbug_exe", None)
    path = getattr(energy_folders, "ironbug_path", None)
    if not path and exe:
        path = str(Path(exe).expanduser().parent)
    return _engine_record(
        "ironbug_console",
        path=path,
        exe=exe,
        version_getter=lambda: getattr(energy_folders, "ironbug_version_str", None),
    )


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
    openstudio = _select_openstudio_config()
    energyplus = _select_energyplus_config(openstudio)
    engines = {
        "radiance": _engine_record(
            "radiance",
            path=radiance_folders.radiance_path,
            bin_path=radiance_folders.radbin_path,
            lib_path=radiance_folders.radlib_path,
            version_getter=lambda: radiance_folders.radiance_version_str,
        ),
        "openstudio": openstudio,
        "energyplus": energyplus,
        "urbanopt": _urbanopt_config(),
        "therm": therm_engine_config(),
        "ironbug_console": _ironbug_console_config(),
    }
    _apply_runtime_requirement("therm", engines["therm"])
    engines["therm"].update(_ENGINE_HELP["therm"])
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
    incompatible = [
        name
        for name, engine in engines.items()
        if engine.get("version_requirement")
        and engine.get("version_status") in {"older", "newer", "unknown"}
    ]
    guidance_names = sorted({*missing, *incompatible})
    status = "warning" if missing or incompatible else "ok"
    warnings: list[str] = []
    if missing:
        warnings.append(
            "Some configured Ladybug Tools engines or executable paths are missing: "
            + ", ".join(missing)
        )
    if incompatible:
        warnings.append(
            "Some configured Ladybug Tools engines do not match the current DEV "
            "runtime version requirements: "
            + ", ".join(incompatible)
        )
    return {
        "summary_view": {
            "engines": engines,
            "measures": measures,
            "path_updates": path_updates,
            "missing_engines": missing,
            "incompatible_engines": incompatible,
            "missing_engine_guidance": {
                name: _runtime_guidance(name, engines[name])
                for name in missing
            },
            "runtime_requirement_guidance": {
                name: _runtime_guidance(name, engines[name]) for name in guidance_names
            },
        },
        "report": make_report(
            status=status,
            message="Ladybug Tools SDK runtime configuration returned.",
            warnings=warnings,
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


def urbanopt_cli_gem_bundle_path(runtime: dict[str, Any] | None) -> Path | None:
    """Return the URBANopt CLI bundle path used by project-local Bundler config."""
    if not isinstance(runtime, dict):
        return None
    direct = runtime.get("cli_gem_bundle")
    if isinstance(direct, dict):
        path_value = direct.get("path")
        if isinstance(path_value, str) and path_value:
            return Path(path_value).expanduser()
    path_updates = runtime.get("path_updates")
    if isinstance(path_updates, dict):
        env = path_updates.get("env")
        if isinstance(env, dict):
            for key in ("UO_CLI_GEM_BUNDLE_PATH", "GEM_HOME"):
                value = env.get(key)
                if isinstance(value, str) and value:
                    return Path(value).expanduser()
    return None


def urbanopt_cli_runtime_gemfile_path(runtime: dict[str, Any] | None) -> Path | None:
    """Return the URBANopt CLI Gemfile used for ``bundle exec uo`` commands."""
    if not isinstance(runtime, dict):
        return None
    direct = runtime.get("cli_runtime_gemfile")
    if isinstance(direct, dict):
        path_value = direct.get("path")
        if isinstance(path_value, str) and path_value:
            return Path(path_value).expanduser()
    path_updates = runtime.get("path_updates")
    if isinstance(path_updates, dict):
        env = path_updates.get("env")
        if isinstance(env, dict):
            for key in ("BUNDLE_GEMFILE", "UO_CLI_GEMFILE_PATH"):
                value = env.get(key)
                if isinstance(value, str) and value:
                    return Path(value).expanduser()
    cli_path = runtime.get("path")
    if isinstance(cli_path, str) and cli_path:
        candidate = Path(cli_path).expanduser() / "gems" / "Gemfile"
        if candidate.is_file():
            return candidate
    return None


def write_urbanopt_bundle_config(project_dir: str | Path, runtime: dict[str, Any] | None) -> Path | None:
    """Write project-local Bundler config for the URBANopt CLI gem bundle."""
    bundle_path = urbanopt_cli_gem_bundle_path(runtime)
    if bundle_path is None:
        return None
    config_dir = Path(project_dir).expanduser().resolve() / ".bundle"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config"
    bundle_value = str(bundle_path).replace("\\", "/")
    config_path.write_text(f'---\nBUNDLE_PATH: "{bundle_value}"\n', encoding="utf-8")
    return config_path


@contextmanager
def urbanopt_runtime_env(runtime: dict[str, Any] | None):
    """Temporarily expose URBANopt CLI env discovered by config_get_runtime_config."""
    if not isinstance(runtime, dict):
        yield
        return
    path_updates = runtime.get("path_updates")
    if not isinstance(path_updates, dict):
        yield
        return
    env_updates = path_updates.get("env")
    prepend = path_updates.get("prepend")
    env_updates = env_updates if isinstance(env_updates, dict) else {}
    prepend = prepend if isinstance(prepend, list) else []
    original: dict[str, str | None] = {}
    try:
        for key, value in env_updates.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            original.setdefault(key, os.environ.get(key))
            if key.upper() == "PATH":
                parts = [part for part in value.split(os.pathsep) if part]
                current = os.environ.get("PATH", "")
                os.environ["PATH"] = os.pathsep.join([*parts, current]) if current else value
            else:
                os.environ[key] = value
        path_parts = [str(part) for part in prepend if isinstance(part, str) and part]
        if path_parts:
            original.setdefault("PATH", os.environ.get("PATH"))
            current = os.environ.get("PATH", "")
            os.environ["PATH"] = (
                os.pathsep.join([*path_parts, current])
                if current
                else os.pathsep.join(path_parts)
            )
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


URBANOPT_SDK_OUTPUT_TYPES = ("osm", "idf", "sql", "zsz", "rdd", "html", "err")


def iter_urbanopt_sdk_output_paths(value: Any):
    """Yield (output_type, path) pairs from Dragonfly Energy URBANopt SDK results."""
    if isinstance(value, dict):
        for output_type, paths in value.items():
            if isinstance(paths, (list, tuple)):
                for path in paths:
                    if path:
                        yield str(output_type), path
            elif paths:
                yield str(output_type), paths
        return
    if isinstance(value, (list, tuple)):
        looks_like_sdk_tuple = len(value) == len(URBANOPT_SDK_OUTPUT_TYPES) and any(
            isinstance(item, (list, tuple)) for item in value
        )
        if looks_like_sdk_tuple:
            for output_type, paths in zip(URBANOPT_SDK_OUTPUT_TYPES, value):
                if isinstance(paths, (list, tuple)):
                    for path in paths:
                        if path:
                            yield output_type, path
                elif paths:
                    yield output_type, paths
            return
        for path in value:
            if path:
                yield None, path
        return
    if value:
        yield None, value
