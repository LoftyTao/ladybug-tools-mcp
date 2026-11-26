#!/usr/bin/env python3
"""Generate third-party license notices, corresponding-source manifests, and verbatim component license trees."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import tomllib
from typing import Any
import urllib.error
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[2]

RADIANCE_ATTRIBUTION = (
    "This product includes Radiance software (http://radsite.lbl.gov/) "
    "developed by the Lawrence Berkeley National Laboratory (http://www.lbl.gov/)."
)
EVALGLARE_ATTRIBUTION = (
    "This product includes the evalglare software, "
    "developed at Fraunhofer ISE and EPFL by J. Wienold"
)

DEFAULT_VERSIONS: dict[str, str] = {
    "python": "3.12.16",
    "openstudio": "3.11.0",
    "energyplus": "25.2.0",
    "radiance": "5.4",
    "radiance_tag": "rad5R4",
    "evalglare": "2.10",
    "ironbug": "1.26.1",
    "urbanopt": "1.4.0-rc1",
    "gmsh": "4.15.2",
    "geos": "3.14.1",
    "libraryfemtherm": "0.24.0",
    "lbt_measures": "0.3.3",
    "honeybee_openstudio_gem": "2.38.23",
    "newtonsoft_json": "13.0.3",
    "system_security_permissions": "8.0.0",
    "setuptools": "84.2.1",
}

DEFAULT_URLS: dict[str, str] = {
    "lbt_mcp_repo": "https://github.com/LoftyTao/ladybug-tools-mcp",
    "gmsh_source": "https://gmsh.info/src/gmsh-4.15.2-source.tgz",
    "geos_source": "https://download.osgeo.org/geos/geos-3.14.1.tar.bz2",
    "ironbug_source": "https://github.com/MingboPeng/Ironbug/archive/refs/tags/v1.26.1.tar.gz",
    "dss_python_backend_repo": "https://github.com/dss-extensions/dss_python_backend",
    "dss_capi_repo": "https://github.com/dss-extensions/dss_capi",
    "klusolvex_repo": "https://github.com/dss-extensions/klusolve",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_project_meta() -> tuple[str, str]:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    return str(project["name"]), str(project["version"])


def _read_requirements_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    req_path = REPO_ROOT / "requirements.txt"
    if not req_path.is_file():
        return pins
    for raw_line in req_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if "==" in line:
            name, ver = line.split("==", 1)
            pins[name.strip().lower().replace("_", "-")] = ver.strip()
    return pins


def _detect_installed_versions(pins: dict[str, str]) -> dict[str, str]:
    versions = dict(DEFAULT_VERSIONS)
    for pkg_key, ver_key in (
        ("gmsh", "gmsh"),
        ("openstudio", "openstudio"),
        ("libraryfemtherm", "libraryfemtherm"),
        ("setuptools", "setuptools"),
    ):
        try:
            versions[ver_key] = importlib.metadata.version(pkg_key)
        except importlib.metadata.PackageNotFoundError:
            if pkg_key in pins:
                versions[ver_key] = pins[pkg_key]

    try:
        import shapely

        geos_ver = getattr(shapely, "geos_version_string", None)
        if isinstance(geos_ver, str) and geos_ver.strip():
            versions["geos"] = geos_ver.strip()
    except Exception:
        pass
    return versions


def _load_bundle_manifest(manifest_path: Path | None) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Extract optional exact version and source-archive overrides from a bundle manifest JSON."""
    version_overrides: dict[str, str] = {}
    archive_overrides: dict[str, dict[str, Any]] = {}
    if manifest_path is None or not manifest_path.is_file():
        return version_overrides, archive_overrides

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return version_overrides, archive_overrides

    exact_version_keys = {
        "python",
        "openstudio",
        "energyplus",
        "radiance",
        "radiance_tag",
        "evalglare",
        "ironbug",
        "urbanopt",
        "gmsh",
        "geos",
        "libraryfemtherm",
        "lbt_measures",
        "honeybee_openstudio_gem",
        "newtonsoft_json",
        "system_security_permissions",
        "setuptools",
    }
    source_archive_keys = {"gmsh", "geos", "ironbug"}

    target_versions = payload.get("target_versions")
    if isinstance(target_versions, dict):
        for raw_key, raw_val in target_versions.items():
            norm_key = str(raw_key).lower().replace("-", "_")
            if norm_key in exact_version_keys and isinstance(raw_val, str) and raw_val.strip():
                version_overrides[norm_key] = raw_val.strip()

    def _visit(key_hint: str, obj: Any, *, section: str = "") -> None:
        if isinstance(obj, dict):
            norm = key_hint.lower().replace("-", "_")
            if norm in exact_version_keys and isinstance(obj.get("version"), str) and obj["version"].strip():
                version_overrides[norm] = obj["version"].strip()
            in_source_section = section in {"corresponding_sources", "sources"}
            if (
                norm in source_archive_keys
                and section != "runtimes"
                and (in_source_section or section == "")
                and any(k in obj for k in ("url", "archive", "filename", "sha256", "path"))
            ):
                archive_overrides.setdefault(norm, {}).update(obj)
            next_section = norm if norm in {"runtimes", "corresponding_sources", "sources", "components"} else section
            for child_key, child_val in obj.items():
                _visit(str(child_key), child_val, section=next_section)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    item_id = str(item.get("id") or item.get("name") or key_hint)
                    _visit(item_id, item, section=section)

    _visit("root", payload)
    return version_overrides, archive_overrides


def _read_tar_member(archive_path: Path, member_suffix: str) -> bytes | None:
    if not archive_path.is_file():
        return None
    suffix_norm = member_suffix.replace("\\", "/").lstrip("./")
    with tarfile.open(archive_path, "r:*") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            member_norm = member.name.replace("\\", "/").lstrip("./")
            if member_norm == suffix_norm or member_norm.endswith("/" + suffix_norm):
                extracted = tf.extractfile(member)
                if extracted is not None:
                    return extracted.read()
    return None


def _extract_energyplus_notice_from_openstudio_copyright(copyright_bytes: bytes) -> bytes | None:
    text = copyright_bytes.decode("utf-8", errors="replace").replace("\r\n", "\n")
    marker = "*** EnergyPlus ***"
    start = text.find(marker)
    if start < 0:
        return None
    after_header = text.find("\n", start)
    if after_header < 0:
        return None
    body_start = after_header + 1
    next_section = text.find("\n*** ", body_start)
    section = text[body_start:next_section] if next_section > 0 else text[body_start:]
    return (section.strip() + "\n").encode("utf-8")


def _extract_evalglare_license(evalglare_c: bytes) -> bytes:
    text = evalglare_c.decode("utf-8", errors="replace").replace("\r\n", "\n")
    lines = text.splitlines()
    block: list[str] = []
    in_block = False
    for line in lines:
        if "/* EVALGLARE" in line:
            in_block = True
        if in_block:
            cleaned = line.lstrip("/* ").rstrip()
            if line.strip().endswith("*/"):
                break
            if cleaned.startswith("*"):
                cleaned = cleaned[1:].lstrip()
            block.append(cleaned)
    return ("\n".join(block).strip() + "\n").encode("utf-8")


def _fetch_url_bytes(url: str, *, retries: int = 2) -> bytes:
    headers = {"User-Agent": "ladybug-tools-mcp-license-generator/1.0"}
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            last_error = err
            if err.code == 429 and attempt < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except Exception as err:
            last_error = err
            if attempt < retries:
                time.sleep(1.0)
                continue
            raise
    assert last_error is not None
    raise last_error


def _resolve_bytes(
    *,
    local_paths: list[Path] | None = None,
    archive_spec: tuple[Path, str] | None = None,
    fallback_repo_component: Path | None = None,
    remote_url: str | None = None,
    allow_remote: bool = False,
    transform: Any = None,
) -> bytes:
    if archive_spec is not None:
        archive_path, member_suffix = archive_spec
        raw = _read_tar_member(archive_path, member_suffix)
        if raw is not None:
            return transform(raw) if transform else raw

    for path in local_paths or []:
        if path.is_file():
            raw = path.read_bytes()
            return transform(raw) if transform else raw

    if fallback_repo_component is not None and fallback_repo_component.is_file():
        return fallback_repo_component.read_bytes()

    if remote_url and (allow_remote or fallback_repo_component is None or not fallback_repo_component.is_file()):
        raw = _fetch_url_bytes(remote_url)
        return transform(raw) if transform else raw

    raise FileNotFoundError(
        f"Unable to resolve license asset from local paths={local_paths}, "
        f"archive={archive_spec}, fallback={fallback_repo_component}, url={remote_url}"
    )


