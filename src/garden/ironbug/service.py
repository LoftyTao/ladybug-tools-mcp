"""Service layer for the 8 high-cohesion Ironbug DetailedHVAC MCP tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from honeybee.model import Model as HoneybeeModel
from honeybee.room import Room as HoneybeeRoom
from honeybee_energy.hvac.detailed import DetailedHVAC

from garden.dragonfly_core.conversion import dragonfly_model_to_honeybee
from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target as resolve_dragonfly_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target as resolve_honeybee_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target
from garden.ironbug.client import IronbugBridgeError, get_bridge_client
from garden.ironbug.runtime import IronbugRuntimeUnavailable
from garden.ironbug.store import (
    empty_draft,
    load_ironbug_system_files,
    save_ironbug_system,
)
from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report

_CN_QUERY_ALIASES: tuple[tuple[str, str], ...] = (
    ("冷水机组", "chiller"),
    ("冷机", "chiller"),
    ("冷却塔", "cooling tower"),
    ("风机盘管", "four pipe fan coil"),
    ("锅炉", "boiler"),
    ("热泵", "heat pump"),
    ("水泵", "pump"),
    ("循环泵", "pump"),
    ("风机", "fan"),
    ("盘管", "coil"),
    ("变风量", "vav"),
    ("新风机组", "outdoor air"),
    ("新风", "outdoor air"),
    ("多联机", "vrf"),
    ("设定点", "setpoint"),
    ("窗机", "ptac"),
    ("热回收", "heat exchanger"),
    ("辐射", "radiant"),
    ("空调箱", "air loop"),
    ("加湿", "humidifier"),
    ("蓄冷", "thermal storage"),
    ("冰蓄冷", "thermal storage"),
    ("太阳能", "solar"),
    ("光伏", "photovoltaic"),
)


def _expand_query(query: str | None) -> str | None:
    if not query or not query.strip():
        return None
    text = query.strip()
    remaining = text
    extra: list[str] = []
    for cn, en in sorted(_CN_QUERY_ALIASES, key=lambda pair: len(pair[0]), reverse=True):
        if cn in remaining:
            extra.append(en)
            remaining = remaining.replace(cn, " ")
    if not extra:
        return text
    # Strip leftover non-ASCII chars so C# ASCII token matcher hits cleanly
    ascii_tokens = " ".join(
        tok for tok in remaining.split() if all(ord(ch) < 128 for ch in tok)
    )
    return " ".join(part for part in [ascii_tokens, *extra] if part).strip()


def _runtime_blocked_response(exc: IronbugRuntimeUnavailable) -> dict[str, Any]:
    return {
        "blocked": True,
        "missing": exc.missing,
        "details": exc.details,
        "report": make_report(
            status="blocked",
            message=str(exc),
            details=exc.details,
        ),
    }


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _normalize_components_input(
    components: dict[str, dict[str, Any]] | list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if components is None:
        return {}
    if isinstance(components, dict):
        normalized: dict[str, dict[str, Any]] = {}
        for comp_id, spec in components.items():
            key = str(comp_id).strip()
            if not key:
                raise ValueError("Component id must not be empty.")
            if not isinstance(spec, dict):
                raise ValueError(f"Component '{key}' specification must be a dict.")
            normalized[key] = dict(spec)
        return normalized
    if isinstance(components, list):
        normalized = {}
        for item in components:
            if not isinstance(item, dict):
                raise ValueError("Each component item must be a dict with 'id' and 'type'.")
            key = str(item.get("id") or "").strip()
            if not key:
                raise ValueError("Each component item in list form requires a non-empty 'id'.")
            spec = {k: v for k, v in item.items() if k != "id"}
            normalized[key] = spec
        return normalized
    raise ValueError("components must be a dict mapping id -> spec, or a list of dicts with 'id'.")


def list_ironbug_components(
    *,
    category: str | None = None,
    query: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Search or browse available official C# Ironbug component classes."""
    offset_val = max(0, int(offset))
    try:
        client = get_bridge_client(require_openstudio=False)
        expanded = _expand_query(query)
        result = client.call(
            "catalog",
            {
                "category": category.strip().lower() if category else None,
                "query": expanded,
                "limit": max(1, min(int(limit), 100)),
                "offset": offset_val,
            },
        )
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    matches = list(result.get("matches") or [])
    total_matched = result.get("total_matched", len(matches))
    truncated = bool(result.get("truncated", False))
    unknown_category = result.get("unknown_category")
    valid_categories = list(result.get("valid_categories") or [])

    if unknown_category:
        status = "warning"
        message = (
            f"Unknown category '{unknown_category}'. "
            f"Valid categories: {', '.join(valid_categories)}."
        )
    elif truncated:
        next_offset = result.get("offset", offset_val) + len(matches)
        status = "ok"
        message = (
            f"Returned {len(matches)} of {total_matched} Ironbug component class(es) "
            f"(offset={result.get('offset', offset_val)}; pass offset={next_offset} for next page)."
        )
    else:
        status = "ok"
        message = f"Returned {len(matches)} of {total_matched} Ironbug component class(es)."

    payload: dict[str, Any] = {
        "matches": matches,
        "categories": result.get("categories") or {},
        "total_catalog_types": result.get("total_catalog_types", 0),
        "total_matched": total_matched,
        "offset": result.get("offset", offset_val),
        "truncated": truncated,
        "expanded_query": expanded if query and expanded != query else None,
        "report": make_report(
            status=status,
            message=message,
        ),
    }
    if unknown_category:
        payload["unknown_category"] = unknown_category
        payload["valid_categories"] = valid_categories
    return payload


def describe_ironbug_components(
    *,
    type_names: list[str] | str,
    include_advanced: bool = False,
) -> dict[str, Any]:
    """Inspect constructors, wiring methods, and FieldSet/EPDoc metadata for Ironbug types."""
    if isinstance(type_names, str):
        names = [part.strip() for part in type_names.split(",") if part.strip()]
    else:
        names = [str(n).strip() for n in type_names if n and str(n).strip()]
    if not names:
        raise ValueError("Provide at least one Ironbug component type name.")
    try:
        client = get_bridge_client(require_openstudio=False)
        result = client.call(
            "describe",
            {
                "type_names": names,
                "include_advanced": bool(include_advanced),
            },
        )
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    components = list(result.get("components") or [])
    not_found = list(result.get("not_found") or [])
    status = "warning" if not_found and components else ("error" if not_found else "ok")
    msg = f"Described {len(components)} Ironbug component type(s)."
    if not_found:
        msg += f" Not found: {', '.join(not_found)}."
    return {
        "components": components,
        "not_found": not_found,
        "report": make_report(status=status, message=msg),
    }


IRONBUG_TEMPLATE_NAMES: tuple[str, ...] = (
    "vav_chiller_boiler",
    "doas_fcu",
    "vrf_doas",
    "wshp",
)


