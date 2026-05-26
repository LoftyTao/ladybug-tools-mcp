"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_AirLoopHVAC(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_AirLoopHVAC'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Loops/IB_AirLoopHVAC.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Loop',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_AirLoopHVAC_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'SizingSystem',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'SizingSystem',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'DesignSupplyAirFlowRate',
        'DesignReturnAirFlowFractionofSupplyAirFlow',
        'AvailabilitySchedule',
        'NightCycleControlType',
        'AvailabilityManagers',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'DesignReturnAirFlowFractionofSupplyAirFlow': 'float',
        'DesignSupplyAirFlowRate': 'float',
        'NightCycleControlType': 'str | float | int | bool',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilityManagers': 'IB_AvailabilityManager',
        'AvailabilitySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilityManagers',
    )
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'SizingSystem': 'IB_SizingSystem',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'SizingSystem': 'IB_SizingSystem',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_AirLoopHVAC'] = PydanticField(default='IB_AirLoopHVAC')
    SizingSystem: IB_SizingSystem | None = PydanticField(default=None)

__all__ = [
    'IB_AirLoopHVAC',
]
