"""End-to-end tests for passive strategy, indoor/outdoor solar MRT, chart overlays, and solar/view geometry studies."""

from __future__ import annotations

import asyncio
import json
import math
import shutil
from pathlib import Path
from typing import Any

from fastmcp import Client, FastMCP
from ladybug.location import Location
from ladybug_geometry.geometry3d import Face3D, Point3D
import pytest

from ladybug_tools_mcp.registry import register_tools


REPO_ROOT = Path(__file__).resolve().parents[1]
CHICAGO_EPW = REPO_ROOT / "resources" / "ladybug" / "tests" / "assets" / "epw" / "chicago.epw"


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
        "Comfort Passive Solar Studies Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


def _copy_chicago_epw(dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    epw_dst = dest_dir / "chicago.epw"
    shutil.copy2(CHICAGO_EPW, epw_dst)
    return epw_dst


def test_calculate_comfort_passive_strategy_and_solar_mrt(
    raw_mcp: FastMCP, tmp_path: Path
) -> None:
    garden_dir = tmp_path / "garden_comfort"
    epw_dst = _copy_chicago_epw(tmp_path / "weather")
    loc_dict = Location(
        city="Chicago", latitude=41.78, longitude=-87.75, time_zone=-6
    ).to_dict()

    # Large overhead shade roof blocking overhead sky & midday sun above [2, 2, 0]
    canopy_shade = Face3D(
        [
            Point3D(-3.0, -3.0, 2.5),
            Point3D(7.0, -3.0, 2.5),
            Point3D(7.0, 7.0, 2.5),
            Point3D(-3.0, 7.0, 2.5),
        ]
    ).to_dict()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(
                client, "GD_Create", {"root_dir": str(garden_dir), "name": "comfort"}
            )
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            async def _read_epw(field: str, ident: str) -> dict[str, Any]:
                res = await _call(
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
                return res["target"]

            dbt = await _read_epw("dry_bulb_temperature", "dbt")
            rh = await _read_epw("relative_humidity", "rh")
            ghi = await _read_epw("global_horizontal_radiation", "ghi")

            # 1. passive_strategy via weather_target shortcut
            ps_epw = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "passive_strategy",
                    "weather_target": w_target,
                    "output_metrics": [
                        "total_comfort",
                        "comfort",
                        "evaporative_cooling",
                        "night_flush",
                        "fan_use",
                        "internal_heat",
                        "passive_solar",
                    ],
                    "identifier": "ps_epw",
                },
            )
            assert ps_epw["target"]["target_type"] == "ladybug_data_collection"
            sv = ps_epw["summary_view"]
            assert sv["comfort_model"] == "PassiveStrategy"
            assert sv["baseline_comfort_percent"] < sv["total_comfort_percent"]
            assert math.isclose(
                sv["passive_gain_percent"],
                sv["total_comfort_percent"] - sv["baseline_comfort_percent"],
                rel_tol=1e-6,
            )
            for key in (
                "evaporative_cooling",
                "night_flush",
                "fan_use",
                "internal_heat",
                "passive_solar",
            ):
                assert key in sv["strategy_percents"]
                assert key in sv["output_targets"]

            # 2. passive_strategy via explicit DataCollections + custom PassiveStrategyParameters & Grasshopper aliases
            ps_custom = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "passive_strategy",
                    "air_temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "outdoor_temperature_target": dbt,
                    "incident_irradiance_target": ghi,
                    "strategies": [
                        "Capture Internal Heat",
                        "Occupant Use of Fans",
                        "Mass + Night Vent",
                        "Passive Solar Heating",
                    ],
                    "passive_strategy_parameters": {
                        "day_above_comfort": 14.0,
                        "night_below_comfort": 2.5,
                        "fan_air_speed": 1.2,
                        "balance_temperature": 12.0,
                        "solar_heat_capacity": 45.0,
                        "time_constant": 10,
                    },
                    "identifier": "ps_custom",
                },
            )
            csv_view = ps_custom["summary_view"]
            assert csv_view["passive_strategy_parameters"]["fan_air_speed"] == 1.2
            assert csv_view["passive_strategy_parameters"]["time_constant"] == 10
            assert set(csv_view["strategies_added"]) == {
                "internal_heat",
                "fan_use",
                "night_flush",
                "passive_solar",
            }

            # 3. indoor_solar_mrt (EPW shortcut, scalar, and human_position + context_geometry)
            in_epw = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "indoor_solar_mrt",
                    "weather_target": w_target,
                    "output_metrics": ["mrt", "dmrt", "erf"],
                    "identifier": "in_mrt_epw",
                },
            )
            assert in_epw["summary_view"]["comfort_model"] == "IndoorSolarCal"
            assert in_epw["summary_view"]["input_targets"]["sky_exposure"] == 0.5
            assert "erf" in in_epw["summary_view"]["output_targets"]
            assert "dmrt" in in_epw["summary_view"]["output_targets"]

            in_shaded = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "indoor_solar_mrt",
                    "weather_target": w_target,
                    "human_position": [2.0, 2.0, 0.0],
                    "context_geometry": [canopy_shade],
                    "identifier": "in_mrt_shaded",
                },
            )
            h2s = in_shaded["summary_view"]["human_to_sky"]
            assert 0.0 <= h2s["computed_sky_exposure"] < 0.5
            assert (
                in_shaded["summary_view"]["mrt_delta"]["average"]
                < in_epw["summary_view"]["mrt_delta"]["average"]
            )

            in_scalar = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "indoor_solar_mrt",
                    "solar_altitude": 45.0,
                    "direct_normal_solar": 700.0,
                    "diffuse_horizontal_solar": 120.0,
                    "longwave_mrt": 22.0,
                    "window_transmittance": 0.6,
                },
            )
            assert in_scalar["mrt"] > 22.0
            assert in_scalar["dmrt"] > 0.0
            assert in_scalar["erf"] > 0.0

            # 4. outdoor_solar_mrt (EPW shortcut, scalar, and human_position + context_geometry)
            out_epw = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "outdoor_solar_mrt",
                    "weather_target": w_target,
                    "output_metrics": [
                        "mrt",
                        "short_dmrt",
                        "long_dmrt",
                        "short_erf",
                        "long_erf",
                    ],
                    "identifier": "out_mrt_epw",
                },
            )
            assert out_epw["summary_view"]["comfort_model"] == "OutdoorSolarCal"
            assert "short_dmrt" in out_epw["summary_view"]["output_targets"]
            assert out_epw["summary_view"]["longwave_mrt_delta"]["average"] < 0.0

            out_shaded = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "outdoor_solar_mrt",
                    "weather_target": w_target,
                    "location": loc_dict,
                    "human_position": [2.0, 2.0, 0.0],
                    "context_geometry": [canopy_shade],
                    "identifier": "out_mrt_shaded",
                },
            )
            assert (
                out_shaded["summary_view"]["shortwave_mrt_delta"]["average"]
                < out_epw["summary_view"]["shortwave_mrt_delta"]["average"]
            )

            out_scalar = await _call(
                client,
                "LB_Calculate_Comfort",
                {
                    "garden_root": root,
                    "model": "outdoor_solar_mrt",
                    "solar_altitude": 50.0,
                    "direct_normal_solar": 800.0,
                    "diffuse_horizontal_solar": 150.0,
                    "horizontal_infrared": 320.0,
                    "surface_temperatures": 25.0,
                },
            )
            assert out_scalar["s_dmrt"] > 0.0
            assert out_scalar["l_dmrt"] < 0.0
            assert math.isclose(
                out_scalar["mrt"],
                25.0 + out_scalar["s_dmrt"] + out_scalar["l_dmrt"],
                rel_tol=1e-6,
            )

    asyncio.run(_run())