def _normalize_template_rooms(room_names: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for raw in room_names or []:
        name = str(raw).strip()
        if name and name not in cleaned:
            cleaned.append(name)
    return cleaned or ["Zone1"]


def _build_template_draft(
    template: str,
    *,
    display_name: str | None = None,
    room_names: list[str] | None = None,
) -> dict[str, Any]:
    """Build an editable Ironbug draft from a named HVAC system template preset."""
    key = str(template).strip().lower()
    if key not in IRONBUG_TEMPLATE_NAMES:
        valid = ", ".join(IRONBUG_TEMPLATE_NAMES)
        raise ValueError(f"Unknown Ironbug template {template!r}. Valid templates: {valid}.")

    zones = _normalize_template_rooms(room_names)
    draft = empty_draft(display_name=display_name or key, imported_only=False)
    components: dict[str, dict[str, Any]] = {}
    thermal_zones: list[dict[str, Any]] = []
    air_loops: list[dict[str, Any]] = []
    plant_loops: list[dict[str, Any]] = []
    vrf_systems: list[dict[str, Any]] = []

    if key == "vav_chiller_boiler":
        components.update(
            {
                "oa_ctrl": {"type": "IB_ControllerOutdoorAir"},
                "oa_sys": {"type": "IB_OutdoorAirSystem", "wiring": {"controller": "oa_ctrl"}},
                "ahu_cc": {"type": "IB_CoilCoolingWater"},
                "ahu_hc": {"type": "IB_CoilHeatingWater"},
                "ahu_fan": {"type": "IB_FanVariableVolume"},
                "ahu_spm": {"type": "IB_SetpointManagerScheduled", "ctor_args": [12.8]},
                "ahu_am": {"type": "IB_AvailabilityManagerNightCycle"},
                "chw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "chiller": {
                    "type": "IB_ChillerElectricEIR",
                    "fields": {"ReferenceCapacity": "autosize", "ReferenceCOP": 5.5, "CondenserType": "WaterCooled"},
                },
                "cw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "cooling_tower": {"type": "IB_CoolingTowerVariableSpeed"},
                "hw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "boiler": {
                    "type": "IB_BoilerHotWater",
                    "fields": {"FuelType": "NaturalGas", "NominalCapacity": "autosize", "NominalThermalEfficiency": 0.85},
                },
            }
        )
        hw_demand_branches: list[list[str]] = [["ahu_hc"]]
        for idx, zname in enumerate(zones, 1):
            rh_id = f"vav_rh_{idx}"
            vav_id = f"vav_{idx}"
            components[rh_id] = {"type": "IB_CoilHeatingWater"}
            components[vav_id] = {"type": "IB_AirTerminalSingleDuctVAVReheat", "wiring": {"reheat_coil": rh_id}}
            thermal_zones.append({"room_name": zname, "air_terminal": vav_id})
            hw_demand_branches.append([rh_id])

        air_loops.append(
            {
                "name": "VAV_AirLoop",
                "availability_managers": ["ahu_am"],
                "supply": ["oa_sys", "ahu_cc", "ahu_hc", "ahu_fan", "ahu_spm"],
                "demand_zones": list(zones),
            }
        )
        plant_loops.extend(
            [
                {
                    "name": "ChilledWaterLoop",
                    "loop_type": "Cooling",
                    "design_loop_exit_temperature": 6.7,
                    "loop_design_temperature_difference": 5.6,
                    "supply": ["chw_pump"],
                    "supply_branches": [["chiller"]],
                    "bypass_pipes": True,
                    "supply_setpoint": 6.7,
                    "demand_branches": [["ahu_cc"]],
                },
                {
                    "name": "CondenserWaterLoop",
                    "loop_type": "Condenser",
                    "design_loop_exit_temperature": 29.4,
                    "loop_design_temperature_difference": 5.6,
                    "supply": ["cw_pump"],
                    "supply_branches": [["cooling_tower"]],
                    "bypass_pipes": True,
                    "supply_setpoint": 29.4,
                    "demand_branches": [["chiller"]],
                },
                {
                    "name": "HotWaterLoop",
                    "loop_type": "Heating",
                    "design_loop_exit_temperature": 82.0,
                    "loop_design_temperature_difference": 11.0,
                    "supply": ["hw_pump"],
                    "supply_branches": [["boiler"]],
                    "bypass_pipes": True,
                    "supply_setpoint": 82.0,
                    "demand_branches": hw_demand_branches,
                },
            ]
        )

    elif key == "doas_fcu":
        components.update(
            {
                "doas_hx": {"type": "IB_HeatExchangerAirToAirSensibleAndLatent"},
                "doas_oa_ctrl": {"type": "IB_ControllerOutdoorAir"},
                "doas_oa": {
                    "type": "IB_OutdoorAirSystem",
                    "wiring": {"controller": "doas_oa_ctrl", "oa_stream_objs": ["doas_hx"]},
                },
                "doas_cc": {"type": "IB_CoilCoolingWater"},
                "doas_hc": {"type": "IB_CoilHeatingWater"},
                "doas_fan": {"type": "IB_FanConstantVolume"},
                "doas_spm": {"type": "IB_SetpointManagerScheduled", "ctor_args": [18.0]},
                "doas_sizing": {
                    "type": "IB_SizingSystem",
                    "fields": {
                        "TypeofLoadtoSizeOn": "VentilationRequirement",
                        "AllOutdoorAirinCooling": True,
                        "AllOutdoorAirinHeating": True,
                    },
                },
                "chw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "chiller": {
                    "type": "IB_ChillerElectricEIR",
                    "fields": {"ReferenceCapacity": "autosize", "ReferenceCOP": 5.5, "CondenserType": "AirCooled"},
                },
                "hw_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "boiler": {
                    "type": "IB_BoilerHotWater",
                    "fields": {"FuelType": "NaturalGas", "NominalCapacity": "autosize", "NominalThermalEfficiency": 0.85},
                },
            }
        )
        chw_demand: list[list[str]] = [["doas_cc"]]
        hw_demand: list[list[str]] = [["doas_hc"]]
        for idx, zname in enumerate(zones, 1):
            term_id = f"doas_term_{idx}"
            fan_id = f"fcu_fan_{idx}"
            cc_id = f"fcu_cc_{idx}"
            hc_id = f"fcu_hc_{idx}"
            fcu_id = f"fcu_{idx}"
            components[term_id] = {"type": "IB_AirTerminalSingleDuctConstantVolumeNoReheat"}
            components[fan_id] = {"type": "IB_FanOnOff"}
            components[cc_id] = {"type": "IB_CoilCoolingWater"}
            components[hc_id] = {"type": "IB_CoilHeatingWater"}
            components[fcu_id] = {
                "type": "IB_ZoneHVACFourPipeFanCoil",
                "fields": {"CapacityControlMethod": "CyclingFan"},
                "wiring": {"fan": fan_id, "cooling_coil": cc_id, "heating_coil": hc_id},
            }
            thermal_zones.append(
                {
                    "room_name": zname,
                    "air_terminal": term_id,
                    "zone_equipments": [fcu_id],
                }
            )
            chw_demand.append([cc_id])
            hw_demand.append([hc_id])

        air_loops.append(
            {
                "name": "DOAS_AirLoop",
                "sizing_system": "doas_sizing",
                "supply": ["doas_oa", "doas_cc", "doas_hc", "doas_fan", "doas_spm"],
                "demand_zones": list(zones),
            }
        )
        plant_loops.extend(
            [
                {
                    "name": "ChilledWaterLoop",
                    "loop_type": "Cooling",
                    "design_loop_exit_temperature": 6.7,
                    "loop_design_temperature_difference": 5.6,
                    "supply": ["chw_pump"],
                    "supply_branches": [["chiller"]],
                    "bypass_pipes": True,
                    "supply_setpoint": 6.7,
                    "demand_branches": chw_demand,
                },
                {
                    "name": "HotWaterLoop",
                    "loop_type": "Heating",
                    "design_loop_exit_temperature": 82.0,
                    "loop_design_temperature_difference": 11.0,
                    "supply": ["hw_pump"],
                    "supply_branches": [["boiler"]],
                    "bypass_pipes": True,
                    "supply_setpoint": 82.0,
                    "demand_branches": hw_demand,
                },
            ]
        )

    elif key == "vrf_doas":
        components.update(
            {
                "doas_hx": {"type": "IB_HeatExchangerAirToAirSensibleAndLatent"},
                "doas_oa_ctrl": {"type": "IB_ControllerOutdoorAir"},
                "doas_oa": {
                    "type": "IB_OutdoorAirSystem",
                    "wiring": {"controller": "doas_oa_ctrl", "oa_stream_objs": ["doas_hx"]},
                },
                "doas_cc": {"type": "IB_CoilCoolingDXSingleSpeed"},
                "doas_hc": {"type": "IB_CoilHeatingElectric"},
                "doas_fan": {"type": "IB_FanConstantVolume"},
                "doas_spm": {"type": "IB_SetpointManagerScheduled", "ctor_args": [20.0]},
                "doas_sizing": {
                    "type": "IB_SizingSystem",
                    "fields": {
                        "TypeofLoadtoSizeOn": "VentilationRequirement",
                        "AllOutdoorAirinCooling": True,
                        "AllOutdoorAirinHeating": True,
                    },
                },
                "vrf_outdoor": {"type": "IB_AirConditionerVariableRefrigerantFlow"},
            }
        )
        vrf_terms: list[str] = []
        for idx, zname in enumerate(zones, 1):
            term_id = f"doas_term_{idx}"
            cc_id = f"vrf_cc_{idx}"
            hc_id = f"vrf_hc_{idx}"
            fan_id = f"vrf_fan_{idx}"
            vrf_t_id = f"vrf_term_{idx}"
            components[term_id] = {"type": "IB_AirTerminalSingleDuctConstantVolumeNoReheat"}
            components[cc_id] = {"type": "IB_CoilCoolingDXVariableRefrigerantFlow"}
            components[hc_id] = {"type": "IB_CoilHeatingDXVariableRefrigerantFlow"}
            components[fan_id] = {"type": "IB_FanOnOff"}
            components[vrf_t_id] = {
                "type": "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow",
                "ctor_args": [cc_id, hc_id, fan_id],
            }
            vrf_terms.append(vrf_t_id)
            thermal_zones.append(
                {
                    "room_name": zname,
                    "air_terminal": term_id,
                    "zone_equipments": [vrf_t_id],
                }
            )

        air_loops.append(
            {
                "name": "DOAS_AirLoop",
                "sizing_system": "doas_sizing",
                "supply": ["doas_oa", "doas_cc", "doas_hc", "doas_fan", "doas_spm"],
                "demand_zones": list(zones),
            }
        )
        vrf_systems.append({"vrf": "vrf_outdoor", "terminals": vrf_terms})

    elif key == "wshp":
        components.update(
            {
                "wshp_pump": {"type": "IB_PumpVariableSpeed", "fields": {"RatedFlowRate": "autosize"}},
                "wshp_boiler": {
                    "type": "IB_BoilerHotWater",
                    "fields": {"FuelType": "NaturalGas", "NominalCapacity": "autosize", "NominalThermalEfficiency": 0.85},
                },
                "wshp_tower": {"type": "IB_CoolingTowerVariableSpeed"},
                "wshp_spm": {"type": "IB_SetpointManagerScheduled", "ctor_args": [25.0]},
            }
        )
        demand_branches: list[list[str]] = []
        for idx, zname in enumerate(zones, 1):
            fan_id = f"wshp_fan_{idx}"
            hc_id = f"wshp_hc_{idx}"
            cc_id = f"wshp_cc_{idx}"
            supp_id = f"wshp_supp_{idx}"
            wshp_id = f"wshp_{idx}"
            components[fan_id] = {"type": "IB_FanOnOff"}
            components[hc_id] = {"type": "IB_CoilHeatingWaterToAirHeatPumpEquationFit"}
            components[cc_id] = {"type": "IB_CoilCoolingWaterToAirHeatPumpEquationFit"}
            components[supp_id] = {"type": "IB_CoilHeatingElectric"}
            components[wshp_id] = {
                "type": "IB_ZoneHVACWaterToAirHeatPump",
                "ctor_args": [fan_id, hc_id, cc_id, supp_id],
            }
            thermal_zones.append({"room_name": zname, "zone_equipments": [wshp_id]})
            demand_branches.append([cc_id])
            demand_branches.append([hc_id])

        plant_loops.append(
            {
                "name": "WSHP_CondenserLoop",
                "loop_type": "Condenser",
                "design_loop_exit_temperature": 25.0,
                "loop_design_temperature_difference": 5.6,
                "supply": ["wshp_pump"],
                "supply_branches": [["wshp_boiler"], ["wshp_tower"]],
                "bypass_pipes": True,
                "supply_setpoint_manager": "wshp_spm",
                "demand_branches": demand_branches,
            }
        )

    draft["components"] = components
    draft["thermal_zones"] = thermal_zones
    draft["air_loops"] = air_loops
    draft["plant_loops"] = plant_loops
    draft["vrf_systems"] = vrf_systems
    return draft


