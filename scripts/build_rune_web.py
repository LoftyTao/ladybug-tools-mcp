#!/usr/bin/env python3
"""Build the browser WASM bundle for lbt-viewer-app into rune_viewer/target/web/."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNE_VIEWER_DIR = REPO_ROOT / "rune_viewer"
OUT_DIR = RUNE_VIEWER_DIR / "target" / "web"
INTER_FACES_DIR = REPO_ROOT / "vendor" / "rune" / "crates" / "rune" / "assets" / "web"
INTER_FACES = ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf")

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>Rune 3D Web View</title>
<style>
  html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    overscroll-behavior: none;
    touch-action: none;
    background: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  #status {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    font-size: 15px;
    z-index: 9999;
    background: #0d1117;
    color: #e6edf3;
    text-align: center;
  }
</style>
</head>
<body>
<div id="status">Loading Rune 3D Web View...</div>
<script type="module">
import init from './app.js';
const statusEl = document.querySelector('#status');
try {
    const hasWebGPU = !!navigator.gpu;
    const probeCanvas = document.createElement('canvas');
    const hasWebGL2 = !!probeCanvas.getContext('webgl2');
    if (!hasWebGPU && !hasWebGL2) {
        throw new Error('This browser lacks both WebGPU and WebGL2 support.');
    }
    await init();
    statusEl?.remove();
} catch (error) {
    if (statusEl) {
        statusEl.textContent = 'Rune Web View error: ' + String(error);
    }
    console.error(error);
}
</script>
</body>
</html>
"""


def _read_lock_wasm_bindgen_version(lock_path: Path) -> str:
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    for pkg in data.get("package", []):
        if pkg.get("name") == "wasm-bindgen":
            return str(pkg["version"])
    raise RuntimeError(f"wasm-bindgen not found in {lock_path}")


def _verify_wasm_bindgen_cli(expected_version: str) -> str:
    exe = shutil.which("wasm-bindgen")
    if not exe:
        raise RuntimeError(
            f"wasm-bindgen CLI not found on PATH. Run: cargo install wasm-bindgen-cli --version {expected_version} --locked"
        )
    proc = subprocess.run([exe, "--version"], capture_output=True, text=True, check=True)
    actual = proc.stdout.strip()
    expected = f"wasm-bindgen {expected_version}"
    if actual != expected:
        raise RuntimeError(f"Expected '{expected}', found '{actual}'. Install matching wasm-bindgen-cli.")
    return exe


def main() -> int:
    expected_version = _read_lock_wasm_bindgen_version(RUNE_VIEWER_DIR / "Cargo.lock")
    wasm_bindgen_exe = _verify_wasm_bindgen_cli(expected_version)

    cargo = shutil.which("cargo")
    if not cargo:
        raise RuntimeError("cargo not found on PATH")

    env = os.environ.copy()
    env.setdefault("CARGO_PROFILE_RELEASE_OPT_LEVEL", "s")
    env.setdefault("CARGO_PROFILE_RELEASE_LTO", "thin")
    env.setdefault("CARGO_PROFILE_RELEASE_CODEGEN_UNITS", "1")
    env.setdefault("CARGO_PROFILE_RELEASE_DEBUG", "0")

    print("Building lbt-viewer-app (wasm32-unknown-unknown release)...")
    subprocess.run(
        [
            cargo,
            "build",
            "--lib",
            "--release",
            "-p",
            "lbt-viewer-app",
            "--target",
            "wasm32-unknown-unknown",
        ],
        cwd=str(RUNE_VIEWER_DIR),
        env=env,
        check=True,
    )

    artifact = RUNE_VIEWER_DIR / "target" / "wasm32-unknown-unknown" / "release" / "lbt_viewer_app.wasm"
    if not artifact.is_file():
        raise FileNotFoundError(f"Expected compiled wasm artifact missing: {artifact}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    staging = OUT_DIR / ".next"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    print(f"Running {wasm_bindgen_exe} --target web...")
    subprocess.run(
        [
            wasm_bindgen_exe,
            "--target",
            "web",
            "--out-dir",
            str(staging),
            "--out-name",
            "app",
            "--remove-name-section",
            str(artifact),
        ],
        cwd=str(RUNE_VIEWER_DIR),
        check=True,
    )

    for face in INTER_FACES:
        src = INTER_FACES_DIR / face
        if not src.is_file():
            raise FileNotFoundError(f"Missing Rune web font asset: {src}")
        shutil.copy2(src, staging / face)

    (staging / "index.html").write_text(INDEX_HTML, encoding="utf-8")

    for entry in staging.iterdir():
        dest = OUT_DIR / entry.name
        if dest.is_dir():
            shutil.rmtree(dest)
        elif dest.exists():
            dest.unlink()
        shutil.move(str(entry), str(dest))
    staging.rmdir()

    wasm_size = (OUT_DIR / "app_bg.wasm").stat().st_size
    js_size = (OUT_DIR / "app.js").stat().st_size
    print(f"Bundle built at {OUT_DIR}")
    print(f"  app_bg.wasm: {wasm_size:,} bytes")
    print(f"  app.js:      {js_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
