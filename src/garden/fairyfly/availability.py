"""Fairyfly and bundled pyHygroThermFEM runtime availability helpers."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import platform
from typing import Any


def is_windows_platform() -> bool:
    """Return True when running on Windows."""
    return platform.system().lower() == "windows"


def package_available(module_name: str) -> bool:
    """Return True when a Python module can be imported."""
    return importlib.util.find_spec(module_name) is not None


def fairyfly_tools_enabled() -> bool:
    """Return True when Fairyfly MCP tools should be registered."""
    return package_available("fairyfly") and package_available("fairyfly_next_therm")


def therm_engine_config() -> dict[str, Any]:
    """Return compact bundled pyHygroThermFEM-Fairyfly + Gmsh runtime configuration."""
    packages = {
        "fairyfly": package_available("fairyfly"),
        "fairyfly_next_therm": package_available("fairyfly_next_therm"),
        "fairyfly_hygrotherm": package_available("fairyfly_hygrotherm"),
        "pyhygrothermfem_fairyfly": package_available("pyhygrothermfem_fairyfly"),
        "libraryfemtherm": package_available("pylibraryfemtherm"),
        "gmsh": package_available("gmsh"),
    }
    path: str | None = None
    exe: str | None = None
    version: str | None = None
    contract_version: str | None = None
    kernel_commit: str | None = None
    native_available = False
    disabled_reason: str | None = None

    if not packages["fairyfly"]:
        disabled_reason = "fairyfly_not_installed"
    elif not packages["fairyfly_next_therm"]:
        disabled_reason = "fairyfly_next_therm_not_installed"
    elif not packages["pyhygrothermfem_fairyfly"]:
        disabled_reason = "pyhygrothermfem_fairyfly_not_installed"
    elif not packages["libraryfemtherm"]:
        disabled_reason = "libraryfemtherm_not_installed"
    elif not packages["gmsh"]:
        disabled_reason = "gmsh_not_installed"
    else:
        try:
            pkg = importlib.import_module("pyhygrothermfem_fairyfly")
            pkg_dir = Path(pkg.__file__).resolve().parent
            path = str(pkg_dir)
            native = importlib.import_module("pyhygrothermfem_fairyfly._native")
            native_path = Path(native.__file__).resolve()
            exe = str(native_path)
            native_available = native_path.is_file()
            build_source = importlib.import_module("pyhygrothermfem_fairyfly._build_source")
            kernel_commit = build_source.verified_kernel_commit()
            run_mod = importlib.import_module("pyhygrothermfem_fairyfly.run")
            version = str(getattr(run_mod, "SOLVER_VERSION", "")) or None
            contract_version = str(getattr(run_mod, "CONTRACT_VERSION", "")) or None
        except Exception as exc:
            disabled_reason = f"hygrothermfem_error:{type(exc).__name__}"

    available = bool(
        all(packages.values())
        and native_available
        and kernel_commit
        and disabled_reason is None
    )
    if not available and disabled_reason is None:
        disabled_reason = "hygrothermfem_native_missing"

    return {
        "name": "therm",
        "kind": "hygrothermfem_runtime",
        "engine": "pyHygroThermFEM-Fairyfly",
        "available": available,
        "enabled": available,
        "platform_supported": True,
        "path": path,
        "path_exists": bool(path and Path(path).is_dir()),
        "exe": exe,
        "exe_exists": native_available,
        "version": version,
        "contract_version": contract_version,
        "kernel_commit": kernel_commit,
        "mesher": "gmsh",
        "mesher_available": packages["gmsh"],
        "packages": packages,
        "disabled_reason": None if available else disabled_reason,
    }
