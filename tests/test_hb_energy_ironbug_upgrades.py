"""Comprehensive tests for Honeybee Core, Energy Authoring, Simulation/Post-Processing, and Ironbug upgrades."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client, FastMCP
from honeybee.boundarycondition import Adiabatic, Ground, OtherSideTemperature, Outdoors, boundary_conditions
from honeybee.face import Face
from honeybee.facetype import face_types
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.lib.constructions import generic_exterior_wall
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D

from garden.honeybee_core.edit import (
    edit_honeybee_face,
    edit_honeybee_model,
    edit_honeybee_objects,
    edit_honeybee_room,
)
from garden.honeybee_core.model_io import load_honeybee_model
from garden.honeybee_core.repair import repair_honeybee_model
from garden.honeybee_core.room_energy import apply_room_energy_properties
from garden.store import create_garden
from ladybug_tools_mcp.registry import register_tools


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "Upgrade Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


@pytest.fixture(scope="module")
def raw_mcp() -> FastMCP:
    return _make_raw_mcp()


def _parse_tool_result(res: Any) -> dict[str, Any]:
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
    raise AssertionError(f"Unable to parse FastMCP tool result: {res!r}")


async def _call(mcp: FastMCP, name: str, args: dict[str, Any]) -> dict[str, Any]:
    async with Client(mcp) as client:
        res = await client.call_tool(name, args)
        return _parse_tool_result(res)


def _create_box_garden(tmp_path: Path, name: str = "hb_upg", *, two_rooms: bool = False) -> tuple[str, dict[str, Any]]:
    g_root = str(tmp_path / name)
    create_garden(name=name, root_dir=g_root)
    mcp = _make_raw_mcp()
    m_res = asyncio.run(_call(mcp, "HB_Create_Model", {"garden_root": g_root, "identifier": f"{name}_model"}))
    asyncio.run(
        _call(
            mcp,
            "HB_Create_Objects",
            {
                "garden_root": g_root,
                "object_type": "room",
                "identifier": "Room_1",
                "x_dim": 4.0,
                "y_dim": 5.0,
                "height": 3.0,
            },
        )
    )
    if two_rooms:
        asyncio.run(
            _call(
                mcp,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "identifier": "Room_2",
                    "x_dim": 4.0,
                    "y_dim": 5.0,
                    "height": 3.0,
                    "origin": [4.0, 0.0, 0.0],
                },
            )
        )
    return g_root, m_res["target"]


# ---------------------------------------------------------------------------
# Section 1: Honeybee Core Bug Fixes, Room Energy Overrides, Imports & Repair
# ---------------------------------------------------------------------------


def test_hb_edit_model_units_convert_geometry_and_flag(tmp_path: Path, raw_mcp: FastMCP) -> None:
    g_root, model_target = _create_box_garden(tmp_path, "units_g")

    # convert_geometry=True scales coordinates and tolerance from Meters -> Millimeters
    res_scaled = asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Model",
            {
                "garden_root": g_root,
                "target": model_target,
                "units": "Millimeters",
                "convert_geometry": True,
            },
        )
    )
    assert res_scaled["persistence_receipt"]["status"] == "persisted"
    scaled_model = load_honeybee_model(Path(g_root), res_scaled["target"])
    assert scaled_model.units == "Millimeters"
    assert pytest.approx(scaled_model.rooms[0].floor_area, rel=1e-4) == 20.0 * 1_000_000.0
    assert pytest.approx(scaled_model.tolerance, rel=1e-4) == 10.0

    # convert_geometry=False updates only the units label
    res_label = edit_honeybee_model(
        garden_root=g_root,
        target=res_scaled["target"],
        units="Meters",
        convert_geometry=False,
    )
    label_model = load_honeybee_model(Path(g_root), res_label["persistence_receipt"]["model_target"])
    assert label_model.units == "Meters"
    assert pytest.approx(label_model.rooms[0].floor_area, rel=1e-4) == 20.0 * 1_000_000.0


def test_hb_boundary_condition_full_dicts_and_air_boundary_and_modifier_set(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root, model_target = _create_box_garden(tmp_path, "bc_air_mod")
    search = asyncio.run(
        _call(
            raw_mcp,
            "HB_Search_Model_Objects",
            {"garden_root": g_root, "object_type": "face", "room_identifier": "Room_1", "face_type": "Wall"},
        )
    )
    wall_target = search["matches"][0]["target"]
    wall_target_2 = search["matches"][1]["target"]

    # Full Outdoors dict preserves sun/wind/view_factor
    out_res = edit_honeybee_face(
        garden_root=g_root,
        target=wall_target,
        boundary_condition={
            "type": "Outdoors",
            "sun_exposure": False,
            "wind_exposure": False,
            "view_factor": 0.25,
        },
    )
    m_after_out = load_honeybee_model(Path(g_root), out_res["persistence_receipt"]["model_target"])
    f1 = m_after_out.faces_by_identifier([wall_target["object_identifier"]])[0]
    assert isinstance(f1.boundary_condition, Outdoors)
    assert f1.boundary_condition.sun_exposure is False
    assert f1.boundary_condition.wind_exposure is False
    assert pytest.approx(f1.boundary_condition.view_factor) == 0.25

    # Full OtherSideTemperature dict
    ost_res = edit_honeybee_face(
        garden_root=g_root,
        target=wall_target,
        boundary_condition={
            "type": "OtherSideTemperature",
            "temperature": 18.5,
            "heat_transfer_coefficient": 4.5,
        },
    )
    m_after_ost = load_honeybee_model(Path(g_root), ost_res["persistence_receipt"]["model_target"])
    f1_ost = m_after_ost.faces_by_identifier([wall_target["object_identifier"]])[0]
    assert isinstance(f1_ost.boundary_condition, OtherSideTemperature)
    assert pytest.approx(f1_ost.boundary_condition.temperature) == 18.5
    assert pytest.approx(f1_ost.boundary_condition.heat_transfer_coefficient) == 4.5

    # Adiabatic & Ground dicts
    adiab_res = edit_honeybee_face(
        garden_root=g_root,
        target=wall_target,
        boundary_condition={"type": "Adiabatic"},
    )
    assert adiab_res["object_dict"]["boundary_condition"]["type"] == "Adiabatic"
    gnd_res = edit_honeybee_face(
        garden_root=g_root,
        target=wall_target,
        boundary_condition={"type": "Ground"},
    )
    assert gnd_res["object_dict"]["boundary_condition"]["type"] == "Ground"

    # AirBoundaryConstruction allowed on AirBoundary faces (single & batch)
    air_constr = AirBoundaryConstruction("Custom_Air_Boundary").to_dict()
    air_res = edit_honeybee_face(
        garden_root=g_root,
        target=wall_target,
        type="AirBoundary",
        construction=air_constr,
    )
    assert air_res["object_dict"]["properties"]["energy"]["construction"]["identifier"] == "Custom_Air_Boundary"

    batch_air = edit_honeybee_objects(
        garden_root=g_root,
        targets=[wall_target_2],
        face_type="AirBoundary",
        construction=air_constr,
    )
    assert batch_air["persistence_receipt"]["status"] == "persisted"

    # AirBoundaryConstruction rejected on non-AirBoundary Wall face
    wall_target_3 = search["matches"][2]["target"]
    with pytest.raises(ValueError, match="opaque construction"):
        edit_honeybee_face(
            garden_root=g_root,
            target=wall_target_3,
            construction=air_constr,
        )

    # Built-in Radiance standards modifier_set identifier string
    mod_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "target": "Room_1",
                "modifier_set": "Generic_Interior_Visible_Modifier_Set",
            },
        )
    )
    assert mod_res["object_dict"]["properties"]["radiance"]["modifier_set"]["identifier"] == "Generic_Interior_Visible_Modifier_Set"


def test_hb_edit_objects_room_energy_overrides_and_reset_fields(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root, _ = _create_box_garden(tmp_path, "room_energy_g", two_rooms=True)

    # Override individual loads, process_loads, internal_masses, shw, window_vent_control, daylighting_control
    res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "program_type": "Generic Office Program",
                "people": {"identifier": "Ov_People", "people_per_area": 0.12},
                "lighting": {"identifier": "Ov_Light", "watts_per_area": 7.5},
                "electric_equipment": {"identifier": "Ov_Elec", "watts_per_area": 6.0},
                "gas_equipment": {"identifier": "Ov_Gas", "watts_per_area": 1.5},
                "service_hot_water": {"identifier": "Ov_SHW_Load", "flow_per_area": 0.0002},
                "infiltration": {"identifier": "Ov_Inf", "flow_per_exterior_area": 0.0003},
                "process_loads": [{"identifier": "Kiln_1", "watts": 450.0, "fuel_type": "Electricity"}],
                "internal_masses": [
                    {"identifier": "Mass_1", "construction": generic_exterior_wall.to_dict(), "area": 12.0}
                ],
                "shw": {
                    "identifier": "SHW_HP",
                    "equipment_type": "HeatPump_WaterHeater",
                    "heater_efficiency": 3.5,
                    "ambient_condition": "Room_1",
                },
                "window_vent_control": {"min_indoor_temperature": 21.0, "max_indoor_temperature": 27.0},
                "daylighting_control": {"sensor_position": [2.0, 2.5, 0.8], "illuminance_setpoint": 400.0},
            },
        )
    )
    assert res["persistence_receipt"]["status"] == "persisted"
    model = load_honeybee_model(Path(g_root), res["model_target"])
    e1 = model.rooms_by_identifier(["Room_1"])[0].properties.energy
    assert e1.people.identifier == "Ov_People"
    assert e1.lighting.identifier == "Ov_Light"
    assert e1.electric_equipment.identifier == "Ov_Elec"
    assert e1.gas_equipment.identifier == "Ov_Gas"
    assert e1.service_hot_water.identifier == "Ov_SHW_Load"
    assert e1.infiltration.identifier == "Ov_Inf"
    assert [p.identifier for p in e1.process_loads] == ["Kiln_1"]
    assert [m.identifier for m in e1.internal_masses] == ["Mass_1"]
    assert e1.shw.identifier == "SHW_HP"
    assert pytest.approx(e1.window_vent_control.min_indoor_temperature) == 21.0
    assert pytest.approx(e1.daylighting_control.illuminance_setpoint) == 400.0

    # Reset lighting + collections + controls via reset_fields
    reset_res = apply_room_energy_properties(
        garden_root=g_root,
        room_identifiers=["Room_1"],
        reset_fields=["lighting", "process_loads", "internal_masses", "shw", "window_vent_control", "daylighting_control"],
    )
    m_after_reset = load_honeybee_model(Path(g_root), reset_res["model_target"])
    e1_reset = m_after_reset.rooms_by_identifier(["Room_1"])[0].properties.energy
    assert e1_reset._lighting is None
    assert e1_reset.lighting.identifier == e1_reset.program_type.lighting.identifier
    assert list(e1_reset.process_loads) == []
    assert list(e1_reset.internal_masses) == []
    assert e1_reset.shw is None
    assert e1_reset.window_vent_control is None
    assert e1_reset.daylighting_control is None

    # make_plenum on Room_2
    plenum_res = edit_honeybee_room(
        garden_root=g_root,
        target="Room_2",
        make_plenum={"conditioned": False, "remove_infiltration": True, "include_floor_area": False},
    )
    m_plenum = load_honeybee_model(Path(g_root), plenum_res["persistence_receipt"]["model_target"])
    r2 = m_plenum.rooms_by_identifier(["Room_2"])[0]
    assert r2.exclude_floor_area is True
    assert r2.properties.energy.hvac is None
    assert r2.properties.energy._infiltration is None

    # make_ground on Room_2
    ground_res = edit_honeybee_room(
        garden_root=g_root,
        target="Room_2",
        make_ground={"soil_construction": generic_exterior_wall.to_dict(), "include_floor_area": False},
    )
    m_ground = load_honeybee_model(Path(g_root), ground_res["persistence_receipt"]["model_target"])
    r2_g = m_ground.rooms_by_identifier(["Room_2"])[0]
    assert r2_g.exclude_floor_area is True
    assert all(
        isinstance(f.boundary_condition, (Outdoors, Ground)) for f in r2_g.faces
    )


def test_hb_create_model_multi_format_imports(tmp_path: Path, raw_mcp: FastMCP) -> None:
    import honeybee_doe2.writer as hdw
    import honeybee_openstudio.writer as how

    g_root = str(tmp_path / "import_formats_g")
    create_garden(name="import_formats_g", root_dir=g_root)
    imports_dir = Path(g_root) / "imports"
    imports_dir.mkdir(parents=True, exist_ok=True)

    box_room = Room.from_box("ImpRoom", 4.0, 5.0, 3.0)
    base_model = Model("ImpSource", rooms=[box_room])

    osm_path = imports_dir / "model.osm"
    osm_path.write_text(how.model_to_osm(base_model), encoding="utf-8")

    idf_path = imports_dir / "model.idf"
    idf_path.write_text(how.model_to_idf(base_model), encoding="utf-8")

    gbxml_path = imports_dir / "model.gbxml"
    gbxml_path.write_text(how.model_to_gbxml(base_model), encoding="utf-8")

    inp_path = imports_dir / "model.inp"
    inp_path.write_text(hdw.model_to_inp(base_model), encoding="utf-8")

    base_model.to_hbpkl(name="model", folder=str(imports_dir))

    stl_path = imports_dir / "shade.stl"
    stl_path.write_text(
        "solid tri_shade\n"
        "  facet normal 0 0 1\n"
        "    outer loop\n"
        "      vertex 0 0 0\n"
        "      vertex 2 0 0\n"
        "      vertex 0 2 0\n"
        "    endloop\n"
        "  endfacet\n"
        "endsolid tri_shade\n",
        encoding="utf-8",
    )

    for rel, ext_id, expect_key, expect_min in (
        ("imports/model.osm", "m_osm", "room_count", 1),
        ("imports/model.idf", "m_idf", "room_count", 1),
        ("imports/model.gbxml", "m_gbxml", "room_count", 1),
        ("imports/model.inp", "m_inp", "room_count", 1),
        ("imports/model.hbpkl", "m_hbpkl", "room_count", 1),
        ("imports/shade.stl", "m_stl_mesh", "shade_mesh_count", 1),
    ):
        res = asyncio.run(
            _call(
                raw_mcp,
                "HB_Create_Model",
                {
                    "garden_root": g_root,
                    "import_file_path": rel,
                    "identifier": ext_id,
                    "set_base": False,
                },
            )
        )
        assert res["summary_view"][expect_key] >= expect_min
        assert res["summary_view"]["model_identifier"] == ext_id

    stl_faces_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Create_Model",
            {
                "garden_root": g_root,
                "import_file_path": "imports/shade.stl",
                "identifier": "m_stl_faces",
                "geometry_to_faces": True,
                "set_base": False,
            },
        )
    )
    assert stl_faces_res["summary_view"]["orphaned_face_count"] == 1


def test_hb_repair_model_all_actions(tmp_path: Path, raw_mcp: FastMCP) -> None:
    g_root = str(tmp_path / "repair_g")
    create_garden(name="repair_g", root_dir=g_root)

    # 1. Build a rich model with hole, non-planar quad shade, degenerate shade, overlapping apertures,
    #    far origin, and missing Surface adjacency.
    r1 = Room.from_box("R1", 4.0, 4.0, 3.0, origin=Point3D(1000.0, 2000.0, 0.0))
    # Face with a hole (split_rooms_through_holes)
    outer = [Point3D(0, 0, 0), Point3D(6, 0, 0), Point3D(6, 0, 4), Point3D(0, 0, 4)]
    hole = [Point3D(2, 0, 1), Point3D(4, 0, 1), Point3D(4, 0, 3), Point3D(2, 0, 3)]
    hole_face = Face("HoleWall", Face3D(outer, holes=[hole]))
    r_hole = Room.from_box("RHole", 6.0, 4.0, 4.0, origin=Point3D(10.0, 0.0, 0.0))
    r_hole._faces = tuple(
        hole_face if f.geometry.normal.y < -0.9 else f for f in r_hole.faces
    )
    for f in r_hole._faces:
        f._parent = r_hole

    # Room with broken Surface adjacency + overlapping apertures on Outdoors wall
    r_adj = Room.from_box("RAdj", 4.0, 4.0, 3.0, origin=Point3D(0.0, 0.0, 0.0))
    ghost_room = Room.from_box("GhostRoom", 4.0, 4.0, 3.0, origin=Point3D(-4.0, 0.0, 0.0))
    wall0 = r_adj.faces[1]  # Wall
    wall0.boundary_condition = boundary_conditions.surface(ghost_room.faces[1])
    # Invalid overlapping apertures extending past wall edge on wall 2
    wall_out = r_adj.faces[2]
    ap_a = wall_out.geometry
    from honeybee.aperture import Aperture

    ap1 = Aperture("Ap1", Face3D([Point3D(4, 0.5, 0.5), Point3D(4, 2.5, 0.5), Point3D(4, 2.5, 2.5), Point3D(4, 0.5, 2.5)]))
    ap2 = Aperture("Ap2", Face3D([Point3D(4, 1.5, 0.5), Point3D(4, 4.2, 0.5), Point3D(4, 4.2, 2.5), Point3D(4, 1.5, 2.5)]))
    wall_out.add_aperture(ap1)
    wall_out.add_aperture(ap2)

    # Second floor room for assign_stories_by_floor_height
    r_top = Room.from_box("RTop", 4.0, 4.0, 3.0, origin=Point3D(0.0, 0.0, 3.0))

    # Non-planar quad shade + degenerate tiny shade
    np_shade = Shade(
        "NonPlanarShade",
        Face3D([Point3D(0, 0, 0), Point3D(2, 0, 0), Point3D(2, 2, 0.5), Point3D(0, 2, 0)]),
    )
    deg_shade = Shade(
        "DegShade",
        Face3D([Point3D(0, 0, 0), Point3D(0.001, 0, 0), Point3D(0, 0.001, 0)]),
    )

    m = Model("RepairTarget", rooms=[r1, r_hole, r_adj, r_top], orphaned_shades=[np_shade, deg_shade])
    from garden.honeybee_core.model_io import save_honeybee_model
    from garden.manifest import GardenManifest

    manifest = GardenManifest.read(Path(g_root))
    m_target, _ = save_honeybee_model(Path(g_root), manifest, m, name="RepairTarget", set_base=True)

    # Second model for add_model and comparison_report
    other_m = Model("OtherModel", rooms=[Room.from_box("ExtraRoom", 3.0, 3.0, 3.0, origin=Point3D(20.0, 0.0, 0.0))])
    other_target, _ = save_honeybee_model(Path(g_root), manifest, other_m, name="OtherModel", set_base=False)

    # Test comparison_report (read-only)
    cmp_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Repair_Model",
            {
                "garden_root": g_root,
                "action": "comparison_report",
                "model_target": m_target,
                "other_model_target": other_target,
            },
        )
    )
    assert "added_objects" in cmp_res["comparison_report"]
    assert "deleted_objects" in cmp_res["comparison_report"]

    # Test missing_adjacencies_to_adiabatic
    adj_res = repair_honeybee_model(
        garden_root=g_root,
        action="missing_adjacencies_to_adiabatic",
        model_target=m_target,
    )
    assert adj_res["summary_view"]["converted_face_count"] == 1
    m_after_adj = load_honeybee_model(Path(g_root), adj_res["model_target"])
    assert m_after_adj.check_missing_adjacencies(raise_exception=False) == ""

    # Test fix_invalid_sub_faces
    sub_res = repair_honeybee_model(
        garden_root=g_root,
        action="fix_invalid_sub_faces",
        model_target=adj_res["model_target"],
    )
    assert sub_res["summary_view"]["modified_face_count"] >= 1

    # Test remove_degenerate_geometry (removes DegShade)
    deg_res = repair_honeybee_model(
        garden_root=g_root,
        action="remove_degenerate_geometry",
        model_target=sub_res["model_target"],
    )
    assert deg_res["summary_view"]["counts_after"]["orphaned_shades"] < deg_res["summary_view"]["counts_before"]["orphaned_shades"]

    # Test triangulate_non_planar_quads (splits NonPlanarShade into 2 triangles)
    tri_res = repair_honeybee_model(
        garden_root=g_root,
        action="triangulate_non_planar_quads",
        model_target=deg_res["model_target"],
    )
    assert tri_res["summary_view"]["counts_after"]["orphaned_shades"] > tri_res["summary_view"]["counts_before"]["orphaned_shades"]

    # Test split_rooms_through_holes
    split_res = repair_honeybee_model(
        garden_root=g_root,
        action="split_rooms_through_holes",
        model_target=tri_res["model_target"],
    )
    assert split_res["summary_view"]["split_face_count"] >= 2

    # Test clean_envelope
    env_res = repair_honeybee_model(
        garden_root=g_root,
        action="clean_envelope",
        model_target=split_res["model_target"],
    )
    assert env_res["summary_view"]["cleaned_room_count"] == 4

    # Test rooms_to_extrusions
    ext_res = repair_honeybee_model(
        garden_root=g_root,
        action="rooms_to_extrusions",
        model_target=env_res["model_target"],
    )
    assert ext_res["summary_view"]["counts_after"]["rooms"] == 4

    # Test assign_stories_by_floor_height
    st_res = repair_honeybee_model(
        garden_root=g_root,
        action="assign_stories_by_floor_height",
        model_target=ext_res["model_target"],
        overwrite=True,
    )
    assert st_res["summary_view"]["story_count"] >= 2

    # Test reset_coordinate_system
    orig_res = repair_honeybee_model(
        garden_root=g_root,
        action="reset_coordinate_system",
        model_target=st_res["model_target"],
    )
    assert all(pytest.approx(v, abs=1e-6) == 0.0 for v in orig_res["summary_view"]["model_min_after"])

    # Test add_model with prefix
    merge_res = repair_honeybee_model(
        garden_root=g_root,
        action="add_model",
        model_target=orig_res["model_target"],
        other_model_target=other_target,
        other_model_prefix="WingB_",
    )
    assert merge_res["summary_view"]["counts_after"]["rooms"] == 5

    # Test clean_irrational_geometry (inject an irrational degenerate room directly in HBJSON)
    hb_path = Path(g_root) / merge_res["model_target"]["path"]
    raw_dict = json.loads(hb_path.read_text(encoding="utf-8"))
    raw_dict["rooms"].append(
        {
            "type": "Room",
            "identifier": "BadEmptyRoom",
            "faces": [
                {
                    "type": "Face",
                    "identifier": "BadFace",
                    "geometry": {"type": "Face3D", "boundary": [[0, 0, 0], [1, 0, 0]]},
                    "face_type": "Wall",
                    "boundary_condition": {"type": "Outdoors"},
                }
            ],
        }
    )
    hb_path.write_text(json.dumps(raw_dict), encoding="utf-8")
    irr_res = repair_honeybee_model(
        garden_root=g_root,
        action="clean_irrational_geometry",
        model_target=merge_res["model_target"],
    )
    assert irr_res["summary_view"]["raw_rooms_before"] == 6
    assert irr_res["summary_view"]["raw_rooms_after"] == 5


# ---------------------------------------------------------------------------
# Section 2: Energy Authoring Upgrades
# ---------------------------------------------------------------------------


def test_energy_constructions_shade_dynamic_and_aperture_set(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root = str(tmp_path / "energy_constr_g")
    create_garden(name="energy_constr_g", root_dir=g_root)

    win_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Construction",
            {
                "construction_type": "window",
                "identifier": "Base_Double_Win",
                "u_factor": 1.8,
                "shgc": 0.45,
                "vt": 0.65,
                "garden_root": g_root,
            },
        )
    )
    shade_mat_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Material",
            {
                "material_type": "window_shade",
                "identifier": "Roller_Shade_Mat",
                "params": {"solar_transmittance": 0.25, "visible_transmittance": 0.2},
                "garden_root": g_root,
            },
        )
    )
    win_shade_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Construction",
            {
                "construction_type": "window_shade",
                "identifier": "Shaded_Double_Win",
                "params": {
                    "window_construction": win_res["target"],
                    "shade_material": shade_mat_res["target"],
                    "shade_location": "Interior",
                    "control_type": "OnIfHighSolarOnWindow",
                    "setpoint": 150.0,
                },
                "garden_root": g_root,
            },
        )
    )
    assert win_shade_res["object_dict"]["type"] == "WindowConstructionShade"

    win2_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Construction",
            {
                "construction_type": "window",
                "identifier": "Tinted_Double_Win",
                "u_factor": 1.6,
                "shgc": 0.22,
                "vt": 0.3,
                "garden_root": g_root,
            },
        )
    )
    dyn_tl = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Dyn_Discrete_TL",
                "schedule_type": "type_limit",
                "lower_limit": 0,
                "upper_limit": 1,
                "numeric_type": "Discrete",
                "unit_type": "Dimensionless",
                "garden_root": g_root,
            },
        )
    )
    sched_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Dyn_Step_Sched",
                "default_day_schedule": [0] * 24,
                "rules": [{"start_time": "08:00", "end_time": "18:00", "value": 1, "days": ["weekdays"]}],
                "schedule_type_limit": dyn_tl["target"],
                "garden_root": g_root,
                "return_data": False,
            },
        )
    )
    win_dyn_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Construction",
            {
                "construction_type": "window_dynamic",
                "identifier": "EC_Dynamic_Win",
                "params": {
                    "constructions": [win_res["target"], win2_res["target"]],
                    "schedule": sched_res["target"],
                },
                "garden_root": g_root,
            },
        )
    )
    assert win_dyn_res["object_dict"]["type"] == "WindowConstructionDynamic"

    cset_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Construction_Set",
            {
                "identifier": "Adv_Win_CSet",
                "aperture_set": {
                    "window_construction": win_shade_res["target"],
                    "operable_construction": win_dyn_res["target"],
                },
                "garden_root": g_root,
            },
        )
    )
    ap_set = cset_res["object_dict"]["aperture_set"]
    assert ap_set["window_construction"]["identifier"] == "Shaded_Double_Win"
    assert ap_set["operable_construction"]["identifier"] == "EC_Dynamic_Win"


def test_energy_loads_process_mass_shw_exhaust_and_schedules(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root, _ = _create_box_garden(tmp_path, "energy_loads_g")

    # Process load -> Garden library -> HB_Edit_Objects
    proc_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Load",
            {
                "load_type": "process",
                "identifier": "Lab_Oven",
                "params": {"watts": 1200.0, "fuel_type": "NaturalGas", "end_use_category": "Ovens"},
                "garden_root": g_root,
                "return_object_dict": False,
            },
        )
    )
    assert proc_res["target"]["object_family"] == "process"

    # InternalMass -> Garden library -> HB_Edit_Objects
    mass_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Load",
            {
                "load_type": "internal_mass",
                "identifier": "Concrete_Furniture",
                "params": {"construction": generic_exterior_wall.to_dict(), "area": 18.0},
                "garden_root": g_root,
                "return_object_dict": False,
            },
        )
    )
    assert mass_res["target"]["object_family"] == "internal_mass"

    # SHWSystem via EP_Create_Load and EP_Create_HVAC_Template
    shw_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Load",
            {
                "load_type": "shw_system",
                "identifier": "Boiler_SHW",
                "params": {"equipment_type": "Gas_WaterHeater", "heater_efficiency": 0.85},
                "garden_root": g_root,
                "return_object_dict": False,
            },
        )
    )
    assert shw_res["target"]["object_family"] == "shw_system"

    shw_hvac_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_HVAC_Template",
            {
                "system_type": "SHWSystem",
                "identifier": "Elec_SHW",
                "equipment_type": "Electric_WaterHeater",
                "heater_efficiency": 0.98,
                "garden_root": g_root,
            },
        )
    )
    assert shw_hvac_res["object_dict"]["type"] == "SHWSystem"

    # ExhaustAir guard on honeybee-energy 1.124.5 (or native if upgraded)
    from garden.energy.programtypes import ExhaustAir as _ExhaustCls

    if _ExhaustCls is None:
        with pytest.raises(Exception, match="1.125|zone_ventilation_fan"):
            asyncio.run(
                _call(
                    raw_mcp,
                    "EP_Create_Load",
                    {"load_type": "exhaust_air", "identifier": "Ex1", "params": {"flow_per_area": 0.001}},
                )
            )

    # Apply library targets from EP_Create_Load directly to Room_1 via HB_Edit_Objects
    apply_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "target": "Room_1",
                "process_loads": [proc_res["target"]],
                "internal_masses": [mass_res["target"]],
                "shw": shw_res["target"],
            },
        )
    )
    assert apply_res["persistence_receipt"]["status"] == "persisted"

    # ScheduleTypeLimit + ScheduleFixedInterval + ScheduleRuleset per-rule start_date/end_date
    tl_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Dimming_TL",
                "schedule_type": "type_limit",
                "lower_limit": 0.0,
                "upper_limit": 1.0,
                "numeric_type": "Continuous",
                "unit_type": "Dimensionless",
                "garden_root": g_root,
            },
        )
    )
    assert tl_res["object_dict"]["type"] == "ScheduleTypeLimit"

    fi_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Fixed_8760",
                "schedule_type": "fixed_interval",
                "values": [0.5] * 8760,
                "schedule_type_limit": tl_res["target"],
                "garden_root": g_root,
                "return_data": False,
            },
        )
    )
    assert fi_res["object_dict"]["type"] == "ScheduleFixedInterval"

    rs_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Seasonal_Rule",
                "default_day_schedule": [0.1] * 24,
                "rules": [
                    {
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "value": 0.9,
                        "days": ["weekdays"],
                        "start_date": [6, 1],
                        "end_date": [8, 31],
                    }
                ],
                "schedule_type_limit": tl_res["target"],
                "garden_root": g_root,
                "return_data": False,
            },
        )
    )
    assert len(rs_res["object_dict"]["schedule_rules"]) == 1
    assert rs_res["object_dict"]["schedule_rules"][0]["start_date"] == [6, 1]
    assert rs_res["object_dict"]["schedule_rules"][0]["end_date"] == [8, 31]


def test_energy_ventilation_schedule_filtering_daylight_sensor_and_clear(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root, model_target = _create_box_garden(tmp_path, "vent_ctrl_g")
    search = asyncio.run(
        _call(
            raw_mcp,
            "HB_Search_Model_Objects",
            {"garden_root": g_root, "object_type": "face", "room_identifier": "Room_1", "face_type": "Wall"},
        )
    )
    w0 = search["matches"][0]["target"]
    w1 = search["matches"][1]["target"]
    # Add two apertures and one door
    ap1_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Create_Apertures",
            {"garden_root": g_root, "host_target": w0, "ratio": 0.3, "identifier_prefix": "ApOne"},
        )
    )
    ap2_res = asyncio.run(
        _call(
            raw_mcp,
            "HB_Create_Apertures",
            {"garden_root": g_root, "host_target": w1, "ratio": 0.3, "identifier_prefix": "ApTwo"},
        )
    )
    aps = asyncio.run(
        _call(raw_mcp, "HB_Search_Model_Objects", {"garden_root": g_root, "object_type": "aperture"})
    )["matches"]
    ap1_id = next(m["identifier"] for m in aps if m["identifier"].startswith("ApOne"))
    ap2_id = next(m["identifier"] for m in aps if m["identifier"].startswith("ApTwo"))

    sched_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Schedule_Ruleset",
            {
                "identifier": "Vent_Avail",
                "default_day_schedule": [1.0] * 24,
                "schedule_type_limit": "Fractional",
                "garden_root": g_root,
                "return_data": False,
            },
        )
    )
    vent_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Setup_Room_Energy_Controls",
            {
                "control_type": "simple_ventilation",
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "params": {
                    "aperture_identifiers": [ap1_id],
                    "min_indoor_temperature": 22.0,
                    "schedule": sched_res["target"],
                },
            },
        )
    )
    assert vent_res["summary_view"]["window_vent_control"]["schedule"] == "Vent_Avail"
    m_after = load_honeybee_model(Path(g_root), vent_res["target"])
    aps_map = {a.identifier: a for a in m_after.apertures}
    assert aps_map[ap1_id].is_operable is True
    assert aps_map[ap2_id].is_operable is False

    # Custom daylight sensor position
    dl_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Setup_Room_Energy_Controls",
            {
                "control_type": "daylighting_control",
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "params": {"sensor_position": [1.5, 2.0, 0.85], "illuminance_setpoint": 500.0},
            },
        )
    )
    pos = dl_res["summary_view"]["controls"][0]["sensor_position"]
    assert pytest.approx([pos["x"], pos["y"], pos["z"]]) == [1.5, 2.0, 0.85]

    # clear=True removes controls cleanly
    clr_vent = asyncio.run(
        _call(
            raw_mcp,
            "EP_Setup_Room_Energy_Controls",
            {
                "control_type": "simple_ventilation",
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "clear": True,
            },
        )
    )
    clr_dl = asyncio.run(
        _call(
            raw_mcp,
            "EP_Setup_Room_Energy_Controls",
            {
                "control_type": "daylighting_control",
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "clear": True,
            },
        )
    )
    m_clr = load_honeybee_model(Path(g_root), clr_dl["target"])
    r1_e = m_clr.rooms[0].properties.energy
    assert r1_e.window_vent_control is None
    assert r1_e.daylighting_control is None
    assert all(a.properties.energy.vent_opening is None for a in m_clr.apertures)


# ---------------------------------------------------------------------------
# Section 4: Ironbug Bridge, EMS, Loop/Zone Config, Reverse-Parse & Templates
# ---------------------------------------------------------------------------


def _ironbug_live_available() -> bool:
    from garden.ironbug.runtime import IronbugRuntimeUnavailable, resolve_runtime_paths

    try:
        resolve_runtime_paths(require_openstudio=True)
        return True
    except IronbugRuntimeUnavailable:
        return False


@pytest.mark.skipif(not _ironbug_live_available(), reason="Ironbug + OpenStudio C# runtime unavailable")
def test_ironbug_ems_catalog_reverse_parse_loops_and_model_validation(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    g_root, model_target = _create_box_garden(tmp_path, "ib_upgrades_g")
    # Assign a program type + construction set so Room_1 satisfies Ironbug preconditions
    asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "program_type": "Generic Office Program",
                "construction_set": "Default Generic Construction Set",
            },
        )
    )

    # 1. CatalogInspector exposes AddEMSSensors / AddEMSInternalVariables / AddEMSActuators
    desc_res = asyncio.run(
        _call(
            raw_mcp,
            "IB_Describe_Component",
            {"type_names": ["IB_ChillerElectricEIR", "IB_ZoneHVACFourPipeFanCoil"], "include_advanced": True},
        )
    )
    chiller_desc = next(c for c in desc_res["components"] if c["type_name"] == "IB_ChillerElectricEIR")
    wiring_methods = {m.get("method") or m.get("method_name") or m.get("name") for m in chiller_desc.get("wiring_methods") or []}
    assert {"AddEMSSensors", "AddEMSInternalVariables", "AddEMSActuators"}.issubset(wiring_methods)

    # 2. Build a system with EMS sensors/internal variables/actuators, loop availability/bypass/branches,
    #    zone fields/output_variables/equipment_list_priorities, then validate against Honeybee model_target
    sys_res = asyncio.run(
        _call(
            raw_mcp,
            "IB_Create_System",
            {"garden_root": g_root, "identifier": "ib_ems_sys", "overwrite": True},
        )
    )
    ib_target = sys_res["target"]
    asyncio.run(
        _call(
            raw_mcp,
            "IB_Upsert_Components",
            {
                "garden_root": g_root,
                "ironbug_model_target": ib_target,
                "components": {
                    "fan": {"type": "IB_FanOnOff"},
                    "cc": {"type": "IB_CoilCoolingWater"},
                    "hc": {"type": "IB_CoilHeatingWater"},
                    "fcu": {
                        "type": "IB_ZoneHVACFourPipeFanCoil",
                        "fields": {"CapacityControlMethod": "CyclingFan"},
                        "wiring": {"fan": "fan", "cooling_coil": "cc", "heating_coil": "hc"},
                        "ems_sensors": [{"name": "FCU_Temp", "key_name": "*", "output_variable": "Zone Mean Air Temperature"}],
                    },
                    "chw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                    "chiller": {
                        "type": "IB_ChillerElectricEIR",
                        "fields": {"ReferenceCapacity": "autosize", "ReferenceCOP": 5.2, "CondenserType": "AirCooled"},
                        "ems_internal_variables": [{"name": "Chiller_Cap", "internal_data_type": "Chiller Nominal Capacity"}],
                        "ems_actuators": [
                            {
                                "name": "Chiller_Avail",
                                "actuated_component_type": "Chiller",
                                "actuated_component_control_type": "On/Off",
                            }
                        ],
                    },
                    "hw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                    "boiler": {
                        "type": "IB_BoilerHotWater",
                        "fields": {"FuelType": "NaturalGas", "NominalCapacity": "autosize", "NominalThermalEfficiency": 0.85},
                    },
                    "chw_am": {"type": "IB_AvailabilityManagerScheduled"},
                },
            },
        )
    )
    asyncio.run(
        _call(
            raw_mcp,
            "IB_Configure_Loops",
            {
                "garden_root": g_root,
                "ironbug_model_target": ib_target,
                "thermal_zones": [
                    {
                        "room_name": "Room_1",
                        "zone_equipments": ["fcu"],
                        "fields": {"Multiplier": 1},
                        "output_variables": [{"variable_name": "Zone Mean Air Temperature", "reporting_frequency": "Hourly"}],
                        "equipment_list_priorities": {"fcu": {"cooling_priority": 1, "heating_priority": 1}},
                    }
                ],
                "plant_loops": [
                    {
                        "name": "CHWLoop",
                        "loop_type": "Cooling",
                        "availability_managers": ["chw_am"],
                        "supply": ["chw_pump"],
                        "supply_branches": [["chiller"]],
                        "bypass_pipes": True,
                        "supply_setpoint": 6.7,
                        "demand_branches": [["cc"]],
                    },
                    {
                        "name": "HWLoop",
                        "loop_type": "Heating",
                        "supply": ["hw_pump"],
                        "supply_branches": [["boiler"]],
                        "bypass_pipes": True,
                        "supply_setpoint": 80.0,
                        "demand_branches": [["hc"]],
                    },
                ],
            },
        )
    )

    val_res = asyncio.run(
        _call(
            raw_mcp,
            "IB_Validate_System",
            {
                "garden_root": g_root,
                "ironbug_model_target": ib_target,
                "model_target": model_target,
                "run_forward_translator": True,
            },
        )
    )
    assert val_res["valid"] is True, val_res
    assert val_res["ready"] is True, val_res
    os_sum = val_res["openstudio_summary"]
    assert os_sum["ems_sensors"] >= 1
    assert os_sum["ems_internal_variables"] >= 1
    assert os_sum["ems_actuators"] >= 1
    assert val_res["forward_translator"]["error_count"] == 0

    # 3. Reverse-parse official IB_HVACSystem JSON into editable draft vs imported_only guard
    spec_path = Path(g_root) / ib_target["path"]
    spec_dict = json.loads(spec_path.read_text(encoding="utf-8"))

    # Default editable=False preserves imported_only=True guard
    ro_res = asyncio.run(
        _call(
            raw_mcp,
            "IB_Create_System",
            {"garden_root": g_root, "identifier": "imp_ro", "specification": spec_dict, "overwrite": True},
        )
    )
    assert ro_res["summary_view"]["imported_only"] is True

    # editable=True calls reverse_parse and allows subsequent component edits without replace=True
    ed_res = asyncio.run(
        _call(
            raw_mcp,
            "IB_Create_System",
            {
                "garden_root": g_root,
                "identifier": "imp_editable",
                "specification": spec_dict,
                "editable": True,
                "overwrite": True,
            },
        )
    )
    assert ed_res["summary_view"]["imported_only"] is False
    assert ed_res["summary_view"]["editable"] is True
    upsert_after_parse = asyncio.run(
        _call(
            raw_mcp,
            "IB_Upsert_Components",
            {
                "garden_root": g_root,
                "ironbug_model_target": ed_res["target"],
                "components": {"extra_sensor_fan": {"type": "IB_FanOnOff"}},
            },
        )
    )
    assert upsert_after_parse["persistence_receipt"]["status"] == "persisted"


@pytest.mark.skipif(not _ironbug_live_available(), reason="Ironbug + OpenStudio C# runtime unavailable")
@pytest.mark.parametrize("template_name", ["vav_chiller_boiler", "doas_fcu", "vrf_doas", "wshp"])
def test_ironbug_templates_create_and_validate(
    tmp_path: Path, raw_mcp: FastMCP, template_name: str
) -> None:
    g_root, model_target = _create_box_garden(tmp_path, f"ib_tpl_{template_name}")
    asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "program_type": "Generic Office Program",
                "construction_set": "Default Generic Construction Set",
            },
        )
    )
    created = asyncio.run(
        _call(
            raw_mcp,
            "IB_Create_System",
            {
                "garden_root": g_root,
                "identifier": f"sys_{template_name}",
                "template": template_name,
                "room_names": ["Room_1"],
                "overwrite": True,
            },
        )
    )
    assert created["summary_view"]["editable"] is True
    val = asyncio.run(
        _call(
            raw_mcp,
            "IB_Validate_System",
            {
                "garden_root": g_root,
                "ironbug_model_target": created["target"],
                "model_target": model_target,
                "run_forward_translator": True,
            },
        )
    )
    assert val["valid"] is True, val
    assert val["ready"] is True, val
    assert val["forward_translator"]["error_count"] == 0


# ===========================================================================
# 3. SimulationParameter, Measures, Weather read_data, & Energy Post-Processing
# ===========================================================================


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_weather_read_data_new_fields_and_batch(tmp_path: Path, raw_mcp: FastMCP) -> None:
    import shutil

    g_root = str(tmp_path / "wx_upg")
    create_garden(name="wx_upg", root_dir=g_root)
    weather_dir = Path(g_root) / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    epw_path = shutil.copy2(
        _repo_root() / "resources" / "dragonfly-energy" / "tests" / "epw" / "chicago.epw",
        weather_dir / "chicago.epw",
    )

    single = asyncio.run(
        _call(
            raw_mcp,
            "LB_Manage_Weather",
            {
                "garden_root": g_root,
                "action": "read_data",
                "epw_path": str(epw_path),
                "data_type": "wet_bulb_temperature",
                "include_values": True,
                "max_values": 4,
            },
        )
    )
    assert single["target"]["target_type"] == "ladybug_data_collection"
    assert single["summary_view"]["epw_data_type"] == "wet_bulb_temperature"
    assert single["summary_view"]["value_count"] == 8760
    assert len(single["summary_view"]["values"]) == 4

    batch = asyncio.run(
        _call(
            raw_mcp,
            "LB_Manage_Weather",
            {
                "garden_root": g_root,
                "action": "read_data",
                "epw_path": str(epw_path),
                "data_type": [
                    "dry_bulb_temperature",
                    "wet_bulb_temperature",
                    "years",
                    "present_weather_codes",
                    "present_weather_observation",
                ],
                "include_values": True,
                "max_values": 3,
            },
        )
    )
    assert batch["summary_view"]["collection_count"] == 5
    for field in (
        "dry_bulb_temperature",
        "wet_bulb_temperature",
        "years",
        "present_weather_codes",
        "present_weather_observation",
    ):
        assert field in batch["targets_by_field"]
        assert batch["results_by_field"][field]["summary_view"]["value_count"] == 8760


def test_simulation_parameter_fields_presets_and_inspect_measures(
    tmp_path: Path, raw_mcp: FastMCP
) -> None:
    import shutil

    g_root = str(tmp_path / "simpar_upg")
    create_garden(name="simpar_upg", root_dir=g_root)

    out_req = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Simulation_Parameter",
            {
                "garden_root": g_root,
                "mode": "output_request",
                "identifier": "out_new_presets",
                "presets": [
                    "zone_energy_use",
                    "plant_temperatures",
                    "plant_variables",
                    "stratification",
                    "comfort_map",
                ],
            },
        )
    )
    assert out_req["summary_view"]["output_count"] >= 40
    out_text = " ".join(out_req["summary_view"]["outputs_preview"]).lower()
    assert any(
        tok in out_text
        for tok in ("boiler", "chiller", "cooling tower", "baseboard", "district")
    )

    sp = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Simulation_Parameter",
            {
                "garden_root": g_root,
                "mode": "simulation_parameter",
                "identifier": "sp_full",
                "timestep": 4,
                "north_angle": 25.0,
                "terrain_type": "Urban",
                "simulation_control": {
                    "do_zone_sizing": True,
                    "do_system_sizing": True,
                    "do_plant_sizing": False,
                    "run_for_run_periods": True,
                },
                "holidays": [[1, 1], [12, 25]],
                "daylight_saving_time": {"start_date": [3, 10], "end_date": [11, 3]},
                "design_days": [
                    {
                        "type": "DesignDay",
                        "name": "CustomSummerDD",
                        "day_type": "SummerDesignDay",
                        "dry_bulb_condition": {"dry_bulb_max": 33.5, "dry_bulb_range": 11.0},
                        "humidity_condition": {
                            "humidity_type": "Wetbulb",
                            "humidity_value": 23.0,
                            "barometric_pressure": 101325.0,
                        },
                        "wind_condition": {"wind_speed": 4.0, "wind_direction": 180.0},
                        "sky_condition": {"type": "ASHRAEClearSky", "date": [7, 21], "clearness": 1.0},
                    }
                ],
                "output_request_target": out_req["target"],
            },
        )
    )
    sv = sp["summary_view"]
    assert sv["timestep"] == 4
    assert sv["north_angle"] == pytest.approx(25.0)
    assert sv["terrain_type"] == "Urban"
    assert sv["simulation_control"]["do_plant_sizing"] is False
    assert sv["run_period"]["holidays"] == [[1, 1], [12, 25]] or sv["run_period"]["holidays"] == [(1, 1), (12, 25)]
    assert sv["run_period"]["daylight_saving_time"]["start_date"] in ([3, 10], (3, 10))
    assert sv["sizing"]["design_day_count"] == 1
    assert sv["design_day_resolution"]["resolved_names_sample"] == ["CustomSummerDD"]

    m_dir = shutil.copytree(
        _repo_root() / "resources" / "honeybee-energy" / "tests" / "measure" / "edit_fraction_radiant_of_lighting_and_equipment",
        Path(g_root) / "measures" / "edit_fraction_radiant_of_lighting_and_equipment",
    )
    insp = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Simulation_Parameter",
            {
                "garden_root": g_root,
                "mode": "inspect_measures",
                "measures": [{"folder": str(m_dir), "arguments": {"lightsFractRad": 0.45, "equipFractRad": 0.35}}],
            },
        )
    )
    assert insp["summary_view"]["measure_count"] == 1
    assert insp["summary_view"]["measures"][0]["argument_count"] == 2
    m_meta = insp["measures"][0]
    assert m_meta["identifier"] == "edit_fraction_radiant_of_lighting_and_equipment"
    arg_names = {a["identifier"] for a in m_meta["arguments"]}
    assert {"lightsFractRad", "equipFractRad"} <= arg_names


def test_measures_only_workflows_and_idf_guard(tmp_path: Path, raw_mcp: FastMCP) -> None:
    import shutil
    from garden.run_energy.annual import OUTPUT_NAMES, run_energy

    for required in ("eio", "rdd", "osw", "zsz", "sql", "err"):
        assert required in OUTPUT_NAMES

    g_root, model_target = _create_box_garden(tmp_path, "meas_upg")
    weather_dir = Path(g_root) / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    epw_path = shutil.copy2(
        _repo_root() / "resources" / "dragonfly-energy" / "tests" / "epw" / "chicago.epw",
        weather_dir / "chicago.epw",
    )
    ddy_path = shutil.copy2(
        _repo_root() / "resources" / "dragonfly-energy" / "tests" / "epw" / "chicago.ddy",
        weather_dir / "chicago.ddy",
    )
    m_dir = shutil.copytree(
        _repo_root() / "resources" / "honeybee-energy" / "tests" / "measure" / "edit_fraction_radiant_of_lighting_and_equipment",
        Path(g_root) / "measures" / "edit_fraction_radiant_of_lighting_and_equipment",
    )
    osm_path = shutil.copy2(
        _repo_root() / "resources" / "honeybee-energy" / "tests" / "osm" / "shoe_box.osm",
        Path(g_root) / "shoe_box.osm",
    )
    idf_path = Path(g_root) / "dummy.idf"
    idf_path.write_text("Version, 23.2;\n", encoding="utf-8")

    # 1. EP_Start_Simulation(inspect_measures=True)
    insp_start = asyncio.run(
        _call(
            raw_mcp,
            "EP_Start_Simulation",
            {
                "garden_root": g_root,
                "inspect_measures": True,
                "measures": [{"folder": str(m_dir), "arguments": {"lightsFractRad": 0.4}}],
            },
        )
    )
    assert insp_start["summary_view"]["measure_count"] == 1

    # 2. EP_Run_Simulation_File on .osm with measures + measures_only=True
    osm_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Run_Simulation_File",
            {
                "garden_root": g_root,
                "file_path": str(osm_path),
                "epw_path": str(epw_path),
                "measures": [{"folder": str(m_dir), "arguments": {"lightsFractRad": 0.5, "equipFractRad": 0.4}}],
                "measures_only": True,
                "run_id": "osm_meas_only",
            },
        )
    )
    assert osm_res["report"]["status"] == "ok"
    assert osm_res["summary_view"]["status"] == "completed"
    assert osm_res["summary_view"]["outputs"]["osm"]["exists"] is True

    # 3. annual.run_energy on HBJSON model with measures + measures_only=True
    asyncio.run(
        _call(
            raw_mcp,
            "HB_Edit_Objects",
            {
                "garden_root": g_root,
                "room_identifiers": ["Room_1"],
                "program_type": "Generic Office Program",
                "construction_set": "Default Generic Construction Set",
            },
        )
    )
    hb_res = run_energy(
        garden_root=g_root,
        epw_path=str(epw_path),
        ddy_path=str(ddy_path),
        model_target=model_target,
        measures=[{"folder": str(m_dir), "arguments": {"lightsFractRad": 0.45}}],
        measures_only=True,
        run_id="hb_meas_only",
        validate_weather=False,
    )
    assert hb_res["report"]["status"] == "ok"
    assert hb_res["summary_view"]["status"] == "completed"

    # 4. .idf with measures must be rejected cleanly
    with pytest.raises(Exception, match="only supported for OpenStudio"):
        asyncio.run(
            _call(
                raw_mcp,
                "EP_Run_Simulation_File",
                {
                    "garden_root": g_root,
                    "file_path": str(idf_path),
                    "epw_path": str(epw_path),
                    "measures": [{"folder": str(m_dir)}],
                },
            )
        )


def test_energy_summarize_results_and_geometry_matching(tmp_path: Path, raw_mcp: FastMCP) -> None:
    import shutil
    from ladybug.sql import SQLiteResult
    from garden.manifest import GardenManifest
    from garden.run_ledger import make_run_target
    from garden.honeybee_core.model_io import import_honeybee_model_file
    from garden.run_energy import annual, results

    g_path = tmp_path / "post_upg"
    g_root = str(g_path)
    create_garden(name="post_upg", root_dir=g_root)
    manifest = GardenManifest.read(g_path)

    res_dir = _repo_root() / "resources" / "honeybee-energy" / "tests" / "result"
    sf_hbjson = shutil.copy2(res_dir / "single_family_home.json", g_path / "single_family_home.hbjson")
    sf_model = import_honeybee_model_file(
        garden_root=g_root,
        file_path=str(sf_hbjson),
        identifier="sf_home",
    )

    run_id = "sf_seeded"
    run_dir = g_path / "runs" / "energy" / run_id
    os_dir = run_dir / "openstudio"
    r_dir = os_dir / "run"
    r_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(res_dir / "single_family_home_eplusout.sql", r_dir / "eplusout.sql")
    shutil.copy2(res_dir / "epluszsz.csv", r_dir / "epluszsz.csv")
    shutil.copy2(res_dir / "eplusout.rdd", r_dir / "eplusout.rdd")
    shutil.copy2(res_dir / "out.osw", os_dir / "out.osw")
    shutil.copy2(res_dir / "eplusout_normal.err", r_dir / "eplusout.err")

    run_target = make_run_target(
        target_type="energy_run",
        garden_id=manifest.garden_id,
        domain="honeybee_energy",
        recipe="annual_energy_use",
        run_id=run_id,
    )
    annual._upsert_record(
        g_path,
        {
            "run_id": run_id,
            "target": run_target,
            "status": "completed",
            "run_dir": f"runs/energy/{run_id}",
            "model_target": sf_model["target"],
            "outputs": annual._recipe_outputs(garden_root_path=g_path, run_dir=run_dir, warnings=[]),
        },
    )

    # loads & load_balance
    loads = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "loads"})
    )
    assert loads["report"]["status"] == "ok"
    loads_by_name = {m["name"]: m for m in loads["summary_view"]["metrics"]}
    assert {"heating", "cooling", "lighting", "equipment"} <= set(loads_by_name)

    lb = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "load_balance"})
    )
    assert lb["report"]["status"] == "ok"
    lb_by_name = {m["name"]: m for m in lb["summary_view"]["metrics"]}
    assert lb_by_name["heating"]["value"] == pytest.approx(loads_by_name["heating"]["value"], rel=1e-4)

    # peaks (coincident <= non_coincident_sum, distinct max_zone_peak)
    peaks = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "peaks"})
    )
    assert peaks["report"]["status"] == "ok"
    heat_peak = {m["name"]: m for m in peaks["summary_view"]["metrics"]}["heating_peak"]
    assert heat_peak["coincident_peak"] > heat_peak["max_zone_peak"]
    assert heat_peak["coincident_peak"] <= heat_peak["non_coincident_sum"] + 1e-6

    # unmet_hours, emissions, generation, zsz, rdd, osw
    unmet = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "unmet_hours"})
    )
    assert unmet["report"]["status"] == "ok"
    assert {m["name"] for m in unmet["summary_view"]["metrics"]} >= {"heating_unmet_hours", "cooling_unmet_hours"}

    emissions = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "emissions"})
    )
    assert emissions["report"]["status"] == "ok"
    em_names = {m["name"] for m in emissions["summary_view"]["metrics"]}
    assert {"carbon_intensity", "total_carbon"} <= em_names

    gen = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "generation"})
    )
    assert gen["report"]["status"] == "ok"
    assert {m["name"] for m in gen["summary_view"]["metrics"]} >= {"total_production", "total_consumption"}

    zsz = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "zsz"})
    )
    assert zsz["report"]["status"] == "ok"
    assert zsz["summary_view"]["coincident_peaks"]["cooling_load"]["zone_count"] == 7

    rdd = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "rdd", "scope": "Zone Lights"})
    )
    assert rdd["report"]["status"] == "ok"
    assert rdd["summary_view"]["total_output_count"] == 461
    assert rdd["summary_view"]["matching_output_count"] >= 1

    osw = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "osw"})
    )
    assert osw["report"]["status"] == "ok"
    assert osw["summary_view"]["step_count"] == 2
    assert osw["summary_view"]["completed_status"] == "Fail"

    # tabular listing & single-table read
    tab_list = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": run_target, "summary_kind": "tabular"})
    )
    assert tab_list["report"]["status"] == "ok"
    assert tab_list["summary_view"]["total_table_count"] > 10

    tab_read = asyncio.run(
        _call(
            raw_mcp,
            "EP_Summarize_Results",
            {"garden_root": g_root, "run_target": run_target, "summary_kind": "tabular", "table_name": "Time Setpoint Not Met"},
        )
    )
    assert tab_read["report"]["status"] == "ok"
    assert len(tab_read["summary_view"]["columns"]) > 0

    # EP_Read_Result_Data geometry matching + direct helper calls
    mr = asyncio.run(
        _call(
            raw_mcp,
            "EP_Read_Result_Data",
            {
                "garden_root": g_root,
                "run_target": run_target,
                "output_name": "Zone Lights Electricity Energy",
                "match_to": "rooms",
                "model_target": sf_model["target"],
            },
        )
    )
    assert mr["summary_view"]["geometry_matches"]["match_mode"] == "rooms"
    assert mr["summary_view"]["geometry_matches"]["matched_room_count"] >= 1

    mf = asyncio.run(
        _call(
            raw_mcp,
            "EP_Read_Result_Data",
            {
                "garden_root": g_root,
                "run_target": run_target,
                "output_name": "Surface Inside Face Temperature",
                "match_to": "faces",
                "model_target": sf_model["target"],
            },
        )
    )
    assert mf["summary_view"]["geometry_matches"]["match_mode"] == "faces"
    assert mf["summary_view"]["geometry_matches"]["matched_face_count"] >= 1

    mr_direct = results.match_energy_results_to_rooms(
        garden_root=g_root,
        run_target=run_target,
        output_name="Zone Lights Electricity Energy",
        model_target=sf_model["target"],
    )
    mf_direct = results.match_energy_results_to_faces(
        garden_root=g_root,
        run_target=run_target,
        output_name="Surface Inside Face Temperature",
        model_target=sf_model["target"],
    )
    assert mr_direct["geometry_matches"]["matched_room_count"] >= 1
    assert mf_direct["geometry_matches"]["matched_face_count"] >= 1

    # Verify no double-counting when SQL contains both Supply Air Total and Zone Total Ideal Loads
    os_run_id = "os_seeded"
    os_run_dir = g_path / "runs" / "energy" / os_run_id
    os_r_dir = os_run_dir / "openstudio" / "run"
    os_r_dir.mkdir(parents=True, exist_ok=True)
    sql_os_path = shutil.copy2(res_dir / "eplusout_openstudio.sql", os_r_dir / "eplusout.sql")
    os_target = make_run_target(
        target_type="energy_run",
        garden_id=manifest.garden_id,
        domain="honeybee_energy",
        recipe="annual_energy_use",
        run_id=os_run_id,
    )
    annual._upsert_record(
        g_path,
        {
            "run_id": os_run_id,
            "target": os_target,
            "status": "completed",
            "run_dir": f"runs/energy/{os_run_id}",
            "outputs": annual._recipe_outputs(garden_root_path=g_path, run_dir=os_run_dir, warnings=[]),
        },
    )
    os_loads = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": g_root, "run_target": os_target, "summary_kind": "loads"})
    )
    os_heat = {m["name"]: m for m in os_loads["summary_view"]["metrics"]}["heating"]
    expected_supply_kwh = sum(
        sum(c.values)
        for c in SQLiteResult(str(sql_os_path)).data_collections_by_output_name(
            "Zone Ideal Loads Supply Air Total Heating Energy"
        )
    )
    assert os_heat["source_outputs"] == ["Zone Ideal Loads Supply Air Total Heating Energy"]
    assert os_heat["value"] == pytest.approx(expected_supply_kwh, rel=1e-4)

