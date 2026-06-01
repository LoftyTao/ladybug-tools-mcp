"""Basic constant-volume AirTerminal writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_heating_electric,
    _new_heating_water,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _coerce_bool,
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_air_terminal_constant_volume_no_reheat(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctConstantVolumeNoReheatByName(
        name
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
    else:
        terminal = openstudio.model.AirTerminalSingleDuctConstantVolumeNoReheat(
            model,
            model.alwaysOnDiscreteSchedule(),
        )
        terminal.setName(name)
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
        openstudio_type="OS:AirTerminal:SingleDuct:ConstantVolume:NoReheat",
        name=name,
    )
    return terminal, (terminal_summary,)


def _new_air_terminal_constant_volume_reheat(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    if "IB_CoilHeatingWater" in child_nodes:
        reheat_coil, coil_summary = _new_heating_water(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingWater"],
        )
    else:
        reheat_coil, coil_summary = _new_heating_electric(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingElectric"],
        )

    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctConstantVolumeReheatByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setReheatCoil(reheat_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctConstantVolumeReheat(
            model,
            model.alwaysOnDiscreteSchedule(),
            reheat_coil,
        )
        terminal.setName(name)
    _set_autosizable_if_present(
        terminal.setMaximumAirFlowRate,
        terminal.autosizeMaximumAirFlowRate,
        node,
        "MaximumAirFlowRate",
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
        terminal.setMaximumReheatAirTemperature,
        node,
        "MaximumReheatAirTemperature",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:ConstantVolume:Reheat",
        name=name,
    )
    return terminal, (coil_summary, terminal_summary)


def _new_air_terminal_inlet_side_mixer(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctInletSideMixerByName(name)
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
    else:
        terminal = openstudio.model.AirTerminalSingleDuctInletSideMixer(model)
        terminal.setName(name)
    _set_if_present(
        terminal.setControlForOutdoorAir,
        node,
        "ControlForOutdoorAir",
        cast=_coerce_bool,
    )
    _set_if_present(
        terminal.setPerPersonVentilationRateMode,
        node,
        "PerPersonVentilationRateMode",
        cast=str,
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:InletSideMixer",
        name=name,
    )
    return terminal, (terminal_summary,)
