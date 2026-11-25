"""Governance tests for Pydantic schemas, FastMCP contracts, and IronPython isolation."""

from __future__ import annotations

import ast
import asyncio
import json
import warnings
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from fastmcp import Client, FastMCP
from pydantic import ValidationError

from garden.dragonfly_core._schemas import validate_dragonfly_batch_item
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from garden.energy.constructionsets import (
    _inline_construction_from_dict,
    create_construction,
    create_material,
)
from garden.fairyfly.availability import fairyfly_tools_enabled
from garden.honeybee_core.targets import normalize_honeybee_model_target
from garden.ironbug._schemas import (
    validate_air_loops,
    validate_ironbug_components,
    validate_ironbug_specification,
    validate_plant_loops,
    validate_thermal_zones,
    validate_vrf_systems,
)
from garden.ironbug.runtime import IronbugRuntimeUnavailable
from garden.ironbug.service import _runtime_blocked_response
from garden.ironbug.targets import normalize_ironbug_model_target
from garden.manifest import CURRENT_SCHEMA_VERSION, GardenManifest
from ladybug_tools_mcp.contracts import (
    ArtifactTargetRef,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    DataCollectionTargetRef,
    FlowerpotRef,
    GardenTargetRef,
    IronbugModelTargetRef,
    LibraryObjectTargetRef,
    MappingReadMixin,
    MutationResultModel,
    RunTargetRef,
    SkyTargetRef,
    WeatherTargetRef,
    validate_output,
)
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.server import create_mcp
from ladybug_tools_mcp.tools.ironbug import (
    ApplyToModelResult,
    DescribeComponentsResult,
    InspectSystemResult,
    IronbugSystemMutationResult,
    ListComponentsResult,
    ValidateSystemResult,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MAX_INPUT_SCHEMA_BYTES = 20 * 1024
_MAX_OUTPUT_SCHEMA_BYTES = 5 * 1024
_REPRESENTATIVE_SCHEMA_TOOLS = (
    "HB_Create_Model",
    "EP_Create_Material",
    "DF_Model",
    "GD_Create",
    "LB_Get_Runtime_Config",
    "LB_Calculate_Comfort",
    "RAD_Create_Sky_Asset",
    "IB_Configure_Loops",
    "IB_Upsert_Components",
    "IB_Validate_System",
    "IB_List_Components",
)
_IRONBUG_TOOLS = (
    "IB_List_Components",
    "IB_Describe_Component",
    "IB_Create_System",
    "IB_Upsert_Components",
    "IB_Configure_Loops",
    "IB_Inspect_System",
    "IB_Validate_System",
    "IB_Apply_To_Model",
)
_IRONPYTHON_CORE_FILES = (
    Path("src/flowerpot/runtime.py"),
    Path("src/flowerpot/component_state.py"),
    Path("src/flowerpot/input_guard.py"),
    Path("src/flowerpot/installation.py"),
    Path("src/flowerpot/worker.py"),
)
_FORBIDDEN_IRONPYTHON_ROOTS = {"pydantic", "garden", "ladybug_tools_mcp"}


def _list_registered_tools() -> list[Any]:
    mcp = register_tools(FastMCP("test", strict_input_validation=True))
    return asyncio.run(mcp.list_tools())


def _extract_text(res: Any) -> str:
    parts: list[str] = []
    data = getattr(res, "data", None)
    if data is not None:
        parts.append(data if isinstance(data, str) else json.dumps(data))
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text)
    return "\n".join(parts)


def _extract_schema_text(res: Any) -> str:
    data = getattr(res, "data", None)
    if isinstance(data, str):
        return data
    blocks = [
        text
        for block in getattr(res, "content", []) or []
        if isinstance((text := getattr(block, "text", None)), str) and text.strip()
    ]
    if blocks:
        return "\n".join(blocks)
    return _extract_text(res)


def _parse_json_tool_result(res: Any) -> dict[str, Any]:
    structured = getattr(res, "structured_content", None)
    if isinstance(structured, dict):
        return structured
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


def _collect_pydantic_warnings(caught: list[warnings.WarningMessage]) -> list[str]:
    return [
        f"{w.category.__name__}: {w.message}"
        for w in caught
        if "PydanticSerializationUnexpectedValue" in str(w.message)
        or "PydanticSerializationUnexpectedValue" in w.category.__name__
        or "Pydantic" in w.category.__name__
    ]


