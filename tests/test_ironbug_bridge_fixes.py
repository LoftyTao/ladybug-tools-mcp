"""Tests for Ironbug bridge field coercion diagnostics and OpenStudio version mismatch validation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest import mock
import warnings

from fastmcp import Client, FastMCP
import pytest

from garden.ironbug.runtime import (
    IronbugRuntimeUnavailable,
    extract_osm_version,
    inspect_ironbug_openstudio_compatibility,
    read_dotnet_assembly_refs,
    read_pe_file_version,
    resolve_runtime_paths,
)
from garden.ironbug.service import (
    configure_ironbug_loops,
    create_ironbug_system,
    upsert_ironbug_components,
    validate_ironbug_system,
)
from garden.ladybug_tools_config import get_ladybug_tools_config
from garden.store import create_garden
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.tools.ironbug import ValidateSystemResult


def _ironbug_live_available() -> bool:
    try:
        resolve_runtime_paths(require_openstudio=True)
        return True
    except IronbugRuntimeUnavailable:
        return False


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP(
        "Ironbug Fixes Test Server",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


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
    raise AssertionError(f"Unable to parse FastMCP tool result: {res!r}")


# ---------------------------------------------------------------------------
# P0-4a: SystemBuilder.cs Schedule & Object Field Coercion / Diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _ironbug_live_available(), reason="Ironbug + OpenStudio C# runtime unavailable")
def test_system_builder_rejects_raw_schedule_strings_and_objects_with_diagnostics(
    tmp_path: Path,
) -> None:
    g_root = str(tmp_path / "ib_coerce_g")
    create_garden(name="ib_coerce_g", root_dir=g_root)
    sys_res = create_ironbug_system(garden_root=g_root, identifier="coerce_sys", overwrite=True)
    ib_target = sys_res["target"]

    # 1. Raw string passed to OpenStudio.Schedule field must NOT fail with opaque InvalidCastException
    with pytest.raises(ValueError) as str_exc:
        upsert_ironbug_components(
            garden_root=g_root,
            ironbug_model_target=ib_target,
            components={
                "ahu_fan": {
                    "type": "IB_FanConstantVolume",
                    "fields": {"AvailabilitySchedule": "AlwaysOn"},
                }
            },
        )
    str_msg = str(str_exc.value)
    assert "ahu_fan" in str_msg
    assert "AvailabilitySchedule" in str_msg
    assert "AlwaysOn" in str_msg
    assert "OpenStudio.Schedule" in str_msg
    assert "IB_ScheduleRuleset" in str_msg
    assert "@<schedule_component_id>" in str_msg
    assert "Invalid cast from 'System.String'" not in str_msg

    # 2. Inline dict/object passed to OpenStudio.Schedule field must NOT fail with opaque Unsupported field value kind
    with pytest.raises(ValueError) as obj_exc:
        upsert_ironbug_components(
            garden_root=g_root,
            ironbug_model_target=ib_target,
            components={
                "fcu_1": {
                    "type": "IB_ZoneHVACFourPipeFanCoil",
                    "fields": {
                        "SupplyAirFanOperatingModeSchedule": {"type": "IB_ScheduleRuleset"}
                    },
                }
            },
        )
    obj_msg = str(obj_exc.value)
    assert "fcu_1" in obj_msg
    assert "SupplyAirFanOperatingModeSchedule" in obj_msg
    assert "OpenStudio.Schedule" in obj_msg
    assert "IB_ScheduleRuleset" in obj_msg
    assert "@<" in obj_msg
    assert "Unsupported field value kind: Object" not in obj_msg

    # 3. Raw string passed to OpenStudio.Curve field also produces clear diagnostics
    with pytest.raises(ValueError) as curve_exc:
        upsert_ironbug_components(
            garden_root=g_root,
            ironbug_model_target=ib_target,
            components={
                "chiller_1": {
                    "type": "IB_ChillerElectricEIR",
                    "fields": {"CoolingCapacityFunctionOfTemperature": "BiQuadCurve"},
                }
            },
        )
    curve_msg = str(curve_exc.value)
    assert "chiller_1" in curve_msg
    assert "CoolingCapacityFunctionOfTemperature" in curve_msg
    assert "BiQuadCurve" in curve_msg
    assert "OpenStudio.Curve" in curve_msg

    # 4. Reference wrappers {"ref": ...}, {"component_id": ...}, {"identifier": ...} and "@<id>" resolve cleanly
    for wrapper_key in ("ref", "component_id", "identifier"):
        ok_res = upsert_ironbug_components(
            garden_root=g_root,
            ironbug_model_target=ib_target,
            replace=True,
            components={
                "avail_sched": {"type": "IB_ScheduleRuleset"},
                "ahu_fan": {
                    "type": "IB_FanConstantVolume",
                    "fields": {"AvailabilitySchedule": {wrapper_key: "avail_sched"}},
                },
            },
        )
        assert ok_res["persistence_receipt"]["status"] == "persisted"

    # End-to-end compile & SaveHVAC validation with @avail_sched reference
    upsert_ironbug_components(
        garden_root=g_root,
        ironbug_model_target=ib_target,
        replace=True,
        components={
            "avail_sched": {"type": "IB_ScheduleRuleset"},
            "oa_ctrl": {"type": "IB_ControllerOutdoorAir"},
            "oa_sys": {"type": "IB_OutdoorAirSystem", "wiring": {"controller": "oa_ctrl"}},
            "cc": {"type": "IB_CoilCoolingDXSingleSpeed"},
            "hc": {"type": "IB_CoilHeatingElectric"},
            "ahu_fan": {
                "type": "IB_FanConstantVolume",
                "fields": {"AvailabilitySchedule": "@avail_sched"},
            },
        },
    )
    configure_ironbug_loops(
        garden_root=g_root,
        ironbug_model_target=ib_target,
        thermal_zones=[{"room_name": "Zone1"}],
        air_loops=[
            {
                "name": "AHU_Sched",
                "supply": ["oa_sys", "cc", "hc", "ahu_fan"],
                "demand_zones": ["Zone1"],
            }
        ],
        replace=True,
    )
    val_res = validate_ironbug_system(garden_root=g_root, ironbug_model_target=ib_target)
    assert val_res["valid"] is True, val_res
    assert val_res["ready"] is True, val_res


# ---------------------------------------------------------------------------
# P0-4b: OpenStudio / Ironbug Version Mismatch Diagnostics & Validation
# ---------------------------------------------------------------------------


def test_extract_osm_version_and_compatibility_matrix(tmp_path: Path) -> None:
    osm_text = (
        "OS:Version,\n"
        "  {8f8fc23c-bf85-4158-84f9-5bf75431490e}, !- Handle\n"
        "  3.11.0;                                 !- Version Identifier\n"
    )
    assert extract_osm_version(osm_text) == "3.11.0"
    osm_file = tmp_path / "sample.osm"
    osm_file.write_text(osm_text, encoding="utf-8")
    assert extract_osm_version(osm_path=osm_file) == "3.11.0"

    # Ironbug 1.26.1 (known -> 3.11.0) vs local OpenStudio CLI 3.10.0 triggers mismatch warning
    fake_ib_dir = tmp_path / "ironbug_1261"
    fake_ib_dir.mkdir()
    compat_1261 = inspect_ironbug_openstudio_compatibility(
        ironbug_dir=fake_ib_dir,
        openstudio_csharp_dir=fake_ib_dir,
        ironbug_version="1.26.1.0",
        openstudio_cli_version="3.10.0+86d7e215a1",
        osm_version="3.11.0",
        python_openstudio_version="3.10.0",
    )
    assert compat_1261["compatible"] is False
    assert compat_1261["ironbug_openstudio_version"] == "3.11.0"
    codes = {w["code"] for w in compat_1261["compatibility_warnings"]}
    assert "ironbug_openstudio_version_mismatch" in codes
    assert "osm_openstudio_version_mismatch" in codes
    joined_msgs = "\n".join(w["message"] for w in compat_1261["compatibility_warnings"])
    assert "3.11.0" in joined_msgs
    assert "3.10.0" in joined_msgs
    assert "OS:Version" in joined_msgs
    assert "ExpandObjects" in joined_msgs

    # Matching 3.10.0 versions produce no compatibility warnings
    compat_ok = inspect_ironbug_openstudio_compatibility(
        ironbug_dir=fake_ib_dir,
        openstudio_csharp_dir=fake_ib_dir,
        ironbug_version="1.22.0.0",
        openstudio_cli_version="3.10.0+86d7e215a1",
        osm_version="3.10.0",
        python_openstudio_version="3.10.0",
    )
    assert compat_ok["compatible"] is True
    assert compat_ok["compatibility_warnings"] == []


@pytest.mark.skipif(not _ironbug_live_available(), reason="Ironbug + OpenStudio C# runtime unavailable")
def test_live_binary_metadata_readers() -> None:
    paths = resolve_runtime_paths(require_openstudio=True)
    hvac_dll = paths.ironbug_dir / "Ironbug.HVAC.dll"
    assert read_pe_file_version(hvac_dll) is not None
    refs = read_dotnet_assembly_refs(hvac_dll)
    assert "OpenStudio" in refs
    if paths.openstudio_csharp_dir is not None:
        os_dll = paths.openstudio_csharp_dir / "OpenStudio.dll"
        assert read_pe_file_version(os_dll) is not None


def test_runtime_config_surfaces_ironbug_openstudio_version_mismatch(tmp_path: Path) -> None:
    fake_ib = tmp_path / "ironbug_1_26_1"
    fake_ib.mkdir()
    (fake_ib / "Ironbug.HVAC.dll").write_bytes(b"")
    (fake_ib / "Ironbug.Console.exe").write_bytes(b"")
    os_dll = fake_ib / "OpenStudio.dll"
    os_dll.write_bytes(b"")

    def fake_pe_ver(path: Path | None) -> str | None:
        if path is None:
            return None
        if path.name == "OpenStudio.dll":
            return "3.11.0.0"
        if path.name in ("Ironbug.HVAC.dll", "Ironbug.Console.exe"):
            return "1.26.1.0"
        return None

    fake_openstudio_cfg = {
        "name": "openstudio",
        "source": "sdk_config",
        "path": "C:/openstudio/bin",
        "path_exists": True,
        "exe": "C:/openstudio/bin/openstudio.exe",
        "exe_exists": True,
        "version": "3.10.0+86d7e215a1",
        "version_status": "compatible",
        "version_requirement": {"required_version": "3.10.0"},
    }

    with (
        mock.patch("garden.ladybug_tools_config._select_openstudio_config", return_value=fake_openstudio_cfg),
        mock.patch("garden.ironbug.runtime.resolve_ironbug_dir", return_value=fake_ib),
        mock.patch("garden.ironbug.runtime.resolve_ironbug_console_exe", return_value=fake_ib / "Ironbug.Console.exe"),
        mock.patch("garden.ironbug.runtime.resolve_openstudio_csharp_dir", return_value=fake_ib),
        mock.patch("garden.ironbug.runtime.read_pe_file_version", side_effect=fake_pe_ver),
        mock.patch("garden.ladybug_tools_config.read_pe_file_version", side_effect=fake_pe_ver, create=True),
        mock.patch("garden.ironbug.runtime.get_python_openstudio_version", return_value="3.11.0"),
    ):
        cfg = get_ladybug_tools_config()

    assert cfg["report"]["status"] == "warning"
    sv = cfg["summary_view"]
    ib_engine = sv["engines"]["ironbug_console"]
    assert ib_engine["bundled_openstudio_version"] == "3.11.0"
    assert ib_engine["expected_openstudio_version"] == "3.11.0"
    assert sv["compatibility_warnings"]
    assert any(
        w.get("code") == "ironbug_openstudio_version_mismatch"
        for w in sv["compatibility_warnings"]
    )
    assert any("3.11.0" in w and "3.10.0" in w for w in cfg["report"]["warnings"])


def test_validate_system_surfaces_compatibility_and_vt_diagnostics(tmp_path: Path) -> None:
    g_root = str(tmp_path / "ib_val_diag_g")
    create_garden(name="ib_val_diag_g", root_dir=g_root)

    class _FakeBridgeClient:
        def call(self, method: str, payload: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
            del timeout
            if method == "build":
                return {
                    "specification_json": json.dumps(
                        {"$type": "Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC", "IBVersion": "1.26.1.0"}
                    ),
                    "summary": {"ib_version": "1.26.1.0", "thermal_zones": ["Zone1"]},
                }
            if method == "validate":
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": [
                        "[openstudio.osversion.VersionTranslator] Version extracted from file '3.11.0' is one increment ahead of OpenStudio Version 3.10.0."
                    ],
                    "thermal_zones": ["Zone1"],
                    "system_summary": {"ib_version": "1.26.1.0", "thermal_zones": ["Zone1"]},
                    "openstudio_summary": {"thermal_zones": 1},
                    "osm_version": "3.11.0",
                    "openstudio_version": "3.10.0",
                    "forward_translator": {
                        "ran": True,
                        "error_count": 0,
                        "warning_count": 2,
                        "errors": [],
                        "warnings": [
                            "[openstudio.osversion.VersionTranslator] Version extracted from file '3.11.0' is one increment ahead of OpenStudio Version 3.10.0.",
                            "[VersionTranslator/OSM] [utilities.idf.IdfObject] IdfObject of type 'OS:Sizing:Zone' cannot have field index of 40.",
                        ],
                        "version_translator_warnings": [
                            "[openstudio.osversion.VersionTranslator] Version extracted from file '3.11.0' is one increment ahead of OpenStudio Version 3.10.0."
                        ],
                        "version_translator_errors": [
                            "[utilities.idf.IdfObject] IdfObject of type 'OS:Sizing:Zone' cannot have field index of 40."
                        ],
                    },
                }
            return {}

    with (
        mock.patch("garden.ironbug.service.get_bridge_client", return_value=_FakeBridgeClient()),
        mock.patch("garden.ironbug.runtime.energy_folders") as mock_ef,
        mock.patch("garden.ironbug.runtime.resolve_ironbug_dir", return_value=None),
        mock.patch("garden.ironbug.runtime.resolve_openstudio_csharp_dir", return_value=None),
        mock.patch("garden.ironbug.runtime.get_python_openstudio_version", return_value="3.11.0"),
    ):
        mock_ef.openstudio_version_str = "3.10.0+86d7e215a1"
        mock_ef.ironbug_version_str = "1.26.1.0"
        sys_res = create_ironbug_system(garden_root=g_root, identifier="diag_sys", overwrite=True)
        raw_val = validate_ironbug_system(
            garden_root=g_root,
            ironbug_model_target=sys_res["target"],
            run_forward_translator=True,
        )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        validated = ValidateSystemResult.model_validate(raw_val)
    assert [w for w in caught if "Pydantic" in w.category.__name__] == []

    assert validated.valid is True
    assert validated.compatibility_warnings
    codes = {w["code"] for w in validated.compatibility_warnings}
    assert "ironbug_openstudio_version_mismatch" in codes
    assert "osm_openstudio_version_mismatch" in codes
    assert any("3.11.0" in w and "3.10.0" in w for w in (validated.warnings or []))
    assert validated.forward_translator is not None
    assert validated.forward_translator.version_translator_warnings
    assert validated.forward_translator.version_translator_errors


@pytest.mark.skipif(not _ironbug_live_available(), reason="Ironbug + OpenStudio C# runtime unavailable")
def test_live_validate_system_surfaces_version_translator_diagnostics_and_schema_budget(
    tmp_path: Path,
) -> None:
    mcp = _make_raw_mcp()
    tools = asyncio.run(mcp.list_tools())
    by_name = {t.name: t for t in tools}
    for name in ("IB_Validate_System", "LB_Get_Runtime_Config"):
        in_bytes = len(json.dumps(by_name[name].parameters or {}).encode("utf-8"))
        out_bytes = len(json.dumps(by_name[name].output_schema or {}).encode("utf-8"))
        assert in_bytes <= 20 * 1024, f"{name} inputSchema exceeded 20KB: {in_bytes}"
        assert out_bytes <= 5 * 1024, f"{name} outputSchema exceeded 5KB: {out_bytes}"

    g_root = str(tmp_path / "ib_live_vt_g")
    create_garden(name="ib_live_vt_g", root_dir=g_root)

    async def _run() -> dict[str, Any]:
        async with Client(mcp) as client:
            m_res = _parse_tool_result(
                await client.call_tool("HB_Create_Model", {"garden_root": g_root, "identifier": "vt_model"})
            )
            await client.call_tool(
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
            await client.call_tool(
                "HB_Edit_Objects",
                {
                    "garden_root": g_root,
                    "room_identifiers": ["Room_1"],
                    "program_type": "Generic Office Program",
                    "construction_set": "Default Generic Construction Set",
                },
            )
            s_res = _parse_tool_result(
                await client.call_tool(
                    "IB_Create_System",
                    {
                        "garden_root": g_root,
                        "identifier": "vt_vav",
                        "template": "vav_chiller_boiler",
                        "room_names": ["Room_1"],
                        "overwrite": True,
                    },
                )
            )
            return _parse_tool_result(
                await client.call_tool(
                    "IB_Validate_System",
                    {
                        "garden_root": g_root,
                        "ironbug_model_target": s_res["target"],
                        "model_target": m_res["target"],
                        "run_forward_translator": True,
                    },
                )
            )

    val_res = asyncio.run(_run())
    assert val_res["valid"] is True, val_res
    assert val_res["ready"] is True, val_res
    ft = val_res["forward_translator"]
    assert ft["ran"] is True
    assert ft["error_count"] == 0

    # If python openstudio (e.g. 3.11.0) is ahead of local OpenStudio C#/CLI (e.g. 3.10.0),
    # VersionTranslator diagnostics and compatibility_warnings must both surface cleanly.
    compat = inspect_ironbug_openstudio_compatibility()
    py_ver = compat.get("python_openstudio_version")
    cli_ver = compat.get("openstudio_cli_version")
    if py_ver and cli_ver and tuple(int(x) for x in py_ver.split(".")[:3]) > tuple(int(x) for x in cli_ver.split(".")[:3]):
        assert val_res.get("compatibility_warnings"), val_res
        assert ft.get("version_translator_warnings"), ft
        assert any("ahead" in w.lower() for w in ft["version_translator_warnings"])
