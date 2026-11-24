"""Comprehensive tests for Ladybug/comfort/climate/visualization upgrades and bug fixes."""

from __future__ import annotations

import asyncio
import json
import pickle
import shutil
from pathlib import Path
from typing import Any

from fastmcp import Client, FastMCP
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from ladybug.datatype.temperature import DryBulbTemperature
from ladybug.location import Location
from ladybug_display.visualization import VisualizationSet
from ladybug_geometry.geometry3d import Face3D, Mesh3D, Plane, Point3D, Vector3D
from ladybug_radiance.skymatrix import SkyMatrix
from PIL import Image
import pytest

from garden.radiance.sky import create_sky_matrix
from ladybug_tools_mcp.registry import register_tools


REPO_ROOT = Path(__file__).resolve().parents[1]
CHICAGO_EPW = REPO_ROOT / "resources" / "ladybug" / "tests" / "assets" / "epw" / "chicago.epw"
CHICAGO_STAT = REPO_ROOT / "resources" / "ladybug" / "tests" / "assets" / "stat" / "chicago.stat"
CHICAGO_DDY = REPO_ROOT / "resources" / "ladybug" / "tests" / "assets" / "ddy" / "chicago.ddy"


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
    return _parse_tool_result(res)


@pytest.fixture(scope="module")
def raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "Ladybug Viz Upgrades Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


