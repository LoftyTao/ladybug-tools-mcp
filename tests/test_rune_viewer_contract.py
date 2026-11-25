"""Contract tests for the Rune 3D viewer protocol, launcher, MCP tools, and Code Mode hooks."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import warnings
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from fastmcp import Client, FastMCP
from PIL import Image

import web_view
import web_view.launcher as wv_launcher
import web_view.protocol as wv_protocol
from garden.manifest import GardenManifest
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.server import create_mcp


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


async def _call(client: Client, name: str, args: dict[str, Any]) -> dict[str, Any]:
    res = await client.call_tool(name, args)
    assert not getattr(res, "is_error", False), f"{name} returned error: {res!r}"
    return _parse_tool_result(res)


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "Raw Rune Viewer Contract Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


def test_rune_viewer_binary_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify binary discovery order: env override, release/debug target, and PATH."""
    exe_name = "lbt-rune-viewer.exe" if os.name == "nt" else "lbt-rune-viewer"
    fake_repo = tmp_path / "repo"
    release_bin = fake_repo / "rune_viewer" / "target" / "release" / exe_name
    debug_bin = fake_repo / "rune_viewer" / "target" / "debug" / exe_name
    env_bin = tmp_path / "custom" / exe_name
    path_dir = tmp_path / "bin"
    path_bin = path_dir / exe_name

    for p in (release_bin, debug_bin, env_bin, path_bin):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"stub")

    monkeypatch.setattr(wv_launcher, "_REPO_ROOT", fake_repo)
    monkeypatch.setenv("LBT_RUNE_VIEWER_BIN", str(env_bin))
    assert wv_launcher.discover_rune_viewer_binary() == env_bin.resolve()

    monkeypatch.delenv("LBT_RUNE_VIEWER_BIN", raising=False)
    assert wv_launcher.discover_rune_viewer_binary() == release_bin.resolve()

    release_bin.unlink()
    assert wv_launcher.discover_rune_viewer_binary() == debug_bin.resolve()

    debug_bin.unlink()
    monkeypatch.setenv("PATH", str(path_dir))
    assert wv_launcher.discover_rune_viewer_binary() == path_bin.resolve()


