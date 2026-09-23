"""Build a fresh wheel tree and include the canonical release assets."""

from pathlib import Path
import hashlib
import json
import runpy
import shutil
import tomllib

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        root = Path(__file__).resolve().parent
        components = root / "src/grasshopper_components"
        manifest = json.loads((components / "user_objects/manifest.json").read_text(encoding="utf-8"))
        version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        runtime_version = runpy.run_path(str(root / "src/ladybug_tools_mcp/__init__.py"))["__version__"]
        if version != runtime_version:
            raise ValueError("Package metadata version must match the MCP runtime version.")
        entries = manifest.get("components")
        source_names = {path.stem for path in components.glob("FP *.py")}
        if manifest.get("version") != version or not entries or {entry.get("name") for entry in entries} != source_names:
            raise ValueError("Rebuild Grasshopper assets for this release with scripts/distribution/build_grasshopper.py.")
        names, files = set(), set()
        for entry in manifest["components"]:
            name, filename = entry.get("name"), entry.get("file")
            source_path = components / (name + ".py")
            asset_path = components / "user_objects" / filename
            if (
                name in names or filename in files
                or entry.get("category") != "Flowerpot"
                or entry.get("subcategory") != "Flowerpot"
                or entry.get("exposure") not in {2, 4, 8, 16, 32, 64, 128}
                or filename != name + ".ghuser"
                or not source_path.is_file() or not asset_path.is_file()
            ):
                raise ValueError("Invalid or duplicate Grasshopper manifest entry: " + str(name))
            names.add(name)
            files.add(filename)
            source = source_path.read_text(encoding="utf-8").encode("utf-8")
            asset = asset_path.read_bytes()
            if hashlib.sha256(source).hexdigest() != entry["source_sha256"] or hashlib.sha256(asset).hexdigest() != entry["sha256"]:
                raise ValueError("Stale or damaged Grasshopper asset: " + name)
        actual_assets = {path.name for path in (components / "user_objects").glob("*.ghuser")}
        if actual_assets != files:
            raise ValueError("Grasshopper manifest and user-object files do not match.")
        output = Path(self.build_lib).resolve()
        if not output.is_relative_to(root / "build") or output == root / "build":
            raise ValueError("The package build directory must be inside this project's build/ directory.")
        if output.exists():
            shutil.rmtree(output)
        super().run()
        resources = Path(self.build_lib) / "ladybug_tools_mcp" / "resources"
        for source, target in (
            (root / ".agents/skills/ladybug-tools-mcp-use", resources / "skills/ladybug-tools-mcp-use"),
            (root / "src/grasshopper_components/user_objects", resources / "grasshopper"),
        ):
            if not source.is_dir():
                raise FileNotFoundError(f"Missing distribution assets: {source}")
            shutil.copytree(
                source, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("AGENTS.md", "__pycache__", "*.pyc"),
            )


setup(cmdclass={"build_py": BuildPy})
