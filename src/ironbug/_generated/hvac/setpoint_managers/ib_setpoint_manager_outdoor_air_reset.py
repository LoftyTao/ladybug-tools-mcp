"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_SetpointManagerOutdoorAirReset(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_SetpointManagerOutdoorAirReset'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/SetpointManagers/IB_SetpointManagerOutdoorAirReset.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_SetpointManager',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_SetpointManagerOutdoorAirReset_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ControlVariable',
        'SetpointatOutdoorLowTemperature',
        'OutdoorLowTemperature',
        'SetpointatOutdoorHighTemperature',
        'OutdoorHighTemperature',
        'Schedule',
        'SetpointatOutdoorLowTemperature2',
        'OutdoorLowTemperature2',
        'SetpointatOutdoorHighTemperature2',
        'OutdoorHighTemperature2',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ControlVariable': 'str',
        'OutdoorHighTemperature': 'float',
        'OutdoorHighTemperature2': 'float',
        'OutdoorLowTemperature': 'float',
        'OutdoorLowTemperature2': 'float',
        'SetpointatOutdoorHighTemperature': 'float',
        'SetpointatOutdoorHighTemperature2': 'float',
        'SetpointatOutdoorLowTemperature': 'float',
        'SetpointatOutdoorLowTemperature2': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'Schedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_SetpointManagerOutdoorAirReset'] = PydanticField(default='IB_SetpointManagerOutdoorAirReset')

__all__ = [
    'IB_SetpointManagerOutdoorAirReset',
]