def _find_cached_archive(prefixes: tuple[str, ...], search_dirs: list[Path]) -> Path | None:
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir()):
            if candidate.is_file() and candidate.name.startswith(prefixes):
                return candidate
    return None


def _infer_dist_license(dist: importlib.metadata.Distribution) -> str:
    raw_lic = (dist.metadata.get("License-Expression") or dist.metadata.get("License") or "").strip()
    dist_path = Path(str(getattr(dist, "_path", "")))
    if raw_lic == "Copying this work" or (
        dist_path.is_dir() and (dist_path / "LICENSE.ASF-2").is_file() and (dist_path / "LICENSE.GPL-3").is_file()
    ):
        return "Apache-2.0 OR GPL-3.0-or-later"
    if "Berkeley Lab LibraryFEMTHERM" in raw_lic:
        return "BSD-3-Clause (LBNL variant)"
    if raw_lic:
        first = raw_lic.splitlines()[0].strip()
        if len(first) <= 80:
            return first

    if dist_path.is_dir():
        for cand in (dist_path / "licenses" / "LICENSE", dist_path / "LICENSE"):
            if cand.is_file():
                head = cand.read_text(encoding="utf-8", errors="replace")[:500]
                if "GNU AFFERO GENERAL PUBLIC LICENSE" in head:
                    return "AGPL-3.0"
                if "GNU GENERAL PUBLIC LICENSE" in head and "Version 3" in head:
                    return "GPL-3.0"
                if "MIT License" in head or "Permission is hereby granted, free of charge" in head:
                    return "MIT"
    return "See package distribution metadata"


def _collect_lbt_sdk_distributions() -> list[dict[str, str]]:
    """Collect installed Ladybug Tools and key runtime Python package license metadata."""
    prefixes = (
        "ladybug-",
        "honeybee-",
        "dragonfly-",
        "fairyfly-",
        "lbt-",
        "pollination-",
        "queenbee",
        "libraryfemtherm",
        "gmsh",
        "shapely",
        "openstudio",
        "vtk",
        "fastmcp",
        "mcp",
        "uwg",
        "python-daemon",
        "luigi",
        "setuptools",
    )
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for dist in sorted(
        importlib.metadata.distributions(),
        key=lambda item: (item.metadata.get("Name") or "").lower(),
    ):
        name = (dist.metadata.get("Name") or "").strip()
        lower = name.lower()
        if not name or lower == "lbt-mcp" or lower in seen:
            continue
        if not (lower == "mcp" or any(lower.startswith(p) for p in prefixes)):
            continue
        seen.add(lower)
        records.append({"name": name, "version": dist.version, "license": _infer_dist_license(dist)})
    return records