def _copy_chicago_bundle(dest_dir: Path) -> tuple[Path, Path, Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    epw_dst = dest_dir / "chicago.epw"
    stat_dst = dest_dir / "chicago.stat"
    ddy_dst = dest_dir / "chicago.ddy"
    shutil.copy2(CHICAGO_EPW, epw_dst)
    shutil.copy2(CHICAGO_STAT, stat_dst)
    shutil.copy2(CHICAGO_DDY, ddy_dst)
    return epw_dst, stat_dst, ddy_dst


def _sample_vis_set(name: str, box_x: float, shared_ctx_id: str, unique_id: str) -> dict[str, Any]:
    face_shared = Face3D.from_rectangle(
        4.0,
        4.0,
        Plane(Vector3D(0.0, 0.0, 1.0), Point3D(box_x, 0.0, 0.0)),
    )
    face_unique = Face3D.from_rectangle(
        2.0,
        2.0,
        Plane(Vector3D(0.0, 0.0, 1.0), Point3D(box_x, 10.0, 0.0)),
    )
    mesh = Mesh3D.from_face_vertices([face_unique.vertices])
    return {
        "type": "VisualizationSet",
        "identifier": name,
        "display_name": name,
        "units": "Meters",
        "geometry": [
            {
                "type": "ContextGeometry",
                "identifier": shared_ctx_id,
                "display_name": shared_ctx_id,
                "geometry": [
                    {
                        "type": "DisplayFace3D",
                        "geometry": face_shared.to_dict(),
                        "color": {"type": "Color", "r": 255 if box_x > 0 else 10, "g": 20, "b": 30, "a": 255},
                    }
                ],
            },
            {
                "type": "AnalysisGeometry",
                "identifier": unique_id,
                "display_name": unique_id,
                "geometry": [mesh.to_dict()],
                "data_sets": [
                    {
                        "type": "VisualizationData",
                        "values": [10.0 if box_x > 0 else 1.0],
                        "data_type": DryBulbTemperature().to_dict(),
                        "unit": "C",
                    }
                ],
            },
        ],
    }


def _create_box_model_dict() -> dict[str, Any]:
    room = Room.from_box("Zone1", width=4.0, depth=4.0, height=3.0)
    shade_face = Face3D(
        [
            Point3D(-0.5, -1.5, 3.2),
            Point3D(4.5, -1.5, 3.2),
            Point3D(4.5, 0.5, 3.2),
            Point3D(-0.5, 0.5, 3.2),
        ]
    )
    shade = Shade("Overhang_1", shade_face)
    model = Model("BoxStudyModel", rooms=[room], orphaned_shades=[shade], units="Meters")
    return model.to_dict()


def test_tool_registration_contains_new_and_upgraded_tools(raw_mcp: FastMCP) -> None:
    async def _run() -> set[str]:
        async with Client(raw_mcp) as client:
            tools = await client.list_tools()
            return {t.name for t in tools}

    tool_names = asyncio.run(_run())
    expected = {
        "LB_Analyze_Data_Collection",
        "LB_Climate_Calc",
        "LB_Calculate_Comfort",
        "LB_Data_Collection_To_File",
        "LB_Chart_To_Visualization_Set",
        "LB_Sky_To_Visualization_Set",
        "LB_Compose_Visualization_Sets",
        "LB_Export_Visualization_Set",
        "LB_Run_Solar_Geometry_Study",
    }
    assert expected.issubset(tool_names)


def test_bug_fixes_conflict_strategies_projections_and_cached_skymatrix(
    raw_mcp: FastMCP, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    garden_dir = tmp_path / "garden_bugs"
    epw_dst, _, _ = _copy_chicago_bundle(tmp_path / "weather_src")

    vs1 = _sample_vis_set("base_vs", box_x=0.0, shared_ctx_id="SharedCtx", unique_id="GridA")
    vs2 = _sample_vis_set("overlay_vs", box_x=5.0, shared_ctx_id="SharedCtx", unique_id="GridB")

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "bugs"})
            root = created["garden_root"]

            # 1. conflict_strategy = overwrite / skip / rename / error
            res_overwrite = await _call(
                client,
                "LB_Compose_Visualization_Sets",
                {
                    "garden_root": root,
                    "visualization_sets": [vs1, vs2],
                    "conflict_strategy": "overwrite",
                    "name": "composed_overwrite",
                    "return_visualization_set": True,
                },
            )
            geo_ow = res_overwrite["visualization_set"]["geometry"]
            ctx_ow = [g for g in geo_ow if g["identifier"] == "SharedCtx"]
            assert len(ctx_ow) == 1
            assert ctx_ow[0]["geometry"][0]["color"]["r"] == 255
            assert {g["identifier"] for g in geo_ow} == {"SharedCtx", "GridA", "GridB"}

            res_skip = await _call(
                client,
                "LB_Compose_Visualization_Sets",
                {
                    "garden_root": root,
                    "visualization_sets": [vs1, vs2],
                    "conflict_strategy": "skip",
                    "name": "composed_skip",
                    "return_visualization_set": True,
                },
            )
            geo_sk = res_skip["visualization_set"]["geometry"]
            ctx_sk = [g for g in geo_sk if g["identifier"] == "SharedCtx"]
            assert len(ctx_sk) == 1
            assert ctx_sk[0]["geometry"][0]["color"]["r"] == 10
            assert {g["identifier"] for g in geo_sk} == {"SharedCtx", "GridA", "GridB"}

            res_rename = await _call(
                client,
                "LB_Compose_Visualization_Sets",
                {
                    "garden_root": root,
                    "visualization_sets": [vs1, vs2],
                    "conflict_strategy": "rename",
                    "name": "composed_rename",
                    "return_visualization_set": True,
                },
            )
            ids_rn = [g["identifier"] for g in res_rename["visualization_set"]["geometry"]]
            assert len(ids_rn) == 4
            assert len(set(ids_rn)) == 4

            with pytest.raises(Exception):
                await _call(
                    client,
                    "LB_Compose_Visualization_Sets",
                    {
                        "garden_root": root,
                        "visualization_sets": [vs1, vs2],
                        "conflict_strategy": "error",
                        "name": "composed_error",
                    },
                )

            # 2. Import weather & build SkyMatrix
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            sky_res = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": root,
                    "asset_type": "sky_matrix",
                    "weather_target": w_target,
                    "compute": True,
                    "identifier": "chi_sky",
                },
            )
            sky_target = sky_res["target"]

            # Create benefit sky matrix before forbidding compute_sky, then verify reuse for BOTH
            sky_benefit = create_sky_matrix(
                garden_root=root,
                weather_target=w_target,
                identifier="chi_sky_benefit",
                hoys=[12, 13, 14, 4380, 4381],
                benefit_matrix=True,
                balance_temperature=15.0,
                compute=True,
            )

            # 3. Verify all 4 projections on sunpath & skydome
            for proj in ("Orthographic", "Stereographic", "Equidistant", "Equisolid"):
                sp = await _call(
                    client,
                    "LB_Sky_To_Visualization_Set",
                    {
                        "garden_root": root,
                        "sky_viz_type": "sunpath",
                        "weather_target": w_target,
                        "projection": proj,
                        "name": f"sp_{proj}",
                        "return_visualization_set": False,
                    },
                )
                assert sp["summary_view"]["projection"] == proj

            # 4. Cached SkyMatrix reuse (must NOT call SkyMatrix.compute_sky) + RadiationDome max_direction/max_info
            def _forbid_compute(self: Any) -> Any:
                raise AssertionError("SkyMatrix.compute_sky must not be called when cached values exist!")

            monkeypatch.setattr(SkyMatrix, "compute_sky", _forbid_compute)
            dome_res = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "radiation_dome",
                    "sky_matrix_target": sky_target,
                    "projection": "Equisolid",
                    "name": "cached_dome",
                    "return_visualization_set": True,
                },
            )
            summary = dome_res["summary_view"]
            assert summary["projection"] == "Equisolid"
            assert summary["used_cached_sky_matrix"] is True
            assert summary["max_direction"] is not None
            assert summary["max_info"] is not None
            assert "total_radiation" in summary

            dome_ben = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "radiation_dome",
                    "sky_matrix_target": sky_benefit["target"],
                    "projection": "Equidistant",
                    "name": "cached_benefit_dome",
                    "return_visualization_set": False,
                },
            )
            assert dome_ben["summary_view"]["used_cached_sky_matrix"] is True
            assert dome_ben["summary_view"]["projection"] == "Equidistant"

    asyncio.run(_run())


