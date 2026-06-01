"""Plant pump writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_pump_constant_speed(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_pump = model.getPumpConstantSpeedByName(name)
    if optional_pump.is_initialized():
        pump = optional_pump.get()
    else:
        pump = openstudio.model.PumpConstantSpeed(model)
        pump.setName(name)
    _set_autosizable_if_present(
        pump.setRatedFlowRate,
        pump.autosizeRatedFlowRate,
        node,
        "RatedFlowRate",
    )
    _set_if_present(pump.setRatedPumpHead, node, "RatedPumpHead")
    _set_if_present(pump.setMotorEfficiency, node, "MotorEfficiency")
    _set_if_present(pump.setPumpControlType, node, "PumpControlType", cast=str)
    return pump, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:Pump:ConstantSpeed",
        name=name,
    )


def _new_pump_variable_speed(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_pump = model.getPumpVariableSpeedByName(name)
    if optional_pump.is_initialized():
        pump = optional_pump.get()
    else:
        pump = openstudio.model.PumpVariableSpeed(model)
        pump.setName(name)
    _set_autosizable_if_present(
        pump.setRatedFlowRate,
        pump.autosizeRatedFlowRate,
        node,
        "RatedFlowRate",
    )
    _set_autosizable_if_present(
        pump.setRatedPowerConsumption,
        pump.autosizeRatedPowerConsumption,
        node,
        "RatedPowerConsumption",
    )
    _set_if_present(pump.setRatedPumpHead, node, "RatedPumpHead")
    _set_if_present(pump.setMotorEfficiency, node, "MotorEfficiency")
    _set_if_present(
        pump.setFractionofMotorInefficienciestoFluidStream,
        node,
        "FractionofMotorInefficienciestoFluidStream",
    )
    _set_if_present(
        pump.setCoefficient1ofthePartLoadPerformanceCurve,
        node,
        "Coefficient1ofthePartLoadPerformanceCurve",
    )
    _set_if_present(
        pump.setCoefficient2ofthePartLoadPerformanceCurve,
        node,
        "Coefficient2ofthePartLoadPerformanceCurve",
    )
    _set_if_present(
        pump.setCoefficient3ofthePartLoadPerformanceCurve,
        node,
        "Coefficient3ofthePartLoadPerformanceCurve",
    )
    _set_if_present(
        pump.setCoefficient4ofthePartLoadPerformanceCurve,
        node,
        "Coefficient4ofthePartLoadPerformanceCurve",
    )
    _set_if_present(pump.setMinimumFlowRate, node, "MinimumFlowRate")
    _set_if_present(pump.setPumpControlType, node, "PumpControlType", cast=str)
    _set_if_present(pump.setImpellerDiameter, node, "ImpellerDiameter")
    _set_if_present(pump.setVFDControlType, node, "VFDControlType", cast=str)
    _set_if_present(
        pump.setDesignPowerSizingMethod,
        node,
        "DesignPowerSizingMethod",
        cast=str,
    )
    _set_if_present(
        pump.setDesignElectricPowerPerUnitFlowRate,
        node,
        "DesignElectricPowerPerUnitFlowRate",
    )
    _set_if_present(
        pump.setDesignShaftPowerPerUnitFlowRatePerUnitHead,
        node,
        "DesignShaftPowerPerUnitFlowRatePerUnitHead",
    )
    _set_if_present(
        pump.setSkinLossRadiativeFraction,
        node,
        "SkinLossRadiativeFraction",
    )
    _set_if_present(
        pump.setDesignMinimumFlowRateFraction,
        node,
        "DesignMinimumFlowRateFraction",
    )
    return pump, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:Pump:VariableSpeed",
        name=name,
    )
