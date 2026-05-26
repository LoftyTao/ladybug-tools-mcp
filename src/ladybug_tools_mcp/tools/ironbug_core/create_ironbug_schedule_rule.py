'MCP tool for detailed_hvac_schedule_rule.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_schedule_rule tool.'

    @mcp.tool(
        name='schedule_rule',
        description=(
            'Create IB_ScheduleRule, a rule child for IB_ScheduleRuleset with one constant value or 24 hourly values, weekday/weekend/day flags, and an optional start/end date range. Use it inside detailed_hvac_schedule_ruleset; it is not a standalone annual schedule, Schedule:File, ScheduleTypeLimits object, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'schedule', 'schedule-rule', 'schedule-day', 'weekday', 'weekend', 'date-range', 'author'},
        timeout=20,
    )
    def create_ironbug_schedule_rule(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_ScheduleRule object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        apply_monday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplyMonday for IB_ScheduleRule."
            ),
        ] = None,
        apply_tuesday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplyTuesday for IB_ScheduleRule."
            ),
        ] = None,
        apply_wednesday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplyWednesday for IB_ScheduleRule."
            ),
        ] = None,
        apply_thursday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplyThursday for IB_ScheduleRule."
            ),
        ] = None,
        apply_friday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplyFriday for IB_ScheduleRule."
            ),
        ] = None,
        apply_saturday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplySaturday for IB_ScheduleRule."
            ),
        ] = None,
        apply_sunday: Annotated[
            bool | str | None,
            Field(
                description="Sets Ironbug field ApplySunday for IB_ScheduleRule."
            ),
        ] = None,
        values: Annotated[
            list[float] | None,
            Field(description='Optional schedule-day values: pass one constant value or exactly 24 hourly values for the rule day profile.'),
        ] = None,
        date_range: Annotated[
            list[int] | None,
            Field(description='Optional [start_month, start_day, end_month, end_day] date range for this ScheduleRule.'),
        ] = None,
        apply_sunday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplySundayNoFail value; maps to Ironbug IB_ScheduleRule field ApplySundayNoFail.'),
        ] = None,
        apply_monday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplyMondayNoFail value; maps to Ironbug IB_ScheduleRule field ApplyMondayNoFail.'),
        ] = None,
        apply_tuesday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplyTuesdayNoFail value; maps to Ironbug IB_ScheduleRule field ApplyTuesdayNoFail.'),
        ] = None,
        apply_wednesday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplyWednesdayNoFail value; maps to Ironbug IB_ScheduleRule field ApplyWednesdayNoFail.'),
        ] = None,
        apply_thursday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplyThursdayNoFail value; maps to Ironbug IB_ScheduleRule field ApplyThursdayNoFail.'),
        ] = None,
        apply_friday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplyFridayNoFail value; maps to Ironbug IB_ScheduleRule field ApplyFridayNoFail.'),
        ] = None,
        apply_saturday_no_fail: Annotated[
            bool | str | None,
            Field(description='Optional ApplySaturdayNoFail value; maps to Ironbug IB_ScheduleRule field ApplySaturdayNoFail.'),
        ] = None,
        start_date: Annotated[
            str | float | int | bool | None,
            Field(description='Optional EnergyPlus/OpenStudio rule start date value; prefer date_range for month/day tuples when possible.'),
        ] = None,
        end_date: Annotated[
            str | float | int | bool | None,
            Field(description='Optional EnergyPlus/OpenStudio rule end date value; prefer date_range for month/day tuples when possible.'),
        ] = None,
        apply_all_days: Annotated[
            bool | str | None,
            Field(description='Optional ApplyAllDays value; maps to Ironbug IB_ScheduleRule field ApplyAllDays.'),
        ] = None,
        apply_weekdays: Annotated[
            bool | str | None,
            Field(description='Optional ApplyWeekdays value; maps to Ironbug IB_ScheduleRule field ApplyWeekdays.'),
        ] = None,
        apply_weekends: Annotated[
            bool | str | None,
            Field(description='Optional ApplyWeekends value; maps to Ironbug IB_ScheduleRule field ApplyWeekends.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name for this ScheduleRule child; maps to Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug ScheduleRule child."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if apply_monday is not None:
            source_fields['ApplyMonday'] = apply_monday
        if apply_tuesday is not None:
            source_fields['ApplyTuesday'] = apply_tuesday
        if apply_wednesday is not None:
            source_fields['ApplyWednesday'] = apply_wednesday
        if apply_thursday is not None:
            source_fields['ApplyThursday'] = apply_thursday
        if apply_friday is not None:
            source_fields['ApplyFriday'] = apply_friday
        if apply_saturday is not None:
            source_fields['ApplySaturday'] = apply_saturday
        if apply_sunday is not None:
            source_fields['ApplySunday'] = apply_sunday
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if apply_sunday_no_fail is not None:
            source_fields['ApplySundayNoFail'] = apply_sunday_no_fail
        if apply_monday_no_fail is not None:
            source_fields['ApplyMondayNoFail'] = apply_monday_no_fail
        if apply_tuesday_no_fail is not None:
            source_fields['ApplyTuesdayNoFail'] = apply_tuesday_no_fail
        if apply_wednesday_no_fail is not None:
            source_fields['ApplyWednesdayNoFail'] = apply_wednesday_no_fail
        if apply_thursday_no_fail is not None:
            source_fields['ApplyThursdayNoFail'] = apply_thursday_no_fail
        if apply_friday_no_fail is not None:
            source_fields['ApplyFridayNoFail'] = apply_friday_no_fail
        if apply_saturday_no_fail is not None:
            source_fields['ApplySaturdayNoFail'] = apply_saturday_no_fail
        if start_date is not None:
            source_fields['StartDate'] = start_date
        if end_date is not None:
            source_fields['EndDate'] = end_date
        if apply_all_days is not None:
            source_fields['ApplyAllDays'] = apply_all_days
        if apply_weekdays is not None:
            source_fields['ApplyWeekdays'] = apply_weekdays
        if apply_weekends is not None:
            source_fields['ApplyWeekends'] = apply_weekends
        custom_attributes: dict[str, Any] = {'Comment': identifier}
        children: list[dict[str, Any]] = []
        ib_properties: dict[str, Any] = {}
        if values is not None:
            if len(values) not in {1, 24}:
                raise ValueError('IB_ScheduleRule values expects either 1 or 24 values.')
            day_properties = {'constantNumber': values[0]} if len(values) == 1 else {'values': values}
            children.append({
                'type': 'IB_ScheduleDay',
                'identifier': f'{identifier}_day',
                'CustomAttributes': {'Comment': f'{identifier}_day'},
                'IBProperties': day_properties,
            })
        if date_range is not None:
            if len(date_range) != 4:
                raise ValueError('IB_ScheduleRule date_range expects four integers: start month/day and end month/day.')
            ib_properties['_dateRange'] = date_range
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ScheduleRule',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            custom_attributes=custom_attributes or None,
            ib_properties=ib_properties or None,
            children=children or None,
            overwrite=overwrite,
        )
