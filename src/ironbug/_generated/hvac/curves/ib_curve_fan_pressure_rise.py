"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CurveFanPressureRise(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CurveFanPressureRise'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Curves/IB_CurveFanPressureRise.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Curves'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Curve',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CurveFanPressureRise_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Coefficient1C1',
        'Coefficient2C2',
        'Coefficient3C3',
        'Coefficient4C4',
        'MinimumValueofQfan',
        'MaximumValueofQfan',
        'MinimumValueofPsm',
        'MaximumValueofPsm',
        'MinimumCurveOutput',
        'MaximumCurveOutput',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'Coefficient1C1': 'float',
        'Coefficient2C2': 'float',
        'Coefficient3C3': 'float',
        'Coefficient4C4': 'float',
        'MaximumValueofPsm': 'float',
        'MaximumValueofQfan': 'float',
        'MinimumValueofPsm': 'float',
        'MinimumValueofQfan': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CurveFanPressureRise'] = PydanticField(default='IB_CurveFanPressureRise')

__all__ = [
    'IB_CurveFanPressureRise',
]
