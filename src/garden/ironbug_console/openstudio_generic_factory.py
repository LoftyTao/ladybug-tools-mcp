"""Generic OpenStudio object factory for reflected source classes."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_generic_families import _generic_writer_family
from garden.ironbug_console.openstudio_generic_fields import (
    _apply_generic_openstudio_fields,
)
from garden.ironbug_console.openstudio_source_classes import (
    GENERIC_OPENSTUDIO_CLASS_NAMES as _GENERIC_OPENSTUDIO_CLASS_NAMES,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject


def _new_generic_openstudio_object(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    class_name = _GENERIC_OPENSTUDIO_CLASS_NAMES[node.source_class]
    name = str(node.fields.get("Name") or node.identifier)
    getter = getattr(model, f"get{class_name}ByName", None)
    if getter is not None:
        optional_object = getter(name)
        if optional_object.is_initialized():
            component = optional_object.get()
        else:
            component = getattr(openstudio.model, class_name)(model)
    else:
        component = getattr(openstudio.model, class_name)(model)
    if hasattr(component, "setName"):
        component.setName(name)
    _apply_generic_openstudio_fields(component, node)
    return component, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family=_generic_writer_family(node.source_class),
        openstudio_type=component.iddObjectType().valueDescription(),
        name=name,
    )
