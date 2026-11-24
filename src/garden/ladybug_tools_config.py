"""Ladybug Tools SDK runtime configuration services."""

from __future__ import annotations

from contextlib import contextmanager
import glob
import json
import os
from pathlib import Path
import re
import socket
from typing import Any
from urllib.parse import urlparse
import shutil

from dragonfly_energy.config import folders as dragonfly_energy_folders
from garden.fairyfly.availability import therm_engine_config
from honeybee.config import folders as hb_folders
from honeybee_energy.config import folders as energy_folders
from honeybee_radiance.config import folders as radiance_folders
from ladybug.config import folders as lb_folders
from ladybug_tools_mcp.contracts import make_report

REQUIRED_RUNTIME_VERSIONS: dict[str, str] = {
    "radiance": "5.4",
    "openstudio": "3.10.0",
    "energyplus": "25.1.0",
    "urbanopt": "1.4.0",
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

URBANOPT_GRID_LOCAL_SERVICE_CONFIGS: dict[str, dict[str, str]] = {
    "rnm": {
        "env_var": "LADYBUG_MCP_RNM_USE_LOCALHOST",
        "default_local_endpoint": "http://0.0.0.0:8080/api/v2/",
        "default_online_endpoint": "https://rnm.urbanopt.net/api/v2/",
    },
    "reopt": {
        "env_var": "LADYBUG_MCP_REOPT_USE_LOCALHOST",
        "default_local_endpoint": "http://127.0.0.1:8000/v3/",
        "default_online_endpoint": "https://developer.nrel.gov/api/reopt/v3/",
    },
}

URBANOPT_PYTHON_CONFIG_ENV_VAR = "LADYBUG_MCP_URBANOPT_PYTHON_CONFIG"
URBANOPT_SDK_OUTPUT_TYPES = ("osm", "idf", "sql", "zsz", "rdd", "html", "err")

_ENGINE_HELP: dict[str, dict[str, Any]] = {
    "radiance": {
        "documentation_url": "https://www.radiance-online.org/download-install",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": "Install Radiance matching the runtime matrix so honeybee-radiance resolves radbin/radlib.",
        "required_for": ["Radiance daylight simulation and postprocess"],
    },
    "openstudio": {
        "documentation_url": "https://github.com/NREL/OpenStudio/releases",
        "compatibility_url": "https://github.com/NREL/OpenStudio/wiki/OpenStudio-SDK-Version-Compatibility-Matrix",
        "install_hint": "Install the OpenStudio SDK version listed in the Ladybug Tools runtime matrix.",
        "required_for": ["Honeybee Energy simulation", "Dragonfly Energy simulation"],
    },
    "energyplus": {
        "documentation_url": "https://energyplus.net/downloads",
        "compatibility_url": "https://github.com/NREL/OpenStudio/wiki/OpenStudio-SDK-Version-Compatibility-Matrix",
        "install_hint": "EnergyPlus is bundled with the compatible OpenStudio SDK.",
        "required_for": ["EnergyPlus simulation through OpenStudio"],
    },
    "urbanopt": {
        "documentation_url": "https://docs.urbanopt.net/installation/installation.html",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": "Install URBANopt CLI matching the Ladybug Tools runtime matrix.",
        "required_for": ["Dragonfly district-scale URBANopt workflows"],
    },
    "des_gmt": {
        "documentation_url": "https://github.com/ladybug-tools/dragonfly-energy",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": "Install geojson-modelica-translator (uo_des), ThermalNetwork, and Modelica Buildings Library.",
        "required_for": ["Dragonfly DES system-parameter sizing", "Dragonfly DES Modelica generation"],
    },
    "therm": {
        "documentation_url": "https://github.com/LoftyTao/pyHygroThermFEM-Fairyfly",
        "compatibility_url": "https://github.com/LoftyTao/fairyfly-next-therm",
        "install_hint": (
            "Bundled cross-platform pyHygroThermFEM-Fairyfly C++20 solver + Gmsh Q4 mesher "
            "(no external LBNL THERM installation required)."
        ),
        "required_for": ["Fairyfly 2D steady-state, transient, and hygrothermal workflows"],
    },
    "ironbug_console": {
        "documentation_url": "https://github.com/MingboPeng/Ironbug",
        "compatibility_url": "https://github.com/ladybug-tools/lbt-grasshopper/wiki/1.4-Compatibility-Matrix",
        "install_hint": "Install Ironbug, OpenStudio C# bindings, and .NET 8+ runtime.",
        "required_for": ["Ironbug DetailedHVAC authoring/validation and OpenStudio translation"],
    },
}


def _normalized_path(value: str | Path | None) -> str | None:
    return str(Path(value).expanduser()) if value else None


def _path_record(value: str | Path | None, *, source: str | None = None) -> dict[str, Any]:
    path = str(value) if value else None
    record: dict[str, Any] = {
        "path": path,
        "exists": bool(path and Path(path).expanduser().exists()),
    }
    if source:
        record["source"] = source
    return record


def _version_tuple(value: Any) -> tuple[int, ...] | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.\-]\d+)+|\d+)", str(value))
    if not match:
        return None
    return tuple(int(item) for item in re.split(r"[.\-]", match.group(1)) if item)