def test_rune_viewer_tools_present_context_and_shades_roundtrip(tmp_path: Path) -> None:
    """Verify all 5 web_view tools, monotonic present.json, annotation resolution, and HB_Create_Shades handoff."""
    raw_mcp = _make_raw_mcp()
    gr = (tmp_path / "rune_garden").as_posix()
    g_path = Path(gr).resolve()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"name": "rune_garden", "root_dir": gr})
            gid = created["target"]["garden_id"]

            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "office_hb"})
            room_res = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "identifier": "Room_South",
                    "x_dim": 6.0,
                    "y_dim": 5.0,
                    "height": 3.2,
                },
            )
            assert room_res["target"]["object_type"] == "room"

            south_walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": gr,
                    "object_type": "face",
                    "orientation": "S",
                    "face_type": "Wall",
                },
            )
            assert len(south_walls["matches"]) == 1
            south_face_target = south_walls["matches"][0]["target"]

            aps = await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "host_target": south_face_target,
                    "ratio": 0.4,
                },
            )
            ap_target = aps["targets"][0]

            # Start Rune backend mode: must auto-populate present.json from base_honeybee_model.
            started = await _call(
                client,
                "GD_Web_View_Start_Mode",
                {
                    "garden_root": gr,
                    "name": "Rune Session",
                    "viewer_backend": "rune",
                    "open_window": False,
                },
            )
            assert started["viewer"]["backend"] == "rune"
            assert started["viewer"]["web_fallback_active"] is False
            assert started["present"]["revision"] == 1
            assert started["present"]["view_type"] == "model"
            assert started["present"]["camera"] == "fit"
            assert started["present"]["model_path"] == "models/honeybee/office_hb.hbjson"

            present_path = g_path / "tmp" / "web_view" / "present.json"
            interaction_path = g_path / "tmp" / "web_view" / "interaction_state.json"
            assert present_path.is_file()
            assert interaction_path.is_file()

            # Director tool: highlight + ghost_context + camera + section + callouts.
            pres_2 = await _call(
                client,
                "GD_Web_View_Present",
                {
                    "garden_root": gr,
                    "view_type": "highlight",
                    "color_by": "wwr",
                    "highlight_targets": [south_face_target],
                    "isolation_mode": "ghost_context",
                    "camera": "fit_highlights",
                    "section": {"enabled": True, "axis": "z", "value": 1.6, "invert": False},
                    "callouts": [{"id": "c1", "text": "South Facade", "target": south_face_target}],
                    "title": "South Glazing Check",
                    "note": "Check shading depth on south wall.",
                },
            )
            assert pres_2["revision"] == 2
            assert pres_2["present"]["color_by"] == "wwr"
            assert pres_2["present"]["isolation_mode"] == "ghost_context"
            assert pres_2["present"]["camera"] == "fit_highlights"
            assert pres_2["present"]["section"]["enabled"] is True
            assert pres_2["present"]["section"]["axis"] == "z"
            assert pres_2["present"]["highlight_targets"][0]["object_identifier"] == south_face_target["object_identifier"]

            # Partial update without camera defaults camera to 'keep'.
            pres_3 = await _call(
                client,
                "GD_Web_View_Present",
                {
                    "garden_root": gr,
                    "view_type": "validation",
                    "validation_issues": [
                        {"code": "TEST01", "message": "Sample issue", "element_id": south_face_target["object_identifier"]}
                    ],
                    "camera": {"position": [10.0, -10.0, 8.0], "target": [3.0, 2.5, 1.5], "orthographic": False},
                },
            )
            assert pres_3["revision"] == 3
            assert pres_3["present"]["view_type"] == "validation"
            assert len(pres_3["present"]["validation_issues"]) == 1
            assert pres_3["present"]["camera"]["position"] == [10.0, -10.0, 8.0]

            pres_4 = await _call(
                client,
                "GD_Web_View_Present",
                {"garden_root": gr, "color_by": "story"},
            )
            assert pres_4["revision"] == 4
            assert pres_4["present"]["camera"] == "keep"
            assert pres_4["present"]["color_by"] == "story"

            # Simulate user selecting the south aperture and dropping two annotations in interaction_state.json.
            wv_protocol.write_interaction_state(
                g_path,
                {
                    "schema_version": "1",
                    "garden_id": gid,
                    "selected_targets": [ap_target],
                    "annotations": [
                        {
                            "id": "ann_1",
                            "status": "open",
                            "target": ap_target,
                            "world_point": [3.0, 0.0, 1.6],
                            "comment": "Add 0.5m overhang louvers here",
                            "camera_bookmark": "south",
                        },
                        {
                            "id": "ann_2",
                            "status": "open",
                            "target": south_face_target,
                            "world_point": [2.0, 0.0, 1.2],
                            "comment": "Verify sill height",
                        },
                    ],
                    "viewport": {
                        "model_path": "models/honeybee/office_hb.hbjson",
                        "color_by": "story",
                        "camera": {"position": [3.0, -8.0, 2.0], "target": [3.0, 0.0, 1.6]},
                        "section": None,
                    },
                    "pending_intents": [{"id": "intent_1", "kind": "add_shades", "targets": [ap_target]}],
                    "viewer_pid": None,
                },
            )

            ctx = await _call(client, "GD_Web_View_Get_Context", {"garden_root": gr})
            assert ctx["selected_targets"] == [ap_target]
            assert ctx["open_annotation_count"] == 2
            assert [a["id"] for a in ctx["annotations"]] == ["ann_1", "ann_2"]
            assert ctx["viewport"]["color_by"] == "story"
            assert ctx["pending_intents"][0]["kind"] == "add_shades"

            # Feed selected_targets straight into HB_Create_Shades!
            shades_res = await _call(
                client,
                "HB_Create_Shades",
                {
                    "garden_root": gr,
                    "mode": "parameters",
                    "host_targets": ctx["selected_targets"],
                    "generation_mode": "louver_by_count",
                    "parameters": {"depth": 0.4, "louver_count": 2},
                },
            )
            assert shades_res["summary_view"]["created_count"] == 2

            # Atomically resolve ann_1 and verify filtering.
            ctx_after = await _call(
                client,
                "GD_Web_View_Get_Context",
                {
                    "garden_root": gr,
                    "only_open_annotations": True,
                    "resolve_annotations": [
                        {"id": "ann_1", "resolution_note": "Created 2 louver shades (0.4m depth)."}
                    ],
                },
            )
            assert ctx_after["resolved_ids"] == ["ann_1"]
            assert ctx_after["open_annotation_count"] == 1
            assert ctx_after["resolved_annotation_count"] == 1
            assert [a["id"] for a in ctx_after["annotations"]] == ["ann_2"]

            ctx_all = await _call(
                client,
                "GD_Web_View_Get_Context",
                {"garden_root": gr, "only_open_annotations": False},
            )
            assert len(ctx_all["annotations"]) == 2
            ann_1 = next(a for a in ctx_all["annotations"] if a["id"] == "ann_1")
            assert ann_1["status"] == "resolved"
            assert ann_1["resolution_note"] == "Created 2 louver shades (0.4m depth)."

            # Tier 3 capture fallback (VTK / matplotlib) when no Rune binary is present.
            with mock.patch.object(wv_launcher, "discover_rune_viewer_binary", return_value=None):
                with mock.patch("web_view.discover_rune_viewer_binary", return_value=None):
                    cap_vtk = await _call(
                        client,
                        "GD_Web_View_Capture",
                        {"garden_root": gr, "view": "axon", "width": 320, "height": 240},
                    )
            cap_png = Path(cap_vtk["absolute_path"])
            assert cap_png.is_file()
            assert cap_png.is_relative_to(g_path / "tmp" / "web_view" / "captures")
            assert cap_vtk["renderer"] in {"vtk_offscreen", "matplotlib_fallback"}
            assert cap_vtk["width"] > 0 and cap_vtk["height"] > 0

            stopped = await _call(client, "GD_Web_View_Stop_Mode", {"garden_root": gr})
            assert stopped["session"]["active"] is False

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        asyncio.run(_run())

    pydantic_warnings = [
        f"{w.category.__name__}: {w.message}"
        for w in caught
        if "Pydantic" in w.category.__name__ or "PydanticSerializationUnexpectedValue" in str(w.message)
    ]
    assert pydantic_warnings == []


