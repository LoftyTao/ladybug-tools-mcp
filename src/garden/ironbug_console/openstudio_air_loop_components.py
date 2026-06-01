"""OpenStudio AirLoopHVAC component factories for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_coils_basic import (
    _new_cooling_water,
    _new_heating_electric,
    _new_heating_water,
)
from garden.ironbug_console.openstudio_coils_dx import (
    _new_cooling_dx_multi_speed,
    _new_cooling_dx_single_speed,
    _new_heating_dx_multi_speed,
    _new_heating_dx_single_speed,
)
from garden.ironbug_console.openstudio_fans import (
    _new_fan_constant_volume,
    _new_fan_on_off,
    _new_fan_system_model,
    _new_fan_variable_volume,
)
from garden.ironbug_console.openstudio_generic_objects import (
    _new_generic_openstudio_object,
    _new_special_openstudio_object,
)
from garden.ironbug_console.openstudio_setpoint_managers import _new_setpoint_manager
from garden.ironbug_console.openstudio_source_classes import (
    GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES as _GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES,
    SETPOINT_MANAGER_SOURCE_CLASSES as _SETPOINT_MANAGER_SOURCE_CLASSES,
    SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES as _SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
    _child_nodes_by_source_class,
    _set_autosizable_if_present,
    _set_if_present,
)

_UNITARY_COOLING_COIL_SOURCE_CLASSES = (
    "IB_CoilCoolingDXSingleSpeed",
    "IB_CoilCoolingDXTwoSpeed",
    "IB_CoilCoolingDXTwoStageWithHumidityControlMode",
)

_UNITARY_HEATING_COIL_SOURCE_CLASSES = (
    "IB_CoilHeatingDXSingleSpeed",
    "IB_CoilHeatingElectric",
)

_UNITARY_FAN_SOURCE_CLASSES = (
    "IB_FanOnOff",
    "IB_FanSystemModel",
)


def _new_air_loop_component(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
    graph: ConsoleGraph | None = None,
    context: OpenStudioWriterContext | None = None,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    if node.source_class == "IB_AirLoopHVACUnitarySystem":
        if graph is None:
            raise ValueError("IB_AirLoopHVACUnitarySystem writer requires graph.")
        return _new_air_loop_unitary_system(openstudio, model, graph, node)
    if node.source_class == "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed":
        if graph is None:
            raise ValueError(
                "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed writer "
                "requires graph."
            )
        return _new_air_loop_unitary_heatpump_multispeed(
            openstudio,
            model,
            graph,
            node,
        )
    if node.source_class == "IB_OutdoorAirSystem":
        if graph is None:
            raise ValueError("IB_OutdoorAirSystem writer requires graph.")
        return _new_outdoor_air_system(openstudio, model, graph, node)
    if node.source_class == "IB_FanConstantVolume":
        component, summary = _new_fan_constant_volume(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_FanVariableVolume":
        component, summary = _new_fan_variable_volume(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_FanOnOff":
        component, summary = _new_fan_on_off(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_FanSystemModel":
        component, summary = _new_fan_system_model(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_CoilCoolingDXSingleSpeed":
        component, summary = _new_cooling_dx_single_speed(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_CoilCoolingDXMultiSpeed":
        if graph is None:
            raise ValueError("IB_CoilCoolingDXMultiSpeed writer requires graph.")
        component, summaries = _new_cooling_dx_multi_speed(
            openstudio,
            model,
            graph,
            node,
        )
        return component, summaries
    if node.source_class == "IB_CoilHeatingDXMultiSpeed":
        if graph is None:
            raise ValueError("IB_CoilHeatingDXMultiSpeed writer requires graph.")
        component, summaries = _new_heating_dx_multi_speed(
            openstudio,
            model,
            graph,
            node,
        )
        return component, summaries
    if node.source_class == "IB_CoilCoolingWater":
        component, summary = _new_cooling_water(openstudio, model, node)
        return component, (summary,)
    if node.source_class == "IB_CoilHeatingWater":
        component, summary = _new_heating_water(openstudio, model, node)
        return component, (summary,)
    if node.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
        if graph is None:
            raise ValueError(f"{node.source_class} writer requires graph.")
        component, summary = _new_setpoint_manager(
            openstudio,
            model,
            graph,
            node,
            context,
        )
        return component, (summary,)
    if node.source_class in _GENERIC_AIR_LOOP_COMPONENT_SOURCE_CLASSES:
        component, summary = _new_generic_openstudio_object(openstudio, model, node)
        return component, (summary,)
    if node.source_class in _SPECIAL_AIR_LOOP_COMPONENT_SOURCE_CLASSES:
        component, summary = _new_special_openstudio_object(openstudio, model, node)
        return component, (summary,)
    raise ValueError(f"Unsupported AirLoopHVAC component: {node.source_class}")


def _new_outdoor_air_system(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    written_objects: list[OpenStudioWrittenObject] = []
    if "IB_ControllerOutdoorAir" in child_nodes:
        controller, controller_summaries = _new_controller_outdoor_air(
            openstudio,
            model,
            graph,
            child_nodes["IB_ControllerOutdoorAir"],
        )
        _append_written(written_objects, controller_summaries)
    else:
        controller = openstudio.model.ControllerOutdoorAir(model)

    name = str(node.fields.get("Name") or node.identifier)
    optional_oa_system = model.getAirLoopHVACOutdoorAirSystemByName(name)
    if optional_oa_system.is_initialized():
        oa_system = optional_oa_system.get()
        oa_system.setControllerOutdoorAir(controller)
    else:
        oa_system = openstudio.model.AirLoopHVACOutdoorAirSystem(
            model,
            controller,
        )
        oa_system.setName(name)
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class == "IB_ControllerOutdoorAir":
            continue
        if child.source_class in _SETPOINT_MANAGER_SOURCE_CLASSES:
            component, summaries = _new_setpoint_manager(
                openstudio,
                model,
                graph,
                child,
                None,
            )
        else:
            component, summaries = _new_air_loop_component(
                openstudio,
                model,
                child,
                graph,
                None,
        )
        _append_written(written_objects, summaries)
        if not _oa_component_already_on_system(component):
            outboard_node = oa_system.outboardOANode()
            if outboard_node.is_initialized():
                component.addToNode(outboard_node.get())
    oa_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_components",
        openstudio_type="OS:AirLoopHVAC:OutdoorAirSystem",
        name=name,
    )
    return oa_system, (*written_objects, oa_summary)


def _new_controller_outdoor_air(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    if "IB_ControllerMechanicalVentilation" in child_nodes:
        mechanical, mechanical_summary = _new_controller_mechanical_ventilation(
            openstudio,
            model,
            child_nodes["IB_ControllerMechanicalVentilation"],
        )
        mechanical_summaries = (mechanical_summary,)
    else:
        mechanical = openstudio.model.ControllerMechanicalVentilation(model)
        mechanical_summaries = ()

    name = str(node.fields.get("Name") or node.identifier)
    optional_controller = model.getControllerOutdoorAirByName(name)
    if optional_controller.is_initialized():
        controller = optional_controller.get()
    else:
        controller = openstudio.model.ControllerOutdoorAir(model)
        controller.setName(name)
    controller.setControllerMechanicalVentilation(mechanical)
    _set_autosizable_if_present(
        controller.setMinimumOutdoorAirFlowRate,
        controller.autosizeMinimumOutdoorAirFlowRate,
        node,
        "MinimumOutdoorAirFlowRate",
    )
    _set_autosizable_if_present(
        controller.setMaximumOutdoorAirFlowRate,
        controller.autosizeMaximumOutdoorAirFlowRate,
        node,
        "MaximumOutdoorAirFlowRate",
    )
    _set_if_present(
        controller.setEconomizerControlType,
        node,
        "EconomizerControlType",
        cast=str,
    )
    _set_if_present(
        controller.setHighHumidityControl,
        node,
        "HighHumidityControl",
        cast=bool,
    )
    controller_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_components",
        openstudio_type="OS:Controller:OutdoorAir",
        name=name,
    )
    return controller, (*mechanical_summaries, controller_summary)


def _new_controller_mechanical_ventilation(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_controller = model.getControllerMechanicalVentilationByName(name)
    if optional_controller.is_initialized():
        controller = optional_controller.get()
    else:
        controller = openstudio.model.ControllerMechanicalVentilation(model)
        controller.setName(name)
    _set_if_present(
        controller.setDemandControlledVentilation,
        node,
        "DemandControlledVentilation",
        cast=bool,
    )
    _set_if_present(
        controller.setSystemOutdoorAirMethod,
        node,
        "SystemOutdoorAirMethod",
        cast=str,
    )
    return controller, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_components",
        openstudio_type="OS:Controller:MechanicalVentilation",
        name=name,
    )


def _new_air_loop_unitary_system(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_node = _first_available_child(
        child_nodes,
        _UNITARY_COOLING_COIL_SOURCE_CLASSES,
    )
    heating_node = _first_available_child(
        child_nodes,
        _UNITARY_HEATING_COIL_SOURCE_CLASSES,
    )
    fan_node = _first_available_child(child_nodes, _UNITARY_FAN_SOURCE_CLASSES)
    if cooling_node is None:
        raise ValueError("IB_AirLoopHVACUnitarySystem requires a cooling coil child.")
    if heating_node is None:
        raise ValueError("IB_AirLoopHVACUnitarySystem requires a heating coil child.")
    if fan_node is None:
        raise ValueError("IB_AirLoopHVACUnitarySystem requires a supply fan child.")

    cooling_coil, cooling_summary = _new_unitary_child_component(
        openstudio,
        model,
        cooling_node,
    )
    heating_coil, heating_summary = _new_unitary_child_component(
        openstudio,
        model,
        heating_node,
    )
    fan, fan_summary = _new_unitary_child_component(
        openstudio,
        model,
        fan_node,
    )
    supplemental_coil = None
    supplemental_summary = None
    if (
        "IB_CoilHeatingElectric" in child_nodes
        and child_nodes["IB_CoilHeatingElectric"] is not heating_node
    ):
        supplemental_coil, supplemental_summary = _new_heating_electric(
            openstudio,
            model,
            child_nodes["IB_CoilHeatingElectric"],
        )

    name = str(node.fields.get("Name") or node.identifier)
    optional_unitary = model.getAirLoopHVACUnitarySystemByName(name)
    if optional_unitary.is_initialized():
        unitary = optional_unitary.get()
    else:
        unitary = openstudio.model.AirLoopHVACUnitarySystem(model)
        unitary.setName(name)
    unitary.setCoolingCoil(cooling_coil)
    unitary.setHeatingCoil(heating_coil)
    unitary.setSupplyFan(fan)
    if supplemental_coil is not None:
        unitary.setSupplementalHeatingCoil(supplemental_coil)
    if "IB_ThermalZone" in child_nodes:
        zone_name = str(
            child_nodes["IB_ThermalZone"].fields.get("Name")
            or child_nodes["IB_ThermalZone"].identifier
        )
        optional_zone = model.getThermalZoneByName(zone_name)
        if optional_zone.is_initialized():
            unitary.setControllingZoneorThermostatLocation(optional_zone.get())

    _set_if_present(unitary.setControlType, node, "ControlType", cast=str)
    _set_if_present(
        unitary.setDehumidificationControlType,
        node,
        "DehumidificationControlType",
        cast=str,
    )
    _set_if_present(unitary.setFanPlacement, node, "FanPlacement", cast=str)
    _set_if_present(unitary.setLatentLoadControl, node, "LatentLoadControl", cast=str)
    _set_if_present(
        unitary.setSupplyAirFlowRateMethodDuringCoolingOperation,
        node,
        "SupplyAirFlowRateMethodDuringCoolingOperation",
        cast=str,
    )
    _set_if_present(
        unitary.setSupplyAirFlowRateMethodDuringHeatingOperation,
        node,
        "SupplyAirFlowRateMethodDuringHeatingOperation",
        cast=str,
    )
    _set_if_present(
        unitary.setSupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired,
        node,
        "SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired",
        cast=str,
    )
    _set_autosizable_if_present(
        unitary.setSupplyAirFlowRateDuringCoolingOperation,
        unitary.autosizeSupplyAirFlowRateDuringCoolingOperation,
        node,
        "SupplyAirFlowRateDuringCoolingOperation",
    )
    _set_autosizable_if_present(
        unitary.setSupplyAirFlowRateDuringHeatingOperation,
        unitary.autosizeSupplyAirFlowRateDuringHeatingOperation,
        node,
        "SupplyAirFlowRateDuringHeatingOperation",
    )
    _set_autosizable_if_present(
        unitary.setSupplyAirFlowRateWhenNoCoolingorHeatingisRequired,
        unitary.autosizeSupplyAirFlowRateWhenNoCoolingorHeatingisRequired,
        node,
        "SupplyAirFlowRateWhenNoCoolingorHeatingisRequired",
    )
    _set_autosizable_if_present(
        unitary.setMaximumSupplyAirTemperature,
        unitary.autosizeMaximumSupplyAirTemperature,
        node,
        "MaximumSupplyAirTemperature",
    )
    unitary_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_unitary",
        openstudio_type="OS:AirLoopHVAC:UnitarySystem",
        name=name,
    )
    summaries = [cooling_summary, heating_summary, fan_summary]
    if supplemental_summary is not None:
        summaries.append(supplemental_summary)
    summaries.append(unitary_summary)
    return unitary, tuple(summaries)


def _new_air_loop_unitary_heatpump_multispeed(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    child_nodes = _child_nodes_by_source_class(graph, node)
    cooling_node = child_nodes.get("IB_CoilCoolingDXMultiSpeed")
    heating_node = child_nodes.get("IB_CoilHeatingDXMultiSpeed")
    fan_node = child_nodes.get("IB_FanOnOff")
    supplemental_node = child_nodes.get("IB_CoilHeatingElectric")
    if cooling_node is None:
        raise ValueError(
            "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed requires an "
            "IB_CoilCoolingDXMultiSpeed child."
        )
    if heating_node is None:
        raise ValueError(
            "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed requires an "
            "IB_CoilHeatingDXMultiSpeed child."
        )
    if fan_node is None:
        raise ValueError(
            "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed currently "
            "requires an IB_FanOnOff child."
        )
    if supplemental_node is None:
        raise ValueError(
            "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed requires an "
            "IB_CoilHeatingElectric supplemental heating coil child."
        )

    cooling_coil, cooling_summaries = _new_cooling_dx_multi_speed(
        openstudio,
        model,
        graph,
        cooling_node,
    )
    heating_coil, heating_summaries = _new_heating_dx_multi_speed(
        openstudio,
        model,
        graph,
        heating_node,
    )
    fan, fan_summary = _new_fan_on_off(openstudio, model, fan_node)
    supplemental_coil, supplemental_summary = _new_heating_electric(
        openstudio,
        model,
        supplemental_node,
    )

    name = str(node.fields.get("Name") or node.identifier)
    optional_unitary = model.getAirLoopHVACUnitaryHeatPumpAirToAirMultiSpeedByName(
        name
    )
    if optional_unitary.is_initialized():
        unitary = optional_unitary.get()
    else:
        unitary = openstudio.model.AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed(
            model,
            fan,
            heating_coil,
            cooling_coil,
            supplemental_coil,
        )
        unitary.setName(name)
    unitary.setSupplyAirFan(fan)
    unitary.setHeatingCoil(heating_coil)
    unitary.setCoolingCoil(cooling_coil)
    unitary.setSupplementalHeatingCoil(supplemental_coil)
    _set_multispeed_heatpump_controlling_zone(model, unitary, node, child_nodes)
    _set_if_present(
        unitary.setSupplyAirFanPlacement,
        node,
        "SupplyAirFanPlacement",
        cast=str,
    )
    _set_if_present(
        unitary.setMinimumOutdoorDryBulbTemperatureforCompressorOperation,
        node,
        "MinimumOutdoorDryBulbTemperatureforCompressorOperation",
    )
    _set_if_present(
        unitary.setMaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation,
        node,
        "MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation",
    )
    _set_if_present(
        unitary.setAuxiliaryOnCycleElectricPower,
        node,
        "AuxiliaryOnCycleElectricPower",
    )
    _set_if_present(
        unitary.setAuxiliaryOffCycleElectricPower,
        node,
        "AuxiliaryOffCycleElectricPower",
    )
    _set_if_present(
        unitary.setDesignHeatRecoveryWaterFlowRate,
        node,
        "DesignHeatRecoveryWaterFlowRate",
    )
    _set_if_present(
        unitary.setMaximumTemperatureforHeatRecovery,
        node,
        "MaximumTemperatureforHeatRecovery",
    )
    _set_autosizable_if_present(
        unitary.setMaximumSupplyAirTemperaturefromSupplementalHeater,
        unitary.autosizeMaximumSupplyAirTemperaturefromSupplementalHeater,
        node,
        "MaximumSupplyAirTemperaturefromSupplementalHeater",
    )
    _set_autosizable_if_present(
        unitary.setSupplyAirFlowRateWhenNoCoolingorHeatingisNeeded,
        unitary.autosizeSupplyAirFlowRateWhenNoCoolingorHeatingisNeeded,
        node,
        "SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded",
    )
    _set_if_present(
        unitary.setNumberofSpeedsforHeating,
        node,
        "NumberofSpeedsforHeating",
        cast=int,
    )
    _set_if_present(
        unitary.setNumberofSpeedsforCooling,
        node,
        "NumberofSpeedsforCooling",
        cast=int,
    )
    for index in range(1, 5):
        _set_autosizable_if_present(
            getattr(
                unitary,
                f"setSpeed{index}SupplyAirFlowRateDuringHeatingOperation",
            ),
            getattr(
                unitary,
                f"autosizeSpeed{index}SupplyAirFlowRateDuringHeatingOperation",
            ),
            node,
            f"Speed{index}SupplyAirFlowRateDuringHeatingOperation",
        )
        _set_autosizable_if_present(
            getattr(
                unitary,
                f"setSpeed{index}SupplyAirFlowRateDuringCoolingOperation",
            ),
            getattr(
                unitary,
                f"autosizeSpeed{index}SupplyAirFlowRateDuringCoolingOperation",
            ),
            node,
            f"Speed{index}SupplyAirFlowRateDuringCoolingOperation",
        )
    unitary_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="air_loop_unitary",
        openstudio_type="OS:AirLoopHVAC:UnitaryHeatPump:AirToAir:MultiSpeed",
        name=name,
    )
    return unitary, (
        *cooling_summaries,
        *heating_summaries,
        fan_summary,
        supplemental_summary,
        unitary_summary,
    )


def _set_multispeed_heatpump_controlling_zone(
    model: Any,
    unitary: Any,
    node: ConsoleGraphNode,
    child_nodes: dict[str, ConsoleGraphNode],
) -> None:
    zone_name = node.fields.get("_controlZoneName")
    if not zone_name and "IB_ThermalZone" in child_nodes:
        zone_name = (
            child_nodes["IB_ThermalZone"].fields.get("Name")
            or child_nodes["IB_ThermalZone"].identifier
        )
    if not zone_name:
        return
    optional_zone = model.getThermalZoneByName(str(zone_name))
    if optional_zone.is_initialized():
        unitary.setControllingZoneorThermostatLocation(optional_zone.get())


def _first_available_child(
    child_nodes: dict[str, ConsoleGraphNode],
    source_classes: tuple[str, ...],
) -> ConsoleGraphNode | None:
    for source_class in source_classes:
        if source_class in child_nodes:
            return child_nodes[source_class]
    return None


def _new_unitary_child_component(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    if node.source_class == "IB_CoilCoolingDXSingleSpeed":
        return _new_cooling_dx_single_speed(openstudio, model, node)
    if node.source_class == "IB_CoilHeatingDXSingleSpeed":
        return _new_heating_dx_single_speed(openstudio, model, node)
    if node.source_class == "IB_CoilCoolingDXMultiSpeed":
        raise ValueError("IB_CoilCoolingDXMultiSpeed writer requires graph.")
    if node.source_class == "IB_CoilHeatingDXMultiSpeed":
        raise ValueError("IB_CoilHeatingDXMultiSpeed writer requires graph.")
    if node.source_class == "IB_CoilHeatingElectric":
        return _new_heating_electric(openstudio, model, node)
    if node.source_class == "IB_FanOnOff":
        return _new_fan_on_off(openstudio, model, node)
    if node.source_class == "IB_FanSystemModel":
        return _new_fan_system_model(openstudio, model, node)
    component, summary = _new_generic_openstudio_object(openstudio, model, node)
    return component, summary


def _oa_component_already_on_system(component: Any) -> bool:
    try:
        optional_oa_system = component.airLoopHVACOutdoorAirSystem()
    except AttributeError:
        return False
    return bool(optional_oa_system.is_initialized())
