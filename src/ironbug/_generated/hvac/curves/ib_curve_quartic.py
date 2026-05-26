"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CurveQuartic(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CurveQuartic'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Curves/IB_CurveQuartic.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Curves'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Curve',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_Curve2D',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CurveQuartic_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Coefficient1Constant',
        'Coefficient2x',
        'Coefficient3xPOW2',
        'Coefficient4xPOW3',
        'Coefficient5xPOW4',
        'MinimumValueofx',
        'MaximumValueofx',
        'MinimumCurveOutput',
        'MaximumCurveOutput',
        'InputUnitTypeforX',
        'OutputUnitType',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient1Constant': 'float',
        'Coefficient2x': 'float',
        'Coefficient3xPOW2': 'str | float | int | bool',
        'Coefficient4xPOW3': 'str | float | int | bool',
        'Coefficient5xPOW4': 'str | float | int | bool',
        'InputUnitTypeforX': 'str',
        'MaximumValueofx': 'float',
        'MinimumValueofx': 'float',
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
    type: Literal['IB_CurveQuartic'] = PydanticField(default='IB_CurveQuartic')

__all__ = [
    'IB_CurveQuartic',
]
