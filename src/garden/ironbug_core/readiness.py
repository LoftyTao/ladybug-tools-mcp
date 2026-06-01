"""Ironbug DetailedHVAC and EnergyPlus readiness validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from garden.ironbug_core.assembly import _component_library
from garden.ironbug_core.model_io import load_ironbug_model
from ladybug_tools_mcp.contracts.report import make_report

ROOM_SERVING_PREFIXES = ("IB_AirTerminal", "IB_ZoneHVAC")
ROOM_SERVING_CLASSES = {
    "IB_AirLoopHVACUnitarySystem",
    "IB_FanZoneExhaust",
    "IB_WaterHeaterHeatPump",
    "IB_WaterHeaterMixed",
    "IB_ZoneEquipmentGroup",
}
PUMP_SOURCE_CLASSES = {"IB_PumpConstantSpeed", "IB_PumpVariableSpeed"}
FAN_SOURCE_PREFIX = "IB_Fan"
PUBLIC_REPAIR_TOOLS = {
    "connect_ironbug_water_coil_to_plant_loop": "detailed_hvac_plant_loop_chilled_water",
    "create_ironbug_air_loop_hvac": "detailed_hvac_air_loop_hvac",
    "create_ironbug_air_terminal_single_duct_constant_volume_no_reheat": (
        "detailed_hvac_air_terminal_single_duct_constant_volume_no_reheat"
    ),
    "create_ironbug_chilled_water_loop": "detailed_hvac_plant_loop_chilled_water",
    "create_ironbug_coil_heating_water": "detailed_hvac_coil_heating_water",
    "create_ironbug_controller_outdoor_air": "detailed_hvac_controller_outdoor_air",
    "create_ironbug_hot_water_loop": "detailed_hvac_plant_loop_hot_water",
    "create_ironbug_pump_constant_speed": "detailed_hvac_pump_constant_speed",
    "create_ironbug_thermal_zone": "detailed_hvac_thermal_zone",
    "create_ironbug_zone_hvac_four_pipe_fan_coil": (
        "detailed_hvac_zone_equipment_four_pipe_fan_coil"
    ),
    "set_ironbug_controller_mechanical_ventilation": (
        "detailed_hvac_controller_mechanical_ventilation"
    ),
    "set_ironbug_thermal_zone_air_terminal": (
        "detailed_hvac_air_terminal_single_duct_constant_volume_no_reheat"
    ),
}


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _source_class(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("type") or value.get("source_class") or "")
    return str(getattr(value, "SOURCE_CLASS", value.__class__.__name__))


def _identifier(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("identifier") or value.get("Name") or "")
    return str(getattr(value, "identifier", "") or getattr(value, "Name", "") or "")


def _object_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    return {}


def _comparable_payload(value: Any) -> dict[str, Any]:
    payload = dict(_object_payload(value))
    payload.pop("user_data", None)
    if _source_class(payload) == "IB_ThermalZone":
        payload.pop("AirTerminal", None)
        payload.pop("ZoneEquipments", None)
    return payload


def _children(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.get("Children") or [])
    return list(getattr(value, "Children", []) or [])


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        if name in value:
            return value[name]
        return (value.get("CustomAttributes") or {}).get(name, default)
    if hasattr(value, name):
        return getattr(value, name)
    return (getattr(value, "CustomAttributes", {}) or {}).get(name, default)


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _user_data(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        user_data = value.get("user_data")
    else:
        user_data = getattr(value, "user_data", None)
    return user_data if isinstance(user_data, dict) else {}


def _iter_nested(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_nested(child)
        return
    if isinstance(value, dict):
        for item in value.values():
            if isinstance(item, dict):
                yield from _iter_nested(item)
            elif isinstance(item, list):
                for child in item:
                    if isinstance(child, (dict, object)):
                        yield from _iter_nested(child)
        return
    for attr in (
        "Children",
        "HVACSystem",
        "AirLoops",
        "PlantLoops",
        "VariableRefrigerantFlows",
        "SupplyComponents",
        "DemandComponents",
        "OAStreamObjs",
        "ReliefStreamObjs",
        "AirTerminal",
        "ZoneEquipments",
        "Branches",
    ):
        item = getattr(value, attr, None)
        if isinstance(item, list):
            for child in item:
                yield from _iter_nested(child)
        elif item is not None:
            yield from _iter_nested(item)


def _iter_model_objects(model: Any) -> Iterable[Any]:
    yield from _iter_nested(model)
    try:
        for record in _component_library(model).values():
            data = record.get("data")
            if data is not None:
                yield from _iter_nested(data)
    except ValueError:
        return


def _iter_active_model_objects(model: Any) -> Iterable[Any]:
    """Iterate objects reachable from the active exported model graph."""

    yield from _iter_nested(model)


def _iter_component_library_objects(library: dict[str, Any]) -> Iterable[Any]:
    """Iterate component-library objects, including embedded child copies."""

    for record in library.values():
        if not isinstance(record, dict):
            continue
        data = record.get("data")
        if data is not None:
            yield from _iter_nested(data)


def _issue(
    *,
    severity: str,
    code: str,
    source: Any,
    message: str,
    repair_tool: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "source_class": _source_class(source),
        "identifier": _identifier(source),
        "message": message,
        "repair_tool": repair_tool,
    }


def _outdoor_air_controller_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ControllerOutdoorAir":
            continue
        has_mechanical = any(
            _source_class(child) == "IB_ControllerMechanicalVentilation"
            for child in _children(obj)
        )
        if not has_mechanical:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_controller_mechanical_ventilation_missing",
                    source=obj,
                    message=(
                        "IB_ControllerOutdoorAir requires an "
                        "IB_ControllerMechanicalVentilation child before DetailedHVAC "
                        "translation."
                    ),
                    repair_tool="set_ironbug_controller_mechanical_ventilation",
                )
            )
    return issues


def _outdoor_air_system_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    for obj in _iter_active_model_objects(model):
        if _source_class(obj) != "IB_OutdoorAirSystem":
            continue
        has_controller = any(
            _source_class(child) == "IB_ControllerOutdoorAir"
            for child in _children(obj)
        )
        if not has_controller:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_outdoor_air_system_controller_missing",
                    source=obj,
                    message=(
                        "IB_OutdoorAirSystem used for DOAS or outdoor-air "
                        "supply requires an IB_ControllerOutdoorAir child before "
                        "EnergyPlus execution."
                    ),
                    repair_tool="create_ironbug_controller_outdoor_air",
                )
            )
    return issues


def _water_coil_autosize_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    for obj in _iter_model_objects(model):
        if _source_class(obj) not in {"IB_CoilHeatingWater", "IB_CoilCoolingWater"}:
            continue
        flow_rate = _field(obj, "MaximumWaterFlowRate")
        if isinstance(flow_rate, str) and flow_rate.strip().lower() == "autosize":
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_water_coil_maximum_water_flow_rate_autosize",
                    source=obj,
                    message=(
                        "Ironbug/OpenStudio does not accept Autosize for "
                        "MaximumWaterFlowRate on water coils in this path."
                    ),
                    repair_tool="create_ironbug_coil_heating_water",
                )
            )
    return issues


def _heating_water_coil_ua_sizing_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_CoilHeatingWater":
            continue
        method = str(_field(obj, "PerformanceInputMethod", "") or "").strip()
        if method != "UFactorTimesAreaAndDesignWaterFlowRate":
            continue
        ua_value = _field(obj, "UFactorTimesAreaValue")
        flow_rate = _field(obj, "MaximumWaterFlowRate")
        if _is_numeric(ua_value) and _is_numeric(flow_rate):
            continue
        issues.append(
            _issue(
                severity="error",
                code="ironbug_heating_water_coil_ua_or_flow_not_numeric",
                source=obj,
                message=(
                    "IB_CoilHeatingWater with "
                    "PerformanceInputMethod=UFactorTimesAreaAndDesignWaterFlowRate "
                    "requires numeric u_factor_times_area_value and numeric "
                    "maximum_water_flow_rate before EnergyPlus execution."
                ),
                repair_tool="create_ironbug_coil_heating_water",
            )
        )
    return issues


def _stale_embedded_component_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    try:
        library = _component_library(model)
    except ValueError:
        return issues
    library_by_identifier = {
        identifier: record
        for identifier, record in library.items()
        if isinstance(record, dict) and isinstance(record.get("data"), dict)
    }
    for obj in (
        *_iter_active_model_objects(model),
        *_iter_component_library_objects(library_by_identifier),
    ):
        identifier = _identifier(obj)
        if not identifier or identifier not in library_by_identifier:
            continue
        record = library_by_identifier[identifier]
        if str(record.get("source_class") or "") != _source_class(obj):
            continue
        if _comparable_payload(obj) == _comparable_payload(record["data"]):
            continue
        issues.append(
            _issue(
                severity="error",
                code="ironbug_embedded_component_stale_after_overwrite",
                source=obj,
                message=(
                    "An active Ironbug HVAC graph contains an embedded component "
                    "whose identifier matches a newer component library record but "
                    "whose fields differ; rebuild the owning Ironbug HVAC graph "
                    "or FCU/terminal/PlantLoop after overwriting component inputs."
                ),
                repair_tool="create_ironbug_zone_hvac_four_pipe_fan_coil",
            )
        )
    return issues


def _plant_connected_coil_ids(model: Any) -> set[str]:
    connected = set()
    hvac_system = getattr(model, "HVACSystem", None)
    for plant_loop in getattr(hvac_system, "PlantLoops", []) or []:
        for attr in ("SupplyComponents", "DemandComponents"):
            for component in getattr(plant_loop, attr, []) or []:
                for nested in _iter_nested(component):
                    if _source_class(nested) in {"IB_CoilHeatingWater", "IB_CoilCoolingWater"}:
                        connected.add(_identifier(nested))
    for obj in _iter_model_objects(model):
        if _source_class(obj) in {"IB_CoilHeatingWater", "IB_CoilCoolingWater"}:
            if _user_data(obj).get("connected_plant_loop_identifier"):
                connected.add(_identifier(obj))
    return connected


def _fan_coil_ids_to_validate(model: Any) -> set[str]:
    active_ids = {
        _identifier(obj)
        for obj in _iter_active_model_objects(model)
        if _source_class(obj) == "IB_ZoneHVACFourPipeFanCoil" and _identifier(obj)
    }
    if active_ids:
        return active_ids
    attached_ids: set[str] = set()
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ThermalZone":
            continue
        for equipment in _field(obj, "ZoneEquipments", []) or []:
            if _source_class(equipment) == "IB_ZoneHVACFourPipeFanCoil":
                identifier = _identifier(equipment)
                if identifier:
                    attached_ids.add(identifier)
    return attached_ids


def _fan_coil_connection_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    connected_ids = _plant_connected_coil_ids(model)
    fan_coil_ids = _fan_coil_ids_to_validate(model)
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ZoneHVACFourPipeFanCoil":
            continue
        if fan_coil_ids and _identifier(obj) not in fan_coil_ids:
            continue
        for child in _children(obj):
            if _source_class(child) not in {"IB_CoilHeatingWater", "IB_CoilCoolingWater"}:
                continue
            if _identifier(child) not in connected_ids:
                issues.append(
                    _issue(
                        severity="error",
                        code="ironbug_fan_coil_water_coil_unconnected",
                        source=child,
                        message=(
                            "Water coils used by IB_ZoneHVACFourPipeFanCoil must be "
                            "connected to a hot-water or chilled-water plant loop."
                        ),
                        repair_tool="connect_ironbug_water_coil_to_plant_loop",
                    )
                )
    return issues


def _thermal_zone_binding_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    air_loop_demand_zone_ids = _air_loop_demand_zone_ids(model)
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ThermalZone":
            continue
        air_terminal = _field(obj, "AirTerminal")
        zone_equipment = _field(obj, "ZoneEquipments", []) or []
        zone_id = _identifier(obj)
        if air_terminal is None and not zone_equipment:
            issues.append(
                _issue(
                    severity="warning",
                    code="ironbug_thermal_zone_has_no_air_terminal_or_equipment",
                    source=obj,
                    message=(
                        "IB_ThermalZone has no AirTerminal and no ZoneEquipments, "
                        "so it is unlikely to participate in a DetailedHVAC graph."
                    ),
                    repair_tool="set_ironbug_thermal_zone_air_terminal",
                )
            )
        if air_terminal is None and zone_id in air_loop_demand_zone_ids:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_air_loop_zone_missing_air_terminal",
                    source=obj,
                    message=(
                        "IB_ThermalZone appears in an IB_AirLoopHVAC demand "
                        "branch but has no AirTerminal. For DOAS, CAV, VAV, "
                        "and other room-serving air loops, bind a real "
                        "IB_AirTerminal such as "
                        "IB_AirTerminalSingleDuctConstantVolumeNoReheat to the "
                        "zone before EnergyPlus execution; zone equipment "
                        "alone does not create air-side nodes for water coils."
                    ),
                    repair_tool=(
                        "create_ironbug_air_terminal_single_duct_constant_volume_no_reheat"
                    ),
                )
            )
        if air_terminal is not None and zone_id not in air_loop_demand_zone_ids:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_air_terminal_zone_not_in_air_loop_demand",
                    source=obj,
                    message=(
                        "IB_ThermalZone has an AirTerminal, but the zone is not "
                        "present in any IB_AirLoopHVAC demand branch. Air terminals "
                        "need an air loop demand path so EnergyPlus receives air-side "
                        "nodes for terminal coils."
                    ),
                    repair_tool="create_ironbug_air_loop_hvac",
                )
            )
    return issues


def _fan_coil_child_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    fan_coil_ids = _fan_coil_ids_to_validate(model)
    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ZoneHVACFourPipeFanCoil":
            continue
        if fan_coil_ids and _identifier(obj) not in fan_coil_ids:
            continue
        child_classes = {_source_class(child) for child in _children(obj)}
        if "IB_CoilHeatingWater" not in child_classes:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_fan_coil_missing_heating_coil",
                    source=obj,
                    message=(
                        "IB_ZoneHVACFourPipeFanCoil requires an "
                        "IB_CoilHeatingWater child before EnergyPlus execution."
                    ),
                    repair_tool="create_ironbug_zone_hvac_four_pipe_fan_coil",
                )
            )
        if "IB_CoilCoolingWater" not in child_classes:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_fan_coil_missing_cooling_coil",
                    source=obj,
                    message=(
                        "IB_ZoneHVACFourPipeFanCoil requires an "
                        "IB_CoilCoolingWater child before EnergyPlus execution."
                    ),
                    repair_tool="create_ironbug_zone_hvac_four_pipe_fan_coil",
                )
            )
        if not any(source_class.startswith(FAN_SOURCE_PREFIX) for source_class in child_classes):
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_fan_coil_missing_fan",
                    source=obj,
                    message=(
                        "IB_ZoneHVACFourPipeFanCoil requires an IB_Fan child "
                        "before EnergyPlus execution."
                    ),
                    repair_tool="create_ironbug_zone_hvac_four_pipe_fan_coil",
                )
            )
    return issues


def _air_loop_demand_zone_ids(model: Any) -> set[str]:
    zone_ids: set[str] = set()
    hvac_system = getattr(model, "HVACSystem", None)
    for air_loop in getattr(hvac_system, "AirLoops", []) or []:
        if _source_class(air_loop) != "IB_AirLoopHVAC":
            continue
        for component in getattr(air_loop, "DemandComponents", []) or []:
            for nested in _iter_nested(component):
                if _source_class(nested) == "IB_ThermalZone":
                    zone_id = _identifier(nested)
                    if zone_id:
                        zone_ids.add(zone_id)
    return zone_ids


def _has_room_linked_thermal_zone(model: Any) -> bool:
    """Return True when a ThermalZone serves an air terminal or zone equipment."""

    for obj in _iter_model_objects(model):
        if _source_class(obj) != "IB_ThermalZone":
            continue
        air_terminal = _field(obj, "AirTerminal")
        zone_equipment = _field(obj, "ZoneEquipments", []) or []
        if air_terminal is not None or zone_equipment:
            return True
    return False


def _has_explicit_thermal_zone(model: Any) -> bool:
    for obj in _iter_model_objects(model):
        if _source_class(obj) == "IB_ThermalZone":
            return True
    return False


def _is_room_serving_source_class(source_class: str) -> bool:
    return (
        source_class in ROOM_SERVING_CLASSES
        or source_class.startswith(ROOM_SERVING_PREFIXES)
    )


def _room_serving_without_thermal_zone_issues(model: Any) -> list[dict[str, Any]]:
    if _has_room_linked_thermal_zone(model):
        return []
    for obj in _iter_model_objects(model):
        if _is_room_serving_source_class(_source_class(obj)):
            return [
                _issue(
                    severity="error",
                    code="ironbug_room_serving_component_without_thermal_zone",
                    source=obj,
                    message=(
                        "Room-serving Ironbug HVAC components require explicit "
                        "room-linked IB_ThermalZone objects before DetailedHVAC "
                        "application or EnergyPlus acceptance."
                    ),
                    repair_tool="create_ironbug_thermal_zone",
                )
            ]
    return []


def _electric_load_center_missing_thermal_zone_issues(
    model: Any,
) -> list[dict[str, Any]]:
    electric_load_center = getattr(model, "ElectricLoadCenter", None)
    if electric_load_center is None or _has_explicit_thermal_zone(model):
        return []
    return [
        _issue(
            severity="error",
            code="ironbug_electric_load_center_missing_thermal_zone",
            source=electric_load_center,
            message=(
                "Ironbug ElectricLoadCenter EnergyPlus paths require an "
                "explicit IB_ThermalZone whose Name or identifier matches each "
                "selected Honeybee Room before DetailedHVAC application."
            ),
            repair_tool="create_ironbug_thermal_zone",
        )
    ]


def _load_profile_plant_issues(model: Any) -> list[dict[str, Any]]:
    """Diagnose plant-only/load-profile demand acceptance risk.

    Triggers ironbug_matrix_demand_not_room_linked when an IB_LoadProfilePlant
    appears in a model that lacks any room-linked IB_ThermalZone serving an
    air terminal or zone equipment path.
    """
    issues = []
    has_load_profile_plant = False
    for obj in _iter_model_objects(model):
        if _source_class(obj) == "IB_LoadProfilePlant":
            has_load_profile_plant = True
            break

    if not has_load_profile_plant:
        return issues

    if not _has_room_linked_thermal_zone(model):
        issues.append(
            _issue(
                severity="error",
                code="ironbug_matrix_demand_not_room_linked",
                source=model,
                message=(
                    "Accepted HVAC matrix systems must serve room-linked terminals, "
                    "coils, air terminals, or zone equipment associated with "
                    "IB_ThermalZone and Honeybee/Dragonfly rooms."
                ),
                repair_tool="create_ironbug_thermal_zone",
            )
        )
    return issues


def _plant_loop_missing_pump_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    hvac_system = getattr(model, "HVACSystem", None)
    for plant_loop in getattr(hvac_system, "PlantLoops", []) or []:
        supply_components = list(getattr(plant_loop, "SupplyComponents", []) or [])
        demand_components = list(getattr(plant_loop, "DemandComponents", []) or [])
        if not supply_components and not demand_components:
            continue
        has_pump = any(
            _source_class(nested) in PUMP_SOURCE_CLASSES
            for component in supply_components
            for nested in _iter_nested(component)
        )
        if has_pump:
            continue
        issues.append(
            _issue(
                severity="error",
                code="ironbug_plant_loop_missing_pump",
                source=plant_loop,
                message=(
                    "IB_PlantLoop supply components require an "
                    "IB_PumpConstantSpeed or IB_PumpVariableSpeed before "
                    "EnergyPlus execution."
                ),
                repair_tool="create_ironbug_pump_constant_speed",
            )
        )
    return issues


def _air_loop_component_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    hvac_system = getattr(model, "HVACSystem", None)
    for air_loop in getattr(hvac_system, "AirLoops", []) or []:
        if _source_class(air_loop) != "IB_AirLoopHVAC":
            continue
        supply_components = list(getattr(air_loop, "SupplyComponents", []) or [])
        demand_components = list(getattr(air_loop, "DemandComponents", []) or [])
        if not supply_components and demand_components:
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_air_loop_missing_supply_components",
                    source=air_loop,
                    message=(
                        "IB_AirLoopHVAC with demand branches requires supply "
                        "components such as an outdoor air system and fan before "
                        "EnergyPlus execution."
                    ),
                    repair_tool="create_ironbug_air_loop_hvac",
                )
            )
            continue
        if supply_components and demand_components:
            has_fan = any(
                _source_class(nested).startswith(FAN_SOURCE_PREFIX)
                for component in supply_components
                for nested in _iter_nested(component)
            )
            if not has_fan:
                issues.append(
                    _issue(
                        severity="error",
                        code="ironbug_air_loop_missing_supply_fan",
                        source=air_loop,
                        message=(
                            "IB_AirLoopHVAC supply components require an IB_Fan "
                            "object before EnergyPlus execution."
                        ),
                        repair_tool="create_ironbug_air_loop_hvac",
                    )
                )
    return issues


def _plant_loop_component_issues(model: Any) -> list[dict[str, Any]]:
    issues = []
    hvac_system = getattr(model, "HVACSystem", None)
    for plant_loop in getattr(hvac_system, "PlantLoops", []) or []:
        if _source_class(plant_loop) != "IB_PlantLoop":
            continue
        supply_components = list(getattr(plant_loop, "SupplyComponents", []) or [])
        demand_components = list(getattr(plant_loop, "DemandComponents", []) or [])
        if supply_components and not demand_components:
            loop_type = str(_field(plant_loop, "LoopType", "")).strip().lower()
            identifier = _identifier(plant_loop).lower()
            repair_tool = (
                "create_ironbug_hot_water_loop"
                if loop_type == "heating" or "hot" in identifier
                else "create_ironbug_chilled_water_loop"
            )
            issues.append(
                _issue(
                    severity="error",
                    code="ironbug_plant_loop_missing_demand_components",
                    source=plant_loop,
                    message=(
                        "IB_PlantLoop with supply equipment requires demand "
                        "components such as room-serving water coils before "
                        "EnergyPlus execution."
                    ),
                    repair_tool=repair_tool,
                )
            )
    return issues


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen: set[tuple[str, str, str]] = set()
    for issue in issues:
        key = (
            str(issue.get("code") or ""),
            str(issue.get("source_class") or ""),
            str(issue.get("identifier") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def _result(target: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    issues = _dedupe_issues(issues)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    recommended_next_tools = []
    for issue in issues:
        tool = PUBLIC_REPAIR_TOOLS.get(issue["repair_tool"], issue["repair_tool"])
        if tool not in recommended_next_tools:
            recommended_next_tools.append(tool)
    status = "pass" if error_count == 0 else "fail"
    return {
        "target": target,
        "summary_view": {
            "status": status,
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "report": {
            "status": status,
            "issues": issues,
            "recommended_next_tools": recommended_next_tools,
        },
    }


def validate_ironbug_detailed_hvac_readiness(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> dict[str, Any]:
    """Validate Ironbug graph readiness before creating Honeybee DetailedHVAC."""

    _, target, _, model = load_ironbug_model(
        _garden_root(garden_root),
        ironbug_model_target=ironbug_model_target,
    )
    issues = [
        *_outdoor_air_controller_issues(model),
        *_outdoor_air_system_issues(model),
        *_thermal_zone_binding_issues(model),
        *_room_serving_without_thermal_zone_issues(model),
        *_electric_load_center_missing_thermal_zone_issues(model),
    ]
    return _result(target, issues)


def validate_ironbug_energyplus_readiness(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> dict[str, Any]:
    """Validate Ironbug graph readiness before EnergyPlus execution."""

    _, target, _, model = load_ironbug_model(
        _garden_root(garden_root),
        ironbug_model_target=ironbug_model_target,
    )
    issues = [
        *_outdoor_air_controller_issues(model),
        *_outdoor_air_system_issues(model),
        *_water_coil_autosize_issues(model),
        *_heating_water_coil_ua_sizing_issues(model),
        *_stale_embedded_component_issues(model),
        *_fan_coil_child_issues(model),
        *_fan_coil_connection_issues(model),
        *_air_loop_component_issues(model),
        *_thermal_zone_binding_issues(model),
        *_room_serving_without_thermal_zone_issues(model),
        *_electric_load_center_missing_thermal_zone_issues(model),
        *_load_profile_plant_issues(model),
        *_plant_loop_missing_pump_issues(model),
        *_plant_loop_component_issues(model),
    ]
    return _result(target, issues)
