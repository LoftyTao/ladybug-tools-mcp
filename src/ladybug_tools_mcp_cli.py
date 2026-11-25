"""Local MCP server, runtime manager, pack manager, diagnostics, and Flowerpot CLI."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from flowerpot.installation import installation_path, read_installation
from ladybug_tools_mcp import __version__
from ladybug_tools_mcp.runtime_home import (
    RUNTIME_CONFIG_KEYS,
    atomic_write_json,
    default_runtime_config,
    home_installation_path,
    install_pack,
    list_packs,
    read_runtime_config,
    remove_pack,
    resolve_home_dir,
    resolved_runtime_config,
    run_doctor,
    sync_sdk_configs,
    user_installation_path,
    write_installation_records,
    write_runtime_config,
)

PACKAGE = "lbt-mcp"


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


def file_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ladybug-tools-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


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
            name in names
            or filename in files
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


def grasshopper_directory() -> Path:
    if sys.platform != "win32":
        raise RuntimeError("Flowerpot's verified first release supports Windows with Rhino 8.")
    default_rhino = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Rhino 8" / "System" / "Rhino.exe"
    if not default_rhino.is_file():
        import winreg

        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\McNeel\Rhinoceros\8.0\Install") as key:
                    if (Path(winreg.QueryValueEx(key, "InstallPath")[0]) / "System" / "Rhino.exe").is_file():
                        break
            except (OSError, TypeError, ValueError):
                pass
        else:
            raise RuntimeError(
                "Rhino 8 was not found. Select its Grasshopper UserObjects directory with --grasshopper-dir if it is installed elsewhere."
            )
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is unavailable; cannot locate Grasshopper UserObjects.")
    return absolute(Path(appdata) / "Grasshopper/UserObjects/Flowerpot")


def _owned_grasshopper_paths(record: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    gh_root_raw = record.get("grasshopper_dir")
    for item in record.get("assets", []):
        if item.get("kind") != "grasshopper":
            continue
        if not isinstance(gh_root_raw, str) or not gh_root_raw:
            raise ValueError("Installation record missing grasshopper_dir for Flowerpot asset.")
        root = absolute(gh_root_raw)
        path = absolute(item["path"])
        path.relative_to(root)
        if path == root:
            raise ValueError("An installation asset must be a file, not its root directory.")
        result[str(path)] = item
    return result


def _commit_files(changes: dict[Path, bytes | None], before: dict[Path, bytes | None]) -> list[str]:
    """Back up existing files and roll back partial writes on a local failure."""
    for path in changes:
        if path.is_symlink() or file_bytes(path) != before[path]:
            raise RuntimeError(f"File changed during operation or is a symlink; retry: {path}")
    backups: list[str] = []
    written: list[Path] = []
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        for path, content in changes.items():
            if path.is_symlink():
                raise ValueError(f"Refusing to replace a symlink: {path}")
            if file_bytes(path) != before[path]:
                raise RuntimeError(f"File changed during operation; retry: {path}")
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


def _install_grasshopper_assets(gh_dir: Path, previous: dict, *, replace: bool) -> dict:
    import ladybug_tools_mcp

    resources = Path(ladybug_tools_mcp.__file__).resolve().parent / "resources"
    source = resources / "grasshopper"
    if not source.is_dir():
        source = Path(__file__).resolve().parent / "grasshopper_components" / "user_objects"
    manifest = validate_grasshopper_manifest(source)
    if manifest.get("version") != __version__:
        raise ValueError("Grasshopper assets do not match this release.")

    old = _owned_grasshopper_paths(previous)
    changes: dict[Path, bytes | None] = {}
    expected: dict[Path, bytes | None] = {}
    assets: list[dict] = []
    kept: list[str] = []

    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        dest = gh_dir / item.relative_to(source)
        data = item.read_bytes()
        existing = file_bytes(dest)
        known = old.get(str(dest), {}).get("sha256")
        if existing is not None and existing != data and digest(existing) != known and not replace:
            raise FileExistsError(
                f"Modified or unmanaged asset: {dest}. Use --replace to keep a backup and replace it."
            )
        if existing != data:
            changes[dest] = data
            expected[dest] = existing
        assets.append({"path": str(dest), "kind": "grasshopper", "sha256": digest(data)})

    wanted = {entry["path"] for entry in assets}
    for name, item in old.items():
        if name in wanted:
            continue
        path = Path(name)
        content = file_bytes(path)
        if content is not None:
            if digest(content) == item["sha256"]:
                changes[path] = None
                expected[path] = content
            else:
                kept.append(name)

    backups = _commit_files(changes, expected) if changes else []
    return {
        "grasshopper_dir": str(gh_dir),
        "assets": assets,
        "backups": backups,
        "preserved_files": kept,
    }


def _resolve_state_path(state_arg: str | Path | None, home_arg: str | Path | None) -> Path:
    if state_arg is not None:
        return absolute(state_arg)
    if home_arg is not None:
        home_rec = home_installation_path(home_arg)
        if home_rec.is_file():
            return home_rec
    return Path(installation_path())


def _cmd_serve(args) -> int:
    state_arg = getattr(args, "state", None)
    home_arg = getattr(args, "home", None)
    resolved_state = _resolve_state_path(state_arg, home_arg)
    settings: dict = {}
    if resolved_state.is_file():
        settings = read_installation(str(resolved_state))
        os.environ.setdefault("LADYBUG_TOOLS_MCP_INSTALLATION", str(resolved_state))
    else:
        settings = read_installation()
    if settings:
        if settings.get("gardens_root"):
            os.environ.setdefault("LADYBUG_TOOLS_GARDENS_ROOT", settings["gardens_root"])
        if settings.get("home"):
            os.environ.setdefault("LADYBUG_TOOLS_MCP_HOME", settings["home"])
    elif home_arg is not None:
        os.environ.setdefault("LADYBUG_TOOLS_MCP_HOME", str(resolve_home_dir(home_arg)))

    from ladybug_tools_mcp.server import mcp

    mcp.run(show_banner=False)
    return 0


def _cmd_status(args) -> dict:
    resolved_state = _resolve_state_path(args.state, args.home)
    home_dir = resolve_home_dir(args.home, state_path=resolved_state if resolved_state.is_file() else None)
    record = read_installation(str(resolved_state)) if resolved_state.is_file() else {}
    if not record and home_installation_path(home_dir).is_file():
        record = read_installation(str(home_installation_path(home_dir)))
    if not record and args.home is None and args.state is None and user_installation_path().is_file():
        candidate = read_installation(str(user_installation_path()))
        if not candidate.get("home") or Path(candidate["home"]).expanduser().resolve() == home_dir:
            record = candidate
    if not record:
        return {
            "status": "not_installed",
            "version": __version__,
            "home": str(home_dir),
            "state": str(resolved_state),
            "packs": list_packs(home_dir),
        }
    return {
        "home": str(home_dir),
        **record,
        "status": "installed",
        "state": str(resolved_state),
        "packs": list_packs(home_dir),
    }


def _cmd_runtime_list(args) -> dict:
    home_dir = resolve_home_dir(args.home)
    return {
        "home": str(home_dir),
        "raw": read_runtime_config(home_dir),
        "resolved": resolved_runtime_config(home_dir),
    }


def _cmd_runtime_sync(args) -> dict:
    home_dir = resolve_home_dir(args.home)
    sync_res = sync_sdk_configs(
        home_dir,
        site_packages=args.site_packages,
        gardens_root=args.gardens,
    )

    gh_assets_info = None
    gh_dir_resolved = None
    if args.grasshopper_dir is not None:
        gh_dir_resolved = absolute(args.grasshopper_dir)
        prior_rec = (
            read_installation(str(home_installation_path(home_dir)))
            if home_installation_path(home_dir).is_file()
            else {}
        )
        gh_assets_info = _install_grasshopper_assets(gh_dir_resolved, prior_rec, replace=True)

    inst_info = None
    has_existing_inst = home_installation_path(home_dir).is_file()
    if args.gardens is not None or has_existing_inst or args.version or args.launcher or gh_dir_resolved:
        existing = read_installation(str(home_installation_path(home_dir))) if has_existing_inst else {}
        gardens = args.gardens or existing.get("gardens_root") or (Path.home() / "Gardens")
        inst_info = write_installation_records(
            home_dir,
            gardens_root=gardens,
            site_packages=args.site_packages,
            launcher=args.launcher,
            version=args.version,
            grasshopper_dir=gh_dir_resolved,
            assets=gh_assets_info["assets"] if gh_assets_info else None,
            state_path=args.state,
        )

    return {
        "status": "synced",
        **sync_res,
        "grasshopper": gh_assets_info,
        "installation": inst_info,
    }


def _cmd_runtime_set(args) -> dict:
    key = args.key
    if key not in RUNTIME_CONFIG_KEYS:
        raise ValueError(f"Unknown runtime config key {key!r}. Valid keys: {', '.join(RUNTIME_CONFIG_KEYS)}")
    home_dir = resolve_home_dir(args.home)
    cfg = read_runtime_config(home_dir)
    if key == "standards_extension_folders":
        val_str = args.value.strip()
        if val_str.startswith("["):
            parsed = json.loads(val_str)
            if not isinstance(parsed, list):
                raise ValueError("standards_extension_folders must be a JSON list or comma-separated paths.")
            cfg[key] = [str(item) for item in parsed]
        elif not val_str:
            cfg[key] = []
        else:
            cfg[key] = [part.strip() for part in val_str.split(",") if part.strip()]
    else:
        cfg[key] = args.value
    write_runtime_config(cfg, home_dir)
    sync_res = None if args.no_sync else sync_sdk_configs(home_dir, site_packages=args.site_packages)
    return {
        "status": "updated",
        "home": str(home_dir),
        "key": key,
        "value": cfg[key],
        "sync": sync_res,
    }


def _cmd_runtime_reset(args) -> dict:
    home_dir = resolve_home_dir(args.home)
    defaults = default_runtime_config(home_dir)
    if args.key:
        if args.key not in RUNTIME_CONFIG_KEYS:
            raise ValueError(f"Unknown runtime config key {args.key!r}.")
        cfg = read_runtime_config(home_dir)
        cfg[args.key] = defaults[args.key]
    else:
        cfg = defaults
    write_runtime_config(cfg, home_dir)
    sync_res = sync_sdk_configs(home_dir, site_packages=args.site_packages)
    return {
        "status": "reset",
        "home": str(home_dir),
        "key": args.key or "all",
        "sync": sync_res,
    }


def _cmd_flowerpot_install(args) -> dict:
    if sys.platform != "win32" and args.grasshopper_dir is None:
        raise RuntimeError("Flowerpot's verified first release supports Windows with Rhino 8.")
    state_path = _resolve_state_path(args.state, args.home)
    previous = read_installation(str(state_path)) if state_path.is_file() else {}
    if not previous and user_installation_path().is_file():
        previous = read_installation(str(user_installation_path()))

    gh_dir = absolute(
        args.grasshopper_dir or previous.get("grasshopper_dir") or grasshopper_directory()
    )
    gh_res = _install_grasshopper_assets(gh_dir, previous, replace=args.replace)

    home_dir = resolve_home_dir(args.home, state_path=state_path)
    if previous.get("home") or (home_dir / "config").is_dir():
        gardens = previous.get("gardens_root") or os.environ.get("LADYBUG_TOOLS_GARDENS_ROOT") or (Path.home() / "Gardens")
        write_installation_records(
            home_dir,
            gardens_root=gardens,
            python=previous.get("python"),
            package_root=previous.get("package_root"),
            launcher=previous.get("launcher"),
            version=previous.get("version"),
            distribution_mode=previous.get("distribution_mode") or "offline_bundle",
            grasshopper_dir=gh_dir,
            assets=gh_res["assets"],
            state_path=state_path if args.state else None,
        )
    else:
        import flowerpot

        gardens = Path(previous.get("gardens_root") or os.environ.get("LADYBUG_TOOLS_GARDENS_ROOT") or (Path.home() / "Gardens")).expanduser().resolve()
        gardens.mkdir(parents=True, exist_ok=True)
        record = {
            **previous,
            "schema_version": 1,
            "version": previous.get("version") or __version__,
            "python": previous.get("python") or str(Path(sys.executable).resolve()),
            "package_root": previous.get("package_root") or str(Path(flowerpot.__file__).resolve().parents[1]),
            "gardens_root": str(gardens),
            "grasshopper_dir": str(gh_dir),
            "assets": gh_res["assets"],
        }
        atomic_write_json(state_path, record)

    return {"status": "installed", **gh_res, "state": str(state_path)}


def _cmd_flowerpot_uninstall(args) -> dict:
    state_path = _resolve_state_path(args.state, args.home)
    record = read_installation(str(state_path)) if state_path.is_file() else {}
    if not record:
        return {"status": "not_installed", "state": str(state_path)}

    changes: dict[Path, bytes | None] = {}
    expected: dict[Path, bytes | None] = {}
    kept: list[str] = []
    removed: list[str] = []
    for name, item in _owned_grasshopper_paths(record).items():
        path = Path(name)
        data = file_bytes(path)
        if data is not None:
            if digest(data) == item["sha256"]:
                changes[path] = None
                expected[path] = data
                removed.append(name)
            else:
                kept.append(name)

    backups = _commit_files(changes, expected) if changes else []

    remaining_assets = [item for item in record.get("assets", []) if item.get("kind") != "grasshopper"]
    updated = {**record, "grasshopper_dir": None, "assets": remaining_assets}

    targets = [state_path]
    if updated.get("home"):
        targets.append(home_installation_path(updated["home"]))
    if user_installation_path().is_file():
        targets.append(user_installation_path())
    seen: set[Path] = set()
    for target in targets:
        if target in seen or not target.is_file():
            continue
        seen.add(target)
        atomic_write_json(target, updated)

    return {
        "status": "uninstalled",
        "removed_files": removed,
        "preserved_files": kept,
        "backups": backups,
        "state": str(state_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PACKAGE,
        description="Ladybug Tools MCP server, runtime configuration, pack manager, and Flowerpot tools.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    serve_p = subparsers.add_parser("serve", help="Run the stdio MCP server (default).")
    serve_p.add_argument("--home", type=Path, help="Runtime home directory.")
    serve_p.add_argument("--state", type=Path, help="Installation record path.")

    status_p = subparsers.add_parser("status", help="Show installation and pack status.")
    status_p.add_argument("--home", type=Path, help="Runtime home directory.")
    status_p.add_argument("--state", type=Path, help="Installation record path.")

    doctor_p = subparsers.add_parser("doctor", help="Diagnose runtime health and SDK config sync.")
    doctor_p.add_argument("--home", type=Path, help="Runtime home directory.")
    doctor_p.add_argument("--smoke", action="store_true", help="Run subprocess binary health probes.")
    doctor_p.add_argument("--site-packages", type=Path, help="Override target venv site-packages.")

    rt_p = subparsers.add_parser("runtime", help="Inspect, sync, set, or reset runtime configuration.")
    rt_sub = rt_p.add_subparsers(dest="runtime_command", required=True)

    rt_list = rt_sub.add_parser("list", help="Show raw and resolved runtime.json entries.")
    rt_list.add_argument("--home", type=Path)

    rt_sync = rt_sub.add_parser("sync", help="Sync SDK config.json files and pyvenv.cfg from runtime.json.")
    rt_sync.add_argument("--home", type=Path)
    rt_sync.add_argument("--site-packages", type=Path)
    rt_sync.add_argument("--gardens", type=Path, help="Gardens root directory (must be outside --home).")
    rt_sync.add_argument("--version", help="Release version string to record in installation.json.")
    rt_sync.add_argument("--launcher", type=Path, help="Launcher executable path.")
    rt_sync.add_argument("--grasshopper-dir", type=Path, help="Optional Grasshopper UserObjects/Flowerpot directory.")
    rt_sync.add_argument("--state", type=Path, help="Optional explicit installation record path.")

    rt_set = rt_sub.add_parser("set", help="Set a runtime.json key and sync SDK configs.")
    rt_set.add_argument("key", help="Runtime configuration key.")
    rt_set.add_argument("value", help="Value or path to assign.")
    rt_set.add_argument("--home", type=Path)
    rt_set.add_argument("--site-packages", type=Path)
    rt_set.add_argument("--no-sync", action="store_true", help="Do not sync SDK configs after updating runtime.json.")

    rt_reset = rt_sub.add_parser("reset", help="Reset runtime.json to <home>/runtimes defaults and sync.")
    rt_reset.add_argument("key", nargs="?", help="Optional single key to reset.")
    rt_reset.add_argument("--home", type=Path)
    rt_reset.add_argument("--site-packages", type=Path)

    pack_p = subparsers.add_parser("pack", help="Manage optional .lbtpack offline runtime packs.")
    pack_sub = pack_p.add_subparsers(dest="pack_command", required=True)

    pack_install = pack_sub.add_parser("install", help="Verify and install a .lbtpack archive.")
    pack_install.add_argument("file", type=Path, help="Path to .lbtpack archive.")
    pack_install.add_argument("--home", type=Path)
    pack_install.add_argument("--force", action="store_true", help="Replace existing pack or conflicting files.")
    pack_install.add_argument("--site-packages", type=Path)

    pack_list = pack_sub.add_parser("list", help="List installed packs.")
    pack_list.add_argument("--home", type=Path)

    pack_remove = pack_sub.add_parser("remove", help="Remove an installed pack.")
    pack_remove.add_argument("name", help="Pack name to remove.")
    pack_remove.add_argument("--home", type=Path)
    pack_remove.add_argument("--site-packages", type=Path)

    fp_p = subparsers.add_parser("flowerpot", help="Install or uninstall Grasshopper Flowerpot user objects.")
    fp_sub = fp_p.add_subparsers(dest="flowerpot_command", required=True)

    fp_install = fp_sub.add_parser("install", help="Install Flowerpot .ghuser components.")
    fp_install.add_argument("--grasshopper-dir", type=Path)
    fp_install.add_argument("--replace", action="store_true")
    fp_install.add_argument("--state", type=Path)
    fp_install.add_argument("--home", type=Path)

    fp_uninstall = fp_sub.add_parser("uninstall", help="Uninstall unmodified Flowerpot .ghuser components.")
    fp_uninstall.add_argument("--state", type=Path)
    fp_uninstall.add_argument("--home", type=Path)

    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "serve"):
        return _cmd_serve(args)

    configure_stdio()
    try:
        exit_code = 0
        if args.command == "status":
            result = _cmd_status(args)
        elif args.command == "doctor":
            result = run_doctor(
                home=args.home,
                smoke=args.smoke,
                site_packages=args.site_packages,
            )
            exit_code = 0 if result.get("ok") else 1
        elif args.command == "runtime":
            if args.runtime_command == "list":
                result = _cmd_runtime_list(args)
            elif args.runtime_command == "sync":
                result = _cmd_runtime_sync(args)
            elif args.runtime_command == "set":
                result = _cmd_runtime_set(args)
            else:
                result = _cmd_runtime_reset(args)
        elif args.command == "pack":
            if args.pack_command == "install":
                result = install_pack(
                    args.file,
                    home=args.home,
                    force=args.force,
                    site_packages=args.site_packages,
                )
            elif args.pack_command == "list":
                result = {"home": str(resolve_home_dir(args.home)), "packs": list_packs(args.home)}
            else:
                result = remove_pack(
                    args.name,
                    home=args.home,
                    site_packages=args.site_packages,
                )
        elif args.command == "flowerpot":
            if args.flowerpot_command == "install":
                result = _cmd_flowerpot_install(args)
            else:
                result = _cmd_flowerpot_uninstall(args)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return exit_code
    except (OSError, ValueError, RuntimeError) as error:
        print(f"{PACKAGE}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