def test_capture_live_handshake_and_headless_snap(tmp_path: Path) -> None:
    """Verify GD_Web_View_Capture Tier 1 live handshake and Tier 2 headless --snap."""
    raw_mcp = _make_raw_mcp()
    gr = (tmp_path / "cap_garden").as_posix()
    g_path = Path(gr).resolve()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "cap_garden", "root_dir": gr})
            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "cap_hb"})
            await _call(
                client,
                "HB_Create_Objects",
                {"garden_root": gr, "object_type": "room", "identifier": "R1", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0},
            )
            await _call(
                client,
                "GD_Web_View_Start_Mode",
                {"garden_root": gr, "viewer_backend": "rune"},
            )

            # Tier 1: simulated live viewer fulfilling capture_request.json.
            req_file = g_path / "tmp" / "web_view" / "capture_request.json"
            stop_flag = threading.Event()

            def _responder() -> None:
                while not stop_flag.is_set():
                    if req_file.is_file():
                        try:
                            req = json.loads(req_file.read_text(encoding="utf-8"))
                            png_rel = req["output_png_path"]
                            rec_rel = req["receipt_path"]
                            png_abs = g_path / png_rel
                            rec_abs = g_path / rec_rel
                            png_abs.parent.mkdir(parents=True, exist_ok=True)
                            Image.new("RGB", (640, 480), color=(40, 120, 180)).save(png_abs, format="PNG")
                            rec_abs.write_text(
                                json.dumps(
                                    {
                                        "schema_version": "1",
                                        "request_id": req["request_id"],
                                        "status": "ok",
                                        "image_path": png_rel,
                                        "width": 640,
                                        "height": 480,
                                    }
                                ),
                                encoding="utf-8",
                            )
                            return
                        except Exception:
                            pass
                    time.sleep(0.02)

            t = threading.Thread(target=_responder, daemon=True)
            t.start()
            try:
                with mock.patch("web_view.is_rune_viewer_running", return_value=True):
                    cap_live = await _call(
                        client,
                        "GD_Web_View_Capture",
                        {"garden_root": gr, "view": "axon", "width": 640, "height": 480, "timeout_secs": 3.0},
                    )
            finally:
                stop_flag.set()
                t.join(timeout=2.0)

            assert cap_live["renderer"] == "rune_live"
            assert cap_live["width"] == 640
            assert cap_live["height"] == 480
            assert Path(cap_live["absolute_path"]).is_file()
            assert not req_file.is_file()

            # Tier 2: simulated headless --snap when no live viewer is running.
            fake_exe = tmp_path / ("lbt-rune-viewer.exe" if os.name == "nt" else "lbt-rune-viewer")
            fake_exe.write_bytes(b"fake")

            def _fake_snap(*, garden_root: Any, output_png_path: Any, view: Any = None, width: int = 1280, height: int = 720, **kwargs: Any) -> dict[str, Any]:
                assert view == "top"
                assert width == 800
                assert height == 600
                out = Path(output_png_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (width, height), color=(200, 200, 200)).save(out, format="PNG")
                return {"status": "ok", "png_path": str(out), "width": width, "height": height}

            with (
                mock.patch("web_view.is_rune_viewer_running", return_value=False),
                mock.patch("web_view.discover_rune_viewer_binary", return_value=fake_exe),
                mock.patch("web_view.run_headless_snap", side_effect=_fake_snap),
            ):
                cap_snap = await _call(
                    client,
                    "GD_Web_View_Capture",
                    {"garden_root": gr, "view": "top", "width": 800, "height": 600},
                )
            assert cap_snap["renderer"] == "rune_headless"
            assert cap_snap["width"] == 800
            assert cap_snap["height"] == 600
            assert Path(cap_snap["absolute_path"]).is_file()

            # Verify launcher.run_headless_snap builds --view/--width/--height flags cleanly.
            captured_cmds: list[list[str]] = []

            def _mock_subproc(cmd: list[str], **kwargs: Any) -> Any:
                captured_cmds.append(list(cmd))
                out_idx = cmd.index("--snap") + 1
                Image.new("RGB", (640, 360), color=(10, 20, 30)).save(Path(cmd[out_idx]), format="PNG")
                return mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch("subprocess.run", side_effect=_mock_subproc):
                snap_cmd_res = wv_launcher.run_headless_snap(
                    garden_root=g_path,
                    output_png_path=g_path / "tmp" / "web_view" / "captures" / "cli_check.png",
                    view="axon",
                    width=640,
                    height=360,
                    binary_path=fake_exe,
                )
            assert snap_cmd_res["status"] == "ok"
            assert "--garden" in captured_cmds[0]
            assert "--view" in captured_cmds[0] and captured_cmds[0][captured_cmds[0].index("--view") + 1] == "axon"
            assert "--width" in captured_cmds[0] and captured_cmds[0][captured_cmds[0].index("--width") + 1] == "640"
            assert "--height" in captured_cmds[0] and captured_cmds[0][captured_cmds[0].index("--height") + 1] == "360"

            await _call(client, "GD_Web_View_Stop_Mode", {"garden_root": gr})

    asyncio.run(_run())