def create_ironbug_system(
    *,
    garden_root: str,
    identifier: str,
    display_name: str | None = None,
    specification: dict[str, Any] | str | None = None,
    template: str | None = None,
    editable: bool = False,
    room_names: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a Garden-managed official Ironbug IB_HVACSystem file."""
    if specification is not None and template is not None:
        raise ValueError("Pass either specification or template, not both.")

    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    clean_id = str(identifier).strip()
    if not clean_id:
        raise ValueError("identifier must not be empty.")

    extra_warnings: list[str] = []
    try:
        client = get_bridge_client()
        if specification is not None:
            spec_json = (
                specification
                if isinstance(specification, str)
                else json.dumps(specification, ensure_ascii=False)
            )
            if editable:
                parsed = client.call("reverse_parse", {"specification_json": spec_json})
                draft = dict(parsed["draft"])
                draft["imported_only"] = False
                if display_name is not None:
                    draft["display_name"] = display_name
                summary = dict(parsed["summary"])
                extra_warnings.extend(str(w) for w in (parsed.get("warnings") or []) if w)
            else:
                summary = client.call("inspect", {"specification_json": spec_json})
                draft = empty_draft(
                    display_name=summary.get("display_name") or display_name,
                    imported_only=True,
                )
        elif template is not None:
            draft = _build_template_draft(
                template,
                display_name=display_name or clean_id,
                room_names=room_names,
            )
            built = client.call("build", draft)
            spec_json = str(built["specification_json"])
            summary = dict(built["summary"])
        else:
            draft = empty_draft(display_name=display_name or clean_id)
            built = client.call("build", draft)
            spec_json = str(built["specification_json"])
            summary = dict(built["summary"])
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    target, spec_rel, draft_rel = save_ironbug_system(
        root,
        manifest,
        identifier=clean_id,
        specification_json=spec_json,
        draft=draft,
        overwrite=bool(overwrite),
    )
    imported_only = bool(draft.get("imported_only", False))
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=target,
        persisted_path=spec_rel,
        change_summary={
            "operation": "IB_Create_System",
            "identifier": clean_id,
            "draft_path": draft_rel,
            "imported_only": imported_only,
            "editable": not imported_only,
            "template": template,
        },
    )
    return {
        "target": target,
        "ironbug_model_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "identifier": clean_id,
            "path": spec_rel,
            "draft_path": draft_rel,
            "imported_only": imported_only,
            "editable": not imported_only,
            "template": template,
            **summary,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Created Ironbug HVAC system '{clean_id}' at {spec_rel}.",
            warnings=extra_warnings,
        ),
    }


def upsert_ironbug_components(
    *,
    garden_root: str,
    components: dict[str, dict[str, Any]] | list[dict[str, Any]] | None = None,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
    remove_ids: list[str] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Add, update, or remove typed Ironbug components in a system draft and compile via C#."""
    root = _garden_root(garden_root)
    manifest, target, _, _, _, draft = load_ironbug_system_files(
        root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    sys_id = str(target["id"])
    if draft.get("imported_only") and not replace:
        raise ValueError(
            f"Ironbug system '{sys_id}' was imported from an external official specification "
            "without an authoring draft. Updating components without replace=true would overwrite "
            "the imported specification; pass replace=true to discard it and author from a new draft."
        )
    incoming = _normalize_components_input(components)
    removed_ids = [str(x).strip() for x in (remove_ids or []) if str(x).strip()]
    if not incoming and not removed_ids and not replace:
        raise ValueError(
            "Provide at least one component in components or at least one id in remove_ids (or pass replace=true)."
        )

    next_draft = dict(draft)
    if replace:
        next_draft["imported_only"] = False
    existing_comps = {} if replace else dict(next_draft.get("components") or {})
    for rm_id in removed_ids:
        existing_comps.pop(rm_id, None)
    existing_comps.update(incoming)
    next_draft["components"] = existing_comps

    try:
        client = get_bridge_client()
        built = client.call("build", next_draft)
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)
    except IronbugBridgeError as exc:
        raise ValueError(f"Ironbug component build failed: {exc}") from exc

    saved_target, spec_rel, draft_rel = save_ironbug_system(
        root,
        manifest,
        identifier=sys_id,
        specification_json=str(built["specification_json"]),
        draft=next_draft,
        overwrite=True,
    )
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=saved_target,
        persisted_path=spec_rel,
        change_summary={
            "operation": "IB_Upsert_Components",
            "identifier": sys_id,
            "upserted_ids": sorted(incoming),
            "removed_ids": removed_ids,
            "component_count": len(existing_comps),
        },
    )
    if incoming and removed_ids:
        report_msg = (
            f"Updated {len(incoming)} and removed {len(removed_ids)} component(s) "
            f"in Ironbug system '{sys_id}'."
        )
    elif removed_ids:
        report_msg = f"Removed {len(removed_ids)} component(s) from Ironbug system '{sys_id}'."
    elif replace:
        report_msg = f"Replaced components in Ironbug system '{sys_id}' ({len(existing_comps)} total)."
    else:
        report_msg = f"Updated {len(incoming)} component(s) in Ironbug system '{sys_id}'."
    return {
        "target": saved_target,
        "ironbug_model_target": saved_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": saved_target,
            "component_count": len(existing_comps),
            "components": {k: v.get("type") for k, v in existing_comps.items()},
            "draft_path": draft_rel,
            **dict(built.get("summary") or {}),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=report_msg,
        ),
    }