def test_chart_to_vis_set_passive_strategy_and_comfort_polygons(
    raw_mcp: FastMCP, tmp_path: Path
) -> None:
    garden_dir = tmp_path / "garden_charts"
    epw_dst = _copy_chicago_epw(tmp_path / "weather")

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(
                client, "GD_Create", {"root_dir": str(garden_dir), "name": "charts"}
            )
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            async def _read_epw(field: str, ident: str) -> dict[str, Any]:
                res = await _call(
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
                return res["target"]

            dbt = await _read_epw("dry_bulb_temperature", "dbt")
            rh = await _read_epw("relative_humidity", "rh")
            ghi = await _read_epw("global_horizontal_radiation", "ghi")

            # 1. psychrometric_chart with NO comfort_polygon auto-draws PMVPolygon + PassiveStrategyParameters
            psy_auto = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "incident_irradiance_target": ghi,
                    "name": "psy_auto",
                },
            )
            geo_ids_auto = {
                g["identifier"] for g in psy_auto["visualization_set"]["geometry"]
            }
            assert "Comfort_Polygon" in geo_ids_auto
            assert "Evaporative_Cooling_Polygon" in geo_ids_auto
            assert "Fan_Use_Polygon" in geo_ids_auto
            assert "Night_Flush_Polygon" in geo_ids_auto
            assert "Internal_Heat_Polygon" in geo_ids_auto
            assert "Passive_Solar_Polygon" in geo_ids_auto
            pstats = psy_auto["summary_view"]["passive_strategy_statistics"]
            assert pstats["total_comfort_percent"] > pstats["baseline_comfort_percent"]

            # 2. psychrometric_chart with UTCI + stress polygons + passive strategy stats
            psy_utci = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "comfort_polygon": {"model": "utci", "stress_polygons": True},
                    "name": "psy_utci_stress",
                },
            )
            geo_ids_utci = {
                g["identifier"] for g in psy_utci["visualization_set"]["geometry"]
            }
            assert "Comfort_Polygon" in geo_ids_utci
            assert "UTCI_moderate_cold" in geo_ids_utci
            assert "UTCI_moderate_heat" in geo_ids_utci
            assert (
                "moderate_cold"
                in psy_utci["summary_view"]["comfort_polygon"]["stress_percents"]
            )
            assert psy_utci["summary_view"]["passive_strategy_statistics"] is not None

            # 3. psychrometric_chart with model='both' overlays both PMV & UTCI polygons
            psy_both = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "comfort_polygon": {"model": "both"},
                    "name": "psy_both",
                },
            )
            geo_ids_both = {
                g["identifier"] for g in psy_both["visualization_set"]["geometry"]
            }
            assert "PMV_Comfort_Polygon" in geo_ids_both
            assert "UTCI_Comfort_Polygon" in geo_ids_both
            assert psy_both["summary_view"]["comfort_polygon"]["model"] == "both"

            # 4. opt-out include_passive_strategies=False leaves only baseline chart
            psy_none = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "psychrometric_chart",
                    "temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "include_passive_strategies": False,
                    "name": "psy_none",
                },
            )
            geo_ids_none = {
                g["identifier"] for g in psy_none["visualization_set"]["geometry"]
            }
            assert "Comfort_Polygon" not in geo_ids_none
            assert psy_none["summary_view"]["passive_strategy_statistics"] is None

            # 5. adaptive_chart auto-overlays PMV_Comfort_Polygon + Adaptive_Fan_Use_Polygon + PassiveStrategyParameters
            adp_auto = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "adaptive_chart",
                    "outdoor_temperature_target": dbt,
                    "operative_temperature_target": dbt,
                    "relative_humidity_target": rh,
                    "incident_irradiance_target": ghi,
                    "passive_strategy_parameters": {"fan_air_speed": 1.2},
                    "name": "adp_auto",
                },
            )
            adp_geo_ids = {
                g["identifier"] for g in adp_auto["visualization_set"]["geometry"]
            }
            assert "Comfort_Polygon" in adp_geo_ids
            assert "PMV_Comfort_Polygon" in adp_geo_ids
            assert "Adaptive_Fan_Use_Polygon" in adp_geo_ids
            cp = adp_auto["summary_view"]["comfort_percentages"]
            for key in ("comfortable", "uncomfortable", "neutral", "cold", "hot"):
                assert isinstance(cp[key], (int, float))
            adp_pstats = adp_auto["summary_view"]["passive_strategy_statistics"]
            assert adp_pstats["relative_humidity_source"] == "target"
            assert adp_pstats["adaptive_fan_comfort_percent"] >= cp["comfortable"]

            # 6. adaptive_chart with UTCI overlay (even without explicit relative_humidity_target)
            adp_utci = await _call(
                client,
                "LB_Chart_To_Visualization_Set",
                {
                    "garden_root": root,
                    "chart_type": "adaptive_chart",
                    "outdoor_temperature_target": dbt,
                    "operative_temperature_target": dbt,
                    "comfort_polygon": {"model": "utci"},
                    "name": "adp_utci",
                },
            )
            adp_utci_ids = {
                g["identifier"] for g in adp_utci["visualization_set"]["geometry"]
            }
            assert "UTCI_Comfort_Polygon" in adp_utci_ids
            assert (
                adp_utci["summary_view"]["comfort_polygon"]["relative_humidity_source"]
                == "default_50pct"
            )

    asyncio.run(_run())


