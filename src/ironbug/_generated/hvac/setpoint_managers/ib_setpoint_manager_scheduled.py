"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_SetpointManagerScheduled(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_SetpointManagerScheduled'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/SetpointManagers/IB_SetpointManagerScheduled.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_SetpointManager',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_SetpointManagerScheduled_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Value',
        'IsTemperature',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ControlVariable',
        'Schedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ControlVariable': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'Schedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'IsTemperature': 'bool',
        'Value': 'double',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_SetpointManagerScheduled'] = PydanticField(default='IB_SetpointManagerScheduled')
    Value: float | None = PydanticField(default=None)
    IsTemperature: bool | None = PydanticField(default=None)

__all__ = [
    'IB_SetpointManagerScheduled',
]