def configure_ironbug_loops(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
    thermal_zones: list[dict[str, Any]] | None = None,
    air_loops: list[dict[str, Any]] | None = None,
    plant_loops: list[dict[str, Any]] | None = None,
    vrf_systems: list[dict[str, Any]] | None = None,
    energy_management_system: str | None = None,
    electric_load_center: str | None = None,
    display_name: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Configure thermal zones, air loops, plant loops, VRF topologies, EMS, and ELC via C#."""
    root = _garden_root(garden_root)
    manifest, target, _, _, _, draft = load_ironbug_system_files(
        root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    sys_id = str(target["id"])
    if draft.get("imported_only") and not replace:
        raise ValueError(
            f"Ironbug system '{sys_id}' was imported from an external official specification "
            "without an authoring draft. Configuring loops without replace=true would overwrite "
            "the imported specification; pass replace=true to discard it and author from a new draft."
        )

    next_draft = dict(draft)
    if replace:
        next_draft["imported_only"] = False
        next_draft["thermal_zones"] = []
        next_draft["air_loops"] = []
        next_draft["plant_loops"] = []
        next_draft["vrf_systems"] = []
        next_draft["energy_management_system"] = None
        next_draft["electric_load_center"] = None
    if display_name is not None:
        next_draft["display_name"] = display_name
    if thermal_zones is not None:
        next_draft["thermal_zones"] = list(thermal_zones)
    if air_loops is not None:
        next_draft["air_loops"] = list(air_loops)
    if plant_loops is not None:
        next_draft["plant_loops"] = list(plant_loops)
    if vrf_systems is not None:
        next_draft["vrf_systems"] = list(vrf_systems)
    if energy_management_system is not None:
        next_draft["energy_management_system"] = energy_management_system.strip() or None
    if electric_load_center is not None:
        next_draft["electric_load_center"] = electric_load_center.strip() or None

    try:
        client = get_bridge_client()
        built = client.call("build", next_draft)
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)
    except IronbugBridgeError as exc:
        raise ValueError(f"Ironbug loop assembly failed: {exc}") from exc

    saved_target, spec_rel, draft_rel = save_ironbug_system(
        root,
        manifest,
        identifier=sys_id,
        specification_json=str(built["specification_json"]),
        draft=next_draft,
        overwrite=True,
    )
    summary = dict(built.get("summary") or {})
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=saved_target,
        persisted_path=spec_rel,
        change_summary={
            "operation": "IB_Configure_Loops",
            "identifier": sys_id,
            **summary,
        },
    )
    return {
        "target": saved_target,
        "ironbug_model_target": saved_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": saved_target,
            "draft_path": draft_rel,
            "energy_management_system": next_draft.get("energy_management_system"),
            "electric_load_center": next_draft.get("electric_load_center"),
            **summary,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Configured Ironbug loops for '{sys_id}': "
                f"{summary.get('air_loop_count', 0)} air loop(s), "
                f"{summary.get('plant_loop_count', 0)} plant loop(s), "
                f"{summary.get('vrf_count', 0)} VRF system(s), "
                f"{len(summary.get('thermal_zones', []))} thermal zone(s)."
            ),
        ),
    }


