"""Comprehensive tests for Dragonfly & Fairyfly bug fixes and P1 parity upgrades."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import zipfile

from fastmcp import FastMCP
import pytest

from garden.store import create_garden
from ladybug_tools_mcp.registry import register_tools


# ---------------------------------------------------------------------------
# Shared test helpers & fixtures
# ---------------------------------------------------------------------------


def _call_tool(mcp: FastMCP, tool_name: str, **kwargs):
    tool = asyncio.run(mcp.get_tool(tool_name))
    assert tool is not None, f"Expected registered MCP tool {tool_name}"
    return tool.fn(**kwargs)


@pytest.fixture()
def mcp_server() -> FastMCP:
    mcp = FastMCP("test-df-ff")
    register_tools(mcp)
    return mcp


@pytest.fixture()
def garden_root(tmp_path: Path) -> str:
    created = create_garden(name="upgrade-test-garden", root_dir=str(tmp_path / "garden"))
    return str(created["garden_root"])


def _write_minimal_epw(epw_path: Path) -> Path:
    """Create a valid minimal 8760-hour EPW file using Ladybug."""
    from ladybug.epw import EPW
    from ladybug.location import Location

    epw = EPW.from_missing_values()
    epw.location = Location(
        city="Boston", state="MA", country="USA", latitude=42.36, longitude=-71.06, time_zone=-5, elevation=6
    )
    epw.dry_bulb_temperature.values = [10.0 + (i % 24) * 0.2 for i in range(8760)]
    epw.dew_point_temperature.values = [5.0] * 8760
    epw.relative_humidity.values = [60.0] * 8760
    epw.atmospheric_station_pressure.values = [101325.0] * 8760
    epw.save(str(epw_path))
    return epw_path


def _build_basic_building_model(mcp: FastMCP, garden_root: str, *, identifier: str = "df_base"):
    m = _call_tool(mcp, "DF_Model", garden_root=garden_root, identifier=identifier, units="Meters")
    r1 = _call_tool(
        mcp,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="room2d",
        identifier="r_north",
        vertices=[[0, 5], [10, 5], [10, 10], [0, 10]],
        floor_height=0.0,
        floor_to_ceiling_height=3.0,
        is_ground_contact=True,
    )
    r2 = _call_tool(
        mcp,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="room2d",
        identifier="r_south",
        vertices=[[0, 0], [10, 0], [10, 5], [0, 5]],
        floor_height=0.0,
        floor_to_ceiling_height=3.0,
        is_top_exposed=True,
    )
    s1 = _call_tool(
        mcp,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="story",
        identifier="story_1",
        room2d_targets=[r1["target"], r2["target"]],
        floor_to_floor_height=3.5,
    )
    b = _call_tool(
        mcp,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="building",
        identifier="bldg_1",
        story_targets=[s1["target"]],
    )
    return m["model_target"], b["target"], s1["target"], r1["target"], r2["target"]


def _inject_synthetic_therm_results(thmz_path: Path) -> None:
    """Append synthetic Mesh.xml, SteadyStateMeshResults.xml, and SteadyStateResults.xml to a .thmz."""
    from fairyfly_therm.result import THMZResult
    from ladybug_geometry.geometry3d.pointvector import Point3D

    tr = THMZResult(str(thmz_path))
    plane = tr.plane
    tvec = tr._translation_vec

    # Invert THMZResult._extract_mesh(): plane.xy_to_xyz(pt2.move(tvec)) -> fairyfly 3D (mm).
    coords_mm = [(0.0, 0.0), (100.0, 0.0), (100.0, 200.0), (0.0, 200.0)]
    node_lines: list[str] = []
    for x_mm, y_mm in coords_mm:
        pt2 = plane.xyz_to_xy(Point3D(x_mm, y_mm, 0.0))
        node_lines.append(
            f"      <Node><x>{(pt2.x - float(tvec.x)) / 1000.0:.6f}</x>"
            f"<y>{(pt2.y - float(tvec.y)) / 1000.0:.6f}</y></Node>"
        )
    nodes_xml = "\n".join(node_lines)
    mesh_xml = f"""<Mesh>
  <Case>
    <Nodes>
{nodes_xml}
    </Nodes>
    <Elements>
      <Element><node0>0</node0><node1>1</node1><node2>2</node2><node3>3</node3></Element>
    </Elements>
  </Case>
</Mesh>
"""
    # Interior edge (x=0: nodes 0 and 3) is warm (11.5C min, 12.0C); exterior edge (x=100: nodes 1 and 2) is cold (1.2C, 2.0C).
    ss_mesh_xml = """<SteadyStateMeshResults>
  <Case>
    <Nodes>
      <Node><Temperature>11.5</Temperature><X-flux>3.0</X-flux><Y-flux>4.0</Y-flux></Node>
      <Node><Temperature>1.2</Temperature><X-flux>3.5</X-flux><Y-flux>4.5</Y-flux></Node>
      <Node><Temperature>2.0</Temperature><X-flux>2.5</X-flux><Y-flux>3.5</Y-flux></Node>
      <Node><Temperature>12.0</Temperature><X-flux>2.0</X-flux><Y-flux>3.0</Y-flux></Node>
    </Nodes>
  </Case>
</SteadyStateMeshResults>
"""
    ss_res_xml = """<SteadyStateResults>
  <Case>
    <U-factors>
      <Tag>WindowFrame</Tag>
      <DeltaT>20.0</DeltaT>
      <HeatFlux>18.0</HeatFlux>
      <Projection>
        <Length-type>Total Length</Length-type>
        <U-factor>1.8</U-factor>
        <Length>500.0</Length>
      </Projection>
      <Projection>
        <Length-type>Projected X</Length-type>
        <U-factor>2.0</U-factor>
        <Length>450.0</Length>
      </Projection>
    </U-factors>
  </Case>