def test_code_mode_rune_present_and_2d_chart_skip(tmp_path: Path) -> None:
    """Verify Code Mode updates present.json with changed_targets without vtkjs in Rune mode, and skips 2D charts."""
    mcp = create_mcp()
    gr = (tmp_path / "cm_rune_garden").as_posix()
    g_path = Path(gr).resolve()
    weather_src = Path(__file__).resolve().parents[1] / "resources" / "ladybug" / "tests" / "assets"

    # Stage an EPW file for LB_Chart_To_Visualization_Set tests.
    epw_dir = tmp_path / "weather"
    epw_dir.mkdir(parents=True, exist_ok=True)
    for subdir, suffix in (("epw", ".epw"), ("ddy", ".ddy"), ("stat", ".stat")):
        src = weather_src / subdir / f"chicago{suffix}"
        if src.is_file():
            (epw_dir / f"chicago{suffix}").write_bytes(src.read_bytes())

    async def _run() -> None:
        async with Client(mcp) as client:
            # 1. Rune mode: Honeybee edits update present.json with changed_targets and do NOT export vtkjs.
            await client.call_tool(
                "execute",
                {
                    "code": (
                        f'g = await call_tool("GD_Create", {{"name": "cm_rune_garden", "root_dir": {gr!r}}})\n'
                        f'return await call_tool("GD_Web_View_Start_Mode", {{"garden_root": g["garden_root"], "viewer_backend": "rune"}})'
                    )
                },
            )
            export_calls: list[str] = []
            orig_export = web_view._export_session_vtkjs

            def counting_export(*args: Any, **kwargs: Any) -> str:
                export_calls.append(str(kwargs.get("name") or ""))
                return orig_export(*args, **kwargs)

            with mock.patch.object(web_view, "_export_session_vtkjs", side_effect=counting_export):
                await client.call_tool(
                    "execute",
                    {
                        "code": (
                            f'gr = {gr!r}\n'
                            f'await call_tool("HB_Create_Model", {{"garden_root": gr, "identifier": "rune_cm"}})\n'
                            f'r1 = await call_tool("HB_Create_Objects", {{"garden_root": gr, "object_type": "room", "identifier": "Room_A", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0}})\n'
                            f'r2 = await call_tool("HB_Create_Objects", {{"garden_root": gr, "object_type": "room", "identifier": "Room_B", "x_dim": 4.0, "y_dim": 4.0, "height": 3.0, "origin": [4.0, 0.0, 0.0]}})\n'
                            f'return {{"r1": r1["target"], "r2": r2["target"]}}'
                        )
                    },
                )
            assert export_calls == []
            present = wv_protocol.read_present(g_path)
            assert present is not None
            assert present["revision"] >= 2
            assert present["model_path"] == "models/honeybee/rune_cm.hbjson"
            changed_ids = {t["object_identifier"] for t in present["highlight_targets"]}
            assert changed_ids == {"Room_A", "Room_B"}

            # 2. Switch to web mode: 2D chart VisualizationSets MUST NOT trigger _export_session_vtkjs,
            #    and must NOT clobber Honeybee changes in the same Code Mode execute block.
            await client.call_tool(
                "execute",
                {
                    "code": f'return await call_tool("GD_Web_View_Start_Mode", {{"garden_root": {gr!r}, "viewer_backend": "web"}})'
                },
            )
            try:
                chart_export_calls: list[str] = []

                def counting_chart_export(*args: Any, **kwargs: Any) -> str:
                    chart_export_calls.append(str(kwargs.get("name") or ""))
                    return orig_export(*args, **kwargs)

                with mock.patch.object(web_view, "_export_session_vtkjs", side_effect=counting_chart_export):
                    await client.call_tool(
                        "execute",
                        {
                            "code": (
                                f'gr = {gr!r}\n'
                                f'w = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "import", "source_path": {str(epw_dir)!r}}})\n'
                                f'dbt = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "read_data", "weather_target": w["target"], "data_type": "dry_bulb_temperature"}})\n'
                                f'rh = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "read_data", "weather_target": w["target"], "data_type": "relative_humidity"}})\n'
                                f'ws = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "read_data", "weather_target": w["target"], "data_type": "wind_speed"}})\n'
                                f'wd = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "read_data", "weather_target": w["target"], "data_type": "wind_direction"}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "hourly_plot", "data_collection_target": dbt["target"], "return_visualization_set": False}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "monthly_chart", "series": [{{"data_collection_target": dbt["target"], "label": "DBT"}}], "return_visualization_set": False}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "psychrometric_chart", "temperature_target": dbt["target"], "relative_humidity_target": rh["target"], "return_visualization_set": False}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "adaptive_chart", "outdoor_temperature_target": dbt["target"], "operative_temperature_target": dbt["target"], "return_visualization_set": False}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "windrose", "direction_data_collection_target": wd["target"], "analysis_data_collection_target": ws["target"], "return_visualization_set": False}})\n'
                                f'return {{"ok": True}}'
                            )
                        },
                    )
                assert chart_export_calls == []

                # Now run Honeybee edit followed by 2D chart in the SAME Code Mode execute block:
                # Honeybee edit must still flush while the 2D chart is ignored.
                with mock.patch.object(web_view, "_export_session_vtkjs", side_effect=counting_chart_export):
                    await client.call_tool(
                        "execute",
                        {
                            "code": (
                                f'gr = {gr!r}\n'
                                f'await call_tool("HB_Create_Objects", {{"garden_root": gr, "object_type": "room", "identifier": "Room_C", "x_dim": 3.0, "y_dim": 3.0, "height": 3.0, "origin": [8.0, 0.0, 0.0]}})\n'
                                f'w = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "search"}})\n'
                                f'dc_list = await call_tool("LB_Manage_Weather", {{"garden_root": gr, "action": "read_data", "weather_target": w["matches"][0]["target"], "data_type": "dry_bulb_temperature"}})\n'
                                f'await call_tool("LB_Chart_To_Visualization_Set", {{"garden_root": gr, "chart_type": "hourly_plot", "data_collection_target": dc_list["target"], "return_visualization_set": False}})\n'
                                f'return {{"ok": True}}'
                            )
                        },
                    )
                assert len(chart_export_calls) == 1
                present_after = wv_protocol.read_present(g_path)
                assert present_after is not None
                assert any(t["object_identifier"] == "Room_C" for t in present_after["highlight_targets"])
            finally:
                await client.call_tool(
                    "execute",
                    {"code": f'return await call_tool("GD_Web_View_Stop_Mode", {{"garden_root": {gr!r}}})'},
                )
                web_view.stop_preview_url_fallback(garden_root=gr)

    asyncio.run(_run())


