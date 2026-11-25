"""External Ironbug, OpenStudio C#, and .NET runtime resolution."""

from __future__ import annotations

import os
import re
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from honeybee_energy.config import folders as energy_folders

KNOWN_IRONBUG_OPENSTUDIO_VERSIONS: tuple[tuple[tuple[int, ...], str], ...] = (
    ((1, 26), "3.11.0"),
)

_OS_VERSION_BLOCK_RE = re.compile(
    r"OS:Version\s*,[^;]*?(\d+\.\d+\.\d+(?:\.\d+)?)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_UNSET: Any = object()


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


def _parse_version_tuple(value: Any, *, max_parts: int = 3) -> tuple[int, ...] | None:
    if not value:
        return None
    text = str(value).strip().split("+", 1)[0].split("-", 1)[0]
    match = re.search(r"(\d+(?:\.\d+)+|\d+)", text)
    if not match:
        return None
    parts = [int(item) for item in match.group(1).split(".") if item]
    return tuple(parts[:max_parts]) if parts else None


def _short_version(value: Any, *, parts: int = 3) -> str | None:
    parsed = _parse_version_tuple(value, max_parts=parts)
    if not parsed:
        return None
    return ".".join(str(x) for x in parsed)


def read_pe_file_version(path: Path | None) -> str | None:
    """Read ProductVersion or FileVersion from a Windows PE binary without spawning a process."""
    if path is None or not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    utf16 = data.decode("utf-16-le", errors="ignore")
    for key in ("ProductVersion", "FileVersion"):
        match = re.search(rf"{key}\x00+([0-9]+(?:\.[0-9]+)+)", utf16)
        if match:
            return match.group(1)
    return None


def read_dotnet_assembly_refs(path: Path | None) -> dict[str, str]:
    """Read referenced .NET assembly versions from a managed DLL's AssemblyRef table."""
    if path is None or not path.is_file():
        return {}
    try:
        data = path.read_bytes()
        if len(data) < 0x40 or data[:2] != b"MZ":
            return {}
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off : pe_off + 4] != b"PE\x00\x00":
            return {}
        coff_off = pe_off + 4
        num_sections = struct.unpack_from("<H", data, coff_off + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff_off + 16)[0]
        opt_off = coff_off + 20
        magic = struct.unpack_from("<H", data, opt_off)[0]
        dd_off = opt_off + (96 if magic == 0x10B else 112)
        cli_rva, _ = struct.unpack_from("<II", data, dd_off + 14 * 8)
        if not cli_rva:
            return {}

        sec_off = opt_off + opt_size
        sections: list[tuple[int, int, int]] = []
        for idx in range(num_sections):
            s_off = sec_off + idx * 40
            vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", data, s_off + 8)
            sections.append((vaddr, max(vsize, rsize), rptr))

        def rva_to_off(rva: int) -> int | None:
            for vaddr, span, rptr in sections:
                if vaddr <= rva < vaddr + span:
                    return rptr + (rva - vaddr)
            return None

        cli_off = rva_to_off(cli_rva)
        if cli_off is None:
            return {}
        meta_rva, _ = struct.unpack_from("<II", data, cli_off + 8)
        meta_off = rva_to_off(meta_rva)
        if meta_off is None or data[meta_off : meta_off + 4] != b"BSJB":
            return {}

        ver_len = struct.unpack_from("<I", data, meta_off + 12)[0]
        pos = meta_off + 16 + ver_len + 2
        num_streams = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        streams: dict[str, tuple[int, int]] = {}
        for _ in range(num_streams):
            s_offset, s_size = struct.unpack_from("<II", data, pos)
            pos += 8
            end = data.index(b"\x00", pos)
            name = data[pos:end].decode("ascii", errors="ignore")
            pos = (end + 4) & ~3
            streams[name] = (meta_off + s_offset, s_size)

        if "#~" not in streams or "#Strings" not in streams:
            return {}
        str_off, str_size = streams["#Strings"]
        str_heap = data[str_off : str_off + str_size]

        def get_str(idx: int) -> str:
            end = str_heap.index(b"\x00", idx)
            return str_heap[idx:end].decode("utf-8", errors="ignore")

        tbl_off, _ = streams["#~"]
        heap_sizes = data[tbl_off + 6]
        str_sz = 4 if (heap_sizes & 0x01) else 2
        guid_sz = 4 if (heap_sizes & 0x02) else 2
        blob_sz = 4 if (heap_sizes & 0x04) else 2
        valid_mask = struct.unpack_from("<Q", data, tbl_off + 8)[0]
        cur = tbl_off + 24
        counts: dict[int, int] = {}
        for tid in range(64):
            if valid_mask & (1 << tid):
                counts[tid] = struct.unpack_from("<I", data, cur)[0]
                cur += 4

        def c_sz(tid: int) -> int:
            return 4 if counts.get(tid, 0) >= 65536 else 2

        def coded_sz(tids: list[int], bits: int) -> int:
            mx = max((counts.get(t, 0) for t in tids), default=0)
            return 4 if mx >= (1 << (16 - bits)) else 2

        row_sizes = {
            0x00: 2 + str_sz + 3 * guid_sz,
            0x01: coded_sz([0x00, 0x01, 0x1A, 0x23], 2) + 2 * str_sz,
            0x02: 4 + 2 * str_sz + coded_sz([0x02, 0x01, 0x1B], 2) + c_sz(0x04) + c_sz(0x06),
            0x03: c_sz(0x04),
            0x04: 2 + str_sz + blob_sz,
            0x05: c_sz(0x06),
            0x06: 4 + 2 + 2 + str_sz + blob_sz + c_sz(0x08),
            0x07: c_sz(0x08),
            0x08: 2 + 2 + str_sz,
            0x09: c_sz(0x02) + coded_sz([0x02, 0x01, 0x1B], 2),
            0x0A: coded_sz([0x02, 0x01, 0x1A, 0x06, 0x1B], 3) + str_sz + blob_sz,
            0x0B: 2 + coded_sz([0x04, 0x06, 0x08], 2) + blob_sz,
            0x0C: coded_sz(
                [0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x00, 0x0E, 0x17, 0x14, 0x11, 0x1A, 0x1B, 0x20, 0x23, 0x26, 0x27, 0x2A, 0x2C, 0x2B],
                5,
            )
            + coded_sz([0x06, 0x0A], 3)
            + blob_sz,
            0x0D: coded_sz([0x04, 0x08], 1) + blob_sz,
            0x0E: 2 + coded_sz([0x02, 0x06, 0x20], 2) + blob_sz,
            0x0F: 2 + 4 + c_sz(0x02),
            0x10: 4 + c_sz(0x04),
            0x11: blob_sz,
            0x12: c_sz(0x02) + c_sz(0x14),
            0x13: c_sz(0x14),
            0x14: 2 + str_sz + coded_sz([0x02, 0x01, 0x1B], 2),
            0x15: c_sz(0x02) + c_sz(0x17),
            0x16: c_sz(0x17),
            0x17: 2 + str_sz + blob_sz,
            0x18: 2 + coded_sz([0x06, 0x04], 1) + coded_sz([0x14, 0x17], 1),
            0x19: coded_sz([0x02, 0x01, 0x1B], 2) + coded_sz([0x06, 0x0A], 1) + coded_sz([0x06, 0x0A], 1),
            0x1A: str_sz,
            0x1B: blob_sz,
            0x1C: 2 + coded_sz([0x04, 0x06], 1) + str_sz + c_sz(0x1A),
            0x1D: 4 + c_sz(0x04),
            0x1E: 8,
            0x1F: 4,
            0x20: 4 + 8 + 4 + blob_sz + 2 * str_sz,
            0x21: 4,
            0x22: 4 + 4 + 4,
            0x23: 8 + 4 + blob_sz + 2 * str_sz + blob_sz,
        }
        for tid in range(0x23):
            if tid in counts:
                cur += counts[tid] * row_sizes[tid]

        refs: dict[str, str] = {}
        for _ in range(counts.get(0x23, 0)):
            maj, min_, bld, rev, _flags = struct.unpack_from("<HHHHI", data, cur)
            name_off = cur + 12 + blob_sz
            name_idx = struct.unpack_from("<I" if str_sz == 4 else "<H", data, name_off)[0]
            refs[get_str(name_idx)] = f"{maj}.{min_}.{bld}.{rev}"
            cur += row_sizes[0x23]
        return refs
    except (OSError, struct.error, ValueError, IndexError):
        return {}