def test_analyze_data_collection_and_multifile_export(raw_mcp: FastMCP, tmp_path: Path) -> None:
    garden_dir = tmp_path / "garden_dc"
    temps = [5.0 + (h % 24) * 1.1 for h in range(8760)]
    rhs = [40.0 + (h % 24) * 1.5 for h in range(8760)]

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "dc_ops"})
            root = created["garden_root"]

            t_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "create",
                    "values": temps,
                    "data_type": "DryBulbTemperature",
                    "unit": "C",
                    "identifier": "dry_bulb",
                },
            )
            t_tgt = t_res["target"]

            rh_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "create",
                    "values": rhs,
                    "data_type": "RelativeHumidity",
                    "unit": "%",
                    "identifier": "rel_hum",
                },
            )
            rh_tgt = rh_res["target"]

            # Inspect
            insp = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "inspect",
                    "data_collection_target": t_tgt,
                    "percentiles": [10.0, 50.0, 90.0],
                    "histogram_bins": 5,
                    "include_values": True,
                    "max_values": 6,
                },
            )
            sv = insp["summary_view"]
            assert sv["value_count"] == 8760
            assert "p10" in sv["percentiles"]
            assert len(sv["histogram"]) == 5
            assert len(sv["values"]) == 6

            # Multi-collection & pkl export via LB_Data_Collection_To_File + import back
            csv_exp = await _call(
                client,
                "LB_Data_Collection_To_File",
                {
                    "garden_root": root,
                    "data_collection_targets": [t_tgt, rh_tgt],
                    "file_format": "csv",
                    "name": "multi_pair",
                },
            )
            pkl_exp = await _call(
                client,
                "LB_Data_Collection_To_File",
                {
                    "garden_root": root,
                    "data_collection_targets": [t_tgt, rh_tgt],
                    "file_format": "pkl",
                    "name": "multi_pair",
                },
            )
            json_exp = await _call(
                client,
                "LB_Data_Collection_To_File",
                {
                    "garden_root": root,
                    "data_collection_targets": [t_tgt, rh_tgt],
                    "file_format": "json",
                    "name": "multi_pair",
                },
            )
            assert Path(csv_exp["persistence_receipt"]["absolute_path"]).is_file()
            assert Path(pkl_exp["persistence_receipt"]["absolute_path"]).is_file()
            assert Path(json_exp["persistence_receipt"]["absolute_path"]).is_file()
            assert csv_exp["summary_view"]["collection_count"] == 2

            for fmt_name, exp_res in [("csv", csv_exp), ("pkl", pkl_exp), ("json", json_exp)]:
                imp = await _call(
                    client,
                    "LB_Analyze_Data_Collection",
                    {
                        "garden_root": root,
                        "action": "import",
                        "source_path": exp_res["artifact"]["path"],
                        "identifier": f"reimp_{fmt_name}",
                    },
                )
                assert len(imp["targets"]) == 2

            # Filters: analysis_period, hoys, range, conditional_statement, pattern, multi-collection statement
            flt_ap = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "filter",
                    "filter_type": "analysis_period",
                    "data_collection_target": t_tgt,
                    "analysis_period": "6/1 to 6/30 between 9 and 17 @1",
                    "identifier": "june_day",
                },
            )
            assert flt_ap["summary_view"]["value_count"] == 30 * 9

            flt_rng = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "filter",
                    "filter_type": "range",
                    "data_collection_target": t_tgt,
                    "greater_than": 15.0,
                    "less_than": 25.0,
                },
            )
            assert 0 < flt_rng["summary_view"]["value_count"] < 8760

            flt_stmt = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "filter",
                    "filter_type": "statement",
                    "data_collection_targets": [t_tgt, rh_tgt],
                    "conditional_statement": "a > 15 and b < 65",
                    "identifier": "aligned_flt",
                },
            )
            assert len(flt_stmt["targets"]) == 2

            flt_hoys = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "filter",
                    "filter_type": "hoys",
                    "data_collection_target": t_tgt,
                    "hoys": [12.0, 4000.0],
                },
            )
            assert flt_hoys["summary_view"]["value_count"] == 2

            flt_pat = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "filter",
                    "filter_type": "pattern",
                    "data_collection_target": t_tgt,
                    "pattern": [True, False] * 4380,
                },
            )
            assert flt_pat["summary_view"]["value_count"] == 4380

            # Aggregations
            agg_daily = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "aggregate",
                    "operation": "daily",
                    "aggregation_method": "average",
                    "data_collection_target": t_tgt,
                },
            )
            assert agg_daily["summary_view"]["value_count"] == 365

            agg_mph = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "aggregate",
                    "operation": "monthly_per_hour",
                    "aggregation_method": "percentile",
                    "percentile_value": 90.0,
                    "data_collection_target": t_tgt,
                },
            )
            assert agg_mph["summary_view"]["value_count"] == 288

            energy_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "create",
                    "values": [100.0] * 8760,
                    "data_type": "Energy",
                    "unit": "Wh",
                    "identifier": "energy_series",
                },
            )
            e_tgt = energy_res["target"]

            for op_name, target_in, extra in [
                ("monthly", t_tgt, {"aggregation_method": "total"}),
                ("to_time_rate_of_change", e_tgt, {}),
                ("interpolate_to_timestep", t_tgt, {"timestep": 2}),
                ("convert_to_culled_timestep", t_tgt, {"timestep": 2}),
                ("normalize_by_area", e_tgt, {"area": 100.0}),
            ]:
                r = await _call(
                    client,
                    "LB_Analyze_Data_Collection",
                    {
                        "garden_root": root,
                        "action": "aggregate",
                        "operation": op_name,
                        "data_collection_target": target_in,
                        **extra,
                    },
                )
                assert r["target"] is not None

            # Math: units, arithmetic, degree_days
            ip_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "math",
                    "operation": "to_ip",
                    "data_collection_target": t_tgt,
                },
            )
            assert ip_res["summary_view"]["unit"] == "F"

            unit_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "math",
                    "operation": "to_unit",
                    "target_unit": "K",
                    "data_collection_target": t_tgt,
                },
            )
            assert unit_res["summary_view"]["unit"] == "K"

            add_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "math",
                    "operation": "+",
                    "scalar": 2.5,
                    "data_collection_target": t_tgt,
                },
            )
            assert pytest.approx(add_res["summary_view"]["min"], abs=1e-4) == min(temps) + 2.5

            dd_res = await _call(
                client,
                "LB_Analyze_Data_Collection",
                {
                    "garden_root": root,
                    "action": "math",
                    "operation": "degree_days",
                    "heating_base_temperature": 18.0,
                    "cooling_base_temperature": 22.0,
                    "degree_day_type": "both",
                    "data_collection_target": t_tgt,
                },
            )
            assert "heating" in dd_res["targets"]
            assert "cooling" in dd_res["targets"]

    asyncio.run(_run())


