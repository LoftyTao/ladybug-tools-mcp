"""Tests for architectural and platform upgrades."""

from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
import re
import socket
import threading
from typing import Any
import urllib.request
from unittest import mock

from fastmcp import Client, FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode
import pytest

from garden.energy.libraries import get_energy_library_object, search_energy_library_objects
from ladybug_tools_mcp.code_mode import (
    PreviewMontySandboxProvider,
    create_code_mode_transform,
    resolve_sandbox_limits,
)
from ladybug_tools_mcp.registry import _TOOL_FAMILIES, register_tools
from ladybug_tools_mcp.server import create_mcp
import web_view
from web_view import VENDOR_VTKJS_PATH, fallback_viewer_html, stop_preview_url_fallback


def _parse_tool_result(res: Any) -> dict[str, Any]:
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
    raise AssertionError(f"Unable to parse FastMCP tool result: {res!r}")


def _extract_text(res: Any) -> str:
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
    res = await client.call_tool(name, args)
    return _parse_tool_result(res)


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "Raw Arch Upgrade Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


@pytest.fixture(scope="module")
def raw_mcp() -> FastMCP:
    return _make_raw_mcp()


def test_code_mode_discovery_tools_env_limits_and_thread_offload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify GetTags/ListTools discovery tools, env-configurable limits, and to_thread preview offload."""
    # Default configuration keeps max_tool_calls == 100 and exposes 5 Code Mode tools.
    monkeypatch.delenv("LBT_MCP_MAX_TOOL_CALLS", raising=False)
    monkeypatch.delenv("LBT_MCP_SANDBOX_MAX_DURATION_SECS", raising=False)
    monkeypatch.delenv("LBT_MCP_SANDBOX_MAX_MEMORY", raising=False)

    mcp = create_mcp()
    cms = [tr for tr in mcp.transforms if isinstance(tr, CodeMode)]
    assert len(cms) == 1
    cm = cms[0]
    assert cm.max_tool_calls == 100
    assert isinstance(cm.sandbox_provider, PreviewMontySandboxProvider)
    assert cm.sandbox_provider.limits == {"max_duration_secs": 30.0, "max_memory": 100_000_000}

    async def _run_discovery() -> None:
        async with Client(mcp) as client:
            exposed = await client.list_tools()
            assert {t.name for t in exposed} == {
                "search",
                "get_schema",
                "tags",
                "list_tools",
                "execute",
            }
            tags_brief = _extract_text(await client.call_tool("tags", {"detail": "brief"}))
            assert "garden" in tags_brief
            assert "standards" in tags_brief
            assert "therm" in tags_brief
            tags_full = _extract_text(await client.call_tool("tags", {"detail": "full"}))
            assert "LB_Search_Standards_Library" in tags_full
            listed = _extract_text(await client.call_tool("list_tools", {"detail": "brief"}))
            assert "GD_Export_Model_File" in listed
            assert "GD_Web_View_Start_Mode" in listed

    asyncio.run(_run_discovery())

    # Env configuration overrides.
    monkeypatch.setenv("LBT_MCP_MAX_TOOL_CALLS", "42")
    monkeypatch.setenv("LBT_MCP_SANDBOX_MAX_DURATION_SECS", "12.5")
    monkeypatch.setenv("LBT_MCP_SANDBOX_MAX_MEMORY", "200000000")
    custom_cm = create_code_mode_transform()
    assert custom_cm.max_tool_calls == 42
    assert custom_cm.sandbox_provider.limits == {
        "max_duration_secs": 12.5,
        "max_memory": 200_000_000,
    }
    assert resolve_sandbox_limits() == {"max_duration_secs": 12.5, "max_memory": 200_000_000}

    monkeypatch.setenv("LBT_MCP_MAX_TOOL_CALLS", "0")
    with pytest.raises(ValueError):
        create_code_mode_transform()
    monkeypatch.setenv("LBT_MCP_MAX_TOOL_CALLS", "100")
    monkeypatch.setenv("LBT_MCP_SANDBOX_MAX_DURATION_SECS", "-1")
    with pytest.raises(ValueError):
        resolve_sandbox_limits()

    # Verify preview recording runs on a worker thread via asyncio.to_thread and finishes before run() returns.
    monkeypatch.delenv("LBT_MCP_SANDBOX_MAX_DURATION_SECS", raising=False)
    monkeypatch.delenv("LBT_MCP_SANDBOX_MAX_MEMORY", raising=False)
    gr = (tmp_path / "offload_g").as_posix()

    async def _run_offload() -> None:
        loop_tid = threading.get_ident()
        call_tids: list[int] = []

        def fake_record(*, tool_name: str, arguments: Any, result: Any) -> None:
            call_tids.append(threading.get_ident())

        async def fake_call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            target = {
                "target_type": "honeybee_model",
                "domain": "honeybee",
                "garden_id": "g_offload",
                "model_identifier": "m",
            }
            return {
                "model_target": target,
                "persistence_receipt": {"status": "persisted", "model_target": target},
            }

        provider = PreviewMontySandboxProvider()
        with mock.patch.object(web_view, "maybe_record_code_mode_preview", side_effect=fake_record):
            out = await provider.run(
                f'await call_tool("HB_Create_Model", {{"garden_root": {gr!r}}})\nreturn {{"ok": True}}',
                external_functions={"call_tool": fake_call_tool},
            )
            assert out == {"ok": True}
            assert len(call_tids) == 1
            assert call_tids[0] != loop_tid

    asyncio.run(_run_offload())


def test_standards_library_get_therm_and_structured_filters(raw_mcp: FastMCP) -> None:
    """Verify LB_Search_Standards_Library structured filters, domain='therm', and action='get'."""
    # Direct service checks for structured energy filters.
    cs_filtered = search_energy_library_objects(
        query="",
        object_family="construction_set",
        climate_zone="4",
        vintage="2019",
        construction_type="SteelFramed",
        limit=10,
    )
    assert cs_filtered["identifiers"] == ["2019::ClimateZone4::SteelFramed"]

    pt_filtered = search_energy_library_objects(
        query="",
        object_family="program_type",
        vintage="2019",
        building_type="MediumOffice",
        limit=20,
    )
    assert pt_filtered["identifiers"]
    assert all(
        item.startswith("2019::MediumOffice::") for item in pt_filtered["identifiers"]
    )

    got_cs = get_energy_library_object(
        identifier="2019::ClimateZone4::SteelFramed",
        object_family="construction_set",
    )
    assert got_cs["object_dict"]["type"] == "ConstructionSetAbridged" or "ConstructionSet" in got_cs["object_dict"]["type"]
    assert got_cs["properties"]["wall_set"]["exterior_construction"]["u_value"] > 0

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            # Energy structured search + get across construction, window, program, schedule.
            e_search = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "action": "search",
                    "domain": "energy",
                    "object_family": "construction_set",
                    "climate_zone": "4A",
                    "vintage": "ASHRAE 90.1-2019",
                    "construction_type": "Steel Framed",
                    "limit": 5,
                },
            )
            assert e_search["identifiers"] == ["2019::ClimateZone4::SteelFramed"]

            e_constr = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "action": "get",
                    "domain": "energy",
                    "object_family": "opaque_construction",
                    "identifier": "Generic Exterior Wall",
                },
            )
            assert e_constr["properties"]["u_value"] > 0
            assert len(e_constr["properties"]["layers"]) >= 1
            assert e_constr["object_dict"]["identifier"] == "Generic Exterior Wall"

            e_win = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "action": "get",
                    "domain": "energy",
                    "object_family": "window_construction",
                    "identifier": "Generic Double Pane",
                },
            )
            assert e_win["properties"]["u_value"] > 0
            assert e_win["properties"]["shgc"] > 0
            assert len(e_win["properties"]["layers"]) >= 1

            e_prog = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "action": "get",
                    "domain": "energy",
                    "object_family": "program_type",
                    "identifier": "Generic Office Program",
                },
            )
            assert "schedules" in e_prog["properties"]
            assert e_prog["properties"]["lighting"] is not None

            # Radiance get.
            rad_search = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "radiance", "query": "generic_wall", "object_family": "modifier", "limit": 5},
            )
            rad_id = rad_search["matches"][0]["identifier"]
            rad_get = await _call(
                client,
                "LB_Search_Standards_Library",
                {"action": "get", "domain": "radiance", "object_family": "modifier", "identifier": rad_id},
            )
            assert rad_get["identifier"] == rad_id
            assert rad_get["object_dict"]["identifier"] == rad_id

            # OpenDSS get.
            dss_search = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "opendss", "query": "OH", "catalogs": ["wires"], "limit": 3},
            )
            wire_id = dss_search["matches"][0]["identifier"]
            dss_get = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "action": "get",
                    "domain": "opendss",
                    "catalogs": ["wires"],
                    "identifier": wire_id,
                },
            )
            assert dss_get["identifier"] == wire_id
            assert "ampacity" in dss_get["properties"]

            # THERM search & get across solid_material, cavity_material, condition, gas, pure_gas.
            for fam, query, expected_prop in (
                ("solid_material", "Concrete", "conductivity"),
                ("cavity_material", "NFRC", "cavity_model"),
                ("condition", "Interior", "film_coefficient"),
                ("gas", "Argon", "gas_fractions"),
                ("pure_gas", "Argon", "molecular_weight"),
            ):
                t_search = await _call(
                    client,
                    "LB_Search_Standards_Library",
                    {
                        "action": "search",
                        "domain": "therm",
                        "object_family": fam,
                        "query": query,
                        "limit": 5,
                    },
                )
                assert len(t_search["matches"]) >= 1
                assert t_search["matches"][0]["object_family"] == fam
                t_id = t_search["matches"][0]["identifier"]
                t_get = await _call(
                    client,
                    "LB_Search_Standards_Library",
                    {
                        "action": "get",
                        "domain": "therm",
                        "object_family": fam,
                        "identifier": t_id,
                    },
                )
                assert t_get["domain"] == "therm"
                assert expected_prop in t_get["properties"]
                assert t_get["object_dict"]["display_name"]

    asyncio.run(_run())


def test_multiformat_model_export_and_destructive_annotations(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    """Verify GD_Export_Model_File across all 13 formats + export_options and destructiveHint annotations."""
    gr = (tmp_path / "export_garden").as_posix()

    async def _run() -> None:
        # Check destructiveHint annotations on registered tools.
        tools = {t.name: t for t in await raw_mcp.list_tools()}
        for name in ("GD_Cleanup_Workspace", "GD_Cancel_Run", "GD_Manage_Versions", "FP_Cleanup_All"):
            assert tools[name].annotations is not None
            assert tools[name].annotations.destructive_hint is True
        assert tools["GD_Get"].annotations is not None
        assert tools["GD_Get"].annotations.destructive_hint is not True

        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "export_garden", "root_dir": gr})

            # Create Honeybee model with a room and aperture.
            hb_res = await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "hb_exp"})
            hb_target = hb_res["model_target"]
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "identifier": "Office_1",
                    "x_dim": 5.0,
                    "y_dim": 4.0,
                    "height": 3.0,
                },
            )
            walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "orientation": "S",
                    "face_type": "Wall",
                    "room_identifier": "Office_1",
                },
            )
            wall_target = walls["matches"][0]["target"]
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "generation_mode": "by_ratio",
                    "host_target": wall_target,
                    "ratio": 0.35,
                },
            )

            # Create Dragonfly model with one Building/Story/Room2D.
            df_res = await _call(client, "DF_Model", {"garden_root": gr, "identifier": "df_exp"})
            df_target = df_res["model_target"]
            await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "building_from_footprint",
                    "identifier": "Bldg_1",
                    "footprints": [[[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]],
                    "floor_to_floor_heights": [3.5],
                },
            )

            hb_formats_options: list[tuple[str, dict[str, Any] | None, str]] = [
                ("doe_inp", {"hvac_mapping": "Room"}, "INPUT"),
                ("designbuilder_dsbxml", {"xml_template": "Default"}, "<Site"),
                ("osm", {"use_geometry_names": True}, "OS:Space"),
                ("idf", {"use_geometry_names": True}, "BuildingSurface:Detailed"),
                ("epjson", {"use_geometry_names": True}, "BuildingSurface:Detailed"),
                ("gbxml", {"ip_units": True}, "<gbXML"),
                ("trace_gbxml", {"single_window": True}, "<gbXML"),
                ("sdd", {"use_simple_window_constructions": True}, "<SDDXML"),
                ("rad", {"minimal": True}, "polygon"),
                ("stl", None, "solid "),
            ]
            for fmt, opts, expected_substr in hb_formats_options:
                out = await _call(
                    client,
                    "GD_Export_Model_File",
                    {
                        "garden_root": gr,
                        "export_format": fmt,
                        "model_target": hb_target,
                        "include_body": True,
                        "export_options": opts,
                    },
                )
                assert out["target"]["artifact_type"] == fmt
                assert expected_substr in out["file_body"]
                assert (Path(gr) / out["target"]["path"]).is_file()

            # Folder and binary formats on Honeybee.
            rad_folder_out = await _call(
                client,
                "GD_Export_Model_File",
                {
                    "garden_root": gr,
                    "export_format": "rad_folder",
                    "model_target": hb_target,
                    "include_body": True,
                },
            )
            assert rad_folder_out["summary_view"]["generated_file_count"] >= 1
            assert (Path(gr) / rad_folder_out["target"]["path"]).is_dir()
            assert rad_folder_out["report"]["warnings"]

            hbpkl_out = await _call(
                client,
                "GD_Export_Model_File",
                {
                    "garden_root": gr,
                    "export_format": "hbpkl",
                    "model_target": hb_target,
                    "export_options": {"triangulate_sub_faces": True},
                },
            )
            assert hbpkl_out["summary_view"]["size_bytes"] > 0
            assert (Path(gr) / hbpkl_out["target"]["path"]).is_file()

            # Native GBAS2026 DWG export (binary) + optional JSON report + overwrite guard.
            gbas_out = await _call(
                client,
                "GD_Export_Model_File",
                {
                    "garden_root": gr,
                    "export_format": "gbas_dwg",
                    "model_target": hb_target,
                    "include_body": True,
                },
            )
            assert gbas_out["target"]["artifact_type"] == "gbas_dwg"
            assert "file_body" not in gbas_out
            assert gbas_out["report"]["warnings"]
            assert gbas_out["summary_view"]["size_bytes"] > 0
            assert gbas_out["summary_view"]["self_check_passed"] is True
            assert gbas_out["summary_view"]["counts"]["rooms"] == 1
            assert gbas_out["summary_view"]["counts"]["native_openings"] >= 1
            gbas_dwg_path = Path(gr) / gbas_out["target"]["path"]
            assert gbas_dwg_path.is_file()
            assert gbas_dwg_path.read_bytes().startswith(b"AC1015")

            gbas_reported_out = await _call(
                client,
                "GD_Export_Model_File",
                {
                    "garden_root": gr,
                    "export_format": "gbas_dwg",
                    "model_target": hb_target,
                    "name": "hb_gbas_reported",
                    "export_options": {"write_report": True},
                },
            )
            gbas_report_rel = gbas_reported_out["summary_view"]["report_path"]
            gbas_report_file = Path(gr) / gbas_report_rel
            assert gbas_report_file.is_file()
            gbas_report_payload = json.loads(gbas_report_file.read_text(encoding="utf-8"))
            assert gbas_report_payload["status"] == "translated"
            assert gbas_report_payload["self_check"]["passed"] is True

            with pytest.raises(Exception):
                await _call(
                    client,
                    "GD_Export_Model_File",
                    {
                        "garden_root": gr,
                        "export_format": "gbas_dwg",
                        "model_target": hb_target,
                        "name": "hb_gbas_reported",
                        "export_options": {"overwrite": False},
                    },
                )

            # Dragonfly multi-format export coverage.
            for fmt in ("doe_inp", "gbas_dwg", "osm", "idf", "gbxml", "trace_gbxml", "sdd", "rad", "stl"):
                df_out = await _call(
                    client,
                    "GD_Export_Model_File",
                    {
                        "garden_root": gr,
                        "export_format": fmt,
                        "model_target": df_target,
                        "name": f"df_{fmt}",
                    },
                )
                assert df_out["summary_view"]["model_domain"] == "dragonfly"
                df_artifact_path = Path(gr) / df_out["target"]["path"]
                assert df_artifact_path.is_file()
                if fmt == "gbas_dwg":
                    assert df_artifact_path.read_bytes().startswith(b"AC1015")

    asyncio.run(_run())


def test_offline_web_view_workbench_and_port_support(tmp_path: Path, raw_mcp: FastMCP) -> None:
    """Verify bundled /vendor/vtk.js, zero CDN links, workbench UI, HTML/SVG tab, and port conflict handling."""
    assert VENDOR_VTKJS_PATH.is_file()
    assert VENDOR_VTKJS_PATH.stat().st_size > 100_000

    html = fallback_viewer_html()
    assert "unpkg.com" not in html
    assert 'src="/vendor/vtk.js"' in html
    for expected_ui in (
        'id="step-slider"',
        'id="layers-panel"',
        'id="legend-overlay"',
        'id="tab-docs"',
        'id="doc-frame"',
        'id="axon"',
        'id="top"',
        'id="front"',
        'id="back"',
        'id="left"',
        'id="right"',
        'id="fit"',
    ):
        assert expected_ui in html

    g1 = (tmp_path / "wv_g1").as_posix()
    g2 = (tmp_path / "wv_g2").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "wv_g1", "root_dir": g1})
            await _call(client, "GD_Create", {"name": "wv_g2", "root_dir": g2})
            await _call(client, "HB_Create_Model", {"garden_root": g1, "identifier": "wv_hb"})
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g1,
                    "object_type": "room",
                    "identifier": "WV_Room",
                    "x_dim": 4.0,
                    "y_dim": 4.0,
                    "height": 3.0,
                },
            )
            vis = await _call(
                client,
                "LB_Honeybee_To_Visualization_Set",
                {
                    "garden_root": g1,
                    "color_by": "type",
                    "name": "wv_vis",
                    "return_visualization_set": False,
                },
            )
            vtkjs_exp = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": g1,
                    "export_format": "vtkjs",
                    "visualization_set_target": vis["visualization_set_target"],
                    "name": "wv_scene",
                },
            )
            svg_exp = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": g1,
                    "export_format": "svg",
                    "visualization_set_target": vis["visualization_set_target"],
                    "name": "wv_plan",
                },
            )

            # Find a free loopback port, then start g1 on that explicit port.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                explicit_port = probe.getsockname()[1]

            try:
                started = await _call(
                    client,
                    "GD_Web_View_Start_Mode",
                    {"garden_root": g1, "name": "Offline Workbench", "port": explicit_port},
                )
                assert started["viewer"]["port"] == explicit_port
                assert started["viewer"]["url"] == f"http://127.0.0.1:{explicit_port}/"
                assert started["viewer"]["vendor_url"] == "/vendor/vtk.js"

                web_view.record_preview_file_step(
                    garden_root=g1,
                    preview_kind="analysis_overlay",
                    label="Step 1 scene",
                    vtkjs_file_path=vtkjs_exp["artifact_receipt"]["absolute_path"],
                    source_tool="LB_Export_Visualization_Set",
                )

                base_url = started["viewer"]["url"].rstrip("/")
                with urllib.request.urlopen(f"{base_url}/", timeout=5) as resp:
                    assert resp.status == 200
                    body = resp.read().decode("utf-8")
                    assert "unpkg.com" not in body
                    assert "/vendor/vtk.js" in body

                with urllib.request.urlopen(f"{base_url}/vendor/vtk.js", timeout=5) as resp:
                    assert resp.status == 200
                    js_bytes = resp.read()
                    assert len(js_bytes) == VENDOR_VTKJS_PATH.stat().st_size

                with urllib.request.urlopen(f"{base_url}/api/state", timeout=5) as resp:
                    state_json = json.loads(resp.read().decode("utf-8"))
                    assert len(state_json["steps"]) == 1
                    assert state_json["steps"][0]["label"] == "Step 1 scene"
                    assert len(state_json["html_svg_artifacts"]) == 1
                    assert state_json["html_svg_artifacts"][0]["path"] == svg_exp["artifact_path"]

                with urllib.request.urlopen(
                    f"{base_url}/api/artifact?path={vtkjs_exp['artifact_path']}",
                    timeout=5,
                ) as resp:
                    art_json = json.loads(resp.read().decode("utf-8"))
                    assert art_json["scene_metadata"]["scene_items"]

                with urllib.request.urlopen(
                    f"{base_url}/api/document?path={svg_exp['artifact_path']}",
                    timeout=5,
                ) as resp:
                    assert resp.status == 200
                    assert "image/svg+xml" in resp.headers.get("Content-Type", "")
                    assert "<svg" in resp.read().decode("utf-8")

                # Explicit port conflict on g2 must raise a clear error.
                with pytest.raises(Exception, match="already in use|port"):
                    await _call(
                        client,
                        "GD_Web_View_Start_Mode",
                        {"garden_root": g2, "port": explicit_port},
                    )

                # Ephemeral port (port=None) succeeds on g2.
                g2_started = await _call(
                    client,
                    "GD_Web_View_Start_Mode",
                    {"garden_root": g2},
                )
                assert g2_started["viewer"]["port"] != explicit_port
                assert g2_started["viewer"]["port"] > 0
            finally:
                stop_preview_url_fallback(garden_root=g1)
                stop_preview_url_fallback(garden_root=g2)

    asyncio.run(_run())


def test_docs_manifest_and_stale_token_reconciliation() -> None:
    """Verify docs drift reconciliation, MANIFEST.in bundling, and zero unregistered tool tokens."""
    root = Path(__file__).resolve().parents[1]
    readme_en = (root / "README.md").read_text(encoding="utf-8")
    readme_zh = (root / "README.zh-CN.md").read_text(encoding="utf-8")
    wv_readme = (root / "src" / "web_view" / "README.md").read_text(encoding="utf-8")
    manifest_in = (root / "MANIFEST.in").read_text(encoding="utf-8")

    for doc in (readme_en, readme_zh, wv_readme):
        assert "LB_Set_To_VTKJS" not in doc
        assert "LB_Export_Visualization_Set" in doc
        assert "/vendor/vtk.js" in doc
        assert "port" in doc

    assert "3.11.0" not in readme_en
    assert "3.11.0" not in readme_zh
    assert "3.10.0" in readme_en
    assert "3.10.0" in readme_zh
    assert "src/web_view/vendor" in manifest_in

    # Verify all owned src/**/*.py files remain free of unregistered MCP tool tokens.
    registered_names: set[str] = set()
    for family in _TOOL_FAMILIES:
        mod_mcp = FastMCP(f"mod-{family}", on_duplicate="error", strict_input_validation=True)
        importlib.import_module(f"ladybug_tools_mcp.tools.{family}").register(mod_mcp)
        registered_names.update(t.name for t in asyncio.run(mod_mcp.list_tools()))

    owned_py_files = [
        root / "src" / "ladybug_tools_mcp" / "code_mode.py",
        root / "src" / "ladybug_tools_mcp" / "tools" / "libraries.py",
        root / "src" / "garden" / "energy" / "libraries.py",
        root / "src" / "ladybug_tools_mcp" / "tools" / "garden.py",
        root / "src" / "ladybug_tools_mcp" / "tools" / "web_view.py",
        root / "src" / "ladybug_tools_mcp" / "tools" / "flowerpot.py",
        root / "src" / "garden" / "model_export.py",
        root / "src" / "web_view" / "__init__.py",
        root / "src" / "web_view" / "viewer.py",
    ]
    token_re = re.compile(r"\b(?:GD|HB|DF|EP|RAD|LB|FF|FP|IB)_[A-Z][A-Za-z0-9_]*\b")
    stale_hits: list[str] = []
    for py_file in owned_py_files:
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for match in token_re.finditer(line):
                tok = match.group(0)
                if tok in registered_names:
                    continue
                if tok.startswith("IB_") and "_" not in tok[3:]:
                    continue
                stale_hits.append(f"{py_file.relative_to(root)}:{lineno}: {tok}")
    assert stale_hits == [], f"Stale tool tokens found: {stale_hits}"
