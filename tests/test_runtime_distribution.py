"""Tests for offline runtime home, SDK config sync, .lbtpack manager, doctor, CLI, self-contained IronbugBridge, and Rust launcher."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock
from zipfile import ZIP_LZMA, ZipFile

import pytest

from flowerpot.installation import installation_path, read_installation
from garden.ironbug.client import IronbugBridgeClient
from garden.ironbug.runtime import (
    is_self_contained_bridge_dir,
    resolve_runtime_paths,
)
from garden.ladybug_tools_config import (
    OPENSTUDIO_ENERGYPLUS_VERSIONS,
    REQUIRED_RUNTIME_VERSIONS,
    _des_gmt_config,
    _urbanopt_path_updates,
    get_ladybug_tools_config,
)
import ladybug_tools_mcp_cli
from ladybug_tools_mcp.runtime_home import (
    default_home_dir,
    install_pack,
    is_ascii_space_free,
    list_packs,
    read_runtime_config,
    remove_pack,
    run_doctor,
    sync_sdk_configs,
    write_installation_records,
    write_runtime_config,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_fake_sdk_site_packages(sp_dir: Path) -> Path:
    for pkg in ("ladybug", "honeybee", "honeybee_energy", "honeybee_radiance", "dragonfly_energy"):
        pkg_dir = sp_dir / pkg
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "config.json").write_text("{}", encoding="utf-8")
    fp_dir = sp_dir / "flowerpot"
    fp_dir.mkdir(parents=True, exist_ok=True)
    (fp_dir / "runtime.py").write_text("# stub\n", encoding="utf-8")
    return sp_dir


def _populate_minimal_home(home: Path, *, with_urbanopt_files: bool = False) -> dict[str, Path]:
    exe_ext = ".exe" if os.name == "nt" else ""
    os_bin = home / "runtimes" / "openstudio" / "3.11.0" / "bin"
    os_ep = home / "runtimes" / "openstudio" / "3.11.0" / "EnergyPlus"
    os_cs = home / "runtimes" / "openstudio" / "3.11.0" / "CSharp" / "openstudio"
    rad_bin = home / "runtimes" / "radiance" / "5.4" / "bin"
    rad_lib = home / "runtimes" / "radiance" / "5.4" / "lib"
    ib_dir = home / "runtimes" / "ironbug" / "1.26.1"
    measures_dir = home / "runtimes" / "lbt_home" / "resources" / "measures"
    py_home = home / "runtimes" / "python" / "3.12.16"
    venv_dir = home / "app" / "releases" / "1.2.3" / "venv"
    venv_scripts = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    sp_dir = venv_dir / "Lib" / "site-packages"
    skills_dir = home / "app" / "releases" / "1.2.3" / "skills" / "ladybug-tools-mcp-use"

    for d in (
        os_bin,
        os_ep,
        os_cs,
        rad_bin,
        rad_lib,
        ib_dir,
        measures_dir / "openstudio_results",
        measures_dir / "honeybee_openstudio_gem" / "lib",
        py_home,
        venv_scripts,
        skills_dir,
        home / "licenses",
        home / "bin",
    ):
        d.mkdir(parents=True, exist_ok=True)

    (os_bin / f"openstudio{exe_ext}").write_bytes(b"os")
    (os_ep / f"energyplus{exe_ext}").write_bytes(b"ep")
    (os_cs / "OpenStudio.dll").write_bytes(b"oscs")
    (rad_bin / f"rad{exe_ext}").write_bytes(b"rad")
    (rad_bin / f"rtrace{exe_ext}").write_bytes(b"rtrace")
    (rad_bin / f"evalglare{exe_ext}").write_bytes(b"evalglare")
    (ib_dir / "Ironbug.HVAC.dll").write_bytes(b"ibhvac")
    (ib_dir / f"Ironbug.Console{exe_ext}").write_bytes(b"ibconsole")
    (py_home / f"python{exe_ext}").write_bytes(b"py")
    (venv_scripts / f"python{exe_ext}").write_bytes(b"venvpy")
    (skills_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (home / "LICENSE").write_text("GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3\n", encoding="utf-8")
    (home / "licenses" / "THIRD_PARTY_NOTICES.md").write_text("# Notices\n", encoding="utf-8")
    (home / "bin" / f"lbt-mcp{exe_ext}").write_bytes(b"launcher")

    (venv_dir / "pyvenv.cfg").write_text(
        "home = D:\\BuildMachine\\runtimes\\python\\3.12.16\n"
        "implementation = CPython\n"
        "version_info = 3.12.16\n"
        "include-system-site-packages = false\n",
        encoding="utf-8",
    )
    (home / "app" / "current.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "1.2.3",
                "release_dir": "app/releases/1.2.3",
                "python": f"app/releases/1.2.3/venv/{'Scripts' if os.name == 'nt' else 'bin'}/python{exe_ext}",
                "python_home": "runtimes/python/3.12.16",
                "site_packages": "app/releases/1.2.3/venv/Lib/site-packages",
                "skills_dir": "app/releases/1.2.3/skills/ladybug-tools-mcp-use",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _make_fake_sdk_site_packages(sp_dir)

    if with_urbanopt_files:
        uo_dir = home / "runtimes" / "urbanopt-cli-1.4.0"
        (uo_dir / "gems" / "ruby" / "3.2.0" / "bin").mkdir(parents=True, exist_ok=True)
        (uo_dir / "gems" / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
        (uo_dir / "ruby" / "bin").mkdir(parents=True, exist_ok=True)

    return {
        "os_bin": os_bin,
        "os_ep": os_ep,
        "os_cs": os_cs,
        "rad_root": rad_bin.parent,
        "rad_bin": rad_bin,
        "ib_dir": ib_dir,
        "measures_dir": measures_dir,
        "py_home": py_home,
        "venv_dir": venv_dir,
        "sp_dir": sp_dir,
    }


def _build_lbtpack(
    archive_path: Path,
    files: dict[str, bytes],
    *,
    name: str = "urbanopt",
    version: str = "1.4.0-rc1",
    platform_name: str = "win-x64",
    compatible_openstudio: str = "3.11.0",
    runtime_updates: dict[str, str] | None = None,
    corrupt_sha_for: str | None = None,
) -> Path:
    manifest_files = []
    with ZipFile(archive_path, "w", compression=ZIP_LZMA) as zf:
        for rel_path, content in files.items():
            digest = hashlib.sha256(content).hexdigest()
            if corrupt_sha_for == rel_path:
                digest = "0" * 64
            archive_rel = f"files/{rel_path}"
            if not rel_path.startswith("/") and ".." not in rel_path.split("/"):
                zf.writestr(archive_rel, content)
            else:
                zf.writestr(rel_path, content)
                archive_rel = rel_path
            manifest_files.append(
                {
                    "path": rel_path,
                    "archive_path": archive_rel,
                    "sha256": digest,
                    "size": len(content),
                }
            )
        manifest = {
            "schema_version": 1,
            "name": name,
            "version": version,
            "platform": platform_name,
            "compatible_openstudio": compatible_openstudio,
            "runtime_updates": runtime_updates if runtime_updates is not None else {},
            "files": manifest_files,
        }
        zf.writestr("pack.json", json.dumps(manifest, indent=2))
    return archive_path


def test_default_home_dir_and_ascii_space_safety(monkeypatch: pytest.MonkeyPatch) -> None:
    assert is_ascii_space_free(r"C:\lbt-mcp") is True
    assert is_ascii_space_free(r"C:\Users\Alice Smith\lbt-mcp") is False
    assert is_ascii_space_free(r"C:\Users\张涛\lbt-mcp") is False

    monkeypatch.setenv("LADYBUG_TOOLS_MCP_HOME", r"D:\CustomHome\lbt-mcp")
    assert default_home_dir() == Path(r"D:\CustomHome\lbt-mcp").resolve()

    monkeypatch.delenv("LADYBUG_TOOLS_MCP_HOME", raising=False)
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(sys, "platform", "win32")

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Alice\AppData\Local")
    assert default_home_dir() == Path(r"C:\Users\Alice\AppData\Local\lbt-mcp")

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Alice Smith\AppData\Local")
    assert default_home_dir() == Path(r"C:\lbt-mcp")

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\张涛\AppData\Local")
    assert default_home_dir() == Path(r"C:\lbt-mcp")


def test_sync_sdk_configs_pyvenv_relocation_and_installation_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_user = tmp_path / "userprofile"
    fake_user.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_user))
    monkeypatch.setenv("HOME", str(fake_user))
    monkeypatch.delenv("LADYBUG_TOOLS_MCP_INSTALLATION", raising=False)
    monkeypatch.delenv("LADYBUG_TOOLS_MCP_HOME", raising=False)

    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    sp_dir = layout["sp_dir"]

    # Deliberately write Radiance .../bin in runtime.json to verify sync normalizes it to Radiance ROOT.
    cfg = read_runtime_config(home)
    cfg["radiance_path"] = str(layout["rad_bin"])
    write_runtime_config(cfg, home)

    sync_res = sync_sdk_configs(home, site_packages=sp_dir)
    assert len(sync_res["updated_sdk_configs"]) == 5

    rad_cfg = json.loads((sp_dir / "honeybee_radiance" / "config.json").read_text(encoding="utf-8"))
    assert Path(rad_cfg["radiance_path"]) == layout["rad_root"].resolve()
    assert not rad_cfg["radiance_path"].lower().endswith("bin")

    # Verify honeybee_radiance.config.Folders accepts synced config.json (does not append bin/bin).
    from honeybee_radiance.config import Folders as RadFolders

    rad_folders = RadFolders(config_file=str(sp_dir / "honeybee_radiance" / "config.json"), mute=True)
    assert Path(rad_folders.radiance_path).resolve() == layout["rad_root"].resolve()
    assert Path(rad_folders.radbin_path).resolve() == layout["rad_bin"].resolve()
    assert Path(rad_folders.radlib_path).resolve() == (layout["rad_root"] / "lib").resolve()

    # Verify honeybee_energy.config.Folders loads synced config.json cleanly.
    from honeybee_energy.config import Folders as EnergyFolders

    he_folders = EnergyFolders(config_file=str(sp_dir / "honeybee_energy" / "config.json"), mute=True)
    assert Path(he_folders.openstudio_path).resolve() == layout["os_bin"].resolve()
    assert Path(he_folders.energyplus_path).resolve() == layout["os_ep"].resolve()
    assert Path(he_folders.ironbug_path).resolve() == layout["ib_dir"].resolve()

    # Verify pyvenv.cfg relocated to <home>\runtimes\python\3.12.16.
    pyvenv_text = (layout["venv_dir"] / "pyvenv.cfg").read_text(encoding="utf-8")
    assert f"home = {layout['py_home'].resolve()}" in pyvenv_text
    assert f"executable = {(layout['py_home'] / ('python.exe' if os.name == 'nt' else 'bin/python3')).resolve()}" in pyvenv_text
    assert (home / "app" / "current" / "skills" / "ladybug-tools-mcp-use" / "SKILL.md").is_file()
    # Verify OpenStudio C# DLLs are hardlinked into Ironbug dir.
    ib_os_dll = layout["ib_dir"] / "OpenStudio.dll"
    assert ib_os_dll.is_file()
    if os.name == "nt":
        assert ib_os_dll.stat().st_ino == (layout["os_cs"] / "OpenStudio.dll").stat().st_ino

    # Gardens inside <home> must be rejected.
    with pytest.raises(ValueError, match="outside runtime home"):
        write_installation_records(home, gardens_root=home / "gardens", site_packages=sp_dir)

    # Non-ASCII / spaces in Gardens outside <home> must succeed.
    gardens = tmp_path / "中文 验收 Gardens"
    written = write_installation_records(home, gardens_root=gardens, site_packages=sp_dir)
    rec = written["record"]
    assert rec["schema_version"] == 1
    assert rec["home"] == str(home.resolve())
    assert rec["gardens_root"] == str(gardens.resolve())
    assert Path(rec["runtime_config"]) == (home / "config" / "runtime.json").resolve()
    assert (home / "config" / "installation.json").is_file()
    assert (fake_user / ".ladybug-tools-mcp" / "installation.json").is_file()

    # Validate IronPython-compatible reader accepts both additive and legacy records.
    loaded = read_installation(str(fake_user / ".ladybug-tools-mcp" / "installation.json"))
    assert loaded["schema_version"] == 1
    assert loaded["home"] == str(home.resolve())

    # Confirm src/flowerpot/installation.py contains zero non-IronPython syntax (no f-strings or annotations).
    inst_src = (_REPO_ROOT / "src" / "flowerpot" / "installation.py").read_text(encoding="utf-8")
    tree = ast.parse(inst_src)
    assert not any(isinstance(node, (ast.JoinedStr, ast.AnnAssign)) for node in ast.walk(tree))
    assert not any(
        isinstance(node, ast.FunctionDef) and (node.returns is not None or any(a.annotation is not None for a in node.args.args))
        for node in ast.walk(tree)
    )
    assert installation_path().endswith("installation.json")


def test_lbtpack_install_security_and_remove(tmp_path: Path) -> None:
    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    sp_dir = layout["sp_dir"]
    sync_sdk_configs(home, site_packages=sp_dir)

    # 1. Path traversal rejected before any writes.
    bad_trav = _build_lbtpack(
        tmp_path / "trav.lbtpack",
        {"../escape.txt": b"evil"},
        runtime_updates={},
    )
    with pytest.raises(ValueError, match="traversal|escapes"):
        install_pack(bad_trav, home=home, site_packages=sp_dir)
    assert not (tmp_path / "escape.txt").exists()

    # 2. Absolute path rejected.
    bad_abs = _build_lbtpack(
        tmp_path / "abs.lbtpack",
        {"C:/temp/evil.txt": b"evil"},
        runtime_updates={},
    )
    with pytest.raises(ValueError, match="Absolute|forbidden"):
        install_pack(bad_abs, home=home, site_packages=sp_dir)

    # 3. Wrong platform rejected.
    bad_plat = _build_lbtpack(
        tmp_path / "plat.lbtpack",
        {"runtimes/urbanopt-cli-1.4.0/VERSION": b"1.4.0"},
        platform_name="linux-x64" if os.name == "nt" else "win-x64",
    )
    with pytest.raises(ValueError, match="Incompatible pack platform"):
        install_pack(bad_plat, home=home, site_packages=sp_dir)

    # 4. Incompatible OpenStudio version rejected.
    bad_os = _build_lbtpack(
        tmp_path / "bad_os.lbtpack",
        {"runtimes/urbanopt-cli-1.4.0/VERSION": b"1.4.0"},
        compatible_openstudio="3.10.0",
    )
    with pytest.raises(ValueError, match="requires OpenStudio"):
        install_pack(bad_os, home=home, site_packages=sp_dir)

    # 5. SHA-256 mismatch rejected BEFORE any file is extracted.
    bad_sha = _build_lbtpack(
        tmp_path / "bad_sha.lbtpack",
        {
            "runtimes/urbanopt-cli-1.4.0/VERSION": b"1.4.0",
            "runtimes/urbanopt-cli-1.4.0/gems/Gemfile": b"source 'https://rubygems.org'\n",
        },
        corrupt_sha_for="runtimes/urbanopt-cli-1.4.0/gems/Gemfile",
    )
    with pytest.raises(ValueError, match="SHA-256 verification failed"):
        install_pack(bad_sha, home=home, site_packages=sp_dir)
    assert not (home / "runtimes" / "urbanopt-cli-1.4.0").exists()

    # 6. Valid pack installs, updates runtime.json + dragonfly_energy/config.json, and cleanly removes.
    keep_marker = home / "runtimes" / "openstudio" / "3.11.0" / "bin" / "keep.txt"
    keep_marker.write_text("core", encoding="utf-8")

    good_pack = _build_lbtpack(
        tmp_path / "urbanopt.lbtpack",
        {
            "runtimes/urbanopt-cli-1.4.0/gems/Gemfile": b"source 'https://rubygems.org'\n",
            "runtimes/urbanopt-cli-1.4.0/ruby/bin/ruby.exe": b"ruby",
            "runtimes/openstudio/3.11.0/Ruby/openstudio.rb": b"# os ruby\n",
        },
        runtime_updates={"urbanopt_cli_path": "runtimes/urbanopt-cli-1.4.0"},
    )
    res = install_pack(good_pack, home=home, site_packages=sp_dir)
    assert res["status"] == "installed"
    assert res["file_count"] == 3
    assert (home / "runtimes" / "openstudio" / "3.11.0" / "Ruby" / "openstudio.rb").is_file()
    assert (home / "config" / "packs" / "urbanopt.json").is_file()

    df_cfg = json.loads((sp_dir / "dragonfly_energy" / "config.json").read_text(encoding="utf-8"))
    assert Path(df_cfg["urbanopt_cli_path"]).resolve() == (home / "runtimes" / "urbanopt-cli-1.4.0").resolve()

    listed = list_packs(home)
    assert len(listed) == 1 and listed[0]["name"] == "urbanopt"

    # Re-install without --force raises FileExistsError.
    with pytest.raises(FileExistsError):
        install_pack(good_pack, home=home, site_packages=sp_dir)

    # Remove deletes ONLY pack files and empty parent dirs, leaving core OpenStudio files intact.
    rm_res = remove_pack("urbanopt", home=home, site_packages=sp_dir)
    assert rm_res["status"] == "removed"
    assert rm_res["removed_count"] == 3
    assert not (home / "runtimes" / "urbanopt-cli-1.4.0").exists()
    assert not (home / "runtimes" / "openstudio" / "3.11.0" / "Ruby").exists()
    assert keep_marker.is_file()
    df_cfg_after = json.loads((sp_dir / "dragonfly_energy" / "config.json").read_text(encoding="utf-8"))
    assert df_cfg_after["urbanopt_cli_path"] == ""


def test_ladybug_tools_config_matrix_des_tuple_urbanopt_paths_and_runtime_source(tmp_path: Path) -> None:
    assert REQUIRED_RUNTIME_VERSIONS == {
        "radiance": "5.4",
        "openstudio": "3.11.0",
        "energyplus": "25.2.0",
        "urbanopt": "1.4.0",
        "ironbug_console": "1.26",
    }
    assert OPENSTUDIO_ENERGYPLUS_VERSIONS == {"3.11.0": "25.2.0"}

    # _des_gmt_config() must format tuple (0, 13, 0) as "0.13.0", NOT "(0, 13, 0)".
    fake_sp = tmp_path / "site-packages"
    (fake_sp / "geojson_modelica_translator-0.13.0.dist-info").mkdir(parents=True)
    (fake_sp / "ThermalNetwork-0.5.0.dist-info").mkdir(parents=True)
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    exe_ext = ".exe" if os.name == "nt" else ""
    (scripts / f"uo_des{exe_ext}").write_bytes(b"")
    (scripts / f"thermalnetwork{exe_ext}").write_bytes(b"")
    mbl = tmp_path / "lbt" / "resources" / "mbl"
    mbl.mkdir(parents=True)
    (mbl / "version.txt").write_text("12.0.0\n", encoding="utf-8")

    with (
        mock.patch(
            "garden.ladybug_tools_config.hb_folders",
            SimpleNamespace(python_scripts_path=str(scripts), python_package_path=str(fake_sp)),
        ),
        mock.patch(
            "garden.ladybug_tools_config.dragonfly_energy_folders",
            SimpleNamespace(UO_GMT_VERSION=(0, 13, 0), UO_TN_VERSION=(0, 5, 0), MBL_VERSION=(12, 0, 0), urbanopt_cli_path=None),
        ),
        mock.patch(
            "garden.ladybug_tools_config.lb_folders",
            SimpleNamespace(ladybug_tools_folder=str(tmp_path / "lbt")),
        ),
    ):
        des_cfg = _des_gmt_config()
    assert des_cfg["available"] is True
    assert des_cfg["packages"]["geojson_modelica_translator"]["required_version"] == "0.13.0"
    assert des_cfg["packages"]["thermalnetwork"]["required_version"] == "0.5.0"
    assert des_cfg["modelica_buildings_library"]["required_version"] == "12.0.0"

    # _urbanopt_path_updates resolves deduplicated OpenStudio/Ruby and prepends <os_root>/bin to PATH and RUBY_DLL_PATH.
    uo_cli = tmp_path / "urbanopt-cli-1.4.0"
    (uo_cli / "ruby" / "bin").mkdir(parents=True)
    (uo_cli / "gems" / "ruby" / "3.2.0" / "bin").mkdir(parents=True)
    (uo_cli / "gems" / "Gemfile").write_text("", encoding="utf-8")
    os_root = tmp_path / "openstudio-3.11.0"
    (os_root / "bin").mkdir(parents=True)
    (os_root / "Ruby").mkdir(parents=True)

    updates = _urbanopt_path_updates(str(uo_cli), openstudio_path=str(os_root / "bin"))
    assert updates["prepend"][0] == str(os_root / "bin")
    assert updates["env"]["RUBYLIB"] == str(os_root / "Ruby")
    dll_parts = updates["env"]["RUBY_DLL_PATH"].split(os.pathsep)
    assert str(os_root / "bin") in dll_parts
    assert str(os_root / "Ruby") in dll_parts


def test_self_contained_ironbug_bridge_detection_and_runtime_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    bridge_dir = tmp_path / "sc_bridge"
    bridge_dir.mkdir()
    exe_name = "IronbugBridge.exe" if os.name == "nt" else "IronbugBridge"
    bridge_exe = bridge_dir / exe_name
    bridge_dll = bridge_dir / "IronbugBridge.dll"
    bridge_exe.write_bytes(b"exe")
    bridge_dll.write_bytes(b"dll")
    (bridge_dir / "coreclr.dll").write_bytes(b"clr")
    (bridge_dir / "IronbugBridge.runtimeconfig.json").write_text(
        json.dumps({"runtimeOptions": {"tfm": "net8.0", "includedFrameworks": [{"name": "Microsoft.NETCore.App", "version": "8.0.4"}]}}),
        encoding="utf-8",
    )
    assert is_self_contained_bridge_dir(bridge_dir) is True

    fw_dir = tmp_path / "fw_bridge"
    fw_dir.mkdir()
    (fw_dir / exe_name).write_bytes(b"apphost")
    (fw_dir / "IronbugBridge.dll").write_bytes(b"dll")
    (fw_dir / "IronbugBridge.runtimeconfig.json").write_text(
        json.dumps({"runtimeOptions": {"tfm": "net8.0", "framework": {"name": "Microsoft.NETCore.App", "version": "8.0.0"}}}),
        encoding="utf-8",
    )
    assert is_self_contained_bridge_dir(fw_dir) is False

    # Resolves self-contained IronbugBridge.exe even with NO dotnet on PATH.
    with (
        mock.patch("garden.ironbug.runtime.resolve_ironbug_dir", return_value=layout["ib_dir"]),
        mock.patch("garden.ironbug.runtime.resolve_ironbug_console_exe", return_value=layout["ib_dir"] / f"Ironbug.Console{'.exe' if os.name == 'nt' else ''}"),
        mock.patch("garden.ironbug.runtime.resolve_openstudio_csharp_dir", return_value=layout["os_cs"]),
        mock.patch("garden.ironbug.runtime.shutil.which", return_value=None),
        mock.patch("garden.ironbug.runtime._repo_or_packaged_bridge_dll", return_value=bridge_dll),
    ):
        paths = resolve_runtime_paths(require_openstudio=True)
        assert paths.is_self_contained is True
        assert paths.bridge_exe == bridge_exe
        assert paths.dotnet_exe is None

    # Verify IronbugBridgeClient invokes bridge_exe directly without dotnet when self-contained.
    client = IronbugBridgeClient(paths)
    launched_cmds: list[list[str]] = []

    class _FakeProc:
        def __init__(self, cmd):
            launched_cmds.append(cmd)
            self.stdin = mock.MagicMock()
            self.stdout = mock.MagicMock()
            self.stderr = mock.MagicMock()
            self.stdout.readline.side_effect = ['{"id":"1","ok":true,"result":{"ok":true}}\n', ""]
            self.stderr.readline.return_value = ""

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    with mock.patch("garden.ironbug.client.subprocess.Popen", side_effect=lambda cmd, **kw: _FakeProc(cmd)):
        client.call("health")
        client.close(force=True)
    assert launched_cmds[0][0] == str(bridge_exe)
    assert "--serve" in launched_cmds[0]

    # Verify get_ladybug_tools_config annotates runtime_source ("bundled" vs "external_override") and bridge_self_contained.
    monkeypatch.setenv("LADYBUG_TOOLS_MCP_HOME", str(home))
    ext_rad = tmp_path / "external_radiance"
    (ext_rad / "bin").mkdir(parents=True)
    (ext_rad / "lib").mkdir(parents=True)
    with (
        mock.patch("garden.ladybug_tools_config._select_openstudio_config", return_value={
            "name": "openstudio", "source": "sdk_config", "path": str(layout["os_bin"]), "path_exists": True,
            "exe": str(layout["os_bin"] / "openstudio.exe"), "exe_exists": True, "version": "3.11.0", "version_status": "compatible",
            "version_requirement": {"required_version": "3.11.0"},
        }),
        mock.patch("garden.ladybug_tools_config._radiance_config", return_value={
            "name": "radiance", "source": "sdk_config", "path": str(ext_rad), "path_exists": True,
            "bin_path": str(ext_rad / "bin"), "bin_path_exists": True, "lib_path": str(ext_rad / "lib"), "lib_path_exists": True,
            "version": "5.4", "version_status": "compatible", "version_requirement": {"required_version": "5.4"},
        }),
        mock.patch("garden.ironbug.runtime._repo_or_packaged_bridge_dll", return_value=bridge_dll),
        mock.patch("garden.ironbug.runtime._repo_or_packaged_bridge_exe", return_value=bridge_exe),
        mock.patch("garden.ironbug.runtime.resolve_ironbug_dir", return_value=layout["ib_dir"]),
        mock.patch("garden.ironbug.runtime.resolve_openstudio_csharp_dir", return_value=layout["os_cs"]),
    ):
        cfg = get_ladybug_tools_config()
    engines = cfg["summary_view"]["engines"]
    assert engines["openstudio"]["runtime_source"] == "bundled"
    assert engines["radiance"]["runtime_source"] == "external_override"
    assert engines["ironbug_console"]["bridge_exe_exists"] is True
    assert engines["ironbug_console"]["bridge_self_contained"] is True


def test_doctor_standard_tolerates_missing_optional_urbanopt_and_detects_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_user = tmp_path / "userprofile"
    fake_user.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_user))
    monkeypatch.setenv("HOME", str(fake_user))
    monkeypatch.delenv("LADYBUG_TOOLS_MCP_INSTALLATION", raising=False)

    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    sp_dir = layout["sp_dir"]
    sync_sdk_configs(home, site_packages=sp_dir)
    write_installation_records(home, gardens_root=tmp_path / "Gardens", site_packages=sp_dir)

    fake_rune = tmp_path / "lbt-rune-viewer.exe"
    fake_rune.write_bytes(b"rune")

    healthy_engines = {
        "radiance": {"name": "radiance", "path": str(layout["rad_root"]), "path_exists": True, "bin_path": str(layout["rad_bin"]), "bin_path_exists": True, "lib_path_exists": True, "version": "5.4", "version_status": "compatible"},
        "openstudio": {"name": "openstudio", "path": str(layout["os_bin"]), "path_exists": True, "exe": str(layout["os_bin"] / "openstudio.exe"), "exe_exists": True, "version": "3.11.0", "version_status": "compatible"},
        "energyplus": {"name": "energyplus", "path": str(layout["os_ep"]), "path_exists": True, "exe": str(layout["os_ep"] / "energyplus.exe"), "exe_exists": True, "version": "25.2.0", "version_status": "compatible"},
        "ironbug_console": {"name": "ironbug_console", "path": str(layout["ib_dir"]), "path_exists": True, "exe_exists": True, "ironbug_hvac_dll_exists": True, "openstudio_csharp_dll_exists": True, "bridge_self_contained": True, "bridge_exe_exists": True, "dotnet_available": False, "version": "1.26.1.0", "version_status": "compatible", "compatibility_warnings": []},
        "therm": {"name": "therm", "available": True, "version": 1, "kernel_commit": "abc", "packages": {"gmsh": True}},
        "urbanopt": {"name": "urbanopt", "available": False, "path_exists": False, "version_status": "unknown"},
        "des_gmt": {"name": "des_gmt", "available": False},
    }

    with (
        mock.patch("garden.ladybug_tools_config.get_ladybug_tools_config", return_value={"summary_view": {"engines": healthy_engines}}),
        mock.patch("web_view.launcher.discover_rune_viewer_binary", return_value=fake_rune),
    ):
        report = run_doctor(home, smoke=False, site_packages=sp_dir)
    assert report["ok"] is True, report
    assert "urbanopt" in report["checks"]["runtime_engines"]["optional_not_installed"]
    assert "des_gmt" in report["checks"]["runtime_engines"]["optional_not_installed"]

    # Mutate one SDK config to introduce drift -> doctor fails.
    (sp_dir / "honeybee_radiance" / "config.json").write_text('{"radiance_path": ""}', encoding="utf-8")
    with (
        mock.patch("garden.ladybug_tools_config.get_ladybug_tools_config", return_value={"summary_view": {"engines": healthy_engines}}),
        mock.patch("web_view.launcher.discover_rune_viewer_binary", return_value=fake_rune),
    ):
        drifted = run_doctor(home, smoke=False, site_packages=sp_dir)
    assert drifted["ok"] is False
    assert "honeybee_radiance" in drifted["checks"]["sdk_config_sync"]["drift"]


def test_doctor_smoke_probes_with_and_without_urbanopt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_user = tmp_path / "userprofile"
    fake_user.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_user))
    monkeypatch.setenv("HOME", str(fake_user))
    monkeypatch.delenv("LADYBUG_TOOLS_MCP_INSTALLATION", raising=False)

    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    sp_dir = layout["sp_dir"]
    sync_sdk_configs(home, site_packages=sp_dir)
    write_installation_records(home, gardens_root=tmp_path / "Gardens", site_packages=sp_dir)

    fake_rune = tmp_path / "lbt-rune-viewer.exe"
    fake_rune.write_bytes(b"rune")
    bridge_exe = tmp_path / "IronbugBridge.exe"
    bridge_exe.write_bytes(b"bridge")
    bridge_dll = tmp_path / "IronbugBridge.dll"
    bridge_dll.write_bytes(b"dll")

    healthy_engines = {
        "radiance": {"name": "radiance", "path": str(layout["rad_root"]), "path_exists": True, "bin_path": str(layout["rad_bin"]), "bin_path_exists": True, "lib_path_exists": True, "version": "5.4", "version_status": "compatible"},
        "openstudio": {"name": "openstudio", "path": str(layout["os_bin"]), "path_exists": True, "exe": str(layout["os_bin"] / ("openstudio.exe" if os.name == "nt" else "openstudio")), "exe_exists": True, "version": "3.11.0", "version_status": "compatible"},
        "energyplus": {"name": "energyplus", "path": str(layout["os_ep"]), "path_exists": True, "exe": str(layout["os_ep"] / ("energyplus.exe" if os.name == "nt" else "energyplus")), "exe_exists": True, "version": "25.2.0", "version_status": "compatible"},
        "ironbug_console": {"name": "ironbug_console", "path": str(layout["ib_dir"]), "path_exists": True, "exe_exists": True, "ironbug_hvac_dll_exists": True, "openstudio_csharp_dll_exists": True, "bridge_self_contained": True, "bridge_exe_exists": True, "dotnet_available": False, "version": "1.26.1.0", "version_status": "compatible", "compatibility_warnings": []},
        "therm": {"name": "therm", "available": True, "version": 1, "kernel_commit": "abc", "packages": {"gmsh": True}},
        "urbanopt": {"name": "urbanopt", "available": False, "path_exists": False, "version_status": "unknown"},
        "des_gmt": {"name": "des_gmt", "available": False},
    }

    fake_ib_paths = SimpleNamespace(
        ironbug_dir=layout["ib_dir"],
        ironbug_exe=None,
        openstudio_csharp_dir=layout["os_cs"],
        dotnet_exe=None,
        bridge_dll=bridge_dll,
        bridge_exe=bridge_exe,
        is_self_contained=True,
    )

    seen_cmds: list[list[str]] = []

    def _fake_subprocess_run(cmd, **kwargs):
        del kwargs
        seen_cmds.append(list(cmd))
        exe_name = Path(cmd[0]).name.lower()
        if "openstudio" in exe_name:
            return SimpleNamespace(returncode=0, stdout="3.11.0+241b8abb4d\n", stderr="")
        if "energyplus" in exe_name:
            return SimpleNamespace(returncode=0, stdout="EnergyPlus, Version 25.2.0\n", stderr="")
        if "rtrace" in exe_name:
            return SimpleNamespace(returncode=0, stdout="RADIANCE 5.4 2023-11-05 LBNL\n", stderr="")
        if "evalglare" in exe_name:
            if "-version" in cmd:
                return SimpleNamespace(returncode=1, stdout="", stderr="Usage: evalglare [-v] picfile\n")
            return SimpleNamespace(returncode=1, stdout="evalglare 2.10 release 25.06.2020 by EPFL\n", stderr="")
        if "ironbugbridge" in exe_name:
            return SimpleNamespace(returncode=0, stdout='{"id":"health","ok":true,"result":{"ok":true}}\n', stderr="")
        if "rune" in exe_name:
            return SimpleNamespace(returncode=0, stdout="lbt-rune-viewer 0.1.0 (protocol v1)\n", stderr="")
        if "bundle" in exe_name:
            return SimpleNamespace(returncode=0, stdout="1.4.0-rc1\n", stderr="")
        raise AssertionError(f"Unexpected smoke probe command: {cmd}")

    with (
        mock.patch("garden.ladybug_tools_config.get_ladybug_tools_config", return_value={"summary_view": {"engines": healthy_engines}}),
        mock.patch("web_view.launcher.discover_rune_viewer_binary", return_value=fake_rune),
        mock.patch("garden.ironbug.runtime.resolve_runtime_paths", return_value=fake_ib_paths),
        mock.patch("ladybug_tools_mcp.runtime_home.subprocess.run", side_effect=_fake_subprocess_run),
    ):
        smoke_report = run_doctor(home, smoke=True, site_packages=sp_dir)

    assert smoke_report["ok"] is True, smoke_report
    probes = smoke_report["smoke_probes"]
    assert probes is not None
    assert probes["openstudio"]["ok"] is True
    assert probes["energyplus"]["ok"] is True
    assert probes["rtrace"]["ok"] is True
    assert probes["evalglare"]["ok"] is True
    assert probes["ironbug_bridge"]["ok"] is True
    assert probes["lbt_rune_viewer"]["ok"] is True
    assert probes["urbanopt"]["skipped"] is True

    # Now enable urbanopt pack receipt and verify bundle exec uo --version probe runs and passes.
    (home / "config" / "packs").mkdir(parents=True, exist_ok=True)
    uo_cli = home / "runtimes" / "urbanopt-cli-1.4.0"
    (uo_cli / "gems" / "ruby" / "3.2.0" / "bin").mkdir(parents=True, exist_ok=True)
    (uo_cli / "gems" / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
    (home / "config" / "packs" / "urbanopt.json").write_text(
        json.dumps({"name": "urbanopt", "version": "1.4.0-rc1", "platform": "win-x64", "files": []}),
        encoding="utf-8",
    )
    healthy_engines["urbanopt"] = {
        "name": "urbanopt",
        "available": True,
        "path": str(uo_cli),
        "path_exists": True,
        "version": "1.4.0",
        "version_status": "compatible",
        "cli_gem_bundle": {"path": str(uo_cli / "gems" / "ruby" / "3.2.0"), "exists": True},
        "cli_runtime_gemfile": {"path": str(uo_cli / "gems" / "Gemfile"), "exists": True},
        "path_updates": {"prepend": [], "env": {}},
    }
    seen_cmds.clear()
    with (
        mock.patch("garden.ladybug_tools_config.get_ladybug_tools_config", return_value={"summary_view": {"engines": healthy_engines}}),
        mock.patch("web_view.launcher.discover_rune_viewer_binary", return_value=fake_rune),
        mock.patch("garden.ironbug.runtime.resolve_runtime_paths", return_value=fake_ib_paths),
        mock.patch("ladybug_tools_mcp.runtime_home.subprocess.run", side_effect=_fake_subprocess_run),
    ):
        uo_smoke = run_doctor(home, smoke=True, site_packages=sp_dir)
    assert uo_smoke["ok"] is True, uo_smoke
    assert uo_smoke["smoke_probes"]["urbanopt"]["ok"] is True
    assert not uo_smoke["smoke_probes"]["urbanopt"].get("skipped")
    assert any(cmd[-3:] == ["exec", "uo", "--version"] for cmd in seen_cmds)


def test_cli_removed_client_presets_and_subcommands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not (_REPO_ROOT / "src" / "ladybug_tools_mcp_clients.py").exists()
    assert importlib.util.find_spec("ladybug_tools_mcp_clients") is None

    for obsolete in ("install", "uninstall", "clients"):
        with pytest.raises(SystemExit):
            ladybug_tools_mcp_cli.main([obsolete])

    home = tmp_path / "lbt-mcp"
    layout = _populate_minimal_home(home)
    fake_user = tmp_path / "userprofile"
    fake_user.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_user))
    monkeypatch.setenv("HOME", str(fake_user))
    monkeypatch.delenv("LADYBUG_TOOLS_MCP_INSTALLATION", raising=False)

    assert ladybug_tools_mcp_cli.main(
        ["runtime", "sync", "--home", str(home), "--site-packages", str(layout["sp_dir"]), "--gardens", str(tmp_path / "Gardens")]
    ) == 0
    sync_out = json.loads(capsys.readouterr().out)
    assert sync_out["status"] == "synced"

    assert ladybug_tools_mcp_cli.main(["status", "--home", str(home)]) == 0
    status_out = json.loads(capsys.readouterr().out)
    assert status_out["status"] == "installed"

    custom_rad = tmp_path / "custom_rad"
    (custom_rad / "bin").mkdir(parents=True)
    (custom_rad / "bin" / ("rad.exe" if os.name == "nt" else "rad")).write_bytes(b"rad")
    assert ladybug_tools_mcp_cli.main(
        ["runtime", "set", "radiance_path", str(custom_rad), "--home", str(home), "--site-packages", str(layout["sp_dir"])]
    ) == 0
    _ = capsys.readouterr()
    assert json.loads((layout["sp_dir"] / "honeybee_radiance" / "config.json").read_text(encoding="utf-8"))["radiance_path"] == str(custom_rad.resolve())

    assert ladybug_tools_mcp_cli.main(
        ["runtime", "reset", "--home", str(home), "--site-packages", str(layout["sp_dir"])]
    ) == 0
    _ = capsys.readouterr()
    assert Path(json.loads((layout["sp_dir"] / "honeybee_radiance" / "config.json").read_text(encoding="utf-8"))["radiance_path"]).resolve() == layout["rad_root"].resolve()

    # Verify default serve sets env defaults and produces zero stdout noise before FastMCP runs.
    called_run: list[bool] = []
    fake_mcp = SimpleNamespace(run=lambda show_banner=True: called_run.append(show_banner))
    monkeypatch.delenv("LADYBUG_TOOLS_GARDENS_ROOT", raising=False)
    with mock.patch("ladybug_tools_mcp.server.mcp", fake_mcp):
        assert ladybug_tools_mcp_cli.main(["serve", "--home", str(home)]) == 0
    assert called_run == [False]
    assert capsys.readouterr().out == ""
    assert os.environ["LADYBUG_TOOLS_GARDENS_ROOT"] == str((tmp_path / "Gardens").resolve())


def test_rust_launcher_spawns_isolated_cli_with_zero_stdout_noise(tmp_path: Path) -> None:
    exe_name = "lbt-mcp.exe" if os.name == "nt" else "lbt-mcp"
    launcher_bin = _REPO_ROOT / "scripts" / "distribution" / "launcher" / "target" / "release" / exe_name
    assert launcher_bin.is_file(), f"Missing built Rust launcher: {launcher_bin}"

    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    (home / "app").mkdir(parents=True)
    (home / "config").mkdir(parents=True)
    installed_launcher = home / "bin" / exe_name
    shutil.copy2(launcher_bin, installed_launcher)

    # 1. Point current.json at the active test Python (outside home -> repo .venv/pyvenv.cfg stays untouched).
    py_exe = Path(sys.executable).resolve()
    (home / "app" / "current.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "1.2.3",
                "python": str(py_exe),
            }
        ),
        encoding="utf-8",
    )

    fake_user = tmp_path / "userprofile"
    fake_user.mkdir()
    env = os.environ.copy()
    env["USERPROFILE"] = str(fake_user)
    env["HOME"] = str(fake_user)
    env.pop("LADYBUG_TOOLS_MCP_HOME", None)
    env.pop("LADYBUG_TOOLS_MCP_INSTALLATION", None)

    res = subprocess.run(
        [str(installed_launcher), "status", "--home", str(home)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["home"] == str(home.resolve())

    # Verify non-zero exit code forwarding when invalid subcommand is passed.
    bad = subprocess.run(
        [str(installed_launcher), "unknown_subcommand_xyz"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert bad.returncode != 0
    assert bad.stdout == ""

    # 2. Verify pyvenv.cfg auto-relocation when venv lives inside <home>.
    home2 = tmp_path / "home2"
    (home2 / "bin").mkdir(parents=True)
    (home2 / "app" / "releases" / "1.2.3" / "venv" / ("Scripts" if os.name == "nt" else "bin")).mkdir(parents=True)
    (home2 / "runtimes" / "python").mkdir(parents=True)
    installed2 = home2 / "bin" / exe_name
    shutil.copy2(launcher_bin, installed2)

    py_home2 = home2 / "runtimes" / "python" / "3.12"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(py_home2), sys.base_prefix], check=True, capture_output=True)
    else:
        os.symlink(sys.base_prefix, py_home2)

    venv_dir2 = home2 / "app" / "releases" / "1.2.3" / "venv"
    venv_py2 = venv_dir2 / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    shutil.copy2(py_exe, venv_py2)
    sp_link = venv_dir2 / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    sp_link.parent.mkdir(parents=True, exist_ok=True)
    src_sp = Path(sys.prefix) / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(sp_link), str(src_sp)], check=True, capture_output=True)
    else:
        os.symlink(src_sp, sp_link)

    (venv_dir2 / "pyvenv.cfg").write_text(
        "home = C:\\StaleBuildMachine\\runtimes\\python\\3.12\n"
        "include-system-site-packages = false\n",
        encoding="utf-8",
    )
    (home2 / "app" / "current.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "1.2.3",
                "python": f"app/releases/1.2.3/venv/{'Scripts/python.exe' if os.name == 'nt' else 'bin/python'}",
                "python_home": "runtimes/python/3.12",
            }
        ),
        encoding="utf-8",
    )

    res2 = subprocess.run(
        [str(installed2), "status"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert res2.returncode == 0, res2.stderr
    payload2 = json.loads(res2.stdout)
    assert payload2["home"] == str(home2.resolve())
    assert payload2["state"] == str((home2 / "config" / "installation.json").resolve())
    relocated_cfg = (venv_dir2 / "pyvenv.cfg").read_text(encoding="utf-8")
    assert f"home = {py_home2}" in relocated_cfg
