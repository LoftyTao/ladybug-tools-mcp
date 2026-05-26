"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CurveBicubic(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CurveBicubic'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Curves/IB_CurveBicubic.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Curves'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Curve',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_Curve3D',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CurveBicubic_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Coefficient1Constant',
        'Coefficient2x',
        'Coefficient3xPOW2',
        'Coefficient4y',
        'Coefficient5yPOW2',
        'Coefficient6xTIMESY',
        'Coefficient7xPOW3',
        'Coefficient8yPOW3',
        'Coefficient9xPOW2TIMESY',
        'Coefficient10xTIMESYPOW2',
        'MinimumValueofx',
        'MaximumValueofx',
        'MinimumValueofy',
        'MaximumValueofy',
        'MinimumCurveOutput',
        'MaximumCurveOutput',
        'InputUnitTypeforX',
        'InputUnitTypeforY',
        'OutputUnitType',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient10xTIMESYPOW2': 'str | float | int | bool',
        'Coefficient1Constant': 'float',
        'Coefficient2x': 'float',
        'Coefficient3xPOW2': 'str | float | int | bool',
        'Coefficient4y': 'float',
        'Coefficient5yPOW2': 'str | float | int | bool',
        'Coefficient6xTIMESY': 'str | float | int | bool',
        'Coefficient7xPOW3': 'str | float | int | bool',
        'Coefficient8yPOW3': 'str | float | int | bool',
        'Coefficient9xPOW2TIMESY': 'str | float | int | bool',
        'InputUnitTypeforX': 'str',
        'InputUnitTypeforY': 'str',
        'MaximumValueofx': 'float',
        'MaximumValueofy': 'float',
        'MinimumValueofx': 'float',
        'MinimumValueofy': 'float',
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
    type: Literal['IB_CurveBicubic'] = PydanticField(default='IB_CurveBicubic')

__all__ = [
    'IB_CurveBicubic',
]
