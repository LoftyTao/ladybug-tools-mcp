"""Regression tests for P0-7b, P0-7c, and Wave 2 comfort/visualization schema slimming."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import time
from typing import Any
import xml.etree.ElementTree as ET

from fastmcp import Client, FastMCP
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.temperature import Temperature
from ladybug.header import Header
from ladybug_display.visualization import AnalysisGeometry, VisualizationData, VisualizationSet
from ladybug_geometry.geometry3d import Mesh3D, Point3D
import pytest

from garden.manifest import GardenManifest
from garden.visualize.artifacts import (
    coerce_legend_parameter_dict,
    export_visualization_set,
    save_visualization_set,
    visualization_set_to_svg,
)
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.server import create_mcp

REPO_ROOT = Path(__file__).resolve().parents[1]
CHICAGO_EPW = REPO_ROOT / "resources" / "ladybug" / "tests" / "assets" / "epw" / "chicago.epw"


def _init_garden(tmp_path: Path, name: str = "comfort_viz_test") -> Path:
    root = tmp_path / "garden"
    root.mkdir(parents=True, exist_ok=True)
    GardenManifest.new(name).write(root)
    return root


def _copy_chicago_epw(garden_root: Path) -> Path:
    weather_dir = garden_root / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    epw_dst = weather_dir / "chicago.epw"
    shutil.copy2(CHICAGO_EPW, epw_dst)
    return epw_dst


async def _call(client: Client, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool_name, args)
    return json.loads(result.content[0].text)


def _make_direct_mcp() -> FastMCP:
    mcp = FastMCP("test-comfort-viz", strict_input_validation=True)
    register_tools(mcp)
    return mcp


def _sample_grid_mesh(nx: int, ny: int, *, spacing: float = 1.0) -> Mesh3D:
    vertices: list[Point3D] = []
    for iy in range(ny + 1):
        for ix in range(nx + 1):
            vertices.append(Point3D(ix * spacing, iy * spacing, 0.0))
    faces: list[tuple[int, int, int, int]] = []
    stride = nx + 1
    for iy in range(ny):
        for ix in range(nx):
            i0 = iy * stride + ix
            faces.append((i0, i0 + 1, i0 + stride + 1, i0 + stride))
    return Mesh3D(vertices, faces)


def test_adaptive_epw_shortcut_and_missing_args_guard(tmp_path: Path) -> None:
    """Adaptive comfort supports weather_target/epw_path shortcut and preserves required-args guard."""
    root = _init_garden(tmp_path)
    epw_dst = _copy_chicago_epw(root)

    async def _run() -> None:
        mcp = _make_direct_mcp()
        async with Client(mcp) as client:
            epw_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": str(root),
                    "model": "adaptive",
                    "epw_path": str(epw_dst),
                    "identifier": "adaptive_epw_path",
                },
            )
            sv = epw_res["summary_view"]
            assert epw_res["target"]["target_type"] == "ladybug_data_collection"
            assert sv["method"]["comfort_index"] == "Adaptive"
            assert sv["method"]["epw_shortcut_used"] is True
            assert sv["assumptions"]["outdoor_temperature_source"] == "epw_dry_bulb_temperature"
            assert sv["assumptions"]["operative_temperature_source"] == "assumed_operative_equals_outdoor_dry_bulb"
            assert sv["assumptions"]["operative_equals_outdoor_dry_bulb"] is True
            assert "outdoor_dry_bulb" in sv["assumptions"]["baseline_note"]
            assert sv["applicable_scope"]["domain"] == "naturally_ventilated_or_free_running_buildings"

            weather_res = await _call(
                client,
                "LB_Manage_Weather",
                {
                    "garden_root": str(root),
                    "action": "import",
                    "source_path": str(epw_dst),
                    "identifier": "chi",
                },
            )
            weather_target = weather_res.get("weather_target") or weather_res["target"]
            wt_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": str(root),
                    "model": "adaptive",
                    "weather_target": weather_target,
                    "identifier": "adaptive_weather_target",
                },
            )
            assert wt_res["summary_view"]["method"]["epw_shortcut_used"] is True
            assert wt_res["summary_view"]["percentages"] == sv["percentages"]

            with pytest.raises(Exception, match="Adaptive comfort requires"):
                await _call(
                    client,
                    "LB_Calculate_Comfort",
                    {
                        "garden_root": str(root),
                        "model": "adaptive",
                    },
                )

    asyncio.run(_run())


def test_comfort_methodology_fields_and_passive_strategy_semantics(tmp_path: Path) -> None:
    """All comfort models expose method/assumptions/applicable_scope, with clear passive_strategy semantics."""
    root = _init_garden(tmp_path)
    epw_dst = _copy_chicago_epw(root)

    async def _run() -> None:
        mcp = _make_direct_mcp()
        async with Client(mcp) as client:
            for model_name in ("pmv", "utci", "pet", "solarcal"):
                res = await _call(
                    client,
                    "LB_Calculate_Comfort",
                    {
                        "garden_root": str(root),
                        "model": model_name,
                        "epw_path": str(epw_dst),
                        "identifier": f"check_{model_name}",
                    },
                )
                sv = res["summary_view"]
                assert isinstance(sv.get("method"), dict) and sv["method"]
                assert isinstance(sv.get("assumptions"), dict) and sv["assumptions"]
                assert isinstance(sv.get("applicable_scope"), dict) and sv["applicable_scope"]

            scalar_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": str(root),
                    "model": "indoor_solar_mrt",
                    "solar_altitude": 45.0,
                    "direct_normal_solar": 600.0,
                    "diffuse_horizontal_solar": 120.0,
                    "longwave_mrt": 22.0,
                },
            )
            scalar_sv = scalar_res["summary_view"]
            assert scalar_sv["method"]["comfort_index"] == "IndoorSolarCal"
            assert scalar_sv["assumptions"]["window_transmittance"] == pytest.approx(0.4)
            assert scalar_sv["applicable_scope"]["domain"] == "indoor_solar_mean_radiant_temperature"

            ps_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": str(root),
                    "model": "passive_strategy",
                    "epw_path": str(epw_dst),
                    "strategies": ["natural_ventilation", "night_flush", "passive_solar"],
                    "identifier": "ps_chi",
                },
            )
            ps_sv = ps_res["summary_view"]
            ps_method = ps_sv["method"]
            ps_scope = ps_sv["applicable_scope"]
            assert ps_method["hourly_combination_rule"] == "hourly_boolean_union_or"
            assert ps_method["combined_total_comfort_percent"] <= ps_method["additive_strategy_sum_percent"]
            assert "fan_use" in ps_method["strategy_semantics"]
            assert "night_flush" in ps_method["strategy_semantics"]
            assert "natural_ventilation" in ps_method["strategy_semantics"]["fan_use"]
            assert "fan_use" in ps_scope["fan_use_vs_natural_ventilation"]

    asyncio.run(_run())


def test_analyze_data_collection_degree_days_routing(tmp_path: Path) -> None:
    """LB_Analyze_Data_Collection supports degree_days via action='aggregate', 'degree_days', and 'math'."""
    root = _init_garden(tmp_path)
    vals = [10.0, 15.0, 20.0, 25.0, 30.0, 18.0] * 4

    async def _run() -> None:
        mcp = _make_direct_mcp()
        async with Client(mcp) as client:
            created = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": str(root),
                    "action": "create",
                    "values": vals,
                    "data_type": "Temperature",
                    "unit": "C",
                    "collection_type": "HourlyContinuous",
                    "analysis_period": {"st_month": 1, "st_day": 1, "st_hour": 0, "end_month": 1, "end_day": 1, "end_hour": 23},
                    "identifier": "temp_series",
                },
            )
            dc_target = created["target"]

            agg_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": str(root),
                    "action": "aggregate",
                    "operation": "degree_days",
                    "data_collection_target": dc_target,
                    "degree_day_type": "both",
                    "identifier": "dd_agg",
                },
            )
            math_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": str(root),
                    "action": "math",
                    "operation": "degree_days",
                    "data_collection_target": dc_target,
                    "degree_day_type": "both",
                    "identifier": "dd_math",
                },
            )
            direct_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": str(root),
                    "action": "degree_days",
                    "data_collection_target": dc_target,
                    "degree_day_type": "heating",
                    "base_temperature": 18.0,
                    "identifier": "dd_direct",
                },
            )

            assert agg_res["summary_view"]["degree_days"]["heating"]["degree_days_total"] == pytest.approx(
                math_res["summary_view"]["degree_days"]["heating"]["degree_days_total"]
            )
            assert agg_res["summary_view"]["degree_days"]["cooling"]["degree_days_total"] == pytest.approx(
                math_res["summary_view"]["degree_days"]["cooling"]["degree_days_total"]
            )
            assert direct_res["summary_view"]["degree_days"]["heating"]["degree_days_total"] == pytest.approx(
                agg_res["summary_view"]["degree_days"]["heating"]["degree_days_total"]
            )

    asyncio.run(_run())


def test_coerce_legend_parameter_dict_edge_cases(tmp_path: Path) -> None:
    """coerce_legend_parameter_dict auto-injects missing types, 2D CSS strings, and categorized defaults."""
    plain = coerce_legend_parameter_dict({"color_set": "Nuanced", "segment_count": 7})
    assert plain is not None and plain["type"] == "LegendParameters"
    assert plain["segment_count"] == 7

    empty_type = coerce_legend_parameter_dict({"type": "", "title": "Temp"})
    assert empty_type is not None and empty_type["type"] == "LegendParameters"

    prop2d = coerce_legend_parameter_dict({"properties_2d": {"origin_x": "10px"}})
    assert prop2d is not None and prop2d["type"] == "LegendParameters"
    assert prop2d["properties_2d"]["type"] == "Legend2DParameters"

    css_dims = coerce_legend_parameter_dict(
        {"segment_height": "25px", "segment_width": "12px", "text_height": "10px"}
    )
    assert css_dims is not None and css_dims["type"] == "LegendParameters"
    assert css_dims["properties_2d"]["segment_height"] == "25px"

    categorized = coerce_legend_parameter_dict(
        {"domain": [10.0, 20.0], "category_names": ["Cold", "Comfy", "Hot"]}
    )
    assert categorized is not None and categorized["type"] == "LegendParametersCategorized"
    assert len(categorized["colors"]) == 3

    categorized_auto = coerce_legend_parameter_dict({"domain": [0, 10, 20]})
    assert categorized_auto is not None and categorized_auto["type"] == "LegendParametersCategorized"
    assert len(categorized_auto["colors"]) == 4

    # Inline VisualizationSet with legend_parameters missing 'type' still exports cleanly.
    root = _init_garden(tmp_path)
    mesh = _sample_grid_mesh(2, 2, spacing=2.0)
    ag = AnalysisGeometry("grid", [mesh], [VisualizationData([1.0, 2.0, 3.0, 4.0])])
    vs_dict = VisualizationSet("inline_leg", [ag]).to_dict()
    vs_dict["geometry"][0]["data_sets"][0]["legend_parameters"] = {
        "min": 0.0,
        "max": 5.0,
        "segment_count": 5,
    }
    svg_res = export_visualization_set(
        garden_root=str(root),
        export_format="svg",
        visualization_set=vs_dict,
        name="inline_no_type_legend",
    )
    assert Path(svg_res["artifact_receipt"]["absolute_path"]).is_file()


def test_svg_auto_crop_viewbox_preserves_content_and_shrinks_whitespace(tmp_path: Path) -> None:
    """SVG export tight-crops viewBox around small geometry, legends, and rotated chart text."""
    root = _init_garden(tmp_path)
    mesh = _sample_grid_mesh(1, 5, spacing=2.0)
    ag = AnalysisGeometry(
        "narrow_mesh",
        [mesh],
        [VisualizationData(list(range(5)))],
        display_mode="SurfaceWithEdges",
    )
    vs_mesh = VisualizationSet("narrow_mesh", [ag]).to_dict()

    async def _run() -> None:
        mcp = _make_direct_mcp()
        async with Client(mcp) as client:
            uncropped = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": str(root),
                    "export_format": "svg",
                    "visualization_set": vs_mesh,
                    "width": 1600,
                    "height": 900,
                    "auto_crop": False,
                    "name": "mesh_uncropped",
                },
            )
            cropped = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": str(root),
                    "export_format": "svg",
                    "visualization_set": vs_mesh,
                    "width": 1600,
                    "height": 900,
                    "auto_crop": True,
                    "name": "mesh_cropped",
                },
            )
            uncrop_svg = ET.fromstring(Path(uncropped["artifact_receipt"]["absolute_path"]).read_text("utf-8"))
            crop_svg = ET.fromstring(Path(cropped["artifact_receipt"]["absolute_path"]).read_text("utf-8"))

            assert uncrop_svg.attrib["width"] == "1600"
            assert uncrop_svg.attrib["height"] == "900"
            assert "viewBox" in crop_svg.attrib
            vx, vy, vw, vh = (float(x) for x in crop_svg.attrib["viewBox"].split())
            assert vw < 1000 and vh <= 900
            assert vw * vh < 0.60 * 1600 * 900
            assert cropped["summary_view"]["auto_crop"] is True
            assert cropped["summary_view"]["canvas_width"] == 1600
            assert cropped["summary_view"]["canvas_height"] == 900
            assert cropped["summary_view"]["width"] == int(vw)
            assert cropped["summary_view"]["height"] == int(vh)

            # Verify every rect & text anchor falls inside viewBox (nothing clipped).
            def _strip_ns(tag: str) -> str:
                return tag.split("}")[-1]

            for elem in crop_svg.iter():
                tag = _strip_ns(elem.tag)
                if tag == "rect":
                    rx = float(elem.attrib.get("x", 0.0))
                    ry = float(elem.attrib.get("y", 0.0))
                    rw = float(elem.attrib.get("width", 0.0))
                    rh = float(elem.attrib.get("height", 0.0))
                    assert vx <= rx and rx + rw <= vx + vw
                    assert vy <= ry and ry + rh <= vy + vh
                elif tag == "text" and (elem.text or "").strip():
                    tx = float(elem.attrib.get("x", 0.0))
                    ty = float(elem.attrib.get("y", 0.0))
                    assert vx <= tx <= vx + vw
                    assert vy <= ty <= vy + vh

            # Also verify MonthlyChart with rotated Y-axis text keeps all labels inside cropped viewBox.
            col = HourlyContinuousCollection(Header(Temperature(), "C", AnalysisPeriod()), [21.5] * 8760)
            chart_vs = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": str(root),
                    "chart_type": "monthly_chart",
                    "series": [{"data_collection": col.to_dict(), "name": "DBT"}],
                    "chart_title": "Monthly Dry Bulb",
                    "y_axis_title": "Temperature (C)",
                },
            )
            chart_svg_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": str(root),
                    "export_format": "svg",
                    "visualization_set": chart_vs["visualization_set"],
                    "width": 1600,
                    "height": 900,
                    "auto_crop": True,
                    "name": "chart_cropped",
                },
            )
            chart_svg = ET.fromstring(Path(chart_svg_res["artifact_receipt"]["absolute_path"]).read_text("utf-8"))
            cvx, cvy, cvw, cvh = (float(x) for x in chart_svg.attrib["viewBox"].split())
            assert cvw * cvh < 0.85 * 1600 * 900
            for elem in chart_svg.iter():
                if _strip_ns(elem.tag) == "text" and (elem.text or "").strip():
                    tx = float(elem.attrib.get("x", 0.0))
                    ty = float(elem.attrib.get("y", 0.0))
                    assert cvx <= tx <= cvx + cvw
                    assert cvy <= ty <= cvy + cvh

    asyncio.run(_run())


def test_dense_mesh_svg_export_performance_and_cleanup(tmp_path: Path) -> None:
    """Dense Mesh3D SVG export runs in linear time without leaking patched _group_child."""
    import ladybug_display._svg_order as svg_order

    orig_fn = svg_order._group_child
    root = _init_garden(tmp_path)
    mesh = _sample_grid_mesh(50, 40, spacing=0.5)  # 2,000 faces
    ag = AnalysisGeometry(
        "dense_therm",
        [mesh],
        [VisualizationData([float(i % 20) for i in range(len(mesh.faces))])],
        display_mode="SurfaceWithEdges",
    )
    vs_dict = VisualizationSet("dense", [ag]).to_dict()

    started = time.perf_counter()
    res = visualization_set_to_svg(
        garden_root=str(root),
        visualization_set=vs_dict,
        name="dense_mesh",
    )
    elapsed = time.perf_counter() - started

    assert Path(res["artifact_receipt"]["absolute_path"]).is_file()
    assert elapsed < 5.0
    assert svg_order._group_child is orig_fn


def test_source_run_id_propagation_to_exported_artifacts(tmp_path: Path) -> None:
    """Exporting a VisualizationSet propagates source_run_id to artifact source and summary_view."""
    root = _init_garden(tmp_path)
    mesh = _sample_grid_mesh(2, 2, spacing=1.0)
    ag = AnalysisGeometry("run_mesh", [mesh], [VisualizationData([1.0, 2.0, 3.0, 4.0])])
    vs_dict = VisualizationSet("run_tagged", [ag]).to_dict()
    vs_dict["user_data"] = {"source_run_id": "run_abc_789"}

    saved = save_visualization_set(
        garden_root=str(root),
        visualization_set=vs_dict,
        name="run_tagged_vs",
    )
    assert saved["artifact"]["source"]["source_run_id"] == "run_abc_789"
    target = saved["visualization_set_target"]

    for fmt in ("svg", "html", "vsf"):
        exp = export_visualization_set(
            garden_root=str(root),
            export_format=fmt,
            visualization_set_target=target,
            name=f"run_tagged_{fmt}",
        )
        assert exp["summary_view"]["source_run_id"] == "run_abc_789"
        assert exp["artifact_receipt"]["source"]["source_run_id"] == "run_abc_789"
        assert exp["summary_view"]["artifact"]["source"]["source_run_id"] == "run_abc_789"


def test_wave2_schema_slimming_and_chart_backwards_compat(tmp_path: Path) -> None:
    """Slimmed schemas hit >=40% reduction while preserving kwargs, defaults, and CodeMode get_schema."""
    baselines_compact = {
        "LB_Calculate_Comfort": 14429,
        "LB_Analyze_Data_Collection": 7313,
        "LB_Chart_To_Visualization_Set": 10577,
    }
    expected_kwargs = {
        "LB_Calculate_Comfort": {
            "garden_root",
            "model",
            "weather_target",
            "epw_path",
            "outdoor_temperature_target",
            "operative_temperature_target",
            "strategies",
            "passive_strategy_parameters",
            "return_data_collection",
        },
        "LB_Analyze_Data_Collection": {
            "garden_root",
            "action",
            "operation",
            "degree_day_type",
            "heating_base_temperature",
            "cooling_base_temperature",
            "return_data_collection",
        },
        "LB_Chart_To_Visualization_Set": {
            "chart_type",
            "export_format",
            "garden_root",
            "legend_parameter",
            "x_dim",
            "y_dim",
            "width",
            "height",
            "return_visualization_set",
            "series",
        },
    }

    root = _init_garden(tmp_path)
    col = HourlyContinuousCollection(Header(Temperature(), "C", AnalysisPeriod()), [22.0] * 8760)

    async def _run() -> None:
        mcp = _make_direct_mcp()
        tools = {t.name: t for t in await mcp.list_tools()}
        for name, base_bytes in baselines_compact.items():
            tool = tools[name]
            assert tool.description and tool.description.strip()
            props = tool.parameters.get("properties", {})
            assert expected_kwargs[name].issubset(props.keys())
            for pname, pschema in props.items():
                assert pschema.get("description", "").strip(), f"{name}.{pname} missing description"
            compact_bytes = len(json.dumps(tool.parameters, separators=(",", ":")).encode("utf-8"))
            reduction = 1.0 - (compact_bytes / base_bytes)
            assert reduction >= 0.40, f"{name} reduced only {reduction:.1%} ({compact_bytes} vs {base_bytes})"

        assert "auto_crop" in tools["LB_Export_Visualization_Set"].parameters["properties"]
        assert "degree_days" in tools["LB_Analyze_Data_Collection"].parameters["properties"]["action"]["enum"]

        # Verify CodeMode get_schema(detail="full") works cleanly on slimmed tools.
        async with Client(create_mcp()) as cm_client:
            cm_res = await cm_client.call_tool(
                "get_schema",
                {"tools": list(baselines_compact.keys()), "detail": "full"},
            )
            assert cm_res.content and "LB_Calculate_Comfort" in cm_res.content[0].text

        async with Client(mcp) as client:
            # Default return_visualization_set=True is preserved for existing callers.
            chart_default = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "chart_type": "hourly_plot",
                    "data_collection": col.to_dict(),
                    "width": 1200,
                    "height": 700,
                },
            )
            assert isinstance(chart_default.get("visualization_set"), dict)
            assert "LB_Export_Visualization_Set" in chart_default["summary_view"]["export_dimensions_note"]

            # return_visualization_set=False omits VisualizationSet payload cleanly.
            chart_compact = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": str(root),
                    "chart_type": "hourly_plot",
                    "data_collection": col.to_dict(),
                    "return_visualization_set": False,
                },
            )
            assert chart_compact.get("visualization_set") is None
            assert isinstance(chart_compact["summary_view"], dict)

    asyncio.run(_run())
