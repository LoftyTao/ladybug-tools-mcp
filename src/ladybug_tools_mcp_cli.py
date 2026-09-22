"""Local MCP launcher and installer. Environment management belongs to uv."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from zipfile import ZipFile
from email.parser import Parser

from ladybug_tools_mcp import __version__
from flowerpot.installation import installation_path, read_installation


PACKAGE = "ladybug-tools-mcp"
SKILL = "ladybug-tools-mcp-use"


def configure_stdio() -> None:
    """Keep generated configuration printable on Windows console encodings."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def absolute(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ladybug-tools-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def file_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def uv_command() -> str:
    executable = shutil.which("uv")
    if not executable:
        raise RuntimeError("Install uv first: https://docs.astral.sh/uv/getting-started/installation/")
    return str(absolute(executable))


def tool_environment(directory: Path) -> dict[str, str]:
    return {**os.environ, "UV_TOOL_DIR": str(directory), "UV_TOOL_BIN_DIR": str(directory / "bin")}


def tool_python(directory: Path) -> Path:
    return directory / PACKAGE / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def isolated_instruction(command: str) -> str:
    return f"uvx --isolated --python 3.12 --prerelease allow {PACKAGE}@{__version__} {command}"


def check_not_running_in_target(python: Path, command: str) -> None:
    # Compare paths without following POSIX venv symlinks to the shared base Python.
    if os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(str(python.absolute())):
        raise RuntimeError("Run the installer outside its target environment:\n" + isolated_instruction(command))


def ask_path(label: str, default: Path) -> Path:
    return absolute(input(f"{label} [{default}]: ").strip() or default)


def ask_yes(label: str, default: bool) -> bool:
    answer = input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not answer:
        return default
    if answer not in {"y", "yes", "n", "no"}:
        raise ValueError("Answer yes or no.")
    return answer in {"y", "yes"}


def grasshopper_directory() -> Path:
    if sys.platform != "win32":
        raise RuntimeError("Flowerpot's verified first release supports Windows with Rhino 8.")
    rhino = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Rhino 8/System/Rhino.exe"
    if not rhino.is_file():
        raise RuntimeError("Install Rhino 8 before selecting Flowerpot / Grasshopper.")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is unavailable; cannot locate Grasshopper UserObjects.")
    return absolute(Path(appdata) / "Grasshopper/UserObjects/Flowerpot")


def configuration(python: Path, gardens: Path, state: Path) -> dict:
    return {
        "command": str(python),
        "args": ["-I", "-m", "ladybug_tools_mcp.server"],
        "env": {
            "LADYBUG_TOOLS_GARDENS_ROOT": str(gardens),
            "LADYBUG_TOOLS_MCP_INSTALLATION": str(state),
        },
        "startup_timeout_sec": 60,
        "required": True,
    }


def codex_update(path: Path, server: dict, previous: dict, replace: bool):
    import tomlkit

    content = file_bytes(path)
    document = tomlkit.parse(content.decode("utf-8-sig") if content else "")
    servers = document.setdefault("mcp_servers", tomlkit.table())
    current = servers.get(PACKAGE)
    prior = previous.get("codex") or {}
    owned = prior.get("path") == str(path) and current == prior.get("installed")
    if current is not None and current != server and not owned and not replace:
        raise FileExistsError(f"Existing MCP configuration differs: {path}. Use --replace to back it up and replace this server only.")
    original = prior.get("original") if owned else (current.unwrap() if current is not None else None)
    servers[PACKAGE] = server
    updated = tomlkit.dumps(document).encode("utf-8")
    assert tomllib.loads(updated.decode("utf-8"))["mcp_servers"][PACKAGE] == server
    return updated, {"path": str(path), "installed": server, "original": original}, content


def owned_asset_paths(record: dict) -> dict[str, dict]:
    result = {}
    for item in record.get("assets", []):
        kind = item["kind"]
        if kind == "skill":
            root = absolute(record["skills_dir"]) / SKILL
        elif kind == "grasshopper":
            root = absolute(record["grasshopper_dir"])
        else:
            raise ValueError("Unknown installed asset kind.")
        path = absolute(item["path"])
        path.relative_to(root)
        if path == root:
            raise ValueError("An installation asset must be a file, not its root directory.")
        result[str(path)] = item
    return result