def _extract_markdown_section(doc: str, tool_name: str) -> str:
    header = f"### {tool_name}"
    start = doc.find(header)
    assert start != -1, f"Missing schema section for {tool_name!r} in Code Mode output:\n{doc}"
    next_header = doc.find("\n### ", start + len(header))
    return doc[start:] if next_header == -1 else doc[start:next_header]


def test_zero_undocumented_tool_parameters() -> None:
    """Every parameter of every registered MCP tool must declare a non-empty description."""
    tools = _list_registered_tools()
    expected_count = 109 if fairyfly_tools_enabled() else 103
    assert len(tools) == expected_count

    missing_descriptions: list[str] = []
    for tool in tools:
        properties = (tool.parameters or {}).get("properties", {})
        for param_name, prop_schema in properties.items():
            desc = prop_schema.get("description") if isinstance(prop_schema, dict) else None
            if not isinstance(desc, str) or not desc.strip():
                missing_descriptions.append(f"{tool.name}.{param_name}")

    assert missing_descriptions == [], f"Undocumented tool parameters: {missing_descriptions}"


def test_zero_opaque_output_schema() -> None:
    """Every registered MCP tool must expose structured outputSchema properties."""
    tools = _list_registered_tools()
    expected_count = 109 if fairyfly_tools_enabled() else 103
    assert len(tools) == expected_count

    opaque_tools: list[str] = []
    for tool in tools:
        out_schema = tool.output_schema
        props = out_schema.get("properties") if isinstance(out_schema, dict) else None
        if (
            not isinstance(out_schema, dict)
            or out_schema == {"additionalProperties": True, "type": "object"}
            or not isinstance(props, dict)
            or not props
        ):
            opaque_tools.append(tool.name)

    assert opaque_tools == [], f"Tools with opaque outputSchema: {opaque_tools}"


def test_code_mode_get_schema_exposes_real_return_fields() -> None:
    """Code Mode get_schema(detail='detailed') must list real return fields, never opaque object."""
    mcp = create_mcp()

    async def _fetch() -> str:
        async with Client(mcp) as client:
            res = await client.call_tool(
                "get_schema",
                {"tools": list(_REPRESENTATIVE_SCHEMA_TOOLS), "detail": "detailed"},
            )
            return _extract_text(res)

    schema_doc = asyncio.run(_fetch())
    for tool_name in _REPRESENTATIVE_SCHEMA_TOOLS:
        section = _extract_markdown_section(schema_doc, tool_name)
        assert "**Returns**" in section, f"Missing **Returns** block in {tool_name} schema"
        assert "- `value` (object)" not in section, f"Opaque return in {tool_name}:\n{section}"
        assert "- value (object)" not in section, f"Opaque return in {tool_name}:\n{section}"
        returns_block = section.split("**Returns**", 1)[1]
        assert "- `" in returns_block, f"Expected structured return fields for {tool_name}:\n{section}"


def test_schema_size_budget() -> None:
    """All registered MCP tools (including Ironbug) must stay within 20 KB inputSchema and 5 KB outputSchema."""
    tools = _list_registered_tools()
    oversized: list[str] = []
    for tool in tools:
        in_bytes = len(json.dumps(tool.parameters or {}).encode("utf-8"))
        out_bytes = len(json.dumps(tool.output_schema or {}).encode("utf-8"))
        if in_bytes > _MAX_INPUT_SCHEMA_BYTES or out_bytes > _MAX_OUTPUT_SCHEMA_BYTES:
            oversized.append(f"{tool.name}(input={in_bytes}B, output={out_bytes}B)")

    assert oversized == [], f"Tools exceeding schema size budget: {oversized}"


