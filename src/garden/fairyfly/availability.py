"""Fairyfly and THERM runtime availability helpers."""

from __future__ import annotations

import importlib.util
import platform
from pathlib import Path
from typing import Any


def is_windows_platform() -> bool:
    """Return True when the current platform can run THERM."""
    return platform.system().lower() == "windows"


def package_available(module_name: str) -> bool:
    """Return True when a Python module can be imported."""
    return importlib.util.find_spec(module_name) is not None


def fairyfly_tools_enabled() -> bool:
    """Return True when Fairyfly MCP tools should be registered."""
    return (
        is_windows_platform()
        and package_available("fairyfly")
        and package_available("fairyfly_therm")
    )


def therm_engine_config() -> dict[str, Any]:
    """Return compact THERM runtime configuration."""
    if not is_windows_platform():
        return {
            "name": "therm",
            "kind": "therm_runtime",
            "available": False,
            "enabled": False,
            "platform_supported": False,
            "path": None,
            "path_exists": False,
            "exe": None,
            "exe_exists": False,
            "version": None,
            "packages": {
                "fairyfly": package_available("fairyfly"),
                "fairyfly_therm": package_available("fairyfly_therm"),
            },
            "disabled_reason": "therm_windows_only",
        }

    packages = {
        "fairyfly": package_available("fairyfly"),
        "fairyfly_therm": package_available("fairyfly_therm"),
    }
    path = None
    exe = None
    version = None
    disabled_reason = None
    if packages["fairyfly_therm"]:
        try:
            from fairyfly_therm.config import folders as therm_folders

            path = getattr(therm_folders, "therm_path", None)
            exe = getattr(therm_folders, "therm_exe", None)
            version = getattr(therm_folders, "therm_version_str", None)
        except Exception as exc:  # pragma: no cover - depends on local SDK config
            disabled_reason = f"therm_config_error:{type(exc).__name__}"
    else:
        disabled_reason = "fairyfly_therm_not_installed"

    path_exists = bool(path and Path(path).expanduser().is_dir())
    exe_exists = bool(exe and Path(exe).expanduser().is_file())
    available = bool(
        is_windows_platform()
        and packages["fairyfly"]
        and packages["fairyfly_therm"]
        and exe_exists
    )
    if disabled_reason is None and not packages["fairyfly"]:
        disabled_reason = "fairyfly_not_installed"
    if disabled_reason is None and not exe_exists:
        disabled_reason = "therm_exe_missing"

    return {
        "name": "therm",
        "kind": "therm_runtime",
        "available": available,
        "enabled": available,
        "platform_supported": True,
        "path": path,
        "path_exists": path_exists,
        "exe": exe,
        "exe_exists": exe_exists,
        "version": version,
        "packages": packages,
        "disabled_reason": None if available else disabled_reason,
    }
