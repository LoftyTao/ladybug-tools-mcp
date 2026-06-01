"""Writer-family source-class maps for the Python Ironbug Console."""

from __future__ import annotations

from garden.ironbug_console.writer_registry_explicit_families import (
    FIRST_WRITER_FAMILY_NAMES,
    _EXPLICIT_IMPLEMENTED_SOURCE_CLASSES,
)
from garden.ironbug_console.writer_registry_generic_families import (
    _GENERIC_OPENSTUDIO_WRITER_SOURCE_CLASSES,
)
from garden.ironbug_console.writer_registry_openstudio_families import (
    _OPENSTUDIO_OBJECT_SOURCE_CLASSES,
)

_GENERIC_SOURCE_CLASS_SET = frozenset(_GENERIC_OPENSTUDIO_WRITER_SOURCE_CLASSES)
_SPECIAL_OPENSTUDIO_WRITER_SOURCE_CLASSES = tuple(
    source_class
    for source_class in _OPENSTUDIO_OBJECT_SOURCE_CLASSES
    if source_class not in _GENERIC_SOURCE_CLASS_SET
)

_IMPLEMENTED_SOURCE_CLASSES: dict[str, str] = {
    **_EXPLICIT_IMPLEMENTED_SOURCE_CLASSES,
    **_OPENSTUDIO_OBJECT_SOURCE_CLASSES,
}
_FUTURE_SOURCE_CLASSES: dict[str, str] = {}


def known_source_class_families() -> dict[str, str]:
    """Return all source classes the Python Console can classify today."""

    return {**_FUTURE_SOURCE_CLASSES, **_IMPLEMENTED_SOURCE_CLASSES}