def _version_from_name(value: str) -> str | None:
    parsed = _version_tuple(value)
    return ".".join(str(item) for item in parsed) if parsed else None


def _version_status(version: str | None, required: str | None) -> str:
    if not required:
        return "not_required"
    current, target = _version_tuple(version), _version_tuple(required)
    if current is None or target is None:
        return "unknown"
    prefix = current[: len(target)]
    if prefix == target:
        return "compatible"
    return "older" if prefix < target else "newer"


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
    source: str,
    exe: str | Path | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    path_str = _normalized_path(path)
    exe_str = _normalized_path(exe)
    record: dict[str, Any] = {
        "name": name,
        "source": source,
        "path": path_str,
        "path_exists": bool(path_str and Path(path_str).is_dir()),
        "version": version,
        "version_status": _version_status(version, REQUIRED_RUNTIME_VERSIONS.get(name)),
    }
    if exe is not None:
        record["exe"] = exe_str
        record["exe_exists"] = bool(exe_str and Path(exe_str).is_file())
    return record


def _dedupe_and_select(
    candidates: list[dict[str, Any]],
    *,
    name: str,
    configured_path: str | None,
) -> dict[str, Any]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item.get("path") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    selected = next((c for c in deduped if c.get("version_status") == "compatible"), None)
    reason = "compatible_candidate"
    if selected is None and configured_path:
        selected = next((c for c in deduped if c.get("path") == configured_path), None)
        reason = "configured_candidate_incompatible"
    if selected is None:
        selected = next((c for c in deduped if c.get("path_exists")), None)
        reason = "first_existing_candidate_incompatible" if selected else "no_candidate"
    if selected is None:
        selected = _candidate(name=name, path=None, source="not_found")

    record = dict(selected)
    record["configured_path"] = configured_path
    record["selection_reason"] = reason
    record["version_requirement"] = _version_requirement(name)
    record["candidates"] = deduped
    record.update(_ENGINE_HELP[name])
    return record


def _scan_runtime_dirs(prefix: str) -> list[Path]:
    matches: list[Path] = []
    for root in RUNTIME_SEARCH_ROOTS:
        if not root.exists():
            continue
        try:
            for folder in root.iterdir():
                if folder.is_dir() and folder.name.lower().startswith(prefix):
                    matches.append(folder)
        except OSError:
            continue
    return matches


def _first_existing_glob(pattern: str) -> Path | None:
    for raw in glob.glob(pattern):
        candidate = Path(raw)
        if candidate.exists():
            return candidate
    return None


def _select_openstudio_config() -> dict[str, Any]:
    exe_name = "openstudio.exe" if os.name == "nt" else "openstudio"
    configured_path = _normalized_path(getattr(energy_folders, "openstudio_path", None))
    candidates = [
        _candidate(
            name="openstudio",
            path=configured_path,
            exe=getattr(energy_folders, "openstudio_exe", None),
            version=getattr(energy_folders, "openstudio_version_str", None),
            source="sdk_config",
        )
    ]
    for folder in _scan_runtime_dirs("openstudio"):
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
    return _dedupe_and_select(candidates, name="openstudio", configured_path=configured_path)


