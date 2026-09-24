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
from ladybug_tools_mcp_clients import CLIENTS, render_client


PACKAGE = "lbt-mcp"
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


def validate_grasshopper_manifest(source: Path) -> dict:
    """Validate the packaged Flowerpot index before copying user objects."""
    try:
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("Invalid Grasshopper asset manifest.") from error
    entries = manifest.get("components")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Grasshopper asset manifest is empty.")
    names, files = set(), set()
    for entry in entries:
        name, filename = entry.get("name"), entry.get("file")
        if not isinstance(name, str) or not isinstance(filename, str):
            raise ValueError("Invalid Grasshopper manifest entry.")
        asset = source / filename
        if (
            name in names or filename in files
            or entry.get("category") != "Flowerpot"
            or entry.get("subcategory") != "Flowerpot"
            or entry.get("exposure") not in {2, 4, 8, 16, 32, 64, 128}
            or filename != name + ".ghuser"
            or asset.resolve().parent != source.resolve()
            or not asset.is_file()
        ):
            raise ValueError("Invalid or duplicate Grasshopper manifest entry: " + name)
        names.add(name)
        files.add(filename)
        if digest(asset.read_bytes()) != entry.get("sha256"):
            raise ValueError("Grasshopper asset checksum mismatch: " + filename)
    if {path.name for path in source.glob("*.ghuser")} != files:
        raise ValueError("Grasshopper manifest and user-object files do not match.")
    return manifest


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
    bin_dir = directory / "bin"
    return {**os.environ, "UV_TOOL_DIR": str(directory), "UV_TOOL_BIN_DIR": str(bin_dir),
            "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}


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


def normalize_clients(values: list[str]) -> list[str]:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError("Client selection must be a list of client IDs.")
    if values == ["all"]:
        return list(CLIENTS)
    if values == ["none"]:
        return []
    unknown = [value for value in values if value not in CLIENTS]
    if unknown:
        raise ValueError("Unknown client selection: " + ", ".join(unknown) + ". Run lbt-mcp clients.")
    return list(dict.fromkeys(values))


def ask_clients(default: list[str]) -> list[str]:
    print("Client presets (comma-separated numbers or IDs; 0 = runtime only, all = every preset):")
    choices = list(CLIENTS)
    for index, client in enumerate(choices, 1):
        mode = "automatic or export" if client == "codex" else "export / import guide"
        print(f"  {index}. {CLIENTS[client]['label']} [{client}] - {mode}")
    answer = input(f"Clients [{', '.join(default) or 'none'}]: ").strip()
    if not answer:
        return default
    values = []
    for token in answer.split(","):
        token = token.strip()
        if token == "0":
            token = "none"
        elif token.isdecimal():
            index = int(token)
            if not 1 <= index <= len(choices):
                raise ValueError("Client number is outside the displayed list.")
            token = choices[index - 1]
        values.append(token)
    return normalize_clients(values)


def preset_updates(clients: list[str], server: dict, skill_source: Path,
                   output: Path | None, replace: bool, reserved: set[Path]):
    """Generate importable fragments; these exports are never managed client files."""
    changes, expected, results, rendered = {}, {}, [], {}
    guide = [f"# lbt-mcp {__version__} client presets", "",
             "Merge only the lbt-mcp entry into the selected client's configuration.",
             "Do not replace an entire existing configuration with a fragment.",
             "Generated files do not mean the client has connected or loaded Skills.",
             "Use the paths only on the machine where this MCP runtime is installed.", ""]

    def add_export(path: Path, content: str):
        if path in reserved or path in changes:
            raise ValueError(f"Preset output overlaps another installation file: {path}")
        existing, data = file_bytes(path), content.encode("utf-8")
        if path.is_symlink():
            raise ValueError(f"Refusing to export through a symlink: {path}")
        if existing is not None and existing != data and not replace:
            raise FileExistsError(f"Preset export differs: {path}. Choose another --output-dir or use --replace for a backup.")
        if existing != data:
            changes[path], expected[path] = data, existing

    for client in clients:
        info = CLIENTS[client]
        content = render_client(client, server, skill_source)
        rendered[client] = content
        entry = {"client": client, **info,
                 "status": "guide" if info["format"] == "text" else "generated"}
        if output:
            suffix = "md" if info["format"] == "text" else info["format"]
            path = output / f"lbt-mcp-{client}.{suffix}"
            add_export(path, content)
            entry["path"] = str(path)
        results.append(entry)
        guide.extend([f"## {info['label']} ({client})", "", info["instructions"], "",
                      f"Reference: {info['docs']}", ""])
    if output and clients:
        if any(client != "devin-cloud" for client in clients):
            guide.extend(["## Bundled Skill", "", str(skill_source), "",
                          "Copy the complete ladybug-tools-mcp-use folder, including its references,",
                          "to the selected client's documented Skills directory or use its import UI.",
                          "An MCP resource is separate from client-side Skill discovery.", ""])
        add_export(output / "lbt-mcp-README.md", "\n".join(guide))
    return changes, expected, results, rendered


def grasshopper_directory() -> Path:
    if sys.platform != "win32":
        raise RuntimeError("Flowerpot's verified first release supports Windows with Rhino 8.")
    import winreg

    locations = [Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Rhino 8"]
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\McNeel\Rhinoceros\8.0\Install") as key:
                locations.insert(0, Path(winreg.QueryValueEx(key, "InstallPath")[0]))
        except (OSError, TypeError, ValueError):
            pass
    if not any((location / "System" / "Rhino.exe").is_file() for location in locations):
        raise RuntimeError("Rhino 8 was not found. Select its Grasshopper UserObjects directory with --grasshopper-dir if it is installed elsewhere.")
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
        manifest = validate_grasshopper_manifest(source)
        if manifest.get("version") != __version__:
            raise ValueError("Grasshopper assets do not match this release.")
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
    if previous and not args.yes:
        if not sys.stdin.isatty():
            raise ValueError("Interactive install requires a terminal. Use --yes with explicit options for automation.")
        action = input("Existing installation: [I]nstall/update, [U]ninstall, or [Q]uit [I]: ").strip().lower()
        if action in {"u", "uninstall"}:
            return uninstall(args)
        if action in {"q", "quit"}:
            return {"status": "cancelled"}
        if action not in {"", "i", "install", "update"}:
            raise ValueError("Choose install, uninstall, or quit.")
    requested = getattr(args, "client", None)
    clients = normalize_clients(requested if requested is not None else previous.get("client_presets", ["codex"]))
    output = absolute(args.output_dir) if getattr(args, "output_dir", None) else None
    uv = uv_command()
    tools_dir = absolute(args.tool_dir or previous.get("tool_dir") or Path.home() / ".ladybug-tools-mcp" / "tools")
    gardens = absolute(args.garden_dir or previous.get("gardens_root") or Path.home() / "Gardens")
    codex = absolute(args.codex_config or (previous.get("codex") or {}).get("path") or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml")
    skills = absolute(args.skills_dir or previous.get("skills_dir") or Path.home() / ".agents/skills")
    gh_enabled = args.grasshopper if args.grasshopper is not None else bool(previous.get("grasshopper_dir"))
    if not args.yes:
        if not sys.stdin.isatty():
            raise ValueError("Interactive install requires a terminal. Use --yes with explicit options for automation.")
        print(f"Ladybug Tools MCP {__version__}")
        tools_dir = ask_path("Runtime directory", tools_dir)
        gardens = ask_path("Garden directory", gardens)
        clients = ask_clients(clients)
        if "codex" in clients:
            args.generate_config = not ask_yes("Configure Codex and install local Skills?", not args.generate_config)
        if clients and output is None:
            answer = input("Save preset files to a directory (blank = print only): ").strip()
            output = absolute(answer) if answer else None
        gh_enabled = ask_yes("Install Flowerpot integration (Grasshopper / Rhino 8 on Windows)?", gh_enabled)
    configure_codex = "codex" in clients and not args.generate_config
    if configure_codex and previous.get("codex") and previous["codex"]["path"] != str(codex):
        raise ValueError("Uninstall before changing the managed Codex configuration path.")
    if not configure_codex and previous.get("assets") and previous.get("skills_dir") != str(skills):
        raise ValueError("Keep the installed Skills directory when only generating configuration.")
    gh = None
    if gh_enabled:
        if sys.platform != "win32":
            raise RuntimeError("Flowerpot's verified first release supports Windows with Rhino 8.")
        try:
            gh = absolute(args.grasshopper_dir or previous.get("grasshopper_dir") or grasshopper_directory())
        except RuntimeError as error:
            if args.yes:
                raise
            print(error)
            answer = input("Grasshopper UserObjects/Flowerpot directory (blank = skip Flowerpot): ").strip()
            gh = absolute(answer) if answer else None
        else:
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
    if output and (output.is_relative_to(tools_dir) or output.is_relative_to(cache_dir)):
        raise ValueError("Preset exports must be outside the runtime directory and uv cache.")
    if not args.yes:
        print(f"Runtime: {python}\nGardens: {gardens}")
        print(f"Codex: {codex if configure_codex else 'not modified'}")
        print(f"Preset output: {output or 'terminal'}")
    server = configuration(python, gardens, state)
    config_bytes, config_record, config_before = (None, None, None)
    if configure_codex:
        config_bytes, config_record, config_before = codex_update(codex, server, previous, args.replace)
    import ladybug_tools_mcp
    resources = Path(ladybug_tools_mcp.__file__).resolve().parent / "resources"
    changes, assets, kept, expected = asset_updates(resources, skills if configure_codex else None, gh, previous, args.replace)
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
    skill_source = Path(details["resources"]) / "skills"
    export_changes, export_expected, presets, rendered = preset_updates(
        clients, server, skill_source, output, args.replace,
        {state, codex, *changes, *(Path(asset["path"]) for asset in assets)},
    )
    changes.update(export_changes)
    expected.update(export_expected)
    for entry in presets:
        if entry["client"] == "codex" and configure_codex:
            entry["status"] = "configured"
    gardens.mkdir(parents=True, exist_ok=True)
    record = {
        **previous,
        "schema_version": 1, "version": __version__, "wheel_sha256": wheel_hash, "tool_dir": str(tools_dir),
        "python": str(python), "package_root": details["package_root"],
        "gardens_root": str(gardens), "skills_dir": str(skills),
        "grasshopper_dir": str(gh) if gh else None,
        "codex": config_record if config_record else previous.get("codex"), "assets": assets,
        "client_presets": clients,
    }
    changes[state] = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    expected[state] = state_before
    backups = commit_files(changes, expected)
    for entry in presets:
        if not output and entry["status"] != "configured":
            print(f"\n# {entry['label']} - {entry['status']}\n{entry['instructions']}\n")
            print(rendered[entry["client"]])
    return {"version": __version__, "python": str(python), "gardens_root": str(gardens),
            "state": str(state), "codex_configured": configure_codex, "client_presets": presets,
            "bundled_skills": str(skill_source),
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
    if not args.yes:
        print(f"Runtime: {tools_dir}\nManaged Codex config: {(record.get('codex') or {}).get('path') or 'none'}")
        print(f"Flowerpot: {record.get('grasshopper_dir') or 'none'}\nGardens retained: {record['gardens_root']}")
        print("Only unchanged managed integrations will be removed; modified files will remain.")
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
    commands.add_parser("clients", help="List available client presets without installing or changing settings.")
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
            command.add_argument("--client", action="append", choices=[*CLIENTS, "all", "none"],
                                 help="Select a client preset; repeat for multiple clients. New installs default to codex.")
            command.add_argument("--output-dir", type=Path, help="Save selected presets and import instructions here; otherwise print them.")
            command.add_argument("--generate-config", action="store_true", help="Prepare runtime and generate selected presets without changing client settings or local Skills.")
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
        if args.command == "clients":
            result = [{"client": client, **info, "automatic_configuration": client == "codex"}
                      for client, info in CLIENTS.items()]
        elif args.command == "install":
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