def test_zero_pydantic_serialization_warnings(tmp_path: Path) -> None:
    """Invoking representative FastMCP tools must emit zero PydanticSerializationUnexpectedValue warnings."""
    raw_mcp = register_tools(FastMCP("warnings-test", strict_input_validation=True))
    garden_root = (tmp_path / "warnings_garden").as_posix()

    async def _invoke() -> None:
        async with Client(raw_mcp) as client:
            calls = [
                ("GD_Create", {"name": "warnings_garden", "root_dir": garden_root}),
                ("HB_Create_Model", {"garden_root": garden_root, "identifier": "hb_warn"}),
                ("DF_Model", {"garden_root": garden_root, "identifier": "df_warn"}),
                (
                    "EP_Create_Material",
                    {
                        "material_type": "opaque",
                        "identifier": "mat_warn",
                        "params": {
                            "thickness": 0.2,
                            "conductivity": 1.4,
                            "density": 2200,
                            "specific_heat": 900,
                        },
                        "garden_root": garden_root,
                    },
                ),
                ("LB_Get_Runtime_Config", {"include_path_updates": False}),
            ]
            for tool_name, arguments in calls:
                res = await client.call_tool(tool_name, arguments)
                assert not getattr(res, "is_error", False), f"{tool_name} failed: {res!r}"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        asyncio.run(_invoke())

    pydantic_warnings = _collect_pydantic_warnings(caught)
    assert pydantic_warnings == [], f"Unexpected Pydantic warnings: {pydantic_warnings}"


def test_garden_manifest_pydantic_validation(tmp_path: Path) -> None:
    """GardenManifest enforces Pydantic validation on roundtrips and invalid fields."""
    manifest = GardenManifest.new("contract_garden", description="Contract verification")
    manifest.write(tmp_path)
    loaded = GardenManifest.read(tmp_path)

    assert loaded.garden_id == manifest.garden_id
    assert loaded.name == "contract_garden"
    assert loaded.description == "Contract verification"
    assert loaded.schema_version == CURRENT_SCHEMA_VERSION
    assert loaded.revision == 1
    assert GardenManifest.from_dict(loaded.to_dict()).to_dict() == loaded.to_dict()

    base_payload = loaded.to_dict()

    for bad_revision in (True, False, -1, 1.5, "1"):
        bad = dict(base_payload, revision=bad_revision)
        with pytest.raises(ValueError):
            GardenManifest.from_dict(bad)

    mutated = GardenManifest.from_dict(base_payload)
    mutated.revision = True  # type: ignore[assignment]
    with pytest.raises(ValueError):
        mutated.validate()

    for bad_version in ("2", "", None, 1):
        bad = dict(base_payload, schema_version=bad_version)
        with pytest.raises(ValueError):
            GardenManifest.from_dict(bad)
    missing_version = dict(base_payload)
    missing_version.pop("schema_version")
    with pytest.raises(ValueError):
        GardenManifest.from_dict(missing_version)

    for bad_id in ("", "   ", None, 123):
        with pytest.raises(ValueError):
            GardenManifest.from_dict(dict(base_payload, garden_id=bad_id))
        with pytest.raises(ValueError):
            GardenManifest.from_dict(dict(base_payload, name=bad_id))

    for bad_models in (["not_a_dict"], [123], "not_a_list"):
        with pytest.raises(ValueError):
            GardenManifest.from_dict(dict(base_payload, models=bad_models))


