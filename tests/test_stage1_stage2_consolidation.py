"""Stage 1 & Stage 2 consolidation verification and comprehensive integration tests."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import re
import shutil
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode

import web_view
from garden.background import submit_worker_process
from garden.dragonfly_des.runs import _DES_RUNS
from garden.dragonfly_grid.runs import _GRID_RUNS
from garden.fairyfly.availability import fairyfly_tools_enabled
from garden.fairyfly.therm import _THERM_RUNS
from garden.manifest import GardenManifest, utc_now_iso
from garden.radiance.run import _RADIANCE_RUNS
from garden.run_energy.annual import _ENERGY_RUNS
from garden.run_urbanopt import _URBANOPT_RUNS
from garden.run_uwg import _UWG_RUNS
from ladybug_tools_mcp.code_mode import PreviewMontySandboxProvider
from ladybug_tools_mcp.registry import _TOOL_FAMILIES, register_tools
from ladybug_tools_mcp.server import create_mcp

EXPECTED_MODULE_COUNTS: dict[str, int] = {
    "config": 1,
    "garden": 13,
    "flowerpot": 4,
    "honeybee_core": 13,
    "ironbug": 8,
    "dragonfly_core": 11,
    "dragonfly_grid": 3,
    "des": 3,
    "energy": 9,
    "radiance": 12,
    "run_energy": 7,
    "run_urbanopt": 3,
    "run_uwg": 2,
    "libraries": 2,
    "comfort": 3,
    "visualize": 7,
    "web_view": 5,
    "fairyfly": 6,
}


def _parse_tool_result(res: Any) -> dict[str, Any]:
    """Extract a JSON dictionary from a FastMCP CallToolResult."""
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    content = getattr(res, "content", []) or []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
    raise AssertionError(f"Unable to parse FastMCP tool result: {res!r}")


def _extract_text(res: Any) -> str:
    """Extract text payload from a FastMCP CallToolResult."""
    parts: list[str] = []
    data = getattr(res, "data", None)
    if data is not None:
        parts.append(json.dumps(data) if not isinstance(data, str) else data)
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text)
    return "\n".join(parts)


async def _call(client: Client, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool through FastMCP Client and decode its JSON dict."""
    res = await client.call_tool(name, args)
    return _parse_tool_result(res)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_WEATHER_ASSETS = _REPO_ROOT / "resources" / "ladybug" / "tests" / "assets"


def _weather_source_folder(tmp_path: Path) -> str:
    """Copy the repository's Chicago EPW/DDY/STAT assets into a local source folder."""
    folder = tmp_path / "weather_source"
    folder.mkdir(parents=True, exist_ok=True)
    for subdir, suffix in (("epw", ".epw"), ("ddy", ".ddy"), ("stat", ".stat")):
        shutil.copy2(
            _WEATHER_ASSETS / subdir / f"chicago{suffix}",
            folder / f"chicago{suffix}",
        )
    return str(folder)


