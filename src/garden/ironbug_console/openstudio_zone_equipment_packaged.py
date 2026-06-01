"""Packaged terminal ZoneHVAC writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import _new_heating_electric
from garden.ironbug_console.openstudio_coils_dx import (
    _new_cooling_dx_single_speed,
    _new_heating_dx_single_speed,
)
from garden.ironbug_console.openstudio_fans import _new_fan_on_off
from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _thermal_zone_name_for_field_reference,
)


def _write_ptac(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_on_off(openstudio, model, child_nodes["IB_FanOnOff"])
    heating_coil, heating_summary = _new_heating_electric(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingElectric"],
    )
    cooling_coil, cooling_summary = _new_cooling_dx_single_speed(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingDXSingleSpeed"],
    )
    ptac = openstudio.model.ZoneHVACPackagedTerminalAirConditioner(
        model,
        model.alwaysOnDiscreteSchedule(),
        fan,
        heating_coil,
        cooling_coil,
    )
    ptac_name = str(node.fields.get("Name") or node.identifier)
    ptac.setName(ptac_name)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    ptac.addToThermalZone(zone)
    ptac_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:PackagedTerminalAirConditioner",
        name=ptac_name,
    )
    return (
        cooling_summary,
        heating_summary,
        fan_summary,
        ptac_summary,
    )


def _write_pthp(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_on_off(openstudio, model, child_nodes["IB_FanOnOff"])
    heating_coil, heating_summary = _new_heating_dx_single_speed(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingDXSingleSpeed"],
    )
    cooling_coil, cooling_summary = _new_cooling_dx_single_speed(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingDXSingleSpeed"],
    )
    supplemental_coil, supplemental_summary = _new_heating_electric(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingElectric"],
    )
    pthp = openstudio.model.ZoneHVACPackagedTerminalHeatPump(
        model,
        model.alwaysOnDiscreteSchedule(),
        fan,
        heating_coil,
        cooling_coil,
        supplemental_coil,
    )
    pthp_name = str(node.fields.get("Name") or node.identifier)
    pthp.setName(pthp_name)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    pthp.addToThermalZone(zone)
    pthp_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:PackagedTerminalHeatPump",
        name=pthp_name,
    )
    return (
        cooling_summary,
        heating_summary,
        fan_summary,
        supplemental_summary,
        pthp_summary,
    )


def _write_water_to_air_heat_pump(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_on_off(openstudio, model, child_nodes["IB_FanOnOff"])
    heating_coil, heating_summary = _new_generic_openstudio_object(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingWaterToAirHeatPumpEquationFit"],
    )
    cooling_coil, cooling_summary = _new_generic_openstudio_object(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingWaterToAirHeatPumpEquationFit"],
    )
    supplemental_coil, supplemental_summary = _new_heating_electric(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingElectric"],
    )
    heat_pump = openstudio.model.ZoneHVACWaterToAirHeatPump(
        model,
        model.alwaysOnDiscreteSchedule(),
        fan,
        heating_coil,
        cooling_coil,
        supplemental_coil,
    )
    heat_pump_name = str(node.fields.get("Name") or node.identifier)
    heat_pump.setName(heat_pump_name)
    _apply_generic_openstudio_fields(heat_pump, node)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    heat_pump.addToThermalZone(zone)
    heat_pump_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:WaterToAirHeatPump",
        name=heat_pump_name,
    )
    return (
        cooling_summary,
        heating_summary,
        fan_summary,
        supplemental_summary,
        heat_pump_summary,
    )
