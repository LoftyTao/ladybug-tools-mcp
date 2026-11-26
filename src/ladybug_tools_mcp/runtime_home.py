"""Managed runtime home, SDK config synchronization, .lbtpack packs, and doctor checks."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from typing import Any
from zipfile import ZipFile

from flowerpot.installation import read_installation
from ladybug_tools_mcp import __version__

_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PACK_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

REQUIRED_ENGINES: tuple[str, ...] = (
    "radiance",
    "openstudio",
    "energyplus",
    "ironbug_console",
    "therm",
)
OPTIONAL_ENGINES: tuple[str, ...] = ("urbanopt", "des_gmt")

RUNTIME_CONFIG_KEYS: tuple[str, ...] = (
    "ladybug_tools_folder",
    "default_epw_folder",
    "default_simulation_folder",
    "default_standards_folder",
    "openstudio_path",
    "energyplus_path",
    "radiance_path",
    "ironbug_path",
    "openstudio_csharp_path",
    "lbt_measures_path",
    "standards_data_folder",
    "standards_extension_folders",
    "defaults_file",
    "mapper_path",
    "urbanopt_gemfile_path",
    "urbanopt_cli_path",
    "urbanopt_env_path",
    "reopt_assumptions_path",
    "python_home",
)

_SDK_CONFIG_TEMPLATES: dict[str, dict[str, Any]] = {
    "ladybug": {
        "__comment__": "Managed by lbt-mcp runtime sync. Do not edit manually.",
        "ladybug_tools_folder": "",
        "default_epw_folder": "",
    },
    "honeybee": {
        "__comment__": "Managed by lbt-mcp runtime sync. Do not edit manually.",
        "default_simulation_folder": "",
        "default_standards_folder": "",
    },
    "honeybee_energy": {
        "__comment__": "Managed by lbt-mcp runtime sync. Do not edit manually.",
        "energyplus_path": "",
        "openstudio_path": "",
        "lbt_measures_path": "",
        "ironbug_path": "",
        "standards_data_folder": "",
        "standards_extension_folders": [],
        "defaults_file": "",
    },
    "honeybee_radiance": {
        "__comment__": "Managed by lbt-mcp runtime sync. Do not edit manually.",
        "radiance_path": "",
        "standards_data_folder": "",
        "defaults_file": "",
    },
    "dragonfly_energy": {
        "__comment__": "Managed by lbt-mcp runtime sync. Do not edit manually.",
        "mapper_path": "",
        "urbanopt_gemfile_path": "",
        "urbanopt_cli_path": "",
        "urbanopt_env_path": "",
        "reopt_assumptions_path": "",
    },
}


def is_ascii_space_free(path: str | Path) -> bool:
    """Return True when path is non-empty, pure ASCII, and contains no whitespace."""
    text = os.fspath(path)
    return bool(text) and text.isascii() and not any(ch.isspace() for ch in text)


def default_home_dir() -> Path:
    """Resolve default runtime home: LADYBUG_TOOLS_MCP_HOME, %LOCALAPPDATA%\\lbt-mcp if safe, else C:\\lbt-mcp."""
    env_home = os.environ.get("LADYBUG_TOOLS_MCP_HOME")
    if isinstance(env_home, str) and env_home.strip():
        return Path(env_home.strip()).expanduser().resolve()

    if os.name == "nt" or sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if isinstance(local_appdata, str) and local_appdata.strip():
            candidate = Path(local_appdata.strip()).expanduser() / "lbt-mcp"
            if is_ascii_space_free(str(candidate)):
                return candidate
        return Path(r"C:\lbt-mcp")

    xdg_data = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data.strip()).expanduser() if isinstance(xdg_data, str) and xdg_data.strip() else (Path.home() / ".local" / "share")
    candidate = base / "lbt-mcp"
    if is_ascii_space_free(str(candidate)):
        return candidate
    return Path("/tmp/lbt-mcp")


def resolve_home_dir(
    home: str | Path | None = None,
    *,
    state_path: str | Path | None = None,
) -> Path:
    """Resolve active runtime home from explicit path, env var, installation record, or default."""
    if home is not None:
        return Path(home).expanduser().resolve()
    env_home = os.environ.get("LADYBUG_TOOLS_MCP_HOME")
    if isinstance(env_home, str) and env_home.strip():
        return Path(env_home.strip()).expanduser().resolve()
    try:
        record = read_installation(str(Path(state_path).expanduser()) if state_path else None)
    except Exception:
        record = {}
    if isinstance(record, dict) and isinstance(record.get("home"), str) and record["home"].strip():
        return Path(record["home"].strip()).expanduser().resolve()
    return default_home_dir()


def safe_ascii_temp_dir(garden_root: Path, run_name: str) -> Path:
    """Return a pure-ASCII temp directory for simulation workers on Windows."""
    resolved_root = Path(garden_root).expanduser().resolve()
    direct = (resolved_root / "tmp" / run_name).resolve()
    direct.relative_to(resolved_root)
    if str(direct).isascii():
        direct.mkdir(parents=True, exist_ok=True)
        return direct

    digest = hashlib.sha1(f"{resolved_root}\0{run_name}".encode()).hexdigest()[:12]
    candidates: list[Path] = []
    lbt_home = os.environ.get("LADYBUG_TOOLS_MCP_HOME")
    if isinstance(lbt_home, str) and lbt_home.strip():
        candidates.append(Path(lbt_home.strip()).expanduser().resolve() / "tmp" / "runs" / digest)
    candidates.append(Path(tempfile.gettempdir()).resolve() / "lbt_mcp_runs" / digest)
    sys_drive = (os.environ.get("SystemDrive") or "C:").rstrip("\\/")
    candidates.append(
        (Path(f"{sys_drive}{os.sep}") if os.name == "nt" else Path("/tmp")) / "lbt_mcp_tmp" / digest
    )
    for cand in candidates:
        if str(cand).isascii():
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    direct.mkdir(parents=True, exist_ok=True)
    return direct


def runtime_config_path(home: str | Path | None = None) -> Path:
    """Return <home>/config/runtime.json."""
    return resolve_home_dir(home) / "config" / "runtime.json"


def home_installation_path(home: str | Path | None = None) -> Path:
    """Return <home>/config/installation.json."""
    return resolve_home_dir(home) / "config" / "installation.json"


def user_installation_path() -> Path:
    """Return %USERPROFILE%/.ladybug-tools-mcp/installation.json."""
    return (Path.home() / ".ladybug-tools-mcp" / "installation.json").resolve()


def packs_dir(home: str | Path | None = None) -> Path:
    """Return <home>/config/packs."""
    return resolve_home_dir(home) / "config" / "packs"


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Write content atomically via temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def atomic_write_json(path: Path, data: Any) -> None:
    """Serialize JSON UTF-8 cleanly and write atomically."""
    encoded = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write_bytes(path, encoded)


def _version_sort_key(name: str) -> tuple[tuple[int, ...], str]:
    nums = tuple(int(part) for part in re.findall(r"\d+", name))
    return nums, name


def _rel_posix(home: Path, path: Path) -> str:
    return path.relative_to(home).as_posix()


def _discover_versioned_subdir(
    parent: Path,
    marker_rel: str,
    *,
    preferred: str | None = None,
) -> Path | None:
    if not parent.is_dir():
        return None
    if (parent / marker_rel).exists():
        return parent
    matches = [
        child for child in parent.iterdir()
        if child.is_dir() and (child / marker_rel).exists()
    ]
    if not matches:
        return None
    if preferred:
        for item in matches:
            if item.name == preferred:
                return item
    matches.sort(key=lambda item: _version_sort_key(item.name), reverse=True)
    return matches[0]


def _exe_name(stem: str) -> str:
    return f"{stem}.exe" if os.name == "nt" else stem


def default_runtime_config(home: str | Path | None = None) -> dict[str, Any]:
    """Build default runtime configuration anchored under <home>/runtimes/..."""
    home_dir = resolve_home_dir(home)
    runtimes = home_dir / "runtimes"

    os_exe = _exe_name("openstudio")
    ep_exe = _exe_name("energyplus")
    rad_exe = _exe_name("rad")
    py_exe = "python.exe" if os.name == "nt" else "bin/python3"

    lbt_home = runtimes / "lbt_home"
    if not lbt_home.is_dir() and (runtimes / "resources").is_dir():
        lbt_home = runtimes
    lbt_home_rel = _rel_posix(home_dir, lbt_home)

    os_root = _discover_versioned_subdir(
        runtimes / "openstudio",
        f"bin/{os_exe}",
        preferred="3.11.0",
    )
    if os_root is not None:
        os_bin_rel = _rel_posix(home_dir, os_root / "bin")
        ep_dir = (os_root / "EnergyPlus") if (os_root / "EnergyPlus" / ep_exe).is_file() else None
        cs_dir = (
            (os_root / "CSharp" / "openstudio")
            if (os_root / "CSharp" / "openstudio" / "OpenStudio.dll").is_file()
            else None
        )
    else:
        os_bin_rel = "runtimes/openstudio/3.11.0/bin"
        ep_dir = None
        cs_dir = None

    if ep_dir is None:
        ep_dir = _discover_versioned_subdir(runtimes / "energyplus", ep_exe, preferred="25.2.0")
    ep_rel = _rel_posix(home_dir, ep_dir) if ep_dir is not None else "runtimes/openstudio/3.11.0/EnergyPlus"
    cs_rel = (
        _rel_posix(home_dir, cs_dir)
        if cs_dir is not None
        else "runtimes/openstudio/3.11.0/CSharp/openstudio"
    )

    rad_root = _discover_versioned_subdir(runtimes / "radiance", f"bin/{rad_exe}", preferred="5.4")
    rad_rel = _rel_posix(home_dir, rad_root) if rad_root is not None else "runtimes/radiance/5.4"

    ib_root = _discover_versioned_subdir(runtimes / "ironbug", "Ironbug.HVAC.dll", preferred="1.26.1")
    ib_rel = _rel_posix(home_dir, ib_root) if ib_root is not None else "runtimes/ironbug/1.26.1"

    py_root = _discover_versioned_subdir(runtimes / "python", py_exe)
    if py_root is None and (runtimes / "python").is_dir():
        py_subdirs = sorted(
            (d for d in (runtimes / "python").iterdir() if d.is_dir()),
            key=lambda item: _version_sort_key(item.name),
            reverse=True,
        )
        if py_subdirs:
            py_root = py_subdirs[0]
    py_rel = _rel_posix(home_dir, py_root) if py_root is not None else ""

    uo_rel = ""
    if runtimes.is_dir():
        uo_candidates = sorted(
            (
                child for child in runtimes.iterdir()
                if child.is_dir()
                and child.name.lower().startswith("urbanopt")
                and (child / "gems" / "Gemfile").is_file()
            ),
            key=lambda item: _version_sort_key(item.name),
            reverse=True,
        )
        if uo_candidates:
            uo_rel = _rel_posix(home_dir, uo_candidates[0])
        else:
            nested = _discover_versioned_subdir(runtimes / "urbanopt", "gems/Gemfile")
            if nested is not None:
                uo_rel = _rel_posix(home_dir, nested)

    return {
        "schema_version": 1,
        "ladybug_tools_folder": lbt_home_rel,
        "default_epw_folder": "",
        "default_simulation_folder": "",
        "default_standards_folder": "",
        "openstudio_path": os_bin_rel,
        "energyplus_path": ep_rel,
        "radiance_path": rad_rel,
        "ironbug_path": ib_rel,
        "openstudio_csharp_path": cs_rel,
        "lbt_measures_path": f"{lbt_home_rel}/resources/measures",
        "standards_data_folder": "",
        "standards_extension_folders": [],
        "defaults_file": "",
        "mapper_path": "",
        "urbanopt_gemfile_path": "",
        "urbanopt_cli_path": uo_rel,
        "urbanopt_env_path": "",
        "reopt_assumptions_path": "",
        "python_home": py_rel,
    }


def read_runtime_config(home: str | Path | None = None) -> dict[str, Any]:
    """Read <home>/config/runtime.json merged with <home>/runtimes defaults."""
    home_dir = resolve_home_dir(home)
    defaults = default_runtime_config(home_dir)
    cfg_path = runtime_config_path(home_dir)
    if not cfg_path.is_file():
        return defaults
    loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid runtime config (expected JSON object): {cfg_path}")
    merged = {**defaults, **loaded}
    merged["schema_version"] = 1
    if not isinstance(merged.get("standards_extension_folders"), list):
        merged["standards_extension_folders"] = []
    return merged


def write_runtime_config(config: dict[str, Any], home: str | Path | None = None) -> Path:
    """Atomically persist <home>/config/runtime.json."""
    home_dir = resolve_home_dir(home)
    payload = dict(config)
    payload.setdefault("schema_version", 1)
    cfg_path = runtime_config_path(home_dir)
    atomic_write_json(cfg_path, payload)
    return cfg_path


def resolve_runtime_value(home: Path, value: Any) -> str:
    """Resolve a path value relative to home (preserving empty strings)."""
    if not isinstance(value, str) or not value.strip():
        return ""
    raw = Path(value.strip()).expanduser()
    resolved = raw if raw.is_absolute() else (home / raw)
    return str(resolved.resolve())


def resolved_runtime_config(home: str | Path | None = None) -> dict[str, Any]:
    """Return runtime.json values resolved to absolute paths under <home>."""
    home_dir = resolve_home_dir(home)
    raw = read_runtime_config(home_dir)
    resolved: dict[str, Any] = {"home": str(home_dir), "schema_version": raw.get("schema_version", 1)}
    for key in RUNTIME_CONFIG_KEYS:
        if key == "standards_extension_folders":
            items = raw.get(key) or []
            resolved[key] = [resolve_runtime_value(home_dir, item) for item in items if isinstance(item, str) and item.strip()]
        else:
            resolved[key] = resolve_runtime_value(home_dir, raw.get(key))
    return resolved


def _normalize_radiance_root(path_str: str) -> str:
    if not path_str:
        return ""
    rad_exe = _exe_name("rad")
    p = Path(path_str)
    if p.name.lower() == "bin" and (p / rad_exe).is_file():
        return str(p.parent)
    if (p / "bin" / rad_exe).is_file():
        return str(p)
    return ""


def _resolve_site_packages(home: Path, site_packages: str | Path | None) -> Path:
    if site_packages is not None:
        return Path(site_packages).expanduser().resolve()

    current_json = home / "app" / "current.json"
    if current_json.is_file():
        try:
            current = json.loads(current_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
        if isinstance(current, dict):
            sp_val = current.get("site_packages")
            if isinstance(sp_val, str) and sp_val.strip():
                candidate = Path(sp_val.strip())
                if not candidate.is_absolute():
                    candidate = home / candidate
                if candidate.is_dir():
                    return candidate.resolve()
            py_val = current.get("python")
            if isinstance(py_val, str) and py_val.strip():
                py_path = Path(py_val.strip())
                if not py_path.is_absolute():
                    py_path = home / py_path
                venv_dir = py_path.parent.parent
                candidate = venv_dir / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
                if candidate.is_dir():
                    return candidate.resolve()

    spec = importlib.util.find_spec("ladybug")
    if spec and spec.origin:
        return Path(spec.origin).resolve().parents[1]
    purelib = sysconfig.get_path("purelib")
    if purelib:
        return Path(purelib).resolve()
    raise RuntimeError("Could not locate Python site-packages directory.")


def _expected_sdk_configs(home: Path, raw_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute validated per-SDK config.json payloads that never raise AssertionError on import."""
    os_exe = _exe_name("openstudio")
    ep_exe = _exe_name("energyplus")
    ib_exe = _exe_name("Ironbug.Console")

    lbt_folder = resolve_runtime_value(home, raw_config.get("ladybug_tools_folder"))
    if lbt_folder and not Path(lbt_folder).is_dir():
        lbt_folder = ""

    default_epw = resolve_runtime_value(home, raw_config.get("default_epw_folder"))
    default_sim = resolve_runtime_value(home, raw_config.get("default_simulation_folder"))
    default_std = resolve_runtime_value(home, raw_config.get("default_standards_folder"))
    if default_std and not Path(default_std).is_dir():
        default_std = ""

    os_path = resolve_runtime_value(home, raw_config.get("openstudio_path"))
    if os_path and not (Path(os_path) / os_exe).is_file():
        os_path = ""

    ep_path = resolve_runtime_value(home, raw_config.get("energyplus_path"))
    if ep_path and not (Path(ep_path) / ep_exe).is_file():
        ep_path = ""

    lbt_measures = resolve_runtime_value(home, raw_config.get("lbt_measures_path"))
    if lbt_measures and not Path(lbt_measures).is_dir():
        lbt_measures = ""

    ib_path = resolve_runtime_value(home, raw_config.get("ironbug_path"))
    if ib_path and not (Path(ib_path) / ib_exe).is_file():
        ib_path = ""

    hb_std = resolve_runtime_value(home, raw_config.get("standards_data_folder"))
    if hb_std and not all((Path(hb_std) / sub).is_dir() for sub in ("constructions", "constructionsets", "schedules", "programtypes")):
        hb_std = ""

    hb_ext = [
        resolved
        for item in (raw_config.get("standards_extension_folders") or [])
        if isinstance(item, str)
        and (resolved := resolve_runtime_value(home, item))
        and all((Path(resolved) / sub).is_dir() for sub in ("constructions", "constructionsets", "schedules", "programtypes"))
    ]

    defaults_file = resolve_runtime_value(home, raw_config.get("defaults_file"))
    if defaults_file and not Path(defaults_file).is_file():
        defaults_file = ""

    rad_root = _normalize_radiance_root(resolve_runtime_value(home, raw_config.get("radiance_path")))

    mapper_path = resolve_runtime_value(home, raw_config.get("mapper_path"))
    if mapper_path and not (Path(mapper_path).is_file() and mapper_path.endswith(".rb")):
        mapper_path = ""

    uo_gemfile = resolve_runtime_value(home, raw_config.get("urbanopt_gemfile_path"))
    if uo_gemfile and not Path(uo_gemfile).is_file():
        uo_gemfile = ""

    uo_cli = resolve_runtime_value(home, raw_config.get("urbanopt_cli_path"))
    if uo_cli and not Path(uo_cli).is_dir():
        uo_cli = ""

    uo_env = resolve_runtime_value(home, raw_config.get("urbanopt_env_path"))
    if uo_env and not Path(uo_env).is_file():
        uo_env = ""

    reopt_path = resolve_runtime_value(home, raw_config.get("reopt_assumptions_path"))
    if reopt_path and not Path(reopt_path).is_file():
        reopt_path = ""

    return {
        "ladybug": {
            **_SDK_CONFIG_TEMPLATES["ladybug"],
            "ladybug_tools_folder": lbt_folder,
            "default_epw_folder": default_epw,
        },
        "honeybee": {
            **_SDK_CONFIG_TEMPLATES["honeybee"],
            "default_simulation_folder": default_sim,
            "default_standards_folder": default_std,
        },
        "honeybee_energy": {
            **_SDK_CONFIG_TEMPLATES["honeybee_energy"],
            "energyplus_path": ep_path,
            "openstudio_path": os_path,
            "lbt_measures_path": lbt_measures,
            "ironbug_path": ib_path,
            "standards_data_folder": hb_std,
            "standards_extension_folders": hb_ext,
            "defaults_file": defaults_file,
        },
        "honeybee_radiance": {
            **_SDK_CONFIG_TEMPLATES["honeybee_radiance"],
            "radiance_path": rad_root,
            "standards_data_folder": "",
            "defaults_file": defaults_file,
        },
        "dragonfly_energy": {
            **_SDK_CONFIG_TEMPLATES["dragonfly_energy"],
            "mapper_path": mapper_path,
            "urbanopt_gemfile_path": uo_gemfile,
            "urbanopt_cli_path": uo_cli,
            "urbanopt_env_path": uo_env,
            "reopt_assumptions_path": reopt_path,
        },
    }


