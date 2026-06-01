"""Unit ventilator ZoneHVAC writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_cooling_water,
    _new_heating_water,
)
from garden.ironbug_console.openstudio_fans import _new_fan_on_off
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _set_if_present,
    _thermal_zone_name_for_field_reference,
)


def _write_unit_ventilator_cooling_heating(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    return _write_unit_ventilator(
        openstudio,
        model,
        graph,
        node,
        has_cooling=True,
        has_heating=True,
    )


def _write_unit_ventilator_cooling_only(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    return _write_unit_ventilator(
        openstudio,
        model,
        graph,
        node,
        has_cooling=True,
        has_heating=False,
    )


def _write_unit_ventilator_heating_only(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    return _write_unit_ventilator(
        openstudio,
        model,
        graph,
        node,
        has_cooling=False,
        has_heating=True,
    )


def _write_unit_ventilator(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    *,
    has_cooling: bool,
    has_heating: bool,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_on_off(
        openstudio,
        model,
        child_nodes["IB_FanOnOff"],
    )
    coil_summaries: list[OpenStudioWrittenObject] = []
    cooling_coil = None
    if has_cooling:
        cooling_coil, cooling_summary = _new_cooling_water(
            openstudio,
            model,
            child_nodes["IB_CoilCoolingWater"],
        )
        coil_summaries.append(cooling_summary)
    heating_coil = None
    if has_heating:
        heating_coil, heating_summary = _new_heating_water(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingWater"],
        )
        coil_summaries.append(heating_summary)
    unit_ventilator_name = str(node.fields.get("Name") or node.identifier)
    optional_unit_ventilator = model.getZoneHVACUnitVentilatorByName(
        unit_ventilator_name
    )
    if optional_unit_ventilator.is_initialized():
        unit_ventilator = optional_unit_ventilator.get()
    else:
        unit_ventilator = openstudio.model.ZoneHVACUnitVentilator(model)
        unit_ventilator.setName(unit_ventilator_name)
    if cooling_coil is not None:
        unit_ventilator.setCoolingCoil(cooling_coil)
    if heating_coil is not None:
        unit_ventilator.setHeatingCoil(heating_coil)
    unit_ventilator.setSupplyAirFan(fan)
    _set_autosizable_if_present(
        unit_ventilator.setMaximumSupplyAirFlowRate,
        unit_ventilator.autosizeMaximumSupplyAirFlowRate,
        node,
        "MaximumSupplyAirFlowRate",
    )
    _set_if_present(
        unit_ventilator.setOutdoorAirControlType,
        node,
        "OutdoorAirControlType",
        cast=str,
    )
    _set_autosizable_if_present(
        unit_ventilator.setMinimumOutdoorAirFlowRate,
        unit_ventilator.autosizeMinimumOutdoorAirFlowRate,
        node,
        "MinimumOutdoorAirFlowRate",
    )
    _set_autosizable_if_present(
        unit_ventilator.setMaximumOutdoorAirFlowRate,
        unit_ventilator.autosizeMaximumOutdoorAirFlowRate,
        node,
        "MaximumOutdoorAirFlowRate",
    )
    _set_if_present(
        unit_ventilator.setHeatingConvergenceTolerance,
        node,
        "HeatingConvergenceTolerance",
    )
    _set_if_present(
        unit_ventilator.setCoolingConvergenceTolerance,
        node,
        "CoolingConvergenceTolerance",
    )
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    unit_ventilator.addToThermalZone(zone)
    unit_ventilator_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:UnitVentilator",
        name=unit_ventilator_name,
    )
    return (
        *coil_summaries,
        fan_summary,
        unit_ventilator_summary,
    )
