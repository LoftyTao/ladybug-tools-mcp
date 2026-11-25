#!/usr/bin/env python3
"""Package corresponding source for AGPL-3.0-only, GPL, and LGPL dependencies into .tar.zst."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from typing import Any
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / "build" / "offline-cache"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist" / "windows-offline"
DEFAULT_MANIFEST = REPO_ROOT / "scripts" / "distribution" / "runtime_manifest.windows-x64.json"
DEFAULT_SOURCE_MANIFEST = REPO_ROOT / "licenses" / "SOURCE_MANIFEST.json"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "tests",
    "gardens",
    "resources",
    "node_modules",
}

EXCLUDED_PREFIXES = (
    "src/ironbug_bridge/bin/",
    "src/ironbug_bridge/obj/",
    "src/web_view/vendor/",
    "rune_viewer/target/",
    "vendor/rune/.git/",
    "vendor/rune/target/",
    "vendor/pyHygroThermFEM-Fairyfly/.git/",
    "vendor/pyHygroThermFEM-Fairyfly/build/",
    "vendor/pyHygroThermFEM-Fairyfly/dist/",
    "vendor/pyHygroThermFEM-Fairyfly/tests/",
    "vendor/pyHygroThermFEM-Fairyfly/docs/",
    "scripts/distribution/launcher/target/",
)

EXCLUDED_FILENAMES = {
    "CONTEXT.md",
    "AGENTS.md",
    "_build_source.json",
}

INCLUDED_TOP_FILES = {
    "LICENSE",
    "MANIFEST.in",
    "pyproject.toml",
    "README.md",
    "README.zh-CN.md",
    "requirements.in",
    "requirements.txt",
    "setup.py",
    "scripts/build_rune_web.py",
}

INCLUDED_TOP_DIRS = (
    "src",
    "rune_viewer",
    "vendor/rune",
    "vendor/pyHygroThermFEM-Fairyfly",
    "scripts/distribution",
    "licenses",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_project_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _inject_tls_store() -> None:
    try:
        import truststore  # type: ignore[import-not-found]

        truststore.inject_into_ssl()
    except Exception:
        pass


def _ensure_source_tarball(
    *,
    cache_dir: Path,
    relpath: str,
    url: str,
    expected_sha256: str | None,
    skip_downloads: bool,
) -> Path:
    dest = (cache_dir / relpath).resolve()
    if not dest.is_relative_to(cache_dir.resolve()):
        raise ValueError(f"Source cache path escapes cache dir: {relpath}")

    if dest.is_file():
        if expected_sha256:
            actual = _sha256_file(dest)
            if actual.lower() == expected_sha256.lower():
                return dest
            if skip_downloads:
                raise RuntimeError(f"Cached source SHA-256 mismatch for {dest}: {actual} != {expected_sha256}")
            dest.unlink()
        else:
            return dest

    if skip_downloads:
        raise FileNotFoundError(f"Missing cached source tarball (--skip-downloads): {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    _inject_tls_store()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    print(f"Downloading corresponding source {relpath} from {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "lbt-mcp-corresponding-source/1.0"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while chunk := resp.read(1024 * 1024):
            out.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if expected_sha256 and actual.lower() != expected_sha256.lower():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for {relpath}: expected {expected_sha256}, got {actual}")
    tmp.replace(dest)
    return dest


def _is_excluded(rel_posix: str) -> bool:
    parts = PurePosixPath(rel_posix).parts
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    name = parts[-1]
    if name in EXCLUDED_FILENAMES:
        return True
    if name.endswith((".pyc", ".pyo", ".pyd", ".so")) and (
        name.startswith("_native") or name.endswith((".pyc", ".pyo"))
    ):
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    norm_slash = rel_posix + ("/" if not rel_posix.endswith("/") else "")
    for prefix in EXCLUDED_PREFIXES:
        if norm_slash.startswith(prefix) or rel_posix == prefix.rstrip("/"):
            return True
    return False


def _collect_repo_source_files() -> list[Path]:
    collected: list[Path] = []
    for name in sorted(INCLUDED_TOP_FILES):
        cand = REPO_ROOT / name
        if cand.is_file():
            collected.append(cand)

    for rel_dir in INCLUDED_TOP_DIRS:
        base = REPO_ROOT / rel_dir
        if not base.is_dir():
            raise FileNotFoundError(f"Required corresponding-source directory missing: {base}")
        for item in sorted(base.rglob("*")):
            if not item.is_file() or item.is_symlink():
                continue
            rel = item.relative_to(REPO_ROOT).as_posix()
            if _is_excluded(rel):
                continue
            collected.append(item)

    skills_dir = REPO_ROOT / ".agents" / "skills" / "ladybug-tools-mcp-use"
    if skills_dir.is_dir():
        for item in sorted(skills_dir.rglob("*")):
            if item.is_file() and not item.is_symlink():
                rel = item.relative_to(REPO_ROOT).as_posix()
                if not _is_excluded(rel):
                    collected.append(item)

    return collected


def _compress_tar_to_zst(tar_path: Path, zst_path: Path) -> None:
    tmp_out = zst_path.with_suffix(".zst.tmp")
    tmp_out.unlink(missing_ok=True)
    zstd_cli = shutil.which("zstd")
    if zstd_cli:
        subprocess.run(
            [zstd_cli, "-19", "-T0", "-q", "-f", "-o", str(tmp_out), str(tar_path)],
            check=True,
        )
        tmp_out.replace(zst_path)
        return

    try:
        import zstandard as zstd  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Neither `zstd` CLI nor Python `zstandard` package was found to build .tar.zst."
        ) from exc

    cctx = zstd.ZstdCompressor(level=15)
    with tar_path.open("rb") as src, tmp_out.open("wb") as dst:
        cctx.copy_stream(src, dst)
    tmp_out.replace(zst_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--version", default=None)
    parser.add_argument("--skip-downloads", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    version = args.version or _read_project_version()
    cache_dir = args.cache_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    source_manifest_path = args.source_manifest.expanduser().resolve()

    if not source_manifest_path.is_file():
        raise FileNotFoundError(
            f"Missing SOURCE_MANIFEST.json at {source_manifest_path}. Run scripts/distribution/generate_licenses.py first."
        )

    runtime_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    corr_sources: dict[str, dict[str, Any]] = runtime_manifest.get("corresponding_sources") or {}

    resolved_tarballs: list[tuple[str, Path, str]] = []
    for entry in source_manifest.get("entries", []):
        if not entry.get("bundled_in_standard") or not entry.get("requires_corresponding_source"):
            continue
        if entry.get("source_type") != "upstream_tarball":
            continue
        entry_id = str(entry["id"])
        src_meta = corr_sources.get(entry_id) or {}
        relpath = src_meta.get("relpath") or f"sources/{entry['archive_name']}"
        url = src_meta.get("url") or entry["source_url"]
        expected_sha = entry.get("sha256") or src_meta.get("sha256")
        tarball = _ensure_source_tarball(
            cache_dir=cache_dir,
            relpath=relpath,
            url=url,
            expected_sha256=expected_sha,
            skip_downloads=args.skip_downloads,
        )
        actual_sha = _sha256_file(tarball)
        if expected_sha and actual_sha.lower() != expected_sha.lower():
            raise RuntimeError(f"Source tarball SHA-256 mismatch for {tarball}: {actual_sha} != {expected_sha}")
        resolved_tarballs.append((entry["archive_name"] or tarball.name, tarball, actual_sha))

    repo_files = _collect_repo_source_files()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"lbt-mcp-{version}-corresponding-source.tar.zst"
    out_zst = output_dir / archive_name
    root_prefix = f"lbt-mcp-{version}-corresponding-source"
    repo_prefix = f"{root_prefix}/lbt-mcp-{version}"

    with tempfile.TemporaryDirectory(prefix="lbt-mcp-corr-src-") as td:
        tmp_tar = Path(td) / f"lbt-mcp-{version}-corresponding-source.tar"
        print(f"Packaging {len(repo_files)} repo source files + {len(resolved_tarballs)} upstream tarballs...", flush=True)
        with tarfile.open(tmp_tar, "w", format=tarfile.PAX_FORMAT) as tf:
            for src_file in repo_files:
                rel = src_file.relative_to(REPO_ROOT).as_posix()
                tf.add(src_file, arcname=f"{repo_prefix}/{rel}", recursive=False)

            for arc_name, tarball_path, _sha in resolved_tarballs:
                tf.add(tarball_path, arcname=f"{root_prefix}/upstream-sources/{arc_name}", recursive=False)

            manifest_bytes = source_manifest_path.read_bytes()
            info = tarfile.TarInfo(name=f"{root_prefix}/SOURCE_MANIFEST.json")
            info.size = len(manifest_bytes)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(manifest_bytes))

        _compress_tar_to_zst(tmp_tar, out_zst)

    sha = _sha256_file(out_zst)
    print(
        json.dumps(
            {
                "archive": str(out_zst),
                "bytes": out_zst.stat().st_size,
                "sha256": sha,
                "repo_file_count": len(repo_files),
                "upstream_sources": [
                    {"name": name, "sha256": s} for name, _p, s in resolved_tarballs
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