def _select_energyplus_config(openstudio: dict[str, Any]) -> dict[str, Any]:
    exe_name = "energyplus.exe" if os.name == "nt" else "energyplus"
    configured_path = _normalized_path(getattr(energy_folders, "energyplus_path", None))
    candidates = [
        _candidate(
            name="energyplus",
            path=configured_path,
            exe=getattr(energy_folders, "energyplus_exe", None),
            version=getattr(energy_folders, "energyplus_version_str", None),
            source="sdk_config",
        )
    ]
    os_path = openstudio.get("path")
    if isinstance(os_path, str) and os_path:
        os_root = Path(os_path).parent if Path(os_path).name.lower() == "bin" else Path(os_path)
        bundled = os_root / "EnergyPlus"
        if (bundled / exe_name).is_file():
            os_ver = _version_tuple(openstudio.get("version"))
            ver_key = ".".join(str(x) for x in os_ver[:3]) if os_ver else ""
            candidates.append(
                _candidate(
                    name="energyplus",
                    path=bundled,
                    exe=bundled / exe_name,
                    version=OPENSTUDIO_ENERGYPLUS_VERSIONS.get(ver_key),
                    source="selected_openstudio_bundle",
                )
            )
    for folder in _scan_runtime_dirs("energyplus"):
        if (folder / exe_name).is_file():
            candidates.append(
                _candidate(
                    name="energyplus",
                    path=folder,
                    exe=folder / exe_name,
                    version=_version_from_name(folder.name),
                    source="filesystem_scan",
                )
            )
    return _dedupe_and_select(candidates, name="energyplus", configured_path=configured_path)


def _urbanopt_python_config_path(cli_gem_bundle: Path | None) -> tuple[Path | None, str]:
    explicit = os.environ.get(URBANOPT_PYTHON_CONFIG_ENV_VAR)
    if isinstance(explicit, str) and explicit.strip():
        return Path(explicit.strip()).expanduser(), f"env:{URBANOPT_PYTHON_CONFIG_ENV_VAR}"
    if cli_gem_bundle is None:
        return None, "cli_bundle_python_deps"
    matches = sorted(
        (cli_gem_bundle / "gems").glob("urbanopt-cli-*/example_files/python_deps/python_config.json")
    )
    if matches:
        return matches[0], "cli_bundle_python_deps"
    return (
        cli_gem_bundle
        / "gems"
        / f"urbanopt-cli-{REQUIRED_RUNTIME_VERSIONS['urbanopt']}"
        / "example_files"
        / "python_deps"
        / "python_config.json",
        "cli_bundle_python_deps",
    )


