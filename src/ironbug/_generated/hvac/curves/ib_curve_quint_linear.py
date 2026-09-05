"""Incremental Ironbug HVAC source mirror."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CurveQuintLinear(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CurveQuintLinear'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Curves/IB_CurveQuintLinear.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Curves'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Curve',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CurveQuintLinear_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Name',
        'Coefficient1Constant',
        'Coefficient2v',
        'Coefficient3w',
        'Coefficient4x',
        'Coefficient5y',
        'Coefficient6z',
        'MinimumValueofv',
        'MaximumValueofv',
        'MinimumValueofw',
        'MaximumValueofw',
        'MinimumValueofx',
        'MaximumValueofx',
        'MinimumValueofy',
        'MaximumValueofy',
        'MinimumValueofz',
        'MaximumValueofz',
        'MinimumCurveOutput',
        'MaximumCurveOutput',
        'InputUnitTypeforv',
        'InputUnitTypeforw',
        'InputUnitTypeforx',
        'InputUnitTypefory',
        'InputUnitTypeforz',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient1Constant': 'float',
        'Coefficient2v': 'float',
        'Coefficient3w': 'float',
        'Coefficient4x': 'float',
        'Coefficient5y': 'float',
        'Coefficient6z': 'float',
        'InputUnitTypeforv': 'str',
        'InputUnitTypeforw': 'str',
        'InputUnitTypeforx': 'str',
        'InputUnitTypefory': 'str',
        'InputUnitTypeforz': 'str',
        'MaximumCurveOutput': 'float',
        'MaximumValueofv': 'float',
        'MaximumValueofw': 'float',
        'MaximumValueofx': 'float',
        'MaximumValueofy': 'float',
        'MaximumValueofz': 'float',
        'MinimumCurveOutput': 'float',
        'MinimumValueofv': 'float',
        'MinimumValueofw': 'float',
        'MinimumValueofx': 'float',
        'MinimumValueofy': 'float',
        'MinimumValueofz': 'float',
        'Name': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CurveQuintLinear'] = PydanticField(default='IB_CurveQuintLinear')

__all__ = [
    'IB_CurveQuintLinear',
]
