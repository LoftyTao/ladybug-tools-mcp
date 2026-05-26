"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ScheduleRule(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ScheduleRule'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/Schedules/IB_ScheduleRule.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.Schedules'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Schedule',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ScheduleRule_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ApplySunday',
        'ApplySundayNoFail',
        'ApplyMonday',
        'ApplyMondayNoFail',
        'ApplyTuesday',
        'ApplyTuesdayNoFail',
        'ApplyWednesday',
        'ApplyWednesdayNoFail',
        'ApplyThursday',
        'ApplyThursdayNoFail',
        'ApplyFriday',
        'ApplyFridayNoFail',
        'ApplySaturday',
        'ApplySaturdayNoFail',
        'StartDate',
        'EndDate',
        'ApplyAllDays',
        'ApplyWeekdays',
        'ApplyWeekends',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ApplyAllDays': 'bool | str',
        'ApplyFriday': 'bool | str',
        'ApplyFridayNoFail': 'bool | str',
        'ApplyMonday': 'bool | str',
        'ApplyMondayNoFail': 'bool | str',
        'ApplySaturday': 'bool | str',
        'ApplySaturdayNoFail': 'bool | str',
        'ApplySunday': 'bool | str',
        'ApplySundayNoFail': 'bool | str',
        'ApplyThursday': 'bool | str',
        'ApplyThursdayNoFail': 'bool | str',
        'ApplyTuesday': 'bool | str',
        'ApplyTuesdayNoFail': 'bool | str',
        'ApplyWednesday': 'bool | str',
        'ApplyWednesdayNoFail': 'bool | str',
        'ApplyWeekdays': 'bool | str',
        'ApplyWeekends': 'bool | str',
        'EndDate': 'str | float | int | bool',
        'StartDate': 'str | float | int | bool',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ScheduleRule'] = PydanticField(default='IB_ScheduleRule')

__all__ = [
    'IB_ScheduleRule',
]