def extract_osm_version(osm_text: str | None = None, *, osm_path: Path | None = None) -> str | None:
    """Extract the OS:Version identifier from an OSM payload or file header."""
    text = osm_text
    if text is None and osm_path is not None and osm_path.is_file():
        try:
            with osm_path.open("r", encoding="utf-8", errors="replace") as handle:
                text = handle.read(16384)
        except OSError:
            return None
    if not text:
        return None
    match = _OS_VERSION_BLOCK_RE.search(text[:16384])
    return match.group(1) if match else None


def get_python_openstudio_version() -> str | None:
    """Return the OpenStudio version exposed by Python openstudio bindings if installed."""
    try:
        import openstudio  # type: ignore[import-not-found]

        ver = openstudio.openStudioVersion()
        return str(ver).strip() if ver else None
    except Exception:
        return None


def _known_openstudio_for_ironbug(ironbug_version: str | None) -> str | None:
    parsed = _parse_version_tuple(ironbug_version, max_parts=2)
    if not parsed:
        return None
    for prefix, os_ver in KNOWN_IRONBUG_OPENSTUDIO_VERSIONS:
        if parsed[: len(prefix)] == prefix:
            return os_ver
    return None


def inspect_ironbug_openstudio_compatibility(
    *,
    ironbug_dir: Path | None = None,
    openstudio_csharp_dir: Path | None = None,
    ironbug_version: str | None = None,
    openstudio_cli_version: str | None = None,
    osm_version: str | None = None,
    python_openstudio_version: Any = _UNSET,
) -> dict[str, Any]:
    """Compare Ironbug / OSM / Python OpenStudio versions against local OpenStudio CLI."""
    ib_dir = ironbug_dir if ironbug_dir is not None else resolve_ironbug_dir()
    os_cs_dir = (
        openstudio_csharp_dir
        if openstudio_csharp_dir is not None
        else resolve_openstudio_csharp_dir(ib_dir)
    )

    ib_dll_ver = read_pe_file_version(ib_dir / "Ironbug.HVAC.dll") if ib_dir else None
    ib_exe_ver = (
        read_pe_file_version(resolve_ironbug_console_exe(ib_dir))
        if ib_dir
        else None
    )
    effective_ib_ver = (
        ironbug_version
        or ib_dll_ver
        or ib_exe_ver
        or getattr(energy_folders, "ironbug_version_str", None)
    )

    ib_bundled_os_ver = read_pe_file_version(ib_dir / "OpenStudio.dll") if ib_dir else None
    ib_asm_os_ver = (
        read_dotnet_assembly_refs(ib_dir / "Ironbug.HVAC.dll").get("OpenStudio")
        if ib_dir
        else None
    )
    ib_known_os_ver = _known_openstudio_for_ironbug(effective_ib_ver)

    if ib_bundled_os_ver:
        ironbug_os_ver: str | None = ib_bundled_os_ver
    elif ib_known_os_ver and ib_asm_os_ver:
        k_t = _parse_version_tuple(ib_known_os_ver)
        a_t = _parse_version_tuple(ib_asm_os_ver)
        ironbug_os_ver = ib_known_os_ver if (k_t and a_t and k_t >= a_t) else ib_asm_os_ver
    else:
        ironbug_os_ver = ib_known_os_ver or ib_asm_os_ver

    os_cs_ver = read_pe_file_version(os_cs_dir / "OpenStudio.dll") if os_cs_dir else None
    cli_os_ver = (
        openstudio_cli_version
        if openstudio_cli_version is not None
        else getattr(energy_folders, "openstudio_version_str", None)
    )
    py_os_ver = (
        get_python_openstudio_version()
        if python_openstudio_version is _UNSET
        else python_openstudio_version
    )

    cli_short = _short_version(cli_os_ver)
    cli_tuple = _parse_version_tuple(cli_os_ver)
    cs_short = _short_version(os_cs_ver)
    cs_tuple = _parse_version_tuple(os_cs_ver)
    ib_os_short = _short_version(ironbug_os_ver)
    ib_os_tuple = _parse_version_tuple(ironbug_os_ver)
    osm_short = _short_version(osm_version)
    osm_tuple = _parse_version_tuple(osm_version)
    py_short = _short_version(py_os_ver)
    py_tuple = _parse_version_tuple(py_os_ver)
    ib_ver_short = _short_version(effective_ib_ver, parts=4) or (
        str(effective_ib_ver).strip() if effective_ib_ver else None
    )

    compatibility_warnings: list[dict[str, Any]] = []

    if ib_os_tuple and cli_tuple and ib_os_tuple > cli_tuple:
        compatibility_warnings.append(
            {
                "code": "ironbug_openstudio_version_mismatch",
                "severity": "warning",
                "source": "ironbug",
                "ironbug_version": ib_ver_short,
                "ironbug_openstudio_version": ib_os_short,
                "openstudio_cli_version": cli_short,
                "impact": (
                    "OS:Version / VersionTranslator ahead-of-CLI warning, "
                    "OS:Site:WaterMainsTemperature / OS:Sizing:Zone field parsing errors, "
                    "and ExpandObjects field count mismatches (e.g. Chiller:Electric:EIR)."
                ),
                "message": (
                    f"Ironbug ({ib_ver_short or 'unknown'}) targets/bundles OpenStudio {ib_os_short}, "
                    f"which is newer than local OpenStudio CLI {cli_short} ({ib_os_short} > {cli_short}). "
                    "Generated OSM models may trigger OS:Version ahead-of-version warnings, "
                    "OS:Site:WaterMainsTemperature / OS:Sizing:Zone field errors, and ExpandObjects "
                    "field mismatches (such as Chiller:Electric:EIR)."
                ),
            }
        )

    if cs_tuple and cli_tuple and cs_tuple > cli_tuple:
        compatibility_warnings.append(
            {
                "code": "openstudio_csharp_version_mismatch",
                "severity": "warning",
                "source": "openstudio_csharp",
                "openstudio_csharp_version": cs_short,
                "openstudio_cli_version": cli_short,
                "impact": (
                    "OpenStudio C# bindings may emit OSM schemas newer than the local OpenStudio CLI."
                ),
                "message": (
                    f"OpenStudio C# bindings ({cs_short}) are newer than local OpenStudio CLI "
                    f"{cli_short} ({cs_short} > {cli_short}), which may cause OS:Version and "
                    "ExpandObjects field mismatches during simulation."
                ),
            }
        )

    if osm_tuple and (
        (cli_tuple and osm_tuple > cli_tuple) or (cs_tuple and osm_tuple > cs_tuple)
    ):
        target_label = "OpenStudio CLI" if (cli_tuple and osm_tuple > cli_tuple) else "OpenStudio C#"
        target_ver = cli_short if (cli_tuple and osm_tuple > cli_tuple) else cs_short
        compatibility_warnings.append(
            {
                "code": "osm_openstudio_version_mismatch",
                "severity": "warning",
                "source": "osm",
                "osm_version": osm_short,
                "openstudio_cli_version": cli_short,
                "openstudio_csharp_version": cs_short,
                "impact": (
                    "VersionTranslator ahead-of-version warning, OS:Site:WaterMainsTemperature / "
                    "OS:Sizing:Zone field cutoff errors, and ExpandObjects field count mismatches."
                ),
                "message": (
                    f"Exported OSM OS:Version {osm_short} is newer than local {target_label} "
                    f"{target_ver} ({osm_short} > {target_ver}). VersionTranslator may warn "
                    f"(\"Version extracted from file '{osm_short}' is one increment ahead of OpenStudio "
                    f"Version {target_ver}\"), and newer fields (OS:Site:WaterMainsTemperature, "
                    "OS:Sizing:Zone, Chiller:Electric:EIR in ExpandObjects) may cause field mismatches."
                ),
            }
        )

    if (
        py_tuple
        and cli_tuple
        and py_tuple > cli_tuple
        and not (osm_tuple and osm_tuple == py_tuple and osm_tuple > cli_tuple)
    ):
        compatibility_warnings.append(
            {
                "code": "python_openstudio_version_mismatch",
                "severity": "warning",
                "source": "python_openstudio",
                "python_openstudio_version": py_short,
                "openstudio_cli_version": cli_short,
                "impact": (
                    "honeybee_openstudio exports OSM with OS:Version ahead of local OpenStudio CLI, "
                    "risking VersionTranslator warnings and OS:Site:WaterMainsTemperature / "
                    "OS:Sizing:Zone / ExpandObjects field mismatches."
                ),
                "message": (
                    f"Python OpenStudio package ({py_short}, used by honeybee_openstudio) is newer than "
                    f"local OpenStudio CLI {cli_short} ({py_short} > {cli_short}). Exported OSM files "
                    f"emit OS:Version {py_short}, which may trigger VersionTranslator ahead-of-version "
                    "warnings, OS:Site:WaterMainsTemperature / OS:Sizing:Zone field errors, and "
                    "ExpandObjects field mismatches."
                ),
            }
        )

    return {
        "ironbug_version": ib_ver_short,
        "ironbug_openstudio_version": ib_os_short,
        "ironbug_bundled_openstudio_version": _short_version(ib_bundled_os_ver),
        "ironbug_assembly_openstudio_version": _short_version(ib_asm_os_ver),
        "ironbug_known_openstudio_version": _short_version(ib_known_os_ver),
        "openstudio_csharp_version": cs_short,
        "openstudio_cli_version": cli_short,
        "python_openstudio_version": py_short,
        "osm_version": osm_short,
        "compatible": len(compatibility_warnings) == 0,
        "compatibility_warnings": compatibility_warnings,
    }
