"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ScheduleRuleset(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ScheduleRuleset'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Schedules/IB_ScheduleRuleset.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Schedules'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Schedule',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ScheduleRuleset_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Rules',
        'ScheduleTypeLimits',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'SummerDesignDaySchedule',
        'WinterDesignDaySchedule',
        'HolidaySchedule',
        'CustomDay1Schedule',
        'CustomDay2Schedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CustomDay1Schedule': 'IB_Schedule',
        'CustomDay2Schedule': 'IB_Schedule',
        'HolidaySchedule': 'IB_Schedule',
        'SummerDesignDaySchedule': 'IB_Schedule',
        'WinterDesignDaySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Rules': 'List<IB_ScheduleRule>',
        'ScheduleTypeLimits': 'IB_ScheduleTypeLimits',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ScheduleRuleset'] = PydanticField(default='IB_ScheduleRuleset')
    Rules: list[IB_ScheduleRule] | None = PydanticField(default=None)
    ScheduleTypeLimits: IB_ScheduleTypeLimits | None = PydanticField(default=None)

__all__ = [
    'IB_ScheduleRuleset',
]