def _make_raw_mcp() -> FastMCP:
    """Build an unwrapped FastMCP server with strict validation for direct tool calls."""
    mcp = FastMCP(
        "Raw Consolidation Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


@pytest.fixture(scope="module")
def raw_mcp() -> FastMCP:
    """Module-scoped FastMCP server with all consolidated tools registered."""
    return _make_raw_mcp()


def test_server_boot_registry_code_mode_and_stale_python_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify server boot, 18-module registration counts, CodeMode tools, and zero stale Python refs."""
    mcp = create_mcp()
    assert mcp.strict_input_validation is True

    # Verify per-module counts and total internal tool count.
    registered_names: set[str] = set()
    module_counts: dict[str, int] = {}
    for family in _TOOL_FAMILIES:
        if family == "fairyfly" and not fairyfly_tools_enabled():
            continue
        mod_mcp = FastMCP(
            f"mod-{family}",
            on_duplicate="error",
            strict_input_validation=True,
        )
        module = importlib.import_module(f"ladybug_tools_mcp.tools.{family}")
        module.register(mod_mcp)
        tools = asyncio.run(mod_mcp.list_tools())
        module_counts[family] = len(tools)
        assert len(tools) == EXPECTED_MODULE_COUNTS[family], (
            f"Module {family} registered {len(tools)} tools, expected {EXPECTED_MODULE_COUNTS[family]}"
        )
        registered_names.update(tool.name for tool in tools)

    expected_total = 112 if fairyfly_tools_enabled() else 106
    assert sum(module_counts.values()) == expected_total
    assert len(registered_names) == expected_total

    # Verify toggling fairyfly_tools_enabled=False cleanly drops 6 tools -> 106.
    disabled_mcp = FastMCP("disabled-ff", on_duplicate="error", strict_input_validation=True)
    with monkeypatch.context() as mp:
        mp.setattr("ladybug_tools_mcp.registry.fairyfly_tools_enabled", lambda: False)
        register_tools(disabled_mcp)
    disabled_tools = asyncio.run(disabled_mcp.list_tools())
    assert len(disabled_tools) == 106

    # Inspect CodeMode transform settings.
    code_mode_transforms = [tr for tr in mcp.transforms if isinstance(tr, CodeMode)]
    assert len(code_mode_transforms) == 1
    cm = code_mode_transforms[0]
    assert cm.max_tool_calls == 100
    assert isinstance(cm.sandbox_provider, PreviewMontySandboxProvider)

    # Verify CodeMode exposed tools + search, get_schema, tags, list_tools, execute end-to-end.
    cm_garden_root = (tmp_path / "cm_garden").as_posix()

    async def _run_code_mode() -> None:
        async with Client(mcp) as client:
            exposed = await client.list_tools()
            assert {t.name for t in exposed} == {"search", "get_schema", "tags", "list_tools", "execute"}

            search_res = await client.call_tool("search", {"query": "honeybee model"})
            assert "HB_Create_Model" in _extract_text(search_res)

            schema_res = await client.call_tool("get_schema", {"tools": ["GD_Create"]})
            schema_text = _extract_text(schema_res)
            assert "GD_Create" in schema_text
            assert "root_dir" in schema_text

            exec_code = (
                f'created = await call_tool("GD_Create", {{"name": "cm_garden", "root_dir": {cm_garden_root!r}}})\n'
                f'fetched = await call_tool("GD_Get", {{"garden_root": created["garden_root"]}})\n'
                f'return {{"created_root": created["garden_root"], "exists": fetched["exists"]}}'
            )
            exec_res = _parse_tool_result(await client.call_tool("execute", {"code": exec_code}))
            assert exec_res["exists"] is True
            assert Path(str(exec_res["created_root"])).resolve() == Path(cm_garden_root).resolve()

    asyncio.run(_run_code_mode())

    # Scan src/**/*.py for any unregistered MCP tool references.
    src_root = Path(__file__).resolve().parents[1] / "src"
    token_re = re.compile(r"\b(?:GD|HB|DF|EP|RAD|LB|FF|FP|IB)_[A-Z][A-Za-z0-9_]*\b")
    stale_python_hits: list[str] = []
    for py_file in sorted(src_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in token_re.finditer(line):
                tok = match.group(0)
                if tok in registered_names:
                    continue
                # Ironbug C# runtime class names have a single underscore after IB_ (e.g. IB_HVACSystem).
                if tok.startswith("IB_") and "_" not in tok[3:]:
                    continue
                # honeybee_gbas AutoCAD XDATA APPID literal, not an MCP tool name.
                if tok == "HB_BESI":
                    continue
                stale_python_hits.append(f"{py_file.relative_to(src_root)}:{lineno}: {tok}")
    assert stale_python_hits == [], f"Stale tool references in src Python files: {stale_python_hits}"


def test_code_mode_preview_throttling(tmp_path: Path) -> None:
    """Verify CodeMode coalesces multiple Honeybee edits into one Rune present.json flush per Garden."""
    g1_root = (tmp_path / "preview_g1").as_posix()
    g2_root = (tmp_path / "preview_g2").as_posix()
    mcp = create_mcp()

    async def _run() -> None:
        async with Client(mcp) as client:
            await client.call_tool(
                "execute",
                {
                    "code": (
                        f'g = await call_tool("GD_Create", {{"name": "preview_g1", "root_dir": {g1_root!r}}})\n'
                        f'return await call_tool("GD_Web_View_Start_Mode", {{"garden_root": g["garden_root"], "open_window": False}})'
                    )
                },
            )
            try:
                update_calls: list[dict[str, Any]] = []
                orig_update = web_view.update_present

                def counting_update(*args: Any, **kwargs: Any) -> dict[str, Any]:
                    update_calls.append(dict(kwargs))
                    return orig_update(*args, **kwargs)

                with mock.patch.object(web_view, "update_present", side_effect=counting_update):
                    batch_code = (
                        f'gr = {g1_root!r}\n'
                        f'await call_tool("HB_Create_Model", {{"garden_root": gr, "identifier": "prev_hb"}})\n'
                        f'r1 = await call_tool("HB_Create_Objects", {{"garden_root": gr, "object_type": "room", "identifier": "Room_1", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0}})\n'
                        f'await call_tool("HB_Create_Objects", {{"garden_root": gr, "object_type": "room", "identifier": "Room_2", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0, "origin": [4.0, 0.0, 0.0]}})\n'
                        f'await call_tool("HB_Edit_Objects", {{"garden_root": gr, "target": r1["target"], "display_name": "Updated Room 1"}})\n'
                        f'return {{"done": True}}'
                    )
                    res = _parse_tool_result(await client.call_tool("execute", {"code": batch_code}))
                    assert res == {"done": True}

                assert len(update_calls) == 1, f"Expected 1 coalesced update_present call, got {len(update_calls)}"
                session = web_view.read_web_view_session(garden_root=g1_root)
                assert session is not None
                assert len(session["steps"]) == 1
                assert session["steps"][0]["source_tool"] == "HB_Edit_Objects"
                assert session["steps"][0]["viewer_source"]["kind"] == "rune_present"
                present = web_view.read_present(g1_root)
                assert present is not None
                assert present["model_path"] == "models/honeybee/prev_hb.hbjson"
                assert {t["object_identifier"] for t in present["highlight_targets"]} == {"Room_1", "Room_2"}
                assert not (Path(g1_root) / "tmp" / "web_view" / "previews").exists()
            finally:
                await client.call_tool(
                    "execute",
                    {
                        "code": f'return await call_tool("GD_Web_View_Stop_Mode", {{"garden_root": {g1_root!r}}})'
                    },
                )

        # Direct PreviewMontySandboxProvider test across two separate Gardens.
        await _call_raw_create_garden(g2_root, "preview_g2")
        web_view.start_web_view_session(garden_root=g1_root)
        web_view.start_web_view_session(garden_root=g2_root)
        try:
            recorded: list[tuple[str, str]] = []

            def fake_record(*, tool_name: str, arguments: Any, result: Any) -> None:
                recorded.append((tool_name, str(arguments["garden_root"])))

            async def fake_call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                gr = arguments["garden_root"]
                gid = "g1" if gr == g1_root else "g2"
                target = {
                    "target_type": "honeybee_model",
                    "domain": "honeybee",
                    "garden_id": gid,
                    "model_identifier": arguments.get("tag", "m"),
                }
                return {
                    "model_target": target,
                    "persistence_receipt": {"status": "persisted", "model_target": target},
                }

            provider = PreviewMontySandboxProvider()
            snippet = (
                f'await call_tool("HB_Create_Model", {{"garden_root": {g1_root!r}, "tag": "g1_first"}})\n'
                f'await call_tool("HB_Create_Objects", {{"garden_root": {g1_root!r}, "tag": "g1_last"}})\n'
                f'await call_tool("HB_Create_Model", {{"garden_root": {g2_root!r}, "tag": "g2_first"}})\n'
                f'await call_tool("HB_Edit_Objects", {{"garden_root": {g2_root!r}, "tag": "g2_last"}})\n'
                f'return {{"ok": True}}'
            )
            with mock.patch.object(web_view, "maybe_record_code_mode_preview", side_effect=fake_record):
                out = await provider.run(snippet, external_functions={"call_tool": fake_call_tool})
                assert out == {"ok": True}
            assert len(recorded) == 2
            assert recorded == [("HB_Create_Objects", g1_root), ("HB_Edit_Objects", g2_root)]
        finally:
            web_view.stop_web_view_session(garden_root=g1_root)
            web_view.stop_web_view_session(garden_root=g2_root)

    asyncio.run(_run())


async def _call_raw_create_garden(root_dir: str, name: str) -> dict[str, Any]:
    from garden.store import create_garden

    return create_garden(name=name, root_dir=root_dir)


def test_garden_base_models_versions_artifacts_and_libraries(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    """Exercise GD_Create, GD_Get, GD_Manage_Base_Model, GD_Manage_Versions, GD_List_Artifacts, GD_Properties_Library, LB_Search_Standards_Library."""
    g_root = (tmp_path / "gd_garden").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"name": "gd_garden", "root_dir": g_root})
            gr = created["garden_root"]
            got = await _call(client, "GD_Get", {"garden_root": gr})
            assert got["exists"] is True

            # Create models in honeybee, dragonfly, and fairyfly (if enabled).
            hb_a = await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "hb_a", "set_base": True})
            hb_b = await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "hb_b", "set_base": False})
            df_a = await _call(client, "DF_Model", {"garden_root": gr, "identifier": "df_a", "set_base": True})
            ff_enabled = fairyfly_tools_enabled()
            ff_a = (
                await _call(client, "FF_Create_Model", {"garden_root": gr, "identifier": "ff_a", "set_base": True})
                if ff_enabled
                else None
            )

            # GD_Manage_Base_Model: get (all), set, save across domains.
            all_bases = await _call(client, "GD_Manage_Base_Model", {"garden_root": gr, "action": "get"})
            assert all_bases["base_models"]["honeybee"]["model_identifier"] == "hb_a"
            assert all_bases["base_models"]["dragonfly"]["model_identifier"] == "df_a"
            if ff_enabled:
                assert all_bases["base_models"]["fairyfly"]["model_identifier"] == "ff_a"

            await _call(
                client,
                "GD_Manage_Base_Model",
                {"garden_root": gr, "action": "set", "domain": "honeybee", "model_target": hb_b["target"]},
            )
            hb_slot = await _call(
                client,
                "GD_Manage_Base_Model",
                {"garden_root": gr, "action": "get", "domain": "honeybee"},
            )
            assert hb_slot["target"]["model_identifier"] == "hb_b"
            await _call(
                client,
                "GD_Manage_Base_Model",
                {"garden_root": gr, "action": "set", "domain": "honeybee", "model_target": hb_a["target"]},
            )

            for dom in ("honeybee", "dragonfly", *(("fairyfly",) if ff_enabled else ())):
                saved = await _call(
                    client,
                    "GD_Manage_Base_Model",
                    {"garden_root": gr, "action": "save", "domain": dom, "message": f"save {dom}", "force": True},
                )
                assert saved["persistence_receipt"]["status"] == "persisted"

            # GD_Manage_Versions: status, create, mutate, create, list, restore.
            st1 = await _call(client, "GD_Manage_Versions", {"garden_root": gr, "action": "status"})
            assert st1["summary_view"]["is_dirty"] is True

            cp1 = await _call(
                client,
                "GD_Manage_Versions",
                {"garden_root": gr, "action": "create", "subject": "Checkpoint 1", "summary": {"step": 1}},
            )
            cp1_id = cp1["version_id"]

            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "identifier": "VerRoom",
                    "x_dim": 4.0,
                    "y_dim": 4.0,
                    "height": 3.0,
                    "model_target": hb_a["target"],
                },
            )
            st2 = await _call(client, "GD_Manage_Versions", {"garden_root": gr, "action": "status"})
            assert st2["summary_view"]["is_dirty"] is True

            await _call(
                client,
                "GD_Manage_Versions",
                {"garden_root": gr, "action": "create", "subject": "Checkpoint 2", "summary": {"step": 2}},
            )
            v_list = await _call(client, "GD_Manage_Versions", {"garden_root": gr, "action": "list", "limit": 5})
            assert len(v_list["matches"]) >= 2
            assert v_list["matches"][0]["subject"] == "Checkpoint 2"

            await _call(
                client,
                "GD_Manage_Versions",
                {"garden_root": gr, "action": "restore", "version_id": cp1_id},
            )
            restored_sum = await _call(
                client,
                "HB_Get_Model_Summary",
                {"garden_root": gr, "model_target": hb_a["target"]},
            )
            assert restored_sum["object_counts"]["rooms"] == 0

            # Generate multi-domain artifacts for GD_List_Artifacts.
            await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "cie_sky",
                    "identifier": "art_sky",
                    "month": 6,
                    "day": 21,
                    "time": "12:00",
                },
            )
            vis = await _call(
                client,
                "LB_Honeybee_To_Visualization_Set",
                {"garden_root": gr, "model_target": hb_a["target"], "name": "art_vis", "return_visualization_set": False},
            )
            await _call(
                client,
                "LB_Export_Visualization_Set",
                {"garden_root": gr, "export_format": "vtkjs", "visualization_set_target": vis["target"], "name": "art_vtk"},
            )
            await _call(
                client,
                "LB_Export_Visualization_Set",
                {"garden_root": gr, "export_format": "html", "visualization_set_target": vis["target"], "name": "art_html"},
            )
            await _call(
                client,
                "DF_UWG_Run",
                {"garden_root": gr, "mode": "create_parameter", "identifier": "art_uwg_par"},
            )

            sky_arts = await _call(
                client,
                "GD_List_Artifacts",
                {"garden_root": gr, "artifact_type": "sky", "domain": "radiance"},
            )
            assert len(sky_arts["matches"]) == 1
            assert sky_arts["matches"][0]["artifact_type"] == "radiance_sky_file"

            vtk_arts = await _call(
                client,
                "GD_List_Artifacts",
                {"garden_root": gr, "artifact_type": "vtkjs", "domain": "visualize"},
            )
            assert len(vtk_arts["matches"]) == 1
            assert vtk_arts["matches"][0]["artifact_type"] == "visualization_vtkjs"

            html_arts = await _call(
                client,
                "GD_List_Artifacts",
                {"garden_root": gr, "artifact_type": "html", "query": "art_html", "limit": 1},
            )
            assert len(html_arts["matches"]) == 1

            limited_arts = await _call(client, "GD_List_Artifacts", {"garden_root": gr, "limit": 2})
            assert len(limited_arts["matches"]) == 2

            # GD_Properties_Library: save, search, get.
            mat = await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "opaque",
                    "identifier": "lib_concrete_200",
                    "params": {
                        "thickness": 0.2,
                        "conductivity": 1.4,
                        "density": 2200,
                        "specific_heat": 900,
                    },
                },
            )
            saved_lib = await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": gr,
                    "action": "save",
                    "domain": "honeybee_energy",
                    "object_family": "material",
                    "object_dict": mat["object_dict"],
                },
            )
            assert saved_lib["persistence_receipt"]["status"] == "persisted"

            searched_lib = await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": gr,
                    "action": "search",
                    "domain": "honeybee_energy",
                    "object_family": "material",
                    "query": "lib_concrete_200",
                },
            )
            assert len(searched_lib["matches"]) == 1
            got_by_target = await _call(
                client,
                "GD_Properties_Library",
                {"garden_root": gr, "action": "get", "target": searched_lib["matches"][0]["target"]},
            )
            assert got_by_target["object_dict"]["identifier"] == "lib_concrete_200"
            got_by_id = await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": gr,
                    "action": "get",
                    "domain": "honeybee_energy",
                    "object_family": "material",
                    "identifier": "lib_concrete_200",
                },
            )
            assert got_by_id["object_dict"]["identifier"] == "lib_concrete_200"

            # LB_Search_Standards_Library across energy, radiance, opendss.
            ep_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "energy", "query": "Office", "object_family": "program_type", "limit": 5},
            )
            assert len(ep_std["matches"]) >= 1
            rad_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "radiance", "query": "wall", "object_family": "modifier", "limit": 5},
            )
            assert len(rad_std["matches"]) >= 1
            dss_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "domain": "opendss",
                    "query": "OH",
                    "catalogs": ["transformer_properties", "power_lines"],
                    "limit": 5,
                },
            )
            assert len(dss_std["matches"]) >= 1

    asyncio.run(_run())


def test_unified_run_control_list_poll_cancel_and_logs(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    """Verify GD_List_Runs, GD_Poll_Run across all 7 domains, GD_Cancel_Run OS termination, and GD_Read_Run_Logs."""
    g_path = (tmp_path / "runs_garden").resolve()
    gr = g_path.as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "runs_garden", "root_dir": gr})
            manifest = GardenManifest.read(g_path)
            gid = manifest.garden_id

            # Seed 7 domain ledgers with deterministic staggered timestamps.
            def _seed_record(
                mgr: Any,
                *,
                run_id: str,
                created_at: str,
                recipe: str | None = None,
                status: str = "completed",
                outputs: Any = None,
                run_folder: str | None = None,
            ) -> dict[str, Any]:
                eff_recipe = recipe or mgr.default_recipe
                target = mgr.make_target(gid, run_id, recipe=eff_recipe)
                rec: dict[str, Any] = {
                    "run_id": run_id,
                    "target": target,
                    "recipe": eff_recipe,
                    "status": status,
                    "runtime_status": status,
                    "created_at": created_at,
                    "started_at": created_at,
                    "run_folder": run_folder or f"runs/{mgr.domain}/{run_id}",
                    "outputs": outputs if outputs is not None else [],
                }
                if status == "completed":
                    rec["completed_at"] = created_at
                mgr.upsert(g_path, rec, recipe=recipe if mgr.per_recipe_index else None)
                return target

            ep_dir = g_path / "runs" / "energy" / "ep_run_1"
            ep_dir.mkdir(parents=True, exist_ok=True)
            (ep_dir / "background_stdio.log").write_text(
                "\n".join(f"line-{i:04d}" for i in range(1, 26)) + "\n", encoding="utf-8"
            )
            (ep_dir / "nested").mkdir(exist_ok=True)
            (ep_dir / "nested" / "engine.err").write_text("ERR_SENTINEL: ok\n", encoding="utf-8")

            t_ep = _seed_record(
                _ENERGY_RUNS,
                run_id="ep_run_1",
                created_at="2026-01-01T00:00:01Z",
                outputs=[{"name": "eui", "path": "runs/energy/ep_run_1/eui.json", "exists": True}],
                run_folder="runs/energy/ep_run_1",
            )
            t_rad = _seed_record(
                _RADIANCE_RUNS,
                run_id="rad_run_1",
                recipe="point-in-time-grid",
                created_at="2026-01-01T00:00:02Z",
                outputs=[{"name": "results", "path": "runs/radiance/rad_run_1/results", "exists": True}],
            )
            t_uwg = _seed_record(
                _UWG_RUNS,
                run_id="uwg_run_1",
                created_at="2026-01-01T00:00:03Z",
                outputs={"morphed_epw": {"name": "morphed_epw", "exists": True}},
            )
            t_uo = _seed_record(
                _URBANOPT_RUNS,
                run_id="uo_run_1",
                created_at="2026-01-01T00:00:04Z",
                outputs=[{"name": "default_scenario_report", "path": "runs/urbanopt/uo_run_1/report.json"}],
            )
            t_des = _seed_record(
                _DES_RUNS,
                run_id="des_run_1",
                recipe="sys_param",
                created_at="2026-01-01T00:00:05Z",
                outputs=[{"name": "system_params", "path": "runs/dragonfly_des/sys_param/sys.json"}],
            )
            t_grid = _seed_record(
                _GRID_RUNS,
                run_id="grid_run_1",
                recipe="opendss",
                created_at="2026-01-01T00:00:06Z",
                outputs=[{"name": "opendss_csv", "path": "runs/dragonfly_grid/opendss/out.csv"}],
            )
            t_ff = _seed_record(
                _THERM_RUNS,
                run_id="ff_run_1",
                created_at="2026-01-01T00:00:07Z",
                outputs=[{"name": "thmz", "path": "runs/fairyfly_therm/ff.thmz"}],
            )

            # GD_List_Runs across all and filtered.
            all_runs = await _call(client, "GD_List_Runs", {"garden_root": gr, "domain": "all"})
            assert len(all_runs["matches"]) == 7
            assert all_runs["matches"][0]["run_id"] == "ff_run_1"  # newest first

            grid_runs = await _call(
                client, "GD_List_Runs", {"garden_root": gr, "domain": "dragonfly_grid", "status": "completed"}
            )
            assert [m["run_id"] for m in grid_runs["matches"]] == ["grid_run_1"]

            limited_runs = await _call(client, "GD_List_Runs", {"garden_root": gr, "limit": 3})
            assert len(limited_runs["matches"]) == 3

            # GD_Poll_Run across all 7 domains + include_outputs toggle.
            for expected_domain, target in [
                ("honeybee_energy", t_ep),
                ("honeybee_radiance", t_rad),
                ("dragonfly_uwg", t_uwg),
                ("urbanopt", t_uo),
                ("dragonfly_des", t_des),
                ("dragonfly_grid", t_grid),
                ("fairyfly", t_ff),
            ]:
                polled_full = await _call(
                    client, "GD_Poll_Run", {"garden_root": gr, "run_target": target, "include_outputs": True}
                )
                assert polled_full["domain"] == expected_domain
                assert "outputs" in polled_full
                assert polled_full["outputs"]

                polled_compact = await _call(
                    client, "GD_Poll_Run", {"garden_root": gr, "run_target": target, "include_outputs": False}
                )
                assert "outputs" not in polled_compact
                assert "outputs" not in polled_compact["summary_view"]
                assert "outputs" not in polled_compact["summary_view"]["run"]

            # Test GD_Poll_Run wait_seconds transition from running -> completed.
            _seed_record(
                _UWG_RUNS,
                run_id="uwg_wait_1",
                created_at="2026-01-01T00:00:08Z",
                status="running",
            )

            def _complete_uwg() -> None:
                time.sleep(0.25)
                rec = _UWG_RUNS.get(g_path, "uwg_wait_1")
                assert rec is not None
                rec["status"] = "completed"
                rec["runtime_status"] = "completed"
                rec["completed_at"] = utc_now_iso()
                _UWG_RUNS.upsert(g_path, rec)

            t = threading.Thread(target=_complete_uwg, daemon=True)
            t.start()
            try:
                waited = await _call(
                    client,
                    "GD_Poll_Run",
                    {
                        "garden_root": gr,
                        "domain": "dragonfly_uwg",
                        "run_id": "uwg_wait_1",
                        "wait_seconds": 3.0,
                        "poll_interval": 0.1,
                    },
                )
                assert waited["runtime_status"] == "completed"
            finally:
                t.join(timeout=2.0)

            # GD_Cancel_Run with a real sleeping subprocess via submit_worker_process.
            helper_py = tmp_path / "dummy_sleep_worker.py"
            helper_py.write_text(
                "import time\n"
                "def sleep_worker(seconds: float = 60.0) -> None:\n"
                "    print('DUMMY_WORKER_READY', flush=True)\n"
                "    time.sleep(seconds)\n",
                encoding="utf-8",
            )
            cancel_dir = g_path / "runs" / "energy" / "ep_cancel_1"
            t_cancel = _seed_record(
                _ENERGY_RUNS,
                run_id="ep_cancel_1",
                created_at="2026-01-01T00:00:09Z",
                status="running",
                run_folder="runs/energy/ep_cancel_1",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                part for part in (str(tmp_path), env.get("PYTHONPATH", "")) if part
            )
            proc = submit_worker_process(
                garden_root=g_path,
                run_dir=cancel_dir,
                worker_module="dummy_sleep_worker:sleep_worker",
                request={"seconds": 60.0},
                cwd=g_path,
                environment=env,
            )
            try:
                pid_file = cancel_dir / "worker.pid"
                assert pid_file.is_file()
                assert int(pid_file.read_text(encoding="utf-8").strip()) == proc.pid
                assert proc.poll() is None

                cancelled = await _call(
                    client,
                    "GD_Cancel_Run",
                    {"garden_root": gr, "run_target": t_cancel, "reason": "pytest cancel test"},
                )
                assert cancelled["cancelled"] is True
                assert cancelled["status"] == "cancelled"
                assert cancelled["runtime_status"] == "cancelled"
                assert cancelled["worker_pid"] == proc.pid

                proc.wait(timeout=5)
                assert proc.poll() is not None

                polled_cancelled = await _call(
                    client, "GD_Poll_Run", {"garden_root": gr, "run_target": t_cancel}
                )
                assert polled_cancelled["status"] == "cancelled"
                assert polled_cancelled["runtime_status"] == "cancelled"
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)

            # GD_Read_Run_Logs: valid tail + nested file + path traversal rejection.
            logs_default = await _call(
                client,
                "GD_Read_Run_Logs",
                {"garden_root": gr, "run_target": t_ep, "tail_lines": 5},
            )
            assert logs_default["log_file"] == "background_stdio.log"
            assert "line-0025" in logs_default["log_text"]
            assert "line-0001" not in logs_default["log_text"]
            assert "nested/engine.err" in logs_default["available_logs"]

            logs_nested = await _call(
                client,
                "GD_Read_Run_Logs",
                {"garden_root": gr, "run_target": t_ep, "log_file": "nested/engine.err", "tail_lines": 5},
            )
            assert "ERR_SENTINEL" in logs_nested["log_text"]

            for bad_path in ("../../garden.json", "../ep_run_1/../../garden.json", str(g_path / "garden.json")):
                with pytest.raises(Exception):
                    await _call(
                        client,
                        "GD_Read_Run_Logs",
                        {"garden_root": gr, "run_target": t_ep, "log_file": bad_path},
                    )

    asyncio.run(_run())


def test_honeybee_consolidation_and_batching(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Test consolidated Honeybee tools: create/import, batch objects, relate, apertures, shades, edits, transforms, removal, search, summary, validate."""
    gr = (tmp_path / "hb_garden").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "hb_garden", "root_dir": gr})
            m = await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "hb_main"})
            model_target = m["target"]

            # Batch create 2 adjacent rooms with deferred postprocess_strategy='none'.
            rooms_res = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "postprocess_strategy": "none",
                    "items": [
                        {"identifier": "Room_S", "x_dim": 6.0, "y_dim": 4.0, "height": 3.0, "origin": [0.0, 0.0, 0.0]},
                        {"identifier": "Room_N", "x_dim": 6.0, "y_dim": 4.0, "height": 3.0, "origin": [0.0, 4.0, 0.0]},
                    ],
                },
            )
            assert len(rooms_res["targets"]) == 2
            room_s_target = rooms_res["targets"][0]

            # Create an orphaned face before HB_Relate_Model.
            orphan_face = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "identifier": "Orphan_Wall",
                    "postprocess_strategy": "none",
                    "geometry": {
                        "type": "Face3D",
                        "boundary": [[15.0, 0.0, 0.0], [18.0, 0.0, 0.0], [18.0, 0.0, 3.0], [15.0, 0.0, 3.0]],
                    },
                },
            )

            # Solve adjacency once after batch build.
            relate_res = await _call(client, "HB_Relate_Model", {"garden_root": gr})
            assert relate_res["report"]["status"] == "ok"

            # Search faces by orientation and boundary_condition (and verify room_identifier filter isolates Room_S from Orphan_Wall).
            all_s_walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "orientation": "S",
                    "face_type": "Wall",
                    "boundary_condition": "Outdoors",
                },
            )
            assert len(all_s_walls["matches"]) == 2
            s_walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "orientation": "S",
                    "face_type": "Wall",
                    "boundary_condition": "Outdoors",
                    "room_identifier": "Room_S",
                },
            )
            assert len(s_walls["matches"]) == 1
            south_wall_target = s_walls["matches"][0]["target"]

            n_walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "orientation": "N",
                    "face_type": "Wall",
                    "boundary_condition": "Outdoors",
                },
            )
            assert len(n_walls["matches"]) == 1
            north_wall_target = n_walls["matches"][0]["target"]

            roofs = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "room_identifier": "Room_S",
                    "orientation": "horizontal_up",
                    "face_type": "RoofCeiling",
                },
            )
            assert len(roofs["matches"]) == 1
            roof_target = roofs["matches"][0]["target"]

            # Create Door on North exterior wall.
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "door",
                    "identifier": "North_Door",
                    "host_target": north_wall_target,
                },
            )

            # Create Apertures: parameters (WWR) + skylight_ratio.
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "generation_mode": "by_ratio",
                    "ratio": 0.4,
                    "host_target": south_wall_target,
                },
            )
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "skylight_ratio",
                    "ratio": 0.15,
                    "host_target": roof_target,
                },
            )

            # Create Shades: parametric louvers + orphaned geometry shade.
            await _call(
                client,
                "HB_Create_Shades",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "host_target": south_wall_target,
                    "generation_mode": "louver_by_count",
                    "parameters": {"depth": 0.4, "louver_count": 2},
                },
            )
            orphan_shade = await _call(
                client,
                "HB_Create_Shades",
                {
                    "garden_root": gr,
                    "mode": "geometry",
                    "identifier": "Orphan_Shade",
                    "is_detached": True,
                    "geometry": {
                        "type": "Face3D",
                        "boundary": [[10.0, 0.0, 0.0], [12.0, 0.0, 0.0], [12.0, 2.0, 0.0], [10.0, 2.0, 0.0]],
                    },
                },
            )

            # Look up valid standards IDs dynamically before batch HB_Edit_Objects.
            prog_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "energy", "query": "Office", "object_family": "program_type", "limit": 1},
            )
            cset_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "energy", "query": "SteelFramed", "object_family": "construction_set", "limit": 1},
            )
            prog_id = prog_std["matches"][0]["identifier"]
            cset_id = cset_std["matches"][0]["identifier"]

            # Single + batch HB_Edit_Objects.
            await _call(
                client,
                "HB_Edit_Objects",
                {
                    "garden_root": gr,
                    "target": room_s_target,
                    "story": "Floor_1",
                    "zone": "South_Zone",
                    "display_name": "South Office",
                },
            )
            await _call(
                client,
                "HB_Edit_Objects",
                {
                    "garden_root": gr,
                    "room_identifiers": ["Room_S", "Room_N"],
                    "energy_properties": {
                        "program_type": prog_id,
                        "construction_set": cset_id,
                    },
                },
            )

            # Search with story, zone, min_area, max_area, and orientation.
            room_search = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "story": "Floor_1",
                    "zone": "South_Zone",
                    "min_area": 20.0,
                    "max_area": 30.0,
                },
            )
            assert [m["identifier"] for m in room_search["matches"]] == ["Room_S"]

            s_aps = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": gr, "object_type": "aperture", "orientation": "S"},
            )
            assert len(s_aps["matches"]) >= 1

            # HB_Get_Model_Summary: WWR overall + per-orientation + energy/radiance coverage.
            summary = await _call(client, "HB_Get_Model_Summary", {"garden_root": gr})
            assert summary["object_counts"]["rooms"] == 2
            assert summary["object_counts"]["apertures"] >= 2
            assert summary["object_counts"]["doors"] == 1
            assert summary["object_counts"]["shades"] >= 3
            assert summary["total_floor_area"] == pytest.approx(48.0)
            assert summary["overall_wwr"] > 0
            assert summary["wwr_by_orientation"]["S"] > 0
            assert "Floor_1" in summary["stories"]
            assert "South_Zone" in summary["zones"]
            assert prog_id in summary["energy"]["program_types"]
            assert cset_id in summary["energy"]["construction_sets"]
            assert "radiance" in summary

            # HB_Transform_Objects: move, rotate, scale, mirror on Orphan_Shade.
            shade_t = orphan_shade["target"]
            for tx_args in [
                {"operation": "move", "vector": [1.0, 0.0, 0.0]},
                {"operation": "rotate", "axis": [0.0, 0.0, 1.0], "angle_degrees": 90.0, "origin": [10.0, 0.0, 0.0]},
                {"operation": "scale", "factor": 1.2, "origin": [10.0, 0.0, 0.0]},
                {"operation": "mirror", "plane": {"o": [10.0, 0.0, 0.0], "n": [1.0, 0.0, 0.0]}},
            ]:
                tx_res = await _call(
                    client,
                    "HB_Transform_Objects",
                    {"garden_root": gr, "target": shade_t, **tx_args},
                )
                assert tx_res["report"]["status"] == "ok"

            # Batch HB_Remove_Objects removing orphaned face & orphaned shade.
            rm_res = await _call(
                client,
                "HB_Remove_Objects",
                {"garden_root": gr, "targets": [orphan_face["target"], shade_t]},
            )
            assert rm_res["report"]["status"] == "ok"

            summary_after_rm = await _call(client, "HB_Get_Model_Summary", {"garden_root": gr})
            assert summary_after_rm["object_counts"]["orphaned_faces"] == 0

            # HB_Validate_Model.
            val = await _call(client, "HB_Validate_Model", {"garden_root": gr})
            assert val["is_valid"] is True
            assert val["issues"] == []

            # HB_Create_Model import mode.
            imported = await _call(
                client,
                "HB_Create_Model",
                {
                    "garden_root": gr,
                    "import_file_path": model_target["path"],
                    "identifier": "hb_imported",
                    "set_base": False,
                },
            )
            imp_sum = await _call(
                client,
                "HB_Get_Model_Summary",
                {"garden_root": gr, "model_target": imported["target"]},
            )
            assert imp_sum["object_counts"]["rooms"] == 2

    asyncio.run(_run())


