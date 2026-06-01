"""OpenStudio postprocess steps mirrored from C# IB_Utility.SaveHVAC."""

from __future__ import annotations

from typing import Any


DRYBULB_OUTPUT_VARIABLE = "Site Outdoor Air Drybulb Temperature"
SETPOINT_NOT_MET_TOLERANCE = 1.11


def apply_csharp_save_hvac_postprocess(openstudio: Any, model: Any) -> None:
    """Apply fixed model edits that C# Ironbug SaveHVAC always performs."""

    _ensure_hourly_drybulb_output(openstudio, model)
    _convert_internal_source_constructions(openstudio, model)
    tolerances = model.getOutputControlReportingTolerances()
    tolerances.setToleranceforTimeCoolingSetpointNotMet(
        SETPOINT_NOT_MET_TOLERANCE
    )
    tolerances.setToleranceforTimeHeatingSetpointNotMet(
        SETPOINT_NOT_MET_TOLERANCE
    )


def _ensure_hourly_drybulb_output(openstudio: Any, model: Any) -> None:
    for output_variable in model.getOutputVariables():
        if output_variable.variableName() == DRYBULB_OUTPUT_VARIABLE:
            output_variable.setReportingFrequency("Hourly")
            return
    output_variable = openstudio.model.OutputVariable(DRYBULB_OUTPUT_VARIABLE, model)
    output_variable.setReportingFrequency("Hourly")


def _convert_internal_source_constructions(openstudio: Any, model: Any) -> None:
    optional_material = model.getMaterialByName("INTERNAL SOURCE")
    if not optional_material.is_initialized():
        return
    material = optional_material.get()
    for source in list(material.sources()):
        optional_construction = source.to_Construction()
        if not optional_construction.is_initialized():
            continue
        construction = optional_construction.get()
        _convert_internal_source_construction(openstudio, model, construction)


def _convert_internal_source_construction(
    openstudio: Any,
    model: Any,
    construction: Any,
) -> None:
    layers = list(construction.layers())
    source_index = _internal_source_layer_index(layers)
    if source_index is None:
        return

    name = construction.nameString()
    converted = openstudio.model.ConstructionWithInternalSource(model)
    converted.setName(name)
    for layer in layers[:source_index] + layers[source_index + 1 :]:
        converted.insertLayer(converted.numLayers(), layer)
    converted.setSourcePresentAfterLayerNumber(source_index)
    reversed_converted = converted.reverseConstructionWithInternalSource()

    sources = list(construction.sources())
    for surface in _surface_sources(sources):
        surface.setConstruction(converted)
        optional_adjacent = surface.adjacentSurface()
        if optional_adjacent.is_initialized():
            optional_adjacent.get().setConstruction(reversed_converted)

    for defaults in _default_surface_construction_sources(sources):
        _replace_default_construction(
            defaults.wallConstruction,
            defaults.setWallConstruction,
            name,
            converted,
        )
        _replace_default_construction(
            defaults.floorConstruction,
            defaults.setFloorConstruction,
            name,
            converted,
        )
        _replace_default_construction(
            defaults.roofCeilingConstruction,
            defaults.setRoofCeilingConstruction,
            name,
            converted,
        )

    construction.remove()


def _internal_source_layer_index(layers: list[Any]) -> int | None:
    for index, layer in enumerate(layers):
        if layer.nameString() == "INTERNAL SOURCE":
            return index
    return None


def _surface_sources(sources: list[Any]) -> list[Any]:
    surfaces: list[Any] = []
    for source in sources:
        optional_surface = source.to_Surface()
        if optional_surface.is_initialized():
            surfaces.append(optional_surface.get())
    return surfaces


def _default_surface_construction_sources(sources: list[Any]) -> list[Any]:
    defaults: list[Any] = []
    for source in sources:
        optional_defaults = source.to_DefaultSurfaceConstructions()
        if optional_defaults.is_initialized():
            defaults.append(optional_defaults.get())
    return defaults


def _replace_default_construction(
    getter: Any,
    setter: Any,
    old_name: str,
    converted: Any,
) -> None:
    optional_construction = getter()
    if (
        optional_construction.is_initialized()
        and optional_construction.get().nameString() == old_name
    ):
        setter(converted)