def _load_json_dict(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _urbanopt_opendss_python_deps(cli_gem_bundle: Path | None) -> dict[str, Any]:
    config_path, source = _urbanopt_python_config_path(cli_gem_bundle)
    loaded = _load_json_dict(config_path)
    required_keys = ["python_path", "pip_path", "ditto_path"]
    configured_paths = {
        key: _path_record(loaded.get(key) if isinstance(loaded.get(key), str) else None)
        for key in required_keys
    }
    missing = [key for key in required_keys if not configured_paths[key]["exists"]]
    ready = bool(config_path and config_path.is_file() and loaded and not missing)
    deps_dir = (
        sorted((cli_gem_bundle / "gems").glob("urbanopt-cli-*/example_files/python_deps"))[0]
        if cli_gem_bundle and sorted((cli_gem_bundle / "gems").glob("urbanopt-cli-*/example_files/python_deps"))
        else (config_path.parent if config_path else None)
    )
    deps_file = (deps_dir / "dependencies.json") if deps_dir else None
    return {
        "path": str(deps_dir) if deps_dir else None,
        "path_exists": bool(deps_dir and deps_dir.is_dir()),
        "initialized": bool(config_path and config_path.is_file()),
        "python_config": _path_record(config_path, source=source if config_path else None),
        "dependencies_file": _path_record(deps_file),
        "offline_runtime_pack": {
            "required": True,
            "source": "explicit_python_config" if source.startswith("env:") else source,
            "ready": ready,
            "python_config": _path_record(
                config_path,
                source=source if source.startswith("env:") else "cli_bundle_python_deps",
            ),
            "configured_paths": configured_paths,
            "missing_required_paths": missing,
        },
    }


def _local_endpoint_reachable(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    host, port = parsed.hostname, parsed.port
    if not host or port is None:
        return False
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _urbanopt_grid_service_config(recipe: str, cli_gem_bundle: Path | None) -> dict[str, Any]:
    cfg = URBANOPT_GRID_LOCAL_SERVICE_CONFIGS[recipe]
    env_var = cfg["env_var"]
    configured = (os.environ.get(env_var) or "").strip().lower() in {"1", "true", "yes", "on"}
    adapter_ready = bool(cli_gem_bundle and cli_gem_bundle.is_dir())
    reachable = configured and adapter_ready and _local_endpoint_reachable(cfg["default_local_endpoint"])
    missing = []
    if not configured:
        missing.append("local_service_configuration")
    if not adapter_ready:
        missing.append("mcp_localhost_adapter")
    elif not reachable:
        missing.append("local_service_unreachable")
    return {
        "recipe": recipe,
        "local_service_required": True,
        "configured": configured,
        "configuration_env_var": env_var,
        "ready": bool(configured and adapter_ready and reachable),
        "missing": missing,
        "mcp_adapter_ready": adapter_ready,
        "local_service_reachable": reachable,
        "default_local_endpoint": cfg["default_local_endpoint"],
        "default_online_endpoint": cfg["default_online_endpoint"],
    }


def _urbanopt_path_updates(cli_path: str | None) -> dict[str, Any]:
    if not cli_path:
        return {"prepend": [], "env": {}}
    base = Path(cli_path)
    ruby_bin = base / "ruby" / "bin"
    gem_bin = _first_existing_glob(str(base / "gems" / "ruby" / "*" / "bin"))
    prepend = [str(p) for p in [ruby_bin, *([gem_bin] if gem_bin else [])] if p.is_dir()]
    env: dict[str, str] = {"PATH": os.pathsep.join(prepend)}
    gem_home = gem_bin.parent if gem_bin else None
    if gem_home and gem_home.is_dir():
        env.update(
            {
                "GEM_HOME": str(gem_home),
                "GEM_PATH": str(gem_home),
                "UO_CLI_GEM_BUNDLE_PATH": str(gem_home),
                "BUNDLE_RETRY": "0",
                "BUNDLE_DISABLE_VERSION_CHECK": "true",
                "UO_BUNDLE_INSTALL_PATH": str(gem_home),
            }
        )
    cli_gemfile = base / "gems" / "Gemfile"
    if cli_gemfile.is_file():
        env["BUNDLE_GEMFILE"] = str(cli_gemfile)
        env["UO_CLI_GEMFILE_PATH"] = str(cli_gemfile)
    os_gemfile = base / "openstudio-runtime-gems" / "Gemfile"
    if os_gemfile.is_file():
        env["UO_OPENSTUDIO_RUNTIME_GEMFILE_PATH"] = str(os_gemfile)
        env["UO_GEMFILE_PATH"] = str(os_gemfile)
        env["UO_BUNDLE_INSTALL_PATH"] = str(os_gemfile.parent)
    openstudio_ruby = base / "OpenStudio" / "Ruby"
    if openstudio_ruby.is_dir():
        env["RUBYLIB"] = str(openstudio_ruby)
        env["RUBY_DLL_PATH"] = str(openstudio_ruby)
    return {"prepend": prepend, "env": env}


def _urbanopt_version_from_dir(path: str | None) -> str | None:
    if not path:
        return None
    match = re.search(r"URBANopt-cli-(\d+(?:\.\d+)+)", str(path), re.IGNORECASE)
    return match.group(1) if match else None


def _urbanopt_config() -> dict[str, Any]:
    folders = dragonfly_energy_folders
    configured_path = _normalized_path(getattr(folders, "urbanopt_cli_path", None))
    detected = getattr(folders, "_urbanopt_version_str", None) or _urbanopt_version_from_dir(configured_path)
    candidates = [_candidate(name="urbanopt", path=configured_path, version=detected, source="sdk_config")]
    for folder in _scan_runtime_dirs("urbanopt-cli"):
        candidates.append(
            _candidate(
                name="urbanopt",
                path=folder,
                version=_urbanopt_version_from_dir(str(folder)),
                source="filesystem_scan",
            )
        )
    selected = _dedupe_and_select(candidates, name="urbanopt", configured_path=configured_path)
    cli_path = selected.get("path") or configured_path
    sdk_gemfile = _normalized_path(getattr(folders, "urbanopt_gemfile_path", None))
    cli_gemfile = str(Path(cli_path) / "gems" / "Gemfile") if cli_path else None
    os_gemfile = str(Path(cli_path) / "openstudio-runtime-gems" / "Gemfile") if cli_path else None
    gemfile_path, gemfile_source = (
        (sdk_gemfile, "sdk_config")
        if sdk_gemfile and Path(sdk_gemfile).expanduser().is_file()
        else (cli_gemfile, "cli_bundle")
    )
    cli_gem_bundle = _first_existing_glob(str(Path(cli_path) / "gems" / "ruby" / "*")) if cli_path else None
    setup_candidates = (
        [_path_record(Path(cli_path) / f"setup-env.{ext}") for ext in ("bat", "ps1", "sh")]
        if cli_path
        else []
    )
    record: dict[str, Any] = {
        **selected,
        "kind": "urbanopt_runtime",
        "available": bool(
            cli_path and Path(cli_path).expanduser().is_dir() and gemfile_path and Path(gemfile_path).expanduser().is_file()
        ),
        "detected_version": selected.get("version"),
        "cli": _path_record(cli_path),
        "gemfile": _path_record(gemfile_path, source=gemfile_source),
        "cli_runtime_gemfile": _path_record(cli_gemfile, source="cli_bundle"),
        "openstudio_runtime_gemfile": _path_record(os_gemfile, source="openstudio_runtime"),
        "cli_gem_bundle": _path_record(cli_gem_bundle, source="cli_runtime"),
        "rnm_service": _urbanopt_grid_service_config("rnm", cli_gem_bundle),
        "reopt_service": _urbanopt_grid_service_config("reopt", cli_gem_bundle),
        "opendss_python_deps": _urbanopt_opendss_python_deps(cli_gem_bundle),
        "setup_env": {
            "configured": _path_record(getattr(folders, "urbanopt_env_path", None)),
            "candidates": setup_candidates,
            "generatable": any(item["exists"] for item in setup_candidates),
        },
        "path_updates": _urbanopt_path_updates(cli_path),
    }
    _apply_runtime_requirement("urbanopt", record)
    return record


def _dist_info_record(package_path: Path, package_name: str, required_version: str | None) -> dict[str, Any]:
    candidates = sorted(package_path.glob(f"{package_name}-*.dist-info")) if package_path.is_dir() else []
    expected = package_path / f"{package_name}-{required_version}.dist-info" if required_version else None
    selected = expected if expected and expected.is_dir() else (candidates[0] if candidates else None)
    version = _version_from_name(selected.name) if selected else None
    return {
        "package_name": package_name,
        "required_version": required_version,
        "path": str(selected) if selected else str(package_path / f"{package_name}-{required_version or '*'}.dist-info"),
        "installed": bool(selected and selected.is_dir()),
        "version": version,
        "version_status": _version_status(version, required_version),
    }


def _des_gmt_config() -> dict[str, Any]:
    scripts_path = Path(str(getattr(hb_folders, "python_scripts_path", "") or "")).expanduser()
    package_path = Path(str(getattr(hb_folders, "python_package_path", "") or "")).expanduser()
    ext = ".exe" if os.name == "nt" else ""
    uo_des, thermalnetwork = scripts_path / f"uo_des{ext}", scripts_path / f"thermalnetwork{ext}"
    gmt_ver = str(getattr(dragonfly_energy_folders, "UO_GMT_VERSION", "") or "") or None
    tn_ver = str(getattr(dragonfly_energy_folders, "UO_TN_VERSION", "") or "") or None
    mbl_ver = str(getattr(dragonfly_energy_folders, "MBL_VERSION", "") or "") or None

    packages = {
        "geojson_modelica_translator": _dist_info_record(package_path, "geojson_modelica_translator", gmt_ver),
        "thermalnetwork": _dist_info_record(package_path, "ThermalNetwork", tn_ver),
    }
    source = "ladybug_tools_python"

    # Fall back to initialized URBANopt offline runtime pack if LBT Python lacks DES tools.
    if not (uo_des.is_file() and thermalnetwork.is_file() and all(p["installed"] for p in packages.values())):
        cli_path = _normalized_path(getattr(dragonfly_energy_folders, "urbanopt_cli_path", None))
        bundle = _first_existing_glob(str(Path(cli_path) / "gems" / "ruby" / "*")) if cli_path else None
        cfg_path, _ = _urbanopt_python_config_path(bundle)
        cfg = _load_json_dict(cfg_path)
        py_path = Path(cfg["python_path"]).expanduser() if isinstance(cfg.get("python_path"), str) else None
        pack_uo = Path(cfg["gmt_path"]).expanduser() if isinstance(cfg.get("gmt_path"), str) else None
        pack_tn = Path(cfg["ghe_path"]).expanduser() if isinstance(cfg.get("ghe_path"), str) else None
        pack_pkgs_dir = py_path.parent / "Lib" / "site-packages" if py_path else Path("")
        if pack_uo and pack_uo.is_file() and pack_tn and pack_tn.is_file() and py_path:
            cand_pkgs = {
                "geojson_modelica_translator": _dist_info_record(pack_pkgs_dir, "geojson_modelica_translator", gmt_ver),
                "thermalnetwork": _dist_info_record(pack_pkgs_dir, "ThermalNetwork", tn_ver),
            }
            if all(p["installed"] for p in cand_pkgs.values()):
                source = "urbanopt_offline_runtime_pack"
                scripts_path, package_path = py_path.parent, pack_pkgs_dir
                uo_des, thermalnetwork, packages = pack_uo, pack_tn, cand_pkgs

    mbl_dir = Path(str(getattr(lb_folders, "ladybug_tools_folder", "") or "")).expanduser() / "resources" / "mbl"
    version_file = mbl_dir / "version.txt"
    installed_mbl = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None
    mbl = {
        "path": str(mbl_dir),
        "exists": mbl_dir.is_dir(),
        "required_version": mbl_ver,
        "version": installed_mbl,
        "version_status": _version_status(installed_mbl, mbl_ver),
    }
    missing = [
        name
        for name, is_missing in {
            "uo_des": not uo_des.is_file(),
            "thermalnetwork": not thermalnetwork.is_file(),
            "geojson_modelica_translator": not packages["geojson_modelica_translator"]["installed"],
            "thermalnetwork_package": not packages["thermalnetwork"]["installed"],
            "modelica_buildings_library": not (mbl["exists"] and mbl["version_status"] == "compatible"),
        }.items()
        if is_missing
    ]
    return {
        "name": "des_gmt",
        "kind": "dragonfly_des_dependency_runtime",
        "available": not missing,
        "source": source,
        "path": str(scripts_path),
        "path_exists": scripts_path.is_dir(),
        "exe": _path_record(uo_des),
        "exe_exists": uo_des.is_file(),
        "thermalnetwork_exe": _path_record(thermalnetwork),
        "python_package_path": str(package_path),
        "python_package_path_exists": package_path.is_dir(),
        "packages": packages,
        "modelica_buildings_library": mbl,
        "missing": missing,
        **_ENGINE_HELP["des_gmt"],
    }


def _ironbug_console_config() -> dict[str, Any]:
    from garden.ironbug.runtime import (
        _repo_or_packaged_bridge_dll,
        resolve_ironbug_console_exe,
        resolve_ironbug_dir,
        resolve_openstudio_csharp_dir,
    )

    ib_dir = resolve_ironbug_dir()
    exe = resolve_ironbug_console_exe(ib_dir)
    os_cs_dir = resolve_openstudio_csharp_dir(ib_dir)
    bridge_dll = _repo_or_packaged_bridge_dll()
    dotnet_exe = shutil.which("dotnet")
    path_str = str(ib_dir) if ib_dir else getattr(energy_folders, "ironbug_path", None)
    exe_str = str(exe) if exe else getattr(energy_folders, "ironbug_exe", None)
    record: dict[str, Any] = {
        "name": "ironbug_console",
        "path": path_str,
        "path_exists": bool(path_str and Path(path_str).expanduser().is_dir()),
        "exe": exe_str,
        "exe_exists": bool(exe_str and Path(exe_str).expanduser().is_file()),
        "version": getattr(energy_folders, "ironbug_version_str", None),
        "ironbug_hvac_dll_exists": bool(ib_dir and (ib_dir / "Ironbug.HVAC.dll").is_file()),
        "openstudio_csharp_path": str(os_cs_dir) if os_cs_dir else None,
        "openstudio_csharp_dll_exists": bool(os_cs_dir and (os_cs_dir / "OpenStudio.dll").is_file()),
        "dotnet_available": bool(dotnet_exe),
        "dotnet_exe": dotnet_exe,
        "bridge_dll_exists": bool(bridge_dll and bridge_dll.is_file()),
        **_ENGINE_HELP["ironbug_console"],
    }
    return _apply_runtime_requirement("ironbug_console", record)


def _radiance_config() -> dict[str, Any]:
    path = radiance_folders.radiance_path
    bin_path = radiance_folders.radbin_path
    lib_path = radiance_folders.radlib_path
    try:
        version = radiance_folders.radiance_version_str
    except Exception:
        version = None
    record: dict[str, Any] = {
        "name": "radiance",
        "path": path,
        "path_exists": bool(path and Path(path).expanduser().is_dir()),
        "bin_path": bin_path,
        "bin_path_exists": bool(bin_path and Path(bin_path).expanduser().is_dir()),
        "lib_path": lib_path,
        "lib_path_exists": bool(lib_path and Path(lib_path).expanduser().is_dir()),
        "version": version,
        **_ENGINE_HELP["radiance"],
    }
    return _apply_runtime_requirement("radiance", record)


def _path_prepend_values(engines: dict[str, dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for engine in engines.values():
        if engine.get("kind") == "hygrothermfem_runtime":
            continue
        prepend = (engine.get("path_updates") or {}).get("prepend") or []
        for value in prepend:
            if isinstance(value, str) and value and Path(value).expanduser().is_dir() and value not in values:
                values.append(value)
        for key in ("bin_path", "path"):
            value = engine.get(key)
            if isinstance(value, str) and value and Path(value).expanduser().is_dir() and value not in values:
                values.append(value)
                break
    return values


def _runtime_guidance(name: str, engine: dict[str, Any]) -> dict[str, Any]:
    required = REQUIRED_RUNTIME_VERSIONS.get(name)
    hint = engine.get("install_hint") or _ENGINE_HELP[name].get("install_hint")
    if required and hint:
        hint = f"{hint} Required version: {required}."
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


def get_ladybug_tools_config() -> dict[str, Any]:
    """Return compact SDK runtime configuration for Ladybug Tools engines."""
    openstudio = _select_openstudio_config()
    therm = therm_engine_config()
    _apply_runtime_requirement("therm", therm)
    therm.update(_ENGINE_HELP["therm"])

    engines: dict[str, dict[str, Any]] = {
        "radiance": _radiance_config(),
        "openstudio": openstudio,
        "energyplus": _select_energyplus_config(openstudio),
        "urbanopt": _urbanopt_config(),
        "des_gmt": _des_gmt_config(),
        "therm": therm,
        "ironbug_console": _ironbug_console_config(),
    }
    measures = {
        "lbt_measures_path": _path_record(energy_folders.lbt_measures_path),
        "openstudio_results_measure_path": _path_record(energy_folders.openstudio_results_measure_path),
        "honeybee_openstudio_gem_path": _path_record(energy_folders.honeybee_openstudio_gem_path),
    }
    prepend = _path_prepend_values(engines)
    missing = [
        name
        for name, engine in engines.items()
        if not engine.get("path_exists")
        or ("exe_exists" in engine and not engine.get("exe_exists"))
        or ("bin_path_exists" in engine and not engine.get("bin_path_exists"))
        or (name in {"des_gmt", "therm"} and not engine.get("available"))
    ]
    incompatible = [
        name
        for name, engine in engines.items()
        if engine.get("version_requirement") and engine.get("version_status") in {"older", "newer", "unknown"}
    ]
    warnings: list[str] = []
    if missing:
        warnings.append("Some configured Ladybug Tools engines or executable paths are missing: " + ", ".join(missing))
    if incompatible:
        warnings.append("Some configured Ladybug Tools engines do not match the required runtime versions: " + ", ".join(incompatible))

    return {
        "summary_view": {
            "engines": engines,
            "measures": measures,
            "path_updates": {"prepend": prepend, "env": {"PATH": os.pathsep.join(prepend)}},
            "missing_engines": missing,
            "incompatible_engines": incompatible,
            "missing_engine_guidance": {name: _runtime_guidance(name, engines[name]) for name in missing},
            "runtime_requirement_guidance": {
                name: _runtime_guidance(name, engines[name]) for name in sorted({*missing, *incompatible})
            },
        },
        "report": make_report(
            status="warning" if missing or incompatible else "ok",
            message="Ladybug Tools SDK runtime configuration returned.",
            warnings=warnings,
        ),
    }


def apply_ladybug_tools_runtime_to_path() -> list[str]:
    """Prepend SDK-discovered engine paths to the current process PATH."""
    prepend = list(get_ladybug_tools_config()["summary_view"]["path_updates"]["prepend"])
    if not prepend:
        return []
    current_parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    normalized_current = {str(Path(part)).lower() for part in current_parts}
    new_parts = [part for part in prepend if str(Path(part)).lower() not in normalized_current]
    if new_parts:
        os.environ["PATH"] = os.pathsep.join([*new_parts, *current_parts])
    return prepend


def _extract_runtime_path(runtime: dict[str, Any] | None, direct_key: str, env_keys: tuple[str, ...]) -> Path | None:
    if not isinstance(runtime, dict):
        return None
    direct = runtime.get(direct_key)
    if isinstance(direct, dict) and isinstance(direct.get("path"), str) and direct["path"]:
        return Path(direct["path"]).expanduser()
    env = (runtime.get("path_updates") or {}).get("env")
    if isinstance(env, dict):
        for key in env_keys:
            if isinstance(env.get(key), str) and env[key]:
                return Path(env[key]).expanduser()
    return None


def urbanopt_cli_gem_bundle_path(runtime: dict[str, Any] | None) -> Path | None:
    """Return the URBANopt CLI bundle path used by project-local Bundler config."""
    return _extract_runtime_path(runtime, "cli_gem_bundle", ("UO_CLI_GEM_BUNDLE_PATH", "GEM_HOME"))


def urbanopt_cli_runtime_gemfile_path(runtime: dict[str, Any] | None) -> Path | None:
    """Return the URBANopt CLI Gemfile used for ``bundle exec uo`` commands."""
    path = _extract_runtime_path(runtime, "cli_runtime_gemfile", ("BUNDLE_GEMFILE", "UO_CLI_GEMFILE_PATH"))
    if path is not None:
        return path
    cli_path = runtime.get("path") if isinstance(runtime, dict) else None
    if isinstance(cli_path, str) and cli_path:
        candidate = Path(cli_path).expanduser() / "gems" / "Gemfile"
        if candidate.is_file():
            return candidate
    return None


def write_urbanopt_bundle_config(project_dir: str | Path, runtime: dict[str, Any] | None) -> Path | None:
    """Use the installed OpenStudio runtime bundle for building simulations."""
    if urbanopt_cli_gem_bundle_path(runtime) is None:
        return None
    runtime_file = (runtime or {}).get("openstudio_runtime_gemfile", {}).get("path")
    if not runtime_file:
        raise ValueError("URBANopt OpenStudio runtime Gemfile is unavailable.")
    bundle_path = Path(runtime_file).parent
    if not (bundle_path / "Gemfile.lock").is_file():
        raise ValueError("URBANopt OpenStudio runtime Gemfile.lock is unavailable.")
    project_path = Path(project_dir).expanduser().resolve()
    config_dir = project_path / ".bundle"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config"
    bundle_value = str(bundle_path).replace("\\", "/")
    config_path.write_text(f'---\nBUNDLE_PATH: "{bundle_value}"\n', encoding="utf-8")

    gemfile_path, runner_conf = project_path / "Gemfile", project_path / "runner.conf"
    if gemfile_path.is_file() and runner_conf.is_file():
        runner_config = _load_json_dict(runner_conf)
        if runner_config:
            for source in [bundle_path / "Gemfile", *bundle_path.glob("*.gemspec"), bundle_path / "Gemfile.lock"]:
                shutil.copyfile(source, project_path / source.name)
            runner_config["gemfile_path"] = str(gemfile_path).replace("\\", "/")
            runner_config["bundle_install_path"] = bundle_value
            runner_conf.write_text(json.dumps(runner_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return config_path


@contextmanager
def urbanopt_runtime_env(runtime: dict[str, Any] | None):
    """Temporarily expose URBANopt CLI env discovered by LB_Get_Runtime_Config."""
    path_updates = runtime.get("path_updates") if isinstance(runtime, dict) else None
    if not isinstance(path_updates, dict):
        yield
        return
    env_updates = path_updates.get("env") if isinstance(path_updates.get("env"), dict) else {}
    prepend = [str(p) for p in (path_updates.get("prepend") or []) if isinstance(p, str) and p]
    original: dict[str, str | None] = {}
    try:
        for key, value in env_updates.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            original.setdefault(key, os.environ.get(key))
            if key.upper() == "PATH":
                parts = [p for p in value.split(os.pathsep) if p]
                current = os.environ.get("PATH", "")
                os.environ["PATH"] = os.pathsep.join([*parts, current]) if current else value
            else:
                os.environ[key] = value
        if prepend:
            original.setdefault("PATH", os.environ.get("PATH"))
            current = os.environ.get("PATH", "")
            os.environ["PATH"] = os.pathsep.join([*prepend, current]) if current else os.pathsep.join(prepend)
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def iter_urbanopt_sdk_output_paths(value: Any):
    """Yield (output_type, path) pairs from Dragonfly Energy URBANopt SDK results."""
    if isinstance(value, dict):
        for output_type, paths in value.items():
            items = paths if isinstance(paths, (list, tuple)) else [paths]
            for path in items:
                if path:
                    yield str(output_type), path
        return
    if isinstance(value, (list, tuple)):
        if len(value) == len(URBANOPT_SDK_OUTPUT_TYPES) and any(isinstance(item, (list, tuple)) for item in value):
            for output_type, paths in zip(URBANOPT_SDK_OUTPUT_TYPES, value):
                items = paths if isinstance(paths, (list, tuple)) else [paths]
                for path in items:
                    if path:
                        yield output_type, path
            return
        for path in value:
            if path:
                yield None, path
        return
    if value:
        yield None, value
