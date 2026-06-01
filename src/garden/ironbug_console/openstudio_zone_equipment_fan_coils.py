"""Fan coil ZoneHVAC writers for Python Ironbug Console."""

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


def _write_four_pipe_fan_coil(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_on_off(
        openstudio,
        model,
        child_nodes["IB_FanOnOff"],
    )
    cooling_coil, cooling_summary = _new_cooling_water(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingWater"],
    )
    heating_coil, heating_summary = _new_heating_water(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingWater"],
    )
    fan_coil = openstudio.model.ZoneHVACFourPipeFanCoil(
        model,
        model.alwaysOnDiscreteSchedule(),
        fan,
        cooling_coil,
        heating_coil,
    )
    fan_coil_name = str(node.fields.get("Name") or node.identifier)
    fan_coil.setName(fan_coil_name)
    _set_if_present(
        fan_coil.setCapacityControlMethod,
        node,
        "CapacityControlMethod",
        cast=str,
    )
    _set_autosizable_if_present(
        fan_coil.setMaximumSupplyAirFlowRate,
        fan_coil.autosizeMaximumSupplyAirFlowRate,
        node,
        "MaximumSupplyAirFlowRate",
    )
    _set_if_present(
        fan_coil.setLowSpeedSupplyAirFlowRatio,
        node,
        "LowSpeedSupplyAirFlowRatio",
    )
    _set_if_present(
        fan_coil.setMediumSpeedSupplyAirFlowRatio,
        node,
        "MediumSpeedSupplyAirFlowRatio",
    )
    _set_autosizable_if_present(
        fan_coil.setMaximumOutdoorAirFlowRate,
        fan_coil.autosizeMaximumOutdoorAirFlowRate,
        node,
        "MaximumOutdoorAirFlowRate",
    )
    _set_if_present(
        fan_coil.setOutdoorAirMixerObjectType,
        node,
        "OutdoorAirMixerObjectType",
        cast=str,
    )
    _set_autosizable_if_present(
        fan_coil.setMaximumColdWaterFlowRate,
        fan_coil.autosizeMaximumColdWaterFlowRate,
        node,
        "MaximumColdWaterFlowRate",
    )
    _set_if_present(
        fan_coil.setMinimumColdWaterFlowRate,
        node,
        "MinimumColdWaterFlowRate",
    )
    _set_if_present(
        fan_coil.setCoolingConvergenceTolerance,
        node,
        "CoolingConvergenceTolerance",
    )
    _set_autosizable_if_present(
        fan_coil.setMaximumHotWaterFlowRate,
        fan_coil.autosizeMaximumHotWaterFlowRate,
        node,
        "MaximumHotWaterFlowRate",
    )
    _set_if_present(
        fan_coil.setMinimumHotWaterFlowRate,
        node,
        "MinimumHotWaterFlowRate",
    )
    _set_if_present(
        fan_coil.setHeatingConvergenceTolerance,
        node,
        "HeatingConvergenceTolerance",
    )
    _set_autosizable_if_present(
        fan_coil.setMinimumSupplyAirTemperatureInCoolingMode,
        fan_coil.autosizeMinimumSupplyAirTemperatureInCoolingMode,
        node,
        "MinimumSupplyAirTemperatureInCoolingMode",
    )
    _set_autosizable_if_present(
        fan_coil.setMaximumSupplyAirTemperatureInHeatingMode,
        fan_coil.autosizeMaximumSupplyAirTemperatureInHeatingMode,
        node,
        "MaximumSupplyAirTemperatureInHeatingMode",
    )
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    fan_coil.addToThermalZone(zone)
    fan_coil_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:FourPipeFanCoil",
        name=fan_coil_name,
    )
    return (
        cooling_summary,
        heating_summary,
        fan_summary,
        fan_coil_summary,
    )