</SteadyStateResults>
"""
    with zipfile.ZipFile(thmz_path, "r") as src:
        entries = {name: src.read(name) for name in src.namelist()}
    entries["Mesh.xml"] = mesh_xml.encode("utf-8")
    entries["SteadyStateMeshResults.xml"] = ss_mesh_xml.encode("utf-8")
    entries["SteadyStateResults.xml"] = ss_res_xml.encode("utf-8")
    with zipfile.ZipFile(thmz_path, "w") as dst:
        for name, data in entries.items():
            dst.writestr(name, data)


# ---------------------------------------------------------------------------
# 1. Verified Bug Fixes (DF + FF)
# ---------------------------------------------------------------------------


def test_bugfix_units_conversion_scales_geometry_and_preserves_flag(mcp_server: FastMCP, garden_root: str):
    from garden.dragonfly_core.model_files import load_dragonfly_model

    model_target, _, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="unit_m")
    res_geom = _call_tool(
        mcp_server,
        "DF_Edit_Object",
        garden_root=garden_root,
        object_type="model",
        model_target=model_target,
        units="Feet",
        convert_geometry=True,
    )
    assert res_geom["summary_view"]["units"] == "Feet"
    converted_model = load_dragonfly_model(Path(garden_root), res_geom["model_target"])
    xs = [pt.x for pt in converted_model.buildings[0].unique_room_2ds[0].floor_geometry.boundary]
    assert max(xs) > 30.0  # 10m -> ~32.808 ft

    res_raw = _call_tool(
        mcp_server,
        "DF_Edit_Object",
        garden_root=garden_root,
        object_type="model",
        model_target=res_geom["model_target"],
        units="Meters",
        convert_geometry=False,
    )
    raw_model = load_dragonfly_model(Path(garden_root), res_raw["model_target"])
    assert raw_model.units == "Meters"
    xs_raw = [pt.x for pt in raw_model.buildings[0].unique_room_2ds[0].floor_geometry.boundary]
    assert max(xs_raw) > 30.0  # coordinates preserved when convert_geometry=False


def test_bugfix_queries_symbol_and_named_operators(mcp_server: FastMCP, garden_root: str):
    model_target, _, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="q_ops")
    for op in ("==", "!=", "<", "<=", ">", ">=", "in", "contains", "equals", "not_equals", "gt", "lt", "gte", "lte"):
        if op == "contains":
            val = "north"
            attr = "identifier"
        elif op == "in":
            val = ["r_north", "r_other"]
            attr = "identifier"
        elif op in ("==", "!=", "equals", "not_equals"):
            val = "r_north"
            attr = "identifier"
        else:
            val = 40.0
            attr = "floor_area"
        res = _call_tool(
            mcp_server,
            "DF_Inspect_Model",
            garden_root=garden_root,
            view="room2ds_by_attribute",
            model_target=model_target,
            attribute=attr,
            operator=op,
            value=val,
        )
        assert res["report"]["status"] == "ok"
        assert "matches" in res


def test_bugfix_search_children_scope_strings_and_dict(mcp_server: FastMCP, garden_root: str):
    model_target, bldg_target, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="search_scope")
    for scope in ("none", "direct", "all", bldg_target):
        res = _call_tool(
            mcp_server,
            "DF_Search_Objects",
            garden_root=garden_root,
            model_target=model_target,
            object_type="all",
            children_scope=scope,
        )
        assert res["report"]["status"] == "ok"
        assert res["summary_view"]["count"] >= 1


def test_bugfix_envelope_segment_index_list(mcp_server: FastMCP, garden_root: str):
    from garden.dragonfly_core.model_files import load_dragonfly_model

    model_target, _, _, r1_target, _ = _build_basic_building_model(mcp_server, garden_root, identifier="seg_list")
    res_w = _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="window",
        host_target=r1_target,
        model_target=model_target,
        window_parameter={"type": "SimpleWindowRatio", "window_ratio": 0.4},
        application_scope="segment_index",
        segment_index=[0, 2],
    )
    assert res_w["report"]["status"] == "ok"
    res = _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="shading",
        host_target=r1_target,
        model_target=res_w["model_target"],
        shading_parameter={"type": "Overhang", "depth": 0.6, "angle": 0.0},
        application_scope="segment_index",
        segment_index=[0, 2],
    )
    assert res["report"]["status"] == "ok"
    m = load_dragonfly_model(Path(garden_root), res["model_target"])
    room = m.buildings[0].unique_room_2ds[0]
    assert room.window_parameters[0] is not None and room.window_parameters[2] is not None
    assert room.window_parameters[1] is None
    assert room.shading_parameters[0] is not None and room.shading_parameters[2] is not None


def test_bugfix_separate_top_bottom_floors_opt_in(mcp_server: FastMCP, garden_root: str):
    from garden.dragonfly_core.model_files import load_dragonfly_model

    model_target = _call_tool(mcp_server, "DF_Model", garden_root=garden_root, identifier="sep_opt")["model_target"]
    r1 = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="room2d",
        identifier="r_1",
        x_dim=10,
        y_dim=10,
        is_ground_contact=True,
        is_top_exposed=True,
    )
    s1 = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="story",
        identifier="s_1",
        room2d_targets=[r1["target"]],
    )
    s2 = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="story",
        identifier="s_2",
        room2d_targets=[r1["target"]],
    )
    b_keep = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="building",
        identifier="b_keep",
        story_targets=[s1["target"], s2["target"]],
        separate_top_bottom_floors=False,
        model_target=model_target,
    )
    m = load_dragonfly_model(Path(garden_root), b_keep["model_target"])
    # Story 1 room keeps original is_top_exposed=True when separate_top_bottom_floors=False
    assert m.buildings[0].unique_stories[0].room_2ds[0].is_top_exposed is True

    b_sep = _call_tool(
        mcp_server,
        "DF_Edit_Object",
        garden_root=garden_root,
        object_type="building",
        building_identifier="b_keep",
        model_target=b_keep["model_target"],
        separate_top_bottom_floors=True,
    )
    m_sep = load_dragonfly_model(Path(garden_root), b_sep["model_target"])
    assert m_sep.buildings[0].unique_stories[0].room_2ds[0].is_ground_contact is True
    assert m_sep.buildings[0].unique_stories[0].room_2ds[0].is_top_exposed is False
    assert m_sep.buildings[0].unique_stories[1].room_2ds[0].is_top_exposed is True


def test_bugfix_transfer_model_district_conversion(mcp_server: FastMCP, garden_root: str):
    m = _call_tool(mcp_server, "DF_Model", garden_root=garden_root, identifier="district_m")["model_target"]
    for b_id, ox in (("b1", 0.0), ("b2", 25.0)):
        _call_tool(
            mcp_server,
            "DF_Create_Objects",
            garden_root=garden_root,
            object_type="building_from_footprint",
            identifier=b_id,
            footprints=[[[ox, 0], [ox + 8, 0], [ox + 8, 8], [ox, 8]]],
            floor_to_floor_heights=[3.5],
            model_target=m,
        )
    res = _call_tool(
        mcp_server,
        "DF_Transfer_Model",
        garden_root=garden_root,
        operation="to_honeybee",
        model_target=m,
        object_per_model="District",
    )
    assert res["summary_view"]["honeybee_model_count"] == 1
    assert len(res["honeybee_model_targets"]) == 1


def test_bugfix_grid_color_network_and_results_visualizations_and_readers(
    mcp_server: FastMCP, garden_root: str, tmp_path: Path
):
    from garden.dragonfly_grid.authoring import (
        grid_network_to_visualization_set,
        grid_results_to_visualization_set,
    )

    sub = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="substation",
        identifier="sub1",
        footprint_points=[[0, 0], [5, 0], [5, 5], [0, 5]],
    )
    tx_prop = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="transformer_properties",
        identifier="custom_tx_prop",
        kva=500.0,
    )
    tx = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="transformer",
        identifier="tx1",
        footprint_points=[[10, 0], [13, 0], [13, 3], [10, 3]],
        transformer_properties_target=tx_prop["target"],
    )
    wire = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="wire",
        identifier="wire1",
        ampacity=220,
    )
    line = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="power_line",
        identifier="line1",
        wires=[wire["target"]],
        heights=[8.0],
        relative_xs=[0.0],
        phases=["A"],
    )
    conn = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="electrical_connector",
        identifier="conn1",
        polyline_points=[[2.5, 2.5], [11.5, 1.5]],
        power_line_target=line["target"],
    )
    net = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="electrical_network",
        identifier="net1",
        substation_target=sub["target"],
        transformer_targets=[tx["target"]],
        connector_targets=[conn["target"]],
    )
    vis = grid_network_to_visualization_set(
        garden_root=garden_root,
        network_target=net["target"],
        return_visualization_set=True,
    )
    assert len(vis["visualization_set"]["geometry"]) > 0

    csv_path = Path(garden_root) / "Line.conn1.csv"
    csv_lines = ["Datetime,Loading,Overloaded"]
    for hr in range(23):
        csv_lines.append(f"2020/01/01 {hr:02d}:00:00,{0.50 + hr * 0.02:.4f},False")
    csv_lines.append("2020/01/01 23:00:00,1.0200,True")
    csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
    res_target = {
        "target_type": "dragonfly_grid_result",
        "domain": "dragonfly_grid",
        "kind": "connector_result",
        "identifier": "Line.conn1",
        "path": "Line.conn1.csv",
    }
    res_vis = grid_results_to_visualization_set(
        garden_root=garden_root,
        result_targets=[res_target],
        network_target=net["target"],
        return_visualization_set=True,
    )
    assert len(res_vis["visualization_set"]["geometry"]) > 0

    opendss_read = _call_tool(
        mcp_server,
        "DF_Grid_Results",
        garden_root=garden_root,
        action="read_opendss",
        result_targets=[res_target],
    )
    assert opendss_read["report"]["status"] == "ok"
    assert opendss_read["summary_view"]["peak_factor_max"] == pytest.approx(1.02, abs=1e-4)

    reopt_json = Path(garden_root) / "reopt_report.json"
    reopt_json.write_text(
        json.dumps(
            {
                "outputs": {
                    "Scenario": {
                        "Site": {
                            "Financial": {"npv_us_dollars": 15000.0, "lcc_us_dollars": 90000.0},
                            "PV": {"size_kw": 75.0},
                            "ElectricStorage": {"size_kw": 30.0, "size_kwh": 60.0},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    reopt_read = _call_tool(
        mcp_server,
        "DF_Grid_Results",
        garden_root=garden_root,
        action="read_reopt_result",
        report_json_path="reopt_report.json",
    )
    assert reopt_read["report"]["status"] == "ok"


def test_bugfix_reopt_assumptions_wires_financial_and_reopt_params(
    mcp_server: FastMCP, garden_root: str, tmp_path: Path
):
    from garden.dragonfly_grid.authoring import load_grid_object
    from garden.urbanopt_cli import _write_reopt_assumptions_file

    fp = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="financial_parameters",
        identifier="fp_custom",
        analysis_years=20,
        escalation_rate=0.03,
        tax_rate=0.21,
        discount_rate=0.07,
    )
    rp = _call_tool(
        mcp_server,
        "DF_Grid_Create_Object",
        garden_root=garden_root,
        kind="reopt_parameter",
        identifier="rp_custom",
        financial_parameters_target=fp["target"],
        pv_parameter={"max_kw": 250.0},
        storage_parameter={"max_kw": 100.0},
    )
    assump = _write_reopt_assumptions_file(
        project_dir=tmp_path,
        runtime=None,
        urdb_label="539f6a23ec4f024411ec8bf9",
        reopt_parameter=load_grid_object(garden_root=garden_root, target=rp["target"]),
        financial_parameter=load_grid_object(garden_root=garden_root, target=fp["target"]),
    )
    data = json.loads(assump.read_text(encoding="utf-8"))
    assert data["Financial"]["analysis_years"] == 20
    pv_val = data["PV"][0] if isinstance(data["PV"], list) else data["PV"]
    assert pv_val["max_kw"] == 250.0
    assert data["ElectricStorage"]["max_kw"] == 100.0


def test_bugfix_fairyfly_cross_platform_registration_and_async_worker(
    mcp_server: FastMCP, garden_root: str, monkeypatch: pytest.MonkeyPatch
):
    import garden.fairyfly.availability as avail
    import garden.fairyfly.therm as ff_therm

    monkeypatch.setattr(avail, "is_windows_platform", lambda: False)
    assert avail.fairyfly_tools_enabled() is True
    assert avail.therm_engine_config()["available"] is False

    m = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_async")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m["target"],
        shapes=[{"vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]], "material": {"conductivity": 1.0, "name": "Brick"}}],
        boundaries=[
            {"line_segments_2d": [[[0, 0], [0, 100]]], "temperature": 20.0, "film_coefficient": 8.0, "u_factor_tag": "UF1"},
            {"line_segments_2d": [[[100, 0], [100, 100]]], "temperature": 0.0, "film_coefficient": 25.0},
        ],
    )
    exported = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m["target"],
        export_only=True,
        run_id="ff_export_1",
    )
    assert exported["summary_view"]["status"] == "written"

    blocked = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m["target"],
        export_only=False,
        run_id="ff_blocked_1",
    )
    assert blocked["status"] == "blocked"

    # Mock Windows engine + submit_worker_process to verify async submission + therm.log check
    monkeypatch.setattr(ff_therm, "therm_engine_config", lambda: {"available": True, "therm_exe": "THERM.exe"})
    submitted: list[dict] = []

    class DummyProc:
        pid = 99999

    def fake_submit(**kwargs):
        submitted.append(kwargs)
        req = kwargs["request"]
        ff_therm._run_therm_worker(**req)
        return DummyProc()

    monkeypatch.setattr(ff_therm, "submit_worker_process", fake_submit)

    # Fail case: run_thmz writes therm.log without 'Calculation complete.'
    def fake_run_incomplete(thmz_file: str, silent: bool = True):
        (Path(thmz_file).parent / "therm.log").write_text("THERM started...\nFatal error", encoding="utf-8")
        return thmz_file

    monkeypatch.setattr(ff_therm, "run_thmz", fake_run_incomplete)
    failed_res = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m["target"],
        run_id="ff_fail_1",
        wait_seconds=1.0,
    )
    assert len(submitted) == 1
    assert failed_res["status"] == "failed"
    assert "Calculation complete." in str(failed_res["error"])

    # Success case: run_thmz writes 'Calculation complete.'
    def fake_run_ok(thmz_file: str, silent: bool = True):
        (Path(thmz_file).parent / "therm.log").write_text("Calculation complete.\n", encoding="utf-8")
        _inject_synthetic_therm_results(Path(thmz_file))
        return thmz_file

    monkeypatch.setattr(ff_therm, "run_thmz", fake_run_ok)
    ok_res = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m["target"],
        run_id="ff_ok_1",
        simulation_parameter={
            "mesh": {"mesh_type": "Simmetrix", "parameter": 15},
            "exposure": {"model_type": "Opaque Wall"},
        },
        wait_seconds=1.0,
    )
    assert ok_res["status"] == "completed"
    assert ok_res["summary_view"]["simulation_parameter"]["mesh"]["parameter"] == 15


# ---------------------------------------------------------------------------
# 2. Dragonfly Core, Energy, Files, Display, URBANopt, DES, Grid, UWG P1
# ---------------------------------------------------------------------------


def test_df_core_creation_and_geometry_parity(mcp_server: FastMCP, garden_root: str):
    from garden.dragonfly_core.model_files import load_dragonfly_model

    model_target = _call_tool(mcp_server, "DF_Model", garden_root=garden_root, identifier="geom_p1")["model_target"]
    b1 = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="building_from_all_story_geometry",
        identifier="b_all_story",
        all_story_geometry=[[[[0, 0], [20, 0], [20, 20], [0, 20]]], [[[0, 0], [16, 0], [16, 16], [0, 16]]]],
        floor_to_floor_heights=[4.0, 4.0],
        roof_geometry=[
            [[0, 0, 8], [16, 0, 8], [8, 8, 10]],
            [[16, 0, 8], [16, 16, 8], [8, 8, 10]],
            [[16, 16, 8], [0, 16, 8], [8, 8, 10]],
            [[0, 16, 8], [0, 0, 8], [8, 8, 10]],
        ],
        basement_count=1,
        basement_remove_windows=True,
        model_target=model_target,
    )
    assert b1["report"]["status"] == "ok"
    m = load_dragonfly_model(Path(garden_root), b1["model_target"])
    assert len(m.buildings[0].unique_stories) == 2
    assert m.buildings[0].unique_stories[0].room_2ds[0].is_ground_contact is True
    assert any(
        getattr(bc, "__class__", None).__name__ == "Ground"
        for bc in m.buildings[0].unique_stories[0].room_2ds[0].boundary_conditions
    )

    # Run P1 geometry operations on a two-story setup
    m2 = _call_tool(mcp_server, "DF_Model", garden_root=garden_root, identifier="geom_ops")["model_target"]
    b2 = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="building_from_footprint",
        identifier="b_ops",
        footprints=[[[0, 0], [20, 0], [20, 20], [0, 20]]],
        floor_to_floor_heights=[4.0, 4.0],
        model_target=m2,
    )
    res_cp = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="core_perimeter",
        model_target=b2["model_target"],
        perimeter_offset=4.0,
        air_boundary=True,
    )
    assert res_cp["report"]["status"] == "ok"
    res_split = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="split_with_story_above",
        model_target=res_cp["model_target"],
        building_identifier="b_ops",
    )
    assert res_split["report"]["status"] == "ok"
    res_plenum = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="separate_plenums",
        model_target=res_split["model_target"],
        building_identifier="b_ops",
        target_floor_to_ceiling=3.0,
    )
    assert res_plenum["report"]["status"] == "ok"
    res_tr = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="transform",
        model_target=res_plenum["model_target"],
        transform_type="move",
        vector=[5.0, 0.0, 0.0],
    )
    assert res_tr["report"]["status"] == "ok"
    res_mult = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="convert_multipliers",
        model_target=res_tr["model_target"],
    )
    assert res_mult["report"]["status"] == "ok"
    base_sid = load_dragonfly_model(Path(garden_root), res_mult["model_target"]).buildings[0].unique_stories[0].identifier
    res_pull = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="pull_to_story",
        model_target=res_mult["model_target"],
        building_identifier="b_ops",
        base_story_id=base_sid,
        distance=1.0,
    )
    assert res_pull["report"]["status"] == "ok"
    res_merge = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="merge_model",
        model_target=res_pull["model_target"],
        incoming_model_target=b1["model_target"],
    )
    assert res_merge["report"]["status"] == "ok"
    assert len(load_dragonfly_model(Path(garden_root), res_merge["model_target"]).buildings) == 2

    # fill_holes & join_room_2ds on adjacent rooms
    m3 = _call_tool(mcp_server, "DF_Model", garden_root=garden_root, identifier="geom_join")["model_target"]
    ra = _call_tool(mcp_server, "DF_Create_Objects", garden_root=garden_root, object_type="room2d", identifier="ra", vertices=[[0, 0], [5, 0], [5, 5], [0, 5]], model_target=m3)["target"]
    rb = _call_tool(mcp_server, "DF_Create_Objects", garden_root=garden_root, object_type="room2d", identifier="rb", vertices=[[5, 0], [10, 0], [10, 5], [5, 5]], model_target=m3)["target"]
    st = _call_tool(mcp_server, "DF_Create_Objects", garden_root=garden_root, object_type="story", identifier="st", room2d_targets=[ra, rb], model_target=m3)["target"]
    _call_tool(mcp_server, "DF_Create_Objects", garden_root=garden_root, object_type="building", identifier="bj", story_targets=[st], model_target=m3)
    assert _call_tool(mcp_server, "DF_Process_Geometry", garden_root=garden_root, operation="fill_holes", model_target=m3, story_target=st)["report"]["status"] == "ok"
    assert _call_tool(mcp_server, "DF_Process_Geometry", garden_root=garden_root, operation="join_room_2ds", model_target=m3, story_target=st, room_identifiers=["ra", "rb"])["report"]["status"] == "ok"


def test_df_envelope_all_windows_shading_skylights_walls_and_properties(mcp_server: FastMCP, garden_root: str):
    model_target, _, s_target, r1_target, r2_target = _build_basic_building_model(mcp_server, garden_root, identifier="env_prop")
    shade = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="context_shade",
        identifier="ctx_1",
        x_dim=4.0,
        y_dim=2.0,
        height=3.0,
        model_target=model_target,
    )["target"]

    for win_param in (
        {"type": "SingleWindow", "width": 2.0, "height": 1.5, "sill_height": 0.9},
        {"type": "SimpleWindowArea", "window_area": 3.0},
        {"type": "SimpleWindowRatio", "window_ratio": 0.35},
        {"type": "RepeatingWindowRatio", "window_ratio": 0.4, "window_height": 1.5, "sill_height": 0.9, "horizontal_separation": 3.0},
        {"type": "RepeatingWindowWidthHeight", "window_height": 1.5, "window_width": 1.2, "sill_height": 0.9, "horizontal_separation": 2.0},
        {"type": "RectangularWindows", "origins": [[1.0, 0.9]], "widths": [2.0], "heights": [1.5]},
        {"type": "DetailedWindows", "polygons": [[[1.0, 0.9], [3.0, 0.9], [3.0, 2.4], [1.0, 2.4]]]},
    ):
        res = _call_tool(
            mcp_server,
            "DF_Apply_Properties",
            garden_root=garden_root,
            property_domain="window",
            host_target=r1_target,
            model_target=model_target,
            window_parameter=win_param,
        )
        assert res["report"]["status"] == "ok"

    for shd in (
        {"type": "LouversByDistance", "depth": 0.3, "distance": 0.25, "angle": 15.0},
        {"type": "LouversByCount", "depth": 0.3, "louver_count": 4, "angle": 10.0},
    ):
        assert _call_tool(mcp_server, "DF_Apply_Properties", garden_root=garden_root, property_domain="shading", host_target=r1_target, model_target=model_target, shading_parameter=shd)["report"]["status"] == "ok"

    for sky in (
        {"type": "GriddedSkylightArea", "skylight_area": 1.0, "spacing": 2.5},
        {"type": "GriddedSkylightRatio", "skylight_ratio": 0.05, "spacing": 3.0},
        {"type": "DetailedSkylights", "polygons": [[[2.0, 6.0], [4.0, 6.0], [4.0, 8.0], [2.0, 8.0]]]},
    ):
        assert _call_tool(mcp_server, "DF_Apply_Properties", garden_root=garden_root, property_domain="skylight", host_target=r1_target, model_target=model_target, skylight_parameter=sky)["report"]["status"] == "ok"

    # Attach roof + DetailedClerestory on a dedicated building with RoofSpecification
    b_roof = _call_tool(
        mcp_server,
        "DF_Create_Objects",
        garden_root=garden_root,
        object_type="building_from_footprint",
        identifier="b_clerestory",
        footprints=[[[0, 20], [10, 20], [10, 30], [0, 30]]],
        floor_to_floor_heights=[4.0],
        roof_geometry=[[[0, 20, 4], [10, 20, 4], [5, 25, 6]], [[10, 20, 4], [10, 30, 4], [5, 25, 6]], [[10, 30, 4], [0, 30, 4], [5, 25, 6]], [[0, 30, 4], [0, 20, 4], [5, 25, 6]]],
        model_target=model_target,
    )
    assert _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="clerestory",
        story_identifier="b_clerestory_Floor1",
        model_target=b_roof["model_target"],
        clerestory_parameter={
            "type": "DetailedClerestory",
            "base_line": [[0, 20, 4], [10, 20, 4]],
            "elevation": 4.2,
            "polygons": [[[1.0, 0.2], [3.0, 0.2], [3.0, 1.0], [1.0, 1.0]]],
        },
    )["report"]["status"] == "ok"

    adj_res = _call_tool(
        mcp_server,
        "DF_Process_Geometry",
        garden_root=garden_root,
        operation="solve_adjacency",
        model_target=b_roof["model_target"],
        story_target=s_target,
        intersect=True,
    )
    assert adj_res["report"]["status"] == "ok"

    assert _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="wall",
        host_target=r2_target,
        model_target=adj_res["model_target"],
        segment_index=[2],
        air_boundary=True,
    )["report"]["status"] == "ok"

    assert _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="wall",
        host_target=r2_target,
        model_target=adj_res["model_target"],
        segment_index=[0, 1],
        boundary_condition="Adiabatic",
    )["report"]["status"] == "ok"

    # Energy P1 properties (HVAC, SHW, loads, daylight, vent, fans, process, plenums, diversify, context shade)
    res_e = _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="energy",
        host_target=r1_target,
        model_target=model_target,
        hvac={"type": "IdealAirSystem", "identifier": "ideal_1"},
        shw={"type": "SHWSystem", "identifier": "shw_1", "equipment_type": "Gas_WaterHeater"},
        person_count=4,
        lighting_watts=120.0,
        electric_equipment_watts=250.0,
        gas_equipment_watts=50.0,
        hot_water_flow=0.02,
        infiltration_ach=0.4,
        daylighting_control={"illuminance_setpoint": 300.0},
        window_vent_control={"min_indoor_temp": 21.0, "max_outdoor_temp": 26.0},
        fans=[{"name": "exhaust_1", "flow_rate": 0.1, "pressure_rise": 150.0, "motor_efficiency": 0.7}],
        process_loads=[{"name": "oven_1", "watts": 400.0}],
    )
    assert res_e["report"]["status"] == "ok"

    res_ctx_e = _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="energy",
        host_target=shade,
        model_target=model_target,
        construction="Generic Context",
        transmittance_schedule="Always On",
    )
    assert res_ctx_e["report"]["status"] == "ok"
    res_ctx_r = _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="radiance",
        host_target=shade,
        model_target=model_target,
        modifier="generic_context_0.20",
    )
    assert res_ctx_r["report"]["status"] == "ok"


def test_df_model_files_and_visualizations_parity(mcp_server: FastMCP, garden_root: str):
    model_target, _, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="files_vis")
    for ftype in ("dfpkl", "osm", "idf", "gbxml", "sdd", "rad_folder"):
        exp = _call_tool(
            mcp_server,
            "DF_Transfer_Model",
            garden_root=garden_root,
            operation="export_file",
            model_target=model_target,
            file_type=ftype,
            artifact_name=f"out_{ftype}",
        )
        assert exp["report"]["status"] == "ok"

    dfpkl_res = _call_tool(
        mcp_server,
        "DF_Transfer_Model",
        garden_root=garden_root,
        operation="export_file",
        model_target=model_target,
        file_type="dfpkl",
        artifact_name="roundtrip_pkg",
    )
    dfpkl_path = Path(garden_root) / dfpkl_res["persistence_receipt"]["artifact_path"]
    imp = _call_tool(
        mcp_server,
        "DF_Transfer_Model",
        garden_root=garden_root,
        operation="import_file",
        file_type="dfpkl",
        file_path=str(dfpkl_path),
        identifier="reimported_df",
    )
    assert imp["summary_view"]["building_count"] == 1

    vis_attr = _call_tool(
        mcp_server,
        "DF_To_Visualization_Set",
        garden_root=garden_root,
        mode="attribute",
        model_target=model_target,
        room_attrs=["floor_area"],
        return_visualization_set=True,
    )
    assert len(vis_attr["visualization_set"]["geometry"]) > 0

    _call_tool(
        mcp_server,
        "DF_Transfer_Model",
        garden_root=garden_root,
        operation="to_honeybee",
        model_target=model_target,
        object_per_model="District",
        set_base=True,
    )
    vis_op = _call_tool(
        mcp_server,
        "DF_To_Visualization_Set",
        garden_root=garden_root,
        mode="opening_projection",
        model_target=model_target,
        projection_distance=0.3,
        return_visualization_set=True,
    )
    assert vis_op["report"]["status"] == "ok"


def test_df_urbanopt_prepare_and_read_results(
    mcp_server: FastMCP, garden_root: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from contextlib import nullcontext
    import garden.dragonfly_des.export as des_export
    import garden.run_urbanopt as ruo

    epw = _write_minimal_epw(tmp_path / "boston.epw")
    model_target, _, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="uo_m")

    def fake_sdk_model_to_urbanopt(*, folder: str, **kwargs):
        out_dir = Path(folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        hb_path = out_dir / "bldg_1.hbjson"
        hb_path.write_text('{"type": "Model", "identifier": "bldg_1"}\n', encoding="utf-8")
        gj_path = out_dir / "uo_m.geojson"
        gj_path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {
                                "id": "bldg_1",
                                "name": "bldg_1",
                                "type": "Building",
                                "detailed_model_filename": str(hb_path),
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return str(gj_path), [str(hb_path)], []

    monkeypatch.setattr(des_export, "sdk_model_to_urbanopt", fake_sdk_model_to_urbanopt)
    exported_gj = _call_tool(
        mcp_server,
        "DF_DES_Export_Model",
        garden_root=garden_root,
        export_kind="urbanopt",
        model_target=model_target,
        location={"city": "Boston", "latitude": 42.36, "longitude": -71.06, "time_zone": -5},
        point=[0.0, 0.0],
    )
    geojson_target = exported_gj["feature_geojson_target"]
    geojson_abs = Path(garden_root) / geojson_target["path"]
    weather_target = {"target_type": "epw", "domain": "ladybug", "path": str(epw)}

    custom_osw = Path(garden_root) / "custom_base.osw"
    custom_osw.write_text('{"steps": []}\n', encoding="utf-8")
    (Path(garden_root) / "m1").mkdir(exist_ok=True)
    (Path(garden_root) / "m2").mkdir(exist_ok=True)
    sim_par_file = Path(garden_root) / "sim_par.json"
    from honeybee_energy.simulation.parameter import SimulationParameter

    sim_par_file.write_text(json.dumps(SimulationParameter().to_dict()), encoding="utf-8")

    monkeypatch.setattr(ruo, "resolve_garden_weather_epw", lambda *a, **k: epw)
    monkeypatch.setattr(ruo, "preflight_urbanopt_runtime", lambda: {"runtime_status": "ready", "runtime": {"urbanopt_exe": "uo"}})
    monkeypatch.setattr(ruo, "prime_urbanopt_sdk_version_cache", lambda *a, **k: None)
    monkeypatch.setattr(ruo, "Measure", lambda folder: {"measure_folder": str(folder)})
    monkeypatch.setattr(ruo, "MapperMeasure", lambda folder: {"mapper_folder": str(folder)})
    captured: dict = {}

    def fake_base_osw(project_dir: str, **kwargs):
        captured.update(kwargs)

    def fake_prepare_folder(geojson_path: str, **kwargs):
        scsv = Path(geojson_path).parent / "baseline_scenario.csv"
        scsv.write_text("Feature Id,Feature Name\nbldg_1,bldg_1\n", encoding="utf-8")
        return str(scsv)

    monkeypatch.setattr(ruo, "sdk_base_honeybee_osw", fake_base_osw)
    monkeypatch.setattr(ruo, "sdk_prepare_urbanopt_folder", fake_prepare_folder)

    prep = _call_tool(
        mcp_server,
        "DF_URBANopt_Prepare_Project",
        garden_root=garden_root,
        feature_geojson_target=geojson_target,
        weather_target=weather_target,
        sim_par_target={"path": "sim_par.json"},
        additional_measures=["m1"],
        additional_mapper_measures=["m2"],
        base_osw="custom_base.osw",
        emissions_year=2025,
    )
    assert prep["report"]["status"] == "ok"
    assert captured["emissions_year"] == 2025
    assert len(captured["additional_measures"]) == 1
    assert len(captured["additional_mapper_measures"]) == 1
    assert captured["base_osw"] == str(custom_osw.resolve())

    run_dir = geojson_abs.parent / "run" / "baseline_scenario"
    run_dir.mkdir(parents=True, exist_ok=True)
    b_dir = run_dir / "bldg_1"
    b_dir.mkdir(parents=True, exist_ok=True)
    (b_dir / "eplusout.sql").write_bytes(b"sqlite")
    scenario_target = prep["scenario_csv_target"]

    def fake_default_report(*a, **k):
        r_csv = run_dir / "default_scenario_report.csv"
        r_json = run_dir / "default_scenario_report.json"
        r_json.write_text(
            json.dumps({"scenario_report": {"total_energy_kwh": 12345.0, "eui_kwh_m2": 98.5}}),
            encoding="utf-8",
        )
        r_csv.write_text("Metric,Value\nTotal,12345\n", encoding="utf-8")
        return str(r_csv), str(r_json)

    class DummySQL:
        def __init__(self, path: str):
            self.path = path

        def tabular_data_by_name(self, name: str):
            if "Demand End Use" in name:
                return {"Total End Uses": [42.5]}
            return {}

    monkeypatch.setattr(ruo, "has_urbanopt_cli_bundle", lambda *a, **k: False)
    monkeypatch.setattr(ruo, "urbanopt_runtime_env", lambda *a, **k: nullcontext())
    monkeypatch.setattr(ruo, "sdk_run_default_report", fake_default_report)
    monkeypatch.setattr(
        ruo,
        "eui_from_sql",
        lambda sql, absolute=False: {
            "eui": 120.5,
            "total_floor_area": 100.0,
            "conditioned_floor_area": 100.0,
            "total_energy": 12050.0,
            "end_uses": {"Cooling": 30.0, "Heating": 40.0},
        },
    )
    monkeypatch.setattr(ruo, "SQLiteResult", DummySQL)
    monkeypatch.setattr(ruo, "emissions_from_sql", lambda sql, subregion=None: {"total_co2_kg": 420.0})

    res_read = _call_tool(
        mcp_server,
        "DF_URBANopt_Read_Results",
        garden_root=garden_root,
        feature_geojson_target=geojson_target,
        scenario_csv_target=scenario_target,
        run_default_report=True,
        include_building_sql_summary=True,
        subregion="NEWE",
    )
    assert res_read["report"]["status"] == "ok"
    assert res_read["summary_view"]["building_count"] == 1
    assert res_read["buildings"][0]["peak_electric_kw"] == pytest.approx(42.5, abs=1e-4)
    assert res_read["buildings"][0]["emissions"]["total_co2_kg"] == 420.0


def test_df_des_plants_ets_geojson_compat_bind_and_ghe_results(
    mcp_server: FastMCP, garden_root: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import garden.dragonfly_des.runs as des_runs

    hp = _call_tool(mcp_server, "DF_DES_Create_Object", garden_root=garden_root, kind="heating_plant", identifier="hp_1", params={"hw_setpoint": 60.0})
    cp = _call_tool(mcp_server, "DF_DES_Create_Object", garden_root=garden_root, kind="cooling_plant", identifier="cp_1", params={"chw_setpoint": 6.5})
    hx = _call_tool(mcp_server, "DF_DES_Create_Object", garden_root=garden_root, kind="heat_exchanger_ets", identifier="hx_1")
    hpe = _call_tool(mcp_server, "DF_DES_Create_Object", garden_root=garden_root, kind="heat_pump_ets", identifier="hpe_1")
    loop4 = _call_tool(
        mcp_server,
        "DF_DES_Create_Object",
        garden_root=garden_root,
        kind="fourth_gen_thermal_loop",
        identifier="loop4g",
        heating_plant_target=hp["target"],
        cooling_plant_target=cp["target"],
    )
    assert loop4["report"]["status"] == "ok"
    assert hx["target"]["kind"] == "heat_exchanger_ets"
    assert hpe["target"]["kind"] == "heat_pump_ets"

    model_target, _, _, _, _ = _build_basic_building_model(mcp_server, garden_root, identifier="des_bind")
    bind_res = _call_tool(
        mcp_server,
        "DF_DES_Run_Step",
        garden_root=garden_root,
        step="bind_des_loads",
        model_target=model_target,
        heat_exchanger_ets_target=hx["target"],
    )
    assert bind_res["report"]["status"] == "ok"

    geojson_file = Path(garden_root) / "des_site.geojson"
    geojson_file.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"id": "tc1", "type": "ThermalConnector"},
                        "geometry": {"type": "LineString", "coordinates": [[-71.06, 42.36], [-71.059, 42.36]]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    from garden.manifest import GardenManifest

    gj_target = {
        "target_type": "artifact",
        "artifact_type": "dragonfly_des_feature_geojson",
        "domain": "dragonfly_des",
        "garden_id": GardenManifest.read(Path(garden_root)).garden_id,
        "path": "des_site.geojson",
    }

    import garden.dragonfly_des.runs as des_runs_mod

    monkeypatch.setattr(des_runs_mod, "sdk_check_des_compatibility", lambda gj: (True, []))
    compat = _call_tool(
        mcp_server,
        "DF_DES_Run_Step",
        garden_root=garden_root,
        step="check_compatibility",
        feature_geojson_target=gj_target,
    )
    assert compat["compatible"] is True

    # Test 5G & GHE from_geojson paths
    loop5_gj = _call_tool(
        mcp_server,
        "DF_DES_Create_Object",
        garden_root=garden_root,
        kind="fifth_gen_thermal_loop",
        identifier="loop5_gj",
        geojson_file_path="des_site.geojson",
    )
    assert loop5_gj["report"]["status"] == "ok"

    from dragonfly_energy.des.ghe import GroundHeatExchanger

    monkeypatch.setattr(GroundHeatExchanger, "load_g_function", staticmethod(lambda *a, **k: [[-2.0, 1.5]]))
    monkeypatch.setattr(GroundHeatExchanger, "load_monthly_temperatures", staticmethod(lambda *a, **k: [18.0] * 12))
    monkeypatch.setattr(
        GroundHeatExchanger,
        "load_energyplus_properties",
        staticmethod(lambda *a, **k: [120.0] + [1.0] * max(len(GroundHeatExchanger.PROPERTY_NAMES) - 1, 0)),
    )

    ghe_dir = Path(garden_root) / "ghe_out"
    ghe_dir.mkdir(parents=True, exist_ok=True)
    bh = ghe_dir / "boreholes.csv"
    gf = ghe_dir / "g_function.csv"
    sm = ghe_dir / "SimulationSummary.json"
    bh.write_text("x,y\n0,0\n5,0\n", encoding="utf-8")
    gf.write_text("t,g\n-2,1.5\n", encoding="utf-8")
    sm.write_text("{}", encoding="utf-8")
    ghe_res = des_runs.read_ghe_results(
        garden_root=garden_root,
        ghe_folder=str(ghe_dir),
        borehole_file=str(bh),
        g_function_file=str(gf),
        summary_file=str(sm),
    )
    assert ghe_res["summary_view"]["borehole_count"] == 2
    assert ghe_res["summary_view"]["monthly_temperature_count"] == 12
    assert ghe_res["energyplus_properties"] is not None


def test_df_uwg_helpers_metrics_inference_and_uhi_summary(
    mcp_server: FastMCP, garden_root: str, tmp_path: Path
):
    from garden.run_uwg import _compute_uhi_summary
    from ladybug.epw import EPW

    epw_rural = _write_minimal_epw(tmp_path / "rural.epw")
    epw_urban = tmp_path / "urban.epw"
    urb = EPW(str(epw_rural))
    urb.dry_bulb_temperature.values = [v + 2.5 for v in urb.dry_bulb_temperature.values]
    urb.save(str(epw_urban))

    uhi = _compute_uhi_summary(epw_rural, epw_urban)
    assert uhi is not None
    assert pytest.approx(uhi["mean_uhi_delta_c"], abs=0.05) == 2.5
    assert "hdd_18_3c_delta" in uhi and "cdd_18_3c_delta" in uhi

    for helper, h_params in (
        ("terrain", {"geometry": [[0, 0], [20, 0], [20, 20], [0, 20]]}),
        ("traffic", {}),
        ("vegetation", {}),
        ("reference_epw_site", {}),
        ("boundary_layer_parameter", {}),
    ):
        res = _call_tool(
            mcp_server,
            "DF_UWG_Properties",
            garden_root=garden_root,
            action="create_helper",
            helper_type=helper,
            helper_params=h_params,
        )
        assert res["report"]["status"] == "ok"

    model_target, _, _, r1_target, _ = _build_basic_building_model(mcp_server, garden_root, identifier="uwg_m")
    _call_tool(
        mcp_server,
        "DF_Apply_Properties",
        garden_root=garden_root,
        property_domain="energy",
        host_target=r1_target,
        model_target=model_target,
        program_type_identifier="2013::LargeOffice::OpenOffice",
    )
    inf = _call_tool(
        mcp_server,
        "DF_UWG_Properties",
        garden_root=garden_root,
        action="apply",
        host_target=model_target,
        model_target=model_target,
        infer_program_from_energy_program=True,
    )
    assert inf["report"]["status"] == "ok"
    summ = _call_tool(
        mcp_server,
        "DF_UWG_Properties",
        garden_root=garden_root,
        action="get_summary",
        model_target=model_target,
    )
    assert summ["report"]["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. Fairyfly / THERM P1 Parity
# ---------------------------------------------------------------------------


def test_fairyfly_p1_materials_xml_layers_geometry_validation_and_results(
    mcp_server: FastMCP, garden_root: str
):
    from garden.fairyfly.model import (
        create_fairyfly_cavity_material,
        create_fairyfly_gas,
        create_fairyfly_pure_gas,
        load_fairyfly_model,
    )

    pg = create_fairyfly_pure_gas(
        name="CustomPureGas",
        conductivity_coeff_a=0.025,
        viscosity_coeff_a=1.8e-5,
        specific_heat_coeff_a=1005.0,
    )
    gas = create_fairyfly_gas(name="CustomMix", pure_gases=[pg["object_dict"]], gas_fractions=[1.0])
    for cm in ("CEN", "NFRC", "ISO15099", "ISO15099Ventilated"):
        cav = create_fairyfly_cavity_material(name=f"Cav_{cm}", cavity_model=cm, gas=gas["object_dict"])
        assert cav["summary_view"]["cavity_model"] == cm

    # Built-in library + HB-Energy opaque + CavityMaterial in Model.from_layers on custom 3D Plane
    m_layers = _call_tool(
        mcp_server,
        "FF_Create_Model",
        garden_root=garden_root,
        identifier="ff_layers",
        plane={"origin": [0, 0, 10], "normal": [0, 0, 1]},
        layers=[
            {"thickness": 50.0, "name": "BrickLayer", "material": {"hb_material_name": "Generic Brick"}},
            {"thickness": 25.0, "name": "CavLayer", "material": {"cavity_model": "NFRC", "gas_name": "Argon"}},
            {"thickness": 12.0, "name": "GypsumLayer", "material": {"material_name": "Aerated Concrete"}},
        ],
        layer_height=150.0,
    )
    assert m_layers["summary_view"]["object_counts"]["shapes"] == 3

    # Export FFJSON & re-import with source_file
    exp_ff = _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_layers["target"],
        export_format="ffjson",
        export_name="layers_export",
    )
    reimp = _call_tool(
        mcp_server,
        "FF_Create_Model",
        garden_root=garden_root,
        identifier="ff_reimported",
        source_file=str(Path(garden_root) / exp_ff["summary_view"]["path"]),
    )
    assert reimp["summary_view"]["object_counts"]["shapes"] == 3

    # Edit/delete/intersect/transforms/units + HB glazing material + condition alias
    edit_res = _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_layers["target"],
        shapes=[
            {
                "name": "ExtraPane",
                "vertices_2d": [[87, 0], [93, 0], [93, 150], [87, 150]],
                "material": {
                    "energy_material": {
                        "type": "EnergyWindowMaterialGlazing",
                        "identifier": "ClearGlass3mm",
                        "thickness": 0.003,
                        "conductivity": 0.9,
                    }
                },
            }
        ],
        boundaries=[
            {"name": "InB", "line_segments_2d": [[[0, 0], [0, 150]]], "condition_name": "Exterior"},
            {"name": "TempB", "line_segments_2d": [[[87, 0], [87, 150]]], "condition_name": "Adiabatic"},
        ],
        edit_shapes=[{"name": "BrickLayer", "new_name": "BrickRenamed"}],
        edit_boundaries=[{"name": "InB", "temperature": 21.0, "film_coefficient": 7.7, "u_factor_tag": "Frame"}],
        intersect_adjacency=True,
        transforms=[
            {"action": "move", "vector": [10, 0, 0]},
            {"action": "rotate_xy", "angle_degrees": 15.0},
            {"action": "scale", "factor": 1.0},
        ],
        convert_units="Meters",
    )
    assert edit_res["report"]["status"] == "ok"
    edit_rm = _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=edit_res["model_target"],
        remove_boundary_identifiers=["TempB"],
    )
    assert edit_rm["report"]["status"] == "ok"
    m_edited = load_fairyfly_model(Path(garden_root), edit_rm["model_target"])
    assert m_edited.units == "Meters"
    assert len(m_edited.boundaries) == 3  # Outdoors, Indoors, InB after TempB removed

    # THERM XML export + import check (validating deduplication too)
    from fairyfly_therm.material.solid import SolidMaterial

    sample_mat = SolidMaterial(1.5)
    sample_mat.display_name = "TestXMLConcrete"
    xml_path = Path(garden_root) / "therm_lib.xml"
    xml_path.write_text(f"<THERM-XML>{sample_mat.to_therm_xml_str()}</THERM-XML>", encoding="utf-8")
    xml_imp = _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        import_therm_xml_path=str(xml_path),
    )
    assert xml_imp["summary_view"]["solid_material_count"] == 1
    assert xml_imp["solid_materials"][0]["display_name"] == "TestXMLConcrete"

    # Validate disconnected problem_areas
    m_disconn = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_prob")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_disconn["target"],
        shapes=[
            {"name": "S1", "vertices_2d": [[0, 0], [50, 0], [50, 50], [0, 50]], "material": {"conductivity": 1.0}},
            {"name": "S2", "vertices_2d": [[100, 0], [150, 0], [150, 50], [100, 50]], "material": {"conductivity": 1.0}},
        ],
    )
    val = _call_tool(mcp_server, "FF_Validate_Model", garden_root=garden_root, model_target=m_disconn["target"])
    assert val["valid"] is False
    assert val["problem_areas"]["problem_region_count"] >= 2

    # Export a THMZ and inject synthetic results to verify heat_flux_vectors, condensation_risk, psi_factor
    m_res = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_results")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_res["target"],
        shapes=[{"name": "Wall", "vertices_2d": [[0, 0], [100, 0], [100, 200], [0, 200]], "material": {"conductivity": 0.5}}],
        boundaries=[
            {"name": "Interior", "line_segments_2d": [[[0, 0], [0, 200]]], "temperature": 20.0, "film_coefficient": 8.0, "relative_humidity": 0.5},
            {"name": "Exterior", "line_segments_2d": [[[100, 0], [100, 200]]], "temperature": 0.0, "film_coefficient": 25.0, "u_factor_tag": "WindowFrame"},
        ],
    )
    thmz = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m_res["target"],
        export_only=True,
        run_id="ff_syn_res",
    )
    thmz_abs = Path(garden_root) / thmz["summary_view"]["path"]
    _inject_synthetic_therm_results(thmz_abs)

    vec_res = _call_tool(
        mcp_server,
        "FF_Read_Results",
        garden_root=garden_root,
        thmz_target=thmz["thmz_target"],
        data_type="heat_flux_vectors",
        include_values=True,
    )
    assert vec_res["summary_view"]["vector_count"] == 4
    assert len(vec_res["vectors"]) == 4

    cond_res = _call_tool(
        mcp_server,
        "FF_Read_Results",
        garden_root=garden_root,
        thmz_target=thmz["thmz_target"],
        model_target=m_res["target"],
        data_type="condensation_risk",
        interior_temp_c=20.0,
        interior_rh=50.0,
        exterior_temp_c=0.0,
    )
    assert cond_res["summary_view"]["status"] == "ok"
    assert cond_res["condensation_risk_analysis"]["min_interior_surface_temp_c"] == pytest.approx(11.5, abs=0.01)
    assert cond_res["condensation_risk_analysis"]["condensation_risk"] is False  # Td~9.27C < 11.5C
    assert 0.5 < cond_res["condensation_risk_analysis"]["f_rsi"] < 0.65

    psi_res = _call_tool(
        mcp_server,
        "FF_Read_Results",
        garden_root=garden_root,
        thmz_target=thmz["thmz_target"],
        data_type="psi_factor",
        u_factor_name="WindowFrame",
        projection="total",
        clear_field_u_values=[{"name": "WallClear", "u_value": 0.5, "length": 0.5}],
    )
    # L_2D = 1.8 * (500/1000) = 0.90 W/mK; clear_field = 0.5 * 0.5 = 0.25 => Psi = 0.65
    assert psi_res["psi_factor"]["psi_w_per_mk"] == pytest.approx(0.65, abs=1e-5)
