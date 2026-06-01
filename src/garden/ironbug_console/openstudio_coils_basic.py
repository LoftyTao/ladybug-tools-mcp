"""OpenStudio basic and water coil factories for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any, Mapping

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)

from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_heating_electric(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingElectricByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingElectric(model)
        coil.setName(name)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:Electric",
        name=name,
    )


def _new_cooling_water(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingWaterByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingWater(model)
        coil.setName(name)
    _set_autosizable_if_present(
        coil.setDesignWaterFlowRate,
        coil.autosizeDesignWaterFlowRate,
        node,
        "DesignWaterFlowRate",
    )
    _set_autosizable_if_present(
        coil.setDesignAirFlowRate,
        coil.autosizeDesignAirFlowRate,
        node,
        "DesignAirFlowRate",
    )
    _set_autosizable_if_present(
        coil.setDesignInletWaterTemperature,
        coil.autosizeDesignInletWaterTemperature,
        node,
        "DesignInletWaterTemperature",
    )
    _set_autosizable_if_present(
        coil.setDesignInletAirTemperature,
        coil.autosizeDesignInletAirTemperature,
        node,
        "DesignInletAirTemperature",
    )
    _set_autosizable_if_present(
        coil.setDesignOutletAirTemperature,
        coil.autosizeDesignOutletAirTemperature,
        node,
        "DesignOutletAirTemperature",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:Water",
        name=name,
    )


def _new_heating_water(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingWaterByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingWater(model)
        coil.setName(name)
    _set_autosizable_if_present(
        coil.setMaximumWaterFlowRate,
        coil.autosizeMaximumWaterFlowRate,
        node,
        "MaximumWaterFlowRate",
    )
    _set_autosizable_if_present(
        coil.setUFactorTimesAreaValue,
        coil.autosizeUFactorTimesAreaValue,
        node,
        "UFactorTimesAreaValue",
    )
    _set_if_present(
        coil.setRatedInletWaterTemperature,
        node,
        "RatedInletWaterTemperature",
    )
    _set_if_present(
        coil.setRatedOutletWaterTemperature,
        node,
        "RatedOutletWaterTemperature",
    )
    _set_if_present(
        coil.setRatedInletAirTemperature,
        node,
        "RatedInletAirTemperature",
    )
    _set_if_present(
        coil.setRatedOutletAirTemperature,
        node,
        "RatedOutletAirTemperature",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:Water",
        name=name,
    )


def _new_heating_water_baseboard(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingWaterBaseboardByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingWaterBaseboard(model)
        coil.setName(name)
    _set_if_present(
        coil.setHeatingDesignCapacityMethod,
        node,
        "HeatingDesignCapacityMethod",
        cast=str,
    )
    _set_autosizable_if_present(
        coil.setHeatingDesignCapacity,
        coil.autosizeHeatingDesignCapacity,
        node,
        "HeatingDesignCapacity",
    )
    _set_if_present(
        coil.setHeatingDesignCapacityPerFloorArea,
        node,
        "HeatingDesignCapacityPerFloorArea",
    )
    _set_if_present(
        coil.setFractionofAutosizedHeatingDesignCapacity,
        node,
        "FractionofAutosizedHeatingDesignCapacity",
    )
    _set_autosizable_if_present(
        coil.setUFactorTimesAreaValue,
        coil.autosizeUFactorTimesAreaValue,
        node,
        "UFactorTimesAreaValue",
    )
    _set_autosizable_if_present(
        coil.setMaximumWaterFlowRate,
        coil.autosizeMaximumWaterFlowRate,
        node,
        "MaximumWaterFlowRate",
    )
    _set_if_present(coil.setConvergenceTolerance, node, "ConvergenceTolerance")
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:Water:Baseboard",
        name=name,
    )

def _new_heating_water_baseboard_radiant(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingWaterBaseboardRadiantByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingWaterBaseboardRadiant(model)
        coil.setName(name)
    _set_if_present(
        coil.setRatedAverageWaterTemperature,
        node,
        "RatedAverageWaterTemperature",
    )
    _set_if_present(coil.setRatedWaterMassFlowRate, node, "RatedWaterMassFlowRate")
    _set_if_present(
        coil.setHeatingDesignCapacityMethod,
        node,
        "HeatingDesignCapacityMethod",
        cast=str,
    )
    _set_autosizable_if_present(
        coil.setHeatingDesignCapacity,
        coil.autosizeHeatingDesignCapacity,
        node,
        "HeatingDesignCapacity",
    )
    _set_if_present(
        coil.setHeatingDesignCapacityPerFloorArea,
        node,
        "HeatingDesignCapacityPerFloorArea",
    )
    _set_if_present(
        coil.setFractionofAutosizedHeatingDesignCapacity,
        node,
        "FractionofAutosizedHeatingDesignCapacity",
    )
    _set_autosizable_if_present(
        coil.setMaximumWaterFlowRate,
        coil.autosizeMaximumWaterFlowRate,
        node,
        "MaximumWaterFlowRate",
    )
    _set_if_present(coil.setConvergenceTolerance, node, "ConvergenceTolerance")
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:Water:Baseboard:Radiant",
        name=name,
    )


def _apply_water_coil_controller_child(
    controller: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> None:
    controller_node = _water_coil_controller_child(graph, node)
    if controller_node is None:
        return
    if controller_node.fields.get("Name"):
        controller.setName(str(controller_node.fields["Name"]))
    _apply_generic_openstudio_fields(controller, controller_node)


def _water_coil_controller_child(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> ConsoleGraphNode | None:
    for child_identifier in node.children:
        try:
            child = graph.node_by_identifier(str(child_identifier))
        except KeyError:
            continue
        if child.source_class == "IB_ControllerWaterCoil":
            return child
    return None


def _new_reheat_coil(
    openstudio: Any,
    model: Any,
    child_nodes: Mapping[str, ConsoleGraphNode],
) -> tuple[Any, OpenStudioWrittenObject]:
    if "IB_CoilHeatingWater" in child_nodes:
        return _new_heating_water(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingWater"],
        )
    return _new_heating_electric(
        openstudio,
        model,
        child_nodes["IB_CoilHeatingElectric"],
    )