def test_climate_calc_full_actions(raw_mcp: FastMCP, tmp_path: Path) -> None:
    garden_dir = tmp_path / "garden_clim"
    epw_dst, _, _ = _copy_chicago_bundle(tmp_path / "clim_weather")

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "clim"})
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            # 1. inspect_weather (EPW + STAT + DDY)
            insp = await _call(
                client,
                "LB_Climate_Calc",
                {"garden_root": root, "action": "inspect_weather", "weather_target": w_target},
            )
            sv = insp["summary_view"]
            assert "epw" in sv and "stat" in sv and "ddy" in sv
            assert sv["epw"]["location"]["city"].lower().startswith("chicago")
            assert len(sv["ddy"]["design_days"]) >= 1

            # 2. translate_weather across EPW/STAT -> DDY/WEA/MOS
            for ttype in (
                "epw_to_ddy",
                "epw_to_ddy_monthly_cooling",
                "epw_to_wea",
                "epw_to_mos",
                "stat_to_ddy",
                "wea_from_stat",
                "wea_from_clear_sky",
                "wea_from_zhang_huang",
            ):
                tr = await _call(
                    client,
                    "LB_Climate_Calc",
                    {
                        "garden_root": root,
                        "action": "translate_weather",
                        "translation_type": ttype,
                        "weather_target": w_target,
                        "identifier": f"tr_{ttype}",
                    },
                )
                assert (Path(root) / tr["summary_view"]["artifact_path"]).is_file(), f"Missing output for {ttype}"

            # 3. write_epw & write_ddy
            w_epw = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "write_epw",
                    "weather_target": w_target,
                    "field_updates": {"dry_bulb_temperature": 21.0},
                    "comments_1": "Test comment 1",
                    "identifier": "modified_chi",
                },
            )
            assert (Path(root) / w_epw["summary_view"]["artifact_path"]).is_file()
            assert w_epw["target"]["target_type"] == "weather_file"

            w_ddy = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "write_ddy",
                    "weather_target": w_target,
                    "identifier": "filtered_ddy",
                },
            )
            assert (Path(root) / w_ddy["summary_view"]["artifact_path"]).is_file()

            # 4. sunpath
            sp = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "sunpath",
                    "weather_target": w_target,
                    "month": 6,
                    "day": 21,
                    "hour": 12.0,
                },
            )
            assert sp["summary_view"]["sun_count"] == 1
            assert sp["suns"][0]["altitude"] > 60.0
            assert sp["summary_view"]["sunrise_sunset"] is not None

            # 5. psychrometrics (scalar & DataCollection target)
            psy_s = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "psychrometrics",
                    "operation": "dew_point_from_db_rh",
                    "inputs": {"db_temp": 25.0, "rel_humid": 50.0},
                },
            )
            assert 12.0 < psy_s["value"] < 16.0

            dbt_col = await _call(
                client,
                "LB_Manage_Weather",
                {
                    "garden_root": root,
                    "action": "read_data",
                    "weather_target": w_target,
                    "data_type": "dry_bulb_temperature",
                    "identifier": "chi_dbt",
                },
            )
            psy_dc = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "psychrometrics",
                    "operation": "enthalpy_from_db_hr",
                    "inputs": {
                        "db_temp": dbt_col["target"],
                        "humid_ratio": 0.01,
                    },
                    "identifier": "chi_enth",
                },
            )
            assert psy_dc["target"]["target_type"] == "ladybug_data_collection"

            # 6. skymodel
            sky_zh = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "skymodel",
                    "operation": "zhang_huang_solar",
                    "inputs": {
                        "altitude": 45.0,
                        "cloud_cover": 3.0,
                        "relative_humidity": 50.0,
                        "dry_bulb_present": 22.0,
                        "dry_bulb_t3_hrs": 18.0,
                        "wind_speed": 3.0,
                    },
                },
            )
            assert sky_zh["global_horizontal_irradiance"] > 0.0

            sky_disc = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "skymodel",
                    "operation": "disc",
                    "inputs": {"ghi": 700.0, "altitude": 55.0, "doy": 172},
                },
            )
            assert sky_disc["direct_normal_irradiance"] >= 0.0

            # 7. wind_profile & magnetic_north
            wp = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "wind_profile",
                    "terrain": "city",
                    "wind_speed": 5.0,
                    "heights": [2.0, 10.0, 30.0],
                },
            )
            speeds = [pt["wind_speed"] for pt in wp["profile"]]
            assert speeds[0] < speeds[1] < speeds[2]

            mag = await _call(
                client,
                "LB_Climate_Calc",
                {
                    "garden_root": root,
                    "action": "magnetic_north",
                    "latitude": 41.78,
                    "longitude": -87.75,
                    "magnetic_north": 0.0,
                },
            )
            assert -20.0 < mag["magnetic_declination"] < 20.0

    asyncio.run(_run())


