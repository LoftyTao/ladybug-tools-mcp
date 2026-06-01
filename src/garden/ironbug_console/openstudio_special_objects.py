"""Special-case OpenStudio object factories for Ironbug source classes."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_families import _generic_writer_family
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
    _temperature_schedule,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


def _new_special_openstudio_object(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    source_class = node.source_class
    if source_class == "IB_AirLoopHVACUnitaryHeatPumpAirToAir":
        component = openstudio.model.AirLoopHVACUnitaryHeatPumpAirToAir(
            model,
            model.alwaysOnDiscreteSchedule(),
            openstudio.model.FanOnOff(model),
            openstudio.model.CoilHeatingDXSingleSpeed(model),
            openstudio.model.CoilCoolingDXSingleSpeed(model),
            openstudio.model.CoilHeatingElectric(model),
        )
    elif source_class == "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed":
        component = openstudio.model.AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed(
            model,
            openstudio.model.FanOnOff(model),
            openstudio.model.CoilHeatingDXMultiSpeed(model),
            openstudio.model.CoilCoolingDXMultiSpeed(model),
            openstudio.model.CoilHeatingElectric(model),
        )
    elif source_class in {
        "IB_CoilCoolingLowTempRadiantConstFlow",
        "IB_CoilHeatingLowTempRadiantConstFlow",
    }:
        class_name = source_class.removeprefix("IB_")
        component = getattr(openstudio.model, class_name)(
            model,
            _temperature_schedule(openstudio, model, f"{name} High Water", 20.0),
            _temperature_schedule(openstudio, model, f"{name} Low Water", 18.0),
            _temperature_schedule(openstudio, model, f"{name} High Control", 24.0),
            _temperature_schedule(openstudio, model, f"{name} Low Control", 20.0),
        )
    elif source_class in {
        "IB_CoilCoolingLowTempRadiantVarFlow",
        "IB_CoilHeatingLowTempRadiantVarFlow",
    }:
        component = getattr(openstudio.model, source_class.removeprefix("IB_"))(
            model,
            _temperature_schedule(openstudio, model, f"{name} Control", 20.0),
        )
    elif source_class == "IB_ControllerWaterCoil":
        dummy_loop = openstudio.model.PlantLoop(model)
        dummy_coil = openstudio.model.CoilCoolingWater(model)
        dummy_loop.addDemandBranchForComponent(dummy_coil)
        component = dummy_coil.controllerWaterCoil().get()
    elif source_class == "IB_EnergyManagementSystemActuator":
        actuated_component = model.alwaysOnDiscreteSchedule()
        component_name = node.fields.get("Space") or node.fields.get(
            "ActuatedComponentName"
        )
        if component_name:
            candidate = model.getModelObjectByName(str(component_name))
            if candidate.is_initialized():
                actuated_component = candidate.get()
        component = openstudio.model.EnergyManagementSystemActuator(
            actuated_component,
            str(
                node.fields.get("ActuatedComponentType")
                or node.fields.get("ComponentType")
                or "Schedule:Constant"
            ),
            str(
                node.fields.get("ActuatedComponentControlType")
                or node.fields.get("ControlType")
                or "Schedule Value"
            ),
        )
    elif source_class == "IB_EnergyManagementSystemCurveVariable":
        component = openstudio.model.EnergyManagementSystemCurveOrTableIndexVariable(
            model
        )
    elif source_class == "IB_EnergyManagementSystemInternalVariable":
        component = openstudio.model.EnergyManagementSystemInternalVariable(
            model,
            str(node.fields.get("InternalDataType") or "Zone Air Volume"),
        )
    elif source_class == "IB_EnergyManagementSystemMeteredOutputVariable":
        component = openstudio.model.EnergyManagementSystemMeteredOutputVariable(
            model,
            str(node.fields.get("VariableName") or name),
        )
    elif source_class == "IB_EnergyManagementSystemSensor":
        component = openstudio.model.EnergyManagementSystemSensor(
            model,
            str(
                node.fields.get("OutputVariableOrMeterName")
                or "Zone Mean Air Temperature"
            ),
        )
    elif source_class == "IB_EvaporativeCoolerDirectResearchSpecial":
        component = openstudio.model.EvaporativeCoolerDirectResearchSpecial(
            model,
            model.alwaysOnDiscreteSchedule(),
        )
    elif source_class == "IB_GeneratorPVWatts":
        component = openstudio.model.GeneratorPVWatts(
            model,
            float(node.fields.get("DCSystemCapacity") or 1000.0),
        )
    elif source_class == "IB_GeneratorPhotovoltaic":
        component = openstudio.model.GeneratorPhotovoltaic.simple(model)
        component.setSurface(_default_shading_surface(openstudio, model, f"{name} Surface"))
    elif source_class == "IB_ShadingSurface":
        component = _default_shading_surface(openstudio, model, name)
    elif source_class == "IB_SolarCollectorPerformanceFlatPlate":
        collector = openstudio.model.SolarCollectorFlatPlateWater(model)
        component = collector.solarCollectorPerformance()
    elif source_class == "IB_SolarCollectorPerformancePhotovoltaicThermal":
        component = openstudio.model.SolarCollectorPerformancePhotovoltaicThermalSimple(
            model
        )
    elif source_class == "IB_SwimmingPoolIndoor":
        component = openstudio.model.SwimmingPoolIndoor(
            model,
            _default_surface(openstudio, model, f"{name} Surface"),
        )
    elif source_class == "IB_WaterHeaterSizing":
        component = openstudio.model.WaterHeaterMixed(model).waterHeaterSizing()
    elif source_class == "IB_WaterUseEquipment":
        definition = openstudio.model.WaterUseEquipmentDefinition(model)
        component = openstudio.model.WaterUseEquipment(definition)
    elif source_class == "IB_ZoneHVACBaseboardConvectiveWater":
        component = openstudio.model.ZoneHVACBaseboardConvectiveWater(
            model,
            model.alwaysOnDiscreteSchedule(),
            openstudio.model.CoilHeatingWaterBaseboard(model),
        )
    elif source_class == "IB_ZoneHVACLowTempRadiantConstFlow":
        component = openstudio.model.ZoneHVACLowTempRadiantConstFlow(
            model,
            model.alwaysOnDiscreteSchedule(),
            openstudio.model.CoilHeatingLowTempRadiantConstFlow(
                model,
                _temperature_schedule(openstudio, model, f"{name} Heat High", 40.0),
                _temperature_schedule(openstudio, model, f"{name} Heat Low", 30.0),
                _temperature_schedule(
                    openstudio,
                    model,
                    f"{name} Heat Control High",
                    22.0,
                ),
                _temperature_schedule(
                    openstudio,
                    model,
                    f"{name} Heat Control Low",
                    18.0,
                ),
            ),
            openstudio.model.CoilCoolingLowTempRadiantConstFlow(
                model,
                _temperature_schedule(openstudio, model, f"{name} Cool High", 20.0),
                _temperature_schedule(openstudio, model, f"{name} Cool Low", 18.0),
                _temperature_schedule(
                    openstudio,
                    model,
                    f"{name} Cool Control High",
                    24.0,
                ),
                _temperature_schedule(
                    openstudio,
                    model,
                    f"{name} Cool Control Low",
                    20.0,
                ),
            ),
        )
    elif source_class == "IB_ZoneHVACLowTemperatureRadiantElectric":
        component = openstudio.model.ZoneHVACLowTemperatureRadiantElectric(
            model,
            model.alwaysOnDiscreteSchedule(),
            _temperature_schedule(openstudio, model, f"{name} Heating Setpoint", 20.0),
        )
    elif source_class == "IB_ZoneHVACWaterToAirHeatPump":
        component = openstudio.model.ZoneHVACWaterToAirHeatPump(
            model,
            model.alwaysOnDiscreteSchedule(),
            openstudio.model.FanOnOff(model),
            openstudio.model.CoilHeatingWaterToAirHeatPumpEquationFit(model),
            openstudio.model.CoilCoolingWaterToAirHeatPumpEquationFit(model),
            openstudio.model.CoilHeatingElectric(model),
        )
    else:
        raise ValueError(f"Unsupported special OpenStudio object: {source_class}")

    if hasattr(component, "setName"):
        component.setName(name)
    _apply_generic_openstudio_fields(component, node)
    if source_class == "IB_EnergyManagementSystemMeteredOutputVariable":
        _apply_ems_program_or_subroutine(model, component, node)
    return component, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family=_generic_writer_family(node.source_class),
        openstudio_type=component.iddObjectType().valueDescription(),
        name=name,
    )


def _apply_ems_program_or_subroutine(
    model: Any,
    component: Any,
    node: ConsoleGraphNode,
) -> None:
    program_name = node.fields.get("EMSProgramOrSubroutineName")
    if not program_name:
        return
    program = model.getEnergyManagementSystemProgramByName(str(program_name))
    if program.is_initialized():
        component.setEMSProgramOrSubroutineName(program.get())
        return
    subroutine = model.getEnergyManagementSystemSubroutineByName(str(program_name))
    if subroutine.is_initialized():
        component.setEMSProgramOrSubroutineName(subroutine.get())


def _default_shading_surface(openstudio: Any, model: Any, name: str) -> Any:
    group = openstudio.model.ShadingSurfaceGroup(model)
    group.setName(f"{name} Group")
    surface = openstudio.model.ShadingSurface(
        _default_planar_vertices(openstudio),
        model,
    )
    surface.setName(name)
    surface.setShadingSurfaceGroup(group)
    return surface


def _default_surface(openstudio: Any, model: Any, name: str) -> Any:
    surface = openstudio.model.Surface(_default_planar_vertices(openstudio), model)
    surface.setName(name)
    surface.setSurfaceType("Floor")
    return surface


def _default_planar_vertices(openstudio: Any) -> Any:
    vertices = openstudio.Point3dVector()
    vertices.append(openstudio.Point3d(0, 0, 0))
    vertices.append(openstudio.Point3d(1, 0, 0))
    vertices.append(openstudio.Point3d(1, 1, 0))
    vertices.append(openstudio.Point3d(0, 1, 0))
    return vertices
