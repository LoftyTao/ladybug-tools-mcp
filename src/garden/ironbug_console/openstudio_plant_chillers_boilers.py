"""Chiller and boiler PlantLoop component writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import (
    _set_autosizable_if_present,
    _set_if_present,
)


def _new_chiller_electric_eir(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_chiller = model.getChillerElectricEIRByName(name)
    if optional_chiller.is_initialized():
        chiller = optional_chiller.get()
    else:
        chiller = openstudio.model.ChillerElectricEIR(model)
        chiller.setName(name)
    _set_autosizable_if_present(
        chiller.setReferenceCapacity,
        chiller.autosizeReferenceCapacity,
        node,
        "ReferenceCapacity",
    )
    _set_if_present(chiller.setReferenceCOP, node, "ReferenceCOP")
    _set_if_present(
        chiller.setReferenceLeavingChilledWaterTemperature,
        node,
        "ReferenceLeavingChilledWaterTemperature",
    )
    _set_if_present(
        chiller.setReferenceEnteringCondenserFluidTemperature,
        node,
        "ReferenceEnteringCondenserFluidTemperature",
    )
    _set_autosizable_if_present(
        chiller.setReferenceChilledWaterFlowRate,
        chiller.autosizeReferenceChilledWaterFlowRate,
        node,
        "ReferenceChilledWaterFlowRate",
    )
    _set_autosizable_if_present(
        chiller.setReferenceCondenserFluidFlowRate,
        chiller.autosizeReferenceCondenserFluidFlowRate,
        node,
        "ReferenceCondenserFluidFlowRate",
    )
    _set_if_present(chiller.setChillerFlowMode, node, "ChillerFlowMode", cast=str)
    _set_if_present(
        chiller.setLeavingChilledWaterLowerTemperatureLimit,
        node,
        "LeavingChilledWaterLowerTemperatureLimit",
    )
    return chiller, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:Chiller:Electric:EIR",
        name=name,
    )


def _new_boiler_hot_water(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_boiler = model.getBoilerHotWaterByName(name)
    if optional_boiler.is_initialized():
        boiler = optional_boiler.get()
    else:
        boiler = openstudio.model.BoilerHotWater(model)
        boiler.setName(name)
    _set_if_present(boiler.setFuelType, node, "FuelType", cast=str)
    _set_autosizable_if_present(
        boiler.setNominalCapacity,
        boiler.autosizeNominalCapacity,
        node,
        "NominalCapacity",
    )
    _set_if_present(
        boiler.setNominalThermalEfficiency,
        node,
        "NominalThermalEfficiency",
    )
    return boiler, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:Boiler:HotWater",
        name=name,
    )