def _collect_cargo_crate_summary(repo_licenses_dir: Path, allow_remote: bool) -> str:
    """Summarize Rust crate licenses for rune_viewer workspace and vendored Rune crates."""
    fallback = repo_licenses_dir / "components" / "rune_viewer" / "CARGO_CRATE_LICENSES.md"
    manifest = REPO_ROOT / "rune_viewer" / "Cargo.toml"
    cargo_exe = shutil.which("cargo")
    if cargo_exe and manifest.is_file():
        for extra_args in (["--offline"], []):
            proc = subprocess.run(
                [cargo_exe, "metadata", "--manifest-path", str(manifest), "--format-version", "1", *extra_args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                packages = sorted(
                    data.get("packages", []),
                    key=lambda pkg: (str(pkg.get("name", "")).lower(), str(pkg.get("version", ""))),
                )
                workspace_ids = set(data.get("workspace_members", []))
                workspace_pkgs = [pkg for pkg in packages if pkg.get("id") in workspace_ids]
                local_path_pkgs = [
                    pkg for pkg in packages if not pkg.get("source") and pkg.get("id") not in workspace_ids
                ]
                counts = Counter((pkg.get("license") or "UNSPECIFIED") for pkg in packages)

                lines = [
                    "# Rune 3D Viewer (`rune_viewer`) Cargo Workspace Crate License Summary",
                    "",
                    f"Generated from `{manifest.relative_to(REPO_ROOT).as_posix()}` and `rune_viewer/Cargo.lock` "
                    f"({len(packages)} total resolved crates).",
                    "",
                    "## 1. Workspace Crates (`rune_viewer/crates/*`)",
                    "",
                    "| Crate | Version | License |",
                    "|---|---|---|",
                ]
                for pkg in workspace_pkgs:
                    lines.append(
                        f"| `{pkg['name']}` | `{pkg['version']}` | `{pkg.get('license') or 'UNSPECIFIED'}` |"
                    )
                lines.extend(
                    [
                        "",
                        "## 2. Vendored Path Crates (`vendor/rune/*`)",
                        "",
                        "| Crate | Version | License |",
                        "|---|---|---|",
                    ]
                )
                for pkg in local_path_pkgs:
                    lines.append(
                        f"| `{pkg['name']}` | `{pkg['version']}` | `{pkg.get('license') or 'UNSPECIFIED'}` |"
                    )
                lines.extend(
                    [
                        "",
                        "## 3. Aggregate License Distribution Across Dependency Graph",
                        "",
                        "| License Expression | Crate Count |",
                        "|---|---|",
                    ]
                )
                for lic_expr, count in counts.most_common():
                    lines.append(f"| `{lic_expr}` | {count} |")
                lines.extend(
                    [
                        "",
                        "## 4. Complete Resolved Crate Inventory",
                        "",
                        "| Crate | Version | License | Source |",
                        "|---|---|---|---|",
                    ]
                )
                for pkg in packages:
                    src = "workspace/path" if not pkg.get("source") else "crates.io"
                    lines.append(
                        f"| `{pkg['name']}` | `{pkg['version']}` | "
                        f"`{pkg.get('license') or 'UNSPECIFIED'}` | {src} |"
                    )
                lines.append("")
                return "\n".join(lines)
            if not allow_remote:
                break

    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")

    lock_path = REPO_ROOT / "rune_viewer" / "Cargo.lock"
    if lock_path.is_file():
        lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
        pkgs = lock.get("package", [])
        lines = [
            "# Rune 3D Viewer (`rune_viewer`) Cargo Workspace Crate License Summary",
            "",
            f"Generated from `rune_viewer/Cargo.lock` ({len(pkgs)} locked packages; `cargo metadata` unavailable).",
            "",
        ]
        for pkg in sorted(pkgs, key=lambda item: str(item.get("name", "")).lower()):
            lines.append(f"- `{pkg['name']}` `{pkg['version']}`")
        lines.append("")
        return "\n".join(lines)
    raise FileNotFoundError("Cannot generate Cargo crate license summary: Cargo.lock missing.")


def _stage_component_licenses(
    *,
    components_dir: Path,
    repo_components_dir: Path,
    versions: dict[str, str],
    allow_remote: bool,
) -> dict[str, list[str]]:
    """Gather verbatim license/notice texts into <output>/licenses/components/."""
    cache_dir = REPO_ROOT / "build" / "offline-cache"
    source_cache_dir = cache_dir / "sources"
    search_dirs = [cache_dir, source_cache_dir]

    openstudio_archive = _find_cached_archive(("OpenStudio-",), search_dirs)
    python_archive = _find_cached_archive(("cpython-3.12",), search_dirs)
    lbt_measures_archive = _find_cached_archive(("lbt-measures-",), search_dirs)
    hb_os_gem_archive = _find_cached_archive(("honeybee-openstudio-gem-",), search_dirs)
    gmsh_archive = _find_cached_archive(("gmsh-",), search_dirs)
    geos_archive = _find_cached_archive(("geos-",), search_dirs)
    ironbug_archive = _find_cached_archive(("Ironbug-",), search_dirs)

    lbt_pf = Path(r"C:\Program Files\ladybug_tools")
    urbanopt_dir = Path(r"C:\URBANopt-cli-1.4.0-rc1")
    dotnet_dir = Path(r"C:\Program Files\dotnet")
    nuget_dir = Path.home() / ".nuget" / "packages"
    site_packages = REPO_ROOT / ".venv" / "Lib" / "site-packages"

    written: dict[str, list[str]] = {}

    def _write_asset(component: str, rel_name: str, data: bytes) -> None:
        dest = components_dir / component / rel_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not (dest.is_file() and dest.read_bytes() == data):
            dest.write_bytes(data)
        written.setdefault(component, []).append(f"licenses/components/{component}/{rel_name}")

    # 1. ladybug-tools-mcp & LBT Core SDKs
    _write_asset(
        "ladybug-tools-mcp",
        "LICENSE",
        _resolve_bytes(
            local_paths=[REPO_ROOT / "LICENSE"],
            fallback_repo_component=repo_components_dir / "ladybug-tools-mcp" / "LICENSE",
        ),
    )
    _write_asset(
        "ladybug-tools-mcp",
        "lbt-measures-LICENSE.md",
        _resolve_bytes(
            local_paths=[lbt_pf / "resources" / "measures" / "LICENSE.md"],
            archive_spec=(lbt_measures_archive, "LICENSE.md") if lbt_measures_archive else None,
            fallback_repo_component=repo_components_dir / "ladybug-tools-mcp" / "lbt-measures-LICENSE.md",
            remote_url=f"https://raw.githubusercontent.com/ladybug-tools/lbt-measures/v{versions['lbt_measures']}/LICENSE.md",
            allow_remote=allow_remote,
        ),
    )
    _write_asset(
        "ladybug-tools-mcp",
        "honeybee-openstudio-gem-LICENSE.md",
        _resolve_bytes(
            archive_spec=(hb_os_gem_archive, f"honeybee-openstudio-gem-{versions['honeybee_openstudio_gem']}/LICENSE.md")
            if hb_os_gem_archive
            else None,
            fallback_repo_component=repo_components_dir / "ladybug-tools-mcp" / "honeybee-openstudio-gem-LICENSE.md",
            remote_url=(
                f"https://raw.githubusercontent.com/ladybug-tools/honeybee-openstudio-gem/"
                f"v{versions['honeybee_openstudio_gem']}/LICENSE.md"
            ),
            allow_remote=allow_remote,
        ),
    )
    sdk_rows = _collect_lbt_sdk_distributions()
    sdk_md = [
        "# Ladybug Tools Core SDKs & Bundled Measure Libraries",
        "",
        "| Package | Version | License |",
        "|---|---|---|",
        *[f"| `{row['name']}` | `{row['version']}` | `{row['license']}` |" for row in sdk_rows],
        "",
    ]
    _write_asset("ladybug-tools-mcp", "LBT_CORE_SDKS_NOTICE.md", "\n".join(sdk_md).encode("utf-8"))

    # 2. fairyfly_next_therm & honeybee_gbas
    _write_asset(
        "fairyfly_next_therm",
        "LICENSE",
        _resolve_bytes(
            local_paths=[REPO_ROOT / "src" / "fairyfly_next_therm" / "LICENSE"],
            fallback_repo_component=repo_components_dir / "fairyfly_next_therm" / "LICENSE",
        ),
    )
    _write_asset(
        "honeybee_gbas",
        "LICENSE",
        _resolve_bytes(
            local_paths=[REPO_ROOT / "src" / "honeybee_gbas" / "LICENSE"],
            fallback_repo_component=repo_components_dir / "honeybee_gbas" / "LICENSE",
        ),
    )
    _write_asset(
        "honeybee_gbas",
        "LICENSE-ezdwg.txt",
        _resolve_bytes(
            local_paths=[REPO_ROOT / "src" / "honeybee_gbas" / "dwg" / "LICENSE-ezdwg.txt"],
            fallback_repo_component=repo_components_dir / "honeybee_gbas" / "LICENSE-ezdwg.txt",
        ),
    )

    # 3. Radiance 5.4 (rad5R4)
    _write_asset(
        "radiance",
        "LICENSE-Radiance-1.0.txt",
        _resolve_bytes(
            local_paths=[lbt_pf / "licenses" / "radiance.txt"],
            fallback_repo_component=repo_components_dir / "radiance" / "LICENSE-Radiance-1.0.txt",
        ),
    )
    _write_asset(
        "radiance",
        "LICENSE-rad5R4.txt",
        _resolve_bytes(
            fallback_repo_component=repo_components_dir / "radiance" / "LICENSE-rad5R4.txt",
            remote_url=f"https://raw.githubusercontent.com/LBNL-ETA/Radiance/{versions['radiance_tag']}/License.txt",
            allow_remote=allow_remote,
        ),
    )
    rad_notice = (
        "Radiance 5.4 (rad5R4)\n"
        "=====================\n\n"
        f"{RADIANCE_ATTRIBUTION}\n\n"
        "Distribution notes:\n"
        "- Included: Radiance 5.4 command-line raytracing binaries and library data (`bin/`, `lib/`).\n"
        "- Excluded/pruned from Windows offline runtime: `rvu.exe` and LGPL Qt5 DLLs "
        "(`Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Widgets.dll`, `platforms/`, `imageformats/`).\n"
    )
    _write_asset("radiance", "NOTICE.txt", rad_notice.encode("utf-8"))

    # 4. Evalglare 2.0 / 2.10
    _write_asset(
        "evalglare",
        "LICENSE.txt",
        _resolve_bytes(
            fallback_repo_component=repo_components_dir / "evalglare" / "LICENSE.txt",
            remote_url=f"https://raw.githubusercontent.com/LBNL-ETA/Radiance/{versions['radiance_tag']}/src/util/evalglare.c",
            allow_remote=allow_remote,
            transform=_extract_evalglare_license,
        ),
    )

    # 5. OpenStudio(R) 3.11.0
    os_license_bytes = _resolve_bytes(
        local_paths=[urbanopt_dir / "OpenStudio" / "LICENSE.md"],
        archive_spec=(openstudio_archive, "LICENSE.md") if openstudio_archive else None,
        fallback_repo_component=repo_components_dir / "openstudio" / "LICENSE.md",
        remote_url=f"https://raw.githubusercontent.com/NREL/OpenStudio/v{versions['openstudio']}/LICENSE.md",
        allow_remote=allow_remote,
    )
    os_copyright_bytes = _resolve_bytes(
        local_paths=[urbanopt_dir / "OpenStudio" / "copyright.txt"],
        archive_spec=(openstudio_archive, "copyright.txt") if openstudio_archive else None,
        fallback_repo_component=repo_components_dir / "openstudio" / "copyright.txt",
        remote_url=f"https://raw.githubusercontent.com/NREL/OpenStudio/v{versions['openstudio']}/copyright.txt",
        allow_remote=allow_remote,
    )
    _write_asset("openstudio", "LICENSE.md", os_license_bytes)
    _write_asset("openstudio", "copyright.txt", os_copyright_bytes)
    os_pruning = (
        f"OpenStudio(R) {versions['openstudio']} Runtime Staging & Pruning Notice\n"
        "=============================================================\n\n"
        "- Included in Standard Windows Installer: `bin/` (excluding `openstudiolib.lib`), "
        "`CSharp/openstudio/` (x64 bindings from NuGet `NREL.OpenStudio.win` "
        f"`{versions['openstudio']}`, `BSD-3-Clause`; `x86/` omitted; hardlinked into "
        f"`runtimes/ironbug/{versions['ironbug']}/` at install/sync time), and the unmodified "
        f"`EnergyPlus/` subdirectory (`EnergyPlus version {versions['energyplus']}`).\n"
        "- Pruned non-runtime directories/files: `Python/`, `Perl/`, `Radiance/`, `include/`, "
        "`Examples/`, and `lib/openstudiolib.lib`.\n"
        "- `Ruby/`: omitted from the Standard Windows Installer and distributed only in the optional "
        f"URBANopt {versions['urbanopt']} `.lbtpack` extension pack.\n"
    )
    _write_asset("openstudio", "PRUNING_NOTICE.txt", os_pruning.encode("utf-8"))

    # 6. EnergyPlus version 25.2.0
    ep_license_bytes = _resolve_bytes(
        archive_spec=(openstudio_archive, "copyright.txt") if openstudio_archive else None,
        local_paths=[urbanopt_dir / "OpenStudio" / "copyright.txt"],
        fallback_repo_component=repo_components_dir / "energyplus" / "LICENSE.txt",
        remote_url=f"https://raw.githubusercontent.com/NREL/EnergyPlus/v{versions['energyplus']}/LICENSE.txt",
        allow_remote=allow_remote,
        transform=lambda raw: (
            _extract_energyplus_notice_from_openstudio_copyright(raw)
            if b"*** EnergyPlus ***" in raw
            else raw
        ),
    )
    _write_asset("energyplus", "LICENSE.txt", ep_license_bytes)
    ep_notice = (
        f"EnergyPlus version {versions['energyplus']} Attribution and Non-Endorsement Notice\n"
        "=====================================================================\n\n"
        f"This distribution includes unmodified EnergyPlus version {versions['energyplus']} software\n"
        f"bundled inside the OpenStudio(R) {versions['openstudio']} `EnergyPlus/` directory.\n\n"
        "No endorsement by the U.S. Department of Energy (DOE), Lawrence Berkeley National Laboratory,\n"
        "the University of Illinois, Oak Ridge National Laboratory, Alliance for Energy Innovation, LLC,\n"
        "or EnergyPlus / E+ is implied or granted. Neither \"EnergyPlus\", \"E+\", nor \"e+\" is used in any\n"
        "company name, product name, or promotional designation.\n"
    )
    _write_asset("energyplus", "NOTICE.txt", ep_notice.encode("utf-8"))

    # 7. HygroThermFEM / Fairyfly native
    htfem_src = REPO_ROOT / "src" / "pyhygrothermfem_fairyfly"
    _write_asset(
        "hygrothermfem_fairyfly",
        "third_party_notices.txt",
        _resolve_bytes(
            local_paths=[htfem_src / "third_party_notices.txt"],
            fallback_repo_component=repo_components_dir / "hygrothermfem_fairyfly" / "third_party_notices.txt",
        ),
    )
    _write_asset(
        "hygrothermfem_fairyfly",
        "LICENSE-pyHygroThermFEM-Fairyfly.txt",
        _resolve_bytes(
            local_paths=[REPO_ROOT / "vendor" / "pyHygroThermFEM-Fairyfly" / "LICENSE"],
            fallback_repo_component=(
                repo_components_dir / "hygrothermfem_fairyfly" / "LICENSE-pyHygroThermFEM-Fairyfly.txt"
            ),
        ),
    )
    _write_asset(
        "hygrothermfem_fairyfly",
        "libraryfemtherm/LICENSE",
        _resolve_bytes(
            local_paths=[
                site_packages / f"libraryfemtherm-{versions['libraryfemtherm']}.dist-info" / "licenses" / "LICENSE"
            ],
            fallback_repo_component=repo_components_dir / "hygrothermfem_fairyfly" / "libraryfemtherm" / "LICENSE",
        ),
    )
    tpl_root = htfem_src / "third_party_licenses"
    if tpl_root.is_dir():
        for src_file in sorted(tpl_root.rglob("*")):
            if src_file.is_file():
                rel = src_file.relative_to(htfem_src).as_posix()
                _write_asset("hygrothermfem_fairyfly", rel, src_file.read_bytes())
    else:
        fallback_tpl = repo_components_dir / "hygrothermfem_fairyfly" / "third_party_licenses"
        for src_file in sorted(fallback_tpl.rglob("*")):
            if src_file.is_file():
                rel = src_file.relative_to(repo_components_dir / "hygrothermfem_fairyfly").as_posix()
                _write_asset("hygrothermfem_fairyfly", rel, src_file.read_bytes())

    # 8. Copyleft binary deps requiring corresponding source: gmsh, GEOS, Ironbug, optional DES/OpenDSS
    _write_asset(
        "gmsh",
        "LICENSE.txt",
        _resolve_bytes(
            archive_spec=(gmsh_archive, f"gmsh-{versions['gmsh']}-source/LICENSE.txt") if gmsh_archive else None,
            fallback_repo_component=repo_components_dir / "gmsh" / "LICENSE.txt",
            remote_url="https://gmsh.info/LICENSE.txt",
            allow_remote=allow_remote,
        ),
    )
    _write_asset(
        "geos",
        "COPYING",
        _resolve_bytes(
            archive_spec=(geos_archive, f"geos-{versions['geos']}/COPYING") if geos_archive else None,
            fallback_repo_component=repo_components_dir / "geos" / "COPYING",
            remote_url=f"https://raw.githubusercontent.com/libgeos/geos/{versions['geos']}/COPYING",
            allow_remote=allow_remote,
        ),
    )
    shapely_geos_candidates = sorted(site_packages.glob("shapely-*.dist-info/licenses/LICENSE_GEOS"))
    _write_asset(
        "geos",
        "LICENSE_GEOS",
        _resolve_bytes(
            local_paths=shapely_geos_candidates,
            fallback_repo_component=repo_components_dir / "geos" / "LICENSE_GEOS",
        ),
    )
    _write_asset(
        "ironbug",
        "LICENSE",
        _resolve_bytes(
            archive_spec=(ironbug_archive, f"Ironbug-{versions['ironbug']}/LICENSE") if ironbug_archive else None,
            fallback_repo_component=repo_components_dir / "ironbug" / "LICENSE",
            remote_url=f"https://raw.githubusercontent.com/MingboPeng/Ironbug/v{versions['ironbug']}/LICENSE",
            allow_remote=allow_remote,
        ),
    )

    for rel, url in (
        ("LICENSE.LGPL3", "https://raw.githubusercontent.com/dss-extensions/dss_python_backend/master/LICENSE.LGPL3"),
        ("LICENSE.BSD3", "https://raw.githubusercontent.com/dss-extensions/dss_python_backend/master/LICENSE.BSD3"),
        ("OPENDSS_LICENSE", "https://raw.githubusercontent.com/dss-extensions/dss_python_backend/master/OPENDSS_LICENSE"),
        ("KLUSOLVEX_LICENSE.txt", "https://raw.githubusercontent.com/dss-extensions/klusolve/master/LICENSE"),
    ):
        _write_asset(
            "dss_opendss",
            rel,
            _resolve_bytes(
                fallback_repo_component=repo_components_dir / "dss_opendss" / rel,
                remote_url=url,
                allow_remote=allow_remote,
            ),
        )

    # 9. IronbugBridge / .NET
    _write_asset(
        "ironbug_bridge",
        "Newtonsoft.Json-LICENSE.md",
        _resolve_bytes(
            local_paths=[nuget_dir / "newtonsoft.json" / versions["newtonsoft_json"] / "LICENSE.md"],
            fallback_repo_component=repo_components_dir / "ironbug_bridge" / "Newtonsoft.Json-LICENSE.md",
            remote_url=f"https://raw.githubusercontent.com/JamesNK/Newtonsoft.Json/{versions['newtonsoft_json']}/LICENSE.md",
            allow_remote=allow_remote,
        ),
    )
    _write_asset(
        "ironbug_bridge",
        "System.Security.Permissions-LICENSE.TXT",
        _resolve_bytes(
            local_paths=[nuget_dir / "system.security.permissions" / versions["system_security_permissions"] / "LICENSE.TXT"],
            fallback_repo_component=repo_components_dir / "ironbug_bridge" / "System.Security.Permissions-LICENSE.TXT",
            remote_url="https://raw.githubusercontent.com/dotnet/runtime/main/LICENSE.TXT",
            allow_remote=allow_remote,
        ),
    )
    _write_asset(
        "ironbug_bridge",
        "MICROSOFT_DOTNET_LICENSE.txt",
        _resolve_bytes(
            local_paths=[dotnet_dir / "LICENSE.txt"],
            fallback_repo_component=repo_components_dir / "ironbug_bridge" / "MICROSOFT_DOTNET_LICENSE.txt",
        ),
    )
    _write_asset(
        "ironbug_bridge",
        "MICROSOFT_DOTNET_THIRD_PARTY_NOTICES.txt",
        _resolve_bytes(
            local_paths=[dotnet_dir / "ThirdPartyNotices.txt"],
            fallback_repo_component=repo_components_dir / "ironbug_bridge" / "MICROSOFT_DOTNET_THIRD_PARTY_NOTICES.txt",
        ),
    )

    # 10. Rune 3D Viewer
    rune_root = REPO_ROOT / "vendor" / "rune"
    for rel, src in (
        ("LICENSE", rune_root / "LICENSE"),
        ("THIRD_PARTY_NOTICES.md", rune_root / "THIRD_PARTY_NOTICES.md"),
        ("OFL.txt", rune_root / "crates" / "rune-kit" / "assets" / "math" / "OFL.txt"),
        ("FONT_NOTICE.txt", rune_root / "crates" / "rune-kit" / "assets" / "math" / "FONT_NOTICE.txt"),
        ("Inter-LICENSE.txt", rune_root / "crates" / "rune" / "assets" / "Inter-LICENSE.txt"),
        ("IBMPlexMono-LICENSE.txt", rune_root / "crates" / "rune" / "assets" / "IBMPlexMono-LICENSE.txt"),
    ):
        _write_asset(
            "rune_viewer",
            rel,
            _resolve_bytes(
                local_paths=[src],
                fallback_repo_component=repo_components_dir / "rune_viewer" / rel,
            ),
        )
    cargo_summary = _collect_cargo_crate_summary(REPO_ROOT / "licenses", allow_remote=allow_remote)
    _write_asset("rune_viewer", "CARGO_CRATE_LICENSES.md", cargo_summary.encode("utf-8"))

    # 11. Python 3.12 (python-build-standalone) & setuptools
    _write_asset(
        "python",
        "LICENSE.txt",
        _resolve_bytes(
            archive_spec=(python_archive, "python/LICENSE.txt") if python_archive else None,
            local_paths=[lbt_pf / "licenses" / "python.txt"],
            fallback_repo_component=repo_components_dir / "python" / "LICENSE.txt",
            remote_url=f"https://raw.githubusercontent.com/python/cpython/v{versions['python']}/LICENSE",
            allow_remote=allow_remote,
        ),
    )
    setuptools_lic_candidates = [
        *sorted(site_packages.glob("setuptools-*.dist-info/licenses/LICENSE")),
        *sorted(site_packages.glob("setuptools-*.dist-info/LICENSE")),
    ]
    _write_asset(
        "setuptools",
        "LICENSE",
        _resolve_bytes(
            local_paths=setuptools_lic_candidates,
            fallback_repo_component=repo_components_dir / "setuptools" / "LICENSE",
            remote_url=f"https://raw.githubusercontent.com/pypa/setuptools/v{versions['setuptools']}/LICENSE",
            allow_remote=allow_remote,
        ),
    )

    # 12. Optional URBANopt 1.4.0-rc1 pack
    _write_asset(
        "urbanopt",
        "RUBY_LICENSE.txt",
        _resolve_bytes(
            local_paths=[urbanopt_dir / "ruby" / "LICENSE.txt"],
            fallback_repo_component=repo_components_dir / "urbanopt" / "RUBY_LICENSE.txt",
        ),
    )
    _write_asset(
        "urbanopt",
        "RUBY_BSDL.txt",
        _resolve_bytes(
            fallback_repo_component=repo_components_dir / "urbanopt" / "RUBY_BSDL.txt",
            remote_url="https://raw.githubusercontent.com/ruby/ruby/master/BSDL",
            allow_remote=allow_remote,
        ),
    )
    uo_cli_lic = sorted((urbanopt_dir / "gems").glob("ruby/*/gems/urbanopt-cli-*/LICENSE.md"))
    _write_asset(
        "urbanopt",
        "URBANOPT_CLI_LICENSE.md",
        _resolve_bytes(
            local_paths=uo_cli_lic,
            fallback_repo_component=repo_components_dir / "urbanopt" / "URBANOPT_CLI_LICENSE.md",
            remote_url=f"https://raw.githubusercontent.com/urbanopt/urbanopt-cli/v{versions['urbanopt']}/LICENSE.md",
            allow_remote=allow_remote,
        ),
    )
    os_gem_lic = sorted((urbanopt_dir / "openstudio-runtime-gems").glob("ruby/*/gems/openstudio-*/LICENSE.md"))
    _write_asset(
        "urbanopt",
        "OPENSTUDIO_GEMS_LICENSE.md",
        _resolve_bytes(
            local_paths=os_gem_lic,
            fallback_repo_component=repo_components_dir / "urbanopt" / "OPENSTUDIO_GEMS_LICENSE.md",
        ),
    )

    return written


def _resolve_source_archive_sha(
    *,
    filename: str,
    manifest_override: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    if manifest_override:
        sha = manifest_override.get("sha256")
        name = manifest_override.get("archive") or manifest_override.get("filename") or filename
        if isinstance(sha, str) and len(sha) == 64:
            return str(name), sha.lower()
    cached = REPO_ROOT / "build" / "offline-cache" / "sources" / filename
    if cached.is_file():
        return filename, _sha256_file(cached)
    return filename, None


def _build_source_manifest(
    *,
    project_name: str,
    project_version: str,
    versions: dict[str, str],
    archive_overrides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gmsh_name, gmsh_sha = _resolve_source_archive_sha(
        filename=f"gmsh-{versions['gmsh']}-source.tgz",
        manifest_override=archive_overrides.get("gmsh"),
    )
    geos_name, geos_sha = _resolve_source_archive_sha(
        filename=f"geos-{versions['geos']}.tar.bz2",
        manifest_override=archive_overrides.get("geos"),
    )
    ironbug_name, ironbug_sha = _resolve_source_archive_sha(
        filename=f"Ironbug-{versions['ironbug']}.tar.gz",
        manifest_override=archive_overrides.get("ironbug"),
    )

    gmsh_url = (archive_overrides.get("gmsh") or {}).get("url") or (
        f"https://gmsh.info/src/gmsh-{versions['gmsh']}-source.tgz"
    )
    geos_url = (archive_overrides.get("geos") or {}).get("url") or (
        f"https://download.osgeo.org/geos/geos-{versions['geos']}.tar.bz2"
    )
    ironbug_url = (archive_overrides.get("ironbug") or {}).get("url") or (
        f"https://github.com/MingboPeng/Ironbug/archive/refs/tags/v{versions['ironbug']}.tar.gz"
    )

    entries: list[dict[str, Any]] = [
        {
            "id": "ladybug-tools-mcp",
            "name": "ladybug-tools-mcp",
            "package_name": project_name,
            "version": project_version,
            "license": "AGPL-3.0-only",
            "kind": "primary_application",
            "bundled_in_standard": True,
            "requires_corresponding_source": True,
            "source_type": "repo_sdist",
            "source_url": DEFAULT_URLS["lbt_mcp_repo"],
            "archive_name": None,
            "sha256": None,
            "included_paths": [
                "LICENSE",
                "pyproject.toml",
                "MANIFEST.in",
                "src/",
                "rune_viewer/",
                "vendor/rune/",
                "vendor/pyHygroThermFEM-Fairyfly/",
                "scripts/distribution/launcher/",
                "licenses/",
            ],
            "license_files": ["LICENSE"],
        },
        {
            "id": "lbt-rune-viewer",
            "name": "Rune 3D Viewer (lbt-rune-viewer)",
            "version": "0.1.0",
            "license": "GPL-3.0-or-later AND MIT AND OFL-1.1",
            "kind": "copyleft_binary_component",
            "bundled_in_standard": True,
            "requires_corresponding_source": True,
            "source_type": "in_repo_workspace",
            "source_url": DEFAULT_URLS["lbt_mcp_repo"],
            "archive_name": None,
            "sha256": None,
            "included_paths": ["rune_viewer/", "vendor/rune/"],
            "license_files": [
                "licenses/components/rune_viewer/LICENSE",
                "licenses/components/rune_viewer/THIRD_PARTY_NOTICES.md",
                "licenses/components/rune_viewer/OFL.txt",
                "licenses/components/rune_viewer/CARGO_CRATE_LICENSES.md",
            ],
        },
        {
            "id": "gmsh",
            "name": "Gmsh",
            "version": versions["gmsh"],
            "license": "GPL-2.0-or-later",
            "kind": "copyleft_binary_dependency",
            "bundled_in_standard": True,
            "requires_corresponding_source": True,
            "source_type": "upstream_tarball",
            "source_url": gmsh_url,
            "archive_name": gmsh_name,
            "sha256": gmsh_sha,
            "binary_artifacts": ["site-packages/gmsh*", "gmsh-*.dll"],
            "license_files": ["licenses/components/gmsh/LICENSE.txt"],
        },
        {
            "id": "geos",
            "name": "GEOS (shapely.libs geos_c)",
            "version": versions["geos"],
            "license": "LGPL-2.1-only",
            "kind": "copyleft_binary_dependency",
            "bundled_in_standard": True,
            "requires_corresponding_source": True,
            "source_type": "upstream_tarball",
            "source_url": geos_url,
            "archive_name": geos_name,
            "sha256": geos_sha,
            "binary_artifacts": [
                "site-packages/shapely.libs/geos_c-*.dll",
                "site-packages/shapely.libs/geos-*.dll",
            ],
            "license_files": [
                "licenses/components/geos/COPYING",
                "licenses/components/geos/LICENSE_GEOS",
            ],
        },
        {
            "id": "ironbug",
            "name": "Ironbug",
            "version": versions["ironbug"],
            "license": "LGPL-3.0-or-later",
            "kind": "copyleft_binary_dependency",
            "bundled_in_standard": True,
            "requires_corresponding_source": True,
            "source_type": "upstream_tarball",
            "source_url": ironbug_url,
            "archive_name": ironbug_name,
            "sha256": ironbug_sha,
            "binary_artifacts": [
                f"runtimes/ironbug/{versions['ironbug']}/Ironbug.Console.exe",
                f"runtimes/ironbug/{versions['ironbug']}/Ironbug.HVAC.dll",
                f"runtimes/ironbug/{versions['ironbug']}/Ironbug.Core.dll",
                f"runtimes/ironbug/{versions['ironbug']}/Ironbug.EPDoc.dll",
            ],
            "license_files": ["licenses/components/ironbug/LICENSE"],
        },
        {
            "id": "dss_python_backend",
            "name": "DSS-Python Backend / KLUSolveX (Optional DES / OpenDSS)",
            "version": "optional-des-opendss",
            "license": "LGPL-3.0-only AND LGPL-2.1-or-later AND BSD-3-Clause",
            "kind": "optional_copyleft_binary_dependency",
            "bundled_in_standard": False,
            "requires_corresponding_source": True,
            "requires_corresponding_source_if_distributed": True,
            "source_type": "upstream_repositories",
            "source_url": DEFAULT_URLS["dss_python_backend_repo"],
            "companion_source_urls": [
                DEFAULT_URLS["dss_capi_repo"],
                DEFAULT_URLS["klusolvex_repo"],
            ],
            "archive_name": None,
            "sha256": None,
            "binary_artifacts": [
                "dss_python_backend (optional DES/OpenDSS)",
                "klusolvex*.dll (optional DES/OpenDSS)",
            ],
            "license_files": [
                "licenses/components/dss_opendss/LICENSE.LGPL3",
                "licenses/components/dss_opendss/LICENSE.BSD3",
                "licenses/components/dss_opendss/OPENDSS_LICENSE",
                "licenses/components/dss_opendss/KLUSOLVEX_LICENSE.txt",
            ],
        },
    ]

    return {
        "schema_version": 1,
        "project": project_name,
        "version": project_version,
        "license": "AGPL-3.0-only",
        "corresponding_source_archive": f"{project_name}-{project_version}-corresponding-source.tar.zst",
        "entries": entries,
    }


def _render_third_party_notices(
    *,
    project_name: str,
    project_version: str,
    versions: dict[str, str],
) -> str:
    sdk_rows = _collect_lbt_sdk_distributions()
    sdk_table = "\n".join(
        f"| `{row['name']}` | `{row['version']}` | `{row['license']}` |" for row in sdk_rows
    )

    return f"""# Third-Party Notices and License Disclosures (`{project_name}` {project_version})

This distribution of **ladybug-tools-mcp** (`{project_name}` `{project_version}`) is licensed under the
**GNU Affero General Public License v3.0 (`AGPL-3.0-only`)** (see [`LICENSE`](../LICENSE)).
Verbatim upstream license texts, notices, and disclosures for all bundled and optional components
are preserved under [`licenses/components/`](components/) and cross-referenced in
[`licenses/CORRESPONDING_SOURCE.md`](CORRESPONDING_SOURCE.md) and
[`licenses/SOURCE_MANIFEST.json`](SOURCE_MANIFEST.json).

---

## 1. Ladybug Tools MCP & Ladybug Tools Core SDKs (`AGPL-3.0-only` / `AGPL-3.0`)

- **ladybug-tools-mcp (`{project_name}` `{project_version}`)**: Licensed under `AGPL-3.0-only`
  ([`LICENSE`](../LICENSE), [`licenses/components/ladybug-tools-mcp/LICENSE`](components/ladybug-tools-mcp/LICENSE)).
- **Ladybug Tools Core Python SDKs**: `ladybug-core`, `ladybug-geometry`, `ladybug-geometry-polyskel`,
  `ladybug-comfort`, `ladybug-display`, `ladybug-radiance`, `ladybug-vtk`, `lbt-ladybug`,
  `honeybee-core`, `honeybee-energy`, `honeybee-energy-standards`, `honeybee-radiance`,
  `honeybee-radiance-command`, `honeybee-radiance-folder`, `honeybee-designbuilder`, `honeybee-doe2`,
  `honeybee-openstudio`, `lbt-honeybee`, `dragonfly-core`, `dragonfly-energy`, `dragonfly-radiance`,
  `dragonfly-uwg`, `dragonfly-comparison`, `dragonfly-designbuilder`, `dragonfly-display`,
  `dragonfly-doe2`, `dragonfly-openstudio`, `lbt-dragonfly`, `fairyfly-core`, `lbt-recipes`,
  `pollination-handlers`, and `queenbee-local` are licensed under `AGPL-3.0` (with schema/companion
  packages under `MIT` / `BSD-3-Clause`, `uwg` under `GPL-3.0`, and `honeybee-radiance-postprocess`
  carrying `GPLv3` metadata and `AGPL-3.0` `LICENSE`).
- **Bundled Measures & Adapter**: `lbt-measures` (`v{versions['lbt_measures']}`) and
  `honeybee-openstudio-gem` (`v{versions['honeybee_openstudio_gem']}`) are licensed under `BSD-3-Clause`
  ([`lbt-measures-LICENSE.md`](components/ladybug-tools-mcp/lbt-measures-LICENSE.md),
  [`honeybee-openstudio-gem-LICENSE.md`](components/ladybug-tools-mcp/honeybee-openstudio-gem-LICENSE.md)).

<details>
<summary>Installed Ladybug Tools and key Python dependency inventory</summary>

| Package | Version | License |
|---|---|---|
{sdk_table}

</details>

---

## 2. Bundled Extensions: `fairyfly_next_therm` & `honeybee_gbas`

- **`fairyfly_next_therm`**: Licensed under `AGPL-3.0-only`
  ([`licenses/components/fairyfly_next_therm/LICENSE`](components/fairyfly_next_therm/LICENSE),
  copied from `src/fairyfly_next_therm/LICENSE`).
- **`honeybee_gbas`**: Licensed under `AGPL-3.0-only`
  ([`licenses/components/honeybee_gbas/LICENSE`](components/honeybee_gbas/LICENSE),
  copied from `src/honeybee_gbas/LICENSE`).
- **`honeybee_gbas/dwg` (`ezdwg` R2000 adapter)**: R2000 container, database defaults, and
  standard-entity encodings adapted from `monozukuri-ai/ezdwg` under the `MIT` License
  ([`licenses/components/honeybee_gbas/LICENSE-ezdwg.txt`](components/honeybee_gbas/LICENSE-ezdwg.txt),
  copied from `src/honeybee_gbas/dwg/LICENSE-ezdwg.txt`).

---

## 3. Radiance {versions['radiance']} (`{versions['radiance_tag']}`)

> {RADIANCE_ATTRIBUTION}

- **Licenses**:
  - Radiance Software License, Version 1.0 (containing the Section 3 attribution above):
    [`licenses/components/radiance/LICENSE-Radiance-1.0.txt`](components/radiance/LICENSE-Radiance-1.0.txt)
  - Radiance Software License, Version 2.0 (`{versions['radiance_tag']}`):
    [`licenses/components/radiance/LICENSE-rad5R4.txt`](components/radiance/LICENSE-rad5R4.txt)
- **Non-endorsement**: Neither "Radiance", "Lawrence Berkeley National Laboratory", nor
  "The Regents of the University of California" may be used to endorse or promote derived products
  without prior written permission.
- **Pruned binaries in Windows offline bundle**: `rvu.exe` and LGPL Qt5 runtime DLLs
  (`Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Widgets.dll`, `platforms/`, `imageformats/`) are excluded.

---

## 4. Evalglare 2.0 (`evalglare` {versions['evalglare']})

> {EVALGLARE_ATTRIBUTION}
>
> {RADIANCE_ATTRIBUTION}

- **License**: Evalglare Software License, Version 2.0 (`Copyright (c) 1995 - 2020 Fraunhofer ISE, EPFL`),
  bundled unmodified with Radiance {versions['radiance']} (`bin/evalglare.exe`).
  Verbatim license text: [`licenses/components/evalglare/LICENSE.txt`](components/evalglare/LICENSE.txt).
- **Non-endorsement**: The names "Evalglare", "EPFL", and "Fraunhofer ISE" must not be used to endorse
  or promote products derived from this software without prior written permission (`jan.wienold@epfl.ch`).

---

## 5. EnergyPlus version {versions['energyplus']}

- **Mandatory Software Designation**: This distribution includes unmodified **EnergyPlus version {versions['energyplus']}**
  bundled inside the OpenStudio(R) {versions['openstudio']} `EnergyPlus/` directory.
- **Non-Endorsement & Trademark Notice**: No endorsement by the U.S. Department of Energy (DOE),
  Lawrence Berkeley National Laboratory, the University of Illinois, Oak Ridge National Laboratory,
  Alliance for Energy Innovation, LLC, or EnergyPlus / E+ is implied or granted. Neither
  "EnergyPlus", "E+", nor "e+" is used in any company name, product name, or promotional designation
  without prior written consent.
- **DOE Government-Rights NOTICE & Full License**:
  Full EnergyPlus version {versions['energyplus']} license and U.S. Department of Energy NOTICE are preserved
  verbatim in [`licenses/components/energyplus/LICENSE.txt`](components/energyplus/LICENSE.txt) and
  [`licenses/components/energyplus/NOTICE.txt`](components/energyplus/NOTICE.txt):
  - *NOTICE*: This Software was developed under funding from the U.S. Department of Energy and the
    U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
    for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
    in the Software to reproduce, distribute copies to the public, prepare derivative works, and
    perform publicly and display publicly, and to permit others to do so.

---

## 6. OpenStudio(R) {versions['openstudio']}

- **License**: `BSD-3-Clause` with OpenStudio(R) trademark & non-endorsement conditions
  (`Copyright (c) 2008-2026, Alliance for Energy Innovation, LLC`).
  Verbatim license & third-party credits:
  [`licenses/components/openstudio/LICENSE.md`](components/openstudio/LICENSE.md) and
  [`licenses/components/openstudio/copyright.txt`](components/openstudio/copyright.txt).
- **Transparent Runtime Pruning & Integrity Disclosure**:
  - Retained in Standard Windows distribution: `bin/` (excluding `openstudiolib.lib`),
    `CSharp/openstudio/` (x64 C# bindings from NuGet `NREL.OpenStudio.win` `{versions['openstudio']}`,
    `BSD-3-Clause`; `x86/` omitted; NTFS-hardlinked into `runtimes/ironbug/{versions['ironbug']}/`
    during `lbt-mcp runtime sync`), and the **unmodified** `EnergyPlus/` subdirectory
    (`EnergyPlus version {versions['energyplus']}`).
  - Pruned non-runtime directories/files: `Python/`, `Perl/`, `Radiance/`, `include/`, `Examples/`, and
    `lib/openstudiolib.lib`.
  - `Ruby/`: omitted from the Standard Windows Installer and staged **only** when installing the optional
    URBANopt {versions['urbanopt']} `.lbtpack` extension pack.
  - Detailed breakdown: [`licenses/components/openstudio/PRUNING_NOTICE.txt`](components/openstudio/PRUNING_NOTICE.txt).

---

## 7. HygroThermFEM / Fairyfly Native (`pyhygrothermfem_fairyfly`)

All upstream notices and licenses copied verbatim from `src/pyhygrothermfem_fairyfly/third_party_notices.txt`
and `src/pyhygrothermfem_fairyfly/third_party_licenses/*/*`:

- **`pyHygroThermFEM-Fairyfly` wrapper & C++20 glue**: `BSD-3-Clause`
  ([`LICENSE-pyHygroThermFEM-Fairyfly.txt`](components/hygrothermfem_fairyfly/LICENSE-pyHygroThermFEM-Fairyfly.txt))
- **Combined Third-Party Notice**:
  [`third_party_notices.txt`](components/hygrothermfem_fairyfly/third_party_notices.txt)
- **LBNL `HygroThermFEM` (`v_1.0.80`)**: BSD-3-Clause LBNL variant with Enhancements clause & DOE NOTICE
  ([`third_party_licenses/HygroThermFEM/LICENSE`](components/hygrothermfem_fairyfly/third_party_licenses/HygroThermFEM/LICENSE))
- **LBNL `libraryfemtherm` (`{versions['libraryfemtherm']}`)**: BSD-3-Clause LBNL variant with Enhancements clause
  ([`libraryfemtherm/LICENSE`](components/hygrothermfem_fairyfly/libraryfemtherm/LICENSE))
- **LBNL `KeffCavity` (`Version_1.1.10`)**: BSD-3-Clause LBNL variant
  ([`third_party_licenses/KeffCavity/LICENSE`](components/hygrothermfem_fairyfly/third_party_licenses/KeffCavity/LICENSE))
- **LBNL `LBNLCPPCommon` (`v0.19`)**: BSD-3-Clause LBNL variant
  ([`third_party_licenses/LBNLCPPCommon/LICENSE`](components/hygrothermfem_fairyfly/third_party_licenses/LBNLCPPCommon/LICENSE))
- **LBNL `Windows-CalcEngine` (`Version_1.0.78`)**: BSD-3-Clause LBNL variant with DOE NOTICE
  ([`third_party_licenses/Windows-CalcEngine/License.txt`](components/hygrothermfem_fairyfly/third_party_licenses/Windows-CalcEngine/License.txt))
- **`Eigen`**: `MPL-2.0` (`COPYING.MPL2`, `LICENSE`) plus accompanying `COPYING.README`, `COPYING.BSD`,
  `COPYING.APACHE`, and `COPYING.MINPACK`
  ([`third_party_licenses/Eigen/`](components/hygrothermfem_fairyfly/third_party_licenses/Eigen/LICENSE))
- **`pybind11`**: `BSD-3-Clause`
  ([`third_party_licenses/pybind11/LICENSE`](components/hygrothermfem_fairyfly/third_party_licenses/pybind11/LICENSE))

---

## 8. Copyleft Binary Dependencies Requiring Corresponding Source

See [`licenses/CORRESPONDING_SOURCE.md`](CORRESPONDING_SOURCE.md) and
[`licenses/SOURCE_MANIFEST.json`](SOURCE_MANIFEST.json) for full source archive URLs, SHA-256 checksums,
and offline corresponding-source archive layout:

- **Gmsh `{versions['gmsh']}`**: `GPL-2.0-or-later` with Gmsh library exceptions
  ([`licenses/components/gmsh/LICENSE.txt`](components/gmsh/LICENSE.txt))
- **GEOS `{versions['geos']}`** (`shapely.libs/geos_c-*.dll`, `geos-*.dll`): `LGPL-2.1-only`
  ([`licenses/components/geos/COPYING`](components/geos/COPYING),
  [`licenses/components/geos/LICENSE_GEOS`](components/geos/LICENSE_GEOS))
- **Ironbug `{versions['ironbug']}`** (`ironbug-win-{versions['ironbug']}.zip`: `net48` `Ironbug.Console.exe`
  and `netstandard2.0` `Ironbug.HVAC.dll` / `Ironbug.Core.dll` / `Ironbug.EPDoc.dll`; `NREL.OpenStudio.win`
  `{versions['openstudio']}` `BSD-3-Clause` C# DLLs hardlinked from `runtimes/openstudio/{versions['openstudio']}/CSharp/openstudio/`):
  `LGPL-3.0` (`LGPL-3.0-or-later`)
  ([`licenses/components/ironbug/LICENSE`](components/ironbug/LICENSE))
- **Optional DES / OpenDSS (`dss_python_backend` / `KLUSolveX`)**: `LGPL-3.0` / `LGPL-2.1-or-later` /
  `BSD-3-Clause` (not bundled in the Standard installer; if distributed with optional DES/OpenDSS
  Python dependencies, corresponding source must accompany distribution). Verbatim licenses preserved under
  [`licenses/components/dss_opendss/`](components/dss_opendss/).

---

## 9. IronbugBridge / .NET 8 Sidecar (`src/ironbug_bridge`)

- **`Newtonsoft.Json` `{versions['newtonsoft_json']}`**: `MIT`
  ([`Newtonsoft.Json-LICENSE.md`](components/ironbug_bridge/Newtonsoft.Json-LICENSE.md))
- **`System.Security.Permissions` `{versions['system_security_permissions']}`** (and transitive
  `System.Windows.Extensions`): `MIT`
  ([`System.Security.Permissions-LICENSE.TXT`](components/ironbug_bridge/System.Security.Permissions-LICENSE.TXT))
- **Microsoft .NET 8 Runtime Distributable Code (Self-Contained App Bundling Only)**:
  The Microsoft .NET 8 runtime binaries (`coreclr.dll`, `hostfxr.dll`, BCL assemblies) are bundled
  exclusively inside the self-contained `IronbugBridge.exe` sidecar application and are NOT
  redistributed as a standalone runtime or linked into AGPL source code.
  License & third-party notices:
  [`MICROSOFT_DOTNET_LICENSE.txt`](components/ironbug_bridge/MICROSOFT_DOTNET_LICENSE.txt),
  [`MICROSOFT_DOTNET_THIRD_PARTY_NOTICES.txt`](components/ironbug_bridge/MICROSOFT_DOTNET_THIRD_PARTY_NOTICES.txt).

---

## 10. Rune 3D Viewer (`lbt-rune-viewer`)

- **`rune_viewer` Workspace Crates** (`lbt-scene`, `lbt-renderer-wgpu`, `lbt-mcp-bridge`,
  `lbt-viewer-app`): `GPL-3.0-or-later`.
- **Vendored `vendor/rune` UI Toolkit**: `MIT`
  ([`licenses/components/rune_viewer/LICENSE`](components/rune_viewer/LICENSE)) and
  [`THIRD_PARTY_NOTICES.md`](components/rune_viewer/THIRD_PARTY_NOTICES.md)
  (KaTeX fonts under `OFL-1.1`, RaTeX under `MIT`, `unicode-normalization`, `wasmi`).
- **Font Licenses**:
  [`OFL.txt`](components/rune_viewer/OFL.txt),
  [`FONT_NOTICE.txt`](components/rune_viewer/FONT_NOTICE.txt),
  [`Inter-LICENSE.txt`](components/rune_viewer/Inter-LICENSE.txt),
  [`IBMPlexMono-LICENSE.txt`](components/rune_viewer/IBMPlexMono-LICENSE.txt).
- **Cargo Workspace Crate License Summary**:
  [`CARGO_CRATE_LICENSES.md`](components/rune_viewer/CARGO_CRATE_LICENSES.md).

---

## 11. Python 3.12 (`python-build-standalone` `{versions['python']}`) & `setuptools` (`{versions['setuptools']}`)

- **Python `{versions['python']}`**: `PSF-2.0` (Python Software Foundation License Version 2)
  ([`licenses/components/python/LICENSE.txt`](components/python/LICENSE.txt)).
- **Windows Dependency Note**: This Windows build contains **no GPL `readline` or `gdbm` libraries**.
- **`setuptools` `{versions['setuptools']}`**: `MIT` (runtime `distutils` compatibility shim required by
  `queenbee-local` on Python 3.12; [`licenses/components/setuptools/LICENSE`](components/setuptools/LICENSE)).

---

## 12. Optional URBANopt `{versions['urbanopt']}` Pack (`.lbtpack`)

Distributed separately as an optional extension pack (`lbt-mcp-{project_version}-win-x64-urbanopt.lbtpack`):

- **Ruby Runtime**: `BSD-2-Clause` / RubyInstaller Modified BSD
  ([`RUBY_LICENSE.txt`](components/urbanopt/RUBY_LICENSE.txt),
  [`RUBY_BSDL.txt`](components/urbanopt/RUBY_BSDL.txt)); `ruby/msys64/` DevKit is pruned from the pack.
- **URBANopt CLI `{versions['urbanopt']}`**: `BSD-3-Clause`
  ([`URBANOPT_CLI_LICENSE.md`](components/urbanopt/URBANOPT_CLI_LICENSE.md)).
- **OpenStudio(R) Runtime Gems & `OpenStudio/Ruby`**: `BSD-3-Clause`
  ([`OPENSTUDIO_GEMS_LICENSE.md`](components/urbanopt/OPENSTUDIO_GEMS_LICENSE.md)).
"""


def _render_corresponding_source(
    *,
    manifest: dict[str, Any],
    versions: dict[str, str],
) -> str:
    rows: list[str] = []
    for entry in manifest["entries"]:
        sha = entry.get("sha256") or "*(resolved at offline build / see `SOURCE_MANIFEST.json`)*"
        archive = entry.get("archive_name") or entry.get("source_type")
        optional_tag = "Yes" if entry.get("bundled_in_standard") else "Optional (only if distributed)"
        rows.append(
            f"| `{entry['id']}` | `{entry['version']}` | `{entry['license']}` | "
            f"{optional_tag} | `{archive}` | `{sha}` |"
        )
    table = "\n".join(rows)

    return f"""# Corresponding Source Notice & Inventory (`{manifest['project']}` {manifest['version']})

Under the terms of the **GNU Affero General Public License v3.0 (`AGPL-3.0-only`)**, **GNU General Public
License (`GPL-3.0-or-later`, `GPL-2.0-or-later`)**, and **GNU Lesser General Public License (`LGPL-3.0`,
`LGPL-2.1-only`)**, the machine-readable Corresponding Source for `{manifest['project']}` and its
copyleft binary dependencies is provided via:

1. **Offline Release Archive**: `{manifest['corresponding_source_archive']}` (distributed alongside
   the Windows offline installer), containing:
   - The full `{manifest['project']}` source tree (matching `MANIFEST.in`: `LICENSE`, `pyproject.toml`,
     `MANIFEST.in`, `src/`, `rune_viewer/`, `vendor/rune/`, `src/ironbug_bridge/`,
     `src/pyhygrothermfem_native/`, `vendor/pyHygroThermFEM-Fairyfly/`,
     `scripts/distribution/launcher/`, and `licenses/`).
   - Upstream source tarballs for bundled copyleft binary dependencies (`gmsh` `{versions['gmsh']}`,
     `GEOS` `{versions['geos']}`, `Ironbug` `{versions['ironbug']}` — `ironbug-win-{versions['ironbug']}.zip`
     `net48` `Ironbug.Console.exe` + `netstandard2.0` `Ironbug.*.dll`, paired with `BSD-3-Clause`
     `NREL.OpenStudio.win` `{versions['openstudio']}` C# DLLs hardlinked from
     `runtimes/openstudio/{versions['openstudio']}/CSharp/openstudio/`).
   - Machine-readable source inventory [`licenses/SOURCE_MANIFEST.json`](SOURCE_MANIFEST.json).
2. **Upstream Source Repositories & Written Offer**:
   - `{manifest['project']}`: {DEFAULT_URLS['lbt_mcp_repo']}
   - `gmsh` `{versions['gmsh']}`: {DEFAULT_URLS['gmsh_source']}
   - `GEOS` `{versions['geos']}`: {DEFAULT_URLS['geos_source']}
   - `Ironbug` `{versions['ironbug']}`: {DEFAULT_URLS['ironbug_source']}
   - Optional DES / OpenDSS (`dss_python_backend` / `KLUSolveX`, if distributed):
     {DEFAULT_URLS['dss_python_backend_repo']}, {DEFAULT_URLS['dss_capi_repo']}, {DEFAULT_URLS['klusolvex_repo']}

## Corresponding Source Matrix

| Component | Version | License | Bundled in Standard Installer | Source Packaging / Archive | SHA-256 |
|---|---|---|---|---|---|
{table}

> Note: Permissively licensed or non-copyleft runtime components (such as `OpenStudio(R)` `{versions['openstudio']}`
> `BSD-3-Clause`, unmodified `EnergyPlus version {versions['energyplus']}`, `Radiance` `{versions['radiance']}`,
> `Evalglare` 2.0, `Python` `{versions['python']}` `PSF-2.0`, and optional `URBANopt` `{versions['urbanopt']}`
> `BSD-2-Clause`/`BSD-3-Clause`) keep their verbatim licenses and notices in
> [`licenses/THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`licenses/components/`](components/).
"""


def generate_licenses(
    *,
    output_dir: Path,
    bundle_manifest: Path | None = None,
    source_manifest_only: bool = False,
    allow_remote: bool = False,
) -> dict[str, Any]:
    """Generate license notices, component license copies, and SOURCE_MANIFEST.json into output_dir."""
    output_dir = output_dir.resolve()
    licenses_dir = output_dir / "licenses"
    licenses_dir.mkdir(parents=True, exist_ok=True)

    project_name, project_version = _read_project_meta()
    pins = _read_requirements_pins()
    versions = _detect_installed_versions(pins)

    if bundle_manifest is None:
        default_manifest = REPO_ROOT / "scripts" / "distribution" / "runtime_manifest.windows-x64.json"
        if default_manifest.is_file():
            bundle_manifest = default_manifest

    ver_overrides, archive_overrides = _load_bundle_manifest(bundle_manifest)
    versions.update(ver_overrides)

    manifest = _build_source_manifest(
        project_name=project_name,
        project_version=project_version,
        versions=versions,
        archive_overrides=archive_overrides,
    )

    if not source_manifest_only:
        if output_dir != REPO_ROOT.resolve():
            shutil.copy2(REPO_ROOT / "LICENSE", output_dir / "LICENSE")
        _stage_component_licenses(
            components_dir=licenses_dir / "components",
            repo_components_dir=REPO_ROOT / "licenses" / "components",
            versions=versions,
            allow_remote=allow_remote,
        )
        (licenses_dir / "THIRD_PARTY_NOTICES.md").write_text(
            _render_third_party_notices(
                project_name=project_name,
                project_version=project_version,
                versions=versions,
            ),
            encoding="utf-8",
            newline="\n",
        )
        (licenses_dir / "CORRESPONDING_SOURCE.md").write_text(
            _render_corresponding_source(manifest=manifest, versions=versions),
            encoding="utf-8",
            newline="\n",
        )

    (licenses_dir / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT,
        help="Target directory receiving licenses/ (and root LICENSE when targeting a staging dir).",
    )
    parser.add_argument(
        "--bundle-manifest",
        type=Path,
        default=None,
        help="Optional runtime/bundle manifest JSON for version and SHA-256 alignment.",
    )
    parser.add_argument(
        "--source-manifest-only",
        action="store_true",
        help="Write only <output-dir>/licenses/SOURCE_MANIFEST.json.",
    )
    parser.add_argument(
        "--fetch-remote",
        action="store_true",
        help="Fetch missing upstream license texts over HTTPS if absent locally.",
    )
    args = parser.parse_args(argv)
    manifest = generate_licenses(
        output_dir=args.output_dir,
        bundle_manifest=args.bundle_manifest,
        source_manifest_only=args.source_manifest_only,
        allow_remote=args.fetch_remote,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "source_manifest_only": args.source_manifest_only,
                "entries": [entry["id"] for entry in manifest["entries"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