def test_calculate_comfort_upgrades_and_backward_compat(raw_mcp: FastMCP, tmp_path: Path) -> None:
    garden_dir = tmp_path / "garden_comfort"
    epw_dst, _, _ = _copy_chicago_bundle(tmp_path / "cmf_weather")

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "comfort"})
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            async def _read_epw_field(field: str, ident: str) -> dict[str, Any]:
                r = await _call(
                    client,
                    "LB_Manage_Weather",
                    {
                        "garden_root": root,
                        "action": "read_data",
                        "weather_target": w_target,
                        "data_type": field,
                        "identifier": ident,
                    },
                )
                return r["target"]

            dbt = await _read_epw_field("dry_bulb_temperature", "dbt")
            rh = await _read_epw_field("relative_humidity", "rh")
            ws = await _read_epw_field("wind_speed", "ws")
            dni = await _read_epw_field("direct_normal_radiation", "dni")
            dhi = await _read_epw_field("diffuse_horizontal_radiation", "dhi")
            ghi = await _read_epw_field("global_horizontal_radiation", "ghi")
            hir = await _read_epw_field("horizontal_infrared_radiation_intensity", "hir")

            # 1. Backward-compatible PMV (default single output without output_metrics)
            pmv_default = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "pmv",
                    "air_temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "mean_radiant_temperature_target": dbt,
                    "identifier": "pmv_def",
                },
            )
            assert pmv_default["target"]["target_type"] == "ladybug_data_collection"
            assert "output_targets" not in pmv_default["summary_view"]

            # 2. Multi-metric PMV
            pmv_multi = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "pmv",
                    "weather_target": w_target,
                    "output_metrics": [
                        "pmv",
                        "ppd",
                        "set",
                        "operative_temperature",
                        "is_comfortable",
                        "thermal_condition",
                        "discomfort_reason",
                        "cooling_effect",
                    ],
                    "identifier": "pmv_multi",
                },
            )
            out_tgts = pmv_multi["summary_view"]["output_targets"]
            for key in ("pmv", "ppd", "set", "operative_temperature", "is_comfortable", "thermal_condition"):
                assert key in out_tgts

            # 3. PET & UTCI weather shortcuts + UTCI category metrics
            pet_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "pet",
                    "weather_target": w_target,
                    "comfort_parameter": {"age": 30, "sex": 0.5, "height": 1.75},
                    "output_metrics": ["pet", "thermal_condition", "is_comfortable", "core_body_temperature"],
                    "identifier": "pet_epw",
                },
            )
            assert "core_body_temperature" in pet_res["summary_view"]["output_targets"]

            utci_res = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "utci",
                    "weather_target": w_target,
                    "output_metrics": ["utci", "thermal_condition_five_point", "thermal_condition_seven_point", "thermal_condition_eleven_point"],
                    "identifier": "utci_epw",
                },
            )
            assert "thermal_condition_seven_point" in utci_res["summary_view"]["output_targets"]
            assert "thermal_condition_eleven_point" in utci_res["summary_view"]["output_targets"]

            # 4. Adaptive.from_air_and_rad_temp
            adp_air = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "adaptive",
                    "outdoor_temperature_target": dbt,
                    "air_temperature_target": dbt,
                    "mean_radiant_temperature_target": dbt,
                    "output_metrics": ["operative_temperature", "is_comfortable", "degrees_from_neutral"],
                    "identifier": "adp_air_rad",
                },
            )
            assert "degrees_from_neutral" in adp_air["summary_view"]["output_targets"]

            # 5. SolarCal (outdoor, indoor, horizontal, horizontal_ref)
            loc_dict = Location(city="Chicago", latitude=41.78, longitude=-87.75, time_zone=-6).to_dict()
            for sc_type in ("outdoor", "indoor", "horizontal", "horizontal_ref"):
                sc_metrics = (
                    [
                        "mean_radiant_temperature",
                        "shortwave_mrt_delta",
                        "longwave_mrt_delta",
                        "effective_radiant_field",
                    ]
                    if sc_type == "outdoor"
                    else [
                        "mean_radiant_temperature",
                        "mrt_delta",
                        "effective_radiant_field",
                    ]
                )
                sc_args: dict[str, Any] = {
                    "garden_root": root,
                    "model": "solarcal",
                    "solarcal_type": sc_type,
                    "location": loc_dict,
                    "surface_temperatures": dbt,
                    "floor_reflectance": 0.25,
                    "output_metrics": sc_metrics,
                    "identifier": f"sc_{sc_type}",
                }
                if sc_type in ("outdoor", "indoor"):
                    sc_args.update(
                        {
                            "direct_normal_solar_target": dni,
                            "diffuse_horizontal_solar_target": dhi,
                            "horizontal_infrared_target": hir,
                        }
                    )
                    if sc_type == "indoor":
                        sc_args["window_transmittance"] = 0.65
                else:
                    sc_args.update(
                        {
                            "direct_horizontal_solar_target": ghi,
                            "diffuse_horizontal_solar_target": dhi,
                        }
                    )
                    if sc_type == "horizontal_ref":
                        sc_args["reflected_horizontal_solar_target"] = dhi
                sc_res = await _call(client, "LB_Calculate_Comfort", sc_args)
                assert "effective_radiant_field" in sc_res["summary_view"]["output_targets"]

            # 6. prevailing_temperature & clo_schiavon
            prev = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "prevailing_temperature",
                    "outdoor_temperature_target": dbt,
                    "avg_month": True,
                    "identifier": "prev_temp",
                },
            )
            assert prev["target"]["target_type"] == "ladybug_data_collection"

            clo = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "clo_schiavon",
                    "outdoor_temperature": 5.0,
                    "identifier": "clo_scalar",
                },
            )
            assert 0.45 <= clo["summary_view"]["clo_value"] <= 1.05

            # 7. local_discomfort (radiant_asymmetry_ppd, ankle_draft_ppd)
            ra = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "local_discomfort",
                    "local_discomfort_type": "radiant_asymmetry_ppd",
                    "radiant_temperature_difference": 8.0,
                    "asymmetry_type": "warm_ceiling",
                },
            )
            assert ra["summary_view"]["ppd"] > 0.0

            ad = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "local_discomfort",
                    "local_discomfort_type": "ankle_draft_ppd",
                    "predicted_mean_vote": 0.0,
                    "air_speed_at_ankle": 0.25,
                },
            )
            assert ad["summary_view"]["ppd"] > 0.0

            # 8. heat_stress (wbgt, hi, humidex, wc, at, di)
            for idx_name in ("wbgt", "hi", "humidex", "wc", "at", "di"):
                hs = await _call(
                    client,
                    "LB_Calculate_Comfort",
                    {
                        "garden_root": root,
                        "model": "heat_stress",
                        "heat_stress_index": idx_name,
                        "air_temperature_target": dbt,
                        "relative_humidity_target": rh,
                        "wind_speed_target": ws,
                        "mean_radiant_temperature_target": dbt,
                        "identifier": f"hs_{idx_name}",
                    },
                )
                assert hs["target"]["target_type"] == "ladybug_data_collection"

    asyncio.run(_run())


