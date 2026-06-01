"""Sizing object writers for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _referenced_node_name,
    _set_autosizable_if_present,
    _set_if_present,
    _thermal_zone_name_for_field_reference,
)


def _write_sizing_zone(
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    sizing_zone = zone.sizingZone()
    sizing_zone.setName(str(node.fields.get("Name") or f"{zone_name} Sizing Zone"))
    _set_if_present(
        sizing_zone.setZoneCoolingDesignSupplyAirTemperatureInputMethod,
        node,
        "ZoneCoolingDesignSupplyAirTemperatureInputMethod",
        cast=str,
    )
    _set_if_present(
        sizing_zone.setZoneCoolingDesignSupplyAirTemperature,
        node,
        "ZoneCoolingDesignSupplyAirTemperature",
    )
    _set_if_present(
        sizing_zone.setZoneHeatingDesignSupplyAirTemperatureInputMethod,
        node,
        "ZoneHeatingDesignSupplyAirTemperatureInputMethod",
        cast=str,
    )
    _set_if_present(
        sizing_zone.setZoneHeatingDesignSupplyAirTemperature,
        node,
        "ZoneHeatingDesignSupplyAirTemperature",
    )
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="sizing",
        openstudio_type="OS:Sizing:Zone",
        name=sizing_zone.nameString(),
    )


def _write_sizing_system(
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    air_loop_name = _referenced_node_name(
        graph,
        node,
        "AirLoopIdentifier",
        "AirLoopHVACIdentifier",
    )
    air_loop = model.getAirLoopHVACByName(air_loop_name).get()
    sizing_system = air_loop.sizingSystem()
    name = str(node.fields.get("Name") or f"{air_loop_name} Sizing")
    sizing_system.setName(name)
    _set_if_present(
        sizing_system.setTypeofLoadtoSizeOn,
        node,
        "TypeofLoadtoSizeOn",
        cast=str,
    )
    _set_autosizable_if_present(
        sizing_system.setDesignOutdoorAirFlowRate,
        sizing_system.autosizeDesignOutdoorAirFlowRate,
        node,
        "DesignOutdoorAirFlowRate",
    )
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="sizing",
        openstudio_type="OS:Sizing:System",
        name=name,
    )


def _write_sizing_plant(
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    plant_loop_name = _referenced_node_name(
        graph,
        node,
        "PlantLoopIdentifier",
    )
    plant_loop = model.getPlantLoopByName(plant_loop_name).get()
    sizing_plant = plant_loop.sizingPlant()
    name = str(node.fields.get("Name") or f"{plant_loop_name} Sizing")
    sizing_plant.setName(name)
    _set_if_present(sizing_plant.setLoopType, node, "LoopType", cast=str)
    _set_if_present(
        sizing_plant.setDesignLoopExitTemperature,
        node,
        "DesignLoopExitTemperature",
    )
    _set_if_present(
        sizing_plant.setLoopDesignTemperatureDifference,
        node,
        "LoopDesignTemperatureDifference",
    )
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="sizing",
        openstudio_type="OS:Sizing:Plant",
        name=name,
    )
