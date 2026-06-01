"""OpenStudio beam coil factories for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_cooling_cooled_beam(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingCooledBeamByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingCooledBeam(model)
        coil.setName(name)
    _set_if_present(
        coil.setCoilSurfaceAreaperCoilLength,
        node,
        "CoilSurfaceAreaperCoilLength",
    )
    _set_if_present(coil.setModelParametera, node, "ModelParametera")
    _set_if_present(coil.setModelParametern1, node, "ModelParametern1")
    _set_if_present(coil.setModelParametern2, node, "ModelParametern2")
    _set_if_present(coil.setModelParametern3, node, "ModelParametern3")
    _set_if_present(coil.setModelParametera0, node, "ModelParametera0")
    _set_if_present(coil.setModelParameterK1, node, "ModelParameterK1")
    _set_if_present(coil.setModelParametern, node, "ModelParametern")
    _set_if_present(
        coil.setLeavingPipeInsideDiameter,
        node,
        "LeavingPipeInsideDiameter",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:CooledBeam",
        name=name,
    )


def _new_cooling_four_pipe_beam(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingFourPipeBeamByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingFourPipeBeam(model)
        coil.setName(name)
    _set_autosizable_if_present(
        coil.setBeamRatedCoolingCapacityperBeamLength,
        coil.resetBeamRatedCoolingCapacityperBeamLength,
        node,
        "BeamRatedCoolingCapacityperBeamLength",
    )
    _set_autosizable_if_present(
        coil.setBeamRatedCoolingRoomAirChilledWaterTemperatureDifference,
        coil.resetBeamRatedCoolingRoomAirChilledWaterTemperatureDifference,
        node,
        "BeamRatedCoolingRoomAirChilledWaterTemperatureDifference",
    )
    _set_autosizable_if_present(
        coil.setBeamRatedChilledWaterVolumeFlowRateperBeamLength,
        coil.resetBeamRatedChilledWaterVolumeFlowRateperBeamLength,
        node,
        "BeamRatedChilledWaterVolumeFlowRateperBeamLength",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:FourPipeBeam",
        name=name,
    )


def _new_heating_four_pipe_beam(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingFourPipeBeamByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingFourPipeBeam(model)
        coil.setName(name)
    _set_autosizable_if_present(
        coil.setBeamRatedHeatingCapacityperBeamLength,
        coil.resetBeamRatedHeatingCapacityperBeamLength,
        node,
        "BeamRatedHeatingCapacityperBeamLength",
    )
    _set_autosizable_if_present(
        coil.setBeamRatedHeatingRoomAirHotWaterTemperatureDifference,
        coil.resetBeamRatedHeatingRoomAirHotWaterTemperatureDifference,
        node,
        "BeamRatedHeatingRoomAirHotWaterTemperatureDifference",
    )
    _set_autosizable_if_present(
        coil.setBeamRatedHotWaterVolumeFlowRateperBeamLength,
        coil.resetBeamRatedHotWaterVolumeFlowRateperBeamLength,
        node,
        "BeamRatedHotWaterVolumeFlowRateperBeamLength",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:FourPipeBeam",
        name=name,
    )
