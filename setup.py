"""Build a fresh wheel tree and include the canonical release assets."""

from pathlib import Path
import hashlib
import json
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
        if manifest["version"] != version or len(manifest["components"]) != 6:
            raise ValueError("Rebuild Grasshopper assets for this release with scripts/distribution/build_grasshopper.py.")
        for entry in manifest["components"]:
            source = (components / (entry["name"] + ".py")).read_text(encoding="utf-8").encode("utf-8")
            asset = (components / "user_objects" / entry["file"]).read_bytes()
            if hashlib.sha256(source).hexdigest() != entry["source_sha256"] or hashlib.sha256(asset).hexdigest() != entry["sha256"]:
                raise ValueError("Stale or damaged Grasshopper asset: " + entry["name"])
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