def test_target_and_service_schema_validation() -> None:
    """Target normalizers and strict service schemas validate valid inputs and reject malformed/extra keys."""
    hb_target = normalize_honeybee_model_target({"target_type": "honeybee_model", "id": "hb_main"})
    assert hb_target["domain"] == "honeybee"
    assert hb_target["model_identifier"] == "hb_main"
    for invalid_hb in ("hb_main", {}, {"target_type": "dragonfly_model", "id": "hb_main"}, {"target_type": "honeybee_model", "id": ""}):
        with pytest.raises(ValueError):
            normalize_honeybee_model_target(invalid_hb)

    df_obj = normalize_dragonfly_object_target(
        {
            "target_type": "dragonfly_object",
            "domain": "dragonfly",
            "model_identifier": "df_main",
            "object_type": "room2d",
            "object_identifier": "room_1",
        },
        expected_type="room2d",
    )
    assert df_obj["object_identifier"] == "room_1"
    with pytest.raises(ValueError):
        normalize_dragonfly_object_target(df_obj, expected_type="story")
    for invalid_df in (
        "room_1",
        {"target_type": "honeybee_object", "domain": "dragonfly", "model_identifier": "m", "object_type": "room2d", "object_identifier": "r"},
        {"target_type": "dragonfly_object", "domain": "dragonfly", "model_identifier": "", "object_type": "room2d", "object_identifier": "r"},
    ):
        with pytest.raises(ValueError):
            normalize_dragonfly_object_target(invalid_df)

    ib_target = normalize_ironbug_model_target(
        {"target_type": "ironbug_model", "id": "hvac_1", "path": "models/ironbug/hvac_1.json"}
    )
    assert ib_target["domain"] == "ironbug"
    assert ib_target["root_type"] == "IB_HVACSystem"
    for invalid_ib in (
        "hvac_1",
        {"target_type": "ironbug_model", "id": "hvac_1"},
        {"target_type": "ironbug_model", "id": "", "path": "models/ironbug/hvac_1.json"},
    ):
        with pytest.raises(ValueError):
            normalize_ironbug_model_target(invalid_ib)

    mat_ok = create_material(
        material_type="opaque",
        identifier="valid_mat",
        params={"thickness": 0.2, "conductivity": 1.4, "density": 2200, "specific_heat": 900},
    )
    assert mat_ok["object_dict"]["identifier"] == "valid_mat"
    with pytest.raises(ValueError):
        create_material(
            material_type="opaque",
            identifier="bad_mat",
            params={
                "thickness": 0.2,
                "conductivity": 1.4,
                "density": 2200,
                "specific_heat": 900,
                "unexpected_extra": 42,
            },
        )

    con_ok = create_construction(
        construction_type="shade",
        identifier="valid_shade_con",
        params={"solar_reflectance": 0.35},
    )
    assert con_ok["object_dict"]["identifier"] == "valid_shade_con"
    with pytest.raises(ValueError):
        create_construction(
            construction_type="shade",
            identifier="bad_shade_con",
            params={"solar_reflectance": 0.35, "unexpected_extra": True},
        )

    inline_ok = _inline_construction_from_dict(
        {"u_factor": 1.6, "shgc": 0.35, "vt": 0.6},
        field_name="aperture_set.window_construction",
    )
    assert inline_ok.identifier == "custom_window"
    with pytest.raises(ValueError):
        _inline_construction_from_dict(
            {"u_factor": 1.6, "shgc": 0.35, "unexpected_extra": 123},
            field_name="aperture_set.window_construction",
        )

    df_item_ok = validate_dragonfly_batch_item(
        "room2d",
        {"identifier": "r2d_1", "x_dim": 4.0, "y_dim": 5.0},
    )
    assert df_item_ok["identifier"] == "r2d_1"
    with pytest.raises(ValueError):
        validate_dragonfly_batch_item(
            "room2d",
            {"identifier": "r2d_bad", "unknown_extra_key": True},
        )
    with pytest.raises(ValueError):
        validate_dragonfly_batch_item(
            "context_shade",
            {"identifier": "shade_bad", "unknown_extra_key": True},
        )


