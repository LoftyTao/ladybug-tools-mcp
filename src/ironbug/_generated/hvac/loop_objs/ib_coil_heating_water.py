"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilHeatingWater(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilHeatingWater'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingWater.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilHeatingBasic',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilHeatingWater_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'AvailableSchedule',
        'UFactorTimesAreaValue',
        'MaximumWaterFlowRate',
        'PerformanceInputMethod',
        'RatedCapacity',
        'RatedInletWaterTemperature',
        'RatedInletAirTemperature',
        'RatedOutletWaterTemperature',
        'RatedOutletAirTemperature',
        'RatedRatioForAirAndWaterConvection',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'MaximumWaterFlowRate': 'float',
        'PerformanceInputMethod': 'str',
        'RatedCapacity': 'float',
        'RatedInletAirTemperature': 'float',
        'RatedInletWaterTemperature': 'float',
        'RatedOutletAirTemperature': 'float',
        'RatedOutletWaterTemperature': 'float',
        'RatedRatioForAirAndWaterConvection': 'float',
        'UFactorTimesAreaValue': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'AvailableSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilHeatingWater'] = PydanticField(default='IB_CoilHeatingWater')

__all__ = [
    'IB_CoilHeatingWater',
]
