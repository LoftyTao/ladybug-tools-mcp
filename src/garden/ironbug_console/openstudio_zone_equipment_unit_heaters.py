"""Unit heater ZoneHVAC writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_heating_electric,
    _new_heating_water,
)
from garden.ironbug_console.openstudio_fans import (
    _new_fan_constant_volume,
    _new_fan_on_off,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _thermal_zone_name_for_field_reference,
)


def _write_unit_heater(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    if "IB_CoilHeatingWater" in child_nodes and "IB_FanOnOff" in child_nodes:
        fan, fan_summary = _new_fan_on_off(
            openstudio,
            model,
            child_nodes["IB_FanOnOff"],
        )
        heating_coil, heating_summary = _new_heating_water(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingWater"],
        )
    else:
        fan, fan_summary = _new_fan_constant_volume(
            openstudio,
            model,
            child_nodes["IB_FanConstantVolume"],
        )
        heating_coil, heating_summary = _new_heating_electric(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingElectric"],
        )
    unit_heater = openstudio.model.ZoneHVACUnitHeater(
        model,
        model.alwaysOnDiscreteSchedule(),
        fan,
        heating_coil,
    )
    unit_heater_name = str(node.fields.get("Name") or node.identifier)
    unit_heater.setName(unit_heater_name)
    _set_autosizable_if_present(
        unit_heater.setMaximumSupplyAirFlowRate,
        unit_heater.autosizeMaximumSupplyAirFlowRate,
        node,
        "MaximumSupplyAirFlowRate",
    )
    _set_autosizable_if_present(
        unit_heater.setMaximumHotWaterFlowRate,
        unit_heater.autosizeMaximumHotWaterFlowRate,
        node,
        "MaximumHotWaterFlowRate",
    )
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    unit_heater.addToThermalZone(zone)
    unit_heater_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:UnitHeater",
        name=unit_heater_name,
    )
    return (
        heating_summary,
        fan_summary,
        unit_heater_summary,
    )