def inspect_ironbug_system(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
    include_draft: bool = False,
) -> dict[str, Any]:
    """Inspect a Garden Ironbug HVAC system's loops, thermal zones, and component inventory."""
    root = _garden_root(garden_root)
    manifest, target, spec_path, draft_path, spec_dict, draft_dict = load_ironbug_system_files(
        root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    try:
        client = get_bridge_client()
        summary = client.call(
            "inspect",
            {"specification_json": json.dumps(spec_dict, ensure_ascii=False)},
        )
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    comps = draft_dict.get("components") or {}
    payload: dict[str, Any] = {
        "target": target,
        "ironbug_model_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "path": target["path"],
            "has_draft": draft_path.is_file(),
            "imported_only": bool(draft_dict.get("imported_only", False)),
            "component_count": len(comps),
            "components": {k: v.get("type") for k, v in comps.items()} if isinstance(comps, dict) else {},
            **summary,
        },
        "report": make_report(
            status="ok",
            message=f"Inspected Ironbug HVAC system '{target['id']}'.",
        ),
    }
    if include_draft:
        payload["draft"] = draft_dict
    return payload


def _evaluate_room_energy_preconditions(
    rooms_by_id: dict[str, Any],
    *,
    room_label: str,
    missing_code: str,
    room_identifiers: list[str] | None,
    system_zone_names: list[str],
    check_conditioned_warning: bool = False,
) -> dict[str, Any]:
    target_ids = room_identifiers or system_zone_names or list(rooms_by_id.keys())
    issues: list[dict[str, Any]] = []
    warnings: list[str] = []
    unconditioned_rooms: list[str] = []
    zone_set = set(system_zone_names)

    for rid in target_ids:
        room = rooms_by_id.get(rid)
        if room is None:
            issues.append(
                {
                    "code": missing_code,
                    "room_identifier": rid,
                    "message": f"{room_label} '{rid}' was not found in the model.",
                }
            )
            continue
        if system_zone_names and rid not in zone_set:
            issues.append(
                {
                    "code": "ironbug_thermal_zone_missing",
                    "room_identifier": rid,
                    "message": f"Ironbug system has no thermal_zones entry matching {room_label} '{rid}'.",
                }
            )
        ep = room.properties.energy
        if ep.program_type is None:
            issues.append(
                {
                    "code": "room_missing_program_type",
                    "room_identifier": rid,
                    "message": f"{room_label} '{rid}' has no ProgramType assigned.",
                }
            )
        if ep.setpoint is None:
            issues.append(
                {
                    "code": "room_missing_setpoint",
                    "room_identifier": rid,
                    "message": (
                        f"{room_label} '{rid}' has no thermostat Setpoint assigned "
                        "(assign a conditioned ProgramType or Setpoint)."
                    ),
                }
            )
        elif check_conditioned_warning and not getattr(ep, "is_conditioned", False):
            unconditioned_rooms.append(rid)
            warnings.append(
                f"{room_label} '{rid}' has no HVAC assigned yet (is_conditioned=False); "
                "pass conditioned_only=false if applying via a Dragonfly Story or Building host_target."
            )

    result: dict[str, Any] = {
        "checked_rooms": target_ids,
        "ready": len(issues) == 0,
        "issues": issues,
    }
    if check_conditioned_warning:
        result["warnings"] = warnings
        result["unconditioned_rooms"] = unconditioned_rooms
    return result


def _check_honeybee_room_preconditions(
    model: HoneybeeModel,
    *,
    room_identifiers: list[str] | None,
    system_zone_names: list[str],
) -> dict[str, Any]:
    return _evaluate_room_energy_preconditions(
        {room.identifier: room for room in model.rooms},
        room_label="Honeybee Room",
        missing_code="honeybee_room_missing",
        room_identifiers=room_identifiers,
        system_zone_names=system_zone_names,
    )


def _check_dragonfly_room_preconditions(
    df_model: Any,
    *,
    room_identifiers: list[str] | None = None,
    system_zone_names: list[str] | None = None,
) -> dict[str, Any]:
    return _evaluate_room_energy_preconditions(
        {room.identifier: room for room in df_model.room_2ds},
        room_label="Dragonfly Room2D",
        missing_code="dragonfly_room2d_missing",
        room_identifiers=room_identifiers,
        system_zone_names=list(system_zone_names or []),
        check_conditioned_warning=True,
    )


def _norm_key(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum()).lower()


def _strip_ref_id(value: str) -> str:
    cleaned = value.strip()
    return cleaned[1:].strip() if cleaned.startswith("@") else cleaned


def _extract_fan_ref_ids(
    spec: dict[str, Any],
    components: dict[str, Any],
) -> list[str]:
    fan_ids: list[str] = []
    wiring = spec.get("wiring")
    if isinstance(wiring, dict):
        for slot, target_val in wiring.items():
            if _norm_key(str(slot)) in {"fan", "setfan", "supplyairfan", "setsupplyairfan"}:
                items = target_val if isinstance(target_val, list) else [target_val]
                for item in items:
                    if isinstance(item, str) and item.strip():
                        fan_ids.append(_strip_ref_id(item))

    ctor_args = spec.get("ctor_args")
    if isinstance(ctor_args, dict):
        for arg_name, arg_val in ctor_args.items():
            if _norm_key(str(arg_name)) in {"fan", "supplyairfan"}:
                items = arg_val if isinstance(arg_val, list) else [arg_val]
                for item in items:
                    if isinstance(item, str) and item.strip():
                        fan_ids.append(_strip_ref_id(item))
            elif isinstance(arg_val, str) and arg_val.strip():
                candidate = _strip_ref_id(arg_val)
                comp = components.get(candidate)
                if isinstance(comp, dict) and str(comp.get("type") or "").strip().startswith("IB_Fan"):
                    fan_ids.append(candidate)
    elif isinstance(ctor_args, list):
        for arg_val in ctor_args:
            if isinstance(arg_val, str) and arg_val.strip():
                candidate = _strip_ref_id(arg_val)
                comp = components.get(candidate)
                if isinstance(comp, dict) and str(comp.get("type") or "").strip().startswith("IB_Fan"):
                    fan_ids.append(candidate)

    deduped: list[str] = []
    for fid in fan_ids:
        if fid not in deduped:
            deduped.append(fid)
    return deduped


