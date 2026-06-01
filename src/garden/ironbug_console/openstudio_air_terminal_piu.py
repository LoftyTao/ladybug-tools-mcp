"""Powered induction unit AirTerminal writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import _new_reheat_coil
from garden.ironbug_console.openstudio_fans import _new_fan_constant_volume
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_air_terminal_parallel_piu_reheat(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_constant_volume(
        openstudio,
        model,
        child_nodes["IB_FanConstantVolume"],
    )
    reheat_coil, coil_summary = _new_reheat_coil(openstudio, model, child_nodes)
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctParallelPIUReheatByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setFan(fan)
        terminal.setReheatCoil(reheat_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctParallelPIUReheat(
            model,
            model.alwaysOnDiscreteSchedule(),
            fan,
            reheat_coil,
        )
        terminal.setName(name)
    _configure_piu_reheat_common(terminal, node)
    _set_autosizable_if_present(
        terminal.setMaximumSecondaryAirFlowRate,
        terminal.autosizeMaximumSecondaryAirFlowRate,
        node,
        "MaximumSecondaryAirFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setFanOnFlowFraction,
        terminal.autosizeFanOnFlowFraction,
        node,
        "FanOnFlowFraction",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:ParallelPIU:Reheat",
        name=name,
    )
    return terminal, (coil_summary, fan_summary, terminal_summary)


def _new_air_terminal_series_piu_reheat(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    fan, fan_summary = _new_fan_constant_volume(
        openstudio,
        model,
        child_nodes["IB_FanConstantVolume"],
    )
    reheat_coil, coil_summary = _new_reheat_coil(openstudio, model, child_nodes)
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctSeriesPIUReheatByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setFan(fan)
        terminal.setReheatCoil(reheat_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctSeriesPIUReheat(
            model,
            fan,
            reheat_coil,
        )
        terminal.setName(name)
    _configure_piu_reheat_common(terminal, node)
    _set_autosizable_if_present(
        terminal.setMaximumAirFlowRate,
        terminal.autosizeMaximumAirFlowRate,
        node,
        "MaximumAirFlowRate",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:SeriesPIU:Reheat",
        name=name,
    )
    return terminal, (coil_summary, fan_summary, terminal_summary)


def _configure_piu_reheat_common(terminal: Any, node: ConsoleGraphNode) -> None:
    _set_autosizable_if_present(
        terminal.setMaximumPrimaryAirFlowRate,
        terminal.autosizeMaximumPrimaryAirFlowRate,
        node,
        "MaximumPrimaryAirFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setMinimumPrimaryAirFlowFraction,
        terminal.autosizeMinimumPrimaryAirFlowFraction,
        node,
        "MinimumPrimaryAirFlowFraction",
    )
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
        terminal.setFanControlType,
        node,
        "FanControlType",
        cast=str,
    )
    _set_if_present(
        terminal.setMinimumFanTurnDownRatio,
        node,
        "MinimumFanTurnDownRatio",
    )
    _set_if_present(
        terminal.setHeatingControlType,
        node,
        "HeatingControlType",
        cast=str,
    )
    _set_if_present(
        terminal.setDesignHeatingDischargeAirTemperature,
        node,
        "DesignHeatingDischargeAirTemperature",
    )
    _set_if_present(
        terminal.setHighLimitHeatingDischargeAirTemperature,
        node,
        "HighLimitHeatingDischargeAirTemperature",
    )
