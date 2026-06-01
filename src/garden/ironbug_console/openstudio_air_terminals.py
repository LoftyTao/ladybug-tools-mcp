"""Air terminal dispatcher for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_air_terminal_basic import (
    _new_air_terminal_constant_volume_no_reheat,
    _new_air_terminal_constant_volume_reheat,
    _new_air_terminal_inlet_side_mixer,
)
from garden.ironbug_console.openstudio_air_terminal_beams import (
    _new_air_terminal_constant_volume_cooled_beam,
    _new_air_terminal_constant_volume_four_pipe_beam,
    _new_air_terminal_constant_volume_four_pipe_induction,
)
from garden.ironbug_console.openstudio_air_terminal_piu import (
    _new_air_terminal_parallel_piu_reheat,
    _new_air_terminal_series_piu_reheat,
)
from garden.ironbug_console.openstudio_air_terminal_vav import (
    _new_air_terminal_vav_heat_and_cool_no_reheat,
    _new_air_terminal_vav_heat_and_cool_reheat,
    _new_air_terminal_vav_no_reheat,
    _new_air_terminal_vav_reheat,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)


def _new_air_terminal(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    if node.source_class == "IB_AirTerminalSingleDuctConstantVolumeNoReheat":
        return _new_air_terminal_constant_volume_no_reheat(
            openstudio,
            model,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctConstantVolumeReheat":
        return _new_air_terminal_constant_volume_reheat(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctConstantVolumeCooledBeam":
        return _new_air_terminal_constant_volume_cooled_beam(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam":
        return _new_air_terminal_constant_volume_four_pipe_beam(
            openstudio,
            model,
            graph,
            node,
        )
    if (
        node.source_class
        == "IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction"
    ):
        return _new_air_terminal_constant_volume_four_pipe_induction(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctInletSideMixer":
        return _new_air_terminal_inlet_side_mixer(
            openstudio,
            model,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctParallelPIUReheat":
        return _new_air_terminal_parallel_piu_reheat(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctSeriesPIUReheat":
        return _new_air_terminal_series_piu_reheat(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctVAVHeatAndCoolNoReheat":
        return _new_air_terminal_vav_heat_and_cool_no_reheat(
            openstudio,
            model,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctVAVHeatAndCoolReheat":
        return _new_air_terminal_vav_heat_and_cool_reheat(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctVAVNoReheat":
        return _new_air_terminal_vav_no_reheat(
            openstudio,
            model,
            node,
        )
    if node.source_class == "IB_AirTerminalSingleDuctVAVReheat":
        return _new_air_terminal_vav_reheat(
            openstudio,
            model,
            graph,
            node,
        )
    raise ValueError(f"Unsupported AirLoop terminal: {node.source_class}")
