"""Solar collector writers for the Python Ironbug Console."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_special_objects import (
    _default_surface,
    _new_special_openstudio_object,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


def _new_solar_collector_flat_plate_water(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    collector, summary = _new_generic_openstudio_object(openstudio, model, node)
    _set_collector_surface(model, collector, node)
    _apply_flat_plate_performance(collector, graph, node)
    return collector, summary


def _new_solar_collector_flat_plate_photovoltaic_thermal(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    collector, summary = _new_generic_openstudio_object(openstudio, model, node)
    generator = _pvt_generator(openstudio, model, graph, node)
    if generator is not None:
        collector.setGeneratorPhotovoltaic(generator)
        _set_pvt_surface(openstudio, model, collector, generator, node)
    else:
        _set_collector_surface(model, collector, node)
    _apply_pvt_performance(openstudio, model, collector, graph, node)
    return collector, summary


def _set_collector_surface(model: Any, collector: Any, node: ConsoleGraphNode) -> None:
    surface_name = node.fields.get("SurfaceID")
    if not surface_name:
        return
    for getter_name in ("getShadingSurfaceByName", "getSurfaceByName"):
        getter = getattr(model, getter_name, None)
        if getter is None:
            continue
        optional_surface = getter(str(surface_name))
        if optional_surface.is_initialized():
            collector.setSurface(optional_surface.get())
            return


def _set_pvt_surface(
    openstudio: Any,
    model: Any,
    collector: Any,
    generator: Any,
    node: ConsoleGraphNode,
) -> None:
    surface = _pvt_surface_from_node(model, node) or _pvt_surface_from_generator(
        model,
        generator,
    )
    if surface is None:
        surface = _first_outdoor_roof_surface(model)
    if surface is None:
        surface = _get_or_create_pvt_surface(
            openstudio,
            model,
            f"{node.fields.get('Name') or node.identifier} Surface",
        )
    generator.setSurface(surface)
    collector.setSurface(surface)


def _pvt_surface_from_node(model: Any, node: ConsoleGraphNode) -> Any | None:
    surface_name = node.fields.get("SurfaceID")
    if not surface_name:
        return None
    optional_surface = model.getSurfaceByName(str(surface_name))
    if optional_surface.is_initialized():
        return optional_surface.get()
    return None


def _pvt_surface_from_generator(model: Any, generator: Any) -> Any | None:
    surface = generator.surface()
    if not surface.is_initialized():
        return None
    optional_surface = model.getSurfaceByName(surface.get().nameString())
    if optional_surface.is_initialized():
        return optional_surface.get()
    return None


def _first_outdoor_roof_surface(model: Any) -> Any | None:
    for surface in model.getSurfaces():
        try:
            if (
                surface.surfaceType() == "RoofCeiling"
                and surface.outsideBoundaryCondition() == "Outdoors"
                and surface.sunExposure() == "SunExposed"
            ):
                return surface
        except AttributeError:
            continue
    return None


def _get_or_create_pvt_surface(openstudio: Any, model: Any, name: str) -> Any:
    optional_surface = model.getSurfaceByName(name)
    if optional_surface.is_initialized():
        return optional_surface.get()
    surface = _default_surface(openstudio, model, name)
    surface.setSurfaceType("RoofCeiling")
    return surface


def _apply_flat_plate_performance(
    collector: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> None:
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_SolarCollectorPerformanceFlatPlate":
            continue
        performance = collector.solarCollectorPerformance()
        if child.fields.get("Name") and hasattr(performance, "setName"):
            performance.setName(str(child.fields["Name"]))
        _apply_generic_openstudio_fields(performance, child)
        return


def _pvt_generator(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> Any | None:
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class != "IB_GeneratorPhotovoltaic":
            continue
        name = str(child.fields.get("Name") or child.identifier)
        optional_generator = model.getGeneratorPhotovoltaicByName(name)
        if optional_generator.is_initialized():
            return optional_generator.get()
        generator, _summary = _new_special_openstudio_object(openstudio, model, child)
        return generator
    return None


def _apply_pvt_performance(
    openstudio: Any,
    model: Any,
    collector: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> None:
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class not in {
            "IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT",
            "IB_SolarCollectorPerformancePhotovoltaicThermalSimple",
        }:
            continue
        performance, _summary = _new_generic_openstudio_object(
            openstudio,
            model,
            child,
        )
        collector.setSolarCollectorPerformance(performance)
        return