def test_run_solar_geometry_study(raw_mcp: FastMCP, tmp_path: Path) -> None:
    garden_dir = tmp_path / "garden_study"
    epw_dst, _, _ = _copy_chicago_bundle(tmp_path / "study_weather")

    study_face = Face3D(
        [
            Point3D(0.0, 0.0, 0.0),
            Point3D(4.0, 0.0, 0.0),
            Point3D(4.0, 4.0, 0.0),
            Point3D(0.0, 4.0, 0.0),
        ]
    ).to_dict()
    ctx_shade = Face3D(
        [
            Point3D(0.5, -1.0, 2.0),
            Point3D(3.5, -1.0, 2.0),
            Point3D(3.5, 2.0, 2.0),
            Point3D(0.5, 2.0, 2.0),
        ]
    ).to_dict()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "study"})
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            mdl_res = await _call(
                client,
                "HB_Create_Model",
                {
                    "garden_root": root,
                    "identifier": "box_study",
                    "add_objects": _create_box_model_dict()["rooms"],
                },
            )
            mdl_target = mdl_res["model_target"]

            # 1. DirectSunStudy
            ds = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "direct_sun",
                    "study_face": study_face,
                    "context_geometry": [ctx_shade],
                    "weather_target": w_target,
                    "analysis_period": "6/21 to 6/21 between 9 and 15 @1",
                    "grid_size": 2.0,
                    "include_values": True,
                    "name": "ds_june",
                },
            )
            assert ds["target"]["target_type"] == "visualization_set"
            assert ds["summary_view"]["study_type"] == "direct_sun"
            assert len(ds["summary_view"]["values"]) > 0

            # 2. RadiationStudy (standard & benefit=True)
            rad = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "radiation",
                    "study_face": study_face,
                    "context_geometry": [ctx_shade],
                    "weather_target": w_target,
                    "hoys": [12, 13, 14, 4380, 4381],
                    "grid_size": 2.0,
                    "benefit": True,
                    "name": "rad_benefit",
                },
            )
            assert rad["target"]["target_type"] == "visualization_set"
            assert rad["summary_view"]["benefit"] is True

            # 3. SolarEnvelope
            env = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "solar_envelope",
                    "study_face": study_face,
                    "context_geometry": [ctx_shade],
                    "weather_target": w_target,
                    "hoys": [12, 4380],
                    "grid_size": 2.0,
                    "name": "env_test",
                },
            )
            assert env["target"]["target_type"] == "visualization_set"
            assert env["summary_view"]["study_type"] == "solar_envelope"

            # 4. SkyIntersection with Honeybee model_target
            si = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "sky_intersection",
                    "model_target": mdl_target,
                    "weather_target": w_target,
                    "center_point": [2.0, -2.0, 1.5],
                    "name": "sky_int",
                },
            )
            assert si["target"]["target_type"] == "visualization_set"
            assert si["summary_view"]["study_type"] == "sky_intersection"

            # 5. ViewSphere study
            vs = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "view_sphere",
                    "context_geometry": [ctx_shade],
                    "center_point": [2.0, 0.0, 0.5],
                    "view_type": "SkyExposure",
                    "name": "vs_study",
                },
            )
            assert vs["target"]["target_type"] == "visualization_set"
            assert "view_average" in vs["summary_view"]

    asyncio.run(_run())


