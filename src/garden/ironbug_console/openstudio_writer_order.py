"""OpenStudio writer ordering for Python Ironbug Console graphs."""

from __future__ import annotations

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_curves import _CURVE_SPECS


def _writer_order(graph: ConsoleGraph) -> tuple[ConsoleGraphNode, ...]:
    thermal_zones = [
        node for node in graph.nodes if node.source_class == "IB_ThermalZone"
    ]
    schedule_type_limits = [
        node for node in graph.nodes if node.source_class == "IB_ScheduleTypeLimits"
    ]
    schedule_days = [
        node for node in graph.nodes if node.source_class == "IB_ScheduleDay"
    ]
    schedule_rulesets = [
        node for node in graph.nodes if node.source_class == "IB_ScheduleRuleset"
    ]
    schedule_files = [
        node for node in graph.nodes if node.source_class == "IB_ScheduleFile"
    ]
    curves = [
        node for node in graph.nodes if node.source_class in _CURVE_SPECS
    ]
    sizing_zones = [
        node for node in graph.nodes if node.source_class == "IB_SizingZone"
    ]
    air_loops = [
        node for node in graph.nodes if node.source_class == "IB_AirLoopHVAC"
    ]
    sizing_systems = [
        node for node in graph.nodes if node.source_class == "IB_SizingSystem"
    ]
    terminal_equipment = [
        node
        for node in graph.nodes
        if node.source_class
        in {
            "IB_ZoneHVACPackagedTerminalAirConditioner",
            "IB_ZoneHVACPackagedTerminalHeatPump",
            "IB_ZoneHVACFourPipeFanCoil",
            "IB_ZoneHVACWaterToAirHeatPump",
            "IB_ZoneHVACBaseboardRadiantConvectiveWater",
            "IB_ZoneHVACUnitHeater",
            "IB_ZoneHVACUnitVentilator_CoolingHeating",
            "IB_ZoneHVACUnitVentilator_CoolingOnly",
            "IB_ZoneHVACUnitVentilator_HeatingOnly",
        }
    ]
    plant_loops = [
        node for node in graph.nodes if node.source_class == "IB_PlantLoop"
    ]
    sizing_plants = [
        node for node in graph.nodes if node.source_class == "IB_SizingPlant"
    ]
    energy_management_system_programs = [
        node
        for node in graph.nodes
        if node.source_class == "IB_EnergyManagementSystemProgram"
    ]
    energy_management_system_metered_outputs = [
        node
        for node in graph.nodes
        if node.source_class == "IB_EnergyManagementSystemMeteredOutputVariable"
    ]
    energy_management_system_containers = [
        node for node in graph.nodes if node.source_class == "IB_EnergyManagementSystem"
    ]
    energy_management_systems = [
        node
        for node in graph.nodes
        if node.source_class.startswith("IB_EnergyManagementSystem")
        and node.source_class
        not in {
            "IB_EnergyManagementSystem",
            "IB_EnergyManagementSystemProgram",
            "IB_EnergyManagementSystemMeteredOutputVariable",
        }
    ]
    others = [
        node
        for node in graph.nodes
        if node.source_class
        not in {
            "IB_ThermalZone",
            "IB_ScheduleDay",
            "IB_ScheduleFile",
            "IB_ScheduleRuleset",
            "IB_ScheduleRule",
            "IB_ScheduleTypeLimits",
            "IB_SizingZone",
            "IB_SizingSystem",
            "IB_SizingPlant",
            "IB_AirLoopHVAC",
            "IB_ZoneHVACPackagedTerminalAirConditioner",
            "IB_ZoneHVACPackagedTerminalHeatPump",
            "IB_ZoneHVACFourPipeFanCoil",
            "IB_ZoneHVACWaterToAirHeatPump",
            "IB_ZoneHVACBaseboardRadiantConvectiveWater",
            "IB_ZoneHVACUnitHeater",
            "IB_ZoneHVACUnitVentilator_CoolingHeating",
            "IB_ZoneHVACUnitVentilator_CoolingOnly",
            "IB_ZoneHVACUnitVentilator_HeatingOnly",
            "IB_PlantLoop",
            *_CURVE_SPECS,
        }
        and not node.source_class.startswith("IB_EnergyManagementSystem")
    ]
    return tuple(
        [
            *thermal_zones,
            *schedule_type_limits,
            *schedule_days,
            *schedule_rulesets,
            *schedule_files,
            *curves,
            *others,
            *sizing_zones,
            *air_loops,
            *plant_loops,
            *sizing_systems,
            *sizing_plants,
            *terminal_equipment,
            *energy_management_system_programs,
            *energy_management_systems,
            *energy_management_system_metered_outputs,
            *energy_management_system_containers,
        ]
    )
