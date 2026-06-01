"""OpenStudio DX coil factories for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_curves import _CURVE_SPECS
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_heating_dx_single_speed(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingDXSingleSpeedByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingDXSingleSpeed(model)
        coil.setName(name)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:DX:SingleSpeed",
        name=name,
    )


def _new_cooling_dx_single_speed(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingDXSingleSpeedByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingDXSingleSpeed(model)
        coil.setName(name)
    _set_if_present(coil.setRatedCOP, node, "RatedCOP")
    _set_if_present(coil.setCondenserType, node, "CondenserType", cast=str)
    _set_autosizable_if_present(
        coil.setRatedTotalCoolingCapacity,
        coil.autosizeRatedTotalCoolingCapacity,
        node,
        "RatedTotalCoolingCapacity",
    )
    _set_autosizable_if_present(
        coil.setRatedSensibleHeatRatio,
        coil.autosizeRatedSensibleHeatRatio,
        node,
        "RatedSensibleHeatRatio",
    )
    _set_autosizable_if_present(
        coil.setRatedAirFlowRate,
        coil.autosizeRatedAirFlowRate,
        node,
        "RatedAirFlowRate",
    )
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:DX:SingleSpeed",
        name=name,
    )


def _new_cooling_dx_variable_refrigerant_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingDXVariableRefrigerantFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingDXVariableRefrigerantFlow(model)
        coil.setName(name)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:DX:VariableRefrigerantFlow",
        name=name,
    )


def _new_cooling_dx_multi_speed(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilCoolingDXMultiSpeedByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilCoolingDXMultiSpeed(model)
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    stages: list[Any] = []
    summaries: list[OpenStudioWrittenObject] = []
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_CoilCoolingDXMultiSpeedStageData":
            continue
        stage, summary = _new_cooling_dx_multi_speed_stage_data(
            openstudio,
            model,
            graph,
            child,
        )
        stages.append(stage)
        summaries.append(summary)
    if stages:
        coil.setStages(stages)
    summaries.append(
        OpenStudioWrittenObject(
            identifier=node.identifier,
            source_class=node.source_class,
            writer_family="terminal_components",
            openstudio_type="OS:Coil:Cooling:DX:MultiSpeed",
            name=name,
        )
    )
    return coil, tuple(summaries)


def _new_heating_dx_multi_speed(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, tuple[OpenStudioWrittenObject, ...]]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingDXMultiSpeedByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingDXMultiSpeed(model)
        coil.setName(name)
    _apply_generic_openstudio_fields(coil, node)
    stages: list[Any] = []
    summaries: list[OpenStudioWrittenObject] = []
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_CoilHeatingDXMultiSpeedStageData":
            continue
        stage, summary = _new_heating_dx_multi_speed_stage_data(
            openstudio,
            model,
            graph,
            child,
        )
        stages.append(stage)
        summaries.append(summary)
    if stages:
        coil.setStages(stages)
    summaries.append(
        OpenStudioWrittenObject(
            identifier=node.identifier,
            source_class=node.source_class,
            writer_family="terminal_components",
            openstudio_type="OS:Coil:Heating:DX:MultiSpeed",
            name=name,
        )
    )
    return coil, tuple(summaries)


def _new_cooling_dx_multi_speed_stage_data(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_stage = model.getCoilCoolingDXMultiSpeedStageDataByName(name)
    if optional_stage.is_initialized():
        stage = optional_stage.get()
    else:
        stage = openstudio.model.CoilCoolingDXMultiSpeedStageData(model)
        stage.setName(name)
    _apply_generic_openstudio_fields(stage, node)
    _set_curve_if_present(
        model,
        graph,
        stage.setTotalCoolingCapacityFunctionofTemperatureCurve,
        node,
        "TotalCoolingCapacityFunctionofTemperatureCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setTotalCoolingCapacityFunctionofFlowFractionCurve,
        node,
        "TotalCoolingCapacityFunctionofFlowFractionCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setEnergyInputRatioFunctionofTemperatureCurve,
        node,
        "EnergyInputRatioFunctionofTemperatureCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setEnergyInputRatioFunctionofFlowFractionCurve,
        node,
        "EnergyInputRatioFunctionofFlowFractionCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setPartLoadFractionCorrelationCurve,
        node,
        "PartLoadFractionCorrelationCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setWasteHeatFunctionofTemperatureCurve,
        node,
        "WasteHeatFunctionofTemperatureCurveIdentifier",
    )
    _set_default_biquadratic_curve(
        openstudio,
        model,
        stage.totalCoolingCapacityFunctionofTemperatureCurve,
        stage.setTotalCoolingCapacityFunctionofTemperatureCurve,
        f"{name} Total Cooling Capacity Temperature Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.totalCoolingCapacityFunctionofFlowFractionCurve,
        stage.setTotalCoolingCapacityFunctionofFlowFractionCurve,
        f"{name} Total Cooling Capacity Flow Fraction Curve",
    )
    _set_default_biquadratic_curve(
        openstudio,
        model,
        stage.energyInputRatioFunctionofTemperatureCurve,
        stage.setEnergyInputRatioFunctionofTemperatureCurve,
        f"{name} EIR Temperature Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.energyInputRatioFunctionofFlowFractionCurve,
        stage.setEnergyInputRatioFunctionofFlowFractionCurve,
        f"{name} EIR Flow Fraction Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.partLoadFractionCorrelationCurve,
        stage.setPartLoadFractionCorrelationCurve,
        f"{name} Part Load Fraction Curve",
    )
    return stage, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Cooling:DX:MultiSpeed:StageData",
        name=name,
    )


def _new_heating_dx_multi_speed_stage_data(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_stage = model.getCoilHeatingDXMultiSpeedStageDataByName(name)
    if optional_stage.is_initialized():
        stage = optional_stage.get()
    else:
        stage = openstudio.model.CoilHeatingDXMultiSpeedStageData(model)
        stage.setName(name)
    _apply_generic_openstudio_fields(stage, node)
    _set_curve_if_present(
        model,
        graph,
        stage.setHeatingCapacityFunctionofTemperatureCurve,
        node,
        "HeatingCapacityFunctionofTemperatureCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setHeatingCapacityFunctionofFlowFractionCurve,
        node,
        "HeatingCapacityFunctionofFlowFractionCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setEnergyInputRatioFunctionofTemperatureCurve,
        node,
        "EnergyInputRatioFunctionofTemperatureCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setEnergyInputRatioFunctionofFlowFractionCurve,
        node,
        "EnergyInputRatioFunctionofFlowFractionCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setPartLoadFractionCorrelationCurve,
        node,
        "PartLoadFractionCorrelationCurveIdentifier",
    )
    _set_curve_if_present(
        model,
        graph,
        stage.setWasteHeatFunctionofTemperatureCurve,
        node,
        "WasteHeatFunctionofTemperatureCurveIdentifier",
    )
    _set_default_biquadratic_curve(
        openstudio,
        model,
        stage.heatingCapacityFunctionofTemperatureCurve,
        stage.setHeatingCapacityFunctionofTemperatureCurve,
        f"{name} Heating Capacity Temperature Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.heatingCapacityFunctionofFlowFractionCurve,
        stage.setHeatingCapacityFunctionofFlowFractionCurve,
        f"{name} Heating Capacity Flow Fraction Curve",
    )
    _set_default_biquadratic_curve(
        openstudio,
        model,
        stage.energyInputRatioFunctionofTemperatureCurve,
        stage.setEnergyInputRatioFunctionofTemperatureCurve,
        f"{name} EIR Temperature Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.energyInputRatioFunctionofFlowFractionCurve,
        stage.setEnergyInputRatioFunctionofFlowFractionCurve,
        f"{name} EIR Flow Fraction Curve",
    )
    _set_default_quadratic_curve(
        openstudio,
        model,
        stage.partLoadFractionCorrelationCurve,
        stage.setPartLoadFractionCorrelationCurve,
        f"{name} Part Load Fraction Curve",
    )
    return stage, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:DX:MultiSpeed:StageData",
        name=name,
    )


def _set_curve_if_present(
    model: Any,
    graph: ConsoleGraph,
    setter: Any,
    node: ConsoleGraphNode,
    field_name: str,
) -> None:
    identifier = node.fields.get(field_name)
    if not identifier:
        return
    curve_node = graph.node_by_identifier(str(identifier))
    curve_spec = _CURVE_SPECS.get(curve_node.source_class)
    if curve_spec is None:
        return
    curve_class_name = curve_spec[0]
    curve_name = str(curve_node.fields.get("Name") or curve_node.identifier)
    optional_curve = getattr(model, f"get{curve_class_name}ByName")(curve_name)
    if optional_curve.is_initialized():
        setter(optional_curve.get())


def _set_default_biquadratic_curve(
    openstudio: Any,
    model: Any,
    getter: Any,
    setter: Any,
    name: str,
) -> None:
    if _is_initialized_curve(getter()):
        return
    optional_curve = model.getCurveBiquadraticByName(name)
    if optional_curve.is_initialized():
        curve = optional_curve.get()
    else:
        curve = openstudio.model.CurveBiquadratic(model)
        curve.setName(name)
        curve.setCoefficient1Constant(1.0)
        curve.setCoefficient2x(0.0)
        curve.setCoefficient3xPOW2(0.0)
        curve.setCoefficient4y(0.0)
        curve.setCoefficient5yPOW2(0.0)
        curve.setCoefficient6xTIMESY(0.0)
        curve.setMinimumValueofx(-100.0)
        curve.setMaximumValueofx(100.0)
        curve.setMinimumValueofy(-100.0)
        curve.setMaximumValueofy(100.0)
        curve.setMinimumCurveOutput(0.1)
        curve.setMaximumCurveOutput(10.0)
    setter(curve)


def _set_default_quadratic_curve(
    openstudio: Any,
    model: Any,
    getter: Any,
    setter: Any,
    name: str,
) -> None:
    if _is_initialized_curve(getter()):
        return
    optional_curve = model.getCurveQuadraticByName(name)
    if optional_curve.is_initialized():
        curve = optional_curve.get()
    else:
        curve = openstudio.model.CurveQuadratic(model)
        curve.setName(name)
        curve.setCoefficient1Constant(1.0)
        curve.setCoefficient2x(0.0)
        curve.setCoefficient3xPOW2(0.0)
        curve.setMinimumValueofx(0.0)
        curve.setMaximumValueofx(2.0)
        curve.setMinimumCurveOutput(0.1)
        curve.setMaximumCurveOutput(10.0)
    setter(curve)


def _is_initialized_curve(curve: Any) -> bool:
    is_initialized = getattr(curve, "is_initialized", None)
    if callable(is_initialized):
        return bool(is_initialized())
    initialized = getattr(curve, "initialized", None)
    if callable(initialized):
        return bool(initialized())
    return curve is not None


def _new_heating_dx_variable_refrigerant_flow(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_coil = model.getCoilHeatingDXVariableRefrigerantFlowByName(name)
    if optional_coil.is_initialized():
        coil = optional_coil.get()
    else:
        coil = openstudio.model.CoilHeatingDXVariableRefrigerantFlow(model)
        coil.setName(name)
    return coil, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="terminal_components",
        openstudio_type="OS:Coil:Heating:DX:VariableRefrigerantFlow",
        name=name,
    )
