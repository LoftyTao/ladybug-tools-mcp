"""OpenStudio VRF writers for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_dx import (
    _new_cooling_dx_variable_refrigerant_flow,
    _new_heating_dx_variable_refrigerant_flow,
)
from garden.ironbug_console.openstudio_fans import _new_fan_on_off
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
    _child_nodes_by_source_class,
    _has_node,
    _set_autosizable_if_present,
    _set_if_present,
    _thermal_zone_name_for_field_reference,
)


def _write_vrf_system(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    written_objects: list[OpenStudioWrittenObject] = []
    terminal_nodes = _vrf_terminal_nodes(graph, node)
    first_zone = None
    terminals = []
    for terminal_node in terminal_nodes:
        terminal, summaries, zone = _new_vrf_terminal(
            openstudio,
            model,
            graph,
            terminal_node,
        )
        _append_written(written_objects, summaries)
        terminals.append(terminal)
        if first_zone is None:
            first_zone = zone

    name = str(node.fields.get("Name") or node.identifier)
    optional_vrf = model.getAirConditionerVariableRefrigerantFlowByName(name)
    if optional_vrf.is_initialized():
        vrf = optional_vrf.get()
    else:
        vrf = openstudio.model.AirConditionerVariableRefrigerantFlow(model)
        vrf.setName(name)
    if hasattr(vrf, "removeAllTerminals"):
        vrf.removeAllTerminals()
    for terminal in terminals:
        vrf.addTerminal(terminal)
    if first_zone is not None:
        vrf.setZoneforMasterThermostatLocation(first_zone)
    _configure_vrf_system(vrf, model, node)
    vrf_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="vrf",
        openstudio_type="OS:AirConditioner:VariableRefrigerantFlow",
        name=name,
    )
    return (*written_objects, vrf_summary)

def _new_vrf_terminal(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...], Any]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_coil, cooling_summary = _new_cooling_dx_variable_refrigerant_flow(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingDXVariableRefrigerantFlow"],
    )
    heating_coil, heating_summary = _new_heating_dx_variable_refrigerant_flow(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingDXVariableRefrigerantFlow"],
    )
    fan, fan_summary = _new_fan_on_off(
        openstudio,
        model,
        child_nodes["IB_FanOnOff"],
    )

    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getZoneHVACTerminalUnitVariableRefrigerantFlowByName(
        name
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setCoolingCoil(cooling_coil)
        terminal.setHeatingCoil(heating_coil)
    else:
        terminal = openstudio.model.ZoneHVACTerminalUnitVariableRefrigerantFlow(
            model,
            cooling_coil,
            heating_coil,
            fan,
        )
        terminal.setName(name)
    terminal.setTerminalUnitAvailabilityschedule(model.alwaysOnDiscreteSchedule())
    terminal.setSupplyAirFanOperatingModeSchedule(model.alwaysOffDiscreteSchedule())
    _configure_vrf_terminal(terminal, node)
    zone_name = _thermal_zone_name_for_field_reference(graph, node)
    zone = model.getThermalZoneByName(zone_name).get()
    terminal.addToThermalZone(zone)
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_zone_equipment",
        openstudio_type="OS:ZoneHVAC:TerminalUnit:VariableRefrigerantFlow",
        name=name,
    )
    return (
        terminal,
        (
            cooling_summary,
            heating_summary,
            fan_summary,
            terminal_summary,
        ),
        zone,
    )

def _configure_vrf_system(vrf: Any, model: Any, node: ConsoleGraphNode) -> None:
    cooling_cop = node.fields.get("RatedCoolingCOP")
    if cooling_cop is not None:
        cooling_cop = float(cooling_cop)
        vrf.setRatedCoolingCOP(cooling_cop)
        if node.fields.get("GrossRatedCoolingCOP") is None:
            vrf.setGrossRatedCoolingCOP(cooling_cop)
    _set_if_present(vrf.setGrossRatedCoolingCOP, node, "GrossRatedCoolingCOP")
    _set_if_present(vrf.setRatedHeatingCOP, node, "RatedHeatingCOP")
    _set_autosizable_if_present(
        vrf.setGrossRatedTotalCoolingCapacity,
        lambda: None,
        node,
        "GrossRatedTotalCoolingCapacity",
    )
    _set_autosizable_if_present(
        vrf.setRatedTotalCoolingCapacity,
        lambda: None,
        node,
        "RatedTotalCoolingCapacity",
    )
    _set_autosizable_if_present(
        vrf.setGrossRatedHeatingCapacity,
        vrf.autosizeGrossRatedHeatingCapacity,
        node,
        "GrossRatedHeatingCapacity",
    )
    _set_autosizable_if_present(
        vrf.setRatedTotalHeatingCapacity,
        lambda: None,
        node,
        "RatedTotalHeatingCapacity",
    )
    _set_if_present(
        vrf.setRatedHeatingCapacitySizingRatio,
        node,
        "RatedHeatingCapacitySizingRatio",
    )
    _set_if_present(
        vrf.setRatedTotalHeatingCapacitySizingRatio,
        node,
        "RatedTotalHeatingCapacitySizingRatio",
    )
    _set_if_present(
        vrf.setMinimumOutdoorTemperatureinCoolingMode,
        node,
        "MinimumOutdoorTemperatureinCoolingMode",
    )
    _set_if_present(
        vrf.setMaximumOutdoorTemperatureinCoolingMode,
        node,
        "MaximumOutdoorTemperatureinCoolingMode",
    )
    _set_if_present(
        vrf.setMinimumOutdoorTemperatureinHeatingMode,
        node,
        "MinimumOutdoorTemperatureinHeatingMode",
    )
    _set_if_present(
        vrf.setMaximumOutdoorTemperatureinHeatingMode,
        node,
        "MaximumOutdoorTemperatureinHeatingMode",
    )
    _set_if_present(vrf.setCondenserType, node, "CondenserType", cast=str)
    _set_if_present(vrf.setDefrostStrategy, node, "DefrostStrategy", cast=str)
    _set_if_present(vrf.setDefrostControl, node, "DefrostControl", cast=str)
    _set_if_present(vrf.setFuelType, node, "FuelType", cast=str)
    minimum_part_load = node.fields.get("MinimumHeatPumpPartLoadRatio")
    vrf.setMinimumHeatPumpPartLoadRatio(
        float(minimum_part_load if minimum_part_load is not None else 0.5)
    )
    priority_control = str(
        node.fields.get("MasterThermostatPriorityControlType") or "LoadPriority"
    )
    vrf.setMasterThermostatPriorityControlType(priority_control)
    if "AvailabilitySchedule" not in node.fields and hasattr(
        vrf,
        "setAvailabilitySchedule",
    ):
        vrf.setAvailabilitySchedule(model.alwaysOnDiscreteSchedule())

def _configure_vrf_terminal(terminal: Any, node: ConsoleGraphNode) -> None:
    _set_autosizable_if_present(
        terminal.setSupplyAirFlowRateDuringCoolingOperation,
        terminal.autosizeSupplyAirFlowRateDuringCoolingOperation,
        node,
        "SupplyAirFlowRateDuringCoolingOperation",
    )
    _set_autosizable_if_present(
        terminal.setSupplyAirFlowRateDuringHeatingOperation,
        terminal.autosizeSupplyAirFlowRateDuringHeatingOperation,
        node,
        "SupplyAirFlowRateDuringHeatingOperation",
    )
    _set_autosizable_if_present(
        terminal.setSupplyAirFlowRateWhenNoCoolingisNeeded,
        terminal.autosizeSupplyAirFlowRateWhenNoCoolingisNeeded,
        node,
        "SupplyAirFlowRateWhenNoCoolingisNeeded",
    )
    _set_autosizable_if_present(
        terminal.setSupplyAirFlowRateWhenNoHeatingisNeeded,
        terminal.autosizeSupplyAirFlowRateWhenNoHeatingisNeeded,
        node,
        "SupplyAirFlowRateWhenNoHeatingisNeeded",
    )
    _set_autosizable_if_present(
        terminal.setOutdoorAirFlowRateDuringCoolingOperation,
        terminal.autosizeOutdoorAirFlowRateDuringCoolingOperation,
        node,
        "OutdoorAirFlowRateDuringCoolingOperation",
    )
    _set_autosizable_if_present(
        terminal.setOutdoorAirFlowRateDuringHeatingOperation,
        terminal.autosizeOutdoorAirFlowRateDuringHeatingOperation,
        node,
        "OutdoorAirFlowRateDuringHeatingOperation",
    )
    _set_autosizable_if_present(
        terminal.setOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded,
        terminal.autosizeOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded,
        node,
        "OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded",
    )
    _set_if_present(
        terminal.setSupplyAirFanPlacement,
        node,
        "SupplyAirFanPlacement",
        cast=str,
    )
    _set_if_present(
        terminal.setZoneTerminalUnitOnParasiticElectricEnergyUse,
        node,
        "ZoneTerminalUnitOnParasiticElectricEnergyUse",
    )
    _set_if_present(
        terminal.setZoneTerminalUnitOffParasiticElectricEnergyUse,
        node,
        "ZoneTerminalUnitOffParasiticElectricEnergyUse",
    )

def _vrf_terminal_identifiers(node: ConsoleGraphNode) -> tuple[str, ...]:
    identifiers = node.fields.get("TerminalIdentifiers") or node.children
    return tuple(str(identifier) for identifier in identifiers)

def _vrf_terminal_nodes(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[ConsoleGraphNode, ...]:
    return tuple(
        graph.node_by_identifier(identifier)
        for identifier in _vrf_terminal_identifiers(node)
        if (
            _has_node(graph, identifier)
            and graph.node_by_identifier(identifier).source_class
            == "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow"
        )
    )
