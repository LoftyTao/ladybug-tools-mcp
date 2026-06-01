"""OpenStudio AirLoopHVAC writers for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_air_terminals import _new_air_terminal
from garden.ironbug_console.openstudio_air_loop_components import (
    _new_air_loop_component,
)
from garden.ironbug_console.openstudio_source_classes import (
    SETPOINT_MANAGER_SOURCE_CLASSES as _SETPOINT_MANAGER_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
)
from garden.ironbug_console.openstudio_zone_equipment import (
    _ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES,
    _write_zone_hvac_equipment,
    _zone_hvac_component_by_node,
)


def _write_air_loop_hvac(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    context: OpenStudioWriterContext | None = None,
) -> tuple[OpenStudioWrittenObject, ...]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_loop = model.getAirLoopHVACByName(name)
    if optional_loop.is_initialized():
        air_loop = optional_loop.get()
    else:
        air_loop = openstudio.model.AirLoopHVAC(model)
        air_loop.setName(name)

    written_objects: list[OpenStudioWrittenObject] = []
    previous_supply_component: Any | None = None
    pending_mixed_air_managers: list[Any] = []
    for child_identifier in tuple(node.fields.get("SupplyComponentIdentifiers") or ()):
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_NodeProbe":
            _register_air_loop_node_probe(
                context,
                child,
                _air_component_outlet_node(
                    previous_supply_component,
                    fallback_node=air_loop.supplyInletNode(),
                ),
            )
            continue
        component, summaries = _new_air_loop_component(
            openstudio,
            model,
            child,
            graph,
            context,
        )
        _append_written(written_objects, summaries)
        if child.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
            if child.source_class == "IB_SetpointManagerMixedAir":
                pending_mixed_air_managers.append(component)
                continue
            component.addToNode(
                _air_component_outlet_node(
                    previous_supply_component,
                    fallback_node=air_loop.supplyOutletNode(),
                )
            )
            continue
        if not _air_component_already_on_loop(component):
            component.addToNode(air_loop.supplyOutletNode())
        _attach_pending_mixed_air_managers(
            pending_mixed_air_managers,
            _air_component_inlet_node(
                component,
                fallback_node=air_loop.supplyOutletNode(),
            ),
        )
        previous_supply_component = component
    _attach_pending_mixed_air_managers(
        pending_mixed_air_managers,
        _air_component_outlet_node(
            previous_supply_component,
            fallback_node=air_loop.supplyOutletNode(),
        ),
    )

    for child_identifier in tuple(node.fields.get("DemandComponentIdentifiers") or ()):
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_NodeProbe":
            _register_air_loop_node_probe(
                context,
                child,
                air_loop.demandInletNode(),
            )
            continue
        if child.source_class != "IB_AirLoopBranches":
            continue
        _append_written(
            written_objects,
            _add_air_loop_branches(openstudio, model, graph, air_loop, child),
        )

    air_loop_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loops",
        openstudio_type="OS:AirLoopHVAC",
        name=name,
    )
    return (*written_objects, air_loop_summary)


def _register_air_loop_node_probe(
    context: OpenStudioWriterContext | None,
    node: ConsoleGraphNode,
    openstudio_node: Any,
) -> None:
    if context is None:
        return
    context.register_node_probe(node.identifier, openstudio_node)


def _add_air_loop_branches(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    air_loop: Any,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    written_objects: list[OpenStudioWrittenObject] = []
    for branch_identifiers in node.fields.get("BranchComponentIdentifiers") or ():
        for child_identifier in branch_identifiers:
            child_node = graph.node_by_identifier(str(child_identifier))
            if child_node.source_class != "IB_ThermalZone":
                continue
            zone_name = str(child_node.fields.get("Name") or child_node.identifier)
            zone = model.getThermalZoneByName(zone_name).get()
            terminal_node = _air_terminal_node_for_zone(graph, child_node.identifier)
            zone_equipment_component = None
            zone_equipment_node = _inlet_side_mixer_zone_equipment_node(
                graph,
                terminal_node,
            )
            if zone_equipment_node is not None:
                _append_written(
                    written_objects,
                    _write_zone_hvac_equipment(
                        openstudio,
                        model,
                        graph,
                        zone_equipment_node,
                    ),
                )
                zone_equipment_component = _zone_hvac_component_by_node(
                    model,
                    zone_equipment_node,
                )
            terminal, terminal_summaries = _new_air_terminal(
                openstudio,
                model,
                graph,
                terminal_node,
            )
            _append_written(written_objects, terminal_summaries)
            if not _air_component_already_on_loop(terminal):
                air_loop.addBranchForZone(zone, terminal)
            if zone_equipment_component is not None:
                _connect_zone_hvac_child_to_terminal(
                    terminal,
                    zone_equipment_component,
                )

    branches_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_components",
        openstudio_type="OS:AirLoopHVAC:Branches",
        name=str(node.fields.get("Name") or node.identifier),
    )
    return (*written_objects, branches_summary)

def _air_component_already_on_loop(component: Any) -> bool:
    try:
        optional_loop = component.airLoopHVAC()
    except AttributeError:
        return False
    return bool(optional_loop.is_initialized())

def _air_component_outlet_node(component: Any, *, fallback_node: Any) -> Any:
    if component is None or not hasattr(component, "airOutletModelObject"):
        return fallback_node
    outlet = component.airOutletModelObject()
    if not outlet.is_initialized():
        return fallback_node
    node = outlet.get().to_Node()
    if not node.is_initialized():
        return fallback_node
    return node.get()


def _air_component_inlet_node(component: Any, *, fallback_node: Any) -> Any:
    if component is None:
        return fallback_node
    for method_name in ("airInletModelObject", "inletModelObject"):
        method = getattr(component, method_name, None)
        if method is None:
            continue
        inlet = method()
        if not inlet.is_initialized():
            continue
        node = inlet.get().to_Node()
        if node.is_initialized():
            return node.get()
    return fallback_node


def _attach_pending_mixed_air_managers(
    managers: list[Any],
    openstudio_node: Any,
) -> None:
    while managers:
        managers.pop(0).addToNode(openstudio_node)


def _air_terminal_node_for_zone(
    graph: ConsoleGraph,
    zone_identifier: str,
) -> ConsoleGraphNode:
    for node in graph.nodes:
        if not node.source_class.startswith("IB_AirTerminal"):
            continue
        if str(node.fields.get("ThermalZoneIdentifier")) == str(zone_identifier):
            return node
    raise KeyError(f"Missing AirTerminal for ThermalZone {zone_identifier}.")


def _inlet_side_mixer_zone_equipment_node(
    graph: ConsoleGraph,
    terminal_node: ConsoleGraphNode,
) -> ConsoleGraphNode | None:
    if terminal_node.source_class != "IB_AirTerminalSingleDuctInletSideMixer":
        return None
    for child_identifier in terminal_node.children:
        child_node = graph.node_by_identifier(str(child_identifier))
        if child_node.source_class in _ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES:
            return child_node
    return None


def _connect_zone_hvac_child_to_terminal(
    terminal: Any,
    zone_equipment_component: Any,
) -> None:
    secondary_node_method = getattr(terminal, "secondaryAirInletNode", None)
    if secondary_node_method is not None:
        secondary_node = secondary_node_method()
        if secondary_node.is_initialized():
            zone_equipment_component.addToNode(secondary_node.get())
            return
    outlet = terminal.outletModelObject()
    if not outlet.is_initialized():
        return
    optional_node = outlet.get().to_Node()
    if not optional_node.is_initialized():
        return
    zone_equipment_component.addToNode(optional_node.get())
