"""Beam and induction AirTerminal writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_cooling_water,
    _new_heating_water,
)
from garden.ironbug_console.openstudio_coils_beams import (
    _new_cooling_cooled_beam,
    _new_cooling_four_pipe_beam,
    _new_heating_four_pipe_beam,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _set_if_present,
    _set_int_autosizable_if_present,
)


def _new_air_terminal_constant_volume_cooled_beam(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_coil, cooling_summary = _new_cooling_cooled_beam(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingCooledBeam"],
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctConstantVolumeCooledBeamByName(
        name
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setCoolingCoil(cooling_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctConstantVolumeCooledBeam(
            model,
            model.alwaysOnDiscreteSchedule(),
            cooling_coil,
        )
        terminal.setName(name)
    _set_if_present(terminal.setCooledBeamType, node, "CooledBeamType", cast=str)
    _set_autosizable_if_present(
        terminal.setSupplyAirVolumetricFlowRate,
        terminal.autosizeSupplyAirVolumetricFlowRate,
        node,
        "SupplyAirVolumetricFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setMaximumTotalChilledWaterVolumetricFlowRate,
        terminal.autosizeMaximumTotalChilledWaterVolumetricFlowRate,
        node,
        "MaximumTotalChilledWaterVolumetricFlowRate",
    )
    _set_int_autosizable_if_present(
        terminal.setNumberofBeams,
        terminal.autosizeNumberofBeams,
        node,
        "NumberofBeams",
    )
    _set_autosizable_if_present(
        terminal.setBeamLength,
        terminal.autosizeBeamLength,
        node,
        "BeamLength",
    )
    _set_if_present(
        terminal.setDesignInletWaterTemperature,
        node,
        "DesignInletWaterTemperature",
    )
    _set_if_present(
        terminal.setDesignOutletWaterTemperature,
        node,
        "DesignOutletWaterTemperature",
    )
    _set_if_present(
        terminal.setCoefficientofInductionKin,
        node,
        "CoefficientofInductionKin",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:ConstantVolume:CooledBeam",
        name=name,
    )
    return terminal, (cooling_summary, terminal_summary)


def _new_air_terminal_constant_volume_four_pipe_beam(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_coil, cooling_summary = _new_cooling_four_pipe_beam(
        openstudio,
        model,
        child_nodes["IB_CoilCoolingFourPipeBeam"],
    )
    heating_coil, heating_summary = _new_heating_four_pipe_beam(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingFourPipeBeam"],
    )
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = model.getAirTerminalSingleDuctConstantVolumeFourPipeBeamByName(
        name
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setCoolingCoil(cooling_coil)
        terminal.setHeatingCoil(heating_coil)
    else:
        terminal = openstudio.model.AirTerminalSingleDuctConstantVolumeFourPipeBeam(
            model,
            cooling_coil,
            heating_coil,
        )
        terminal.setName(name)
    _set_autosizable_if_present(
        terminal.setDesignPrimaryAirVolumeFlowRate,
        terminal.autosizeDesignPrimaryAirVolumeFlowRate,
        node,
        "DesignPrimaryAirVolumeFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setDesignChilledWaterVolumeFlowRate,
        terminal.autosizeDesignChilledWaterVolumeFlowRate,
        node,
        "DesignChilledWaterVolumeFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setDesignHotWaterVolumeFlowRate,
        terminal.autosizeDesignHotWaterVolumeFlowRate,
        node,
        "DesignHotWaterVolumeFlowRate",
    )
    _set_autosizable_if_present(
        terminal.setZoneTotalBeamLength,
        terminal.autosizeZoneTotalBeamLength,
        node,
        "ZoneTotalBeamLength",
    )
    _set_if_present(
        terminal.setRatedPrimaryAirFlowRateperBeamLength,
        node,
        "RatedPrimaryAirFlowRateperBeamLength",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type="OS:AirTerminal:SingleDuct:ConstantVolume:FourPipeBeam",
        name=name,
    )
    return terminal, (cooling_summary, heating_summary, terminal_summary)


def _new_air_terminal_constant_volume_four_pipe_induction(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    heating_coil, heating_summary = _new_heating_water(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingWater"],
    )
    written_objects: list[OpenStudioWrittenObject] = [heating_summary]
    cooling_coil = None
    if "IB_CoilCoolingWater" in child_nodes:
        cooling_coil, cooling_summary = _new_cooling_water(
            openstudio,
            model,
            child_nodes["IB_CoilCoolingWater"],
        )
        written_objects.append(cooling_summary)
    name = str(node.fields.get("Name") or node.identifier)
    optional_terminal = (
        model.getAirTerminalSingleDuctConstantVolumeFourPipeInductionByName(name)
    )
    if optional_terminal.is_initialized():
        terminal = optional_terminal.get()
        terminal.setHeatingCoil(heating_coil)
    else:
        terminal = (
            openstudio.model.AirTerminalSingleDuctConstantVolumeFourPipeInduction(
                model,
                heating_coil,
            )
        )
        terminal.setName(name)
    if cooling_coil is not None:
        terminal.setCoolingCoil(cooling_coil)
    _set_autosizable_if_present(
        terminal.setMaximumTotalAirFlowRate,
        terminal.autosizeMaximumTotalAirFlowRate,
        node,
        "MaximumTotalAirFlowRate",
    )
    _set_if_present(terminal.setInductionRatio, node, "InductionRatio")
    _set_autosizable_if_present(
        terminal.setMaximumHotWaterFlowRate,
        terminal.autosizeMaximumHotWaterFlowRate,
        node,
        "MaximumHotWaterFlowRate",
    )
    _set_if_present(terminal.setMinimumHotWaterFlowRate, node, "MinimumHotWaterFlowRate")
    _set_if_present(
        terminal.setHeatingConvergenceTolerance,
        node,
        "HeatingConvergenceTolerance",
    )
    _set_autosizable_if_present(
        terminal.setMaximumColdWaterFlowRate,
        terminal.autosizeMaximumColdWaterFlowRate,
        node,
        "MaximumColdWaterFlowRate",
    )
    _set_if_present(
        terminal.setMinimumColdWaterFlowRate,
        node,
        "MinimumColdWaterFlowRate",
    )
    _set_if_present(
        terminal.setCoolingConvergenceTolerance,
        node,
        "CoolingConvergenceTolerance",
    )
    terminal_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_terminals",
        openstudio_type=(
            "OS:AirTerminal:SingleDuct:ConstantVolume:FourPipeInduction"
        ),
        name=name,
    )
    written_objects.append(terminal_summary)
    return terminal, tuple(written_objects)
