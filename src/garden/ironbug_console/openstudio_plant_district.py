"""District PlantLoop source writers for Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import _set_autosizable_if_present


def _new_district_cooling(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_source = model.getDistrictCoolingByName(name)
    if optional_source.is_initialized():
        source = optional_source.get()
    else:
        source = openstudio.model.DistrictCooling(model)
        source.setName(name)
    _set_autosizable_if_present(
        source.setNominalCapacity,
        source.autosizeNominalCapacity,
        node,
        "NominalCapacity",
    )
    return source, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:DistrictCooling",
        name=name,
    )


def _new_district_heating_water(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_source = model.getDistrictHeatingWaterByName(name)
    if optional_source.is_initialized():
        source = optional_source.get()
    else:
        source = openstudio.model.DistrictHeatingWater(model)
        source.setName(name)
    _set_autosizable_if_present(
        source.setNominalCapacity,
        source.autosizeNominalCapacity,
        node,
        "NominalCapacity",
    )
    return source, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:DistrictHeating:Water",
        name=name,
    )
