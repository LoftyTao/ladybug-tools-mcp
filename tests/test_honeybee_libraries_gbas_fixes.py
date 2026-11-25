"""Regression tests for P0-5a/b/c, P0-7a (gbas_dwg report artifact), and Wave 2 schema slimming."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from honeybee.model import Model as HoneybeeModel
from honeybee.room import Room
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac.doas.fcu import FCUwithDOAS
from honeybee_energy.programtype import ProgramType

from garden.honeybee_core.model_io import load_honeybee_model
from garden.manifest import GardenManifest
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.server import create_mcp


def _parse_tool_result(res: Any) -> dict[str, Any]:
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    structured = getattr(res, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            return json.loads(text)
    raise AssertionError(f"Unable to parse MCP tool result: {res!r}")


async def _call(client: Client, name: str, args: dict[str, Any]) -> dict[str, Any]:
    res = await client.call_tool(name, args)
    return _parse_tool_result(res)


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "HB Libraries GBAS Fixes Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


@pytest.fixture(scope="module")
def raw_mcp() -> FastMCP:
    return _make_raw_mcp()


def _box_face_shorthands() -> list[dict[str, Any]]:
    """Return 6 shorthand face dicts (omitting Face/FaceProperties/Face3D boilerplate)."""
    return [
        {
            "identifier": "Floor_1",
            "geometry": {"boundary": [[0, 0, 0], [0, 4, 0], [5, 4, 0], [5, 0, 0]]},
            "face_type": "Floor",
            "boundary_condition": "Ground",
        },
        {
            "identifier": "Roof_1",
            "geometry": {"boundary": [[0, 0, 3], [5, 0, 3], [5, 4, 3], [0, 4, 3]]},
            "face_type": "RoofCeiling",
            "boundary_condition": "Outdoors",
        },
        {
            "identifier": "Wall_South",
            "geometry": {"boundary": [[0, 0, 0], [5, 0, 0], [5, 0, 3], [0, 0, 3]]},
            "face_type": "Wall",
        },
        {
            "identifier": "Wall_East",
            "geometry": {"boundary": [[5, 0, 0], [5, 4, 0], [5, 4, 3], [5, 0, 3]]},
            "face_type": "Wall",
            "boundary_condition": "Adiabatic",
        },
        {
            "identifier": "Wall_North",
            "geometry": {"boundary": [[5, 4, 0], [0, 4, 0], [0, 4, 3], [5, 4, 3]]},
            "face_type": "Wall",
            "boundary_condition": "Outdoors",
        },
        {
            "identifier": "Wall_West",
            "geometry": {"boundary": [[0, 4, 0], [0, 0, 0], [0, 0, 3], [0, 4, 3]]},
            "face_type": "Wall",
            "boundary_condition": "Adiabatic",
        },
    ]


def test_p0_5a_hb_edit_objects_garden_library_strings(raw_mcp: FastMCP, tmp_path: Path) -> None:
    """Verify HB_Edit_Objects resolves Garden library IDs for program_type, construction_set, and hvac."""
    g_root = (tmp_path / "p0_5a_garden").as_posix()

    pt = ProgramType("PT_CONFERENCE")
    pt_dict = pt.to_dict()
    cs = ConstructionSet("CS_ENVELOPE")
    cs_dict = cs.to_dict()
    hvac = FCUwithDOAS("SH_FCU_DOAS_ASHP")
    hvac_dict = hvac.to_dict()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "p0_5a", "root_dir": g_root})
            m_res = await _call(client, "HB_Create_Model", {"garden_root": g_root, "identifier": "hb_lib"})
            model_target = m_res["target"]

            await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": g_root,
                    "action": "save",
                    "domain": "honeybee_energy",
                    "object_family": "program_type",
                    "identifier": "PT_CONFERENCE",
                    "object_dict": pt_dict,
                },
            )
            await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": g_root,
                    "action": "save",
                    "domain": "honeybee_energy",
                    "object_family": "construction_set",
                    "identifier": "CS_ENVELOPE",
                    "object_dict": cs_dict,
                },
            )
            await _call(
                client,
                "GD_Properties_Library",
                {
                    "garden_root": g_root,
                    "action": "save",
                    "domain": "honeybee_energy",
                    "object_family": "hvac",
                    "identifier": "SH_FCU_DOAS_ASHP",
                    "object_dict": hvac_dict,
                },
            )

            created_rooms = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "items": [
                        {"identifier": "Room_1", "x_dim": 5.0, "y_dim": 4.0, "height": 3.0},
                        {"identifier": "Room_2", "x_dim": 5.0, "y_dim": 4.0, "height": 3.0, "origin": [6.0, 0.0, 0.0]},
                    ],
                },
            )
            room1_target = created_rooms["targets"][0]

            # Top-level string resolution via Garden Properties Library.
            await _call(
                client,
                "HB_Edit_Objects",
                {
                    "garden_root": g_root,
                    "target": room1_target,
                    "program_type": "PT_CONFERENCE",
                    "construction_set": "CS_ENVELOPE",
                    "hvac": "SH_FCU_DOAS_ASHP",
                },
            )

            hb_model = load_honeybee_model(Path(g_root), model_target)
            r1 = next(r for r in hb_model.rooms if r.identifier == "Room_1")
            assert r1.properties.energy.program_type.identifier == "PT_CONFERENCE"
            assert r1.properties.energy.construction_set.identifier == "CS_ENVELOPE"
            assert r1.properties.energy.hvac.identifier == "SH_FCU_DOAS_ASHP"

            # Batch room_identifiers + nested energy_properties string resolution.
            await _call(
                client,
                "HB_Edit_Objects",
                {
                    "garden_root": g_root,
                    "room_identifiers": ["Room_1", "Room_2"],
                    "energy_properties": {
                        "program_type": "PT_CONFERENCE",
                        "construction_set": "CS_ENVELOPE",
                        "hvac": "SH_FCU_DOAS_ASHP",
                    },
                },
            )
            hb_model_2 = load_honeybee_model(Path(g_root), model_target)
            r2 = next(r for r in hb_model_2.rooms if r.identifier == "Room_2")
            assert r2.properties.energy.program_type.identifier == "PT_CONFERENCE"
            assert r2.properties.energy.construction_set.identifier == "CS_ENVELOPE"
            assert r2.properties.energy.hvac.identifier == "SH_FCU_DOAS_ASHP"

            # Fallback to honeybee_energy standards library.
            std_search = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "energy", "object_family": "program_type", "query": "Office", "limit": 1},
            )
            std_prog_id = std_search["matches"][0]["identifier"]
            await _call(
                client,
                "HB_Edit_Objects",
                {"garden_root": g_root, "target": room1_target, "program_type": std_prog_id},
            )
            hb_model_3 = load_honeybee_model(Path(g_root), model_target)
            r1_std = next(r for r in hb_model_3.rooms if r.identifier == "Room_1")
            assert r1_std.properties.energy.program_type.identifier == std_prog_id

            # Unknown IDs report Garden library options cleanly.
            with pytest.raises(ToolError) as pt_exc:
                await _call(
                    client,
                    "HB_Edit_Objects",
                    {"garden_root": g_root, "target": room1_target, "program_type": "PT_CONFERNCE"},
                )
            assert "PT_CONFERENCE" in str(pt_exc.value)

            with pytest.raises(ToolError) as cs_exc:
                await _call(
                    client,
                    "HB_Edit_Objects",
                    {"garden_root": g_root, "target": room1_target, "construction_set": "CS_ENVELOPE_MISSING"},
                )
            assert "CS_ENVELOPE" in str(cs_exc.value)

            with pytest.raises(ToolError) as hvac_exc:
                await _call(
                    client,
                    "HB_Edit_Objects",
                    {"garden_root": g_root, "target": room1_target, "hvac": "SH_FCU_MISSING"},
                )
            assert "SH_FCU_DOAS_ASHP" in str(hvac_exc.value)

    asyncio.run(_run())


def test_p0_5b_display_name_and_shorthand_room_face_normalization(raw_mcp: FastMCP, tmp_path: Path) -> None:
    """Verify display_name support and shorthand Face/Room/Face3D/BC normalization."""
    g_root = (tmp_path / "p0_5b_norm").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "p0_5b_norm", "root_dir": g_root})

            # Prepare an HBJSON file for import display_name test.
            seed_hb = HoneybeeModel("seed_model", [Room.from_box("Seed_Room", 4.0, 4.0, 3.0)])
            seed_path = Path(g_root) / "seed.hbjson"
            seed_path.write_text(json.dumps(seed_hb.to_dict()), encoding="utf-8")

            imported = await _call(
                client,
                "HB_Create_Model",
                {
                    "garden_root": g_root,
                    "import_file_path": "seed.hbjson",
                    "identifier": "imported_model",
                    "display_name": "Imported Pretty Building",
                    "set_base": False,
                },
            )
            assert imported["summary_view"]["display_name"] == "Imported Pretty Building"

            created_m = await _call(
                client,
                "HB_Create_Model",
                {
                    "garden_root": g_root,
                    "identifier": "main_model",
                    "display_name": "Demo Building",
                    "set_base": True,
                },
            )
            assert created_m["summary_view"]["display_name"] == "Demo Building"

            # Single Room + display_name.
            single_room = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "identifier": "R1",
                    "display_name": "North Office",
                    "x_dim": 4.0,
                    "y_dim": 4.0,
                    "height": 3.0,
                },
            )
            assert single_room["summary_view"]["display_name"] == "North Office"

            # Batch Rooms + per-item display_name.
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "items": [
                        {
                            "identifier": "R2",
                            "display_name": "South Office",
                            "x_dim": 4.0,
                            "y_dim": 4.0,
                            "height": 3.0,
                            "origin": [5.0, 0.0, 0.0],
                        }
                    ],
                },
            )

            # Orphan Face with display_name and geometry shorthand (omitting type="Face3D").
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "face",
                    "identifier": "Orphan_South",
                    "display_name": "South Facade",
                    "geometry": {"boundary": [[12, 0, 0], [16, 0, 0], [16, 0, 3], [12, 0, 3]]},
                },
            )

            # Room created from 6 shorthand faces (omitting type/properties/boundary_condition & string BCs).
            shorthand_room = await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "identifier": "CustomFacesRoom",
                    "display_name": "Custom Envelope",
                    "faces": _box_face_shorthands(),
                    "postprocess_strategy": "none",
                },
            )
            assert shorthand_room["summary_view"]["display_name"] == "Custom Envelope"

            # HB_Edit_Model add_objects with shorthand Room (omitting type/properties) & shorthand Faces.
            shifted_faces = [
                {
                    **face,
                    "identifier": f"Shift_{face['identifier']}",
                    "geometry": {
                        "boundary": [[p[0] + 20.0, p[1], p[2]] for p in face["geometry"]["boundary"]]
                    },
                }
                for face in _box_face_shorthands()
            ]
            await _call(
                client,
                "HB_Edit_Model",
                {
                    "garden_root": g_root,
                    "model_target": created_m["target"],
                    "add_objects": [
                        {
                            "identifier": "AddedShorthandRoom",
                            "display_name": "Added Shorthand",
                            "faces": shifted_faces,
                        }
                    ],
                },
            )

            hb_model = load_honeybee_model(Path(g_root), created_m["target"])
            assert hb_model.display_name == "Demo Building"
            by_id = {r.identifier: r for r in hb_model.rooms}
            assert by_id["R1"].display_name == "North Office"
            assert by_id["R2"].display_name == "South Office"
            assert by_id["CustomFacesRoom"].display_name == "Custom Envelope"
            assert by_id["AddedShorthandRoom"].display_name == "Added Shorthand"
            assert any(
                f.identifier == "Orphan_South" and f.display_name == "South Facade"
                for f in hb_model.orphaned_faces
            )
            c_faces = {f.identifier: f for f in by_id["CustomFacesRoom"].faces}
            assert c_faces["Wall_South"].boundary_condition.name == "Outdoors"
            assert c_faces["Floor_1"].boundary_condition.name == "Ground"
            assert c_faces["Wall_East"].boundary_condition.name == "Adiabatic"

    asyncio.run(_run())


def test_p0_5b_door_errors_apertures_edit_model_search_aliases(raw_mcp: FastMCP, tmp_path: Path) -> None:
    """Verify AirBoundary/mismatch door hints, Aperture by_width_height/mode tolerance, HB_Edit_Model & HB_Search_Model_Objects aliases."""
    g_root = (tmp_path / "p0_5b_misc").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "p0_5b_misc", "root_dir": g_root})
            model_res = await _call(
                client,
                "HB_Create_Model",
                {"garden_root": g_root, "identifier": "misc_hb"},
            )
            model_target = model_res["target"]

            # Create two adjacent boxes sharing x=5 plane.
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room",
                    "items": [
                        {"identifier": "Zone_A", "x_dim": 5.0, "y_dim": 4.0, "height": 3.0, "origin": [0.0, 0.0, 0.0]},
                        {"identifier": "Zone_B", "x_dim": 5.0, "y_dim": 4.0, "height": 3.0, "origin": [5.0, 0.0, 0.0]},
                    ],
                    "postprocess_strategy": "none",
                },
            )
            await _call(
                client,
                "HB_Relate_Model",
                {"garden_root": g_root, "air_boundary": True},
            )

            # Find the AirBoundary host face on Zone_A.
            air_faces = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "face",
                    "room_identifier": "Zone_A",
                    "face_type": "AirBoundary",
                },
            )
            air_face_target = air_faces["matches"][0]["target"]
            air_face_id = air_face_target["identifier"]

            # Door placed on AirBoundary face returns host face ID + actionable split hint.
            with pytest.raises(ToolError) as air_exc:
                await _call(
                    client,
                    "HB_Create_Objects",
                    {
                        "garden_root": g_root,
                        "object_type": "door",
                        "identifier": "Air_Door",
                        "host_target": air_face_target,
                        "door_width": 0.9,
                        "door_height": 2.1,
                    },
                )
            air_msg = str(air_exc.value)
            assert air_face_id in air_msg
            assert "AirBoundary" in air_msg
            assert "split" in air_msg.lower() or "Wall" in air_msg

            # Test mismatched adjacency error on solid interior wall (without cloning).
            await _call(
                client,
                "HB_Edit_Objects",
                {
                    "garden_root": g_root,
                    "target": air_face_target,
                    "face_type": "Wall",
                    "postprocess_strategy": "none",
                },
            )
            await _call(
                client,
                "HB_Relate_Model",
                {"garden_root": g_root, "air_boundary": False, "overwrite": True},
            )
            # Re-fetch Zone_A solid interior Wall face.
            surf_faces = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "face",
                    "room_identifier": "Zone_A",
                    "boundary_condition": "Surface",
                },
            )
            solid_interior_target = surf_faces["matches"][0]["target"]
            with pytest.raises(ToolError) as mismatch_exc:
                await _call(
                    client,
                    "HB_Create_Objects",
                    {
                        "garden_root": g_root,
                        "object_type": "door",
                        "identifier": "OneSided_Door",
                        "host_target": solid_interior_target,
                        "door_width": 0.9,
                        "door_height": 2.1,
                        "postprocess_strategy": "auto_relate_existing_geometry",
                    },
                )
            mismatch_msg = str(mismatch_exc.value)
            assert solid_interior_target["identifier"] in mismatch_msg
            assert "Zone_B" in mismatch_msg or "adjacent" in mismatch_msg.lower()

            # HB_Create_Apertures auto-infers generation_mode="by_width_height" when aperture_width & aperture_height given.
            south_walls = await _call(
                client,
                "HB_Search_Model_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "face",
                    "face_type": "Wall",
                    "orientation": "S",
                },
            )
            wall_a_target = south_walls["matches"][0]["target"]
            wall_b_target = south_walls["matches"][1]["target"]

            ap_single = await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": g_root,
                    "mode": "parameters",
                    "host_target": wall_a_target,
                    "aperture_width": 1.6,
                    "aperture_height": 1.2,
                    "sill_height": 0.9,
                },
            )
            assert ap_single["summary_view"]["created_count"] >= 1

            # Batch items tolerate matching redundant "mode" key and auto-infer by_width_height.
            ap_batch = await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": g_root,
                    "mode": "parameters",
                    "items": [
                        {
                            "mode": "parameters",
                            "host_target": wall_b_target,
                            "aperture_width": 1.4,
                            "aperture_height": 1.1,
                            "sill_height": 1.0,
                        }
                    ],
                },
            )
            assert ap_batch["summary_view"]["created_count"] >= 1

            # Conflicting item "mode" rejected cleanly.
            with pytest.raises(ToolError) as ap_mode_exc:
                await _call(
                    client,
                    "HB_Create_Apertures",
                    {
                        "garden_root": g_root,
                        "mode": "parameters",
                        "items": [{"mode": "geometry", "host_target": wall_b_target}],
                    },
                )
            assert "mode" in str(ap_mode_exc.value)

            # HB_Edit_Model accepts model_target alias when target is omitted.
            edited_m = await _call(
                client,
                "HB_Edit_Model",
                {
                    "garden_root": g_root,
                    "model_target": model_target,
                    "display_name": "Renamed Via Alias",
                },
            )
            assert edited_m["summary_view"]["display_name"] == "Renamed Via Alias"

            # HB_Search_Model_Objects accepts parent_target alias matching children_scope.
            rooms = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": g_root, "object_type": "room"},
            )
            zone_a_target = next(m["target"] for m in rooms["matches"] if m["target"]["identifier"] == "Zone_A")
            via_scope = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": g_root, "object_type": "face", "children_scope": zone_a_target},
            )
            via_parent = await _call(
                client,
                "HB_Search_Model_Objects",
                {"garden_root": g_root, "object_type": "face", "parent_target": zone_a_target},
            )
            assert [m["target"]["identifier"] for m in via_parent["matches"]] == [
                m["target"]["identifier"] for m in via_scope["matches"]
            ]

            with pytest.raises(ToolError):
                await _call(
                    client,
                    "HB_Search_Model_Objects",
                    {"garden_root": g_root, "object_type": "face", "children_scope": "direct"},
                )

    asyncio.run(_run())


def test_p0_5c_lb_search_standards_fairyfly_alias(raw_mcp: FastMCP) -> None:
    """Verify LB_Search_Standards_Library accepts domain='fairyfly' as alias for 'therm'."""

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            ff_res = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "fairyfly", "action": "search", "query": "", "limit": 5},
            )
            therm_res = await _call(
                client,
                "LB_Search_Standards_Library",
                {"domain": "therm", "action": "search", "query": "", "limit": 5},
            )
            assert ff_res["matches"]
            assert [m["identifier"] for m in ff_res["matches"]] == [
                m["identifier"] for m in therm_res["matches"]
            ]
            first_match = ff_res["matches"][0]
            got = await _call(
                client,
                "LB_Search_Standards_Library",
                {
                    "domain": "fairyfly",
                    "action": "get",
                    "identifier": first_match["identifier"],
                    "object_family": first_match.get("object_family"),
                },
            )
            assert got["summary_view"]["identifier"] == first_match["identifier"]

    asyncio.run(_run())


def test_p0_7a_gbas_dwg_selfcheck_report_artifact_registration(
    raw_mcp: FastMCP, tmp_path: Path
) -> None:
    """Verify gbas_dwg export registers its self-check report JSON artifact alongside the DWG."""
    g_root = (tmp_path / "p0_7a_garden").as_posix()

    async def _run() -> None:
        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "p0_7a", "root_dir": g_root})
            m_res = await _call(
                client,
                "HB_Create_Model",
                {"garden_root": g_root, "identifier": "gbas_hb"},
            )
            model_target = m_res["target"]
            await _call(
                client,
                "HB_Create_Objects",
                {
                    "garden_root": g_root,
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
                    "garden_root": g_root,
                    "object_type": "face",
                    "face_type": "Wall",
                    "orientation": "S",
                },
            )
            await _call(
                client,
                "HB_Create_Apertures",
                {
                    "garden_root": g_root,
                    "mode": "parameters",
                    "ratio": 0.35,
                    "host_target": walls["matches"][0]["target"],
                },
            )

            exported = await _call(
                client,
                "GD_Export_Model_File",
                {
                    "garden_root": g_root,
                    "export_format": "gbas_dwg",
                    "model_target": model_target,
                    "name": "gbas_case",
                    "export_options": {"write_report": True},
                },
            )
            sv = exported["summary_view"]
            assert sv["report_artifact"]["artifact_type"] == "gbas_selfcheck_report"
            assert sv["report_target"] == sv["report_artifact"]
            assert sv["report_artifact"]["dwg_identifier"] == "gbas_case"
            assert sv["report_artifact"]["dwg_target"] == exported["target"]
            assert sv["report_artifact"]["model_target"] == model_target
            assert (Path(g_root) / sv["report_artifact"]["path"]).is_file()

            manifest = GardenManifest.read(Path(g_root))
            artifact_types = {a["artifact_type"] for a in manifest.artifacts}
            assert "gbas_dwg" in artifact_types
            assert "gbas_selfcheck_report" in artifact_types

            listed_all = await _call(
                client,
                "GD_List_Artifacts",
                {"garden_root": g_root},
            )
            listed_types = {m["artifact_type"] for m in listed_all["matches"]}
            assert {"gbas_dwg", "gbas_selfcheck_report"}.issubset(listed_types)

            listed_report = await _call(
                client,
                "GD_List_Artifacts",
                {"garden_root": g_root, "artifact_type": "gbas_selfcheck_report"},
            )
            assert len(listed_report["matches"]) == 1
            assert listed_report["matches"][0]["path"].endswith(".json")

    asyncio.run(_run())


def test_wave2_schema_slimming_and_contracts(raw_mcp: FastMCP, tmp_path: Path) -> None:
    """Verify Wave 2 schema byte reductions, undocumented-param invariant, and DF_Apply_Properties validation."""
    g_root = (tmp_path / "wave2_df").as_posix()

    async def _run() -> None:
        tools = await raw_mcp.list_tools()
        by_name = {t.name: t for t in tools}

        hb_bytes = len(json.dumps(by_name["HB_Edit_Objects"].parameters, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        df_bytes = len(json.dumps(by_name["DF_Apply_Properties"].parameters, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        # Baselines before Wave 2: HB_Edit_Objects = 12620 B, DF_Apply_Properties = 13744 B.
        assert hb_bytes <= 7000, f"HB_Edit_Objects schema too large: {hb_bytes}"
        assert df_bytes <= 8000, f"DF_Apply_Properties schema too large: {df_bytes}"

        for t in tools:
            if not (t.name.startswith(("HB_", "DF_")) or t.name == "LB_Search_Standards_Library"):
                continue
            schema = t.parameters or {}
            raw = len(json.dumps(schema, separators=(",", ":"), sort_keys=True).encode("utf-8"))
            assert raw <= 20480, f"{t.name} exceeded 20KB input schema budget: {raw}"
            for prop_name, prop_schema in (schema.get("properties") or {}).items():
                assert isinstance(prop_schema, dict)
                assert str(prop_schema.get("description") or "").strip(), f"Undocumented {t.name}.{prop_name}"

        cm_mcp = create_mcp()
        async with Client(cm_mcp) as cm_client:
            hb_full = await cm_client.call_tool("get_schema", {"tools": ["HB_Edit_Objects"], "detail": "full"})
            df_full = await cm_client.call_tool("get_schema", {"tools": ["DF_Apply_Properties"], "detail": "full"})
            assert len(hb_full.content[0].text.encode("utf-8")) <= 16500
            assert len(df_full.content[0].text.encode("utf-8")) <= 18500

        async with Client(raw_mcp) as client:
            await _call(client, "GD_Create", {"name": "wave2", "root_dir": g_root})
            await _call(client, "DF_Model", {"garden_root": g_root, "identifier": "df_m"})
            r2d = await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "room2d",
                    "identifier": "R2D_1",
                    "x_dim": 6.0,
                    "y_dim": 5.0,
                    "floor_to_ceiling_height": 3.0,
                },
            )
            story = await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "story",
                    "identifier": "DF_Story_1",
                    "room2d_targets": [r2d["target"]],
                    "floor_to_floor_height": 3.0,
                },
            )
            await _call(
                client,
                "DF_Create_Objects",
                {
                    "garden_root": g_root,
                    "object_type": "building",
                    "identifier": "DF_Bldg_1",
                    "story_targets": [story["target"]],
                },
            )
            applied = await _call(
                client,
                "DF_Apply_Properties",
                {
                    "garden_root": g_root,
                    "property_domain": "energy",
                    "host_target": r2d["target"],
                    "lighting_watts": 120.0,
                },
            )
            assert applied["target"]["identifier"] == "R2D_1"

            with pytest.raises(ToolError) as bad_num:
                await _call(
                    client,
                    "DF_Apply_Properties",
                    {
                        "garden_root": g_root,
                        "property_domain": "energy",
                        "host_target": r2d["target"],
                        "person_count": -2,
                    },
                )
            assert "person_count" in str(bad_num.value)

            with pytest.raises(ToolError) as bad_grid:
                await _call(
                    client,
                    "DF_Apply_Properties",
                    {
                        "garden_root": g_root,
                        "property_domain": "radiance",
                        "host_target": r2d["target"],
                        "grid_parameter_type": "invalid_grid",
                    },
                )
            assert "grid_parameter_type" in str(bad_grid.value)

    asyncio.run(_run())
