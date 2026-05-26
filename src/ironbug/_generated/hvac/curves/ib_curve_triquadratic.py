"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CurveTriquadratic(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CurveTriquadratic'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Curves/IB_CurveTriquadratic.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Curves'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Curve',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CurveTriquadratic_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Coefficient1Constant',
        'Coefficient2xPOW2',
        'Coefficient3x',
        'Coefficient4yPOW2',
        'Coefficient5y',
        'Coefficient6zPOW2',
        'Coefficient7z',
        'Coefficient8xPOW2TIMESYPOW2',
        'Coefficient9xTIMESY',
        'Coefficient10xTIMESYPOW2',
        'Coefficient11xPOW2TIMESY',
        'Coefficient12xPOW2TIMESZPOW2',
        'Coefficient13xTIMESZ',
        'Coefficient14xTIMESZPOW2',
        'Coefficient15xPOW2TIMESZ',
        'Coefficient16yPOW2TIMESZPOW2',
        'Coefficient17yTIMESZ',
        'Coefficient18yTIMESZPOW2',
        'Coefficient19yPOW2TIMESZ',
        'Coefficient20xPOW2TIMESYPOW2TIMESZPOW2',
        'Coefficient21xPOW2TIMESYPOW2TIMESZ',
        'Coefficient22xPOW2TIMESYTIMESZPOW2',
        'Coefficient23xTIMESYPOW2TIMESZPOW2',
        'Coefficient24xPOW2TIMESYTIMESZ',
        'Coefficient25xTIMESYPOW2TIMESZ',
        'Coefficient26xTIMESYTIMESZPOW2',
        'Coefficient27xTIMESYTIMESZ',
        'MinimumValueofx',
        'MaximumValueofx',
        'MinimumValueofy',
        'MaximumValueofy',
        'MinimumValueofz',
        'MaximumValueofz',
        'MinimumCurveOutput',
        'MaximumCurveOutput',
        'InputUnitTypeforX',
        'InputUnitTypeforY',
        'InputUnitTypeforZ',
        'OutputUnitType',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient10xTIMESYPOW2': 'str | float | int | bool',
        'Coefficient11xPOW2TIMESY': 'str | float | int | bool',
        'Coefficient12xPOW2TIMESZPOW2': 'str | float | int | bool',
        'Coefficient13xTIMESZ': 'str | float | int | bool',
        'Coefficient14xTIMESZPOW2': 'str | float | int | bool',
        'Coefficient15xPOW2TIMESZ': 'str | float | int | bool',
        'Coefficient16yPOW2TIMESZPOW2': 'str | float | int | bool',
        'Coefficient17yTIMESZ': 'str | float | int | bool',
        'Coefficient18yTIMESZPOW2': 'str | float | int | bool',
        'Coefficient19yPOW2TIMESZ': 'str | float | int | bool',
        'Coefficient1Constant': 'float',
        'Coefficient20xPOW2TIMESYPOW2TIMESZPOW2': 'str | float | int | bool',
        'Coefficient21xPOW2TIMESYPOW2TIMESZ': 'str | float | int | bool',
        'Coefficient22xPOW2TIMESYTIMESZPOW2': 'str | float | int | bool',
        'Coefficient23xTIMESYPOW2TIMESZPOW2': 'str | float | int | bool',
        'Coefficient24xPOW2TIMESYTIMESZ': 'str | float | int | bool',
        'Coefficient25xTIMESYPOW2TIMESZ': 'str | float | int | bool',
        'Coefficient26xTIMESYTIMESZPOW2': 'str | float | int | bool',
        'Coefficient27xTIMESYTIMESZ': 'str | float | int | bool',
        'Coefficient2xPOW2': 'str | float | int | bool',
        'Coefficient3x': 'float',
        'Coefficient4yPOW2': 'str | float | int | bool',
        'Coefficient5y': 'float',
        'Coefficient6zPOW2': 'str | float | int | bool',
        'Coefficient7z': 'float',
        'Coefficient8xPOW2TIMESYPOW2': 'str | float | int | bool',
        'Coefficient9xTIMESY': 'str | float | int | bool',
        'InputUnitTypeforX': 'str',
        'InputUnitTypeforY': 'str',
        'InputUnitTypeforZ': 'str',
        'MaximumValueofx': 'float',
        'MaximumValueofy': 'float',
        'MaximumValueofz': 'float',
        'MinimumValueofx': 'float',
        'MinimumValueofy': 'float',
        'MinimumValueofz': 'float',
        'OutputUnitType': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CurveTriquadratic'] = PydanticField(default='IB_CurveTriquadratic')

__all__ = [
    'IB_CurveTriquadratic',
]