def test_visualization_upgrades_and_exports(raw_mcp: FastMCP, tmp_path: Path) -> None:
    garden_dir = tmp_path / "garden_viz"
    epw_dst, _, _ = _copy_chicago_bundle(tmp_path / "viz_weather")

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(client, "GD_Create", {"root_dir": str(garden_dir), "name": "viz"})
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]
            dbt = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {
                        "garden_root": root,
                        "action": "read_data",
                        "weather_target": w_target,
                        "data_type": "dry_bulb_temperature",
                        "identifier": "viz_dbt",
                    },
                )
            )["target"]
            rh = (
                await _call(
                    client,
                    "LB_Manage_Weather",
                    {
                        "garden_root": root,
                        "action": "read_data",
                        "weather_target": w_target,
                        "data_type": "relative_humidity",
                        "identifier": "viz_rh",
                    },
                )
            )["target"]
            mdl_res = await _call(
                client,
                "HB_Create_Model",
                {
                    "garden_root": root,
                    "identifier": "viz_box",
                    "add_objects": _create_box_model_dict()["rooms"],
                },
            )
            mdl_target = mdl_res["model_target"]
            sky_res = await _call(
                client,
                "RAD_Create_Sky_Asset",
                {
                    "garden_root": root,
                    "asset_type": "sky_matrix",
                    "weather_target": w_target,
                    "identifier": "viz_sky",
                },
            )
            sky_target = sky_res["target"]

            # 1. LB_Sky_To_Visualization_Set upgrades
            rose_shaded = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "radiation_rose",
                    "sky_matrix_target": sky_target,
                    "model_target": mdl_target,
                    "direction_count": 18,
                    "center_point": [2.0, -3.0, 1.5],
                    "legend_parameter": {"color_set": "Nuanced", "segment_count": 7},
                    "name": "rose_shaded",
                },
            )
            assert rose_shaded["summary_view"]["shaded"] is True

            dome_shaded = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "radiation_dome",
                    "sky_matrix_target": sky_target,
                    "model_target": mdl_target,
                    "center_point": [2.0, -3.0, 1.5],
                    "azimuth_count": 18,
                    "altitude_count": 6,
                    "name": "dome_shaded",
                    "return_visualization_set": False,
                },
            )
            assert dome_shaded["summary_view"]["shaded"] is True
            assert dome_shaded["target"]["target_type"] == "visualization_set"

            wp_vis = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "wind_profile",
                    "terrain": "city",
                    "meteorological_wind_speed": 6.0,
                    "name": "wp_vis",
                    "return_visualization_set": False,
                },
            )
            assert wp_vis["target"]["target_type"] == "visualization_set"

            vs_vis = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "view_sphere",
                    "view_type": "HorizontalRadial",
                    "name": "vs_vis",
                    "return_visualization_set": False,
                },
            )
            assert vs_vis["target"]["target_type"] == "visualization_set"

            cmp_vis = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "compass",
                    "north_angle": 15.0,
                    "projection": "Orthographic",
                    "name": "cmp_vis",
                    "return_visualization_set": False,
                },
            )
            assert cmp_vis["target"]["target_type"] == "visualization_set"

            sp_dc = await _call(
                client,
                "LB_Sky_To_Visualization_Set",
                {
                    "garden_root": root,
                    "sky_viz_type": "sunpath",
                    "weather_target": w_target,
                    "data_collection_targets": [dbt],
                    "legend_parameters": [{"color_set": "Ecotect"}],
                    "name": "sp_colored",
                    "return_visualization_set": False,
                },
            )
            assert sp_dc["summary_view"]["data_collection_count"] == 1

            # 2. LB_Chart_To_Visualization_Set upgrades
            adp_chart = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "adaptive_chart",
                    "outdoor_temperature_target": dbt,
                    "operative_temperature_target": dbt,
                    "name": "adp_chart",
                },
            )
            assert "comfortable" in adp_chart["summary_view"]["comfort_percentages"]

            psy_pmv = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "comfort_polygon": {
                        "type": "pmv",
                        "strategies": ["Natural Ventilation", "Thermal Mass"],
                        "shade_balance_temperature": 12.8,
                    },
                    "name": "psy_pmv",
                },
            )
            assert "comfort_polygon" in psy_pmv["summary_view"]

            psy_utci = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "comfort_polygon": {"type": "utci"},
                    "name": "psy_utci",
                },
            )
            assert psy_utci["summary_view"]["comfort_polygon"]["model"] == "utci"

            # HourlyPlot extras + LegendParametersCategorized
            hp = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "hourly_plot",
                    "data_collection_target": dbt,
                    "z_dim": 2.0,
                    "reverse_y": True,
                    "custom_hours": [0, 6, 12, 18, 24],
                    "legend_parameter": {
                        "type": "LegendParametersCategorized",
                        "domain": [0, 15, 25],
                        "color_set": "Nuanced",
                        "category_names": ["Cold", "Cool", "Warm", "Hot"],
                    },
                    "name": "hp_cat",
                },
            )
            assert hp["target"]["target_type"] == "visualization_set"

            # MonthlyChart y_axis_min / y_axis_max + Legend3DParameters
            mc = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "monthly_chart",
                    "series": [{"data_collection_target": dbt, "label": "DBT"}],
                    "y_axis_min": -30.0,
                    "y_axis_max": 45.0,
                    "legend_parameter": {
                        "type": "Legend3DParameters",
                        "color_set": "Original",
                    },
                    "name": "mc_bounds",
                },
            )
            assert mc["target"]["target_type"] == "visualization_set"

            # 3. LB_Export_Visualization_Set upgrades (png, vtk, vtp, vsf, pkl, svg margin + Plane)
            dome_tgt = dome_shaded["target"]

            png_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "png",
                    "visualization_set_target": dome_tgt,
                    "width": 400,
                    "height": 300,
                    "name": "dome_preview",
                },
            )
            png_path = Path(png_res["artifact_receipt"]["absolute_path"])
            assert png_path.is_file()
            with Image.open(png_path) as im:
                assert im.size == (400, 300)

            vtk_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "vtk",
                    "visualization_set_target": dome_tgt,
                    "name": "dome_vtk",
                },
            )
            vtk_path = Path(vtk_res["artifact_receipt"]["absolute_path"])
            assert vtk_path.is_file()
            assert vtk_path.stat().st_size > 100

            vtp_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "vtp",
                    "visualization_set_target": dome_tgt,
                    "name": "dome_vtp",
                },
            )
            assert Path(vtp_res["artifact_receipt"]["absolute_path"]).is_file()

            vsf_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "vsf",
                    "visualization_set_target": dome_tgt,
                    "name": "dome_vsf",
                },
            )
            vs_reloaded = VisualizationSet.from_file(vsf_res["artifact_receipt"]["absolute_path"])
            assert len(vs_reloaded.geometry) >= 1

            pkl_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "pkl",
                    "visualization_set_target": dome_tgt,
                    "name": "dome_pkl",
                },
            )
            unpickled = VisualizationSet.from_pkl(pkl_res["artifact_receipt"]["absolute_path"])
            assert isinstance(unpickled, VisualizationSet)

            svg_res = await _call(
                client,
                "LB_Export_Visualization_Set",
                {
                    "garden_root": root,
                    "export_format": "svg",
                    "visualization_set_target": sp_dc["target"],
                    "margin": 15.0,
                    "view": {"type": "Plane", "n": [0.0, 0.0, 1.0], "o": [0.0, 0.0, 0.0]},
                    "name": "sp_plane_svg",
                },
            )
            assert Path(svg_res["artifact_receipt"]["absolute_path"]).is_file()

    asyncio.run(_run())
