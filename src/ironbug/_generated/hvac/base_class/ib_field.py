"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_Field(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_Field'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/BaseClass/IB_Field.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.BaseClass'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = ()
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'FullName',
        'PerfectName',
        'NickName',
        'GetterMethodName',
        'SetterMethodName',
        'SetterMethod',
        'DataTypeName',
        'IsHidden',
        'ValidData',
        'Description',
        'DetailedDescription',
        'UnitSI',
        'UnitIP',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'FullName',
        'DataTypeName',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'DataTypeName': 'string',
        'Description': 'string',
        'DetailedDescription': 'string',
        'FullName': 'string',
        'GetterMethodName': 'string',
        'IsHidden': 'bool',
        'NickName': 'string',
        'PerfectName': 'string',
        'SetterMethod': 'MethodInfo',
        'SetterMethodName': 'string',
        'UnitIP': 'string',
        'UnitSI': 'string',
        'ValidData': 'IEnumerable<string>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'DataTypeName': 'string',
        'FullName': 'string',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_Field'] = PydanticField(default='IB_Field')
    FullName: str | None = PydanticField(default=None)
    PerfectName: str | None = PydanticField(default=None)
    NickName: str | None = PydanticField(default=None)
    GetterMethodName: str | None = PydanticField(default=None)
    SetterMethodName: str | None = PydanticField(default=None)
    SetterMethod: Any = PydanticField(default=None)
    DataTypeName: str | None = PydanticField(default=None)
    IsHidden: bool | None = PydanticField(default=None)
    ValidData: Any = PydanticField(default=None)
    Description: str | None = PydanticField(default=None)
    DetailedDescription: str | None = PydanticField(default=None)
    UnitSI: str | None = PydanticField(default=None)
    UnitIP: str | None = PydanticField(default=None)

__all__ = [
    'IB_Field',
]