def asset_updates(resources: Path, skills: Path | None, gh: Path | None, previous: dict, replace: bool):
    old = owned_asset_paths(previous)
    changes, assets, kept, expected = {}, [], [], {}
    groups = []
    if skills:
        groups.append((resources / "skills" / SKILL, skills / SKILL, "skill"))
    if gh:
        source = resources / "grasshopper"
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if manifest["version"] != __version__ or len(manifest["components"]) != 6:
            raise ValueError("Grasshopper assets do not match this release.")
        for entry in manifest["components"]:
            asset = source / entry["file"]
            asset.resolve().relative_to(source.resolve())
            if digest(asset.read_bytes()) != entry["sha256"]:
                raise ValueError("Grasshopper asset checksum mismatch: " + entry["file"])
        groups.append((source, gh, "grasshopper"))
    for source, destination, kind in groups:
        if not source.is_dir():
            raise FileNotFoundError(f"Distribution assets missing: {source}")
        for item in sorted(source.rglob("*")):
            if not item.is_file():
                continue
            path = destination / item.relative_to(source)
            data = item.read_bytes()
            existing = file_bytes(path)
            known = old.get(str(path), {}).get("sha256")
            if existing is not None and existing != data and digest(existing) != known and not replace:
                raise FileExistsError(f"Modified or unmanaged asset: {path}. Use --replace to keep a backup and replace it.")
            if existing != data:
                changes[path] = data
                expected[path] = existing
            assets.append({"path": str(path), "kind": kind, "sha256": digest(data)})
    wanted = {item["path"] for item in assets}
    for name, item in old.items():
        if name in wanted:
            continue
        if item["kind"] == "skill" and skills is None:
            assets.append(item)
            continue
        path = Path(name)
        content = file_bytes(path)
        if content is not None:
            if digest(content) == item["sha256"]:
                changes[path] = None
                expected[path] = content
            else:
                kept.append(name)
    return changes, assets, kept, expected


def commit_files(changes: dict[Path, bytes | None], before: dict[Path, bytes | None]) -> list[str]:
    """Back up existing files and roll back partial writes on a local failure."""
    for path in changes:
        if path.is_symlink() or file_bytes(path) != before[path]:
            raise RuntimeError(f"File changed during installation or is a symlink; retry: {path}")
    backups, written = [], []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        for path, content in changes.items():
            if path.is_symlink():
                raise ValueError(f"Refusing to replace a symlink: {path}")
            if file_bytes(path) != before[path]:
                raise RuntimeError(f"File changed during installation; retry: {path}")
            if before[path] is not None:
                backup = path.with_name(path.name + ".ladybug-backup-" + stamp)
                atomic_write(backup, before[path])
                backups.append(str(backup))
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            if before[path] is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, before[path])
        raise
    return backups


def runtime_details(python: Path) -> dict:
    code = (
        "import json, pathlib, ladybug_tools_mcp; "
        "import ladybug_tools_mcp.server; "
        "p=pathlib.Path(ladybug_tools_mcp.__file__).resolve(); "
        "print(json.dumps({'version':ladybug_tools_mcp.__version__,"
        "'package_root':str(p.parent.parent),'resources':str(p.parent/'resources')}))"
    )
    completed = subprocess.run([str(python), "-I", "-c", code], check=True, text=True, capture_output=True)
    details = json.loads(completed.stdout)
    if details["version"] != __version__:
        raise ValueError("Installed MCP version does not match the installer.")
    resources = Path(details["resources"])
    if not (resources / "skills" / SKILL / "SKILL.md").is_file() or not any((resources / "weather").glob("*/*.epw")):
        raise ValueError("Installed wheel is missing Skills or weather resources.")
    return details


def wheel_requirement(path: Path | None) -> str:
    if path is None:
        return f"{PACKAGE}=={__version__}"
    path = absolute(path)
    with ZipFile(path) as archive:
        entries = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(entries) != 1:
            raise ValueError("Wheel must contain exactly one distribution.")
        metadata = Parser().parsestr(archive.read(entries[0]).decode("utf-8"))
        if metadata["Name"].replace("_", "-") != PACKAGE or metadata["Version"] != __version__:
            raise ValueError("Wheel name/version does not match this installer.")
    return str(path)


