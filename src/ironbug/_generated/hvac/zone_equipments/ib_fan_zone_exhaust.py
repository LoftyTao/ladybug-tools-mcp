"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_FanZoneExhaust(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_FanZoneExhaust'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/ZoneHVAC/IB_FanZoneExhaust.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ZoneEquipment',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_FanZoneExhaust_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'FanTotalEfficiency',
        'FanEfficiency',
        'PressureRise',
        'MaximumFlowRate',
        'EndUseSubcategory',
        'FlowFractionSchedule',
        'SystemAvailabilityManagerCouplingMode',
        'MinimumZoneTemperatureLimitSchedule',
        'BalancedExhaustFractionSchedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'EndUseSubcategory': 'str',
        'FanEfficiency': 'str | float | int | bool',
        'FanTotalEfficiency': 'float',
        'MaximumFlowRate': 'float',
        'PressureRise': 'float',
        'SystemAvailabilityManagerCouplingMode': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'BalancedExhaustFractionSchedule': 'IB_Schedule',
        'FlowFractionSchedule': 'IB_Schedule',
        'MinimumZoneTemperatureLimitSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_FanZoneExhaust'] = PydanticField(default='IB_FanZoneExhaust')

__all__ = [
    'IB_FanZoneExhaust',
]