def _check_draft_static_issues(draft_dict: dict[str, Any]) -> list[dict[str, Any]]:
    components = draft_dict.get("components")
    if not isinstance(components, dict):
        return []
    issues: list[dict[str, Any]] = []
    for comp_id, spec in components.items():
        if not isinstance(spec, dict):
            continue
        if str(spec.get("type") or "").strip() != "IB_ZoneHVACFourPipeFanCoil":
            continue
        fields = spec.get("fields")
        if not isinstance(fields, dict):
            continue
        is_cycling_fan = any(
            _norm_key(str(field_name)) in {"capacitycontrolmethod", "capacityctrl"}
            and _norm_key(str(field_val)) == "cyclingfan"
            for field_name, field_val in fields.items()
            if field_val is not None
        )
        if not is_cycling_fan:
            continue
        for fan_id in _extract_fan_ref_ids(spec, components):
            fan_spec = components.get(fan_id)
            if not isinstance(fan_spec, dict):
                continue
            fan_type = str(fan_spec.get("type") or "").strip()
            if fan_type and fan_type != "IB_FanOnOff":
                issues.append(
                    {
                        "code": "ironbug_fcu_cycling_fan_type_mismatch",
                        "component_id": str(comp_id),
                        "fan_component_id": fan_id,
                        "fan_type": fan_type,
                        "message": (
                            f"Component '{comp_id}' (IB_ZoneHVACFourPipeFanCoil) sets "
                            f"CapacityControlMethod='CyclingFan', but its wired fan '{fan_id}' "
                            f"has type '{fan_type}'. EnergyPlus requires IB_FanOnOff when "
                            "CapacityControlMethod='CyclingFan'."
                        ),
                    }
                )
    return issues


def validate_ironbug_system(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    model_family: str = "honeybee",
    room_identifiers: list[str] | None = None,
    run_forward_translator: bool | None = None,
) -> dict[str, Any]:
    """Validate an Ironbug system via official C# SaveHVAC, optional Honeybee OSM export, and ForwardTranslator."""
    family = str(model_family or "honeybee").strip().lower()
    if family not in ("honeybee", "dragonfly"):
        raise ValueError(f"Unsupported model_family: {model_family!r}. Use 'honeybee' or 'dragonfly'.")

    root = _garden_root(garden_root)
    manifest, target, _, _, spec_dict, draft_dict = load_ironbug_system_files(
        root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    static_issues = _check_draft_static_issues(draft_dict)

    hb_model: HoneybeeModel | None = None
    df_model: Any | None = None
    if family == "honeybee" and (model_target is not None or manifest.base_honeybee_model is not None):
        _, resolved_hb = resolve_honeybee_model_target(root, model_target)
        hb_model = load_honeybee_model(root, resolved_hb)
    elif family == "dragonfly" and (model_target is not None or manifest.base_dragonfly_model is not None):
        _, resolved_df = resolve_dragonfly_model_target(root, model_target)
        df_model = load_dragonfly_model(root, resolved_df)

    osm_issues: list[dict[str, Any]] = []
    osm_warnings: list[str] = []
    try:
        client = get_bridge_client()
        validate_payload: dict[str, Any] = {
            "specification_json": json.dumps(spec_dict, ensure_ascii=False),
            "room_names": list(room_identifiers or []),
        }
        if run_forward_translator is not None:
            validate_payload["run_forward_translator"] = bool(run_forward_translator)

        if hb_model is not None and hb_model.rooms:
            with tempfile.TemporaryDirectory(prefix="ironbug_val_") as tmpdir:
                try:
                    from honeybee_openstudio.writer import model_to_osm

                    hb_copy = hb_model.duplicate()
                    for rm in hb_copy.rooms:
                        if isinstance(rm.properties.energy.hvac, DetailedHVAC):
                            rm.properties.energy.hvac = None
                    osm_text = model_to_osm(hb_copy)
                    osm_path = Path(tmpdir) / "validate_model.osm"
                    osm_path.write_text(osm_text, encoding="utf-8")
                    validate_payload["osm_path"] = str(osm_path)
                    if run_forward_translator is None:
                        validate_payload["run_forward_translator"] = True
                except Exception as exc:
                    osm_issues.append(
                        {
                            "code": "honeybee_osm_translation_error",
                            "message": f"Failed to export Honeybee model to temporary OSM for Ironbug validation: {exc}",
                        }
                    )
                val = client.call("validate", validate_payload)
        else:
            val = client.call("validate", validate_payload)
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    os_valid = bool(val.get("valid"))
    os_errors = list(val.get("errors") or [])
    errors = [
        *os_errors,
        *(issue["message"] for issue in static_issues),
        *(issue["message"] for issue in osm_issues),
    ]
    warnings = [*osm_warnings, *list(val.get("warnings") or [])]
    system_summary = val.get("system_summary") or {}
    system_zones = list(
        system_summary["thermal_zones"]
        if "thermal_zones" in system_summary
        else (val.get("thermal_zones") or [])
    )

    room_check: dict[str, Any] | None = None
    if hb_model is not None:
        room_check = _check_honeybee_room_preconditions(
            hb_model,
            room_identifiers=room_identifiers,
            system_zone_names=system_zones,
        )
    elif df_model is not None:
        room_check = _check_dragonfly_room_preconditions(
            df_model,
            room_identifiers=room_identifiers,
            system_zone_names=system_zones,
        )
        warnings.extend(room_check.get("warnings") or [])

    blocking_issues: list[dict[str, Any]] = [
        {"code": "ironbug_openstudio_compile_error", "message": err}
        for err in os_errors
    ]
    blocking_issues.extend(static_issues)
    blocking_issues.extend(osm_issues)
    if room_check and not room_check["ready"]:
        blocking_issues.extend(room_check["issues"])

    valid = os_valid and not static_issues and not osm_issues
    ready = valid and not blocking_issues
    status = "ok" if ready else "invalid"
    forward_translator = val.get("forward_translator")
    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "target": target,
        "valid": valid,
        "ready": ready,
        "blocking_issue_count": len(blocking_issues),
        "warning_count": len(warnings),
        "openstudio_summary": val.get("openstudio_summary") or {},
    }
    if forward_translator is not None:
        summary_view["forward_translator"] = forward_translator

    payload: dict[str, Any] = {
        "valid": valid,
        "ready": ready,
        "target": target,
        "ironbug_model_target": target,
        "errors": errors,
        "warnings": warnings,
        "blocking_issues": blocking_issues,
        "thermal_zones": system_zones,
        "openstudio_summary": val.get("openstudio_summary") or {},
        "system_summary": val.get("system_summary") or {},
        "room_check": room_check,
        "summary_view": summary_view,
        "report": make_report(
            status=status,
            message=(
                f"Ironbug system '{target['id']}' compiled cleanly in OpenStudio."
                if ready
                else f"Ironbug system '{target['id']}' validation failed with {len(blocking_issues)} issue(s)."
            ),
            warnings=warnings,
        ),
    }
    if forward_translator is not None:
        payload["forward_translator"] = forward_translator
    return payload