def test_ironpython_isolation_guard() -> None:
    """IronPython runtime and Grasshopper component sources must never import pydantic, garden, or ladybug_tools_mcp."""
    gh_files = sorted((_REPO_ROOT / "src/grasshopper_components").rglob("*.py"))
    assert gh_files, "Expected Python files under src/grasshopper_components/"

    targets = [(_REPO_ROOT / rel) for rel in _IRONPYTHON_CORE_FILES] + gh_files
    violations: list[str] = []

    for path in targets:
        assert path.is_file(), f"Missing IronPython-isolated file: {path}"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        rel_path = path.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in _FORBIDDEN_IRONPYTHON_ROOTS:
                        violations.append(f"{rel_path}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0]
                if root in _FORBIDDEN_IRONPYTHON_ROOTS:
                    violations.append(f"{rel_path}:{node.lineno}: from {node.module} import ...")

    assert violations == [], f"Forbidden imports in IronPython-isolated files: {violations}"


def test_compact_target_ref_json_schemas_preserve_runtime_validation() -> None:
    """TargetRef and FlowerpotRef emit compact JSON schemas (<200 B) while enforcing runtime types."""
    ref_models = (
        GardenTargetRef,
        BuildingModelTargetRef,
        BuildingObjectTargetRef,
        IronbugModelTargetRef,
        RunTargetRef,
        LibraryObjectTargetRef,
        DataCollectionTargetRef,
        WeatherTargetRef,
        ArtifactTargetRef,
        SkyTargetRef,
        FlowerpotRef,
    )
    for model_cls in ref_models:
        schema = model_cls.model_json_schema()
        encoded_bytes = len(json.dumps(schema).encode("utf-8"))
        assert encoded_bytes < 200, f"{model_cls.__name__} JSON schema too large: {encoded_bytes}B"
        assert schema == {
            "type": "object",
            "title": model_cls.__name__,
            "additionalProperties": True,
        }

    with pytest.raises(ValidationError):
        BuildingModelTargetRef.model_validate({"target_type": 123})
    with pytest.raises(ValidationError):
        DataCollectionTargetRef.model_validate({"garden_id": 456})
    with pytest.raises(ValidationError):
        FlowerpotRef.model_validate({"target": "not_a_dict"})

    parsed_model = BuildingModelTargetRef.model_validate(
        {"target_type": "honeybee_model", "id": "m1", "custom_extra": "kept"}
    )
    assert parsed_model.target_type == "honeybee_model"
    assert parsed_model.model_dump(exclude_none=True)["custom_extra"] == "kept"

    parsed_fp = FlowerpotRef.model_validate(
        {"type": "Flowerpot", "kind": "honeybee", "extra_meta": 7}
    )
    assert parsed_fp.kind == "honeybee"
    assert parsed_fp.model_dump(exclude_none=True)["extra_meta"] == 7


def test_mapping_read_mixin_dict_lookup_and_zero_warnings() -> None:
    """_MappingReadMixin supports direct tool.fn() subscript/get/in lookups without serialization warnings."""
    res = validate_output(
        MutationResultModel,
        {
            "target": {"target_type": "dragonfly_model", "id": "df_1"},
            "report": {"status": "ok", "message": "created"},
            "extra_payload": "kept",
        },
    )
    assert res["target"] == {"target_type": "dragonfly_model", "id": "df_1"}
    assert res["report"]["status"] == "ok"
    assert res["extra_payload"] == "kept"
    assert res.get("missing", "x") == "x"
    assert "target" in res
    assert "extra_payload" in res
    assert "model_target" not in res
    with pytest.raises(KeyError):
        _ = res["model_target"]

    target_ref = BuildingModelTargetRef.model_validate(
        {"target_type": "honeybee_model", "id": "hb_1", "custom_tag": "a"}
    )
    assert target_ref["id"] == "hb_1"
    assert target_ref.get("unset", "fallback") == "fallback"
    assert "custom_tag" in target_ref
    assert "model_identifier" not in target_ref

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        revalidated = MutationResultModel.model_validate(res.model_dump(exclude_none=True))
        dumped = revalidated.model_dump_json()
    assert json.loads(dumped)["target"]["id"] == "df_1"
    assert _collect_pydantic_warnings(caught) == []


def test_ironbug_service_schema_validation() -> None:
    """Ironbug service schemas validate valid authoring payloads and reject malformed/extra keys."""
    assert validate_ironbug_components(None) == {}

    dict_comps = validate_ironbug_components(
        {
            "fan_1": {
                "type": "IB_FanOnOff",
                "fields": {"FanTotalEfficiency": 0.65},
                "output_variables": [
                    "Fan Electricity Rate",
                    {"variable_name": "Fan Air Mass Flow Rate", "reporting_frequency": "Timestep"},
                ],
                "ems_sensors": [
                    {
                        "name": "FanPower",
                        "key_name": "*",
                        "output_variable": "Fan Electricity Rate",
                    }
                ],
            },
            "fcu_1": {
                "type": "IB_ZoneHVACFourPipeFanCoil",
                "wiring": {"fan": "fan_1"},
            },
        }
    )
    assert set(dict_comps) == {"fan_1", "fcu_1"}
    assert dict_comps["fan_1"]["output_variables"][1]["reporting_frequency"] == "Timestep"
    assert dict_comps["fan_1"]["ems_sensors"][0]["name"] == "FanPower"
    assert dict_comps["fcu_1"]["wiring"] == {"fan": "fan_1"}

    list_comps = validate_ironbug_components(
        [
            {
                "id": "chiller_1",
                "type": "IB_ChillerElectricEIR",
                "fields": {"ReferenceCOP": 5.5},
                "output_variables": ["Chiller Electricity Rate"],
                "ems_sensors": ["chiller_sensor"],
            },
            {
                "id": "pump_1",
                "type": "IB_PumpVariableSpeed",
                "wiring": {"set_schedule": "sched_1"},
            },
        ]
    )
    assert set(list_comps) == {"chiller_1", "pump_1"}
    assert "id" not in list_comps["chiller_1"]
    assert list_comps["chiller_1"]["fields"] == {"ReferenceCOP": 5.5}
    assert list_comps["pump_1"]["wiring"] == {"set_schedule": "sched_1"}

    zones = validate_thermal_zones(
        [
            {
                "room_name": "Room_1",
                "air_terminal": "vav_1",
                "zone_equipments": ["fcu_1"],
                "output_variables": ["Zone Mean Air Temperature"],
                "ems_sensors": [
                    {"name": "ZTemp", "key_name": "*", "output_variable": "Zone Mean Air Temperature"}
                ],
            }
        ]
    )
    assert zones is not None and len(zones) == 1
    assert zones[0]["room_name"] == "Room_1"

    air_loops = validate_air_loops(
        [
            {
                "name": "VAV_AirLoop",
                "sizing_system": "ahu_sizing",
                "supply": ["oa_sys", "fan_1"],
                "demand_zones": ["Room_1"],
            }
        ]
    )
    assert air_loops is not None and len(air_loops) == 1
    assert air_loops[0]["name"] == "VAV_AirLoop"

    plant_loops = validate_plant_loops(
        [
            {
                "name": "CHWLoop",
                "loop_type": "Cooling",
                "design_loop_exit_temperature": 6.7,
                "loop_design_temperature_difference": 5.6,
                "supply": ["pump_1"],
                "supply_branches": [["chiller_1"]],
                "demand_branches": [["cc_1"]],
                "bypass_pipes": {"supply": True, "demand": None},
            }
        ]
    )
    assert plant_loops is not None and len(plant_loops) == 1
    assert plant_loops[0]["bypass_pipes"] == {"supply": True, "demand": None}

    vrf_systems = validate_vrf_systems([{"vrf": "vrf_outdoor", "terminals": ["vrf_term_1"]}])
    assert vrf_systems is not None and len(vrf_systems) == 1
    assert vrf_systems[0]["vrf"] == "vrf_outdoor"

    official_spec = {
        "$type": "Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC",
        "DisplayName": "ImportedSystem",
        "AirLoops": [{"$type": "Ironbug.HVAC.IB_AirLoopHVAC, Ironbug.HVAC"}],
        "PlantLoops": [],
    }
    validated_spec = validate_ironbug_specification(official_spec)
    assert isinstance(validated_spec, dict)
    assert validated_spec["$type"] == "Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"
    assert validated_spec["AirLoops"] == [{"$type": "Ironbug.HVAC.IB_AirLoopHVAC, Ironbug.HVAC"}]

    with pytest.raises(ValueError):
        validate_ironbug_components({"fan_1": {"type": "IB_FanOnOff", "unexpected_extra": True}})
    with pytest.raises(ValueError):
        validate_ironbug_components([{"id": "fan_1", "type": "IB_FanOnOff", "unexpected_extra": True}])
    with pytest.raises(ValueError):
        validate_thermal_zones([{"room_name": "Room_1", "unexpected_extra": True}])
    with pytest.raises(ValueError):
        validate_air_loops([{"name": "AHU_1", "unexpected_extra": True}])
    with pytest.raises(ValueError):
        validate_plant_loops([{"name": "CHWLoop", "unexpected_extra": True}])
    with pytest.raises(ValueError):
        validate_vrf_systems([{"vrf": "vrf_1", "terminals": ["t1"], "unexpected_extra": True}])

    for ems_field in ("ems_sensors", "ems_internal_variables", "ems_actuators"):
        with pytest.raises(ValueError):
            validate_ironbug_components({"c1": {"type": "IB_FanOnOff", ems_field: [{}]}})

    with pytest.raises(ValueError):
        validate_ironbug_components([{"type": "IB_FanOnOff"}])
    with pytest.raises(ValueError):
        validate_ironbug_components([{"id": "   ", "type": "IB_FanOnOff"}])

    for bad_dt in (0, 0.0, -5.0):
        with pytest.raises(ValueError):
            validate_plant_loops([{"name": "CHWLoop", "loop_design_temperature_difference": bad_dt}])


def test_ironbug_output_contracts_and_blocked_hydration(tmp_path: Path) -> None:
    """Ironbug outputs preserve MappingReadMixin, compact blocked responses, loose category input, and Code Mode budgets."""
    del tmp_path

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        sample_cases: list[tuple[type[Any], dict[str, Any], str, Any, str]] = [
            (
                ListComponentsResult,
                {
                    "matches": [{"type_name": "IB_PumpVariableSpeed", "category": "pump"}],
                    "total_matched": 1,
                    "report": {"status": "ok", "message": "listed"},
                },
                "total_matched",
                1,
                "unknown_category",
            ),
            (
                DescribeComponentsResult,
                {
                    "components": [
                        {
                            "type_name": "IB_ChillerElectricEIR",
                            "category": "plant_equipment",
                            "core_fields": [
                                {"name": "ReferenceCOP", "type": "number", "default": 5.5},
                            ],
                        }
                    ],
                    "not_found": [],
                    "report": {"status": "ok", "message": "described"},
                },
                "not_found",
                [],
                "missing_field",
            ),
            (
                IronbugSystemMutationResult,
                {
                    "target": {"target_type": "ironbug_model", "id": "hvac_1", "path": "models/ironbug/hvac_1.json"},
                    "ironbug_model_target": {
                        "target_type": "ironbug_model",
                        "id": "hvac_1",
                        "path": "models/ironbug/hvac_1.json",
                    },
                    "summary_view": {"air_loop_count": 1},
                    "persistence_receipt": {"status": "persisted", "persisted_path": "models/ironbug/hvac_1.json"},
                    "report": {"status": "ok", "message": "mutated"},
                },
                "summary_view",
                {"air_loop_count": 1},
                "missing_field",
            ),
            (
                InspectSystemResult,
                {
                    "target": {"target_type": "ironbug_model", "id": "hvac_1", "path": "models/ironbug/hvac_1.json"},
                    "summary_view": {"component_count": 2},
                    "draft": {"components": {}},
                    "report": {"status": "ok", "message": "inspected"},
                },
                "draft",
                {"components": {}},
                "missing_field",
            ),
            (
                ValidateSystemResult,
                {
                    "valid": True,
                    "ready": True,
                    "target": {"target_type": "ironbug_model", "id": "hvac_1", "path": "models/ironbug/hvac_1.json"},
                    "openstudio_summary": {"thermal_zones": 1},
                    "system_summary": {"air_loop_count": 0},
                    "report": {"status": "ok", "message": "valid"},
                },
                "openstudio_summary",
                {"thermal_zones": 1},
                "forward_translator",
            ),
            (
                ApplyToModelResult,
                {
                    "target": {"target_type": "honeybee_model", "id": "hb_1", "model_identifier": "hb_1"},
                    "updated_model_target": {
                        "target_type": "honeybee_model",
                        "id": "hb_1",
                        "model_identifier": "hb_1",
                    },
                    "detailed_hvac_identifier": "hvac_1_detailed_hvac",
                    "report": {"status": "ok", "message": "applied"},
                },
                "detailed_hvac_identifier",
                "hvac_1_detailed_hvac",
                "dragonfly_model_target",
            ),
        ]

        for model_cls, payload, present_key, expected_val, missing_key in sample_cases:
            validated = model_cls.model_validate(payload)
            assert isinstance(validated, MappingReadMixin)
            assert validated[present_key] == expected_val
            assert validated.get(present_key) == expected_val
            assert validated.get(missing_key, "fallback") == "fallback"
            assert present_key in validated
            assert missing_key not in validated
            with pytest.raises(KeyError):
                _ = validated[missing_key]

        desc_res = DescribeComponentsResult.model_validate(
            {
                "components": [
                    {
                        "type_name": "IB_ChillerElectricEIR",
                        "category": "plant_equipment",
                        "core_fields": [
                            {"name": "ReferenceCOP", "type": "number", "default": 5.5},
                        ],
                    }
                ],
                "not_found": [],
                "report": {"status": "ok", "message": "described"},
            }
        )
        assert desc_res["components"][0]["core_fields"][0]["default"] == 5.5

        blocked_raw = _runtime_blocked_response(
            IronbugRuntimeUnavailable("missing", missing=["dotnet"], details={"dotnet_exe": None})
        )
        blocked_res = ValidateSystemResult.model_validate(blocked_raw)
        assert blocked_res["blocked"] is True
        assert blocked_res.openstudio_summary is None
        assert "openstudio_summary" not in blocked_res
        blocked_dumped = blocked_res.model_dump(exclude_none=True)
        assert blocked_dumped["blocked"] is True
        assert "openstudio_summary" not in blocked_dumped
        assert len(json.dumps(blocked_dumped).encode("utf-8")) < 1024

        raw_mcp = register_tools(FastMCP("ib-contracts-test", strict_input_validation=True))
        bridge_calls: list[tuple[str, dict[str, Any]]] = []

        class _FakeBridgeClient:
            def call(
                self,
                method: str,
                payload: dict[str, Any],
                timeout: float = 30.0,
            ) -> dict[str, Any]:
                del timeout
                bridge_calls.append((method, dict(payload)))
                if payload.get("category") == "nonexistent_cat":
                    return {
                        "matches": [],
                        "categories": {"pump": 2, "fan": 3},
                        "total_catalog_types": 5,
                        "total_matched": 0,
                        "offset": 0,
                        "truncated": False,
                        "unknown_category": "nonexistent_cat",
                        "valid_categories": ["fan", "pump"],
                    }
                return {
                    "matches": [
                        {
                            "type_name": "IB_PumpVariableSpeed",
                            "category": "pump",
                            "base_type": "IB_Pump",
                            "summary": "Variable speed hydronic pump.",
                        }
                    ],
                    "categories": {"pump": 1},
                    "total_catalog_types": 1,
                    "total_matched": 1,
                    "offset": 0,
                    "truncated": False,
                }

        async def _invoke_ib_list() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(raw_mcp) as client:
                res_pump = await client.call_tool(
                    "IB_List_Components",
                    {"category": "Pump", "limit": 10},
                )
                assert not getattr(res_pump, "is_error", False), f"IB_List_Components('Pump') failed: {res_pump!r}"
                res_unknown = await client.call_tool(
                    "IB_List_Components",
                    {"category": "nonexistent_cat"},
                )
                assert not getattr(res_unknown, "is_error", False), (
                    f"IB_List_Components('nonexistent_cat') failed: {res_unknown!r}"
                )
                return _parse_json_tool_result(res_pump), _parse_json_tool_result(res_unknown)

        with mock.patch("garden.ironbug.service.get_bridge_client", return_value=_FakeBridgeClient()):
            pump_payload, unknown_payload = asyncio.run(_invoke_ib_list())

        assert bridge_calls[0][0] == "catalog"
        assert bridge_calls[0][1]["category"] == "pump"
        assert pump_payload["report"]["status"] == "ok"
        assert pump_payload["matches"][0]["type_name"] == "IB_PumpVariableSpeed"

        assert bridge_calls[1][0] == "catalog"
        assert bridge_calls[1][1]["category"] == "nonexistent_cat"
        assert unknown_payload["report"]["status"] == "warning"
        assert unknown_payload["unknown_category"] == "nonexistent_cat"
        assert unknown_payload["valid_categories"] == ["fan", "pump"]

        code_mode_mcp = create_mcp()

        async def _fetch_ironbug_full_schemas() -> tuple[str, str]:
            async with Client(code_mode_mcp) as client:
                all_res = await client.call_tool(
                    "get_schema",
                    {"tools": list(_IRONBUG_TOOLS), "detail": "full"},
                )
                cfg_res = await client.call_tool(
                    "get_schema",
                    {"tools": ["IB_Configure_Loops"], "detail": "full"},
                )
                return _extract_schema_text(all_res), _extract_schema_text(cfg_res)

        all_full_doc, cfg_full_doc = asyncio.run(_fetch_ironbug_full_schemas())
        all_full_items = json.loads(all_full_doc)
        assert {item["name"] for item in all_full_items} == set(_IRONBUG_TOOLS)
        cfg_full_items = json.loads(cfg_full_doc)
        assert [item["name"] for item in cfg_full_items] == ["IB_Configure_Loops"]
        assert len(json.dumps(all_full_items).encode("utf-8")) < 45 * 1024
        assert len(json.dumps(cfg_full_items).encode("utf-8")) < 10 * 1024
        assert len(all_full_doc.encode("utf-8")) < 80 * 1024
        assert len(cfg_full_doc.encode("utf-8")) < 15 * 1024

    pydantic_warnings = _collect_pydantic_warnings(caught)
    assert pydantic_warnings == [], f"Unexpected Pydantic warnings: {pydantic_warnings}"
