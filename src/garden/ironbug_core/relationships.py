"""Explicit Ironbug DetailedHVAC graph relationship services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ironbug import hvac

from garden.ironbug_core.assembly import (
    _component_library,
    _dump_source_object,
    _hydrate_source_object,
    _save_update,
    _source_type_accepts,
)
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.targets import make_ironbug_model_object_target
from ladybug_tools_mcp.contracts.report import make_report

_VAV_REHEAT_TERMINAL_COILS: set[str] = {
    "IB_CoilHeatingWater",
    "IB_CoilHeatingElectric",
    "IB_CoilHeatingGas",
}

_UNIT_HEATER_HEATING_COILS: set[str] = {
    "IB_CoilHeatingWater",
    "IB_CoilHeatingElectric",
    "IB_CoilHeatingGas",
}

_UNIT_HEATER_FANS: set[str] = {
    "IB_FanOnOff",
    "IB_FanConstantVolume",
    "IB_FanVariableVolume",
    "IB_FanSystemModel",
}

_UNIT_VENTILATOR_COOLING_COILS: set[str] = {
    "IB_CoilCoolingWater",
}

_UNIT_VENTILATOR_HEATING_COILS: set[str] = {
    "IB_CoilHeatingWater",
    "IB_CoilHeatingElectric",
    "IB_CoilHeatingGas",
}

_UNIT_VENTILATOR_FANS: set[str] = {
    "IB_FanOnOff",
    "IB_FanConstantVolume",
    "IB_FanVariableVolume",
    "IB_FanSystemModel",
}


@dataclass
class _ResolvedObject:
    obj: Any
    target: dict[str, Any]
    save: Callable[[Any], None]


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _object_identifier(obj: Any) -> str:
    if isinstance(obj, dict):
        identifier = obj.get("identifier")
        if identifier is None:
            raise ValueError("Ironbug object dict has no identifier.")
        return str(identifier)
    identifier = getattr(obj, "identifier", None)
    if identifier is None:
        raise ValueError("Ironbug object has no identifier.")
    return str(identifier)


def _target_for_component(model_target: dict[str, Any], identifier: str, source_class: str):
    return make_ironbug_model_object_target(
        model_target=model_target,
        object_type="component",
        object_path=f"user_data.ironbug_component_library.{identifier}",
        source_class=source_class,
        identifier=identifier,
    )


def _resolve_component(model: Any, model_target: dict[str, Any], identifier: str) -> _ResolvedObject:
    library = _component_library(model)
    if identifier not in library:
        raise ValueError(f"Ironbug component not found: {identifier}")
    record = library[identifier]
    obj = _hydrate_source_object(dict(record["data"]))
    source_class = str(record["source_class"])

    def save(updated: Any) -> None:
        record["data"] = _dump_source_object(updated)
        record["source_class"] = getattr(updated, "SOURCE_CLASS", source_class)

    return _ResolvedObject(
        obj=obj,
        target=_target_for_component(model_target, identifier, source_class),
        save=save,
    )


def _resolve_system_list_object(
    *,
    model: Any,
    model_target: dict[str, Any],
    object_type: str,
    identifier: str,
) -> _ResolvedObject:
    if model.HVACSystem is None:
        raise ValueError("Ironbug model has no HVACSystem.")
    list_name, target_type, path_prefix = {
        "air_loop": ("AirLoops", "air_loop", "HVACSystem.AirLoops"),
        "plant_loop": ("PlantLoops", "plant_loop", "HVACSystem.PlantLoops"),
        "vrf": ("VariableRefrigerantFlows", "vrf", "HVACSystem.VariableRefrigerantFlows"),
    }[object_type]
    objects = list(getattr(model.HVACSystem, list_name) or [])
    for index, obj in enumerate(objects):
        if _object_identifier(obj) == identifier:

            def save(updated: Any, *, index: int = index, objects: list[Any] = objects) -> None:
                objects[index] = updated
                setattr(model.HVACSystem, list_name, objects)

            source_class = getattr(obj, "SOURCE_CLASS", obj.__class__.__name__)
            return _ResolvedObject(
                obj=obj,
                target=make_ironbug_model_object_target(
                    model_target=model_target,
                    object_type=target_type,
                    object_path=f"{path_prefix}[{index}]",
                    source_class=source_class,
                    identifier=identifier,
                ),
                save=save,
            )
    raise ValueError(f"Ironbug {object_type} not found: {identifier}")


def _resolve_object(model: Any, model_target: dict[str, Any], reference: Any) -> _ResolvedObject:
    if isinstance(reference, str):
        try:
            return _resolve_component(model, model_target, reference)
        except ValueError:
            pass
        for object_type in ("air_loop", "plant_loop", "vrf"):
            try:
                return _resolve_system_list_object(
                    model=model,
                    model_target=model_target,
                    object_type=object_type,
                    identifier=reference,
                )
            except ValueError:
                continue
        raise ValueError(f"Ironbug object not found: {reference}")
    if not isinstance(reference, dict):
        raise ValueError("Ironbug object references must be targets or identifiers.")
    object_type = reference.get("object_type")
    identifier = reference.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Ironbug object target requires an identifier.")
    if object_type == "component":
        return _resolve_component(model, model_target, identifier)
    if object_type in {"air_loop", "plant_loop", "vrf"}:
        return _resolve_system_list_object(
            model=model,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
        )
    raise ValueError(f"Unsupported Ironbug object target type: {object_type}")


def _require_source(resolved: _ResolvedObject, allowed: set[str]) -> None:
    source_class = getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__)
    if source_class not in allowed:
        raise ValueError(f"Expected {sorted(allowed)}, got {source_class}")


def _load_for_update(garden_root: str, ironbug_model_target: dict[str, Any]):
    garden_root_path = _garden_root(garden_root)
    manifest, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    return garden_root_path, manifest, target, model


def _save_relationship(
    *,
    garden_root_path: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Any,
    operation: str,
    target: dict[str, Any],
    details: dict[str, Any],
) -> dict[str, Any]:
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=model_target,
        model=model,
        operation=operation,
        change_summary=details,
    )
    target["model_target"] = updated_target
    return {
        "target": target,
        "updated_model_target": updated_target,
        "summary_view": details,
        "persistence_receipt": receipt,
        "report": make_report(
            status="updated",
            message=f"Updated Ironbug relationship: {operation}",
            details={"persisted_path": persisted_path, **details},
        ),
    }


def _relationship_update(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    operation: str,
    primary_reference: Any,
    mutator: Callable[[Any, Any, dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    garden_root_path, manifest, model_target, model = _load_for_update(
        garden_root,
        ironbug_model_target,
    )
    primary = _resolve_object(model, model_target, primary_reference)
    details = mutator(model, primary.obj, model_target)
    primary.save(primary.obj)
    return _save_relationship(
        garden_root_path=garden_root_path,
        manifest=manifest,
        model_target=model_target,
        model=model,
        operation=operation,
        target=primary.target,
        details=details,
    )


def add_ironbug_child(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    parent_target: Any,
    child_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, parent: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        child = _resolve_object(model, model_target, child_target)
        parent.Children = [*(parent.Children or []), child.obj]
        return {
            "parent_identifier": _object_identifier(parent),
            "child_identifier": _object_identifier(child.obj),
            "child_source_class": getattr(child.obj, "SOURCE_CLASS", child.obj.__class__.__name__),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="add_ironbug_child",
        primary_reference=parent_target,
        mutator=mutate,
    )


def set_ironbug_constant_volume_reheat_terminal_coil(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    air_terminal_target: Any,
    reheat_coil_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, terminal: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(terminal, {}, lambda _: None),
            {"IB_AirTerminalSingleDuctConstantVolumeReheat"},
        )
        coil = _resolve_object(model, model_target, reheat_coil_target)
        _require_source(coil, {"IB_CoilHeatingWater"})
        existing = [
            child
            for child in (terminal.Children or [])
            if getattr(child, "SOURCE_CLASS", "") != "IB_CoilHeatingWater"
        ]
        terminal.Children = [*existing, coil.obj]
        return {
            "air_terminal_identifier": _object_identifier(terminal),
            "reheat_coil_identifier": _object_identifier(coil.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_constant_volume_reheat_terminal_coil",
        primary_reference=air_terminal_target,
        mutator=mutate,
    )


def set_ironbug_vav_reheat_terminal_coil(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    air_terminal_target: Any,
    reheat_coil_target: Any,
) -> dict[str, Any]:
    """Set the reheat coil child of an IB_AirTerminalSingleDuctVAVReheat.

    Accepts the Ironbug source classes that map to EnergyPlus VAV reheat
    coil object types available in this source mirror: water, electric, and gas.
    """

    def mutate(model: Any, terminal: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(terminal, {}, lambda _: None),
            {"IB_AirTerminalSingleDuctVAVReheat"},
        )
        coil = _resolve_object(model, model_target, reheat_coil_target)
        _require_source(coil, _VAV_REHEAT_TERMINAL_COILS)
        existing = [
            child
            for child in (terminal.Children or [])
            if getattr(child, "SOURCE_CLASS", "") not in _VAV_REHEAT_TERMINAL_COILS
        ]
        terminal.Children = [*existing, coil.obj]
        return {
            "air_terminal_identifier": _object_identifier(terminal),
            "reheat_coil_identifier": _object_identifier(coil.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_vav_reheat_terminal_coil",
        primary_reference=air_terminal_target,
        mutator=mutate,
    )


def set_ironbug_controller_mechanical_ventilation(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    controller_outdoor_air_target: Any,
    controller_mechanical_ventilation_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, controller: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(controller_ref := _ResolvedObject(controller, {}, lambda _: None), {"IB_ControllerOutdoorAir"})
        mechanical = _resolve_object(model, model_target, controller_mechanical_ventilation_target)
        _require_source(mechanical, {"IB_ControllerMechanicalVentilation"})
        existing = [
            child
            for child in (controller.Children or [])
            if getattr(child, "SOURCE_CLASS", "") != "IB_ControllerMechanicalVentilation"
        ]
        controller.Children = [*existing, mechanical.obj]
        return {
            "controller_identifier": _object_identifier(controller),
            "mechanical_ventilation_identifier": _object_identifier(mechanical.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_controller_mechanical_ventilation",
        primary_reference=controller_outdoor_air_target,
        mutator=mutate,
    )


def set_ironbug_outdoor_air_system_controller(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    outdoor_air_system_target: Any,
    controller_outdoor_air_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, outdoor_air_system: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(outdoor_air_system, {}, lambda _: None), {"IB_OutdoorAirSystem"})
        controller = _resolve_object(model, model_target, controller_outdoor_air_target)
        _require_source(controller, {"IB_ControllerOutdoorAir"})
        children = [
            child
            for child in (outdoor_air_system.Children or [])
            if getattr(child, "SOURCE_CLASS", "") != "IB_ControllerOutdoorAir"
        ]
        outdoor_air_system.Children = [*children, controller.obj]
        return {
            "outdoor_air_system_identifier": _object_identifier(outdoor_air_system),
            "controller_identifier": _object_identifier(controller.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_outdoor_air_system_controller",
        primary_reference=outdoor_air_system_target,
        mutator=mutate,
    )


def set_ironbug_outdoor_air_system_oa_stream(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    outdoor_air_system_target: Any,
    oa_stream_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, outdoor_air_system: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(outdoor_air_system, {}, lambda _: None), {"IB_OutdoorAirSystem"})
        objs = [_resolve_object(model, model_target, item).obj for item in oa_stream_targets]
        outdoor_air_system.OAStreamObjs = objs
        return {
            "outdoor_air_system_identifier": _object_identifier(outdoor_air_system),
            "oa_stream_count": len(objs),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_outdoor_air_system_oa_stream",
        primary_reference=outdoor_air_system_target,
        mutator=mutate,
    )


def set_ironbug_outdoor_air_system_relief_stream(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    outdoor_air_system_target: Any,
    relief_stream_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, outdoor_air_system: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(outdoor_air_system, {}, lambda _: None), {"IB_OutdoorAirSystem"})
        objs = [_resolve_object(model, model_target, item).obj for item in relief_stream_targets]
        outdoor_air_system.ReliefStreamObjs = objs
        return {
            "outdoor_air_system_identifier": _object_identifier(outdoor_air_system),
            "relief_stream_count": len(objs),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_outdoor_air_system_relief_stream",
        primary_reference=outdoor_air_system_target,
        mutator=mutate,
    )


def set_ironbug_air_loop_supply_components(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    air_loop_target: Any,
    supply_component_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, air_loop: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        air_loop.SupplyComponents = [
            _resolve_object(model, model_target, item).obj for item in supply_component_targets
        ]
        return {
            "air_loop_identifier": _object_identifier(air_loop),
            "supply_component_count": len(air_loop.SupplyComponents),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_air_loop_supply_components",
        primary_reference=air_loop_target,
        mutator=mutate,
    )


def set_ironbug_air_loop_demand_components(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    air_loop_target: Any,
    demand_component_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, air_loop: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        air_loop.DemandComponents = [
            _resolve_object(model, model_target, item).obj for item in demand_component_targets
        ]
        return {
            "air_loop_identifier": _object_identifier(air_loop),
            "demand_component_count": len(air_loop.DemandComponents),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_air_loop_demand_components",
        primary_reference=air_loop_target,
        mutator=mutate,
    )


def set_ironbug_loop_branches(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    branches_target: Any,
    branch_component_targets: list[list[Any]],
) -> dict[str, Any]:
    def mutate(model: Any, branches: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(branches, {}, lambda _: None),
            {"IB_AirLoopBranches", "IB_PlantLoopBranches"},
        )
        resolved_branches = [
            [_resolve_object(model, model_target, item).obj for item in branch]
            for branch in branch_component_targets
        ]
        branches.Branches = resolved_branches
        return {
            "branches_identifier": _object_identifier(branches),
            "branch_count": len(resolved_branches),
            "branch_lengths": [len(branch) for branch in resolved_branches],
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_loop_branches",
        primary_reference=branches_target,
        mutator=mutate,
    )


def set_ironbug_thermal_zone_air_terminal(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    thermal_zone_target: Any,
    air_terminal_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, thermal_zone: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(thermal_zone, {}, lambda _: None), {"IB_ThermalZone"})
        air_terminal = _resolve_object(model, model_target, air_terminal_target)
        source_class = getattr(
            air_terminal.obj,
            "SOURCE_CLASS",
            air_terminal.obj.__class__.__name__,
        )
        if not _source_type_accepts(str(source_class), "IB_AirTerminal"):
            raise ValueError(f"air_terminal_target accepts IB_AirTerminal targets, got {source_class}.")
        thermal_zone.AirTerminal = air_terminal.obj
        return {
            "thermal_zone_identifier": _object_identifier(thermal_zone),
            "air_terminal_identifier": _object_identifier(air_terminal.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_thermal_zone_air_terminal",
        primary_reference=thermal_zone_target,
        mutator=mutate,
    )


def set_ironbug_thermal_zone_sizing_zone(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    thermal_zone_target: Any,
    sizing_zone_target: Any | None = None,
) -> dict[str, Any]:
    """Set the SizingZone child of an IB_ThermalZone.

    When sizing_zone_target is omitted, installs the Ironbug source default
    IB_SizingZone child. When provided, validates the target first.
    """

    def mutate(model: Any, thermal_zone: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(thermal_zone, {}, lambda _: None), {"IB_ThermalZone"})
        if sizing_zone_target is None:
            sizing_zone_obj = hvac.IB_SizingZone.model_construct()
            sizing_zone_identifier = None
        else:
            sizing_zone = _resolve_object(model, model_target, sizing_zone_target)
            _require_source(sizing_zone, {"IB_SizingZone"})
            sizing_zone_obj = sizing_zone.obj
            sizing_zone_identifier = _object_identifier(sizing_zone.obj)
        thermal_zone.SizingZone = sizing_zone_obj
        return {
            "thermal_zone_identifier": _object_identifier(thermal_zone),
            "sizing_zone_identifier": sizing_zone_identifier,
            "source_default_sizing_zone": sizing_zone_target is None,
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_thermal_zone_sizing_zone",
        primary_reference=thermal_zone_target,
        mutator=mutate,
    )


def add_ironbug_thermal_zone_equipment(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    thermal_zone_target: Any,
    zone_equipment_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, thermal_zone: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(thermal_zone, {}, lambda _: None), {"IB_ThermalZone"})
        equipment = _resolve_object(model, model_target, zone_equipment_target)
        thermal_zone.ZoneEquipments = [*(thermal_zone.ZoneEquipments or []), equipment.obj]
        return {
            "thermal_zone_identifier": _object_identifier(thermal_zone),
            "zone_equipment_identifier": _object_identifier(equipment.obj),
            "zone_equipment_count": len(thermal_zone.ZoneEquipments),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="add_ironbug_thermal_zone_equipment",
        primary_reference=thermal_zone_target,
        mutator=mutate,
    )


def set_ironbug_thermal_zone_supply_plenum(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    thermal_zone_target: Any,
    supply_plenum_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, thermal_zone: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(thermal_zone, {}, lambda _: None), {"IB_ThermalZone"})
        plenum = _resolve_object(model, model_target, supply_plenum_target)
        _require_source(plenum, {"IB_ThermalZone"})
        thermal_zone.SupplyPlenum = plenum.obj
        return {
            "thermal_zone_identifier": _object_identifier(thermal_zone),
            "supply_plenum_identifier": _object_identifier(plenum.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_thermal_zone_supply_plenum",
        primary_reference=thermal_zone_target,
        mutator=mutate,
    )


def set_ironbug_thermal_zone_return_plenum(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    thermal_zone_target: Any,
    return_plenum_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, thermal_zone: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(thermal_zone, {}, lambda _: None), {"IB_ThermalZone"})
        plenum = _resolve_object(model, model_target, return_plenum_target)
        _require_source(plenum, {"IB_ThermalZone"})
        thermal_zone.ReturnPlenum = plenum.obj
        return {
            "thermal_zone_identifier": _object_identifier(thermal_zone),
            "return_plenum_identifier": _object_identifier(plenum.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_thermal_zone_return_plenum",
        primary_reference=thermal_zone_target,
        mutator=mutate,
    )


def set_ironbug_fan_coil_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    fan_coil_target: Any,
    heating_coil_target: Any,
    cooling_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, fan_coil: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(_ResolvedObject(fan_coil, {}, lambda _: None), {"IB_ZoneHVACFourPipeFanCoil"})
        heating = _resolve_object(model, model_target, heating_coil_target)
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(heating, {"IB_CoilHeatingWater"})
        _require_source(cooling, {"IB_CoilCoolingWater"})
        fan_coil.Children = [heating.obj, cooling.obj, fan.obj]
        return {
            "fan_coil_identifier": _object_identifier(fan_coil),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_fan_coil_children",
        primary_reference=fan_coil_target,
        mutator=mutate,
    )


def set_ironbug_ptac_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    ptac_target: Any,
    fan_target: Any,
    heating_coil_target: Any,
    cooling_coil_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, ptac: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(ptac, {}, lambda _: None),
            {"IB_ZoneHVACPackagedTerminalAirConditioner"},
        )
        fan = _resolve_object(model, model_target, fan_target)
        heating = _resolve_object(model, model_target, heating_coil_target)
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        _require_source(fan, {"IB_FanOnOff", "IB_FanConstantVolume", "IB_FanSystemModel"})
        _require_source(
            heating,
            {
                "IB_CoilHeatingElectric",
                "IB_CoilHeatingGas",
                "IB_CoilHeatingWater",
                "IB_CoilHeatingSteam",
            },
        )
        _require_source(
            cooling,
            {
                "IB_CoilCoolingDXSingleSpeed",
                "IB_CoilCoolingDXTwoSpeed",
                "IB_CoilCoolingDXMultiSpeed",
                "IB_CoilCoolingWater",
            },
        )
        ptac.Children = [cooling.obj, heating.obj, fan.obj]
        return {
            "ptac_identifier": _object_identifier(ptac),
            "fan_identifier": _object_identifier(fan.obj),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_ptac_children",
        primary_reference=ptac_target,
        mutator=mutate,
    )


def set_ironbug_pthp_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    pthp_target: Any,
    fan_target: Any,
    heating_coil_target: Any,
    cooling_coil_target: Any,
    supplemental_heating_coil_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, pthp: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(pthp, {}, lambda _: None),
            {"IB_ZoneHVACPackagedTerminalHeatPump"},
        )
        fan = _resolve_object(model, model_target, fan_target)
        heating = _resolve_object(model, model_target, heating_coil_target)
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        supplemental = _resolve_object(
            model,
            model_target,
            supplemental_heating_coil_target,
        )
        _require_source(fan, {"IB_FanOnOff", "IB_FanConstantVolume", "IB_FanSystemModel"})
        _require_source(
            heating,
            {
                "IB_CoilHeatingDXSingleSpeed",
                "IB_CoilHeatingDXMultiSpeed",
                "IB_CoilHeatingElectric",
                "IB_CoilHeatingGas",
            },
        )
        _require_source(
            cooling,
            {
                "IB_CoilCoolingDXSingleSpeed",
                "IB_CoilCoolingDXTwoSpeed",
                "IB_CoilCoolingDXMultiSpeed",
            },
        )
        _require_source(
            supplemental,
            {
                "IB_CoilHeatingElectric",
                "IB_CoilHeatingGas",
            },
        )
        pthp.Children = [cooling.obj, heating.obj, fan.obj, supplemental.obj]
        return {
            "pthp_identifier": _object_identifier(pthp),
            "fan_identifier": _object_identifier(fan.obj),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
            "supplemental_heating_coil_identifier": _object_identifier(supplemental.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_pthp_children",
        primary_reference=pthp_target,
        mutator=mutate,
    )


def set_ironbug_vrf_terminal_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    vrf_terminal_target: Any,
    cooling_coil_target: Any,
    heating_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    def mutate(model: Any, terminal: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(terminal, {}, lambda _: None),
            {"IB_ZoneHVACTerminalUnitVariableRefrigerantFlow"},
        )
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        heating = _resolve_object(model, model_target, heating_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(cooling, {"IB_CoilCoolingDXVariableRefrigerantFlow"})
        _require_source(heating, {"IB_CoilHeatingDXVariableRefrigerantFlow"})
        _require_source(fan, {"IB_FanOnOff"})
        terminal.Children = [cooling.obj, heating.obj, fan.obj]
        return {
            "vrf_terminal_identifier": _object_identifier(terminal),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_vrf_terminal_children",
        primary_reference=vrf_terminal_target,
        mutator=mutate,
    )


def set_ironbug_vrf_terminals(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    vrf_target: Any,
    terminal_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, vrf: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(vrf, {}, lambda _: None),
            {"IB_AirConditionerVariableRefrigerantFlow"},
        )
        terminals = [_resolve_object(model, model_target, item) for item in terminal_targets]
        for terminal in terminals:
            _require_source(terminal, {"IB_ZoneHVACTerminalUnitVariableRefrigerantFlow"})
        vrf.Terminals = [terminal.obj for terminal in terminals]
        return {
            "vrf_identifier": _object_identifier(vrf),
            "terminal_count": len(vrf.Terminals),
            "terminal_identifiers": [_object_identifier(item) for item in vrf.Terminals],
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_vrf_terminals",
        primary_reference=vrf_target,
        mutator=mutate,
    )


def set_ironbug_plant_loop_supply_components(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    plant_loop_target: Any,
    supply_component_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, plant_loop: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        plant_loop.SupplyComponents = [
            _resolve_object(model, model_target, item).obj for item in supply_component_targets
        ]
        return {
            "plant_loop_identifier": _object_identifier(plant_loop),
            "supply_component_count": len(plant_loop.SupplyComponents),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_plant_loop_supply_components",
        primary_reference=plant_loop_target,
        mutator=mutate,
    )


def set_ironbug_plant_loop_demand_components(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    plant_loop_target: Any,
    demand_component_targets: list[Any],
) -> dict[str, Any]:
    def mutate(model: Any, plant_loop: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        plant_loop.DemandComponents = [
            _resolve_object(model, model_target, item).obj for item in demand_component_targets
        ]
        return {
            "plant_loop_identifier": _object_identifier(plant_loop),
            "demand_component_count": len(plant_loop.DemandComponents),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_plant_loop_demand_components",
        primary_reference=plant_loop_target,
        mutator=mutate,
    )


def connect_ironbug_water_coil_to_plant_loop(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    water_coil_target: Any,
    plant_loop_target: Any,
    side: str = "demand",
) -> dict[str, Any]:
    garden_root_path, manifest, model_target, model = _load_for_update(
        garden_root,
        ironbug_model_target,
    )
    coil = _resolve_object(model, model_target, water_coil_target)
    _require_source(coil, {"IB_CoilHeatingWater", "IB_CoilCoolingWater"})
    plant_loop = _resolve_object(model, model_target, plant_loop_target)
    _require_source(plant_loop, {"IB_PlantLoop"})
    side_normalized = side.strip().lower()
    if side_normalized not in {"demand", "supply"}:
        raise ValueError("side must be 'demand' or 'supply'.")
    attr = "DemandComponents" if side_normalized == "demand" else "SupplyComponents"
    components = list(getattr(plant_loop.obj, attr) or [])
    coil_id = _object_identifier(coil.obj)
    if not any(_object_identifier(item) == coil_id for item in components):
        components.append(coil.obj)
    setattr(plant_loop.obj, attr, components)
    if coil.obj.user_data is None:
        coil.obj.user_data = {}
    coil.obj.user_data["connected_plant_loop_identifier"] = _object_identifier(plant_loop.obj)
    coil.obj.user_data["connected_plant_loop_side"] = side_normalized
    coil.save(coil.obj)
    plant_loop.save(plant_loop.obj)
    details = {
        "water_coil_identifier": coil_id,
        "plant_loop_identifier": _object_identifier(plant_loop.obj),
        "side": side_normalized,
    }
    return _save_relationship(
        garden_root_path=garden_root_path,
        manifest=manifest,
        model_target=model_target,
        model=model,
        operation="connect_ironbug_water_coil_to_plant_loop",
        target=coil.target,
        details=details,
    )


def set_ironbug_unit_heater_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    unit_heater_target: Any,
    heating_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    """Set the heating coil and fan children of an IB_ZoneHVACUnitHeater.

    Accepts the Ironbug source classes that map to EnergyPlus
    ZoneHVAC:UnitHeater legal heating coil and fan object types available in
    the current source mirror.
    """

    def mutate(model: Any, unit_heater: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(unit_heater, {}, lambda _: None),
            {"IB_ZoneHVACUnitHeater"},
        )
        heating = _resolve_object(model, model_target, heating_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(heating, _UNIT_HEATER_HEATING_COILS)
        _require_source(fan, _UNIT_HEATER_FANS)
        unit_heater.Children = [heating.obj, fan.obj]
        return {
            "unit_heater_identifier": _object_identifier(unit_heater),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_unit_heater_children",
        primary_reference=unit_heater_target,
        mutator=mutate,
    )


def set_ironbug_unit_ventilator_cooling_heating_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    unit_ventilator_target: Any,
    cooling_coil_target: Any,
    heating_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    """Set the cooling coil, heating coil, and fan children of an
    IB_ZoneHVACUnitVentilator_CoolingHeating.

    Cooling coil is narrowed to IB_CoilCoolingWater. Heating coil accepts
    IB_CoilHeatingWater, IB_CoilHeatingElectric, or IB_CoilHeatingGas.
    Fan accepts IB_FanOnOff, IB_FanConstantVolume, IB_FanVariableVolume,
    or IB_FanSystemModel.  Child order matches Ironbug source: cooling coil,
    heating coil, fan.
    """

    def mutate(model: Any, ventilator: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(ventilator, {}, lambda _: None),
            {"IB_ZoneHVACUnitVentilator_CoolingHeating"},
        )
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        heating = _resolve_object(model, model_target, heating_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(cooling, _UNIT_VENTILATOR_COOLING_COILS)
        _require_source(heating, _UNIT_VENTILATOR_HEATING_COILS)
        _require_source(fan, _UNIT_VENTILATOR_FANS)
        ventilator.Children = [cooling.obj, heating.obj, fan.obj]
        return {
            "unit_ventilator_identifier": _object_identifier(ventilator),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_unit_ventilator_cooling_heating_children",
        primary_reference=unit_ventilator_target,
        mutator=mutate,
    )


def set_ironbug_unit_ventilator_cooling_only_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    unit_ventilator_target: Any,
    cooling_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    """Set the cooling coil and fan children of an
    IB_ZoneHVACUnitVentilator_CoolingOnly.

    Cooling coil is narrowed to IB_CoilCoolingWater. Fan accepts
    IB_FanOnOff, IB_FanConstantVolume, IB_FanVariableVolume,
    or IB_FanSystemModel.  Child order matches Ironbug source: cooling coil,
    fan.
    """

    def mutate(model: Any, ventilator: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(ventilator, {}, lambda _: None),
            {"IB_ZoneHVACUnitVentilator_CoolingOnly"},
        )
        cooling = _resolve_object(model, model_target, cooling_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(cooling, _UNIT_VENTILATOR_COOLING_COILS)
        _require_source(fan, _UNIT_VENTILATOR_FANS)
        ventilator.Children = [cooling.obj, fan.obj]
        return {
            "unit_ventilator_identifier": _object_identifier(ventilator),
            "cooling_coil_identifier": _object_identifier(cooling.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_unit_ventilator_cooling_only_children",
        primary_reference=unit_ventilator_target,
        mutator=mutate,
    )


def set_ironbug_unit_ventilator_heating_only_children(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    unit_ventilator_target: Any,
    heating_coil_target: Any,
    fan_target: Any,
) -> dict[str, Any]:
    """Set the heating coil and fan children of an
    IB_ZoneHVACUnitVentilator_HeatingOnly.

    Heating coil accepts IB_CoilHeatingWater, IB_CoilHeatingElectric, or
    IB_CoilHeatingGas.  Fan accepts IB_FanOnOff, IB_FanConstantVolume,
    IB_FanVariableVolume, or IB_FanSystemModel.  Child order matches Ironbug
    source: heating coil, fan.
    """

    def mutate(model: Any, ventilator: Any, model_target: dict[str, Any]) -> dict[str, Any]:
        _require_source(
            _ResolvedObject(ventilator, {}, lambda _: None),
            {"IB_ZoneHVACUnitVentilator_HeatingOnly"},
        )
        heating = _resolve_object(model, model_target, heating_coil_target)
        fan = _resolve_object(model, model_target, fan_target)
        _require_source(heating, _UNIT_VENTILATOR_HEATING_COILS)
        _require_source(fan, _UNIT_VENTILATOR_FANS)
        ventilator.Children = [heating.obj, fan.obj]
        return {
            "unit_ventilator_identifier": _object_identifier(ventilator),
            "heating_coil_identifier": _object_identifier(heating.obj),
            "fan_identifier": _object_identifier(fan.obj),
        }

    return _relationship_update(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        operation="set_ironbug_unit_ventilator_heating_only_children",
        primary_reference=unit_ventilator_target,
        mutator=mutate,
    )