def install(args) -> dict:
    configure_stdio()
    state = absolute(args.state)
    state_before = file_bytes(state)
    previous = read_installation(str(state))
    uv = uv_command()
    default_tools = subprocess.run([uv, "tool", "dir"], check=True, capture_output=True, text=True).stdout.strip()
    tools_dir = absolute(args.tool_dir or previous.get("tool_dir") or default_tools)
    gardens = absolute(args.garden_dir or previous.get("gardens_root") or Path.home() / "LadybugTools/Gardens")
    codex = absolute(args.codex_config or (previous.get("codex") or {}).get("path") or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml")
    skills = absolute(args.skills_dir or previous.get("skills_dir") or Path.home() / ".agents/skills")
    if previous.get("codex") and previous["codex"]["path"] != str(codex):
        raise ValueError("Uninstall before changing the managed Codex configuration path.")
    gh_enabled = args.grasshopper if args.grasshopper is not None else bool(previous.get("grasshopper_dir"))
    if not args.yes:
        if not sys.stdin.isatty():
            raise ValueError("Interactive install requires a terminal. Use --yes with explicit options for automation.")
        print(f"Ladybug Tools MCP {__version__}")
        tools_dir = ask_path("Runtime directory", tools_dir)
        gardens = ask_path("Garden directory", gardens)
        args.generate_config = not ask_yes("Configure Codex and install local Skills?", not args.generate_config)
        gh_enabled = ask_yes("Install Flowerpot integration (Grasshopper / Rhino 8 on Windows)?", gh_enabled)
    if args.generate_config and previous.get("assets") and previous.get("skills_dir") != str(skills):
        raise ValueError("Keep the installed Skills directory when only generating configuration.")
    gh = None
    if gh_enabled:
        default_gh = grasshopper_directory()
        gh = absolute(args.grasshopper_dir or previous.get("grasshopper_dir") or default_gh)
        if not args.yes:
            gh = ask_path("Grasshopper component directory", gh)
    python = tool_python(tools_dir)
    check_not_running_in_target(python, "install")
    cache_dir = absolute(subprocess.run([uv, "cache", "dir"], check=True, capture_output=True, text=True).stdout.strip())
    if (
        gardens.is_relative_to(tools_dir)
        or tools_dir.is_relative_to(gardens)
        or gardens.is_relative_to(cache_dir)
        or cache_dir.is_relative_to(gardens)
    ):
        raise ValueError("The Garden directory must be outside the runtime directory and uv cache.")
    if previous and previous["tool_dir"] != str(tools_dir):
        raise ValueError("Uninstall the existing runtime before changing its directory. Gardens are retained.")
    server = configuration(python, gardens, state)
    config_bytes, config_record, config_before = (None, None, None)
    if not args.generate_config:
        config_bytes, config_record, config_before = codex_update(codex, server, previous, args.replace)
    import ladybug_tools_mcp
    resources = Path(ladybug_tools_mcp.__file__).resolve().parent / "resources"
    changes, assets, kept, expected = asset_updates(resources, None if args.generate_config else skills, gh, previous, args.replace)
    if config_bytes is not None and config_before != config_bytes:
        changes[codex] = config_bytes
        expected[codex] = config_before
    command = [uv, "tool", "install", "--python", "3.12", "--prerelease", "allow", "--force"]
    if args.wheel:
        command.extend(["--reinstall-package", PACKAGE])
    command.append(wheel_requirement(args.wheel))
    wheel_hash = digest(absolute(args.wheel).read_bytes()) if args.wheel else None
    details = None
    if previous.get("version") == __version__ and previous.get("wheel_sha256") == wheel_hash:
        try:
            details = runtime_details(python)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if details is None:
        try:
            subprocess.run(command, env=tool_environment(tools_dir), check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError("uv could not prepare the runtime. Close MCP clients and Rhino, check the error above, then retry this command. Client settings and Gardens were retained.") from error
        details = runtime_details(python)
    gardens.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1, "version": __version__, "wheel_sha256": wheel_hash, "tool_dir": str(tools_dir),
        "python": str(python), "package_root": details["package_root"],
        "gardens_root": str(gardens), "skills_dir": str(skills),
        "grasshopper_dir": str(gh) if gh else None,
        "codex": config_record if config_record else previous.get("codex"), "assets": assets,
    }
    changes[state] = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    expected[state] = state_before
    backups = commit_files(changes, expected)
    if args.generate_config:
        import tomlkit
        print(tomlkit.dumps({"mcp_servers": {PACKAGE: server}}))
    return {"version": __version__, "python": str(python), "gardens_root": str(gardens),
            "state": str(state), "codex_configured": not args.generate_config,
            "grasshopper": str(gh) if gh else None, "backups": backups, "preserved_files": kept}


def uninstall(args) -> dict:
    state = absolute(args.state)
    state_before = file_bytes(state)
    record = read_installation(str(state))
    if not record:
        return {"status": "not_installed"}
    python = Path(record["python"])
    tools_dir = absolute(record["tool_dir"])
    if python != tool_python(tools_dir):
        raise ValueError("Installation record has an unexpected Python location.")
    check_not_running_in_target(python, "uninstall")
    if not args.yes and (not sys.stdin.isatty() or not ask_yes("Uninstall MCP and its unmodified integrations? Gardens will remain.", False)):
        return {"status": "cancelled"}
    changes, kept, expected = {}, [], {}
    for name, item in owned_asset_paths(record).items():
        path = Path(name)
        data = file_bytes(path)
        if data is not None:
            if digest(data) == item["sha256"]:
                changes[path] = None
                expected[path] = data
            else:
                kept.append(name)
    codex = record.get("codex")
    if codex:
        import tomlkit
        path = Path(codex["path"])
        data = file_bytes(path)
        if data is not None:
            document = tomlkit.parse(data.decode("utf-8-sig"))
            servers = document.get("mcp_servers", {})
            if servers.get(PACKAGE) == codex["installed"]:
                if codex["original"] is None:
                    del servers[PACKAGE]
                else:
                    servers[PACKAGE] = codex["original"]
                changes[path] = tomlkit.dumps(document).encode("utf-8")
                expected[path] = data
            elif PACKAGE in servers:
                kept.append(str(path))
    # A failed or manually removed runtime must not strand the user's config,
    # Skills, or Garden behind an unremovable installation record.
    if python.exists():
        subprocess.run([uv_command(), "tool", "uninstall", PACKAGE], env=tool_environment(tools_dir), check=True)
    changes[state] = None
    expected[state] = state_before
    backups = commit_files(changes, expected)
    return {"status": "uninstalled", "gardens_root": record["gardens_root"],
            "preserved_files": kept, "backups": backups}


def main(argv=None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(prog=PACKAGE, description="Ladybug Tools MCP server and local installation wizard.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("serve", help="Run the stdio MCP server (default).")
    for name in ("install", "uninstall", "status"):
        command = commands.add_parser(name)
        command.add_argument("--state", default=installation_path(), help="Installation record path (for separate test profiles).")
        if name != "status":
            command.add_argument("--yes", action="store_true", help="Use defaults without interactive prompts; conflicts still fail.")
        if name == "install":
            command.add_argument("--tool-dir", type=Path)
            command.add_argument("--garden-dir", type=Path)
            command.add_argument("--codex-config", type=Path)
            command.add_argument("--skills-dir", type=Path)
            command.add_argument("--grasshopper", action=argparse.BooleanOptionalAction, default=None)
            command.add_argument("--grasshopper-dir", type=Path)
            command.add_argument("--generate-config", action="store_true", help="Install runtime and print Codex settings without changing client settings or local Skills.")
            command.add_argument("--replace", action="store_true", help="Back up and replace conflicting MCP settings or integration files.")
            command.add_argument("--wheel", type=Path, help="Use a local wheel of this version instead of PyPI.")
    args = parser.parse_args(argv)
    if args.command in (None, "serve"):
        settings = read_installation()
        if settings:
            os.environ.setdefault("LADYBUG_TOOLS_GARDENS_ROOT", settings["gardens_root"])
        from ladybug_tools_mcp.server import mcp
        mcp.run(show_banner=False)
        return 0
    try:
        if args.command == "install":
            result = install(args)
        elif args.command == "uninstall":
            result = uninstall(args)
        else:
            result = read_installation(str(absolute(args.state))) or {"status": "not_installed"}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"{PACKAGE}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