def test_run_solar_geometry_study_new_study_types(
    raw_mcp: FastMCP, tmp_path: Path
) -> None:
    garden_dir = tmp_path / "garden_studies"
    epw_dst = _copy_chicago_epw(tmp_path / "weather")
    loc_dict = Location(
        city="Chicago", latitude=41.78, longitude=-87.75, time_zone=-6
    ).to_dict()

    # Horizontal shade surface at z=2 directly above study point [2, 2, 0]
    shade_face = Face3D(
        [
            Point3D(0.0, 0.0, 2.0),
            Point3D(4.0, 0.0, 2.0),
            Point3D(4.0, 4.0, 2.0),
            Point3D(0.0, 4.0, 2.0),
        ]
    ).to_dict()
    study_region_face = Face3D(
        [
            Point3D(1.0, 1.0, 0.0),
            Point3D(3.0, 1.0, 0.0),
            Point3D(3.0, 3.0, 0.0),
            Point3D(1.0, 3.0, 0.0),
        ]
    ).to_dict()
    # Context canopy above the shade that blocks sun before it reaches shade_face
    upper_blocker = Face3D(
        [
            Point3D(-2.0, -2.0, 4.0),
            Point3D(6.0, -2.0, 4.0),
            Point3D(6.0, 6.0, 4.0),
            Point3D(-2.0, 6.0, 4.0),
        ]
    ).to_dict()
    # South-facing vertical wall at y=5 for view studies from [2, 2, 1.5]
    south_wall = Face3D(
        [
            Point3D(0.0, 5.0, 0.0),
            Point3D(4.0, 5.0, 0.0),
            Point3D(4.0, 5.0, 3.0),
            Point3D(0.0, 5.0, 3.0),
        ]
    ).to_dict()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            created = await _call(
                client, "GD_Create", {"root_dir": str(garden_dir), "name": "studies"}
            )
            root = created["garden_root"]
            w_res = await _call(
                client,
                "LB_Manage_Weather",
                {"garden_root": root, "action": "import", "source_path": str(epw_dst)},
            )
            w_target = w_res["target"]

            # 1. shade_benefit (unblocked vs context-blocked)
            sb_clear = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "shade_benefit",
                    "shade_geometry": [shade_face],
                    "study_points": [[2.0, 2.0, 0.0]],
                    "vectors": [[0.0, 0.0, -1.0], [0.2, 0.0, -1.0], [-0.2, 0.0, -1.0]],
                    "grid_size": 2.0,
                    "include_values": True,
                    "name": "sb_clear",
                },
            )
            assert sb_clear["summary_view"]["study_type"] == "shade_benefit"
            assert sb_clear["summary_view"]["total_helpful_hours"] > 0.0

            sb_blocked = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "shade_benefit",
                    "shade_geometry": [shade_face],
                    "study_points": [[2.0, 2.0, 0.0]],
                    "context_geometry": [upper_blocker],
                    "vectors": [[0.0, 0.0, -1.0], [0.2, 0.0, -1.0], [-0.2, 0.0, -1.0]],
                    "grid_size": 2.0,
                    "include_values": True,
                    "name": "sb_blocked",
                },
            )
            assert sb_blocked["summary_view"]["total_helpful_hours"] == 0.0

            # 2. thermal_shade_benefit
            tsb = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "thermal_shade_benefit",
                    "shade_geometry": [shade_face],
                    "study_region": [study_region_face],
                    "weather_target": w_target,
                    "grid_size": 2.0,
                    "up_threshold": 24.0,
                    "low_threshold": 12.0,
                    "include_values": True,
                    "name": "tsb_study",
                },
            )
            tsv = tsb["summary_view"]
            assert tsv["study_type"] == "thermal_shade_benefit"
            assert tsv["total_help_degree_days"] > 0.0
            assert tsv["total_harm_degree_days"] < 0.0
            assert math.isclose(
                tsv["total_net_degree_days"],
                tsv["total_help_degree_days"] + tsv["total_harm_degree_days"],
                rel_tol=1e-6,
            )

            # 3. surface_ray_tracing (1-bounce, 2-bounce with reflector, context_block, receiver filter)
            mirror_floor = Face3D(
                [
                    Point3D(0.0, 0.0, 0.0),
                    Point3D(4.0, 0.0, 0.0),
                    Point3D(4.0, 4.0, 0.0),
                    Point3D(0.0, 4.0, 0.0),
                ]
            ).to_dict()
            # Reflector at y=4 sloped slightly or vertical wall at y=4, z=0..6 to catch second bounce
            bounce_wall = Face3D(
                [
                    Point3D(0.0, 4.0, 0.0),
                    Point3D(4.0, 4.0, 0.0),
                    Point3D(4.0, 4.0, 6.0),
                    Point3D(0.0, 4.0, 6.0),
                ]
            ).to_dict()
            srt = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "surface_ray_tracing",
                    "source_geometry": [mirror_floor],
                    "context_geometry": [bounce_wall],
                    "vectors": [[0.0, 0.5, -1.0]],
                    "grid_size": 2.0,
                    "bounce_count": 2,
                    "first_length": 5.0,
                    "last_length": 5.0,
                    "include_values": True,
                    "name": "srt_2bounce",
                },
            )
            assert srt["summary_view"]["study_type"] == "surface_ray_tracing"
            assert srt["summary_view"]["ray_count"] == 4
            assert srt["summary_view"]["total_intersections"] >= 4
            assert all(len(r) >= 3 for r in srt["summary_view"]["rays"])

            # Receiver filter matching bounce_wall
            srt_recv = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "surface_ray_tracing",
                    "source_geometry": [mirror_floor],
                    "receiver_geometry": [bounce_wall],
                    "vectors": [[0.0, 0.5, -1.0]],
                    "grid_size": 2.0,
                    "bounce_count": 1,
                    "first_length": 5.0,
                    "last_length": 10.0,
                    "name": "srt_recv",
                },
            )
            assert srt_recv["summary_view"]["receiver_filtered"] is True
            assert srt_recv["summary_view"]["ray_count"] > 0

            # context_block=True blocks rays from overhead canopy
            srt_blocked = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "surface_ray_tracing",
                    "source_geometry": [mirror_floor],
                    "context_geometry": [upper_blocker],
                    "vectors": [[0.0, 0.0, -1.0]],
                    "grid_size": 2.0,
                    "context_block": True,
                    "name": "srt_blocked",
                },
            )
            assert srt_blocked["summary_view"]["ray_count"] == 0

            # 4. view_percent across all 5 view_types + include_view_rose=True
            for vt in (
                "HorizontalRadial",
                "Horizontal30DegreeOffset",
                "Spherical",
                "SkyExposure",
                "SkyView",
            ):
                vp = await _call(
                    client,
                    "LB_Run_Solar_Geometry_Study",
                    {
                        "garden_root": root,
                        "study_type": "view_percent",
                        "study_face": study_region_face,
                        "context_geometry": [south_wall],
                        "view_type": vt,
                        "grid_size": 2.0,
                        "include_view_rose": (vt == "SkyExposure"),
                        "radius": 5.0,
                        "name": f"vp_{vt}",
                    },
                )
                assert vp["summary_view"]["study_type"] == "view_percent"
                assert vp["summary_view"]["view_type"] == vt
                assert 0.0 < vp["summary_view"]["mean"] < 100.0
                if vt == "SkyExposure":
                    assert "view_rose" in vp["summary_view"]
                    vr_ids = {
                        g["identifier"] for g in vp["visualization_set"]["geometry"]
                    }
                    assert "View_Percent" in vr_ids
                    assert "View_Rose" in vr_ids

            # 5. Standalone view_rose
            vr = await _call(
                client,
                "LB_Run_Solar_Geometry_Study",
                {
                    "garden_root": root,
                    "study_type": "view_rose",
                    "context_geometry": [south_wall],
                    "center_point": [2.0, 2.0, 1.5],
                    "view_type": "HorizontalRadial",
                    "radius": 5.0,
                    "include_values": True,
                    "name": "vr_horiz",
                },
            )
            vr_sv = vr["summary_view"]
            assert vr_sv["study_type"] == "view_rose"
            assert vr_sv["blocked_ray_count"] > 0
            assert 0.0 < vr_sv["unobstructed_percent"] < 100.0
            assert math.isclose(vr_sv["min_distance"], 3.0, abs_tol=0.05)

    asyncio.run(_run())
