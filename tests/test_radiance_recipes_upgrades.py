"""Tests for Radiance bug fixes, generic lbt-recipes runner, postprocess, HDR tools, and authoring upgrades."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest import mock

import numpy as np
import pytest
from fastmcp import Client, FastMCP
from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.lib.scheduletypelimits import fractional as fraction_limit
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_radiance.luminaire import Luminaire as HbLuminaire
from PIL import Image

from garden.honeybee_core.model_io import load_honeybee_model, save_honeybee_model
from garden.libraries.properties import (
    get_garden_properties_library_object,
    save_garden_properties_library_object,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.radiance import assets, dynamic, luminaires, metrics, modifiers, parameters, run as rad_run, sky, visual
from garden.radiance.run import _RADIANCE_RUNS
from garden.recipes import runner as rec_runner
from garden.runs_control import poll_run
from garden.store import create_garden
from ladybug_tools_mcp.registry import register_tools

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WEATHER_ASSETS = _REPO_ROOT / "resources" / "ladybug" / "tests" / "assets"


def _sample_weather_files() -> tuple[Path, Path, Path]:
    epw = _WEATHER_ASSETS / "epw" / "chicago.epw"
    ddy = _WEATHER_ASSETS / "ddy" / "chicago.ddy"
    stat = _WEATHER_ASSETS / "stat" / "chicago.stat"
    assert epw.is_file() and ddy.is_file() and stat.is_file(), (
        "Expected Chicago weather assets under resources/ladybug/tests/assets."
    )
    return epw, ddy, stat


def _copy_weather_into_garden(garden_root: Path) -> tuple[str, str, str, dict[str, Any]]:
    epw_src, ddy_src, stat_src = _sample_weather_files()
    weather_dir = garden_root / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    epw_dst = weather_dir / epw_src.name
    ddy_dst = weather_dir / ddy_src.name
    stat_dst = weather_dir / stat_src.name
    shutil.copy2(epw_src, epw_dst)
    shutil.copy2(ddy_src, ddy_dst)
    shutil.copy2(stat_src, stat_dst)
    manifest = GardenManifest.read(garden_root)
    epw_rel = f"weather/{epw_dst.name}"
    ddy_rel = f"weather/{ddy_dst.name}"
    stat_rel = f"weather/{stat_dst.name}"
    weather_target = {
        "target_type": "weather_file",
        "garden_id": manifest.garden_id,
        "id": epw_dst.stem,
        "epw_path": epw_rel,
        "ddy_path": ddy_rel,
        "stat_path": stat_rel,
    }
    return epw_rel, ddy_rel, stat_rel, weather_target


def _build_and_save_box_model(garden_root: Path, name: str = "box_model") -> tuple[Model, dict[str, Any]]:
    room = Room.from_box("Room_1", width=4.0, depth=5.0, height=3.0)
    room[1].apertures_by_ratio(0.4, 0.01)
    model = Model(name, rooms=[room])
    manifest = GardenManifest.read(garden_root)
    target, _ = save_honeybee_model(
        garden_root=garden_root,
        manifest=manifest,
        model=model,
        name=name,
    )
    return model, target


def _register_completed_run(
    garden_root: Path,
    *,
    manifest: GardenManifest,
    run_id: str,
    recipe: str,
    run_folder_rel: str,
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    target = _RADIANCE_RUNS.make_target(manifest.garden_id, run_id, recipe=recipe)
    record = {
        "run_id": run_id,
        "target": target,
        "domain": "honeybee_radiance",
        "recipe": recipe,
        "garden_id": manifest.garden_id,
        "status": "completed",
        "created_at": utc_now_iso(),
        "completed_at": utc_now_iso(),
        "run_folder": run_folder_rel,
        "outputs": outputs,
        "status_source": "test_fixture",
    }
    _RADIANCE_RUNS.upsert(garden_root, record, recipe=recipe)
    return record


def _build_raw_mcp() -> FastMCP:
    mcp = FastMCP("rad-upgrades-test", on_duplicate="error", strict_input_validation=True)
    register_tools(mcp)
    return mcp


def _parse_mcp_json(res: Any) -> dict[str, Any]:
    if hasattr(res, "data") and isinstance(res.data, dict):
        return res.data
    text = "".join(getattr(block, "text", "") for block in getattr(res, "content", []))
    return json.loads(text)


# ---------------------------------------------------------------------------
# 1. MCP tool registration & stale tool token check
# ---------------------------------------------------------------------------


def test_mcp_registry_radiance_tools_and_zero_stale_tokens() -> None:
    mcp = _build_raw_mcp()
    tools = asyncio.run(mcp.list_tools())
    registered_names = {t.name for t in tools}

    expected_rad = {
        "RAD_Create_Modifier",
        "RAD_Create_Modifier_Set",
        "RAD_Create_Parameters",
        "RAD_Create_Scene_Asset",
        "RAD_Create_Sky_Asset",
        "RAD_Grid_Result_To_Visualization_Set",
        "RAD_Manage_Luminaires",
        "RAD_Manage_Recipes",
        "RAD_Process_HDR_Image",
        "RAD_Read_Results",
        "RAD_Setup_Dynamic_Group",
        "RAD_Start_Simulation",
    }
    assert expected_rad.issubset(registered_names)

    by_name = {t.name: t for t in tools}
    hdr_ops = by_name["RAD_Process_HDR_Image"].parameters["properties"]["operation"]["enum"]
    assert {"falsecolor", "gif", "png", "bmp", "evalglare", "pcond", "pfilt", "pcomb", "getinfo"}.issubset(
        set(hdr_ops)
    )
    read_kinds = by_name["RAD_Read_Results"].parameters["properties"]["result_kind"]["enum"]
    assert {
        "annual_daylight",
        "glare",
        "compliance",
        "grid_summary",
        "annual_postprocess",
        "daylight_control_schedule",
        "dynamic_schedule",
        "comfort_map",
        "list_outputs",
    }.issubset(set(read_kinds))

    src_root = Path(__file__).resolve().parents[1] / "src"
    token_re = re.compile(r"\b(?:GD|HB|DF|EP|RAD|LB|FF|FP|IB)_[A-Z][A-Za-z0-9_]*\b")
    stale_hits: list[str] = []
    for py_file in sorted(src_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in token_re.finditer(line):
                tok = match.group(0)
                if tok in registered_names:
                    continue
                if tok.startswith("IB_") and "_" not in tok[3:]:
                    continue
                stale_hits.append(f"{py_file.relative_to(src_root)}:{lineno}: {tok}")
    assert stale_hits == []


# ---------------------------------------------------------------------------
# 2. Sky bug fixes (-tz, -L) & new sky/sky_matrix capabilities
# ---------------------------------------------------------------------------


def test_sky_bug_fixes_timezone_luminance_and_new_sky_assets(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="sky_garden", root_dir=str(tmp_path))["garden_root"])
    epw_rel, _, stat_rel, _ = _copy_weather_into_garden(garden_root)

    # -tz int, numeric str, and named tz must all preserve -tz in recipe_sky
    for tz_in, expected_tz in [(-6, "-6"), ("-6", "-6"), ("CST", "-6")]:
        res = sky.create_radiance_sky_asset(
            garden_root=str(garden_root),
            asset_type="climate_based_sky",
            month=6,
            day=21,
            time="12:00",
            latitude=41.8,
            longitude=-87.6,
            time_zone=tz_in,
            direct_normal_irradiance=600.0,
            diffuse_horizontal_irradiance=200.0,
            identifier=f"cb_tz_{str(tz_in).replace('-', 'm')}",
        )
        assert f"-tz {expected_tz}" in res["summary_view"]["recipe_sky"]
        sky_text = (garden_root / res["target"]["path"]).read_text(encoding="utf-8")
        assert "!gendaylit" in sky_text

    # -L illuminance flag preserved in recipe_sky (both direct service and run.py token helper)
    illum_res = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="climate_based_sky",
        month=3,
        day=21,
        time=12.0,
        latitude=40.0,
        longitude=-74.0,
        time_zone=-5,
        direct_normal_illuminance=50000.0,
        diffuse_horizontal_illuminance=12000.0,
        identifier="cb_illum",
    )
    assert "-L 50000 12000" in illum_res["summary_view"]["recipe_sky"]
    assert "-tz -5" in illum_res["summary_view"]["recipe_sky"]

    parsed_cli = rad_run._recipe_sky_from_gendaylit_tokens(
        ["-L", "50000", "12000", "-a", "40.0", "-o", "-74.0", "-m", "75", "3", "21", "12:00"]
    )
    assert "-L 50000 12000" in parsed_cli and "-tz -5" in parsed_cli

    # certain_irradiance (including 0 lux dark sky for electric-only lighting + uniform)
    dark_sky = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="certain_irradiance",
        illuminance=0.0,
        identifier="dark_sky",
    )
    assert dark_sky["target"]["identifier"] == "dark_sky"
    assert "0" in (garden_root / dark_sky["target"]["path"]).read_text(encoding="utf-8")

    uniform_rad = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="certain_irradiance",
        irradiance=500.0,
        uniform=True,
        identifier="uniform_500",
    )
    assert "500" in (garden_root / uniform_rad["target"]["path"]).read_text(encoding="utf-8")

    # from_epw_hoy, skydome (uniform & non-uniform), leed_illuminance, abnt_nbr_15575
    epw_hoy = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="from_epw_hoy",
        epw_path=epw_rel,
        hoy=4000,
        identifier="epw_hoy_4000",
    )
    assert (garden_root / epw_hoy["target"]["path"]).is_file()

    uniform_dome = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="skydome",
        uniform=True,
        identifier="uniform_dome",
    )
    assert "sky_glow" in (garden_root / uniform_dome["target"]["path"]).read_text(encoding="utf-8").lower()

    sky_dome = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="skydome",
        uniform=False,
        identifier="cos_dome",
    )
    assert "sky_glow" in (garden_root / sky_dome["target"]["path"]).read_text(encoding="utf-8").lower()

    leed_sky = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="leed_illuminance",
        epw_path=epw_rel,
        identifier="leed_sky",
    )
    assert leed_sky["summary_view"]["sky_family"] == "leed_illuminance"
    assert len(leed_sky["sky_file_targets"]) == 2

    abnt_sky = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="abnt_nbr_15575",
        epw_path=epw_rel,
        identifier="abnt_sky",
    )
    assert abnt_sky["summary_view"]["sky_family"] == "abnt_nbr_15575"
    assert len(abnt_sky["sky_file_targets"]) >= 2

    # sky_matrix enhancements: hoys, stat_path, benefit_matrix
    mtx_hoys = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="sky_matrix",
        epw_path=epw_rel,
        hoys=[10, 11, 12],
        identifier="mtx_hoys",
    )
    assert (garden_root / mtx_hoys["target"]["path"]).is_file()

    mtx_stat = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="sky_matrix",
        stat_path=stat_rel,
        identifier="mtx_stat",
    )
    assert (garden_root / mtx_stat["target"]["path"]).is_file()

    mtx_ben = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="sky_matrix",
        epw_path=epw_rel,
        benefit_matrix=True,
        balance_temperature=16.0,
        balance_offset=2.5,
        identifier="mtx_benefit",
    )
    assert mtx_ben["summary_view"]["has_benefit_matrix"] is True
    assert mtx_ben["target"]["benefit_matrix"] is True
    assert mtx_ben["summary_view"]["benefit_hour_count"] == 8760


# ---------------------------------------------------------------------------
# 3. SensorGrid JSON sidecar persistence & new scene asset generators
# ---------------------------------------------------------------------------


def test_sensor_grid_json_sidecar_and_scene_assets(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="assets_garden", root_dir=str(tmp_path))["garden_root"])
    _, model_target = _build_and_save_box_model(garden_root, name="asset_box")

    # room_floor_grid with wall_offset and remove_out -> persists .pts + .json sidecar
    floor_grid = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_floor_grid",
        identifier="floor_pts",
        model_target=model_target,
        room_identifier="Room_1",
        grid_spacing=1.5,
        height=0.8,
        wall_offset=0.5,
        remove_out=True,
        attach_to_model=True,
    )
    pts_path = garden_root / floor_grid["target"]["path"]
    json_sidecar = pts_path.with_suffix(".json")
    assert pts_path.is_file() and json_sidecar.is_file()

    # Reload via _sensor_grid_from_target -> mesh, room_identifier intact
    reloaded = assets._sensor_grid_from_target(garden_root, floor_grid["target"])
    assert reloaded.mesh is not None
    assert reloaded.room_identifier == "Room_1"

    # room_radial_grid (needed for imageless-annual-glare)
    radial = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_radial_grid",
        identifier="radial_pts",
        model_target=model_target,
        room_identifier="Room_1",
        grid_spacing=2.0,
        height=1.2,
        dir_count=8,
        start_vector=[0.0, 1.0, 0.0],
        attach_to_model=True,
    )
    assert radial["summary_view"]["sensor_count"] > 0

    # exterior_face_grid & exterior_aperture_grid
    ext_face = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="exterior_face_grid",
        identifier="ext_wall_pts",
        model_target=model_target,
        face_type="Wall",
        grid_spacing=2.0,
        offset=0.1,
    )
    assert ext_face["summary_view"]["sensor_count"] > 0

    ext_ap = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="exterior_aperture_grid",
        identifier="ext_ap_pts",
        model_target=model_target,
        grid_spacing=1.0,
        offset=0.1,
    )
    assert ext_ap["summary_view"]["sensor_count"] > 0

    # room_view
    room_view = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_view",
        identifier="room1_eye",
        model_target=model_target,
        room_identifier="Room_1",
        view_type="a",
        h_size=180.0,
        v_size=180.0,
        attach_to_model=True,
    )
    assert room_view["summary_view"]["view_type"] == "a"

    # split -> merge -> remove
    split_res = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        action="split",
        sensor_grid_target=floor_grid["target"],
        split_count=2,
    )
    assert len(split_res["targets"]) >= 2

    merged_res = assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        action="merge",
        identifier="merged_floor",
        sensor_grid_targets=split_res["targets"],
    )
    assert merged_res["summary_view"]["sensor_count"] == floor_grid["summary_view"]["sensor_count"]

    assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        action="remove",
        model_target=model_target,
        grid_identifiers=["floor_pts"],
        view_identifiers=["room1_eye"],
    )
    hb_after = load_honeybee_model(garden_root=garden_root, model_target=model_target)
    assert "floor_pts" not in {g.identifier for g in hb_after.properties.radiance.sensor_grids}
    assert "room1_eye" not in {v.identifier for v in hb_after.properties.radiance.views}


# ---------------------------------------------------------------------------
# 4. Parameters for all 8 missing recipes, comfort maps, and CLI tools
# ---------------------------------------------------------------------------


def test_parameters_all_missing_recipes_comfort_maps_and_commands() -> None:
    expected_recipes = [
        "annual-daylight-enhanced",
        "direct-sun-hours",
        "leed-daylight-option-one",
        "leed-daylight-option-two",
        "annual-daylight-en17037",
        "well-daylight",
        "breeam-daylight-4b",
        "imageless-annual-glare",
        "pmv-comfort-map",
        "utci-comfort-map",
        "adaptive-comfort-map",
        "rcontrib",
        "dcglare",
        "evalglare",
    ]
    for recipe_name in expected_recipes:
        extra = "-b 1800" if recipe_name == "evalglare" else (None if recipe_name == "dcglare" else "-dr 1")
        res = parameters.create_radiance_parameters(
            recipe_type=recipe_name,
            detail_level=1,
            additional_par=extra,
        )
        assert res["radiance_parameters"]
        if extra:
            assert extra in res["radiance_parameters"]


# ---------------------------------------------------------------------------
# 5. imageless-annual-glare (no View!), grid_metrics, schedule CSV, run isolation
# ---------------------------------------------------------------------------


def test_imageless_glare_schedule_grid_metrics_and_run_isolation(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="run_garden", root_dir=str(tmp_path))["garden_root"])
    _, model_target = _build_and_save_box_model(garden_root, name="glare_box")
    _, _, _, weather_target = _copy_weather_into_garden(garden_root)

    # Attach ONLY a radial grid and NO Views
    assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_radial_grid",
        identifier="radial_glare",
        model_target=model_target,
        room_identifier="Room_1",
        grid_spacing=2.0,
        height=1.2,
        dir_count=8,
        attach_to_model=True,
    )
    hb_model = load_honeybee_model(garden_root=garden_root, model_target=model_target)
    assert len(hb_model.properties.radiance.views) == 0

    # Save an energy ScheduleFixedInterval to test schedule materialization from Garden target
    sched = ScheduleFixedInterval("occ_8_to_6", [1] * 8760, fraction_limit)
    saved_sched = save_garden_properties_library_object(
        garden_root=str(garden_root),
        domain="honeybee_energy",
        object_family="schedule",
        identifier=sched.identifier,
        object_dict=sched.to_dict(),
    )

    sky_res = sky.create_radiance_sky_asset(
        garden_root=str(garden_root),
        asset_type="climate_based_sky",
        month=6,
        day=21,
        time="12:00",
        latitude=40.0,
        longitude=-74.0,
        time_zone=-5,
        direct_normal_irradiance=600.0,
        diffuse_horizontal_irradiance=200.0,
        identifier="pit_sky",
    )

    submitted_cmds: list[dict[str, Any]] = []

    def _fake_submit(**kwargs: Any) -> dict[str, Any]:
        submitted_cmds.append(kwargs)
        return {"pid": 9000 + len(submitted_cmds), "worker_status": "running"}

    with mock.patch("garden.radiance.run.submit_worker_process", side_effect=_fake_submit):
        # 5a. imageless-annual-glare succeeds WITHOUT Views + materializes Garden schedule to .csv
        glare_run = rad_run.start_radiance_simulation(
            garden_root=str(garden_root),
            recipe="imageless-annual-glare",
            model_target=model_target,
            weather_file_target=weather_target,
            schedule=saved_sched["target"],
            run_id="glare_v1",
            debug_folder="runs/debug_glare",
        )
        assert glare_run["status"] == "running"
        assert glare_run["recipe"] == "imageless-annual-glare"
        assert glare_run["simulation_id"] == "glare_v1"
        assert glare_run["debug_folder"] == "runs/debug_glare"
        run_folder = garden_root / glare_run["summary_view"]["run_folder"]
        assert (run_folder / "inputs" / "schedule.csv").is_file()
        glare_req_inputs = submitted_cmds[0]["request"]["inputs"]
        assert "schedule" in glare_req_inputs and str(glare_req_inputs["schedule"]).endswith("schedule.csv")

        # 5b. Backward-compatible single-dict grid_metrics converted cleanly to list[dict] for annual-daylight
        ad_run = rad_run.start_radiance_simulation(
            garden_root=str(garden_root),
            recipe="annual-daylight",
            model_target=model_target,
            weather_file_target=weather_target,
            grid_metrics={"da": {"threshold": 300}},
            run_id="ad_dict_metrics",
        )
        assert ad_run["status"] == "running"
        ad_req_inputs = submitted_cmds[1]["request"]["inputs"]
        assert isinstance(ad_req_inputs["grid-metrics"], list)
        assert ad_req_inputs["grid-metrics"][0] == {"da": {"threshold": 300}}

        # 5c. Run isolation: two sequential runs of the SAME recipe do NOT clobber each other
        pit_a = rad_run.start_radiance_simulation(
            garden_root=str(garden_root),
            recipe="point-in-time-grid",
            model_target=model_target,
            radiance_sky_file=sky_res["target"],
            run_id="pit_variant_a",
            debug_folder="runs/debug_a",
        )
        pit_b = rad_run.start_radiance_simulation(
            garden_root=str(garden_root),
            recipe="point-in-time-grid",
            model_target=model_target,
            radiance_sky_file=sky_res["target"],
            run_id="pit_variant_b",
            debug_folder="runs/debug_b",
        )
        pit_a_folder = pit_a["summary_view"]["run_folder"]
        pit_b_folder = pit_b["summary_view"]["run_folder"]
        assert pit_a_folder != pit_b_folder
        assert "pit_variant_a" in pit_a_folder
        assert "pit_variant_b" in pit_b_folder
        assert pit_a["simulation_id"] == "pit_variant_a"
        assert pit_b["simulation_id"] == "pit_variant_b"
        assert submitted_cmds[2]["run_dir"] != submitted_cmds[3]["run_dir"]


# ---------------------------------------------------------------------------
# 6. Generic recipe runner (RAD_Manage_Recipes) + comfort maps + GD_Poll_Run
# ---------------------------------------------------------------------------


def test_manage_recipes_list_describe_external_and_comfort_map(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="recipes_garden", root_dir=str(tmp_path))["garden_root"])
    _, model_target = _build_and_save_box_model(garden_root, name="comfort_box")
    assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_floor_grid",
        identifier="pmv_grid",
        model_target=model_target,
        room_identifier="Room_1",
        grid_spacing=2.0,
        attach_to_model=True,
    )
    epw_rel, ddy_rel, _, weather_target = _copy_weather_into_garden(garden_root)

    listed = rec_runner.list_recipes()
    names = {item["name"] for item in listed["recipes"]}
    assert len(names) == 19
    assert {"pmv-comfort-map", "utci-comfort-map", "adaptive-comfort-map", "annual-energy-use"}.issubset(names)

    pmv_desc = rec_runner.describe_recipe("pmv-comfort-map")["recipe"]
    assert set(["epw", "ddy", "model"]).issubset(set(pmv_desc["required_inputs"]))
    energy_desc = rec_runner.describe_recipe("annual-energy-use")["recipe"]
    assert "model" in energy_desc["required_inputs"]

    # Create a valid external Queenbee recipe folder by copying point-in-time-grid package structure
    ext_dir = tmp_path / "external_queenbee_recipe"
    shutil.copytree(Path(rec_runner.describe_recipe("point-in-time-grid")["recipe"]["folder"]), ext_dir)
    pkg_file = ext_dir / "package.json"
    pkg_json = json.loads(pkg_file.read_text(encoding="utf-8"))
    pkg_json["metadata"]["name"] = "custom-local-pit-grid"
    pkg_file.write_text(json.dumps(pkg_json), encoding="utf-8")

    ext_desc = rec_runner.describe_recipe(str(ext_dir))["recipe"]
    assert ext_desc["is_external"] is True
    assert ext_desc["name"] == "custom-local-pit-grid"

    # Execute pmv-comfort-map via RAD_Manage_Recipes AND RAD_Start_Simulation with mocked worker
    mcp = _build_raw_mcp()

    async def _call_recipes_and_check_poll() -> None:
        async with Client(mcp) as client:
            with mock.patch(
                "garden.radiance.run.submit_worker_process",
                return_value={"pid": 4321, "worker_status": "running"},
            ):
                start_res = _parse_mcp_json(
                    await client.call_tool(
                        "RAD_Manage_Recipes",
                        {
                            "action": "start",
                            "garden_root": str(garden_root),
                            "recipe": "pmv-comfort-map",
                            "model_target": model_target,
                            "epw_path": epw_rel,
                            "ddy_path": ddy_rel,
                            "inputs": {"met-rate": [1.1] * 8760, "air-speed": 0.15},
                            "run_id": "pmv_via_manage",
                            "debug_folder": "runs/pmv_debug",
                        },
                    )
                )
                assert start_res["status"] == "running"
                assert start_res["recipe"] == "pmv-comfort-map"

                # Simulate worker finishing: write _recipe_status_path and all required pmv-comfort-map output dirs
                run_folder = garden_root / start_res["summary_view"]["run"]["run_folder"]
                sim_folder = rad_run._recipe_sim_folder(
                    run_folder,
                    "pmv-comfort-map",
                    simulation_id=start_res["run_id"],
                )
                status_file = rad_run._recipe_status_path(
                    run_folder,
                    "pmv-comfort-map",
                    simulation_id=start_res["run_id"],
                )
                status_file.parent.mkdir(parents=True, exist_ok=True)
                status_file.write_text(
                    json.dumps({"status": "completed", "finished_at": utc_now_iso()}),
                    encoding="utf-8",
                )
                for sub_rel in (
                    "results/condition",
                    "metrics/CSP",
                    "initial_results/conditions",
                    "metrics/HSP",
                    "results/condition_intensity",
                    "metrics/TCP",
                    "results/temperature",
                ):
                    out_sub = sim_folder / sub_rel
                    out_sub.mkdir(parents=True, exist_ok=True)
                    (out_sub / "grids_info.json").write_text(
                        json.dumps([{"full_id": "pmv_grid", "name": "pmv_grid", "count": 4}]),
                        encoding="utf-8",
                    )
                    (out_sub / "pmv_grid.csv").write_text("80.0\n85.0\n90.0\n75.0\n", encoding="utf-8")

                polled = poll_run(
                    garden_root=str(garden_root),
                    run_target=start_res["target"],
                )
                assert polled["status"] == "completed"

    asyncio.run(_call_recipes_and_check_poll())

    # Also allow RAD_Start_Simulation directly for comfort-map recipes
    with mock.patch(
        "garden.radiance.run.submit_worker_process",
        return_value={"pid": 4322, "worker_status": "running"},
    ):
        pmv_direct = rad_run.start_radiance_simulation(
            garden_root=str(garden_root),
            recipe="pmv-comfort-map",
            model_target=model_target,
            weather_file_target=weather_target,
            run_id="pmv_via_start",
        )
        assert pmv_direct["status"] == "running"
        assert pmv_direct["recipe"] == "pmv-comfort-map"


# ---------------------------------------------------------------------------
# 7. RAD_Read_Results postprocess modes & visual.py default output detection
# ---------------------------------------------------------------------------


def _write_annual_results_fixture(
    results_dir: Path,
    *,
    grid_id: str = "room_grid",
    sun_up_hours: list[int] | None = None,
    static_values: np.ndarray | None = None,
    shade_states: dict[str, np.ndarray] | None = None,
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    suh = sun_up_hours if sun_up_hours is not None else list(range(8, 18))
    (results_dir / "sun-up-hours.txt").write_text("\n".join(str(h) for h in suh) + "\n", encoding="utf-8")

    light_paths = [["__static_apertures__"]]
    if shade_states:
        light_paths.append(["SouthShade"])
    grids_info = [
        {
            "full_id": grid_id,
            "name": grid_id,
            "identifier": grid_id,
            "count": 4,
            "min": [0, 0, 0],
            "max": [3, 3, 0],
            "light_path": light_paths,
        }
    ]
    (results_dir / "grids_info.json").write_text(json.dumps(grids_info), encoding="utf-8")

    arr = static_values if static_values is not None else np.array(
        [[500.0] * len(suh), [400.0] * len(suh), [200.0] * len(suh), [1500.0] * len(suh)],
        dtype=float,
    )
    static_total = results_dir / "__static_apertures__" / "default" / "total"
    static_direct = results_dir / "__static_apertures__" / "default" / "direct"
    static_total.mkdir(parents=True, exist_ok=True)
    static_direct.mkdir(parents=True, exist_ok=True)
    np.save(static_total / f"{grid_id}.npy", arr)
    np.save(static_direct / f"{grid_id}.npy", arr * 0.6)

    if shade_states:
        (results_dir / "grid_states.json").write_text(
            json.dumps(
                {
                    grid_id: {
                        "SouthShade": [
                            f"{state_idx}_SouthShade"
                            for state_idx in sorted(shade_states)
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        for state_idx, state_arr in shade_states.items():
            st_total = results_dir / "SouthShade" / f"{state_idx}_SouthShade" / "total"
            st_direct = results_dir / "SouthShade" / f"{state_idx}_SouthShade" / "direct"
            st_total.mkdir(parents=True, exist_ok=True)
            st_direct.mkdir(parents=True, exist_ok=True)
            np.save(st_total / f"{grid_id}.npy", state_arr)
            np.save(st_direct / f"{grid_id}.npy", state_arr * 0.4)


def test_rad_read_results_postprocess_and_visual_default_outputs(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="postproc_garden", root_dir=str(tmp_path))["garden_root"])
    manifest = GardenManifest.read(garden_root)
    _, model_target = _build_and_save_box_model(garden_root, name="post_box")

    assets.create_radiance_scene_asset(
        garden_root=str(garden_root),
        asset_type="room_floor_grid",
        identifier="room_grid",
        model_target=model_target,
        room_identifier="Room_1",
        grid_spacing=2.0,
        attach_to_model=True,
    )

    # 7a. Visual default output_name detection across cumulative-radiation, direct-sun-hours, annual-irradiance, pmv-comfort-map
    pmv_rec: dict[str, Any] | None = None
    for recipe, folder_name, metric_fname in [
        ("cumulative-radiation", "cumulative-radiation", "room_grid.res"),
        ("direct-sun-hours", "cumulative-sun-hours", "room_grid.res"),
        ("annual-irradiance", "average-irradiance", "room_grid.res"),
        ("pmv-comfort-map", "tcp", "room_grid.csv"),
    ]:
        out_dir = garden_root / "runs" / "radiance" / f"{recipe}_run" / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "grids_info.json").write_text(
            json.dumps([{"full_id": "room_grid", "name": "room_grid", "count": 4}]),
            encoding="utf-8",
        )
        (out_dir / metric_fname).write_text("10.0\n20.0\n30.0\n40.0\n", encoding="utf-8")
        run_id = f"run_{recipe.replace('-', '_')}"
        rec = _register_completed_run(
            garden_root,
            manifest=manifest,
            run_id=run_id,
            recipe=recipe,
            run_folder_rel=f"runs/radiance/{recipe}_run",
            outputs=[{"name": folder_name, "path": f"runs/radiance/{recipe}_run/{folder_name}"}],
        )
        if recipe == "pmv-comfort-map":
            pmv_rec = rec
        resolved = visual._resolve_grid_data_path(
            garden_root,
            rec,
            grid_data_path=None,
            output_name=None,
            result_subfolder=None,
        )
        assert resolved == out_dir.resolve()

        grid_sum = metrics.summarize_radiance_grid_results(
            garden_root=str(garden_root),
            run_id=run_id,
            save_report=True,
            include_values=True,
        )
        assert grid_sum["summary_view"]["grids"]["room_grid"]["min"] == pytest.approx(10.0)
        assert grid_sum["summary_view"]["grids"]["room_grid"]["max"] == pytest.approx(40.0)
        assert grid_sum["summary_view"]["grids"]["room_grid"]["mean"] == pytest.approx(25.0)

    # 7b. Comfort map metrics summary
    pmv_base = garden_root / "runs" / "radiance" / "pmv_comfort_map_run"
    for out_key, vals in [
        ("hsp", "5\n5\n0\n0\n"),
        ("csp", "10\n5\n5\n5\n"),
        ("temperature", "22.5\n23.0\n21.5\n24.0\n"),
    ]:
        sub = pmv_base / out_key
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "grids_info.json").write_text(
            json.dumps([{"full_id": "room_grid", "name": "room_grid", "count": 4}]),
            encoding="utf-8",
        )
        (sub / "room_grid.csv").write_text(vals, encoding="utf-8")
    assert pmv_rec is not None
    pmv_rec["outputs"].extend(
        [
            {"name": "hsp", "path": "runs/radiance/pmv_comfort_map_run/hsp"},
            {"name": "csp", "path": "runs/radiance/pmv_comfort_map_run/csp"},
            {"name": "temperature", "path": "runs/radiance/pmv_comfort_map_run/temperature"},
        ]
    )
    _RADIANCE_RUNS.upsert(garden_root, pmv_rec, recipe="pmv-comfort-map")
    comfort_res = metrics.summarize_comfort_map_metrics(
        garden_root=str(garden_root),
        run_id="run_pmv_comfort_map",
    )
    assert comfort_res["summary_view"]["metrics"]["tcp"]["overall"]["mean"] == pytest.approx(25.0)
    assert "temperature" in comfort_res["summary_view"]["metrics"]

    # 7c. Annual Daylight + Dynamic States postprocess + Daylight Control Schedule + Dynamic Schedule
    suh = list(range(8, 18)) + list(range(32, 42))
    static_arr = np.vstack([
        np.full(len(suh), 500.0),
        np.full(len(suh), 350.0),
        np.full(len(suh), 150.0),
        np.full(len(suh), 4000.0),
    ])
    shade_0 = np.full((4, len(suh)), 2500.0)
    shade_1 = np.full((4, len(suh)), 150.0)
    annual_dir = garden_root / "runs" / "radiance" / "annual_daylight_run" / "results"
    _write_annual_results_fixture(
        annual_dir,
        sun_up_hours=suh,
        static_values=static_arr,
        shade_states={"0": shade_0, "1": shade_1},
    )
    _register_completed_run(
        garden_root,
        manifest=manifest,
        run_id="annual_dl_run",
        recipe="annual-daylight",
        run_folder_rel="runs/radiance/annual_daylight_run",
        outputs=[{"name": "results", "path": "runs/radiance/annual_daylight_run/results"}],
    )

    # Dynamic schedule (sensor_maximum, ies_lm_83 [use_states=True/False], and leed)
    dyn_max = metrics.generate_radiance_dynamic_schedule(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
        mode="sensor_maximum",
        maximum=3000.0,
    )
    assert dyn_max["summary_view"]["group_count"] >= 1

    dyn_leed_states = metrics.generate_radiance_dynamic_schedule(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
        mode="ies_lm_83",
        shade_transmittance=0.05,
        use_states=True,
    )
    assert dyn_leed_states["summary_view"]["group_count"] >= 1

    dyn_leed_trans = metrics.generate_radiance_dynamic_schedule(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
        mode="leed",
        shade_transmittance=0.05,
        use_states=False,
    )
    assert dyn_leed_trans["summary_view"]["group_count"] >= 1

    # Post-hoc annual postprocess with custom thresholds & HOY filter
    post = metrics.run_annual_postprocess(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
        threshold=250.0,
        thresholds={"min_threshold": 100.0, "max_threshold": 2000.0},
        schedule=[1] * 8760,
        hoys=suh,
        include_values=True,
    )
    grid_metrics = post["summary_view"]["grids"]["room_grid"]
    assert {
        "da",
        "cda",
        "udi",
        "sda",
        "ase",
        "uniformity_passing_percent",
        "hoy_filtered",
    }.issubset(set(grid_metrics.keys()))

    # Export 8760 daylight control dimming schedule persisted to Garden Energy library
    ctrl = metrics.export_daylight_control_schedules(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
        ill_setpoint=300.0,
        identifier_prefix="dl_ctrl",
        persist_to_garden=True,
    )
    assert len(ctrl["schedules"]) == 1
    assert ctrl["schedules"][0]["value_count"] == 8760
    assert (garden_root / ctrl["schedules"][0]["csv_path"]).is_file()
    sched_target = ctrl["schedules"][0]["target"]
    lib_obj = get_garden_properties_library_object(
        garden_root=str(garden_root),
        target=sched_target,
    )
    assert len(lib_obj["object_dict"]["values"]) == 8760

    # Annual irradiance postprocess
    ann_irr_dir = garden_root / "runs" / "radiance" / "annual_irr_run" / "results"
    _write_annual_results_fixture(ann_irr_dir, sun_up_hours=suh, static_values=static_arr)
    _register_completed_run(
        garden_root,
        manifest=manifest,
        run_id="annual_irr_run",
        recipe="annual-irradiance",
        run_folder_rel="runs/radiance/annual_irr_run",
        outputs=[{"name": "results", "path": "runs/radiance/annual_irr_run/results"}],
    )
    irr_post = metrics.run_annual_postprocess(
        garden_root=str(garden_root),
        run_id="annual_irr_run",
        hoys=suh[:5],
    )
    assert {"average", "cumulative", "peak"}.issubset(
        set(irr_post["summary_view"]["grids"]["room_grid"].keys())
    )

    # list_outputs
    all_out = metrics.list_radiance_run_all_outputs(
        garden_root=str(garden_root),
        run_id="annual_dl_run",
    )
    assert len(all_out["grid_results"]) == 1 and len(all_out["outputs"]) == 1

    # Also invoke RAD_Read_Results through MCP client
    mcp = _build_raw_mcp()

    async def _call_read_results() -> None:
        async with Client(mcp) as client:
            res = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Read_Results",
                    {
                        "garden_root": str(garden_root),
                        "run_id": "annual_dl_run",
                        "result_kind": "annual_postprocess",
                        "threshold": 300.0,
                    },
                )
            )
            assert "da" in res["summary_view"]["grids"]["room_grid"]

    asyncio.run(_call_read_results())


# ---------------------------------------------------------------------------
# 8. Expanded RAD_Process_HDR_Image (evalglare, pcond, pfilt, pcomb, getinfo, bmp, png)
# ---------------------------------------------------------------------------


def test_rad_process_hdr_image_new_operations(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="hdr_garden", root_dir=str(tmp_path))["garden_root"])
    hdr_dir = garden_root / "artifacts" / "radiance" / "images"
    hdr_dir.mkdir(parents=True, exist_ok=True)
    hdr1 = hdr_dir / "fisheye.hdr"
    hdr2 = hdr_dir / "uniform.hdr"

    env = visual._subprocess_env()
    subprocess.run(
        f'pcomb -x 64 -y 64 -e "r=if(100-((x-32)^2+(y-32)^2),100000,50);ro=r;go=r;bo=r" '
        f'| getinfo -a "VIEW= -vta -vv 180 -vh 180" > "{hdr1.as_posix()}"',
        shell=True,
        check=True,
        env=env,
        cwd=str(garden_root),
        stdin=subprocess.DEVNULL,
    )
    subprocess.run(
        f'pcomb -x 64 -y 64 -e "ro=25;go=25;bo=25" > "{hdr2.as_posix()}"',
        shell=True,
        check=True,
        env=env,
        cwd=str(garden_root),
        stdin=subprocess.DEVNULL,
    )

    rel1 = "artifacts/radiance/images/fisheye.hdr"
    rel2 = "artifacts/radiance/images/uniform.hdr"
    mcp = _build_raw_mcp()

    async def _exercise_hdr_tools() -> None:
        async with Client(mcp) as client:
            gi_full = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {"garden_root": str(garden_root), "operation": "getinfo", "image_path": rel1},
                )
            )
            assert "VIEW=" in gi_full["header"]

            gi_dims = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "getinfo",
                        "image_path": rel1,
                        "dimensions_only": True,
                    },
                )
            )
            assert gi_dims["width"] == 64 and gi_dims["height"] == 64

            eg = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "evalglare",
                        "image_path": rel1,
                        "detailed": True,
                        "check_image": True,
                        "check_image_name": "glare_chk",
                    },
                )
            )
            assert eg["dgp"] is not None and eg["ev"] is not None
            assert eg["glare_source_count"] >= 1
            assert (garden_root / eg["check_image_path"]).is_file()

            pc = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "pcond",
                        "image_path": rel1,
                        "human_vision": True,
                        "exposure": 1.0,
                        "name": "tonemapped",
                    },
                )
            )
            assert (garden_root / pc["target"]["path"]).is_file()

            pf = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "pfilt",
                        "image_path": rel1,
                        "x_res": 32,
                        "y_res": 32,
                        "exposure": 0.5,
                        "radius": 0.6,
                        "name": "resized",
                    },
                )
            )
            pf_dims = visual.process_radiance_hdr_image(
                garden_root=str(garden_root),
                operation="getinfo",
                image_path=pf["target"]["path"],
                dimensions_only=True,
            )
            assert pf_dims["width"] == 32 and pf_dims["height"] == 32

            pb = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "pcomb",
                        "image_paths": [rel1, rel2],
                        "expression": "ro=ri(1)+ri(2);go=gi(1)+gi(2);bo=bi(1)+bi(2)",
                        "name": "combined",
                    },
                )
            )
            assert (garden_root / pb["target"]["path"]).is_file()

            bmp_res = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "bmp",
                        "image_path": rel1,
                        "exposure": 0,
                        "name": "preview_bmp",
                    },
                )
            )
            assert (garden_root / bmp_res["target"]["path"]).stat().st_size > 100

            png_res = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Process_HDR_Image",
                    {
                        "garden_root": str(garden_root),
                        "operation": "png",
                        "image_path": rel1,
                        "exposure": "auto",
                        "black_and_white": True,
                        "name": "preview_png",
                    },
                )
            )
            with Image.open(garden_root / png_res["target"]["path"]) as im:
                assert im.format == "PNG"
                assert im.size == (64, 64)

    asyncio.run(_exercise_hdr_tools())


# ---------------------------------------------------------------------------
# 9. Modifiers (all new types, chaining) + RAD_Create_Modifier_Set
# ---------------------------------------------------------------------------


def test_modifiers_chaining_and_modifier_set(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="mod_garden", root_dir=str(tmp_path))["garden_root"])
    bsdf_xml = tmp_path / "sample_bsdf.xml"
    bsdf_xml.write_text(
        "<WindowElement>\n"
        "  <Optical>\n"
        "    <Layer>\n"
        "      <DataDefinition>\n"
        "        <IncidentDataStructure>Columns</IncidentDataStructure>\n"
        "        <AngleBasisName>LBNL/Klems Full</AngleBasisName>\n"
        "      </DataDefinition>\n"
        "    </Layer>\n"
        "  </Optical>\n"
        "</WindowElement>\n",
        encoding="utf-8",
    )

    # Parent modifier for chaining
    base_glow = modifiers.create_radiance_modifier(
        garden_root=str(garden_root),
        modifier_type="glow",
        identifier="parent_glow",
        params={"rgb_emittance": [1.0, 1.0, 1.0], "max_radius": 0.5},
    )
    assert base_glow["summary_view"]["type"] == "Glow"

    # Chained plastic modifier using Garden target as parent
    chained_plastic = modifiers.create_radiance_modifier(
        garden_root=str(garden_root),
        modifier_type="opaque",
        identifier="chained_wall",
        rgb_reflectance=0.55,
        modifier=base_glow["target"],
    )
    assert chained_plastic["object_dict"]["modifier"]["identifier"] == "parent_glow"

    # Exercise every newly supported modifier type
    for mod_type, kwargs in [
        ("bsdf", {"params": {"bsdf_file": str(bsdf_xml), "thickness": 0.02}}),
        ("absdf", {"params": {"bsdf_file": str(bsdf_xml)}}),
        ("light", {"params": {"rgb_emittance": [10.0, 10.0, 10.0]}}),
        ("spotlight", {"params": {"rgb_emittance": [5.0, 5.0, 5.0], "angle": 45.0, "direction": [0, 0, -1]}}),
        ("illum", {"params": {"rgb_emittance": [1.0, 1.0, 1.0], "alternate_material": "void"}}),
        ("dielectric", {"params": {"rgb_transmission": [0.9, 0.9, 0.9], "refraction_index": 1.52}}),
        ("brtdfunc", {"params": {"is_opaque": False}}),
        ("plastic2", {"params": {"rgb_reflectance": 0.4, "specularity": 0.05, "u_roughness": 0.1, "v_roughness": 0.2}}),
        ("metal2", {"params": {"rgb_reflectance": 0.6, "specularity": 0.8, "u_roughness": 0.05, "v_roughness": 0.1}}),
        ("trans2", {"params": {"rgb_reflectance": 0.3, "transmitted_diff": 0.2, "transmitted_spec": 0.1, "u_roughness": 0.05, "v_roughness": 0.1}}),
        ("raw_rad", {"params": {"rad_text": "void plastic custom_raw_p\n0\n0\n5 0.5 0.5 0.5 0 0"}}),
    ]:
        created = modifiers.create_radiance_modifier(
            garden_root=str(garden_root),
            modifier_type=mod_type,
            identifier=f"mod_{mod_type}",
            **kwargs,
        )
        assert created["object_dict"]["identifier"]

    # RAD_Create_Modifier_Set via MCP tool (with base_modifier_set inheritance + persistence)
    mcp = _build_raw_mcp()

    async def _create_mod_set() -> None:
        async with Client(mcp) as client:
            res = _parse_mcp_json(
                await client.call_tool(
                    "RAD_Create_Modifier_Set",
                    {
                        "garden_root": str(garden_root),
                        "identifier": "Custom_Office_Modifiers",
                        "base_modifier_set": "Generic_Interior_Visible_Modifier_Set",
                        "wall_set": {"interior_modifier": chained_plastic["target"]},
                        "return_detail": "full",
                    },
                )
            )
            assert res["target"]["identifier"] == "Custom_Office_Modifiers"
            assert res["summary_view"]["wall_set"]["interior_modifier"] == "chained_wall"
            assert "object_dict" in res

    asyncio.run(_create_mod_set())


# ---------------------------------------------------------------------------
# 10. Dynamic aperture grouping + direct modifiers/tmtx + Luminaires list/remove
# ---------------------------------------------------------------------------


def test_dynamic_apertures_auto_group_and_luminaires(tmp_path: Path) -> None:
    garden_root = Path(create_garden(name="dyn_lum_garden", root_dir=str(tmp_path))["garden_root"])
    manifest = GardenManifest.read(garden_root)
    _, model_target = _build_and_save_box_model(garden_root, name="dyn_box")
    hb_model = load_honeybee_model(garden_root=garden_root, model_target=model_target)
    ap_id = hb_model.apertures[0].identifier

    direct_mod = modifiers.create_radiance_modifier(
        garden_root=str(garden_root),
        modifier_type="glass",
        identifier="shade_direct_glass",
        rgb_transmittance=0.05,
    )
    base_mod = modifiers.create_radiance_modifier(
        garden_root=str(garden_root),
        modifier_type="glass",
        identifier="shade_diff_glass",
        rgb_transmittance=0.25,
    )

    ap_target = {
        "target_type": "honeybee_object",
        "domain": "honeybee",
        "model_identifier": hb_model.identifier,
        "object_type": "aperture",
        "object_identifier": ap_id,
        "model_target": model_target,
    }
    state_geo = [
        [0.5, 0.0, 1.0],
        [3.5, 0.0, 1.0],
        [3.5, 0.0, 2.0],
        [0.5, 0.0, 2.0],
    ]
    dyn_res = dynamic.setup_radiance_dynamic_group(
        garden_root=str(garden_root),
        targets=[ap_target],
        dynamic_group_identifier="SouthShade",
        states=[
            {
                "modifier": base_mod["target"],
                "modifier_direct": direct_mod["target"],
                "shades": [{"vertices": state_geo, "identifier": "louver_1"}],
                "tmtx_thickness": 0.2,
            }
        ],
    )
    assert dyn_res["summary_view"]["updated_count"] == 1

    # Reload model & verify modifier_direct & vmtx/dmtx geometries survived SDK quirk
    hb_reloaded = load_honeybee_model(garden_root=garden_root, model_target=model_target)
    st0 = hb_reloaded.apertures[0].properties.radiance.states[0]
    assert st0.modifier_direct is not None and st0.modifier_direct.identifier == "shade_direct_glass"
    assert st0.vmtx_geometry is not None and st0.dmtx_geometry is not None

    # Automatic aperture grouping (both view_factor_or_orientation=False & True)
    auto_orient = dynamic.setup_radiance_dynamic_group(
        garden_root=str(garden_root),
        operation="auto_group",
        model_target=model_target,
        view_factor_or_orientation=False,
    )
    assert auto_orient["summary_view"]["grouped_aperture_count"] >= 1

    auto_vf = dynamic.setup_radiance_dynamic_group(
        garden_root=str(garden_root),
        operation="auto_group",
        model_target=model_target,
        view_factor_or_orientation=True,
        size=1.0,
        ambient_division=100,
    )
    assert auto_vf["summary_view"]["grouped_aperture_count"] >= 1

    # Luminaires: CustomLamp.from_lamp_name, attach, list, remove
    ies_sample = (
        "IESNA:LM-63-2002\n"
        "[TEST] Simple Downlight\n"
        "[MANUFAC] TestCo\n"
        "TILT=NONE\n"
        "1 1000 1 3 1 1 1 0.5 0.5 0.1\n"
        "1 1 100\n"
        "0 45 90\n"
        "0\n"
        "100 70 10\n"
    )
    lum = luminaires.create_radiance_luminaire(
        garden_root=str(garden_root),
        identifier="office_troffer",
        ies_content=ies_sample,
        custom_lamp={"lamp_name": "fluorescent"},
        instances=[{"point": [2.0, 2.5, 2.8]}],
    )
    assert lum["summary_view"]["identifier"] == "office_troffer"

    listed = luminaires.list_radiance_luminaires(garden_root=str(garden_root))
    assert any(item["identifier"] == "office_troffer" for item in listed["library_luminaires"])

    hb_for_lum = load_honeybee_model(garden_root=garden_root, model_target=model_target)
    hb_for_lum.properties.radiance.add_luminaire(HbLuminaire.from_dict(lum["object_dict"]))
    save_honeybee_model(garden_root=garden_root, manifest=manifest, model=hb_for_lum, name=hb_for_lum.identifier)

    listed_with_model = luminaires.list_radiance_luminaires(
        garden_root=str(garden_root),
        model_target=model_target,
    )
    assert len(listed_with_model["model_luminaires"]) == 1

    removed = luminaires.remove_radiance_luminaire_from_model(
        garden_root=str(garden_root),
        model_target=model_target,
        luminaire_identifiers=["office_troffer"],
        remove_from_library=True,
    )
    assert "office_troffer" in removed["summary_view"]["removed_identifiers"]
    assert len(removed["summary_view"]["removed_library_paths"]) == 1
    assert not (garden_root / "libraries" / "honeybee_radiance" / "luminaires" / "office_troffer.json").exists()