def test_energy_consolidation_and_mocked_simulation(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Exercise all 9 Energy authoring tools + weather/sim-par + mocked EP_Start_Simulation."""
    gr = (tmp_path / "ep_garden").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "ep_garden", "root_dir": gr})
            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "ep_model"})
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "identifier": "Zone_1",
                    "x_dim": 6.0,
                    "y_dim": 5.0,
                    "height": 3.0,
                },
            )
            s_face = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": gr, "object_type": "face", "orientation": "S"},
            )
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "generation_mode": "by_ratio",
                    "ratio": 0.35,
                    "host_target": s_face["matches"][0]["target"],
                },
            )

            # EP_Create_Material across opaque, glazing, gas, shade, frame.
            mat_opaque = await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "opaque",
                    "identifier": "conc_200",
                    "params": {"thickness": 0.2, "conductivity": 1.4, "density": 2200, "specific_heat": 900},
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            assert "target" in mat_opaque and "object_dict" not in mat_opaque

            mat_nomass = await _call(
                client,
                "EP_Create_Material",
                {"material_type": "opaque_no_mass", "identifier": "insul_nomass", "params": {"r_value": 2.5}, "garden_root": gr},
            )
            await _call(
                client,
                "EP_Create_Material",
                {"material_type": "vegetation", "identifier": "green_roof_veg", "params": {}},
            )
            await _call(
                client,
                "EP_Create_Material",
                {"material_type": "simple_glazing", "identifier": "sgl_glz", "params": {"u_factor": 1.8, "shgc": 0.4, "vt": 0.65}},
            )
            mat_glz = await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "window_glazing",
                    "identifier": "clear_6mm",
                    "params": {"thickness": 0.006, "solar_transmittance": 0.77, "visible_transmittance": 0.88},
                    "garden_root": gr,
                },
            )
            mat_gas = await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "window_gas",
                    "identifier": "argon_12mm",
                    "params": {"gas_type": "Argon", "thickness": 0.012},
                    "garden_root": gr,
                },
            )
            await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "window_shade",
                    "identifier": "roller_shade",
                    "params": {
                        "solar_transmittance": 0.2,
                        "solar_reflectance": 0.5,
                        "visible_transmittance": 0.2,
                        "visible_reflectance": 0.5,
                    },
                },
            )
            mat_frame = await _call(
                client,
                "EP_Create_Material",
                {
                    "material_type": "window_frame",
                    "identifier": "alu_frame",
                    "params": {"width": 0.05, "conductance": 2.5},
                    "garden_root": gr,
                },
            )

            # EP_Create_Construction across all 4 types.
            c_opaque = await _call(
                client,
                "EP_Create_Construction",
                {
                    "construction_type": "opaque",
                    "identifier": "wall_const",
                    "materials": [mat_opaque["target"], mat_nomass["target"]],
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            await _call(
                client,
                "EP_Create_Construction",
                {"construction_type": "window", "identifier": "win_simple", "u_factor": 1.6, "shgc": 0.35, "vt": 0.6},
            )
            c_win_layered = await _call(
                client,
                "EP_Create_Construction",
                {
                    "construction_type": "window",
                    "identifier": "win_layered",
                    "materials": [mat_glz["target"], mat_gas["target"], mat_glz["target"]],
                    "frame": mat_frame["target"],
                    "garden_root": gr,
                },
            )
            c_shade = await _call(
                client,
                "EP_Create_Construction",
                {"construction_type": "shade", "identifier": "shade_c", "params": {"solar_reflectance": 0.35}, "garden_root": gr},
            )
            await _call(
                client,
                "EP_Create_Construction",
                {"construction_type": "air_boundary", "identifier": "air_c", "params": {"air_mixing_per_area": 0.1}},
            )

            # EP_Create_Construction_Set with inline subset & inline construction dict.
            cset = await _call(
                client,
                "EP_Create_Construction_Set",
                {
                    "identifier": "custom_cset",
                    "wall_set": {"exterior_construction": c_opaque["target"]},
                    "aperture_set": {"window_construction": c_win_layered["target"], "skylight_construction": {"u_factor": 1.5, "shgc": 0.35, "vt": 0.6}},
                    "shade_construction": c_shade["target"],
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            assert cset["target"]["object_family"] == "construction_set"

            # EP_Create_Load across all 9 load_types.
            for load_type, params in [
                ("people", {"people_per_area": 0.05}),
                ("lighting", {"watts_per_area": 8.0}),
                ("electric_equipment", {"watts_per_area": 6.0}),
                ("gas_equipment", {"watts_per_area": 1.0}),
                ("service_hot_water", {"flow_per_area": 0.1}),
                ("infiltration", {"flow_per_exterior_area": 0.0002}),
                ("ventilation", {"flow_per_person": 0.0025}),
                ("setpoint", {"heating_setpoint": 20.0, "cooling_setpoint": 24.0}),
                ("zone_ventilation_fan", {"flow_rate": 0.15}),
            ]:
                ld = await _call(
                    client,
                    "EP_Create_Load",
                    {"load_type": load_type, "identifier": f"ld_{load_type}", "params": params},
                )
                assert ld["object_dict"]["identifier"] == f"ld_{load_type}"

            # EP_Create_Program_Type with inline shorthands.
            pt = await _call(
                client,
                "EP_Create_Program_Type",
                {
                    "identifier": "custom_office_pt",
                    "people": {"people_per_area": 0.05},
                    "lighting": {"watts_per_area": 8.5},
                    "electric_equipment": {"watts_per_area": 5.0},
                    "infiltration": {"flow_per_exterior_area": 0.0002},
                    "ventilation": {"flow_per_person": 0.0025},
                    "setpoint": {"heating_setpoint": 20.0, "cooling_setpoint": 24.0},
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            assert pt["target"]["object_family"] == "program_type"

            # EP_Create_Schedule_Ruleset: 24-value list + inline rule, and interval rules.
            sched1 = await _call(
                client,
                "EP_Create_Schedule_Ruleset",
                {
                    "identifier": "occ_24",
                    "default_day_schedule": [0.0] * 8 + [1.0] * 10 + [0.0] * 6,
                    "schedule_rules": [
                        {
                            "day": {"values": [0.0, 0.25, 0.0], "times": ["00:00", "09:00", "17:00"]},
                            "weekdays": ["sat", "sun"],
                        }
                    ],
                    "garden_root": gr,
                    "return_data": False,
                    "return_object_dict": False,
                },
            )
            assert sched1["target"]["object_family"] == "schedule"
            assert sched1["data_target"]["target_type"] == "ladybug_data_collection"

            sched2 = await _call(
                client,
                "EP_Create_Schedule_Ruleset",
                {
                    "identifier": "occ_intervals",
                    "default_value": 0.0,
                    "rules": [{"start_time": "08:00", "end_time": "18:00", "value": 1.0, "days": "weekdays"}],
                },
            )
            assert len(sched2["object_dict"]["schedule_rules"]) == 1

            # EP_Create_HVAC_Template: search + IdealAirSystem + standards template.
            hvac_search = await _call(
                client,
                "EP_Create_HVAC_Template",
                {"query": "vav", "return_object": False},
            )
            assert len(hvac_search["matches"]) >= 1

            ideal_hvac = await _call(
                client,
                "EP_Create_HVAC_Template",
                {
                    "system_type": "IdealAirSystem",
                    "identifier": "ideal_office",
                    "economizer_type": "DifferentialDryBulb",
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            assert ideal_hvac["target"]["object_family"] == "hvac"

            ptac_hvac = await _call(
                client,
                "EP_Create_HVAC_Template",
                {
                    "system_type": "PTAC",
                    "identifier": "ptac_office",
                    "vintage": "ASHRAE_2019",
                    "garden_root": gr,
                    "return_object_dict": False,
                },
            )
            assert ptac_hvac["target"]["object_family"] == "hvac"

            # EP_Create_PV_Or_Load_Center.
            pv = await _call(
                client,
                "EP_Create_PV_Or_Load_Center",
                {
                    "object_type": "pv_properties",
                    "identifier": "pv_roof",
                    "params": {"rated_efficiency": 0.2},
                    "garden_root": gr,
                },
            )
            assert pv["target"]["object_family"] == "pv_properties"
            elc = await _call(
                client,
                "EP_Create_PV_Or_Load_Center",
                {
                    "object_type": "electric_load_center",
                    "identifier": "main_elc",
                    "params": {"inverter_efficiency": 0.96},
                    "garden_root": gr,
                },
            )
            assert elc["target"]["object_family"] == "electric_load_center"

            # EP_Setup_Room_Energy_Controls across all 3 control_types.
            for ctrl_type in ("simple_ventilation", "airflow_network", "daylighting_control"):
                ctrl_res = await _call(
                    client,
                    "EP_Setup_Room_Energy_Controls",
                    {"garden_root": gr, "control_type": ctrl_type},
                )
                assert ctrl_res["report"]["status"] == "ok"

            # LB_Manage_Weather: import -> search -> read_data.
            w_imp = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "import", "source_path": _weather_source_folder(tmp_path)},
            )
            w_target = w_imp["target"]
            assert w_target["target_type"] == "weather_file"
            w_search = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "search", "require_ddy": True},
            )
            assert len(w_search["matches"]) >= 1
            w_data = await _call(
                client,
                "LB_Manage_Weather",
                {
                    "garden_root": gr,
                    "action": "read_data",
                    "weather_target": w_target,
                    "data_type": "dry_bulb_temperature",
                    "include_values": True,
                    "max_values": 5,
                },
            )
            assert w_data["target"]["target_type"] == "ladybug_data_collection"
            assert len(w_data["summary_view"]["values"]) == 5
            assert w_data["summary_view"]["values_truncated"] is True

            # EP_Create_Simulation_Parameter: output_request mode + simulation_parameter mode.
            out_req = await _call(
                client,
                "EP_Create_Simulation_Parameter",
                {
                    "garden_root": gr,
                    "mode": "output_request",
                    "identifier": "ep_out_req",
                    "presets": ["zone_energy_use"],
                    "reporting_frequency": "Monthly",
                },
            )
            assert out_req["target"]["target_type"] == "energy_output_request"

            sim_par = await _call(
                client,
                "EP_Create_Simulation_Parameter",
                {
                    "garden_root": gr,
                    "mode": "simulation_parameter",
                    "identifier": "ep_sim_par",
                    "run_period": {"start_month": 1, "start_day": 1, "end_month": 1, "end_day": 7},
                    "design_days": ["99.6/0.4"],
                    "weather_target": w_target,
                    "output_request_target": out_req["target"],
                },
            )
            assert sim_par["target"]["target_type"] == "simulation_parameter"

            # Mocked EP_Start_Simulation verifying worker_pid & GD_Poll_Run handoff.
            with mock.patch(
                "garden.run_energy.annual.submit_worker_process",
                return_value=SimpleNamespace(pid=42424),
            ):
                ep_run = await _call(
                    client,
                    "EP_Start_Simulation",
                    {
                        "garden_root": gr,
                        "weather_target": w_target,
                        "simulation_parameter_target": sim_par["target"],
                        "run_id": "ep_mock_sim",
                    },
                )
            assert ep_run["worker_pid"] == 42424
            assert ep_run["poll_next"]["tool"] == "GD_Poll_Run"
            assert ep_run["summary_view"]["poll_next"]["tool"] == "GD_Poll_Run"

            polled = await _call(client, "GD_Poll_Run", {"garden_root": gr, "run_target": ep_run["run_target"]})
            assert polled["summary_view"]["worker_pid"] == 42424

    asyncio.run(_run())


def test_radiance_consolidation_and_mocked_simulation(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Exercise Radiance sky assets, all 5 modifier types, scene assets, dynamic group, params, and mocked start."""
    gr = (tmp_path / "rad_garden").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "rad_garden", "root_dir": gr})
            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "rad_model"})
            await _call(
                client,
                "HB_Create_Objects",
                {"garden_root": gr, "object_type": "room", "identifier": "Rad_Room", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0},
            )
            s_wall = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": gr, "object_type": "face", "orientation": "S"},
            )
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "generation_mode": "by_ratio",
                    "ratio": 0.4,
                    "host_target": s_wall["matches"][0]["target"],
                },
            )
            ap_search = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": gr, "object_type": "aperture"},
            )
            ap_target = ap_search["matches"][0]["target"]

            # RAD_Create_Sky_Asset: cie_sky, climate_based_sky, wea_clear_sky, sky_matrix.
            cie = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "cie_sky",
                    "identifier": "cie_noon",
                    "month": 6,
                    "day": 21,
                    "time": "12:00",
                    "latitude": 37.6,
                    "longitude": -122.4,
                    "sky_type": "sunny",
                },
            )
            assert cie["target"]["target_type"] == "radiance_sky_file"

            cb = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "climate_based_sky",
                    "identifier": "cb_noon",
                    "month": 6,
                    "day": 21,
                    "time": "12:00",
                    "direct_normal_irradiance": 700,
                    "diffuse_horizontal_irradiance": 120,
                },
            )
            assert cb["target"]["target_type"] == "radiance_sky_file"

            wea = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "wea_clear_sky",
                    "identifier": "clear_wea",
                    "location": {"city": "SF", "latitude": 37.62, "longitude": -122.38, "time_zone": -8, "elevation": 5},
                },
            )
            assert wea["target"]["target_type"] == "wea_file"

            skymtx = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {"garden_root": gr, "asset_type": "sky_matrix", "identifier": "sf_skymtx", "wea_target": wea["target"], "compute": False},
            )
            assert skymtx["target"]["target_type"] == "sky_matrix"

            # RAD_Create_Modifier: all 5 types.
            mods: dict[str, dict[str, Any]] = {}
            for mtype, extra in [
                ("opaque", {"rgb_reflectance": 0.5, "specularity": 0.0, "roughness": 0.1}),
                ("glass", {"rgb_transmittance": 0.65}),
                ("metal", {"rgb_reflectance": 0.8, "specularity": 0.9, "roughness": 0.05}),
                ("mirror", {"rgb_reflectance": 0.9}),
                ("trans", {"rgb_reflectance": 0.4, "transmitted_diff": 0.2, "transmitted_spec": 0.1}),
            ]:
                mods[mtype] = await _call(
                    client,
                    "RAD_Create_Modifier",
                    {
                        "modifier_type": mtype,
                        "identifier": f"mod_{mtype}",
                        "garden_root": gr,
                        "return_object_dict": False,
                        **extra,
                    },
                )
                assert mods[mtype]["target"]["object_family"] == "modifier"

            # RAD_Create_Scene_Asset: sensor_grid + view attached to model.
            sg = await _call(
                client,
                "RAD_Create_Scene_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "sensor_grid",
                    "identifier": "workplane_grid",
                    "x_dim": 4.0,
                    "y_dim": 4.0,
                    "height": 0.8,
                    "x_count": 2,
                    "y_count": 2,
                    "attach_to_model": True,
                    "return_object_dict": False,
                },
            )
            assert sg["target"]["target_type"] == "radiance_sensor_grid"
            assert sg["summary_view"]["sensor_count"] == 4

            vw = await _call(
                client,
                "RAD_Create_Scene_Asset",
                {
                    "garden_root": gr,
                    "asset_type": "view",
                    "identifier": "south_view",
                    "position": [2.0, 2.0, 1.5],
                    "direction": [0.0, -1.0, 0.0],
                    "up_vector": [0.0, 0.0, 1.0],
                    "attach_to_model": True,
                    "return_object_dict": False,
                },
            )
            assert vw["target"]["target_type"] == "radiance_view"

            # RAD_Setup_Dynamic_Group with inline states & inline StateGeometry.
            dyn = await _call(
                client,
                "RAD_Setup_Dynamic_Group",
                {
                    "garden_root": gr,
                    "targets": [ap_target],
                    "dynamic_group_identifier": "dyn_aperture_blinds",
                    "states": [
                        {
                            "modifier": mods["glass"]["target"],
                            "shades": [
                                {
                                    "identifier": "slat_0",
                                    "vertices": [[1.0, 0.0, 1.5], [2.0, 0.0, 1.5], [2.0, 0.0, 1.8], [1.0, 0.0, 1.8]],
                                    "modifier": mods["opaque"]["target"],
                                }
                            ],
                        }
                    ],
                },
            )
            assert dyn["report"]["status"] == "ok"

            # RAD_Create_Parameters.
            rad_par = await _call(
                client,
                "RAD_Create_Parameters",
                {"recipe_type": "point-in-time-grid", "detail_level": "low", "ab": 2, "ad": 512},
            )
            assert "-ab 2" in rad_par["radiance_parameters"]
            assert "-ad 512" in rad_par["radiance_parameters"]

            # Mocked RAD_Start_Simulation verifying worker_pid & GD_Poll_Run.
            with mock.patch(
                "garden.radiance.run.submit_worker_process",
                return_value=SimpleNamespace(pid=51515),
            ):
                rad_run = await _call(
                    client,
                    "RAD_Start_Simulation",
                    {
                        "garden_root": gr,
                        "recipe": "point-in-time-grid",
                        "radiance_sky_file": cie["target"],
                        "radiance_parameters": rad_par,
                        "run_id": "rad_mock_sim",
                    },
                )
            assert rad_run["worker_pid"] == 51515
            assert rad_run["poll_next"]["tool"] == "GD_Poll_Run"
            assert rad_run["summary_view"]["poll_next"]["tool"] == "GD_Poll_Run"
            polled = await _call(client, "GD_Poll_Run", {"garden_root": gr, "run_target": rad_run["run_target"]})
            assert polled["summary_view"]["worker_pid"] == 51515

    asyncio.run(_run())