def _find_pyvenv_cfgs(home: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    candidates: list[Path] = []
    releases = home / "app" / "releases"
    if releases.is_dir():
        candidates.extend(sorted(releases.glob("*/venv/pyvenv.cfg")))
    current_cfg = home / "app" / "current" / "venv" / "pyvenv.cfg"
    if current_cfg.is_file():
        candidates.append(current_cfg)
    for cfg in candidates:
        resolved = cfg.resolve()
        if resolved not in seen and cfg.is_file():
            seen.add(resolved)
            found.append(cfg)
    return found


def _target_python_home_for_cfg(home: Path, raw_config: dict[str, Any], cfg_text: str) -> Path | None:
    py_exe_rel = "python.exe" if os.name == "nt" else "bin/python3"
    configured = resolve_runtime_value(home, raw_config.get("python_home"))
    if configured:
        cand = Path(configured)
        if cand.is_dir():
            return cand
    py_root = home / "runtimes" / "python"
    found = _discover_versioned_subdir(py_root, py_exe_rel)
    if found is not None:
        return found
    if py_root.is_dir():
        subdirs = sorted(
            (d for d in py_root.iterdir() if d.is_dir()),
            key=lambda item: _version_sort_key(item.name),
            reverse=True,
        )
        if subdirs:
            return subdirs[0]
        for line in cfg_text.splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                if key.strip() == "version_info" and val.strip():
                    return py_root / val.strip()
    return None


def _update_pyvenv_cfg(cfg_path: Path, py_home: Path) -> bool:
    py_exe = py_home / ("python.exe" if os.name == "nt" else "bin/python3")
    original = cfg_path.read_text(encoding="utf-8")
    target_home = str(py_home)
    target_exe = str(py_exe)
    saw_home = False
    saw_exe = False
    lines: list[str] = []
    for line in original.splitlines():
        if "=" in line:
            key, _ = line.split("=", 1)
            key_trim = key.strip()
            if key_trim == "home":
                saw_home = True
                lines.append(f"home = {target_home}")
                continue
            if key_trim == "executable":
                saw_exe = True
                lines.append(f"executable = {target_exe}")
                continue
        lines.append(line)
    if not saw_home:
        lines.insert(0, f"home = {target_home}")
    if not saw_exe:
        lines.append(f"executable = {target_exe}")
    updated = "\n".join(lines) + "\n"
    if updated == original:
        return False
    atomic_write_bytes(cfg_path, updated.encode("utf-8"))
    return True


def _sync_current_skills(home: Path) -> str | None:
    current_skill = home / "app" / "current" / "skills" / "ladybug-tools-mcp-use"
    if current_skill.is_dir():
        return str(current_skill)
    current_json = home / "app" / "current.json"
    source_skill: Path | None = None
    if current_json.is_file():
        try:
            meta = json.loads(current_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if isinstance(meta, dict):
            skills_val = meta.get("skills_dir")
            if isinstance(skills_val, str) and skills_val.strip():
                cand = Path(skills_val.strip())
                if not cand.is_absolute():
                    cand = home / cand
                if cand.is_dir():
                    source_skill = cand
    if source_skill is None and (home / "app" / "releases").is_dir():
        for cand in sorted((home / "app" / "releases").glob("*/skills/ladybug-tools-mcp-use"), reverse=True):
            if cand.is_dir():
                source_skill = cand
                break
    if source_skill is not None and not (home / "app" / "current").is_symlink():
        current_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_skill, current_skill, dirs_exist_ok=True)
        return str(current_skill)
    return None


def _link_openstudio_csharp_to_ironbug(home: Path, raw_config: dict[str, Any]) -> list[str]:
    """Hardlink OpenStudio C# DLLs into the Ironbug runtime directory with copy fallback."""
    os_cs_str = resolve_runtime_value(home, raw_config.get("openstudio_csharp_path"))
    ib_str = resolve_runtime_value(home, raw_config.get("ironbug_path"))
    if not os_cs_str or not ib_str:
        return []
    os_cs_dir = Path(os_cs_str)
    ib_dir = Path(ib_str)
    if not os_cs_dir.is_dir() or not ib_dir.is_dir():
        return []
    if os_cs_dir.resolve() == ib_dir.resolve():
        return []

    linked: list[str] = []
    for src_dll in sorted(os_cs_dir.glob("*.dll")):
        if not src_dll.is_file():
            continue
        dst_dll = ib_dir / src_dll.name
        try:
            src_stat = src_dll.stat()
            if dst_dll.exists() or dst_dll.is_symlink():
                if not dst_dll.is_symlink():
                    dst_stat = dst_dll.stat()
                    if (
                        src_stat.st_ino != 0
                        and (src_stat.st_dev, src_stat.st_ino) == (dst_stat.st_dev, dst_stat.st_ino)
                        and src_stat.st_size == dst_stat.st_size
                    ):
                        linked.append(str(dst_dll))
                        continue
                dst_dll.unlink()
            try:
                os.link(src_dll, dst_dll)
            except OSError:
                shutil.copy2(src_dll, dst_dll)
            linked.append(str(dst_dll))
        except OSError:
            continue
    return linked


def sync_sdk_configs(
    home: str | Path | None = None,
    *,
    site_packages: str | Path | None = None,
    gardens_root: str | Path | None = None,
) -> dict[str, Any]:
    """Atomically sync all 5 SDK config.json files and pyvenv.cfg from <home>/config/runtime.json."""
    del gardens_root  # Gardens path belongs in installation.json, never inside SDK config.json.
    home_dir = resolve_home_dir(home)
    raw_config = read_runtime_config(home_dir)
    if not runtime_config_path(home_dir).is_file():
        write_runtime_config(raw_config, home_dir)

    sp_dir = _resolve_site_packages(home_dir, site_packages)
    expected = _expected_sdk_configs(home_dir, raw_config)

    updated_configs: list[str] = []
    skipped_configs: list[str] = []
    for pkg, payload in expected.items():
        pkg_dir = sp_dir / pkg
        if not pkg_dir.is_dir():
            skipped_configs.append(pkg)
            continue
        cfg_file = pkg_dir / "config.json"
        atomic_write_json(cfg_file, payload)
        updated_configs.append(str(cfg_file))

    updated_pyvenv: list[str] = []
    for cfg_path in _find_pyvenv_cfgs(home_dir):
        cfg_text = cfg_path.read_text(encoding="utf-8")
        py_home = _target_python_home_for_cfg(home_dir, raw_config, cfg_text)
        if py_home is not None:
            _update_pyvenv_cfg(cfg_path, py_home)
            updated_pyvenv.append(str(cfg_path))

    linked_dlls = _link_openstudio_csharp_to_ironbug(home_dir, raw_config)
    synced_skills = _sync_current_skills(home_dir)

    return {
        "home": str(home_dir),
        "runtime_config": str(runtime_config_path(home_dir)),
        "site_packages": str(sp_dir),
        "updated_sdk_configs": updated_configs,
        "skipped_sdk_packages": skipped_configs,
        "updated_pyvenv_cfgs": updated_pyvenv,
        "linked_ironbug_openstudio_dlls": linked_dlls,
        "skills_dir": synced_skills,
        "expected": expected,
    }


def _resolve_package_root(site_packages: Path | None) -> Path:
    if site_packages is not None and (site_packages / "flowerpot" / "runtime.py").is_file():
        return site_packages.resolve()
    import flowerpot

    return Path(flowerpot.__file__).resolve().parents[1]


def _resolve_target_python_for_record(home_dir: Path, python: str | Path | None) -> Path:
    if python is not None:
        return Path(python).expanduser().resolve()
    current_json = home_dir / "app" / "current.json"
    if current_json.is_file():
        try:
            meta = json.loads(current_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if isinstance(meta, dict) and isinstance(meta.get("python"), str) and meta["python"].strip():
            cand = Path(meta["python"].strip())
            if not cand.is_absolute():
                cand = home_dir / cand
            if cand.is_file():
                return cand.resolve()
    return Path(sys.executable).resolve()


def _validate_gardens_outside_home(home_dir: Path, gardens_dir: Path) -> None:
    home_res = home_dir.resolve()
    gardens_res = gardens_dir.resolve()
    if (
        gardens_res == home_res
        or gardens_res.is_relative_to(home_res)
        or home_res.is_relative_to(gardens_res)
    ):
        raise ValueError(
            f"Gardens directory ({gardens_res}) must be outside runtime home ({home_res})."
        )


def write_installation_records(
    home: str | Path,
    *,
    gardens_root: str | Path,
    python: str | Path | None = None,
    package_root: str | Path | None = None,
    site_packages: str | Path | None = None,
    launcher: str | Path | None = None,
    version: str | None = None,
    distribution_mode: str = "offline_bundle",
    grasshopper_dir: str | Path | None = None,
    assets: list[dict[str, Any]] | None = None,
    state_path: str | Path | None = None,
    mirror_user_record: bool = True,
) -> dict[str, Any]:
    """Write schema_version=1 installation.json to <home>/config and user profile."""
    home_dir = Path(home).expanduser().resolve()
    gardens_dir = Path(gardens_root).expanduser().resolve()
    _validate_gardens_outside_home(home_dir, gardens_dir)
    gardens_dir.mkdir(parents=True, exist_ok=True)

    sp_dir = Path(site_packages).expanduser().resolve() if site_packages is not None else None
    py_exe = _resolve_target_python_for_record(home_dir, python)
    pkg_root = (
        Path(package_root).expanduser().resolve()
        if package_root is not None
        else _resolve_package_root(sp_dir)
    )
    launcher_path = (
        Path(launcher).expanduser().resolve()
        if launcher is not None
        else (home_dir / "bin" / _exe_name("lbt-mcp")).resolve()
    )

    home_state = home_installation_path(home_dir)
    user_state = user_installation_path()
    prior: dict[str, Any] = {}
    for probe in (home_state, user_state, Path(state_path).expanduser().resolve() if state_path else None):
        if probe and probe.is_file():
            try:
                loaded = read_installation(str(probe))
                if loaded:
                    prior = loaded
                    break
            except Exception:
                pass

    installed_packs = [
        {"name": p["name"], "version": p["version"], "platform": p["platform"]}
        for p in list_packs(home_dir)
    ]
    gh_val = str(Path(grasshopper_dir).expanduser().resolve()) if grasshopper_dir else prior.get("grasshopper_dir")
    assets_val = assets if assets is not None else prior.get("assets", [])

    record: dict[str, Any] = {
        "schema_version": 1,
        "version": version or __version__,
        "python": str(py_exe),
        "package_root": str(pkg_root),
        "gardens_root": str(gardens_dir),
        "home": str(home_dir),
        "launcher": str(launcher_path),
        "runtime_config": str(runtime_config_path(home_dir)),
        "distribution_mode": distribution_mode,
        "packs": installed_packs,
        "grasshopper_dir": gh_val,
        "assets": assets_val,
    }

    written_paths: list[Path] = []
    targets = [home_state]
    if mirror_user_record:
        targets.append(user_state)
    if state_path is not None:
        targets.append(Path(state_path).expanduser().resolve())
    seen: set[Path] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        atomic_write_json(target, record)
        written_paths.append(target)

    return {
        "record": record,
        "written_paths": [str(p) for p in written_paths],
    }


def _refresh_installation_packs(home_dir: Path) -> None:
    installed_packs = [
        {"name": p["name"], "version": p["version"], "platform": p["platform"]}
        for p in list_packs(home_dir)
    ]
    candidates = [home_installation_path(home_dir), user_installation_path()]
    explicit = os.environ.get("LADYBUG_TOOLS_MCP_INSTALLATION")
    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            rec = read_installation(str(path))
        except Exception:
            continue
        if not rec:
            continue
        rec_home = rec.get("home")
        if rec_home and Path(rec_home).expanduser().resolve() != home_dir.resolve():
            continue
        rec["packs"] = installed_packs
        atomic_write_json(path, rec)


def _lexical_rel_pack_path(raw: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError(f"Invalid pack relative path: {raw!r}")
    if raw.startswith(("/", "\\")) or ":" in raw:
        raise ValueError(f"Absolute or drive-qualified pack path is forbidden: {raw!r}")
    normalized = raw.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Path traversal or malformed pack path is forbidden: {raw!r}")
    return pure


def _ensure_safe_pack_dest(
    home_res: Path,
    pure: PurePosixPath,
    dest: Path,
    checked_dirs: set[Path] | None = None,
) -> None:
    if dest == home_res or not dest.is_relative_to(home_res):
        raise ValueError(f"Pack path escapes runtime home: {pure.as_posix()!r}")
    cursor = home_res
    for part in pure.parts[:-1]:
        cursor = cursor / part
        if checked_dirs is not None and cursor in checked_dirs:
            continue
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise ValueError(f"Refusing to extract pack through symlink directory: {cursor}")
        if cursor.exists() and not cursor.resolve().is_relative_to(home_res):
            raise ValueError(f"Pack path escapes runtime home via link directory: {cursor}")
        if checked_dirs is not None:
            checked_dirs.add(cursor)
    if dest.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink file: {dest}")


def _validate_rel_pack_path(raw: str, home: Path) -> tuple[str, Path]:
    pure = _lexical_rel_pack_path(raw)
    home_res = home.resolve()
    dest = home_res.joinpath(*pure.parts).resolve()
    _ensure_safe_pack_dest(home_res, pure, dest)
    return pure.as_posix(), dest


def _sha256_file(path: Path) -> str:
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _installed_openstudio_version(home: Path) -> str | None:
    cfg = read_runtime_config(home)
    os_path = resolve_runtime_value(home, cfg.get("openstudio_path"))
    if os_path:
        os_dir = Path(os_path)
        os_root = os_dir.parent if os_dir.name.lower() == "bin" else os_dir
        match = re.search(r"(\d+\.\d+\.\d+)", os_root.name)
        if match:
            return match.group(1)
        os_exe = os_dir / _exe_name("openstudio")
        if os_exe.is_file():
            try:
                proc = subprocess.run(
                    [str(os_exe), "--version"],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if proc.returncode == 0:
                    m = re.search(r"(\d+\.\d+\.\d+)", proc.stdout)
                    if m:
                        return m.group(1)
            except (OSError, subprocess.SubprocessError):
                pass
    try:
        from garden.ladybug_tools_config import REQUIRED_RUNTIME_VERSIONS

        return REQUIRED_RUNTIME_VERSIONS.get("openstudio")
    except Exception:
        return "3.11.0"


def _versions_compatible(installed: str | None, expected: Any) -> bool:
    if expected is None:
        return True
    if not installed:
        return False
    allowed = expected if isinstance(expected, list) else [expected]
    inst_parts = tuple(int(x) for x in re.findall(r"\d+", installed)[:3])
    if not inst_parts:
        return False
    for item in allowed:
        if not isinstance(item, str) or not item.strip():
            continue
        exp_parts = tuple(int(x) for x in re.findall(r"\d+", item)[:3])
        if exp_parts and inst_parts[: len(exp_parts)] == exp_parts:
            return True
    return False


def _commit_pack_staging_tree(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    with os.scandir(src_dir) as it:
        for entry in it:
            src_child = Path(entry.path)
            dst_child = dst_dir / entry.name
            if entry.is_dir(follow_symlinks=False):
                if not dst_child.exists() and not dst_child.is_symlink():
                    try:
                        os.replace(src_child, dst_child)
                        continue
                    except OSError:
                        pass
                if dst_child.is_symlink() or not dst_child.is_dir():
                    raise ValueError(f"Refusing to merge pack directory into non-directory target: {dst_child}")
                _commit_pack_staging_tree(src_child, dst_child)
            else:
                if dst_child.is_symlink():
                    raise ValueError(f"Refusing to overwrite symlink file: {dst_child}")
                os.replace(src_child, dst_child)


def _collect_prune_ancestors(start_dir: Path, home_res: Path, out: set[Path]) -> None:
    runtimes_res = home_res / "runtimes"
    cursor = start_dir
    while cursor != home_res and cursor != runtimes_res and cursor.is_relative_to(home_res):
        if cursor in out:
            break
        out.add(cursor)
        cursor = cursor.parent


def _prune_collected_dirs(dirs: set[Path], home_res: Path) -> None:
    runtimes_res = home_res / "runtimes"
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if d == home_res or d == runtimes_res or not d.is_relative_to(home_res):
            continue
        try:
            d.rmdir()
        except OSError:
            pass


def install_pack(
    pack_file: str | Path,
    home: str | Path | None = None,
    *,
    force: bool = False,
    site_packages: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and install a .lbtpack archive into <home>."""
    home_dir = resolve_home_dir(home)
    home_res = home_dir.resolve()
    archive_path = Path(pack_file).expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Pack archive not found: {archive_path}")

    expected_platform = "win-x64" if os.name == "nt" else ("osx-arm64" if sys.platform == "darwin" else "linux-x64")

    with ZipFile(archive_path, "r") as zf:
        info_by_name = {}
        for info in zf.infolist():
            mode_type = (info.external_attr >> 16) & 0o170000
            if mode_type == 0o120000:
                raise ValueError(f"Symlink entry forbidden inside .lbtpack: {info.filename}")
            if not info.is_dir():
                _lexical_rel_pack_path(info.filename)
                info_by_name[info.filename] = info

        try:
            manifest_raw = zf.read("pack.json")
        except KeyError as exc:
            raise ValueError("Invalid .lbtpack archive: missing pack.json") from exc
        manifest = json.loads(manifest_raw.decode("utf-8"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise ValueError("Unsupported .lbtpack manifest schema_version.")

        name = manifest.get("name")
        version = manifest.get("version")
        platform_val = manifest.get("platform")
        compat_os = manifest.get("compatible_openstudio")
        files = manifest.get("files")
        runtime_updates = manifest.get("runtime_updates") or {}

        if not isinstance(name, str) or not _PACK_NAME_RE.match(name):
            raise ValueError(f"Invalid pack name in pack.json: {name!r}")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Invalid pack version in pack.json.")
        if platform_val != "win-x64" and platform_val != expected_platform:
            raise ValueError(f"Incompatible pack platform {platform_val!r} (expected {expected_platform!r}).")
        if os.name == "nt" and platform_val != "win-x64":
            raise ValueError(f"Incompatible pack platform {platform_val!r} on Windows x64.")
        installed_os = _installed_openstudio_version(home_dir)
        if not _versions_compatible(installed_os, compat_os):
            raise ValueError(
                f"Pack {name!r} requires OpenStudio {compat_os!r}, but installed OpenStudio is {installed_os!r}."
            )
        if not isinstance(files, list) or not files:
            raise ValueError("Invalid or empty files list in pack.json.")
        if not isinstance(runtime_updates, dict):
            raise ValueError("Invalid runtime_updates in pack.json.")

        receipt_file = packs_dir(home_dir) / f"{name}.json"
        prior_owned: set[str] = set()
        if receipt_file.is_file():
            if not force:
                raise FileExistsError(f"Pack {name!r} is already installed. Use --force to reinstall.")
            prior_receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            prior_owned = {
                entry["path"]
                for entry in (prior_receipt.get("files") or [])
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }

        other_owned: set[str] = set()
        if packs_dir(home_dir).is_dir():
            for other_file in packs_dir(home_dir).glob("*.json"):
                if other_file.stem == name:
                    continue
                other = json.loads(other_file.read_text(encoding="utf-8"))
                for entry in other.get("files") or []:
                    if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                        other_owned.add(entry["path"])

        planned_entries: list[tuple[str, PurePosixPath, Any, str]] = []
        seen_dests: set[str] = set()
        checked_dirs: set[Path] = set()

        for entry in files:
            if not isinstance(entry, dict):
                raise ValueError("Invalid file entry in pack.json.")
            raw_path = entry.get("path")
            expected_sha = entry.get("sha256")
            if not isinstance(raw_path, str) or not isinstance(expected_sha, str) or not _HEX_SHA256_RE.match(expected_sha.lower()):
                raise ValueError(f"Invalid path or sha256 in pack.json entry: {entry!r}")
            pure = _lexical_rel_pack_path(raw_path)
            rel_posix = pure.as_posix()
            if rel_posix in seen_dests:
                raise ValueError(f"Duplicate pack destination path: {rel_posix}")
            seen_dests.add(rel_posix)
            dest = home_res.joinpath(*pure.parts)
            _ensure_safe_pack_dest(home_res, pure, dest, checked_dirs)
            if rel_posix in other_owned:
                raise ValueError(f"Pack file conflicts with another installed pack: {rel_posix}")
            if dest.exists() and rel_posix not in prior_owned and not force:
                raise FileExistsError(f"Destination file already exists: {dest}. Use --force to overwrite.")

            archive_rel = entry.get("archive_path")
            if archive_rel is None:
                archive_rel = f"files/{rel_posix}" if f"files/{rel_posix}" in info_by_name else rel_posix
            if not isinstance(archive_rel, str) or archive_rel not in info_by_name:
                raise ValueError(f"Pack archive missing declared member: {archive_rel!r}")
            _lexical_rel_pack_path(archive_rel)
            planned_entries.append((rel_posix, pure, info_by_name[archive_rel], expected_sha.lower()))

        home_res.mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(dir=home_res, prefix=f".pack-stage-{name}-"))
        receipt_files: list[dict[str, str]] = []
        created_stage_dirs: set[Path] = set()
        try:
            # Stream once into staging inside <home> while verifying every SHA-256 before moving anything into <home>.
            for rel_posix, pure, zip_info, expected_sha in planned_entries:
                stage_file = staging_root.joinpath(*pure.parts)
                stage_parent = stage_file.parent
                if stage_parent not in created_stage_dirs:
                    stage_parent.mkdir(parents=True, exist_ok=True)
                    created_stage_dirs.add(stage_parent)
                hasher = hashlib.sha256()
                with zf.open(zip_info, "r") as src, open(stage_file, "wb") as dst:
                    while chunk := src.read(262144):
                        hasher.update(chunk)
                        dst.write(chunk)
                actual_sha = hasher.hexdigest()
                if actual_sha != expected_sha:
                    raise ValueError(
                        f"SHA-256 verification failed for {rel_posix}: expected {expected_sha}, got {actual_sha}"
                    )
                receipt_files.append({"path": rel_posix, "sha256": actual_sha})

            # All files verified before committing anything to <home>.
            _commit_pack_staging_tree(staging_root, home_res)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    # Remove stale files owned by prior version of the same pack if reinstalling with --force.
    stale_rels = prior_owned - seen_dests
    if stale_rels:
        stale_dirs: set[Path] = set()
        for stale_rel in stale_rels:
            stale_pure = _lexical_rel_pack_path(stale_rel)
            stale_dest = home_res.joinpath(*stale_pure.parts)
            if stale_dest.is_file() and not stale_dest.is_symlink():
                stale_dest.unlink()
                _collect_prune_ancestors(stale_dest.parent, home_res, stale_dirs)
        _prune_collected_dirs(stale_dirs, home_res)

    runtime_cfg = read_runtime_config(home_dir)
    previous_values: dict[str, Any] = {}
    applied_updates: dict[str, Any] = {}
    for key, val in runtime_updates.items():
        if key not in RUNTIME_CONFIG_KEYS:
            raise ValueError(f"Pack {name!r} specifies unsupported runtime key: {key}")
        previous_values[key] = runtime_cfg.get(key)
        runtime_cfg[key] = val
        applied_updates[key] = val

    if not applied_updates and name == "urbanopt":
        discovered_defaults = default_runtime_config(home_dir)
        if discovered_defaults.get("urbanopt_cli_path"):
            previous_values["urbanopt_cli_path"] = runtime_cfg.get("urbanopt_cli_path")
            runtime_cfg["urbanopt_cli_path"] = discovered_defaults["urbanopt_cli_path"]
            applied_updates["urbanopt_cli_path"] = discovered_defaults["urbanopt_cli_path"]

    write_runtime_config(runtime_cfg, home_dir)

    receipt = {
        "schema_version": 1,
        "name": name,
        "version": version,
        "platform": platform_val,
        "compatible_openstudio": compat_os,
        "installed_at": datetime.now(UTC).isoformat(),
        "source_archive": archive_path.name,
        "source_sha256": _sha256_file(archive_path),
        "runtime_updates": applied_updates,
        "previous_runtime_values": previous_values,
        "files": receipt_files,
    }
    atomic_write_json(receipt_file, receipt)

    sync_result = sync_sdk_configs(home_dir, site_packages=site_packages)
    _refresh_installation_packs(home_dir)
    return {
        "status": "installed",
        "name": name,
        "version": version,
        "platform": platform_val,
        "home": str(home_dir),
        "file_count": len(receipt_files),
        "receipt": str(receipt_file),
        "runtime_updates": applied_updates,
        "sync": sync_result,
    }


def list_packs(home: str | Path | None = None) -> list[dict[str, Any]]:
    """List installed .lbtpack receipts in <home>/config/packs."""
    home_dir = resolve_home_dir(home)
    p_dir = packs_dir(home_dir)
    if not p_dir.is_dir():
        return []
    packs: list[dict[str, Any]] = []
    for receipt_path in sorted(p_dir.glob("*.json")):
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        packs.append(
            {
                "name": data.get("name") or receipt_path.stem,
                "version": data.get("version"),
                "platform": data.get("platform"),
                "compatible_openstudio": data.get("compatible_openstudio"),
                "installed_at": data.get("installed_at"),
                "file_count": len(data.get("files") or []),
                "runtime_updates": data.get("runtime_updates") or {},
                "receipt": str(receipt_path),
            }
        )
    return packs


def remove_pack(
    name: str,
    home: str | Path | None = None,
    *,
    site_packages: str | Path | None = None,
) -> dict[str, Any]:
    """Remove an installed pack's owned files, clear its runtime entries, and re-sync SDK configs."""
    if not _PACK_NAME_RE.match(name):
        raise ValueError(f"Invalid pack name: {name!r}")
    home_dir = resolve_home_dir(home)
    home_res = home_dir.resolve()
    receipt_file = packs_dir(home_dir) / f"{name}.json"
    if not receipt_file.is_file():
        raise FileNotFoundError(f"Pack is not installed: {name}")

    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    removed_files: list[str] = []
    candidate_dirs: set[Path] = set()
    checked_dirs: set[Path] = set()
    for entry in receipt.get("files") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        pure = _lexical_rel_pack_path(entry["path"])
        dest = home_res.joinpath(*pure.parts)
        _ensure_safe_pack_dest(home_res, pure, dest, checked_dirs)
        if dest.is_file() and not dest.is_symlink():
            dest.unlink()
            removed_files.append(pure.as_posix())
            _collect_prune_ancestors(dest.parent, home_res, candidate_dirs)
    _prune_collected_dirs(candidate_dirs, home_res)

    runtime_cfg = read_runtime_config(home_dir)
    prev_vals = receipt.get("previous_runtime_values") or {}
    runtime_updates = receipt.get("runtime_updates") or {}
    for key in runtime_updates:
        if key in RUNTIME_CONFIG_KEYS:
            prev = prev_vals.get(key)
            runtime_cfg[key] = prev if isinstance(prev, (str, list)) else ""
    if name == "urbanopt" and "urbanopt_cli_path" not in runtime_updates:
        runtime_cfg["urbanopt_cli_path"] = ""

    receipt_file.unlink(missing_ok=True)
    # Recompute default for urbanopt_cli_path in case files are gone so default doesn't retain it.
    if name == "urbanopt":
        runtime_cfg["urbanopt_cli_path"] = ""
    write_runtime_config(runtime_cfg, home_dir)

    sync_result = sync_sdk_configs(home_dir, site_packages=site_packages)
    _refresh_installation_packs(home_dir)
    return {
        "status": "removed",
        "name": name,
        "home": str(home_dir),
        "removed_count": len(removed_files),
        "sync": sync_result,
    }


def _find_bundled_licenses(home_dir: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    candidates: list[tuple[Path, Path]] = [
        (home_dir / "LICENSE", home_dir / "licenses" / "THIRD_PARTY_NOTICES.md"),
        (repo_root / "LICENSE", repo_root / "licenses" / "THIRD_PARTY_NOTICES.md"),
    ]
    for dist_name in ("lbt-mcp", "lbt_mcp"):
        try:
            dist = importlib.metadata.distribution(dist_name)
            dist_path = getattr(dist, "_path", None)
            if dist_path:
                lic_dir = Path(dist_path) / "licenses"
                candidates.append((lic_dir / "LICENSE", lic_dir / "licenses" / "THIRD_PARTY_NOTICES.md"))
                candidates.append((lic_dir / "LICENSE", lic_dir / "THIRD_PARTY_NOTICES.md"))
        except importlib.metadata.PackageNotFoundError:
            continue

    for lic_file, notices_file in candidates:
        if lic_file.is_file() and notices_file.is_file():
            return {
                "ok": True,
                "license_path": str(lic_file),
                "notices_path": str(notices_file),
            }
    return {
        "ok": False,
        "license_path": str(home_dir / "LICENSE") if (home_dir / "LICENSE").is_file() else None,
        "notices_path": (
            str(home_dir / "licenses" / "THIRD_PARTY_NOTICES.md")
            if (home_dir / "licenses" / "THIRD_PARTY_NOTICES.md").is_file()
            else None
        ),
    }


def _probe_command(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: float = 15.0,
    allow_exit_codes: tuple[int, ...] = (0,),
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        return {
            "ok": proc.returncode in allow_exit_codes and bool(combined),
            "command": cmd,
            "returncode": proc.returncode,
            "output": combined[:500],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "ok": False,
            "command": cmd,
            "error": str(exc),
        }


def _run_smoke_probes(
    *,
    home_dir: Path,
    engines: dict[str, dict[str, Any]],
    rune_bin: Path | None,
    urbanopt_installed: bool,
) -> dict[str, Any]:
    probes: dict[str, Any] = {}

    os_exe = (engines.get("openstudio") or {}).get("exe")
    if isinstance(os_exe, str) and Path(os_exe).is_file():
        probes["openstudio"] = _probe_command([os_exe, "--version"])
    else:
        probes["openstudio"] = {"ok": False, "error": "openstudio executable not found"}

    ep_exe = (engines.get("energyplus") or {}).get("exe")
    if isinstance(ep_exe, str) and Path(ep_exe).is_file():
        probes["energyplus"] = _probe_command([ep_exe, "--version"])
    else:
        probes["energyplus"] = {"ok": False, "error": "energyplus executable not found"}

    rad_bin = (engines.get("radiance") or {}).get("bin_path")
    if isinstance(rad_bin, str) and Path(rad_bin).is_dir():
        rtrace = Path(rad_bin) / _exe_name("rtrace")
        if rtrace.is_file():
            probes["rtrace"] = _probe_command([str(rtrace), "-version"])
        else:
            probes["rtrace"] = {"ok": False, "error": f"rtrace missing in {rad_bin}"}

        evalglare = Path(rad_bin) / _exe_name("evalglare")
        if evalglare.is_file():
            ev_res = _probe_command([str(evalglare), "-version"], allow_exit_codes=(0, 1))
            if "usage:" in (ev_res.get("output") or "").lower():
                ev_v = _probe_command([str(evalglare), "-v"], allow_exit_codes=(0, 1))
                if "evalglare" in (ev_v.get("output") or "").lower():
                    ev_res["version_output"] = ev_v.get("output")
                    ev_res["ok"] = True
            elif "evalglare" not in (ev_res.get("output") or "").lower():
                ev_res["ok"] = False
            probes["evalglare"] = ev_res
        else:
            probes["evalglare"] = {"ok": False, "error": f"evalglare missing in {rad_bin}"}
    else:
        probes["rtrace"] = {"ok": False, "error": "radiance bin_path not found"}
        probes["evalglare"] = {"ok": False, "error": "radiance bin_path not found"}

    try:
        from garden.ironbug.client import IronbugBridgeClient
        from garden.ironbug.runtime import resolve_runtime_paths

        ib_paths = resolve_runtime_paths(require_openstudio=True)
        ib_env = IronbugBridgeClient(ib_paths)._build_env()
        if ib_paths.is_self_contained and ib_paths.bridge_exe is not None:
            cmd = [str(ib_paths.bridge_exe), "--ironbug-dir", str(ib_paths.ironbug_dir), "--command", "health"]
        else:
            assert ib_paths.dotnet_exe is not None
            cmd = [ib_paths.dotnet_exe, "--roll-forward", "Major", str(ib_paths.bridge_dll), "--ironbug-dir", str(ib_paths.ironbug_dir), "--command", "health"]
        if ib_paths.openstudio_csharp_dir:
            cmd.extend(["--openstudio-csharp-dir", str(ib_paths.openstudio_csharp_dir)])
        ib_probe = _probe_command(cmd, env=ib_env, timeout=20.0)
        if ib_probe.get("ok"):
            first_line = (ib_probe.get("output") or "").splitlines()[0]
            try:
                parsed = json.loads(first_line)
                ib_probe["ok"] = bool(parsed.get("ok") and (parsed.get("result") or {}).get("ok"))
                ib_probe["self_contained"] = ib_paths.is_self_contained
            except (ValueError, AttributeError):
                ib_probe["ok"] = False
        probes["ironbug_bridge"] = ib_probe
    except Exception as exc:
        probes["ironbug_bridge"] = {"ok": False, "error": str(exc)}

    if rune_bin is not None and rune_bin.is_file():
        probes["lbt_rune_viewer"] = _probe_command([str(rune_bin), "--version"])
    else:
        probes["lbt_rune_viewer"] = {"ok": False, "error": "lbt-rune-viewer binary not found"}

    uo_engine = engines.get("urbanopt") or {}
    if urbanopt_installed:
        from garden.ladybug_tools_config import urbanopt_runtime_env
        from garden.urbanopt_cli import _bundle_executable

        bundle_exe = _bundle_executable(uo_engine)
        cli_path = uo_engine.get("path")
        with urbanopt_runtime_env(uo_engine):
            env = os.environ.copy()
            env["PYTHONHOME"] = ""
            probes["urbanopt"] = _probe_command(
                [bundle_exe, "exec", "uo", "--version"],
                env=env,
                cwd=Path(cli_path) if isinstance(cli_path, str) and Path(cli_path).is_dir() else home_dir,
                timeout=25.0,
            )
    else:
        probes["urbanopt"] = {"ok": True, "skipped": True, "reason": "optional urbanopt pack not installed"}

    return probes


def run_doctor(
    home: str | Path | None = None,
    *,
    smoke: bool = False,
    site_packages: str | Path | None = None,
) -> dict[str, Any]:
    """Run comprehensive runtime health checks for Standard or Smoke doctor."""
    home_dir = resolve_home_dir(home)
    is_bundled = (
        home is not None
        or bool(os.environ.get("LADYBUG_TOOLS_MCP_HOME"))
        or runtime_config_path(home_dir).is_file()
        or (home_dir / "app" / "current.json").is_file()
    )
    mode = "offline_bundle" if is_bundled else "plain_venv"

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    # 1. Installation record check
    inst_check: dict[str, Any] = {"ok": True, "mode": mode}
    home_inst = home_installation_path(home_dir)
    user_inst = user_installation_path()
    inst_record: dict[str, Any] = {}
    if is_bundled:
        if home_inst.is_file():
            try:
                inst_record = read_installation(str(home_inst))
                _validate_gardens_outside_home(home_dir, Path(inst_record["gardens_root"]))
                inst_check.update(
                    {
                        "home_record": str(home_inst),
                        "user_record_exists": user_inst.is_file(),
                        "gardens_root": inst_record.get("gardens_root"),
                        "schema_version": inst_record.get("schema_version"),
                    }
                )
            except Exception as exc:
                inst_check["ok"] = False
                inst_check["error"] = str(exc)
                errors.append(f"Installation record invalid: {exc}")
        elif user_inst.is_file():
            try:
                inst_record = read_installation(str(user_inst))
                inst_check.update({"user_record": str(user_inst), "home_record_missing": True})
            except Exception as exc:
                inst_check["ok"] = False
                inst_check["error"] = str(exc)
                errors.append(f"Installation record invalid: {exc}")
        else:
            inst_check["ok"] = False
            inst_check["error"] = f"Missing installation.json under {home_inst}"
            errors.append(inst_check["error"])
    else:
        inst_check["skipped"] = True
        inst_check["reason"] = "No managed runtime home configured."
    checks["installation_record"] = inst_check

    # 2. ASCII / space path safety (note: gardens_root is allowed to contain spaces / non-ASCII!)
    path_safe = is_ascii_space_free(str(home_dir))
    path_check: dict[str, Any] = {
        "ok": True if not is_bundled else path_safe,
        "home": str(home_dir),
        "ascii_space_free": path_safe,
    }
    if is_bundled and not path_safe:
        errors.append(f"Runtime home path contains spaces or non-ASCII characters: {home_dir}")
    checks["path_safety"] = path_check

    # 3. runtime.json vs SDK config.json drift check
    drift: dict[str, Any] = {}
    sync_check: dict[str, Any] = {"ok": True}
    if is_bundled:
        try:
            sp_dir = _resolve_site_packages(home_dir, site_packages)
            raw_cfg = read_runtime_config(home_dir)
            expected = _expected_sdk_configs(home_dir, raw_cfg)
            for pkg, exp_data in expected.items():
                pkg_cfg = sp_dir / pkg / "config.json"
                if not (sp_dir / pkg).is_dir():
                    continue
                if not pkg_cfg.is_file():
                    drift[pkg] = {"missing": str(pkg_cfg)}
                    continue
                actual = json.loads(pkg_cfg.read_text(encoding="utf-8"))
                pkg_diff = {}
                for k, exp_val in exp_data.items():
                    if k.startswith("__"):
                        continue
                    if actual.get(k) != exp_val:
                        pkg_diff[k] = {"expected": exp_val, "actual": actual.get(k)}
                if pkg_diff:
                    drift[pkg] = pkg_diff
            sync_check["site_packages"] = str(sp_dir)
            sync_check["drift"] = drift
            if drift:
                sync_check["ok"] = False
                errors.append("SDK config.json drift detected against runtime.json: " + ", ".join(sorted(drift)))
        except Exception as exc:
            sync_check["ok"] = False
            sync_check["error"] = str(exc)
            errors.append(f"SDK config drift check failed: {exc}")
    else:
        sync_check["skipped"] = True
    checks["sdk_config_sync"] = sync_check

    # 4. get_ladybug_tools_config() engines check (missing optional urbanopt/des_gmt MUST NOT fail Standard doctor!)
    from garden.ladybug_tools_config import get_ladybug_tools_config

    sdk_report = get_ladybug_tools_config()
    sv = sdk_report.get("summary_view") or {}
    engines = sv.get("engines") or {}
    installed_packs = list_packs(home_dir) if is_bundled else []
    urbanopt_pack_installed = any(p.get("name") == "urbanopt" for p in installed_packs) or bool(
        is_bundled and read_runtime_config(home_dir).get("urbanopt_cli_path")
    )

    engine_failures: list[str] = []
    for req_name in REQUIRED_ENGINES:
        eng = engines.get(req_name) or {}
        if req_name == "therm":
            if not eng.get("available"):
                engine_failures.append(req_name)
        elif req_name == "ironbug_console":
            bridge_ready = bool(
                (eng.get("bridge_self_contained") and eng.get("bridge_exe_exists"))
                or (eng.get("dotnet_available") and eng.get("bridge_dll_exists"))
            )
            if not (
                eng.get("ironbug_hvac_dll_exists")
                and eng.get("openstudio_csharp_dll_exists")
                and bridge_ready
                and eng.get("version_status") == "compatible"
                and not eng.get("compatibility_warnings")
            ):
                engine_failures.append(req_name)
        else:
            if (
                not eng.get("path_exists")
                or ("exe_exists" in eng and not eng.get("exe_exists"))
                or ("bin_path_exists" in eng and not eng.get("bin_path_exists"))
                or eng.get("version_status") != "compatible"
            ):
                engine_failures.append(req_name)

    if urbanopt_pack_installed:
        uo_eng = engines.get("urbanopt") or {}
        if not uo_eng.get("available") or uo_eng.get("version_status") != "compatible":
            engine_failures.append("urbanopt")

    optional_absent = [opt for opt in OPTIONAL_ENGINES if not (engines.get(opt) or {}).get("available")]
    if optional_absent:
        warnings.append("Optional runtimes not installed: " + ", ".join(optional_absent))
    if engine_failures:
        errors.append("Required runtime engine check failed: " + ", ".join(engine_failures))

    checks["runtime_engines"] = {
        "ok": not engine_failures,
        "required_failures": engine_failures,
        "optional_not_installed": optional_absent,
        "urbanopt_pack_installed": urbanopt_pack_installed,
        "engines": engines,
    }

    # 5. Bundled licenses check
    lic_check = _find_bundled_licenses(home_dir)
    if not lic_check["ok"]:
        errors.append("Bundled LICENSE or licenses/THIRD_PARTY_NOTICES.md missing.")
    checks["licenses"] = lic_check

    # 6. Bundled lbt-rune-viewer check
    from web_view.launcher import discover_rune_viewer_binary

    rune_bin = discover_rune_viewer_binary()
    rune_ok = bool(rune_bin and rune_bin.is_file())
    if not rune_ok:
        errors.append("Bundled lbt-rune-viewer binary not found.")
    checks["rune_viewer"] = {"ok": rune_ok, "path": str(rune_bin) if rune_bin else None}

    # 7. Bundled pyhygrothermfem_fairyfly check
    therm_eng = engines.get("therm") or {}
    htfem_ok = bool(therm_eng.get("available"))
    if not htfem_ok:
        errors.append(
            f"Bundled pyhygrothermfem_fairyfly unavailable ({therm_eng.get('disabled_reason') or 'missing'})."
        )
    checks["pyhygrothermfem_fairyfly"] = {
        "ok": htfem_ok,
        "version": therm_eng.get("version"),
        "kernel_commit": therm_eng.get("kernel_commit"),
        "packages": therm_eng.get("packages"),
    }

    smoke_probes: dict[str, Any] | None = None
    if smoke:
        smoke_probes = _run_smoke_probes(
            home_dir=home_dir,
            engines=engines,
            rune_bin=rune_bin,
            urbanopt_installed=urbanopt_pack_installed,
        )
        failed_probes = [k for k, v in smoke_probes.items() if not v.get("ok")]
        if failed_probes:
            errors.append("Smoke probe(s) failed: " + ", ".join(failed_probes))

    overall_ok = len(errors) == 0
    return {
        "ok": overall_ok,
        "status": "ok" if overall_ok else "error",
        "mode": mode,
        "home": str(home_dir),
        "version": __version__,
        "smoke": bool(smoke),
        "packs": installed_packs,
        "checks": checks,
        "smoke_probes": smoke_probes,
        "errors": errors,
        "warnings": warnings,
    }
