"""OpenStudio ElectricLoadCenter writers for the Python Ironbug Console."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_factory import (
    _new_generic_openstudio_object,
)
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_generic_families import _generic_writer_family
from garden.ironbug_console.openstudio_special_objects import (
    _default_shading_surface,
    _new_special_openstudio_object,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


_GENERATOR_SOURCE_CLASSES = frozenset(
    {
        "IB_GeneratorMicroTurbine",
        "IB_GeneratorPVWatts",
        "IB_GeneratorPhotovoltaic",
        "IB_GeneratorWindTurbine",
    }
)
_INVERTER_SOURCE_CLASSES = frozenset(
    {
        "IB_ElectricLoadCenterInverterLookUpTable",
        "IB_ElectricLoadCenterInverterPVWatts",
        "IB_ElectricLoadCenterInverterSimple",
    }
)
_STORAGE_SOURCE_CLASSES = frozenset(
    {
        "IB_ElectricLoadCenterStorageLiIonNMCBattery",
        "IB_ElectricLoadCenterStorageSimple",
    }
)
_STORAGE_CONVERTER_SOURCE_CLASSES = frozenset(
    {
        "IB_ElectricLoadCenterStorageConverter",
    }
)


def _write_generator_pv_watts(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    component, summary = _new_special_openstudio_object(
        openstudio,
        model,
        _pvwatts_node_with_normalized_losses(node),
    )
    system_losses = node.fields.get("SystemLosses")
    if system_losses is not None:
        component.setSystemLosses(_pvwatts_system_losses(system_losses))
    return summary


def _write_generator_photovoltaic(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    performance_node = _photovoltaic_performance_child(graph, node)
    factory_name = {
        "IB_PhotovoltaicPerformanceEquivalentOneDiode": "equivalentOneDiode",
        "IB_PhotovoltaicPerformanceSandia": "sandia",
        "IB_PhotovoltaicPerformanceSimple": "simple",
    }.get(
        performance_node.source_class if performance_node is not None else "",
        "simple",
    )
    component = getattr(openstudio.model.GeneratorPhotovoltaic, factory_name)(model)
    component.setName(name)
    _apply_generic_openstudio_fields(component, node)
    _apply_photovoltaic_performance(component, performance_node)
    surface = _photovoltaic_surface(openstudio, model, node)
    if surface is not None:
        component.setSurface(surface)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family=_generic_writer_family(node.source_class),
        openstudio_type=component.iddObjectType().valueDescription(),
        name=name,
    )


def _write_electric_load_center_distribution(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    distribution, summary = _new_generic_openstudio_object(openstudio, model, node)
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        child_name = str(child.fields.get("Name") or child.identifier)
        if child.source_class in _GENERATOR_SOURCE_CLASSES:
            generator = _model_object_by_name(model, child.source_class, child_name)
            if generator is not None:
                distribution.addGenerator(generator)
        elif child.source_class in _INVERTER_SOURCE_CLASSES:
            inverter = _model_object_by_name(model, child.source_class, child_name)
            if inverter is not None:
                distribution.setInverter(inverter)
        elif child.source_class in _STORAGE_SOURCE_CLASSES:
            storage = _model_object_by_name(model, child.source_class, child_name)
            if storage is not None:
                distribution.setElectricalStorage(storage)
        elif child.source_class in _STORAGE_CONVERTER_SOURCE_CLASSES:
            converter = _model_object_by_name(model, child.source_class, child_name)
            if converter is not None:
                distribution.setStorageConverter(converter)
    return summary


def _write_electric_load_center_storage_converter(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    converter, summary = _new_generic_openstudio_object(openstudio, model, node)
    simple_efficiency = node.fields.get("SimpleFixedEfficiency")
    if simple_efficiency is not None:
        converter.setSimpleFixedEfficiency(float(simple_efficiency))
    return summary


def _pvwatts_node_with_normalized_losses(
    node: ConsoleGraphNode,
) -> ConsoleGraphNode:
    system_losses = node.fields.get("SystemLosses")
    if system_losses is None:
        return node
    return replace(
        node,
        fields={
            **dict(node.fields),
            "SystemLosses": _pvwatts_system_losses(system_losses),
        },
    )


def _pvwatts_system_losses(value: Any) -> float:
    numeric = float(value)
    if numeric > 1.0:
        return numeric / 100.0
    return numeric


def _photovoltaic_performance_child(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> ConsoleGraphNode | None:
    for child_identifier in node.children:
        child = graph.node_by_identifier(str(child_identifier))
        if child.source_class in {
            "IB_PhotovoltaicPerformanceEquivalentOneDiode",
            "IB_PhotovoltaicPerformanceSandia",
            "IB_PhotovoltaicPerformanceSimple",
        }:
            return child
    return None


def _apply_photovoltaic_performance(
    generator: Any,
    performance_node: ConsoleGraphNode | None,
) -> None:
    if performance_node is None:
        return
    performance = generator.photovoltaicPerformance()
    name = performance_node.fields.get("Name") or performance_node.identifier
    if name and hasattr(performance, "setName"):
        performance.setName(str(name))
    _apply_generic_openstudio_fields(performance, performance_node)


def _photovoltaic_surface(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> Any | None:
    surface_name = node.fields.get("SurfaceID")
    if surface_name:
        for getter_name in ("getShadingSurfaceByName", "getSurfaceByName"):
            getter = getattr(model, getter_name, None)
            if getter is None:
                continue
            optional_surface = getter(str(surface_name))
            if optional_surface.is_initialized():
                return optional_surface.get()
    return _default_shading_surface(openstudio, model, f"{node.identifier} Surface")


def _model_object_by_name(
    model: Any,
    source_class: str,
    name: str,
) -> Any | None:
    getter_name = {
        "IB_ElectricLoadCenterInverterLookUpTable": (
            "getElectricLoadCenterInverterLookUpTableByName"
        ),
        "IB_ElectricLoadCenterInverterPVWatts": (
            "getElectricLoadCenterInverterPVWattsByName"
        ),
        "IB_ElectricLoadCenterInverterSimple": (
            "getElectricLoadCenterInverterSimpleByName"
        ),
        "IB_ElectricLoadCenterStorageConverter": (
            "getElectricLoadCenterStorageConverterByName"
        ),
        "IB_ElectricLoadCenterStorageLiIonNMCBattery": (
            "getElectricLoadCenterStorageLiIonNMCBatteryByName"
        ),
        "IB_ElectricLoadCenterStorageSimple": (
            "getElectricLoadCenterStorageSimpleByName"
        ),
        "IB_GeneratorMicroTurbine": "getGeneratorMicroTurbineByName",
        "IB_GeneratorPVWatts": "getGeneratorPVWattsByName",
        "IB_GeneratorPhotovoltaic": "getGeneratorPhotovoltaicByName",
        "IB_GeneratorWindTurbine": "getGeneratorWindTurbineByName",
    }.get(source_class)
    if getter_name is None:
        return None
    getter = getattr(model, getter_name, None)
    if getter is None:
        return None
    optional_object = getter(name)
    if not optional_object.is_initialized():
        return None
    return optional_object.get()
