"""OpenStudio writer for the Ironbug zone energy-recovery ventilator."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_curves import _CURVE_SPECS
from garden.ironbug_console.openstudio_fans import (
    _new_fan_on_off,
    _new_fan_system_model,
)
from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
    _is_autosize,
    _set_autosizable_if_present,
    _set_if_present,
    _thermal_zone_name_for_field_reference,
)


_FAN_SOURCE_CLASSES = frozenset(
    {
        "IB_FanConstantVolume",
        "IB_FanOnOff",
        "IB_FanSystemModel",
        "IB_FanVariableVolume",
        "IB_FanZoneExhaust",
    }
)
_SCHEDULE_OPENSTUDIO_CLASSES = {
    "IB_ScheduleFile": "ScheduleFile",
    "IB_ScheduleRuleset": "ScheduleRuleset",
}


def _write_energy_recovery_ventilator(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    """Write one ERV and its source-backed children."""

    children = [graph.node_by_identifier(str(identifier)) for identifier in node.children]
    written_objects: list[OpenStudioWrittenObject] = []

    heat_exchanger_node = next(
        (
            child
            for child in children
            if child.source_class == "IB_HeatExchangerAirToAirSensibleAndLatent"
        ),
        None,
    )
    heat_exchanger = None
    if heat_exchanger_node is not None:
        heat_exchanger, summary = _new_generic_openstudio_object(
            openstudio,
            model,
            heat_exchanger_node,
        )
        _append_written(written_objects, (summary,))

    fan_nodes = [child for child in children if child.source_class in _FAN_SOURCE_CLASSES]
    fans: list[Any] = []
    for fan_node in fan_nodes[:2]:
        fan, summary = _new_erv_fan(openstudio, model, fan_node)
        fans.append(fan)
        _append_written(written_objects, (summary,))

    supply_autosized = node.fields.get("SupplyAirFlowRate") is None or _is_autosize(
        node.fields.get("SupplyAirFlowRate")
    )
    exhaust_autosized = node.fields.get("ExhaustAirFlowRate") is None or _is_autosize(
        node.fields.get("ExhaustAirFlowRate")
    )
    for index, autosized in enumerate((supply_autosized, exhaust_autosized)):
        if not autosized or index >= len(fans):
            continue
        method_name = (
            "autosizeDesignMaximumAirFlowRate"
            if fan_nodes[index].source_class == "IB_FanSystemModel"
            else "autosizeMaximumFlowRate"
        )
        getattr(fans[index], method_name)()
    if heat_exchanger is not None and (supply_autosized or exhaust_autosized):
        heat_exchanger.autosizeNominalSupplyAirFlowRate()

    controller_node = next(
        (
            child
            for child in children
            if child.source_class
            == "IB_ZoneHVACEnergyRecoveryVentilatorController"
        ),
        None,
    )
    controller = None
    if controller_node is not None:
        controller, controller_summaries = _new_erv_controller(
            openstudio,
            model,
            graph,
            controller_node,
        )
        _append_written(written_objects, controller_summaries)

    name = str(node.fields.get("Name") or node.identifier)
    optional_equipment = model.getZoneHVACEnergyRecoveryVentilatorByName(name)
    if optional_equipment.is_initialized():
        equipment = optional_equipment.get()
    elif heat_exchanger is not None and len(fans) == 2:
        equipment = openstudio.model.ZoneHVACEnergyRecoveryVentilator(
            model,
            heat_exchanger,
            fans[0],
            fans[1],
        )
    else:
        equipment = openstudio.model.ZoneHVACEnergyRecoveryVentilator(model)
    equipment.setName(name)

    if heat_exchanger is not None:
        equipment.setHeatExchanger(heat_exchanger)
    if fans:
        equipment.setSupplyAirFan(fans[0])
    if len(fans) > 1:
        equipment.setExhaustAirFan(fans[1])
    if controller is not None:
        equipment.setController(controller)

    availability_schedule_node = _referenced_node(
        graph,
        node,
        "AvailabilityScheduleIdentifier",
    )
    if availability_schedule_node is not None:
        equipment.setAvailabilitySchedule(
            _openstudio_target(model, availability_schedule_node)
        )
    _set_autosizable_if_present(
        equipment.setSupplyAirFlowRate,
        equipment.autosizeSupplyAirFlowRate,
        node,
        "SupplyAirFlowRate",
    )
    _set_autosizable_if_present(
        equipment.setExhaustAirFlowRate,
        equipment.autosizeExhaustAirFlowRate,
        node,
        "ExhaustAirFlowRate",
    )
    _set_if_present(
        equipment.setVentilationRateperUnitFloorArea,
        node,
        "VentilationRateperUnitFloorArea",
    )
    _set_if_present(
        equipment.setVentilationRateperOccupant,
        node,
        "VentilationRateperOccupant",
    )

    zone_identifier = node.fields.get("ThermalZoneIdentifier")
    if zone_identifier is not None:
        zone_name = _thermal_zone_name_for_field_reference(graph, node)
        optional_zone = model.getThermalZoneByName(zone_name)
        if optional_zone.is_initialized():
            equipment.addToThermalZone(optional_zone.get())

    written_objects.append(
        OpenStudioWrittenObject(
            identifier=node.identifier,
            source_class=node.source_class,
            writer_family="terminal_zone_equipment",
            openstudio_type="OS:ZoneHVAC:EnergyRecoveryVentilator",
            name=name,
        )
    )
    return tuple(written_objects)


def _new_erv_fan(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    """Create a concrete IB_Fan child supported by the ERV object."""

    factories = {
        "IB_FanOnOff": _new_fan_on_off,
        "IB_FanSystemModel": _new_fan_system_model,
    }
    factory = factories.get(node.source_class)
    if factory is not None:
        return factory(openstudio, model, node)
    raise ValueError(
        "ZoneHVAC:EnergyRecoveryVentilator fans must be IB_FanOnOff or "
        f"IB_FanSystemModel; got {node.source_class}."
    )


def _new_erv_controller(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    """Create the ERV controller and resolve its typed targets."""

    name = str(node.fields.get("Name") or node.identifier)
    optional_controller = model.getZoneHVACEnergyRecoveryVentilatorControllerByName(
        name
    )
    if optional_controller.is_initialized():
        controller = optional_controller.get()
    else:
        controller = openstudio.model.ZoneHVACEnergyRecoveryVentilatorController(model)
        controller.setName(name)

    scalar_fields = {
        key: value
        for key, value in node.fields.items()
        if key
        not in {
            "ElectronicEnthalpyLimitCurve",
            "ElectronicEnthalpyLimitCurveIdentifier",
            "TimeofDayEconomizerFlowControlSchedule",
            "TimeofDayEconomizerFlowControlScheduleIdentifier",
        }
    }
    scalar_node = ConsoleGraphNode(
        identifier=node.identifier,
        source_class=node.source_class,
        path=node.path,
        fields=scalar_fields,
        children=node.children,
    )
    _apply_generic_openstudio_fields(controller, scalar_node)

    curve_node = _referenced_node(
        graph,
        node,
        "ElectronicEnthalpyLimitCurveIdentifier",
    )
    if curve_node is not None:
        controller.setElectronicEnthalpyLimitCurve(
            _openstudio_target(model, curve_node)
        )
    schedule_node = _referenced_node(
        graph,
        node,
        "TimeofDayEconomizerFlowControlScheduleIdentifier",
    )
    if schedule_node is not None:
        controller.setTimeofDayEconomizerFlowControlSchedule(
            _openstudio_target(model, schedule_node)
        )
    return controller, (
        OpenStudioWrittenObject(
            identifier=node.identifier,
            source_class=node.source_class,
            writer_family="terminal_zone_equipment",
            openstudio_type="OS:ZoneHVAC:EnergyRecoveryVentilator:Controller",
            name=name,
        ),
    )


def _referenced_node(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    field_name: str,
) -> ConsoleGraphNode | None:
    identifier = node.fields.get(field_name)
    if identifier is None:
        return None
    return graph.node_by_identifier(str(identifier))


def _openstudio_target(model: Any, node: ConsoleGraphNode) -> Any:
    source_class = node.source_class
    if source_class in _CURVE_SPECS:
        class_name = _CURVE_SPECS[source_class][0]
    else:
        class_name = _SCHEDULE_OPENSTUDIO_CLASSES.get(
            source_class,
            source_class.removeprefix("IB_"),
        )
    getter = getattr(model, f"get{class_name}ByName", None)
    if getter is None:
        raise ValueError(f"Unsupported ERV target object: {source_class}")
    name = str(node.fields.get("Name") or node.identifier)
    optional = getter(name)
    if not optional.is_initialized():
        raise ValueError(
            f"ERV target object was not written: {source_class}/{name}"
        )
    return optional.get()


__all__ = (
    "_new_erv_controller",
    "_write_energy_recovery_ventilator",
)