def test_open_window_lifecycle_and_preserve_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify open_window process spawn/stop lifecycle and preserve_history behavior."""
    raw_mcp = _make_raw_mcp()
    gr = (tmp_path / "proc_garden").as_posix()
    g_path = Path(gr).resolve()

    # Create a tiny Python-based fake executable script via sys.executable wrapper or mock Popen.
    import sys

    fake_bin = tmp_path / ("lbt-rune-viewer.cmd" if os.name == "nt" else "lbt-rune-viewer")
    if os.name == "nt":
        fake_bin.write_text(f'@"{sys.executable}" -c "import time; time.sleep(30)"\n', encoding="utf-8")
    else:
        fake_bin.write_text(f'#!/bin/sh\nexec "{sys.executable}" -c "import time; time.sleep(30)"\n', encoding="utf-8")
        fake_bin.chmod(0o755)
    monkeypatch.setenv("LBT_RUNE_VIEWER_BIN", str(fake_bin))

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "proc_garden", "root_dir": gr})
            started = await _call(
                client,
                "GD_Web_View_Start_Mode",
                {"garden_root": gr, "viewer_backend": "rune", "open_window": True},
            )
            pid = started["viewer"]["pid"]
            assert isinstance(pid, int) and pid > 0
            assert started["viewer"]["web_fallback_active"] is False
            assert wv_launcher.is_rune_viewer_running(g_path) is True

            # Record a step and verify preserve_history=True keeps it, preserve_history=False resets it.
            await _call(client, "HB_Create_Model", {"garden_root": gr, "identifier": "hist_hb"})
            pres = await _call(client, "GD_Web_View_Present", {"garden_root": gr, "color_by": "zone"})
            rev_before = pres["revision"]

            restarted_keep = await _call(
                client,
                "GD_Web_View_Start_Mode",
                {"garden_root": gr, "viewer_backend": "rune", "open_window": True, "preserve_history": True},
            )
            assert restarted_keep["viewer"]["rune_process"]["status"] == "already_running"
            assert restarted_keep["present"]["revision"] == rev_before

            restarted_reset = await _call(
                client,
                "GD_Web_View_Start_Mode",
                {"garden_root": gr, "viewer_backend": "rune", "open_window": False, "preserve_history": False},
            )
            assert restarted_reset["present"]["revision"] == rev_before + 1
            assert restarted_reset["present"]["color_by"] == "type"

            stopped = await _call(client, "GD_Web_View_Stop_Mode", {"garden_root": gr})
            assert stopped["rune_viewer"]["status"] in {"stopped", "already_exited"}
            assert wv_launcher.is_rune_viewer_running(g_path) is False

    asyncio.run(_run())

