"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_GeneratorWindTurbine(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_GeneratorWindTurbine'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ElectricLoadCenter/IB_GeneratorWindTurbine.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Generator',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_GeneratorWindTurbine_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'RotorType',
        'PowerControl',
        'RatedRotorSpeed',
        'RotorDiameter',
        'OverallHeight',
        'NumberofBlades',
        'RatedPower',
        'RatedWindSpeed',
        'CutInWindSpeed',
        'CutOutWindSpeed',
        'FractionSystemEfficiency',
        'MaximumTipSpeedRatio',
        'MaximumPowerCoefficient',
        'AnnualLocalAverageWindSpeed',
        'HeightforLocalAverageWindSpeed',
        'BladeChordArea',
        'BladeDragCoefficient',
        'BladeLiftCoefficient',
        'PowerCoefficientC1',
        'PowerCoefficientC2',
        'PowerCoefficientC3',
        'PowerCoefficientC4',
        'PowerCoefficientC5',
        'PowerCoefficientC6',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AnnualLocalAverageWindSpeed': 'float',
        'BladeChordArea': 'float',
        'BladeDragCoefficient': 'float',
        'BladeLiftCoefficient': 'float',
        'CutInWindSpeed': 'float',
        'CutOutWindSpeed': 'float',
        'FractionSystemEfficiency': 'float',
        'HeightforLocalAverageWindSpeed': 'float',
        'MaximumPowerCoefficient': 'float',
        'MaximumTipSpeedRatio': 'float',
        'NumberofBlades': 'float',
        'OverallHeight': 'float',
        'PowerCoefficientC1': 'float',
        'PowerCoefficientC2': 'float',
        'PowerCoefficientC3': 'float',
        'PowerCoefficientC4': 'float',
        'PowerCoefficientC5': 'float',
        'PowerCoefficientC6': 'float',
        'PowerControl': 'str',
        'RatedPower': 'float',
        'RatedRotorSpeed': 'float',
        'RatedWindSpeed': 'float',
        'RotorDiameter': 'float',
        'RotorType': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_GeneratorWindTurbine'] = PydanticField(default='IB_GeneratorWindTurbine')

__all__ = [
    'IB_GeneratorWindTurbine',
]
