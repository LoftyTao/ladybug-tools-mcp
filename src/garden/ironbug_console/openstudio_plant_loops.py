"""OpenStudio PlantLoop writers for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _apply_water_coil_controller_child,
)
from garden.ironbug_console.openstudio_plant_components import _new_plant_component
from garden.ironbug_console.openstudio_source_classes import (
    SETPOINT_MANAGER_SOURCE_CLASSES as _SETPOINT_MANAGER_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
    _is_autosize,
    _source_classes_for_identifiers,
)


def _write_plant_loop(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    context: OpenStudioWriterContext | None = None,
) -> tuple[OpenStudioWrittenObject, ...]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_loop = model.getPlantLoopByName(name)
    if optional_loop.is_initialized():
        plant_loop = optional_loop.get()
    else:
        plant_loop = openstudio.model.PlantLoop(model)
        plant_loop.setName(name)

    written_objects: list[OpenStudioWrittenObject] = []
    setpoint_values: list[float] = []
    supply_identifiers = tuple(node.fields.get("SupplyComponentIdentifiers") or ())
    demand_identifiers = tuple(node.fields.get("DemandComponentIdentifiers") or ())
    user_defined_supply_components: list[Any] = []

    supply_branch_seen = False
    previous_supply_component: Any | None = None
    for child_identifier in supply_identifiers:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_NodeProbe":
            _register_plant_loop_node_probe(
                context,
                child,
                _plant_component_outlet_node(
                    previous_supply_component,
                    fallback_node=plant_loop.supplyInletNode(),
                ),
            )
            continue
        if child.source_class == "IB_PlantLoopBranches":
            _append_written(
                written_objects,
                _add_plant_loop_branches(
                    openstudio,
                    model,
                    graph,
                    plant_loop,
                    child,
                    side="supply",
                    context=context,
                ),
            )
            supply_branch_seen = True
            continue
        component, summary = _new_plant_component(
            openstudio,
            model,
            child,
            graph,
            context,
        )
        _append_written(written_objects, (summary,))
        if child.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
            setpoint_value = _setpoint_value(child)
            if setpoint_value is not None:
                setpoint_values.append(setpoint_value)
            component.addToNode(plant_loop.supplyOutletNode())
            continue
        if not _component_already_on_loop(component, child, side="supply"):
            component.addToNode(
                plant_loop.supplyOutletNode()
                if supply_branch_seen
                else plant_loop.supplyInletNode()
            )
        if child.source_class == "IB_PlantComponentUserDefined":
            user_defined_supply_components.append(component)
        previous_supply_component = component

    demand_branch_seen = False
    previous_demand_component: Any | None = None
    for child_identifier in demand_identifiers:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_NodeProbe":
            _register_plant_loop_node_probe(
                context,
                child,
                _plant_component_outlet_node(
                    previous_demand_component,
                    fallback_node=plant_loop.demandInletNode(),
                ),
            )
            continue
        if child.source_class == "IB_PlantLoopBranches":
            _append_written(
                written_objects,
                _add_plant_loop_branches(
                    openstudio,
                    model,
                    graph,
                    plant_loop,
                    child,
                    side="demand",
                    context=context,
                ),
            )
            demand_branch_seen = True
            continue
        component, summary = _new_plant_component(
            openstudio,
            model,
            child,
            graph,
            context,
        )
        _append_written(written_objects, (summary,))
        if not _component_already_on_loop(component, child, side="demand"):
            component.addToNode(
                plant_loop.demandOutletNode()
                if demand_branch_seen
                else plant_loop.demandInletNode()
            )
        _configure_plant_demand_component(component, graph, child, side="demand")
        if child.source_class not in _SETPOINT_MANAGER_SOURCE_CLASSES:
            previous_demand_component = component

    _configure_plant_loop_sizing(plant_loop, graph, supply_identifiers, setpoint_values)
    _configure_user_defined_supply_operation(
        openstudio,
        model,
        plant_loop,
        user_defined_supply_components,
    )
    plant_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_loops",
        openstudio_type="OS:PlantLoop",
        name=name,
    )
    return (*written_objects, plant_summary)


def _register_plant_loop_node_probe(
    context: OpenStudioWriterContext | None,
    node: ConsoleGraphNode,
    openstudio_node: Any,
) -> None:
    if context is None:
        return
    context.register_node_probe(node.identifier, openstudio_node)


def _plant_component_outlet_node(component: Any, *, fallback_node: Any) -> Any:
    if component is None or not hasattr(component, "outletModelObject"):
        return fallback_node
    outlet = component.outletModelObject()
    if not outlet.is_initialized():
        return fallback_node
    node = outlet.get().to_Node()
    if not node.is_initialized():
        return fallback_node
    return node.get()


def _add_plant_loop_branches(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    plant_loop: Any,
    node: ConsoleGraphNode,
    *,
    side: str,
    context: OpenStudioWriterContext | None = None,
) -> tuple[OpenStudioWrittenObject, ...]:
    written_objects: list[OpenStudioWrittenObject] = []
    for branch_identifiers in node.fields.get("BranchComponentIdentifiers") or ():
        if not branch_identifiers:
            continue
        branch_insert_node = _latest_branch_insert_node(plant_loop, side=side)
        branch_component_seen = False
        for child_identifier in branch_identifiers:
            child_node = graph.node_by_identifier(str(child_identifier))
            if child_node.source_class == "IB_NodeProbe":
                _register_plant_loop_node_probe(
                    context,
                    child_node,
                    branch_insert_node,
                )
                continue
            component, summary = _new_plant_component(
                openstudio,
                model,
                child_node,
                graph,
                context,
            )
            _append_written(written_objects, (summary,))
            if child_node.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
                component.addToNode(branch_insert_node)
                continue
            if not _component_already_on_loop(component, child_node, side=side):
                if branch_component_seen:
                    component.addToNode(branch_insert_node)
                elif side == "supply":
                    plant_loop.addSupplyBranchForComponent(component)
                else:
                    plant_loop.addDemandBranchForComponent(component)
            branch_component_seen = True
            _configure_plant_demand_component(component, graph, child_node, side=side)
            branch_insert_node = _plant_component_outlet_node(
                component,
                fallback_node=branch_insert_node,
            )
    return tuple(written_objects)

def _configure_plant_demand_component(
    component: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    *,
    side: str,
) -> None:
    if side != "demand":
        return
    if node.source_class not in {"IB_CoilCoolingWater", "IB_CoilHeatingWater"}:
        return
    optional_controller = component.controllerWaterCoil()
    if not optional_controller.is_initialized():
        return
    controller = optional_controller.get()
    controller.setControlVariable("Temperature")
    air_outlet = component.airOutletModelObject()
    if air_outlet.is_initialized():
        controller.setSensorNode(air_outlet.get().to_Node().get())
    water_inlet = component.waterInletModelObject()
    if water_inlet.is_initialized():
        controller.setActuatorNode(water_inlet.get().to_Node().get())
    _apply_water_coil_controller_child(controller, graph, node)

def _latest_branch_insert_node(
    plant_loop: Any,
    *,
    side: str,
) -> Any:
    if side == "supply":
        return plant_loop.supplyMixer().inletModelObjects()[-1].to_Node().get()
    return plant_loop.demandMixer().inletModelObjects()[-1].to_Node().get()

def _component_already_on_loop(
    component: Any,
    node: ConsoleGraphNode,
    *,
    side: str,
) -> bool:
    if node.source_class == "IB_ChillerElectricEIR":
        if side == "demand":
            optional_loop = component.condenserWaterLoop()
        else:
            optional_loop = component.chilledWaterLoop()
        return bool(optional_loop.is_initialized())
    if node.source_class == "IB_HeatExchangerFluidToFluid":
        if side == "demand":
            optional_loop = component.secondaryPlantLoop()
        else:
            optional_loop = component.plantLoop()
        return bool(optional_loop.is_initialized())
    optional_loop = component.plantLoop()
    return bool(optional_loop.is_initialized())


def _configure_user_defined_supply_operation(
    openstudio: Any,
    model: Any,
    plant_loop: Any,
    components: list[Any],
) -> None:
    if not components:
        return
    operation = openstudio.model.PlantEquipmentOperationCoolingLoad(model)
    operation.setName(f"{plant_loop.nameString()} UserDefined Cooling Operation")
    for component in components:
        operation.addEquipment(1_000_000_000.0, component)
    plant_loop.setPlantEquipmentOperationCoolingLoad(operation)

def _setpoint_value(node: ConsoleGraphNode) -> float | None:
    value = node.fields.get("Value")
    if value is None or _is_autosize(value):
        return None
    return float(value)

def _configure_plant_loop_sizing(
    plant_loop: Any,
    graph: ConsoleGraph,
    supply_identifiers: tuple[Any, ...],
    setpoint_values: list[float],
) -> None:
    supply_classes = _source_classes_for_identifiers(graph, supply_identifiers)
    sizing_plant = plant_loop.sizingPlant()
    if (
        "IB_DistrictCooling" in supply_classes
        or "IB_ChillerElectricEIR" in supply_classes
        or "IB_HeatExchangerFluidToFluid" in supply_classes
        or "IB_PlantComponentUserDefined" in supply_classes
    ):
        sizing_plant.setLoopType("Cooling")
        sizing_plant.setDesignLoopExitTemperature(
            setpoint_values[0] if setpoint_values else 6.7
        )
        sizing_plant.setLoopDesignTemperatureDifference(5.0)
    elif "IB_CoolingTowerVariableSpeed" in supply_classes:
        sizing_plant.setLoopType("Condenser")
        sizing_plant.setDesignLoopExitTemperature(
            setpoint_values[0] if setpoint_values else 29.4
        )
        sizing_plant.setLoopDesignTemperatureDifference(5.6)
    elif (
        "IB_DistrictHeatingWater" in supply_classes
        or "IB_BoilerHotWater" in supply_classes
    ):
        sizing_plant.setLoopType("Heating")
        sizing_plant.setDesignLoopExitTemperature(
            setpoint_values[0] if setpoint_values else 60.0
        )
        sizing_plant.setLoopDesignTemperatureDifference(11.0)
