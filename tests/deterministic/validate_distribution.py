"""Exercise an actual wheel, persistent installer, and stdio MCP without an LLM.

Run with the wheel installed in a separate bootstrap environment:
    python validate_distribution.py --wheel dist/<wheel> --root <new-test-directory>
Use --keep to leave the isolated installation for native client/GH acceptance.
"""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import urlopen
from zipfile import ZipFile


def invoke(args, *options, success=True):
    command = [sys.executable, "-I", "-m", "ladybug_tools_mcp_cli", *options,
               "--state", str(args.root / "installation.json"), "--yes"]
    completed = subprocess.run(command, cwd=args.root, text=True, encoding="utf-8",
                               errors="replace", capture_output=True)
    with (args.root / "installer.log").open("a", encoding="utf-8") as stream:
        stream.write(completed.stdout + completed.stderr + "\n")
    assert (completed.returncode == 0) == success, completed.stdout + completed.stderr
    return completed.stdout


def file_snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def make_broken_wheel(source, destination):
    """Make a same-version wheel missing one required runtime resource."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as archive, ZipFile(destination, "w") as broken:
        missing = "resources/skills/ladybug-tools-mcp-use/SKILL.md"
        removed = False
        for entry in archive.infolist():
            if entry.filename.endswith(missing):
                removed = True
                continue
            broken.writestr(entry, archive.read(entry.filename))
    assert removed, "The fixture wheel must contain the bundled Skill."
    return destination


def interactive_generate_config_check(args):
    """Exercise the terminal branch with isolated state and mocked answers."""
    import ladybug_tools_mcp_cli as installer

    state = args.root / "interactive-installation.json"
    runtime = args.root / "interactive runtime"
    gardens = args.root / "Interactive Gardens"
    config = args.root / "interactive" / "config.toml"
    skills = args.root / "interactive" / "skills"
    options = SimpleNamespace(
        state=state,
        tool_dir=runtime,
        garden_dir=gardens,
        codex_config=config,
        skills_dir=skills,
        grasshopper=False,
        grasshopper_dir=None,
        generate_config=False,
        replace=False,
        wheel=args.wheel,
        yes=False,
    )
    answers = iter([str(runtime), str(gardens), "n", ""])
    with patch.object(sys.stdin, "isatty", return_value=True), patch(
        "builtins.input", side_effect=lambda _: next(answers)
    ):
        result = installer.install(options)
    assert result["codex_configured"] is False
    assert state.is_file() and not config.exists() and not skills.exists()
    assert gardens.is_dir()
    installer.uninstall(SimpleNamespace(state=state, yes=True))
    assert not state.exists() and not installer.tool_python(runtime).exists()
    assert gardens.is_dir(), "Uninstall must retain the Garden root."


async def protocol_check(args, record):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    environment = {**os.environ, "LADYBUG_TOOLS_GARDENS_ROOT": record["gardens_root"],
        "LADYBUG_TOOLS_MCP_INSTALLATION": str(args.root / "installation.json")}
    transport = StdioTransport(record["python"], ["-I", "-m", "ladybug_tools_mcp.server"],
        cwd=str(args.root), env=environment,
        keep_alive=False, log_file=args.root / "server.log")
    garden = str(args.root / "Gardens" / "Protocol Garden")
    async with Client(transport, timeout=180, init_timeout=120) as client:
        tools = {tool.name for tool in await client.list_tools()}
        assert {"search", "get_schema", "execute"} <= tools, tools
        resources = await client.list_resources()
        assert any("skill" in str(resource.uri) for resource in resources), resources
        skill_uri = next(resource.uri for resource in resources if "skill" in str(resource.uri))
        skill_contents = await client.read_resource(skill_uri)
        assert any("ladybug-tools-mcp-use" in getattr(block, "text", "") for block in skill_contents)
        weather = await client.read_resource("weather://catalog")
        catalog = json.loads(weather[0].text)
        epw_uri = max((uri for station in catalog["stations"] for uri in station["files"] if uri.endswith(".epw")), key=len)
        epw = await client.read_resource(epw_uri)
        assert epw[0].text.startswith("LOCATION,") and len(epw[0].text.splitlines()) > 8760
        discovery = await client.call_tool("search", {"query": "GD_create HB_create_model HB_create_room HB_validate_model GD_web_view_start_mode"})
        (args.root / "discovery.json").write_text(json.dumps(discovery.data, indent=2, default=str), encoding="utf-8")
        code = f'''
created = await call_tool("GD_create", {{"name": "Distribution acceptance", "root_dir": {garden!r}}})
root = created["garden_root"]
viewer = await call_tool("GD_web_view_start_mode", {{"garden_root": root, "name": "Distribution acceptance"}})
model = await call_tool("HB_create_model", {{"garden_root": root, "identifier": "package_model", "set_base": True}})
room = await call_tool("HB_create_room", {{"garden_root": root, "identifier": "PackageRoom", "x_dim": 6, "y_dim": 5, "height": 3}})
validation = await call_tool("HB_validate_model", {{"garden_root": root}})
base = await call_tool("GD_get_base_honeybee_model", {{"garden_root": root}})
version = await call_tool("GD_create_version", {{"garden_root": root, "subject": "distribution acceptance", "summary": {{"source": "deterministic validator"}}, "source": "test"}})
status = await call_tool("GD_get_version_status", {{"garden_root": root}})
versions = await call_tool("GD_list_versions", {{"garden_root": root, "limit": 5}})
return {{"garden": created, "viewer": viewer, "model": model, "room": room, "validation": validation, "base": base, "version": version, "status": status, "versions": versions}}
'''
        result = await client.call_tool("execute", {"code": code})
        (args.root / "protocol.json").write_text(json.dumps(result.data, indent=2, default=str), encoding="utf-8")
        data = result.data or {}
        if "result" in data:
            data = data["result"]
        try:
            assert not result.is_error, result
            assert data["validation"].get("valid", data["validation"].get("is_valid")), data["validation"]
            assert data["version"].get("version_id"), data["version"]
            assert data["status"]["summary_view"]["has_versions"]
            assert not data["status"]["summary_view"]["is_dirty"]
            assert len(data["versions"]["versions"]) == 1, data["versions"]
            url = data["viewer"]["viewer"]["url"]
            assert url.startswith(("http://127.0.0.1:", "http://localhost:")), url
            with urlopen(url, timeout=20) as response:
                html = response.read().decode("utf-8")
                assert response.status == 200 and "vtk" in html.lower()
            with urlopen(url + "api/state", timeout=20) as response:
                state = json.load(response)
                (args.root / "preview-state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
                assert "package_model" in json.dumps(state), state
            models = list(Path(garden).glob("models/**/*.hbjson"))
            assert len(models) == 1, models
            model = json.loads(models[0].read_text(encoding="utf-8"))
            assert model["identifier"] == "package_model"
            assert len(model["rooms"]) == 1 and model["rooms"][0]["identifier"] == "PackageRoom"
            assert len(model["rooms"][0]["faces"]) == 6
            from honeybee.model import Model
            readback = Model.from_dict(model)
            assert abs(readback.floor_area - 30) < 1e-6 and abs(readback.volume - 90) < 1e-6
        finally:
            await client.call_tool("execute", {"code": f'return await call_tool("GD_web_view_stop_mode", {{"garden_root": {garden!r}}})'})
    return garden


async def gitless_garden_check(args, record):
    """Garden creation remains available when Git is absent from PATH."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    garden = args.root / "Gardens" / "Gitless Garden"
    environment = {
        **os.environ,
        "PATH": str(args.root / "empty PATH"),
        "LADYBUG_TOOLS_GARDENS_ROOT": record["gardens_root"],
        "LADYBUG_TOOLS_MCP_INSTALLATION": str(args.root / "installation.json"),
    }
    transport = StdioTransport(record["python"], ["-I", "-m", "ladybug_tools_mcp.server"],
        cwd=str(args.root), env=environment, keep_alive=False,
        log_file=args.root / "gitless-server.log")
    async with Client(transport, timeout=180, init_timeout=120) as client:
        result = await client.call_tool("execute", {"code": f'return await call_tool("GD_create", {{"name": "Gitless Garden", "root_dir": {str(garden)!r}}})'})
        assert not result.is_error, result
        data = result.data or {}
        if "result" in data:
            data = data["result"]
        summary = data.get("summary_view", {})
        assert summary["version_control"]["git_available"] is False, summary
        assert not (garden / ".git").exists()
    return garden


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    args.wheel = args.wheel.resolve()
    args.root = args.root.resolve()
    args.root.mkdir(parents=True, exist_ok=False)
    with ZipFile(args.wheel) as archive:
        names = archive.namelist()
        assert "ladybug_tools_mcp/tool_namespaces.py" not in names
        assert any(name.endswith("skills/ladybug-tools-mcp-use/SKILL.md") for name in names)
        assert len([name for name in names if name.endswith(".ghuser")]) == 6
        assert any(name.endswith(".epw") for name in names)
        manifest = json.loads(archive.read("ladybug_tools_mcp/resources/grasshopper/manifest.json"))
        for entry in manifest["components"]:
            assert hashlib.sha256(archive.read("ladybug_tools_mcp/resources/grasshopper/" + entry["file"])).hexdigest() == entry["sha256"]

    config = args.root / "codex" / "config.toml"
    skills = args.root / "skills"
    config.parent.mkdir()
    original = '# retain this comment\nmodel_reasoning_effort = "low"\n[mcp_servers.example]\ncommand = "example"\n'
    config.write_text(original, encoding="utf-8")
    options = ("install", "--wheel", str(args.wheel), "--tool-dir", str(args.root / "runtime tools"),
               "--garden-dir", str(args.root / "Gardens"), "--codex-config", str(config),
               "--skills-dir", str(skills), "--no-grasshopper")
    invoke(args, *options, "--generate-config")
    assert config.read_text(encoding="utf-8") == original and not skills.exists()
    invoke(args, *options)
    configured = config.read_bytes()
    assert b"# retain this comment" in configured
    settings = tomllib.loads(configured.decode("utf-8"))
    assert settings["mcp_servers"]["example"]["command"] == "example"
    assert settings["mcp_servers"]["ladybug-tools-mcp"]["args"] == ["-I", "-m", "ladybug_tools_mcp.server"]
    assert settings["mcp_servers"]["ladybug-tools-mcp"]["required"] is True
    skill = skills / "ladybug-tools-mcp-use" / "SKILL.md"
    assert skill.is_file()
    invoke(args, *options)
    assert config.read_bytes() == configured
    record = json.loads((args.root / "installation.json").read_text(encoding="utf-8"))
    assert "runtime tools" in record["python"]
    assert (Path(record["package_root"]) / "flowerpot" / "runtime.py").is_file()
    interactive_generate_config_check(args)
    garden = asyncio.run(protocol_check(args, record))
    gitless_garden = asyncio.run(gitless_garden_check(args, record))
    worker = subprocess.run([record["python"], "-I", "-m", "flowerpot.worker_cli", "garden_list"],
        input=json.dumps({"root_folder": record["gardens_root"]}), capture_output=True, text=True, check=True)
    assert worker.stdout.isascii(), "Keep the IronPython worker wire format ASCII JSON."
    assert garden in json.loads(worker.stdout)["garden_roots"]
    assert gitless_garden.exists()

    # This is a same-version rerun, not a cross-version upgrade. It must keep
    # the verified runtime, client settings, and Garden authoring truth.
    state_before_rerun = (args.root / "installation.json").read_bytes()
    garden_before_rerun = file_snapshot(Path(garden))
    invoke(args, *options)
    assert config.read_bytes() == configured
    assert (args.root / "installation.json").read_bytes() == state_before_rerun
    assert file_snapshot(Path(garden)) == garden_before_rerun

    # A broken same-version wheel exercises runtime failure recovery without
    # pretending to be a real release-to-release upgrade.
    broken = make_broken_wheel(args.wheel, args.root / "broken-wheel" / args.wheel.name)
    config_before_failure = config.read_bytes()
    state_before_failure = (args.root / "installation.json").read_bytes()
    garden_before_failure = file_snapshot(Path(garden))
    invoke(args, *options, "--wheel", str(broken), success=False)
    assert config.read_bytes() == config_before_failure
    assert (args.root / "installation.json").read_bytes() == state_before_failure
    assert file_snapshot(Path(garden)) == garden_before_failure
    invoke(args, *options)
    assert config.read_bytes() == config_before_failure
    assert file_snapshot(Path(garden)) == garden_before_failure
    if args.keep:
        print(json.dumps({"status": "passed; installation retained", "root": str(args.root), "garden": garden}))
        return

    # A user-edited server is protected, then explicitly backed up on replacement.
    import tomlkit
    document = tomlkit.parse(config.read_text(encoding="utf-8"))
    document["mcp_servers"]["ladybug-tools-mcp"]["startup_timeout_sec"] = 75
    config.write_text(tomlkit.dumps(document), encoding="utf-8")
    user_config = config.read_bytes()
    invoke(args, *options, success=False)
    assert config.read_bytes() == user_config
    invoke(args, *options, "--replace")
    assert any(path.read_bytes() == user_config for path in config.parent.glob("config.toml.ladybug-backup-*"))
    user_skill = skill.read_bytes() + b"\nUser customization.\n"
    skill.write_bytes(user_skill)
    invoke(args, *options, success=False)
    assert skill.read_bytes() == user_skill
    before = {str(path): path.read_bytes() for path in Path(garden).rglob("*") if path.is_file()}
    invoke(args, "uninstall")
    assert skill.read_bytes() == user_skill
    assert tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]["ladybug-tools-mcp"]["startup_timeout_sec"] == 75
    assert not Path(record["python"]).exists()
    assert not (args.root / "installation.json").exists()
    assert all(Path(path).read_bytes() == data for path, data in before.items())
    print(json.dumps({"status": "passed", "root": str(args.root), "checks": ["wheel", "generate-config", "interactive-options", "install", "same-version-rerun", "runtime-failure-recovery", "stdio", "Garden", "Git-version", "Gitless-Garden", "model", "localhost", "conflicts", "uninstall"], "upgrade": "cross-version upgrade not exercised; same-version reruns only"}))


if __name__ == "__main__":
    main()