def test_dragonfly_des_grid_uwg_and_mocked_workers(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Exercise Dragonfly Core, DES, Grid, UWG properties, and mocked background worker starts."""
    g_path = (tmp_path / "df_garden").resolve()
    gr = g_path.as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "df_garden", "root_dir": gr})

            # Dragonfly Core modeling.
            df_model = await _call(client, "DF_Model", {"garden_root": gr, "identifier": "district_1"})
            batch_rooms = await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room2d",
                    "items": [
                        {"identifier": "DF_R1", "x_dim": 10.0, "y_dim": 10.0, "height": 3.5, "origin": [0.0, 0.0, 0.0]},
                        {"identifier": "DF_R2", "x_dim": 10.0, "y_dim": 10.0, "height": 3.5, "origin": [10.0, 0.0, 0.0]},
                    ],
                },
            )
            assert len(batch_rooms["targets"]) == 2
            story = await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "story",
                    "identifier": "DF_Story_1",
                    "room2d_targets": batch_rooms["targets"],
                    "floor_to_floor_height": 3.5,
                },
            )
            bldg = await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "building",
                    "identifier": "DF_Bldg_1",
                    "story_targets": [story["target"]],
                },
            )
            await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "context_shade",
                    "identifier": "DF_Tree_1",
                    "x_dim": 4.0,
                    "y_dim": 4.0,
                    "height": 5.0,
                    "origin": [-6.0, 0.0, 0.0],
                },
            )
            await _call(
                client,
                "DF_Edit_Object",
                {
                    "garden_root": gr,
                    "object_type": "building",
                    "building_identifier": "DF_Bldg_1",
                    "display_name": "Main District Building",
                },
            )
            await _call(
                client,
                "DF_Process_Geometry",
                {"garden_root": gr, "operation": "clean", "room2d_target": batch_rooms["targets"][0]},
            )
            await _call(
                client,
                "DF_Process_Geometry",
                {"garden_root": gr, "operation": "solve_adjacency", "story_target": story["target"]},
            )
            await _call(
                client,
                "DF_Apply_Properties",
                {
                    "garden_root": gr,
                    "property_domain": "window",
                    "host_target": bldg["target"],
                    "window_parameter": {"parameter_type": "simple_window_ratio", "window_ratio": 0.35},
                },
            )
            await _call(
                client,
                "DF_Apply_Properties",
                {
                    "garden_root": gr,
                    "property_domain": "shading",
                    "host_target": bldg["target"],
                    "shading_parameter": {"parameter_type": "overhang", "depth": 0.6, "angle": 0.0},
                },
            )
            df_sum = await _call(client, "DF_Inspect_Model", {"garden_root": gr, "view": "model_summary"})
            assert df_sum["summary_view"]["counts"]["buildings"] == 1
            df_val = await _call(client, "DF_Validate_Model", {"garden_root": gr})
            assert df_val["is_valid"] is True
            df_vis = await _call(
                client,
                "DF_To_Visualization_Set",
                {"garden_root": gr, "mode": "model", "return_visualization_set": False},
            )
            assert df_vis["visualization_set_target"]["target_type"] == "visualization_set"

            # DES authoring with inline loop parameter dictionaries.
            conn = await _call(
                client,
                "DF_DES_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "thermal_connector",
                    "identifier": "conn_1",
                    "polyline_points": [[0.0, 0.0], [10.0, 0.0]],
                },
            )
            ghe = await _call(
                client,
                "DF_DES_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "ground_heat_exchanger",
                    "identifier": "ghe_1",
                    "footprint_points": [[25.0, 0.0], [35.0, 0.0], [35.0, 10.0], [25.0, 10.0]],
                },
            )
            loop_5g = await _call(
                client,
                "DF_DES_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "fifth_gen_thermal_loop",
                    "identifier": "loop_5g",
                    "connector_targets": [conn["target"]],
                    "soil_parameter": {"conductivity": 2.0, "undisturbed_temperature": 14.0},
                    "horizontal_pipe_parameter": {"buried_depth": 1.5},
                },
            )
            assert loop_5g["summary_view"]["has_soil_parameters"] is True
            loop_ghe = await _call(
                client,
                "DF_DES_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "ghe_thermal_loop",
                    "identifier": "loop_ghe",
                    "ground_heat_exchanger_targets": [ghe["target"]],
                    "connector_targets": [conn["target"]],
                    "soil_parameter": {"conductivity": 2.2},
                    "fluid_parameter": {"fluid_type": "Water"},
                    "pipe_parameter": {"arrangement": "SingleUTube"},
                    "borehole_parameter": {"min_depth": 50.0, "max_depth": 120.0},
                    "design_parameter": {"method": "AreaProportional"},
                },
            )
            assert loop_ghe["summary_view"]["has_design_parameters"] is True

            # Grid authoring using OpenDSS standards lookups.
            tx_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "opendss", "query": "OH", "catalogs": ["transformer_properties"], "limit": 1},
            )
            pl_std = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "opendss", "query": "1P", "catalogs": ["power_lines"], "limit": 1},
            )
            sub = await _call(
                client,
                "DF_Grid_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "substation",
                    "identifier": "sub_1",
                    "footprint_points": [[-10.0, -10.0], [-5.0, -10.0], [-5.0, -5.0], [-10.0, -5.0]],
                },
            )
            tx = await _call(
                client,
                "DF_Grid_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "transformer",
                    "identifier": "tx_1",
                    "footprint_points": [[0.0, -5.0], [2.0, -5.0], [2.0, -3.0], [0.0, -3.0]],
                    "transformer_properties_identifier": tx_std["matches"][0]["identifier"],
                },
            )
            econn = await _call(
                client,
                "DF_Grid_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "electrical_connector",
                    "identifier": "econn_1",
                    "polyline_points": [[-7.5, -7.5], [1.0, -4.0]],
                    "power_line_identifier": pl_std["matches"][0]["identifier"],
                },
            )
            enet = await _call(
                client,
                "DF_Grid_Create_Object",
                {
                    "garden_root": gr,
                    "kind": "electrical_network",
                    "identifier": "enet_1",
                    "substation_target": sub["target"],
                    "transformer_targets": [tx["target"]],
                    "connector_targets": [econn["target"]],
                },
            )
            assert enet["target"]["kind"] == "electrical_network"
            fin = await _call(
                client,
                "DF_Grid_Create_Object",
                {"garden_root": gr, "kind": "financial_parameters", "identifier": "fin_1", "analysis_years": 20},
            )
            assert fin["target"]["kind"] == "financial_parameters"

            # UWG Properties inspect + apply.
            uwg_before = await _call(client, "DF_UWG_Properties", {"garden_root": gr, "action": "get_summary"})
            assert uwg_before["summary_view"]["counts"]["buildings"] == 1
            await _call(
                client,
                "DF_UWG_Properties",
                {
                    "garden_root": gr,
                    "action": "apply",
                    "host_target": df_model["target"],
                    "tree_coverage_fraction": 0.25,
                    "grass_coverage_fraction": 0.15,
                },
            )
            await _call(
                client,
                "DF_UWG_Properties",
                {
                    "garden_root": gr,
                    "action": "apply",
                    "host_target": bldg["target"],
                    "program": "MediumOffice",
                    "vintage": "New",
                    "wall_albedo": 0.3,
                },
            )
            uwg_after = await _call(client, "DF_UWG_Properties", {"garden_root": gr, "action": "get_summary"})
            assert uwg_after["summary_view"]["model"]["uwg"]["fields"]["tree_coverage_fraction"] == pytest.approx(0.25)

            # Mocked background worker checks for run_urbanopt, dragonfly_des, dragonfly_grid, and run_uwg.
            w_imp = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "import", "source_path": _weather_source_folder(tmp_path)},
            )
            mock_dir = g_path / "artifacts" / "mock_uo"
            mock_dir.mkdir(parents=True, exist_ok=True)
            geojson_path = mock_dir / "feature.geojson"
            csv_path = mock_dir / "scenario.csv"
            geojson_path.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
            csv_path.write_text("Building Id,Building Name\n", encoding="utf-8")

            manifest = GardenManifest.read(g_path)
            gid = manifest.garden_id
            proj_target = {
                "target_type": "artifact",
                "domain": "urbanopt",
                "garden_id": gid,
                "artifact_type": "urbanopt_project_folder",
                "identifier": "mock_uo_proj",
                "path": "artifacts/mock_uo",
            }
            feat_target = {
                "target_type": "artifact",
                "domain": "dragonfly_des",
                "garden_id": gid,
                "artifact_type": "dragonfly_des_feature_geojson",
                "identifier": "mock_feat",
                "path": "artifacts/mock_uo/feature.geojson",
            }
            scen_target = {
                "target_type": "artifact",
                "domain": "dragonfly_des",
                "garden_id": gid,
                "artifact_type": "dragonfly_des_scenario_csv",
                "identifier": "mock_scen",
                "path": "artifacts/mock_uo/scenario.csv",
            }
            for item in (proj_target, feat_target, scen_target):
                manifest.upsert_artifact(item, key_fields=("domain", "artifact_type", "identifier"))
            manifest.write(g_path)

            ready_preflight = {
                "status": "ok",
                "runtime_status": "ready",
                "issues": [],
                "missing": [],
                "recommended_next_tools": [],
                "runtime": {},
            }

            with (
                mock.patch("garden.run_urbanopt.preflight_urbanopt_runtime", return_value=ready_preflight),
                mock.patch("garden.run_urbanopt.prime_urbanopt_sdk_version_cache"),
                mock.patch("garden.run_urbanopt.submit_worker_process", return_value=SimpleNamespace(pid=61001)),
            ):
                uo_run = await _call(
                    client,
                    "DF_URBANopt_Start_Simulation",
                    {
                        "garden_root": gr,
                        "workflow_mode": "energy",
                        "prepared_project_target": proj_target,
                        "feature_geojson_target": feat_target,
                        "scenario_csv_target": scen_target,
                        "run_id": "uo_mock_sim",
                    },
                )
            assert uo_run["worker_pid"] == 61001
            assert uo_run["poll_next"]["tool"] == "GD_Poll_Run"

            with (
                mock.patch("garden.dragonfly_des.runs._preflight_gmt_runtime", return_value=ready_preflight),
                mock.patch("garden.dragonfly_des.runs.submit_worker_process", return_value=SimpleNamespace(pid=61002)),
            ):
                des_run = await _call(
                    client,
                    "DF_DES_Run_Step",
                    {
                        "garden_root": gr,
                        "step": "sys_param",
                        "feature_geojson_target": feat_target,
                        "scenario_csv_target": scen_target,
                        "run_id": "des_mock_sim",
                    },
                )
            assert des_run["worker_pid"] == 61002
            assert des_run["poll_next"]["tool"] == "GD_Poll_Run"

            with (
                mock.patch("garden.dragonfly_grid.runs._preflight_opendss_runtime", return_value=ready_preflight),
                mock.patch("garden.dragonfly_grid.runs.submit_worker_process", return_value=SimpleNamespace(pid=61003)),
            ):
                grid_run = await _call(
                    client,
                    "DF_Grid_Start_Simulation",
                    {
                        "garden_root": gr,
                        "engine": "opendss",
                        "feature_geojson_target": feat_target,
                        "scenario_csv_target": scen_target,
                        "run_id": "grid_mock_sim",
                    },
                )
            assert grid_run["worker_pid"] == 61003
            assert grid_run["poll_next"]["tool"] == "GD_Poll_Run"

            with mock.patch("garden.run_uwg.submit_worker_process", return_value=SimpleNamespace(pid=61004)):
                uwg_run = await _call(
                    client,
                    "DF_UWG_Run",
                    {
                        "garden_root": gr,
                        "mode": "simulate",
                        "weather_target": w_imp["target"],
                        "run_id": "uwg_mock_sim",
                    },
                )
            assert uwg_run["worker_pid"] == 61004
            assert uwg_run["poll_next"]["tool"] == "GD_Poll_Run"

            for expected_pid, run_res in [
                (61001, uo_run),
                (61002, des_run),
                (61003, grid_run),
                (61004, uwg_run),
            ]:
                polled = await _call(
                    client, "GD_Poll_Run", {"garden_root": gr, "run_target": run_res["run_target"]}
                )
                assert polled["summary_view"]["worker_pid"] == expected_pid

    asyncio.run(_run())


def test_comfort_and_visualization_consolidation(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Exercise LB_Calculate_Comfort (pmv/adaptive/utci) and all consolidated visualize tools."""
    g_path = (tmp_path / "viz_garden").resolve()
    gr = g_path.as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "viz_garden", "root_dir": gr})
            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "viz_hb"})
            room = await _call(
                client,
                "HB_Create_Objects",
                {"garden_root": gr, "object_type": "room", "identifier": "Viz_Room", "x_dim": 5.0, "y_dim": 5.0, "height": 3.0},
            )
            w_imp = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "import", "source_path": _weather_source_folder(tmp_path)},
            )
            w_target = w_imp["target"]

            dbt = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {"garden_root": gr, "action": "read_data", "weather_target": w_target, "data_type": "dry_bulb_temperature"},
                )
            )["target"]
            rh = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {"garden_root": gr, "action": "read_data", "weather_target": w_target, "data_type": "relative_humidity"},
                )
            )["target"]
            ws = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {"garden_root": gr, "action": "read_data", "weather_target": w_target, "data_type": "wind_speed"},
                )
            )["target"]
            wd = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {"garden_root": gr, "action": "read_data", "weather_target": w_target, "data_type": "wind_direction"},
                )
            )["target"]

            # LB_Calculate_Comfort: pmv, adaptive, utci.
            pmv = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": gr,
                    "model": "pmv",
                    "air_temperature_target": dbt,
                    "relative_humidity_target": rh,
                },
            )
            assert pmv["target"]["target_type"] == "ladybug_data_collection"
            assert "comfortable" in pmv["summary_view"]["percentages"]

            adaptive = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": gr,
                    "model": "adaptive",
                    "outdoor_temperature_target": dbt,
                    "operative_temperature_target": dbt,
                },
            )
            assert adaptive["target"]["target_type"] == "ladybug_data_collection"

            utci = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": gr,
                    "model": "utci",
                    "air_temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "wind_speed_target": ws,
                },
            )
            assert utci["target"]["target_type"] == "ladybug_data_collection"

            # LB_Honeybee_To_Visualization_Set (model + room).
            hb_vis = await _call(
                client,
                "LB_Honeybee_To_Visualization_Set",
                {"garden_root": gr, "name": "hb_full_vis", "return_visualization_set": False},
            )
            assert hb_vis["target"]["target_type"] == "visualization_set"
            room_vis = await _call(
                client,
                "LB_Honeybee_To_Visualization_Set",
                {"garden_root": gr, "target": room["target"], "name": "hb_room_vis", "return_visualization_set": False},
            )
            assert room_vis["target"]["target_type"] == "visualization_set"

            # LB_Chart_To_Visualization_Set: hourly_plot, monthly_chart, psychrometric_chart, windrose.
            hourly = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "chart_type": "hourly_plot",
                    "data_collection_target": dbt,
                    "return_visualization_set": False,
                },
            )
            assert hourly["target"]["target_type"] == "visualization_set"

            monthly = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "chart_type": "monthly_chart",
                    "series": [{"data_collection_target": dbt, "label": "Dry Bulb"}],
                    "return_visualization_set": False,
                },
            )
            assert monthly["target"]["target_type"] == "visualization_set"

            psych = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "return_visualization_set": False,
                },
            )
            assert psych["target"]["target_type"] == "visualization_set"

            wind = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "chart_type": "windrose",
                    "direction_data_collection_target": wd,
                    "analysis_data_collection_target": ws,
                    "return_visualization_set": False,
                },
            )
            assert wind["target"]["target_type"] == "visualization_set"

            # LB_Sky_To_Visualization_Set: sunpath, skydome, radiation_dome.
            sunpath = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "sky_viz_type": "sunpath",
                    "weather_target": w_target,
                    "return_visualization_set": False,
                },
            )
            assert sunpath["target"]["target_type"] == "visualization_set"

            skymtx = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {"garden_root": gr, "asset_type": "sky_matrix", "identifier": "viz_mtx", "weather_target": w_target, "compute": False},
            )
            skydome = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "sky_viz_type": "skydome",
                    "sky_matrix_target": skymtx["target"],
                    "return_visualization_set": False,
                },
            )
            assert skydome["target"]["target_type"] == "visualization_set"

            raddome = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "sky_viz_type": "radiation_dome",
                    "sky_matrix_target": skymtx["target"],
                    "azimuth_count": 18,
                    "altitude_count": 6,
                    "return_visualization_set": False,
                },
            )
            assert raddome["target"]["target_type"] == "visualization_set"

            # LB_Compose_Visualization_Sets.
            composed = await _call(
                client,
                "LB_Compose_Visualization_Sets",
                {
                    "garden_root": gr,
                    "visualization_set_targets": [hb_vis["target"], sunpath["target"]],
                    "conflict_strategy": "rename",
                    "name": "composed_scene",
                    "return_visualization_set": False,
                },
            )
            assert composed["target"]["target_type"] == "visualization_set"

            # LB_Export_Visualization_Set: html, svg, vtkjs.
            for fmt in ("html", "svg", "vtkjs"):
                exp = await _call(
                    client,
                    "LB_Export_Visualization_Set",
                    {
                        "garden_root": gr,
                        "export_format": fmt,
                        "visualization_set_target": hb_vis["target"],
                        "name": f"viz_export_{fmt}",
                    },
                )
                abs_path = Path(exp["artifact_receipt"]["absolute_path"])
                assert abs_path.is_file()
                assert abs_path.is_relative_to(g_path)
                assert abs_path.stat().st_size > 0

            # LB_Data_Collection_To_File: json and csv.
            for fmt in ("json", "csv"):
                dc_exp = await _call(
                    client,
                    "LB_Data_Collection_To_File",
                    {
                        "garden_root": gr,
                        "data_collection_target": pmv["target"],
                        "file_format": fmt,
                        "name": f"pmv_export_{fmt}",
                    },
                )
                abs_path = Path(dc_exp["persistence_receipt"]["absolute_path"])
                assert abs_path.is_file()
                assert abs_path.is_relative_to(g_path)
                assert abs_path.stat().st_size > 0

    asyncio.run(_run())


