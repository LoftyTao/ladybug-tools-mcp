"""OpenStudio fan factories for the Python Ironbug Console."""

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


def _new_fan_on_off(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_fan = model.getFanOnOffByName(name)
    if optional_fan.is_initialized():
        fan = optional_fan.get()
    else:
        fan = openstudio.model.FanOnOff(model)
        fan.setName(name)
    _set_autosizable_if_present(
        fan.setMaximumFlowRate,
        fan.autosizeMaximumFlowRate,
        node,
        "MaximumFlowRate",
    )
    return fan, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Fan:OnOff",
        name=name,
    )


def _new_fan_constant_volume(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_fan = model.getFanConstantVolumeByName(name)
    if optional_fan.is_initialized():
        fan = optional_fan.get()
    else:
        fan = openstudio.model.FanConstantVolume(model)
        fan.setName(name)
    _set_autosizable_if_present(
        fan.setMaximumFlowRate,
        fan.autosizeMaximumFlowRate,
        node,
        "MaximumFlowRate",
    )
    return fan, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Fan:ConstantVolume",
        name=name,
    )


def _new_fan_variable_volume(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_fan = model.getFanVariableVolumeByName(name)
    if optional_fan.is_initialized():
        fan = optional_fan.get()
    else:
        fan = openstudio.model.FanVariableVolume(model)
        fan.setName(name)
    _set_autosizable_if_present(
        fan.setMaximumFlowRate,
        fan.autosizeMaximumFlowRate,
        node,
        "MaximumFlowRate",
    )
    _set_if_present(
        fan.setFanPowerMinimumFlowRateInputMethod,
        node,
        "FanPowerMinimumFlowRateInputMethod",
        cast=str,
    )
    _set_if_present(
        fan.setFanPowerMinimumFlowFraction,
        node,
        "FanPowerMinimumFlowFraction",
    )
    _set_if_present(
        fan.setFanPowerMinimumAirFlowRate,
        node,
        "FanPowerMinimumAirFlowRate",
    )
    return fan, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Fan:VariableVolume",
        name=name,
    )


def _new_fan_system_model(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_fan = model.getFanSystemModelByName(name)
    if optional_fan.is_initialized():
        fan = optional_fan.get()
    else:
        fan = openstudio.model.FanSystemModel(model)
        fan.setName(name)
    _set_autosizable_if_present(
        fan.setDesignMaximumAirFlowRate,
        fan.autosizeDesignMaximumAirFlowRate,
        node,
        "DesignMaximumAirFlowRate",
    )
    _set_if_present(fan.setSpeedControlMethod, node, "SpeedControlMethod", cast=str)
    _set_if_present(
        fan.setElectricPowerMinimumFlowRateFraction,
        node,
        "ElectricPowerMinimumFlowRateFraction",
    )
    _set_if_present(fan.setDesignPressureRise, node, "DesignPressureRise")
    _set_if_present(fan.setMotorEfficiency, node, "MotorEfficiency")
    _set_if_present(
        fan.setMotorInAirStreamFraction,
        node,
        "MotorInAirStreamFraction",
    )
    _set_autosizable_if_present(
        fan.setDesignElectricPowerConsumption,
        fan.autosizeDesignElectricPowerConsumption,
        node,
        "DesignElectricPowerConsumption",
    )
    _set_if_present(
        fan.setDesignPowerSizingMethod,
        node,
        "DesignPowerSizingMethod",
        cast=str,
    )
    _set_if_present(
        fan.setElectricPowerPerUnitFlowRate,
        node,
        "ElectricPowerPerUnitFlowRate",
    )
    _set_if_present(
        fan.setElectricPowerPerUnitFlowRatePerUnitPressure,
        node,
        "ElectricPowerPerUnitFlowRatePerUnitPressure",
    )
    _set_if_present(fan.setFanTotalEfficiency, node, "FanTotalEfficiency")
    _set_if_present(
        fan.setNightVentilationModePressureRise,
        node,
        "NightVentilationModePressureRise",
    )
    _set_if_present(
        fan.setNightVentilationModeFlowFraction,
        node,
        "NightVentilationModeFlowFraction",
    )
    _set_if_present(
        fan.setMotorLossRadiativeFraction,
        node,
        "MotorLossRadiativeFraction",
    )
    _set_if_present(fan.setEndUseSubcategory, node, "EndUseSubcategory", cast=str)
    _set_default_fan_system_model_power_curve(openstudio, model, fan, name)
    return fan, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Fan:SystemModel",
        name=name,
    )


def _set_default_fan_system_model_power_curve(
    openstudio: Any,
    model: Any,
    fan: Any,
    name: str,
) -> None:
    if fan.electricPowerFunctionofFlowFractionCurve().is_initialized():
        return
    curve_name = f"{name} Electric Power Flow Fraction Curve"
    optional_curve = model.getCurveCubicByName(curve_name)
    if optional_curve.is_initialized():
        curve = optional_curve.get()
    else:
        curve = openstudio.model.CurveCubic(model)
        curve.setName(curve_name)
        curve.setCoefficient1Constant(0.0)
        curve.setCoefficient2x(0.0)
        curve.setCoefficient3xPOW2(0.0)
        curve.setCoefficient4xPOW3(1.0)
        curve.setMinimumValueofx(0.0)
        curve.setMaximumValueofx(1.0)
        curve.setMinimumCurveOutput(0.0)
        curve.setMaximumCurveOutput(1.0)
    fan.setElectricPowerFunctionofFlowFractionCurve(curve)
