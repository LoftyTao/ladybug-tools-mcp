"""VAV AirTerminal writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_reheat_coil,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_air_terminal_vav_heat_and_cool_no_reheat(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = (
        model.getAirTerminalSingleDuctVAVHeatAndCoolNoReheatByName(name)
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
    else:
        terminal = openstudio.model.AirTerminalSingleDuctVAVHeatAndCoolNoReheat(
            model
        )
        terminal.setName(name)
    _configure_vav_heat_and_cool_common(terminal, node)
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:VAV:HeatAndCool:NoReheat",
        name=name,
    )
    return terminal, (terminal_summary,)


def _new_air_terminal_vav_heat_and_cool_reheat(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    reheat_coil, coil_summary = _new_reheat_coil(openstudio, model, child_nodes)
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctVAVHeatAndCoolReheatByName(
        name
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setReheatCoil(reheat_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctVAVHeatAndCoolReheat(
            model,
            reheat_coil,
        )
        terminal.setName(name)
    _configure_vav_heat_and_cool_common(terminal, node)
    _set_autosizable_if_present(
        terminal.setMaximumHotWaterorSteamFlowRate,
        terminal.autosizeMaximumHotWaterorSteamFlowRate,
        node,
        "MaximumHotWaterorSteamFlowRate",
    )
    _set_if_present(
        terminal.setMinimumHotWaterorSteamFlowRate,
        node,
        "MinimumHotWaterorSteamFlowRate",
    )
    _set_if_present(
        terminal.setConvergenceTolerance,
        node,
        "ConvergenceTolerance",
    )
    _set_if_present(
        terminal.setMaximumReheatAirTemperature,
        node,
        "MaximumReheatAirTemperature",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:VAV:HeatAndCool:Reheat",
        name=name,
    )
    return terminal, (coil_summary, terminal_summary)


def _new_air_terminal_vav_no_reheat(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctVAVNoReheatByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
    else:
        terminal = openstudio.model.AirTerminalSingleDuctVAVNoReheat(
            model,
            model.alwaysOnDiscreteSchedule(),
        )
        terminal.setName(name)
    _configure_vav_terminal_common(terminal, node)
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:VAV:NoReheat",
        name=name,
    )
    return terminal, (terminal_summary,)


def _new_air_terminal_vav_reheat(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    reheat_coil, coil_summary = _new_reheat_coil(openstudio, model, child_nodes)
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctVAVReheatByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setReheatCoil(reheat_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctVAVReheat(
            model,
            model.alwaysOnDiscreteSchedule(),
            reheat_coil,
        )
        terminal.setName(name)
    _configure_vav_terminal_common(terminal, node)
    _set_autosizable_if_present(
        terminal.setMaximumHotWaterOrSteamFlowRate,
        terminal.autosizeMaximumHotWaterOrSteamFlowRate,
        node,
        "MaximumHotWaterOrSteamFlowRate",
    )
    _set_if_present(
        terminal.setMinimumHotWaterOrStreamFlowRate,
        node,
        "MinimumHotWaterOrStreamFlowRate",
    )
    _set_if_present(
        terminal.setConvergenceTolerance,
        node,
        "ConvergenceTolerance",
    )
    _set_if_present(
        terminal.setDamperHeatingAction,
        node,
        "DamperHeatingAction",
        cast=str,
    )
    _set_autosizable_if_present(
        terminal.setMaximumFlowPerZoneFloorAreaDuringReheat,
        terminal.autosizeMaximumFlowPerZoneFloorAreaDuringReheat,
        node,
        "MaximumFlowPerZoneFloorAreaDuringReheat",
    )
    _set_autosizable_if_present(
        terminal.setMaximumFlowFractionDuringReheat,
        terminal.autosizeMaximumFlowFractionDuringReheat,
        node,
        "MaximumFlowFractionDuringReheat",
    )
    _set_if_present(
        terminal.setMaximumReheatAirTemperature,
        node,
        "MaximumReheatAirTemperature",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:VAV:Reheat",
        name=name,
    )
    return terminal, (coil_summary, terminal_summary)


def _configure_vav_terminal_common(terminal: Any, node: ConsoleGraphNode) -> None:
    _set_autosizable_if_present(
        terminal.setMaximumAirFlowRate,
        terminal.autosizeMaximumAirFlowRate,
        node,
        "MaximumAirFlowRate",
    )
    _set_if_present(
        terminal.setZoneMinimumAirFlowInputMethod,
        node,
        "ZoneMinimumAirFlowInputMethod",
        cast=str,
    )
    if hasattr(terminal, "setZoneMinimumAirFlowMethod"):
        _set_if_present(
            terminal.setZoneMinimumAirFlowMethod,
            node,
            "ZoneMinimumAirFlowMethod",
            cast=str,
        )
    _set_autosizable_if_present(
        terminal.setConstantMinimumAirFlowFraction,
        terminal.autosizeConstantMinimumAirFlowFraction,
        node,
        "ConstantMinimumAirFlowFraction",
    )
    _set_autosizable_if_present(
        terminal.setFixedMinimumAirFlowRate,
        terminal.autosizeFixedMinimumAirFlowRate,
        node,
        "FixedMinimumAirFlowRate",
    )
    _set_if_present(
        terminal.setControlForOutdoorAir,
        node,
        "ControlForOutdoorAir",
    )


def _configure_vav_heat_and_cool_common(
    terminal: Any,
    node: ConsoleGraphNode,
) -> None:
    _set_autosizable_if_present(
        terminal.setMaximumAirFlowRate,
        terminal.autosizeMaximumAirFlowRate,
        node,
        "MaximumAirFlowRate",
    )
    _set_if_present(
        terminal.setZoneMinimumAirFlowFraction,
        node,
        "ZoneMinimumAirFlowFraction",
    )