def test_fairyfly_consolidation(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Exercise FF_Create_Model, FF_Edit_Model, FF_Validate_Model, FF_To_Visualization_Set + vtkjs export."""
    if not fairyfly_tools_enabled():
        pytest.skip("Fairyfly tools disabled in environment")

    g_path = (tmp_path / "ff_garden").resolve()
    gr = g_path.as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "ff_garden", "root_dir": gr})
            ff_m = await _call(
                client,
                "FF_Create_Model",
                {"garden_root": gr, "identifier": "wall_detail", "units": "Millimeters"},
            )
            assert ff_m["target"]["target_type"] == "fairyfly_model"

            ff_edit = await _call(
                client,
                "FF_Edit_Model",
                {
                    "garden_root": gr,
                    "shapes": [
                        {
                            "name": "Concrete_Layer",
                            "vertices_2d": [[0.0, 0.0], [100.0, 0.0], [100.0, 200.0], [0.0, 200.0]],
                            "material": {"name": "Concrete", "conductivity": 1.5},
                        },
                        {
                            "name": "Insulation_Layer",
                            "vertices_2d": [[100.0, 0.0], [200.0, 0.0], [200.0, 200.0], [100.0, 200.0]],
                            "material": {"name": "Insulation", "conductivity": 0.035},
                        },
                    ],
                    "boundaries": [
                        {
                            "name": "Interior_BC",
                            "line_segments_2d": [[[0.0, 0.0], [0.0, 200.0]]],
                            "temperature": 20.0,
                            "film_coefficient": 8.0,
                            "u_factor_tag": "Interior",
                        },
                        {
                            "name": "Exterior_BC",
                            "line_segments_2d": [[[200.0, 0.0], [200.0, 200.0]]],
                            "temperature": 0.0,
                            "film_coefficient": 25.0,
                        },
                    ],
                },
            )
            assert ff_edit["summary_view"]["added_shape_count"] == 2
            assert ff_edit["summary_view"]["added_boundary_count"] == 2

            ff_val = await _call(client, "FF_Validate_Model", {"garden_root": gr})
            assert ff_val["report"]["status"] == "ok"
            assert "summary_view" in ff_val

            ff_vis = await _call(
                client,
                "FF_To_Visualization_Set",
                {
                    "garden_root": gr,
                    "source_kind": "model",
                    "color_by": "material",
                    "include_boundaries": True,
                    "return_visualization_set": False,
                },
            )
            assert ff_vis["target"]["target_type"] == "visualization_set"

            vtk = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": gr,
                    "export_format": "vtkjs",
                    "visualization_set_target": ff_vis["target"],
                    "name": "ff_wall_vtk",
                },
            )
            vtk_path = Path(vtk["artifact_receipt"]["absolute_path"])
            assert vtk_path.is_file()
            assert vtk_path.is_relative_to(g_path)
            assert vtk_path.stat().st_size > 0

    asyncio.run(_run())