def _select_honeybee_rooms(
    model: HoneybeeModel,
    model_target: dict[str, Any],
    *,
    room_targets: list[dict[str, Any]] | None,
    room_identifiers: list[str] | None,
    apply_to_all_rooms: bool,
    system_zones: list[str],
) -> list[HoneybeeRoom]:
    modes = sum([bool(room_targets), bool(room_identifiers), bool(apply_to_all_rooms)])
    if modes > 1:
        raise ValueError("Pass only one of room_targets, room_identifiers, or apply_to_all_rooms=true.")

    rooms_by_id = {r.identifier: r for r in model.rooms}
    if apply_to_all_rooms:
        selected = list(model.rooms)
    elif room_targets:
        selected = []
        for rt in room_targets:
            norm = normalize_honeybee_object_target(rt)
            if norm["object_type"] != "room" or norm["model_identifier"] != model_target["model_identifier"]:
                raise ValueError("room_targets must identify Honeybee Room objects in the target model.")
            obj = find_object(model, norm)
            if not isinstance(obj, HoneybeeRoom):
                raise ValueError("room_targets must identify Honeybee Room objects.")
            selected.append(obj)
    elif room_identifiers:
        missing = [rid for rid in room_identifiers if rid not in rooms_by_id]
        if missing:
            raise ValueError(f"Honeybee Room identifiers not found: {', '.join(missing)}")
        selected = [rooms_by_id[rid] for rid in room_identifiers]
    elif system_zones:
        missing = [rid for rid in system_zones if rid not in rooms_by_id]
        if missing:
            raise ValueError(
                f"Ironbug thermal_zones ({', '.join(missing)}) not found in Honeybee Model; "
                "pass explicit room_identifiers or align thermal_zones room_name values."
            )
        selected = [rooms_by_id[rid] for rid in system_zones]
    else:
        selected = list(model.rooms)

    if not selected:
        raise ValueError("Honeybee Model has no Rooms to assign HVAC to.")
    return selected


