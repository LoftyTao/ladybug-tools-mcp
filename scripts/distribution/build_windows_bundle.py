#!/usr/bin/env python3
"""Build the reproducible Windows x64 offline bundle, optional URBANopt .lbtpack, and Inno Setup installer."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tomllib
from typing import Any
import urllib.request
from zipfile import ZIP_LZMA, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "distribution" / "runtime_manifest.windows-x64.json"
DEFAULT_CACHE_DIR = REPO_ROOT / "build" / "offline-cache"
DEFAULT_STAGING_DIR = REPO_ROOT / "build" / "windows-offline-staging"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist" / "windows-offline"
DEFAULT_ISS_PATH = REPO_ROOT / "scripts" / "distribution" / "lbt_mcp_windows.iss"
DEFAULT_URBANOPT_DIR = Path(r"C:\URBANopt-cli-1.4.0-rc1")

OPENSTUDIO_CSHARP_DUPLICATE_NAMES = {
    "OpenStudio.dll",
    "openstudiolib.dll",
    "openstudio_csharp.dll",
    "openstudio_model_csharp.dll",
    "openstudio_translators_csharp.dll",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_stats(root: Path) -> dict[str, int]:
    if not root.exists():
        return {"files": 0, "bytes": 0}
    files = 0
    total = 0
    for item in root.rglob("*"):
        if item.is_file() and not item.is_symlink():
            files += 1
            total += item.stat().st_size
    return {"files": files, "bytes": total}


def _read_project_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _inject_tls_store() -> None:
    try:
        import truststore  # type: ignore[import-not-found]

        truststore.inject_into_ssl()
    except Exception:
        pass


def ensure_cached_file(
    *,
    cache_dir: Path,
    relpath: str,
    url: str,
    expected_sha256: str | None = None,
    skip_downloads: bool = False,
) -> Path:
    """Return verified cached archive path, downloading into cache_dir if absent."""
    dest = (cache_dir / relpath).resolve()
    if not dest.is_relative_to(cache_dir.resolve()):
        raise ValueError(f"Cache path escapes cache directory: {relpath}")

    if dest.is_file():
        if expected_sha256:
            actual = _sha256_file(dest)
            if actual.lower() == expected_sha256.lower():
                return dest
            if skip_downloads:
                raise RuntimeError(
                    f"Cached file SHA-256 mismatch for {dest}: expected {expected_sha256}, got {actual}"
                )
            dest.unlink()
        else:
            return dest

    if skip_downloads:
        raise FileNotFoundError(f"Missing offline cache file (--skip-downloads): {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    _inject_tls_store()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    print(f"Downloading {relpath} from {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "lbt-mcp-windows-bundler/1.0"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while chunk := resp.read(1024 * 1024):
            out.write(chunk)
            digest.update(chunk)
    actual_sha = digest.hexdigest()
    if expected_sha256 and actual_sha.lower() != expected_sha256.lower():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Downloaded {relpath} failed SHA-256 verification: expected {expected_sha256}, got {actual_sha}"
        )
    tmp.replace(dest)
    return dest


def _safe_tar_dest(root: Path, rel_posix: str) -> Path:
    pure = PurePosixPath(rel_posix)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Unsafe tar member path: {rel_posix!r}")
    dest = (root / pure.as_posix()).resolve()
    root_res = root.resolve()
    if dest != root_res and not dest.is_relative_to(root_res):
        raise ValueError(f"Tar member escapes destination: {rel_posix!r}")
    return dest


def _safe_zip_dest(root: Path, rel_posix: str) -> Path:
    return _safe_tar_dest(root, rel_posix)


def _find_iscc() -> Path | None:
    on_path = shutil.which("ISCC.exe") or shutil.which("iscc")
    if on_path:
        return Path(on_path).resolve()
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    ]
    for cand in candidates:
        if str(cand) and cand.is_file():
            return cand.resolve()
    return None


def _ensure_rune_viewer_artifacts() -> None:
    """Ensure lbt-rune-viewer.exe and Rune web WASM assets are built."""
    cargo = shutil.which("cargo")
    rune_dir = REPO_ROOT / "rune_viewer"
    exe_path = rune_dir / "target" / "release" / "lbt-rune-viewer.exe"
    if not cargo and not exe_path.is_file():
        raise RuntimeError("Neither `cargo` nor prebuilt rune_viewer/target/release/lbt-rune-viewer.exe found.")
    if cargo:
        print("Building lbt-rune-viewer.exe (release)...", flush=True)
        subprocess.run(
            [cargo, "build", "--release", "-p", "lbt-viewer-app", "--bin", "lbt-rune-viewer"],
            cwd=str(rune_dir),
            check=True,
        )
    if not exe_path.is_file():
        raise FileNotFoundError(f"Missing built Rune viewer binary: {exe_path}")

    web_dir = rune_dir / "target" / "web"
    if not ((web_dir / "app_bg.wasm").is_file() and (web_dir / "index.html").is_file()):
        print("Building Rune web WASM bundle via scripts/build_rune_web.py...", flush=True)
        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "build_rune_web.py")], cwd=str(REPO_ROOT), check=True)
    if not ((web_dir / "app_bg.wasm").is_file() and (web_dir / "index.html").is_file()):
        raise FileNotFoundError(f"Missing Rune web WASM assets in {web_dir}")


def _build_wheel(wheelhouse_dir: Path, version: str) -> Path:
    """Build release wheel with native HygroThermFEM, self-contained IronbugBridge, and Rune viewer."""
    if wheelhouse_dir.exists():
        shutil.rmtree(wheelhouse_dir)
    wheelhouse_dir.mkdir(parents=True, exist_ok=True)

    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("`uv` is required on PATH to build the release wheel.")

    env = dict(os.environ)
    env["LBT_MCP_REQUIRE_HYGROTHERM_NATIVE"] = "1"
    env["LBT_MCP_REQUIRE_IRONBUG_BRIDGE"] = "1"
    env["LBT_MCP_SELF_CONTAINED_IRONBUG_BRIDGE"] = "1"
    env["LBT_MCP_REQUIRE_RUNE_VIEWER"] = "1"

    print("Building lbt-mcp wheel (native solver + self-contained IronbugBridge + Rune viewer)...", flush=True)
    subprocess.run(
        [
            uv,
            "build",
            "--wheel",
            "--python",
            "3.12",
            "--out-dir",
            str(wheelhouse_dir),
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
    )
    wheels = sorted(wheelhouse_dir.glob(f"lbt_mcp-{version}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected 1 built wheel for version {version} in {wheelhouse_dir}, found: {wheels}")

    wheel = wheels[0]
    with ZipFile(wheel, "r") as zf:
        names = set(zf.namelist())
    required = {
        "ladybug_tools_mcp/resources/ironbug_bridge/IronbugBridge.exe",
        "ladybug_tools_mcp/resources/ironbug_bridge/IronbugBridge.dll",
        "ladybug_tools_mcp/resources/ironbug_bridge/coreclr.dll",
        "ladybug_tools_mcp/resources/ironbug_bridge/hostfxr.dll",
        "ladybug_tools_mcp/resources/rune_viewer/lbt-rune-viewer.exe",
        "ladybug_tools_mcp/resources/rune_viewer/web/app_bg.wasm",
        "ladybug_tools_mcp/resources/rune_viewer/web/index.html",
        "ladybug_tools_mcp/resources/grasshopper/manifest.json",
        "pyhygrothermfem_fairyfly/_build_source.json",
    }
    missing = sorted(required - names)
    if missing:
        raise RuntimeError(f"Built wheel {wheel.name} is missing required bundled artifacts: {missing}")
    if not any(n.startswith("pyhygrothermfem_fairyfly/_native.") and n.endswith(".pyd") for n in names):
        raise RuntimeError(f"Built wheel {wheel.name} is missing compiled pyhygrothermfem_fairyfly._native*.pyd")
    return wheel


def _build_launcher(staging_dir: Path) -> Path:
    cargo = shutil.which("cargo")
    launcher_dir = REPO_ROOT / "scripts" / "distribution" / "launcher"
    if not (launcher_dir / "Cargo.toml").is_file():
        raise FileNotFoundError(f"Missing launcher Cargo project: {launcher_dir}")
    if not cargo:
        raise RuntimeError("`cargo` is required on PATH to build bin/lbt-mcp.exe.")
    print("Building Rust launcher bin/lbt-mcp.exe...", flush=True)
    subprocess.run([cargo, "build", "--release"], cwd=str(launcher_dir), check=True)
    built = launcher_dir / "target" / "release" / "lbt-mcp.exe"
    if not built.is_file():
        raise FileNotFoundError(f"Launcher build succeeded without producing {built}")
    dest = staging_dir / "bin" / "lbt-mcp.exe"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, dest)
    return dest


def _stage_portable_python(python_archive: Path, staging_dir: Path, py_ver: str) -> tuple[Path, dict[str, int]]:
    target = staging_dir / "runtimes" / "python" / py_ver
    target.mkdir(parents=True, exist_ok=True)
    raw_bytes = 0
    raw_files = 0
    with tarfile.open(python_archive, "r:gz") as tf:
        for member in tf.getmembers():
            raw_files += 1 if member.isfile() else 0
            raw_bytes += member.size if member.isfile() else 0
            norm = member.name.replace("\\", "/").lstrip("./")
            if norm.startswith("python/"):
                rel = norm[len("python/") :]
            elif norm == "python":
                continue
            else:
                rel = norm
            if not rel:
                continue
            dest = _safe_tar_dest(target, rel)
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                assert src is not None
                with dest.open("wb") as out:
                    shutil.copyfileobj(src, out)
    py_exe = target / "python.exe"
    if not py_exe.is_file():
        raise FileNotFoundError(f"Portable Python extraction missing {py_exe}")
    return py_exe, {"raw_files": raw_files, "raw_bytes": raw_bytes}


def _prune_venv(venv_dir: Path) -> dict[str, Any]:
    sp_dir = venv_dir / "Lib" / "site-packages"
    removed_paths: list[str] = []
    removed_bytes = 0

    for entry in sorted(sp_dir.iterdir()):
        name_low = entry.name.lower()
        is_cuda_noise = (
            name_low.startswith("cupy")
            or name_low.startswith("fastrlock")
        )
        if not is_cuda_noise:
            continue
        if entry.is_dir():
            stats = _dir_stats(entry)
            removed_bytes += stats["bytes"]
            shutil.rmtree(entry)
        elif entry.is_file():
            removed_bytes += entry.stat().st_size
            entry.unlink()
        removed_paths.append(entry.name)

    pdb_count = 0
    for pdb_file in sorted(venv_dir.rglob("*.pdb")):
        if pdb_file.is_file():
            removed_bytes += pdb_file.stat().st_size
            pdb_file.unlink()
            pdb_count += 1

    return {
        "pruned_packages": removed_paths,
        "pruned_pdb_files": pdb_count,
        "pruned_bytes": removed_bytes,
    }


def _build_isolated_venv(
    *,
    portable_python: Path,
    staging_dir: Path,
    version: str,
    wheel_path: Path,
) -> tuple[Path, dict[str, Any]]:
    venv_dir = staging_dir / "app" / "releases" / version / "venv"
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("`uv` is required on PATH to prepare isolated release venv.")

    print(f"Creating relocatable venv at {venv_dir}...", flush=True)
    subprocess.run(
        [uv, "venv", "--python", str(portable_python), "--relocatable", str(venv_dir)],
        check=True,
    )
    venv_python = venv_dir / "Scripts" / "python.exe"
    if not venv_python.is_file():
        raise FileNotFoundError(f"Missing venv Python executable: {venv_python}")

    install_cmd = [
        uv,
        "pip",
        "install",
        "--python",
        str(venv_python),
        "--prerelease",
        "allow",
    ]
    req_txt = REPO_ROOT / "requirements.txt"
    if req_txt.is_file():
        install_cmd.extend(["-r", str(req_txt)])
    # queenbee-local==1.0.3 imports distutils.dir_util.copy_tree (removed in Python 3.12 stdlib).
    install_cmd.extend(["setuptools", str(wheel_path)])

    print("Installing wheel + pinned dependencies into isolated venv...", flush=True)
    subprocess.run(install_cmd, cwd=str(REPO_ROOT), check=True)

    raw_stats = _dir_stats(venv_dir)
    prune_info = _prune_venv(venv_dir)
    pruned_stats = _dir_stats(venv_dir)

    # Verify honeybee_radiance_postprocess imports cleanly with zero stderr (no CuPy/CUDA warning).
    probe = subprocess.run(
        [
            str(venv_python),
            "-I",
            "-c",
            (
                "import honeybee_radiance_postprocess as p, "
                "queenbee_local, "
                "pyhygrothermfem_fairyfly._native as n, "
                "gmsh, shapely, openstudio, ladybug_tools_mcp; "
                "assert p.IS_CPU and not p.IS_GPU; "
                "print(openstudio.openStudioVersion())"
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"Isolated venv verification failed (rc={probe.returncode}):\n"
            f"stdout={probe.stdout}\nstderr={probe.stderr}"
        )
    if probe.stderr.strip():
        raise RuntimeError(
            f"Isolated venv import emitted unexpected stderr noise:\n{probe.stderr}"
        )

    # Verify console script .exe launchers are relocatable (must not embed staging path).
    staging_marker = str(staging_dir).lower().encode("utf-8")
    for script_exe in sorted((venv_dir / "Scripts").glob("*.exe")):
        if script_exe.name.lower() in {"python.exe", "pythonw.exe"}:
            continue
        raw = script_exe.read_bytes()
        shebang_idx = raw.rfind(b"#!")
        if shebang_idx < 0:
            continue
        shebang_line = raw[shebang_idx : raw.find(b"\n", shebang_idx) if b"\n" in raw[shebang_idx:] else len(raw)]
        if staging_marker in shebang_line.lower() or b":\\" in shebang_line:
            raise RuntimeError(
                f"Non-relocatable shebang in {script_exe.name}: {shebang_line!r}"
            )
    hb_cli = venv_dir / "Scripts" / "honeybee-energy.exe"
    if not hb_cli.is_file():
        raise FileNotFoundError(f"Expected console entrypoint missing: {hb_cli}")
    hb_probe = subprocess.run([str(hb_cli), "--version"], capture_output=True, text=True, check=False)
    if hb_probe.returncode != 0:
        raise RuntimeError(f"honeybee-energy.exe --version failed: {hb_probe.stderr}")

    return venv_python, {
        "raw": raw_stats,
        "pruned": pruned_stats,
        "prune_details": prune_info,
        "openstudio_python_version": probe.stdout.strip(),
    }


def _stage_openstudio(
    *,
    openstudio_archive: Path,
    csharp_nupkg: Path,
    staging_dir: Path,
    os_ver: str,
) -> dict[str, Any]:
    target = staging_dir / "runtimes" / "openstudio" / os_ver
    target.mkdir(parents=True, exist_ok=True)
    raw_files = 0
    raw_bytes = 0
    ep_source_hashes: dict[str, str] = {}
    pruned_dirs: set[str] = set()

    print(f"Staging OpenStudio {os_ver} (bin/ + unmodified EnergyPlus/)...", flush=True)
    with tarfile.open(openstudio_archive, "r:gz") as tf:
        for member in tf.getmembers():
            norm = member.name.replace("\\", "/").lstrip("./")
            parts = norm.split("/")
            if len(parts) < 2:
                continue
            rel = "/".join(parts[1:])
            if member.isfile():
                raw_files += 1
                raw_bytes += member.size

            top = rel.split("/", 1)[0]
            if top in {"Python", "Ruby", "Radiance", "Perl", "include", "Examples", "lib"}:
                pruned_dirs.add(top)
                continue
            if top == "bin":
                if Path(rel).name.lower() == "openstudiolib.lib" or rel.lower().endswith(".pdb"):
                    continue
            elif top == "EnergyPlus":
                pass
            elif rel in {"LICENSE.md", "copyright.txt"}:
                pass
            else:
                continue

            dest = _safe_tar_dest(target, rel)
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                assert src is not None
                data = src.read()
                dest.write_bytes(data)
                if top == "EnergyPlus":
                    ep_rel = rel[len("EnergyPlus/") :]
                    ep_source_hashes[ep_rel] = hashlib.sha256(data).hexdigest()

    # Stage official NREL.OpenStudio.win 3.11.0 x64 C# bindings into CSharp/openstudio/
    csharp_dir = target / "CSharp" / "openstudio"
    csharp_dir.mkdir(parents=True, exist_ok=True)
    csharp_prefix = "build/netstandard2.0/x64/"
    csharp_files: list[str] = []
    with ZipFile(csharp_nupkg, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.filename.startswith(csharp_prefix):
                fname = Path(info.filename).name
                dest = _safe_zip_dest(csharp_dir, fname)
                dest.write_bytes(zf.read(info.filename))
                csharp_files.append(fname)

    if "OpenStudio.dll" not in csharp_files:
        raise RuntimeError(f"NREL.OpenStudio.win nupkg missing OpenStudio.dll in {csharp_prefix}")

    # Verify EnergyPlus integrity 100% matches archive
    ep_target = target / "EnergyPlus"
    actual_ep = {
        p.relative_to(ep_target).as_posix(): _sha256_file(p)
        for p in sorted(ep_target.rglob("*"))
        if p.is_file()
    }
    if actual_ep != ep_source_hashes or not actual_ep:
        raise RuntimeError("Staged EnergyPlus/ verification mismatch against OpenStudio archive.")

    pruned_stats = _dir_stats(target)
    return {
        "raw": {"files": raw_files, "bytes": raw_bytes},
        "pruned": pruned_stats,
        "pruned_top_dirs": sorted(pruned_dirs),
        "energyplus_file_count": len(actual_ep),
        "energyplus_integrity_verified": True,
        "csharp_files": sorted(csharp_files),
    }


def _stage_radiance(radiance_archive: Path, staging_dir: Path, rad_ver: str) -> dict[str, Any]:
    target = staging_dir / "runtimes" / "radiance" / rad_ver
    target.mkdir(parents=True, exist_ok=True)
    raw_files = 0
    raw_bytes = 0
    pruned_entries: list[str] = []

    print(f"Staging Radiance {rad_ver} (pruning rvu.exe and Qt5 LGPL DLLs)...", flush=True)
    with ZipFile(radiance_archive, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw_files += 1
            raw_bytes += info.file_size
            norm = info.filename.replace("\\", "/").lstrip("./")
            lower = norm.lower()
            base_lower = Path(norm).name.lower()
            if (
                lower == "bin/rvu.exe"
                or (lower.startswith("bin/qt5") and base_lower.endswith(".dll"))
                or lower == "bin/qt.conf"
                or lower.startswith("bin/plugins/platforms/")
                or lower.startswith("bin/plugins/imageformats/")
            ):
                pruned_entries.append(norm)
                continue
            dest = _safe_zip_dest(target, norm)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info.filename))

    if not (target / "bin" / "rad.exe").is_file() or not (target / "bin" / "evalglare.exe").is_file():
        raise FileNotFoundError(f"Staged Radiance missing expected binaries in {target / 'bin'}")

    return {
        "raw": {"files": raw_files, "bytes": raw_bytes},
        "pruned": _dir_stats(target),
        "pruned_count": len(pruned_entries),
    }


def _stage_lbt_measures(
    *,
    measures_archive: Path,
    gem_archive: Path,
    staging_dir: Path,
) -> dict[str, Any]:
    measures_dir = staging_dir / "runtimes" / "lbt_home" / "resources" / "measures"
    measures_dir.mkdir(parents=True, exist_ok=True)

    print("Staging LBT Measures + honeybee_openstudio_gem...", flush=True)
    with tarfile.open(measures_archive, "r:gz") as tf:
        for member in tf.getmembers():
            norm = member.name.replace("\\", "/").lstrip("./")
            marker = "/lib/"
            if marker not in norm:
                continue
            rel = norm.split(marker, 1)[1]
            if not rel:
                continue
            dest = _safe_tar_dest(measures_dir, rel)
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                assert src is not None
                with dest.open("wb") as out:
                    shutil.copyfileobj(src, out)

    gem_lib_dir = measures_dir / "honeybee_openstudio_gem" / "lib"
    gem_lib_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(gem_archive, "r:gz") as tf:
        for member in tf.getmembers():
            norm = member.name.replace("\\", "/").lstrip("./")
            marker = "/lib/"
            if marker not in norm:
                continue
            rel = norm.split(marker, 1)[1]
            if not rel:
                continue
            dest = _safe_tar_dest(gem_lib_dir, rel)
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                assert src is not None
                with dest.open("wb") as out:
                    shutil.copyfileobj(src, out)

    for expected in (
        measures_dir / "efficiency_standard",
        measures_dir / "inject_idf",
        measures_dir / "openstudio_results",
        measures_dir / "view_data",
        measures_dir / "honeybee_adapter.rb",
        gem_lib_dir / "honeybee.rb",
    ):
        if not expected.exists():
            raise FileNotFoundError(f"Expected staged LBT measure asset missing: {expected}")

    return _dir_stats(measures_dir)


def _stage_ironbug(ironbug_archive: Path, staging_dir: Path, ib_ver: str) -> dict[str, Any]:
    target = staging_dir / "runtimes" / "ironbug" / ib_ver
    target.mkdir(parents=True, exist_ok=True)
    raw_files = 0
    raw_bytes = 0

    print(f"Staging Ironbug {ib_ver}...", flush=True)
    with ZipFile(ironbug_archive, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw_files += 1
            raw_bytes += info.file_size
            norm = info.filename.replace("\\", "/").lstrip("./")
            rel = norm[len("ironbug/") :] if norm.startswith("ironbug/") else norm
            if not rel:
                continue
            if Path(rel).name in OPENSTUDIO_CSHARP_DUPLICATE_NAMES:
                continue
            dest = _safe_zip_dest(target, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info.filename))

    for required in ("Ironbug.HVAC.dll", "Ironbug.EPDoc.dll", "Ironbug.Core.dll", "Ironbug.Console.exe"):
        if not (target / required).is_file():
            raise FileNotFoundError(f"Staged Ironbug missing required binary: {target / required}")

    return {"raw": {"files": raw_files, "bytes": raw_bytes}, "pruned": _dir_stats(target)}


def _stage_skills_and_metadata(
    *,
    staging_dir: Path,
    version: str,
    wheel_path: Path,
    manifest: dict[str, Any],
) -> None:
    targets_ver = manifest["target_versions"]
    skill_rel = f"app/releases/{version}/skills/ladybug-tools-mcp-use"
    rel_skill_dir = staging_dir / skill_rel
    cur_skill_dir = staging_dir / "app" / "current" / "skills" / "ladybug-tools-mcp-use"

    repo_skill = REPO_ROOT / ".agents" / "skills" / "ladybug-tools-mcp-use"
    if repo_skill.is_dir():
        shutil.copytree(
            repo_skill,
            rel_skill_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("AGENTS.md", "__pycache__", "*.pyc"),
        )
        shutil.copytree(
            repo_skill,
            cur_skill_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("AGENTS.md", "__pycache__", "*.pyc"),
        )
    else:
        with ZipFile(wheel_path, "r") as zf:
            prefix = "ladybug_tools_mcp/resources/skills/ladybug-tools-mcp-use/"
            skill_entries = [n for n in zf.namelist() if n.startswith(prefix) and not n.endswith("/")]
            for entry in skill_entries:
                sub = entry[len(prefix) :]
                data = zf.read(entry)
                for base in (rel_skill_dir, cur_skill_dir):
                    dest = _safe_zip_dest(base, sub)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)

    current_json = {
        "schema_version": 1,
        "version": version,
        "release_dir": f"app/releases/{version}",
        "python": f"app/releases/{version}/venv/Scripts/python.exe",
        "python_home": f"runtimes/python/{targets_ver['python']}",
        "site_packages": f"app/releases/{version}/venv/Lib/site-packages",
        "skills_dir": skill_rel,
    }
    (staging_dir / "app" / "current.json").parent.mkdir(parents=True, exist_ok=True)
    (staging_dir / "app" / "current.json").write_text(
        json.dumps(current_json, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    default_runtime = {
        "schema_version": 1,
        "ladybug_tools_folder": "runtimes/lbt_home",
        "default_epw_folder": "",
        "default_simulation_folder": "",
        "default_standards_folder": "",
        "openstudio_path": f"runtimes/openstudio/{targets_ver['openstudio']}/bin",
        "energyplus_path": f"runtimes/openstudio/{targets_ver['openstudio']}/EnergyPlus",
        "radiance_path": f"runtimes/radiance/{targets_ver['radiance']}",
        "ironbug_path": f"runtimes/ironbug/{targets_ver['ironbug']}",
        "openstudio_csharp_path": f"runtimes/openstudio/{targets_ver['openstudio']}/CSharp/openstudio",
        "lbt_measures_path": "runtimes/lbt_home/resources/measures",
        "standards_data_folder": "",
        "standards_extension_folders": [],
        "defaults_file": "",
        "mapper_path": "",
        "urbanopt_gemfile_path": "",
        "urbanopt_cli_path": "",
        "urbanopt_env_path": "",
        "reopt_assumptions_path": "",
        "python_home": f"runtimes/python/{targets_ver['python']}",
    }
    (staging_dir / "config").mkdir(parents=True, exist_ok=True)
    (staging_dir / "config" / "runtime.json").write_text(
        json.dumps(default_runtime, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _stage_licenses(staging_dir: Path, manifest_path: Path) -> None:
    print("Generating LICENSE and licenses/ inside staging directory...", flush=True)
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "distribution" / "generate_licenses.py"),
            "--output-dir",
            str(staging_dir),
            "--bundle-manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        check=True,
    )
    if not (staging_dir / "LICENSE").is_file() or not (staging_dir / "licenses" / "THIRD_PARTY_NOTICES.md").is_file():
        raise FileNotFoundError("generate_licenses.py failed to populate LICENSE or licenses/THIRD_PARTY_NOTICES.md")


def _resolve_urbanopt_dir(
    *,
    explicit_dir: Path | None,
    cache_dir: Path,
    manifest: dict[str, Any],
    skip_downloads: bool,
) -> Path | None:
    if explicit_dir is not None:
        resolved = explicit_dir.expanduser().resolve()
        if not resolved.is_dir():
            raise FileNotFoundError(f"--urbanopt-dir does not exist: {resolved}")
        return resolved

    if DEFAULT_URBANOPT_DIR.is_dir():
        return DEFAULT_URBANOPT_DIR

    uo_meta = manifest["runtimes"]["urbanopt"]
    installer = ensure_cached_file(
        cache_dir=cache_dir,
        relpath=uo_meta["filename"],
        url=uo_meta["url"],
        expected_sha256=uo_meta["sha256"],
        skip_downloads=skip_downloads,
    )
    unpacked_dir = cache_dir / "urbanopt-unpacked-1.4.0-rc1"
    if (unpacked_dir / "gems" / "Gemfile").is_file() and (unpacked_dir / "ruby" / "bin" / "ruby.exe").is_file():
        return unpacked_dir

    # Qt Installer Framework silent unattended install into cache subdir (non-interactive)
    print(f"Installing URBANopt CLI into cache dir {unpacked_dir} for .lbtpack packaging...", flush=True)
    if unpacked_dir.exists():
        shutil.rmtree(unpacked_dir)
    subprocess.run(
        [
            str(installer),
            "install",
            "--root",
            str(unpacked_dir),
            "--accept-licenses",
            "--default-answer",
            "--confirm-command",
        ],
        check=True,
    )
    if not (unpacked_dir / "gems" / "Gemfile").is_file():
        raise RuntimeError(
            f"URBANopt unattended extraction did not produce {unpacked_dir / 'gems' / 'Gemfile'}. "
            "Pass --urbanopt-dir pointing to an installed URBANopt-cli-1.4.0-rc1 directory."
        )
    return unpacked_dir


def _should_prune_urbanopt_rel(rel_posix: str) -> bool:
    parts = rel_posix.split("/")
    top = parts[0]
    if top in {
        "OpenStudio",
        "installerResources",
        "components.xml",
        "InstallationLog.txt",
        "installer.dat",
        "maintenancetool.dat",
        "maintenancetool.exe",
        "maintenancetool.ini",
        "network.xml",
        "uv.exe",
    }:
        return True
    if rel_posix.startswith("ruby/msys64/") or rel_posix == "ruby/msys64":
        return True
    if rel_posix.startswith("ruby/unins000.") or rel_posix.startswith("ruby/packages/"):
        return True
    if len(parts) >= 4 and parts[0] == "gems" and parts[1] == "ruby" and parts[3] == "cache":
        return True
    if len(parts) >= 4 and parts[0] == "openstudio-runtime-gems" and parts[1] == "ruby" and parts[3] == "cache":
        return True
    if (
        len(parts) >= 8
        and parts[0] == "gems"
        and parts[1] == "ruby"
        and parts[3] == "gems"
        and parts[4].startswith("urbanopt-cli-")
        and parts[5] == "example_files"
        and parts[6] == "resources"
        and parts[7] == "residential-measures"
    ):
        return True
    return False


def _build_urbanopt_lbtpack(
    *,
    urbanopt_dir: Path,
    openstudio_archive: Path,
    output_dir: Path,
    version: str,
    manifest: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    uo_meta = manifest["runtimes"]["urbanopt"]
    os_ver = manifest["target_versions"]["openstudio"]
    uo_target_prefix = uo_meta["pack_target_dir"]  # runtimes/urbanopt-cli-1.4.0
    os_ruby_prefix = uo_meta["openstudio_ruby_target_dir"]  # runtimes/openstudio/3.11.0/Ruby

    pack_path = output_dir / f"lbt-mcp-{version}-win-x64-urbanopt.lbtpack"
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_pack = pack_path.with_suffix(".lbtpack.tmp")
    tmp_pack.unlink(missing_ok=True)

    raw_files = 0
    raw_bytes = 0
    pruned_files = 0
    pruned_bytes = 0
    manifest_files: list[dict[str, Any]] = []
    seen_targets: set[str] = set()

    print(f"Building optional URBANopt .lbtpack at {pack_path}...", flush=True)
    with ZipFile(tmp_pack, "w", compression=ZIP_LZMA) as zf:
        for src in sorted(urbanopt_dir.rglob("*")):
            is_sym = src.is_symlink()
            if not is_sym and not src.is_file():
                continue
            rel = src.relative_to(urbanopt_dir).as_posix()
            fsize = src.lstat().st_size if is_sym else src.stat().st_size
            raw_files += 1
            raw_bytes += fsize
            if _should_prune_urbanopt_rel(rel):
                continue
            if is_sym:
                raise ValueError(f"Refusing to pack symlink from {urbanopt_dir}: {src}")

            target_rel = f"{uo_target_prefix}/{rel}"
            if target_rel in seen_targets:
                raise ValueError(f"Duplicate target path in URBANopt pack: {target_rel}")
            seen_targets.add(target_rel)

            data = src.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            archive_rel = f"files/{target_rel}"
            zf.writestr(archive_rel, data)
            manifest_files.append(
                {
                    "path": target_rel,
                    "archive_path": archive_rel,
                    "sha256": sha,
                    "size": len(data),
                }
            )
            pruned_files += 1
            pruned_bytes += len(data)

        # Add ONLY OpenStudio/Ruby/ from OpenStudio 3.11.0 archive (deduplicating bin/ & EnergyPlus/).
        with tarfile.open(openstudio_archive, "r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                norm = member.name.replace("\\", "/").lstrip("./")
                parts = norm.split("/")
                if len(parts) < 3 or parts[1] != "Ruby":
                    continue
                ruby_rel = "/".join(parts[2:])
                target_rel = f"{os_ruby_prefix}/{ruby_rel}"
                if target_rel in seen_targets:
                    continue
                seen_targets.add(target_rel)
                extracted = tf.extractfile(member)
                assert extracted is not None
                data = extracted.read()
                sha = hashlib.sha256(data).hexdigest()
                archive_rel = f"files/{target_rel}"
                zf.writestr(archive_rel, data)
                manifest_files.append(
                    {
                        "path": target_rel,
                        "archive_path": archive_rel,
                        "sha256": sha,
                        "size": len(data),
                    }
                )
                pruned_files += 1
                pruned_bytes += len(data)

        # Sanity checks for required URBANopt files inside pack
        required_suffixes = (
            f"{uo_target_prefix}/gems/Gemfile",
            f"{uo_target_prefix}/openstudio-runtime-gems/Gemfile",
            f"{uo_target_prefix}/ruby/bin/ruby.exe",
            f"{os_ruby_prefix}/openstudio.rb",
            f"{os_ruby_prefix}/openstudio.so",
        )
        for req in required_suffixes:
            if req not in seen_targets:
                raise FileNotFoundError(f"URBANopt .lbtpack missing required file: {req}")
        if not any(
            fnmatch.fnmatch(p, f"{uo_target_prefix}/gems/ruby/*/gems/urbanopt-cli-*/example_files/reopt/multiPV_assumptions.json")
            for p in seen_targets
        ):
            raise FileNotFoundError("URBANopt .lbtpack missing example_files/reopt/multiPV_assumptions.json")
        if not any(
            fnmatch.fnmatch(p, f"{uo_target_prefix}/gems/ruby/*/gems/urbanopt-cli-*/example_files/python_deps/pyproject.toml")
            or fnmatch.fnmatch(
                p, f"{uo_target_prefix}/gems/ruby/*/gems/urbanopt-cli-*/example_files/python_deps/dependencies.json"
            )
            for p in seen_targets
        ):
            raise FileNotFoundError("URBANopt .lbtpack missing example_files/python_deps/")

        pack_manifest = {
            "schema_version": 1,
            "name": "urbanopt",
            "version": uo_meta["version"],
            "platform": "win-x64",
            "compatible_openstudio": os_ver,
            "runtime_updates": {
                "urbanopt_cli_path": uo_target_prefix,
            },
            "files": manifest_files,
        }
        zf.writestr("pack.json", json.dumps(pack_manifest, indent=2) + "\n")

    tmp_pack.replace(pack_path)
    return pack_path, {
        "archive": str(pack_path),
        "raw": {"files": raw_files, "bytes": raw_bytes},
        "pruned": {"files": pruned_files, "bytes": pruned_bytes},
        "compressed_bytes": pack_path.stat().st_size,
        "sha256": _sha256_file(pack_path),
    }


def _compile_inno_installer(
    *,
    iss_path: Path,
    staging_dir: Path,
    output_dir: Path,
    version: str,
) -> Path:
    iscc = _find_iscc()
    if iscc is None:
        raise RuntimeError(
            "Inno Setup 6 ISCC.exe not found. Install Inno Setup 6 (`winget install --id JRSoftware.InnoSetup -e --scope user`)."
        )
    if not iss_path.is_file():
        raise FileNotFoundError(f"Inno Setup script not found: {iss_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Compiling Inno Setup installer via {iscc}...", flush=True)
    subprocess.run(
        [
            str(iscc),
            f"/DMyAppVersion={version}",
            f"/DStagingDir={staging_dir}",
            f"/DOutputDir={output_dir}",
            str(iss_path),
        ],
        cwd=str(iss_path.parent),
        check=True,
    )
    setup_exe = output_dir / f"lbt-mcp-{version}-win-x64-setup.exe"
    if not setup_exe.is_file():
        raise FileNotFoundError(f"ISCC completed without creating {setup_exe}")
    return setup_exe


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR)
    parser.add_argument("--urbanopt-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--iss-path", type=Path, default=DEFAULT_ISS_PATH)
    parser.add_argument("--version", default=None)
    parser.add_argument("--skip-urbanopt", action="store_true")
    parser.add_argument(
        "--reuse-existing-urbanopt",
        action="store_true",
        help="Reuse existing .lbtpack in --output-dir when present instead of rebuilding it.",
    )
    parser.add_argument("--skip-downloads", action="store_true")
    parser.add_argument("--compile-installer", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = args.manifest.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = args.version or _read_project_version()

    cache_dir = args.cache_dir.expanduser().resolve()
    staging_dir = args.staging_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    runtimes = manifest["runtimes"]
    targets = manifest["target_versions"]

    # 1. Verify/download pinned upstream runtime archives
    cached_archives: dict[str, Path] = {}
    for key in ("python", "openstudio", "openstudio_csharp", "radiance", "ironbug", "lbt_measures", "honeybee_openstudio_gem"):
        entry = runtimes[key]
        cached_archives[key] = ensure_cached_file(
            cache_dir=cache_dir,
            relpath=entry["filename"],
            url=entry["url"],
            expected_sha256=entry.get("sha256"),
            skip_downloads=args.skip_downloads,
        )

    # 2. Build Rune viewer binary/web + wheel + Rust launcher
    _ensure_rune_viewer_artifacts()
    wheelhouse_dir = staging_dir.parent / "windows-offline-wheelhouse"
    wheel_path = _build_wheel(wheelhouse_dir, version)

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    launcher_exe = _build_launcher(staging_dir)
    portable_python, py_raw = _stage_portable_python(cached_archives["python"], staging_dir, targets["python"])
    py_pruned = _dir_stats(staging_dir / "runtimes" / "python" / targets["python"])

    venv_python, venv_report = _build_isolated_venv(
        portable_python=portable_python,
        staging_dir=staging_dir,
        version=version,
        wheel_path=wheel_path,
    )
    os_report = _stage_openstudio(
        openstudio_archive=cached_archives["openstudio"],
        csharp_nupkg=cached_archives["openstudio_csharp"],
        staging_dir=staging_dir,
        os_ver=targets["openstudio"],
    )
    rad_report = _stage_radiance(cached_archives["radiance"], staging_dir, targets["radiance"])
    measures_stats = _stage_lbt_measures(
        measures_archive=cached_archives["lbt_measures"],
        gem_archive=cached_archives["honeybee_openstudio_gem"],
        staging_dir=staging_dir,
    )
    ib_report = _stage_ironbug(cached_archives["ironbug"], staging_dir, targets["ironbug"])

    _stage_skills_and_metadata(
        staging_dir=staging_dir,
        version=version,
        wheel_path=wheel_path,
        manifest=manifest,
    )
    _stage_licenses(staging_dir, manifest_path)

    # Strip any stray .pdb anywhere inside staging_dir
    stray_pdbs = 0
    for pdb in list(staging_dir.rglob("*.pdb")):
        if pdb.is_file():
            pdb.unlink()
            stray_pdbs += 1

    staging_stats = _dir_stats(staging_dir)

    # 3. Optional URBANopt .lbtpack
    urbanopt_report: dict[str, Any] = {"skipped": True}
    if not args.skip_urbanopt:
        existing_pack = output_dir / f"lbt-mcp-{version}-win-x64-urbanopt.lbtpack"
        existing_report_path = output_dir / "build_report.json"
        if args.reuse_existing_urbanopt and existing_pack.is_file():
            pack_sha = _sha256_file(existing_pack)
            reused_meta: dict[str, Any] = {
                "archive": str(existing_pack),
                "compressed_bytes": existing_pack.stat().st_size,
                "sha256": pack_sha,
                "reused": True,
            }
            if existing_report_path.is_file():
                try:
                    prev_report = json.loads(existing_report_path.read_text(encoding="utf-8"))
                    prev_uo = prev_report.get("urbanopt_pack") if isinstance(prev_report, dict) else None
                    if isinstance(prev_uo, dict) and prev_uo.get("sha256") == pack_sha:
                        reused_meta = {**prev_uo, "reused": True}
                except (OSError, json.JSONDecodeError):
                    pass
            print(f"Reusing existing URBANopt .lbtpack at {existing_pack} (sha256={pack_sha}).", flush=True)
            urbanopt_report = reused_meta
        else:
            uo_dir = _resolve_urbanopt_dir(
                explicit_dir=args.urbanopt_dir,
                cache_dir=cache_dir,
                manifest=manifest,
                skip_downloads=args.skip_downloads,
            )
            assert uo_dir is not None
            _, urbanopt_report = _build_urbanopt_lbtpack(
                urbanopt_dir=uo_dir,
                openstudio_archive=cached_archives["openstudio"],
                output_dir=output_dir,
                version=version,
                manifest=manifest,
            )

    # 4. Optional Inno Setup compilation
    installer_report: dict[str, Any] = {"compiled": False}
    if args.compile_installer:
        setup_exe = _compile_inno_installer(
            iss_path=args.iss_path.expanduser().resolve(),
            staging_dir=staging_dir,
            output_dir=output_dir,
            version=version,
        )
        installer_report = {
            "compiled": True,
            "path": str(setup_exe),
            "bytes": setup_exe.stat().st_size,
            "sha256": _sha256_file(setup_exe),
        }

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "version": version,
        "platform": "win-x64",
        "staging_dir": str(staging_dir),
        "launcher": str(launcher_exe),
        "venv_python": str(venv_python),
        "wheel": {
            "name": wheel_path.name,
            "bytes": wheel_path.stat().st_size,
            "sha256": _sha256_file(wheel_path),
        },
        "components": {
            "python": {
                "version": targets["python"],
                "raw": {"files": py_raw["raw_files"], "bytes": py_raw["raw_bytes"]},
                "pruned": py_pruned,
            },
            "venv": venv_report,
            "openstudio": os_report,
            "radiance": rad_report,
            "lbt_measures": measures_stats,
            "ironbug": ib_report,
        },
        "stray_pdb_removed": stray_pdbs,
        "staging_totals": staging_stats,
        "urbanopt_pack": urbanopt_report,
        "installer": installer_report,
    }
    report_path = output_dir / "build_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Build complete. Report written to {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
