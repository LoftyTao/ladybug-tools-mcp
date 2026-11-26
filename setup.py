"""Build a fresh wheel tree and include the canonical release assets."""

from pathlib import Path
import hashlib
import importlib.util
import json
import os
import platform
import runpy
import shutil
import subprocess
import sys
import tomllib
import warnings

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py


def _find_cmake():
    cmake = shutil.which("cmake")
    if cmake:
        return cmake
    if os.name == "nt":
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        vswhere = Path(program_files_x86) / "Microsoft Visual Studio/Installer/vswhere.exe"
        if vswhere.is_file():
            proc = subprocess.run(
                [str(vswhere), "-latest", "-products", "*", "-property", "installationPath"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            install_path = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
            if install_path:
                candidate = (
                    Path(install_path)
                    / "Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe"
                )
                if candidate.is_file():
                    return str(candidate)
    return None


class CMakeExtension(Extension):
    def __init__(self, name):
        super().__init__(name, sources=[])


class CMakeBuild(build_ext):
    def _load_build_identity(self, root):
        spec = importlib.util.spec_from_file_location(
            "pyhygrothermfem_build_identity",
            root / "src/pyhygrothermfem_native/build_identity.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def build_extension(self, extension):
        root = Path(__file__).resolve().parent
        cmake = _find_cmake()
        require_native = os.environ.get("LBT_MCP_REQUIRE_HYGROTHERM_NATIVE") == "1"
        if cmake is None:
            if require_native:
                raise RuntimeError(
                    "LBT_MCP_REQUIRE_HYGROTHERM_NATIVE=1 requires CMake and a C++20 toolchain "
                    "to compile pyhygrothermfem_fairyfly._native."
                )
            warnings.warn(
                "CMake was not found; skipping native compilation of pyhygrothermfem_fairyfly._native "
                "(set LBT_MCP_REQUIRE_HYGROTHERM_NATIVE=1 to require it).",
                RuntimeWarning,
                stacklevel=2,
            )
            return

        import pybind11

        build_identity = self._load_build_identity(root)
        native_path = Path(self.get_ext_fullpath(extension.name)).resolve()
        output_dir = native_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        for stale in (*output_dir.glob("_native*"), output_dir / "_build_source.json"):
            if stale.is_file():
                stale.unlink()

        build_dir = Path(self.build_temp).resolve() / "htfem"
        build_dir.mkdir(parents=True, exist_ok=True)
        configuration = "Debug" if self.debug else "Release"

        # Copy os.environ into a plain dict so Windows PATH/Path keys do not
        # collide case-insensitively inside MSBuild (.NET ProcessStartInfo).
        env = dict(os.environ)

        subprocess.run(
            [
                cmake,
                "-S",
                str(root / "src/pyhygrothermfem_native"),
                "-B",
                str(build_dir),
                f"-DPython_EXECUTABLE={sys.executable}",
                f"-Dpybind11_DIR={pybind11.get_cmake_dir()}",
                f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={output_dir}",
                f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{configuration.upper()}={output_dir}",
                f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={output_dir}",
                f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_{configuration.upper()}={output_dir}",
                f"-DCMAKE_BUILD_TYPE={configuration}",
            ],
            check=True,
            env=env,
        )
        subprocess.run(
            [
                cmake,
                "--build",
                str(build_dir),
                "--config",
                configuration,
                "--target",
                "_native",
                "--parallel",
            ],
            check=True,
            env=env,
        )

        identity_path = build_dir / "build-source-identity.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        if build_identity.prepare_identity(root) != identity:
            raise RuntimeError("Build inputs changed after CMake source verification.")
        build_identity.finalize_package(output_dir, identity_path, native_path)

    def get_outputs(self):
        outputs = super().get_outputs()
        for extension in self.extensions:
            metadata = str(
                Path(self.get_ext_fullpath(extension.name)).parent / "_build_source.json"
            )
            if metadata not in outputs and Path(metadata).is_file():
                outputs.append(metadata)
        return outputs

    def copy_extensions_to_source(self):
        super().copy_extensions_to_source()
        build_py = self.get_finalized_command("build_py")
        for ext in self.extensions:
            ext_rel = Path(self.get_ext_filename(ext.name))
            src_meta = Path(self.build_lib) / ext_rel.parent / "_build_source.json"
            if not src_meta.is_file():
                src_meta = Path(self.get_ext_fullpath(ext.name)).parent / "_build_source.json"
            if src_meta.is_file():
                modpath = ext.name.split(".")
                package = ".".join(modpath[:-1])
                package_dir = Path(build_py.get_package_dir(package))
                package_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_meta, package_dir / "_build_source.json")


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
        if not getattr(self, "editable_mode", False):
            if not output.is_relative_to(root / "build") or output == root / "build":
                raise ValueError("The package build directory must be inside this project's build/ directory.")
            if output.exists():
                shutil.rmtree(output)
        super().run()
        resources = Path(self.build_lib) / "ladybug_tools_mcp" / "resources"
        self_contained_bridge = os.environ.get("LBT_MCP_SELF_CONTAINED_IRONBUG_BRIDGE") == "1"
        require_bridge = os.environ.get("LBT_MCP_REQUIRE_IRONBUG_BRIDGE") == "1" or self_contained_bridge
        if self_contained_bridge:
            machine = platform.machine().lower()
            if os.name == "nt":
                default_rid = "win-arm64" if "arm" in machine else "win-x64"
            elif sys.platform == "darwin":
                default_rid = "osx-arm64" if "arm" in machine else "osx-x64"
            else:
                default_rid = "linux-arm64" if "arm" in machine or "aarch64" in machine else "linux-x64"
            rid = os.environ.get("LBT_MCP_DOTNET_RID") or default_rid
            bridge_publish = root / "src/ironbug_bridge/bin/Release/net8.0" / rid / "publish"
            dotnet = shutil.which("dotnet")
            if not dotnet:
                raise RuntimeError(
                    "LBT_MCP_SELF_CONTAINED_IRONBUG_BRIDGE=1 requires `dotnet` on PATH to publish IronbugBridge."
                )
            if bridge_publish.exists():
                shutil.rmtree(bridge_publish)
            subprocess.run(
                [
                    dotnet,
                    "publish",
                    str(root / "src/ironbug_bridge/IronbugBridge.csproj"),
                    "-c",
                    "Release",
                    "-r",
                    rid,
                    "--self-contained",
                    "true",
                    "-p:DebugType=None",
                    "-p:DebugSymbols=false",
                    "-o",
                    str(bridge_publish),
                ],
                check=True,
            )
            exe_name = "IronbugBridge.exe" if rid.startswith("win") else "IronbugBridge"
            if not (bridge_publish / exe_name).is_file() or not (bridge_publish / "IronbugBridge.dll").is_file():
                raise RuntimeError(
                    f"dotnet publish completed but did not produce self-contained IronbugBridge in {bridge_publish}."
                )
            bridge_target = resources / "ironbug_bridge"
            bridge_target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                bridge_publish,
                bridge_target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("*.pdb"),
            )
            if not rid.startswith("win") and (bridge_target / exe_name).is_file():
                (bridge_target / exe_name).chmod(0o755)
        else:
            bridge_out = root / "src/ironbug_bridge/bin/Release/net8.0"
            bridge_dll = bridge_out / "IronbugBridge.dll"
            if not bridge_dll.is_file():
                dotnet = shutil.which("dotnet")
                if dotnet:
                    subprocess.run(
                        [dotnet, "build", str(root / "src/ironbug_bridge/IronbugBridge.csproj"), "-c", "Release"],
                        check=True,
                    )
                    if not bridge_dll.is_file():
                        raise RuntimeError(
                            f"dotnet build completed but did not produce {bridge_dll}."
                        )
                elif require_bridge:
                    raise RuntimeError(
                        "LBT_MCP_REQUIRE_IRONBUG_BRIDGE=1 requires IronbugBridge.dll, "
                        "but neither prebuilt src/ironbug_bridge/bin/Release/net8.0/IronbugBridge.dll "
                        "nor `dotnet` on PATH was found. Install the .NET 8 SDK or prebuild "
                        "src/ironbug_bridge/IronbugBridge.csproj."
                    )
                else:
                    warnings.warn(
                        "Prebuilt IronbugBridge.dll was not found and `dotnet` is unavailable on PATH; "
                        "continuing without bundling the .NET 8 IronbugBridge sidecar "
                        "(set LBT_MCP_REQUIRE_IRONBUG_BRIDGE=1 to require it).",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            if bridge_dll.is_file():
                bridge_target = resources / "ironbug_bridge"
                bridge_target.mkdir(parents=True, exist_ok=True)
                for pattern in ("*.dll", "*.deps.json", "*.runtimeconfig.json"):
                    for asset in bridge_out.glob(pattern):
                        shutil.copy2(asset, bridge_target / asset.name)
                runtimes_dir = bridge_out / "runtimes"
                if runtimes_dir.is_dir():
                    shutil.copytree(runtimes_dir, bridge_target / "runtimes", dirs_exist_ok=True)
        rune_exe_name = "lbt-rune-viewer.exe" if os.name == "nt" else "lbt-rune-viewer"
        rune_bin = root / "rune_viewer" / "target" / "release" / rune_exe_name
        require_rune = os.environ.get("LBT_MCP_REQUIRE_RUNE_VIEWER") == "1"
        if not rune_bin.is_file() and require_rune:
            cargo = shutil.which("cargo")
            if cargo:
                subprocess.run(
                    [cargo, "build", "--release", "-p", "lbt-viewer-app", "--bin", "lbt-rune-viewer"],
                    cwd=str(root / "rune_viewer"),
                    check=True,
                )
            if not rune_bin.is_file():
                raise RuntimeError(
                    "LBT_MCP_REQUIRE_RUNE_VIEWER=1 requires lbt-rune-viewer, "
                    f"but neither prebuilt {rune_bin} nor a working `cargo` build produced it."
                )
        if rune_bin.is_file():
            rune_target = resources / "rune_viewer"
            rune_target.mkdir(parents=True, exist_ok=True)
            copied_bin = rune_target / rune_exe_name
            shutil.copy2(rune_bin, copied_bin)
            if os.name != "nt":
                copied_bin.chmod(0o755)
        rune_web = root / "rune_viewer" / "target" / "web"
        if (rune_web / "app_bg.wasm").is_file() and (rune_web / "index.html").is_file():
            shutil.copytree(rune_web, resources / "rune_viewer" / "web", dirs_exist_ok=True)
        for source, target in (
            (root / ".agents/skills/ladybug-tools", resources / "skills/ladybug-tools"),
            (root / "src/grasshopper_components/user_objects", resources / "grasshopper"),
        ):
            if not source.is_dir():
                raise FileNotFoundError(f"Missing distribution assets: {source}")
            shutil.copytree(
                source, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("AGENTS.md", "__pycache__", "*.pyc"),
            )


setup(
    cmdclass={"build_py": BuildPy, "build_ext": CMakeBuild},
    ext_modules=[CMakeExtension("pyhygrothermfem_fairyfly._native")],
)
