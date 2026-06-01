"""Plant heat exchanger writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_heat_exchanger_fluid_to_fluid(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_heat_exchanger = model.getHeatExchangerFluidToFluidByName(name)
    if optional_heat_exchanger.is_initialized():
        heat_exchanger = optional_heat_exchanger.get()
    else:
        heat_exchanger = openstudio.model.HeatExchangerFluidToFluid(model)
        heat_exchanger.setName(name)
    _set_autosizable_if_present(
        heat_exchanger.setLoopSupplySideDesignFlowRate,
        heat_exchanger.autosizeLoopSupplySideDesignFlowRate,
        node,
        "LoopSupplySideDesignFlowRate",
    )
    _set_autosizable_if_present(
        heat_exchanger.setLoopDemandSideDesignFlowRate,
        heat_exchanger.autosizeLoopDemandSideDesignFlowRate,
        node,
        "LoopDemandSideDesignFlowRate",
    )
    _set_if_present(
        heat_exchanger.setHeatExchangeModelType,
        node,
        "HeatExchangeModelType",
        cast=str,
    )
    _set_autosizable_if_present(
        heat_exchanger.setHeatExchangerUFactorTimesAreaValue,
        heat_exchanger.autosizeHeatExchangerUFactorTimesAreaValue,
        node,
        "HeatExchangerUFactorTimesAreaValue",
    )
    _set_if_present(
        heat_exchanger.setControlType,
        node,
        "ControlType",
        cast=str,
    )
    _set_if_present(
        heat_exchanger.setMinimumTemperatureDifferencetoActivateHeatExchanger,
        node,
        "MinimumTemperatureDifferencetoActivateHeatExchanger",
    )
    _set_if_present(
        heat_exchanger.setHeatTransferMeteringEndUseType,
        node,
        "HeatTransferMeteringEndUseType",
        cast=str,
    )
    _set_if_present(
        heat_exchanger.setComponentOverrideCoolingControlTemperatureMode,
        node,
        "ComponentOverrideCoolingControlTemperatureMode",
        cast=str,
    )
    _set_if_present(heat_exchanger.setSizingFactor, node, "SizingFactor")
    _set_if_present(
        heat_exchanger.setOperationMinimumTemperatureLimit,
        node,
        "OperationMinimumTemperatureLimit",
    )
    _set_if_present(
        heat_exchanger.setOperationMaximumTemperatureLimit,
        node,
        "OperationMaximumTemperatureLimit",
    )
    return heat_exchanger, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:HeatExchanger:FluidToFluid",
        name=name,
    )