def apply_ironbug_to_model(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
    model_family: str = "honeybee",
    model_target: dict[str, Any] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    room_identifiers: list[str] | None = None,
    apply_to_all_rooms: bool = False,
    host_target: dict[str, Any] | None = None,
    conditioned_only: bool = True,
    detailed_hvac_identifier: str | None = None,
) -> dict[str, Any]:
    """Attach a validated official Ironbug IB_HVACSystem as DetailedHVAC on a Honeybee or Dragonfly model."""
    root = _garden_root(garden_root)
    manifest, ib_target, _, _, spec_dict, _ = load_ironbug_system_files(
        root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    sys_id = str(ib_target["id"])
    hvac_id = detailed_hvac_identifier or f"{sys_id}_detailed_hvac"

    try:
        client = get_bridge_client()
        val = client.call(
            "validate",
            {
                "specification_json": json.dumps(spec_dict, ensure_ascii=False),
                "room_names": list(room_identifiers or []),
            },
        )
    except IronbugRuntimeUnavailable as exc:
        return _runtime_blocked_response(exc)

    if not val.get("valid"):
        errors = list(val.get("errors") or [])
        raise ValueError(
            f"Ironbug system '{sys_id}' failed OpenStudio compilation before apply: "
            + "; ".join(errors)
        )

    system_summary = val.get("system_summary") or {}
    system_zones = list(
        system_summary["thermal_zones"]
        if "thermal_zones" in system_summary
        else (val.get("thermal_zones") or [])
    )
    detailed_hvac = DetailedHVAC(hvac_id, spec_dict)

    family = str(model_family or "honeybee").strip().lower()
    if family == "dragonfly":
        if host_target is not None:
            manifest, resolved_df = resolve_dragonfly_model_target(root, model_target)
            df_model = load_dragonfly_model(root, resolved_df)
            norm_host = normalize_dragonfly_object_target(host_target)
            htype = norm_host["object_type"]
            oid = norm_host["object_identifier"]
            if htype == "room2d":
                host = df_model.room_2ds_by_identifier([oid])[0]
                host.properties.energy.hvac = detailed_hvac
                affected = [host.identifier]
            elif htype == "story":
                host = df_model.stories_by_identifier([oid])[0]
                host.properties.energy.set_all_room_2d_hvac(detailed_hvac, conditioned_only=conditioned_only)
                affected = [r.identifier for r in host.room_2ds if getattr(r.properties.energy.hvac, "identifier", None) == hvac_id]
            elif htype == "building":
                host = df_model.buildings_by_identifier([oid])[0]
                host.properties.energy.set_all_room_2d_hvac(detailed_hvac, conditioned_only=conditioned_only)
                affected = [r.identifier for r in host.unique_room_2ds if getattr(r.properties.energy.hvac, "identifier", None) == hvac_id]
            else:
                raise ValueError(f"Unsupported Dragonfly host_target type: {htype}")

            updated_target, persisted_path = save_dragonfly_model(
                root,
                manifest,
                df_model,
                name=str(resolved_df["model_identifier"]),
                included_prop=["energy", "radiance", "uwg"],
                set_base=manifest.base_dragonfly_model == resolved_df,
            )
            receipt = make_persistence_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                model_target=updated_target,
                persisted_path=persisted_path,
                change_summary={
                    "operation": "IB_Apply_To_Model",
                    "model_family": "dragonfly",
                    "ironbug_model_target": ib_target,
                    "detailed_hvac_identifier": hvac_id,
                    "affected_room2ds": affected,
                },
            )
            return {
                "target": updated_target,
                "updated_model_target": updated_target,
                "updated_model_targets": [updated_target],
                "dragonfly_model_target": updated_target,
                "ironbug_model_target": ib_target,
                "detailed_hvac_identifier": hvac_id,
                "summary_view": {
                    "garden_target": manifest.target(),
                    "updated_model_target": updated_target,
                    "updated_model_targets": [updated_target],
                    "detailed_hvac_identifier": hvac_id,
                    "affected_room2d_count": len(affected),
                    "affected_room2d_identifiers": affected,
                    "openstudio_summary": val.get("openstudio_summary") or {},
                },
                "persistence_receipt": receipt,
                "report": make_report(
                    status="ok",
                    message=f"Applied Ironbug DetailedHVAC '{hvac_id}' to {len(affected)} Dragonfly Room2D(s).",
                ),
            }

        # Convert Dragonfly -> Honeybee and select all matching Honeybee models
        modes = sum([bool(room_targets), bool(room_identifiers), bool(apply_to_all_rooms)])
        if modes > 1:
            raise ValueError("Pass only one of room_targets, room_identifiers, or apply_to_all_rooms=true.")

        conversion = dragonfly_model_to_honeybee(garden_root=str(root), model_target=model_target, set_base=False)
        hb_targets = conversion.get("honeybee_model_targets") or conversion.get("model_targets") or []
        if not hb_targets:
            raise ValueError("Dragonfly conversion produced zero Honeybee models.")

        converted: list[tuple[dict[str, Any], HoneybeeModel]] = []
        for hb_t in hb_targets:
            _, resolved_hb = resolve_honeybee_model_target(root, hb_t)
            converted.append((resolved_hb, load_honeybee_model(root, resolved_hb)))

        selected_work: list[
            tuple[
                dict[str, Any],
                HoneybeeModel,
                list[dict[str, Any]] | None,
                list[str] | None,
                bool,
            ]
        ] = []
        if room_targets:
            grouped: dict[str, list[dict[str, Any]]] = {}
            for rt in room_targets:
                norm = normalize_honeybee_object_target(rt)
                if norm["object_type"] != "room":
                    raise ValueError("room_targets must identify Honeybee Room objects.")
                grouped.setdefault(str(norm["model_identifier"]), []).append(rt)
            converted_ids = {str(resolved["model_identifier"]) for resolved, _ in converted}
            unknown_models = [mid for mid in grouped if mid not in converted_ids]
            if unknown_models:
                raise ValueError(
                    "room_targets reference Honeybee model(s) not produced by Dragonfly conversion: "
                    + ", ".join(unknown_models)
                )
            for resolved, hb_model in converted:
                mid = str(resolved["model_identifier"])
                if mid in grouped:
                    selected_work.append((resolved, hb_model, grouped[mid], None, False))
        elif room_identifiers:
            requested_ids = list(room_identifiers)
            found_ids: set[str] = set()
            for resolved, hb_model in converted:
                model_room_ids = {r.identifier for r in hb_model.rooms}
                matched_ids = [rid for rid in requested_ids if rid in model_room_ids]
                if matched_ids:
                    found_ids.update(matched_ids)
                    selected_work.append((resolved, hb_model, None, matched_ids, False))
            missing = [rid for rid in requested_ids if rid not in found_ids]
            if missing:
                raise ValueError(
                    "Honeybee Room identifiers not found in converted Dragonfly model(s): "
                    + ", ".join(missing)
                )
        elif apply_to_all_rooms or not system_zones:
            for resolved, hb_model in converted:
                selected_work.append((resolved, hb_model, None, None, bool(apply_to_all_rooms)))
        else:
            found_zones: set[str] = set()
            for resolved, hb_model in converted:
                model_room_ids = {r.identifier for r in hb_model.rooms}
                matched_zones = [z for z in system_zones if z in model_room_ids]
                if matched_zones:
                    found_zones.update(matched_zones)
                    selected_work.append((resolved, hb_model, None, matched_zones, False))
            missing = [z for z in system_zones if z not in found_zones]
            if missing:
                raise ValueError(
                    f"Ironbug thermal_zones ({', '.join(missing)}) not found in converted Dragonfly "
                    "Honeybee model(s); pass explicit room_identifiers or align thermal_zones room_name values."
                )
            if not selected_work:
                raise ValueError("No converted Honeybee model rooms matched the Ironbug system's thermal_zones.")

    elif family == "honeybee":
        manifest, resolved_hb = resolve_honeybee_model_target(root, model_target)
        hb_model = load_honeybee_model(root, resolved_hb)
        selected_work = [(resolved_hb, hb_model, room_targets, room_identifiers, apply_to_all_rooms)]
    else:
        raise ValueError(f"Unsupported model_family: {model_family!r}. Use 'honeybee' or 'dragonfly'.")

    prepared: list[tuple[dict[str, Any], HoneybeeModel, list[str]]] = []
    raw_hb_checks: list[tuple[dict[str, Any], list[Any]]] = []
    all_selected_ids: list[str] = []
    for resolved_hb, hb_model, m_room_targets, m_room_ids, m_apply_all in selected_work:
        selected_rooms = _select_honeybee_rooms(
            hb_model,
            resolved_hb,
            room_targets=m_room_targets,
            room_identifiers=m_room_ids,
            apply_to_all_rooms=m_apply_all,
            system_zones=system_zones,
        )
        selected_ids = [r.identifier for r in selected_rooms]
        precheck = _check_honeybee_room_preconditions(
            hb_model,
            room_identifiers=selected_ids,
            system_zone_names=system_zones,
        )
        if not precheck["ready"]:
            issues_msg = "; ".join(i["message"] for i in precheck["issues"])
            raise ValueError(
                f"Honeybee Rooms in '{resolved_hb['model_identifier']}' are not ready for Ironbug DetailedHVAC: "
                f"{issues_msg}"
            )

        for room in selected_rooms:
            room.properties.energy.hvac = detailed_hvac

        hb_issues = hb_model.properties.energy.check_detailed_hvac_rooms(
            raise_exception=False,
            detailed=True,
        )
        prepared.append((resolved_hb, hb_model, selected_ids))
        raw_hb_checks.append((resolved_hb, hb_issues))
        all_selected_ids.extend(selected_ids)

    multi_model = len(prepared) > 1
    all_selected_set = set(all_selected_ids)
    all_zones_covered = bool(system_zones) and all(z in all_selected_set for z in system_zones)
    blocking_hb: list[dict[str, Any]] = []
    extra_warnings: list[str] = []
    for resolved_hb, hb_issues in raw_hb_checks:
        for iss in hb_issues:
            if not isinstance(iss, dict):
                continue
            if multi_model and iss.get("code") == "020012" and all_zones_covered:
                extra_warnings.append(
                    f"{resolved_hb['model_identifier']}: {iss.get('message') or iss.get('code')} "
                    "(zones covered across split Dragonfly Honeybee models)"
                )
                continue
            blocking_hb.append(iss)
    if blocking_hb:
        raise ValueError(
            "Honeybee DetailedHVAC room check failed: "
            + "; ".join(str(i.get("message") or i.get("code")) for i in blocking_hb)
        )

    updated_targets: list[dict[str, Any]] = []
    persisted_paths: list[str] = []
    for resolved_hb, hb_model, _ in prepared:
        manifest = GardenManifest.read(root)
        updated_target, persisted_path = save_honeybee_model(
            root,
            manifest,
            hb_model,
            name=str(resolved_hb["model_identifier"]),
            set_base=manifest.base_honeybee_model == resolved_hb,
        )
        updated_targets.append(updated_target)
        persisted_paths.append(persisted_path)

    primary_target = updated_targets[0]
    primary_path = persisted_paths[0]
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=primary_target,
        persisted_path=primary_path,
        change_summary={
            "operation": "IB_Apply_To_Model",
            "model_family": family,
            "ironbug_model_target": ib_target,
            "detailed_hvac_identifier": hvac_id,
            "updated_model_targets": updated_targets,
            "persisted_paths": persisted_paths,
            "room_identifiers": all_selected_ids,
        },
    )
    return {
        "target": primary_target,
        "updated_model_target": primary_target,
        "updated_model_targets": updated_targets,
        "honeybee_model_target": primary_target,
        "ironbug_model_target": ib_target,
        "detailed_hvac_identifier": hvac_id,
        "summary_view": {
            "garden_target": manifest.target(),
            "updated_model_target": primary_target,
            "updated_model_targets": updated_targets,
            "updated_model_count": len(updated_targets),
            "detailed_hvac_identifier": hvac_id,
            "selected_room_count": len(all_selected_ids),
            "room_identifiers": all_selected_ids,
            "openstudio_summary": val.get("openstudio_summary") or {},
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Applied Ironbug DetailedHVAC '{hvac_id}' across {len(updated_targets)} "
                f"Honeybee model(s) to Room(s): {', '.join(all_selected_ids)}."
                if len(updated_targets) > 1
                else f"Applied Ironbug DetailedHVAC '{hvac_id}' to Honeybee Room(s): {', '.join(all_selected_ids)}."
            ),
            warnings=[*list(val.get("warnings") or []), *extra_warnings],
        ),
    }
