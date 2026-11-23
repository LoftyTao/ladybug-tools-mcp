"""External Ironbug, OpenStudio C#, and .NET runtime resolution."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from honeybee_energy.config import folders as energy_folders


class IronbugRuntimeUnavailable(RuntimeError):
    """Raised when required external Ironbug / .NET / OpenStudio binaries are missing."""

    def __init__(self, message: str, *, missing: list[str], details: dict[str, Any]) -> None:
        super().__init__(message)
        self.missing = missing
        self.details = details


@dataclass(frozen=True, slots=True)
class IronbugRuntimePaths:
    ironbug_dir: Path
    ironbug_exe: Path | None
    openstudio_csharp_dir: Path | None
    dotnet_exe: str
    bridge_dll: Path


def _repo_or_packaged_bridge_dll() -> Path | None:
    package_root = Path(__file__).resolve().parents[2]
    candidates = [
        package_root / "ladybug_tools_mcp" / "resources" / "ironbug_bridge" / "IronbugBridge.dll",
        package_root / "ironbug_bridge" / "bin" / "Release" / "net8.0" / "IronbugBridge.dll",
        package_root / "ironbug_bridge" / "bin" / "Debug" / "net8.0" / "IronbugBridge.dll",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_ironbug_dir() -> Path | None:
    env_dir = os.environ.get("LADYBUG_TOOLS_IRONBUG_PATH")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if (candidate / "Ironbug.HVAC.dll").is_file():
            return candidate.resolve()

    sdk_dir = getattr(energy_folders, "ironbug_path", None)
    if sdk_dir:
        candidate = Path(sdk_dir).expanduser()
        if (candidate / "Ironbug.HVAC.dll").is_file():
            return candidate.resolve()

    sdk_exe = getattr(energy_folders, "ironbug_exe", None)
    if sdk_exe:
        parent = Path(sdk_exe).expanduser().parent
        if (parent / "Ironbug.HVAC.dll").is_file():
            return parent.resolve()

    for root in (
        Path("C:/Program Files/ladybug_tools/grasshopper/ironbug"),
        Path.home() / "ladybug_tools" / "grasshopper" / "ironbug",
        Path("/usr/local/ladybug_tools/grasshopper/ironbug"),
        Path("/Applications/ladybug_tools/grasshopper/ironbug"),
    ):
        if (root / "Ironbug.HVAC.dll").is_file():
            return root.resolve()
    return None


def resolve_openstudio_csharp_dir(ironbug_dir: Path | None) -> Path | None:
    env_dir = os.environ.get("LADYBUG_TOOLS_OPENSTUDIO_CSHARP_PATH")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if (candidate / "OpenStudio.dll").is_file():
            return candidate.resolve()

    sdk_cs = getattr(energy_folders, "openstudio_csharp_path", None)
    if sdk_cs:
        candidate = Path(sdk_cs).expanduser()
        if (candidate / "OpenStudio.dll").is_file():
            return candidate.resolve()

    os_path = getattr(energy_folders, "openstudio_path", None)
    if os_path:
        os_root = Path(os_path).expanduser().parent
        for rel in (Path("CSharp") / "openstudio", Path("csharp") / "openstudio", Path("CSharp")):
            candidate = os_root / rel
            if (candidate / "OpenStudio.dll").is_file():
                return candidate.resolve()

    if ironbug_dir and (ironbug_dir / "OpenStudio.dll").is_file():
        return ironbug_dir.resolve()
    return None


def resolve_ironbug_console_exe(ironbug_dir: Path | None) -> Path | None:
    sdk_exe = getattr(energy_folders, "ironbug_exe", None)
    if sdk_exe:
        p = Path(sdk_exe).expanduser()
        if p.is_file():
            return p.resolve()
    if ironbug_dir:
        exe_name = "Ironbug.Console.exe" if os.name == "nt" else "Ironbug.Console"
        p = ironbug_dir / exe_name
        if p.is_file():
            return p.resolve()
    return None


def resolve_runtime_paths(
    *,
    require_console_exe: bool = False,
    require_openstudio: bool = True,
) -> IronbugRuntimePaths:
    ironbug_dir = resolve_ironbug_dir()
    ironbug_exe = resolve_ironbug_console_exe(ironbug_dir)
    openstudio_csharp_dir = resolve_openstudio_csharp_dir(ironbug_dir)
    dotnet_exe = shutil.which("dotnet")
    bridge_dll = _repo_or_packaged_bridge_dll()

    missing: list[str] = []
    if ironbug_dir is None:
        missing.append("Ironbug.HVAC.dll (install Ladybug Tools / Ironbug)")
    if require_console_exe and ironbug_exe is None:
        missing.append("Ironbug.Console executable")
    if require_openstudio and openstudio_csharp_dir is None:
        missing.append("OpenStudio.dll (OpenStudio CSharp bindings)")
    if not dotnet_exe:
        missing.append("dotnet (.NET 8+ runtime)")
    if bridge_dll is None:
        missing.append("IronbugBridge.dll (build src/ironbug_bridge or reinstall lbt-mcp)")

    if missing:
        raise IronbugRuntimeUnavailable(
            "External Ironbug runtime requirements are missing: "
            + "; ".join(missing)
            + ". Install Ladybug Tools (with Ironbug and OpenStudio C# bindings) and .NET 8+, "
            "or inspect LB_Get_Runtime_Config for configured paths.",
            missing=missing,
            details={
                "ironbug_dir": str(ironbug_dir) if ironbug_dir else None,
                "ironbug_exe": str(ironbug_exe) if ironbug_exe else None,
                "openstudio_csharp_dir": str(openstudio_csharp_dir) if openstudio_csharp_dir else None,
                "dotnet_exe": dotnet_exe,
                "bridge_dll": str(bridge_dll) if bridge_dll else None,
            },
        )

    assert ironbug_dir is not None and dotnet_exe is not None and bridge_dll is not None
    return IronbugRuntimePaths(
        ironbug_dir=ironbug_dir,
        ironbug_exe=ironbug_exe,
        openstudio_csharp_dir=openstudio_csharp_dir,
        dotnet_exe=dotnet_exe,
        bridge_dll=bridge_dll,
    )
