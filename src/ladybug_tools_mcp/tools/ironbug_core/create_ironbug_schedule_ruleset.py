'MCP tool for detailed_hvac_schedule_ruleset.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_schedule_ruleset tool.'

    @mcp.tool(
        name='schedule_ruleset',
        description=(
            'Create IB_ScheduleRuleset, the main OpenStudio ScheduleRuleset target for Ironbug DetailedHVAC controls, availability, setpoints, loads, and operating profiles. Use it with ScheduleRule children, ScheduleTypeLimits, design-day, holiday, and custom-day schedules; this is not Schedule:File, a Honeybee Energy schedule library object, or an Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'schedule', 'schedule-ruleset', 'ruleset', 'schedule-rule', 'schedule-type-limit', 'design-day', 'holiday', 'weekday', 'weekend', 'author'},
        timeout=20,
    )
    def create_ironbug_schedule_ruleset(
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
            Field(description="Stable identifier for the new IB_ScheduleRuleset object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio object name for this ScheduleRuleset; maps to Name."
            ),
        ] = None,
        rules_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_ScheduleRule targets or same-model identifiers for date/day rules; the last rule becomes the default/base schedule."
            ),
        ] = None,
        schedule_type_limits_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_ScheduleTypeLimits target or same-model identifier constraining this ScheduleRuleset's values."
            ),
        ] = None,
        summer_design_day_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the summer design-day schedule; maps to SummerDesignDaySchedule.'),
        ] = None,
        winter_design_day_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the winter design-day schedule; maps to WinterDesignDaySchedule.'),
        ] = None,
        holiday_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for holiday day types; maps to HolidaySchedule.'),
        ] = None,
        custom_day1_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for CustomDay1 day types; maps to CustomDay1Schedule.'),
        ] = None,
        custom_day2_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for CustomDay2 day types; maps to CustomDay2Schedule.'),
        ] = None,
        rules_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_ScheduleRule identifiers for IB_ScheduleRuleset.Rules.'),
        ] = None,
        rules_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field Name.'),
        ] = None,
        rules_apply_sunday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplySunday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplySunday.'),
        ] = None,
        rules_apply_sunday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplySundayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplySundayNoFail.'),
        ] = None,
        rules_apply_monday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyMonday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyMonday.'),
        ] = None,
        rules_apply_monday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyMondayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyMondayNoFail.'),
        ] = None,
        rules_apply_tuesday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyTuesday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyTuesday.'),
        ] = None,
        rules_apply_tuesday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyTuesdayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyTuesdayNoFail.'),
        ] = None,
        rules_apply_wednesday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyWednesday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyWednesday.'),
        ] = None,
        rules_apply_wednesday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyWednesdayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyWednesdayNoFail.'),
        ] = None,
        rules_apply_thursday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyThursday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyThursday.'),
        ] = None,
        rules_apply_thursday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyThursdayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyThursdayNoFail.'),
        ] = None,
        rules_apply_friday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyFriday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyFriday.'),
        ] = None,
        rules_apply_friday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyFridayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyFridayNoFail.'),
        ] = None,
        rules_apply_saturday_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplySaturday value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplySaturday.'),
        ] = None,
        rules_apply_saturday_no_fail_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplySaturdayNoFail value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplySaturdayNoFail.'),
        ] = None,
        rules_start_date_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline StartDate value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field StartDate.'),
        ] = None,
        rules_end_date_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EndDate value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field EndDate.'),
        ] = None,
        rules_apply_all_days_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyAllDays value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyAllDays.'),
        ] = None,
        rules_apply_weekdays_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyWeekdays value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyWeekdays.'),
        ] = None,
        rules_apply_weekends_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline ApplyWeekends value for IB_ScheduleRule; maps to Ironbug IB_ScheduleRuleset.Rules child field ApplyWeekends.'),
        ] = None,
        schedule_type_limits_identifier: Annotated[
            str | None,
            Field(description='Optional inline IB_ScheduleTypeLimits identifiers for IB_ScheduleRuleset.ScheduleTypeLimits.'),
        ] = None,
        schedule_type_limits_name: Annotated[
            str | None,
            Field(description='Optional inline Name value for IB_ScheduleTypeLimits; maps to Ironbug IB_ScheduleRuleset.ScheduleTypeLimits child field Name.'),
        ] = None,
        schedule_type_limits_lower_limit_value: Annotated[
            float | None,
            Field(description='Optional inline LowerLimitValue value for IB_ScheduleTypeLimits; maps to Ironbug IB_ScheduleRuleset.ScheduleTypeLimits child field LowerLimitValue.'),
        ] = None,
        schedule_type_limits_upper_limit_value: Annotated[
            float | None,
            Field(description='Optional inline UpperLimitValue value for IB_ScheduleTypeLimits; maps to Ironbug IB_ScheduleRuleset.ScheduleTypeLimits child field UpperLimitValue.'),
        ] = None,
        schedule_type_limits_numeric_type: Annotated[
            str | None,
            Field(description='Optional inline NumericType value for IB_ScheduleTypeLimits; maps to Ironbug IB_ScheduleRuleset.ScheduleTypeLimits child field NumericType.'),
        ] = None,
        schedule_type_limits_unit_type: Annotated[
            str | None,
            Field(description='Optional inline UnitType value for IB_ScheduleTypeLimits; maps to Ironbug IB_ScheduleRuleset.ScheduleTypeLimits child field UnitType.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug ScheduleRuleset target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if summer_design_day_schedule_target is not None:
            source_field_targets['SummerDesignDaySchedule'] = summer_design_day_schedule_target
        if winter_design_day_schedule_target is not None:
            source_field_targets['WinterDesignDaySchedule'] = winter_design_day_schedule_target
        if holiday_schedule_target is not None:
            source_field_targets['HolidaySchedule'] = holiday_schedule_target
        if custom_day1_schedule_target is not None:
            source_field_targets['CustomDay1Schedule'] = custom_day1_schedule_target
        if custom_day2_schedule_target is not None:
            source_field_targets['CustomDay2Schedule'] = custom_day2_schedule_target
        if rules_targets is not None:
            source_property_targets['Rules'] = rules_targets
        if schedule_type_limits_target is not None:
            source_property_targets['ScheduleTypeLimits'] = schedule_type_limits_target
        inline_rules_fields: dict[str, Any] = {}
        inline_rules_field_targets: dict[str, Any] = {}
        if rules_name_values is not None:
            inline_rules_fields['Name'] = rules_name_values
        if rules_apply_sunday_values is not None:
            inline_rules_fields['ApplySunday'] = rules_apply_sunday_values
        if rules_apply_sunday_no_fail_values is not None:
            inline_rules_fields['ApplySundayNoFail'] = rules_apply_sunday_no_fail_values
        if rules_apply_monday_values is not None:
            inline_rules_fields['ApplyMonday'] = rules_apply_monday_values
        if rules_apply_monday_no_fail_values is not None:
            inline_rules_fields['ApplyMondayNoFail'] = rules_apply_monday_no_fail_values
        if rules_apply_tuesday_values is not None:
            inline_rules_fields['ApplyTuesday'] = rules_apply_tuesday_values
        if rules_apply_tuesday_no_fail_values is not None:
            inline_rules_fields['ApplyTuesdayNoFail'] = rules_apply_tuesday_no_fail_values
        if rules_apply_wednesday_values is not None:
            inline_rules_fields['ApplyWednesday'] = rules_apply_wednesday_values
        if rules_apply_wednesday_no_fail_values is not None:
            inline_rules_fields['ApplyWednesdayNoFail'] = rules_apply_wednesday_no_fail_values
        if rules_apply_thursday_values is not None:
            inline_rules_fields['ApplyThursday'] = rules_apply_thursday_values
        if rules_apply_thursday_no_fail_values is not None:
            inline_rules_fields['ApplyThursdayNoFail'] = rules_apply_thursday_no_fail_values
        if rules_apply_friday_values is not None:
            inline_rules_fields['ApplyFriday'] = rules_apply_friday_values
        if rules_apply_friday_no_fail_values is not None:
            inline_rules_fields['ApplyFridayNoFail'] = rules_apply_friday_no_fail_values
        if rules_apply_saturday_values is not None:
            inline_rules_fields['ApplySaturday'] = rules_apply_saturday_values
        if rules_apply_saturday_no_fail_values is not None:
            inline_rules_fields['ApplySaturdayNoFail'] = rules_apply_saturday_no_fail_values
        if rules_start_date_values is not None:
            inline_rules_fields['StartDate'] = rules_start_date_values
        if rules_end_date_values is not None:
            inline_rules_fields['EndDate'] = rules_end_date_values
        if rules_apply_all_days_values is not None:
            inline_rules_fields['ApplyAllDays'] = rules_apply_all_days_values
        if rules_apply_weekdays_values is not None:
            inline_rules_fields['ApplyWeekdays'] = rules_apply_weekdays_values
        if rules_apply_weekends_values is not None:
            inline_rules_fields['ApplyWeekends'] = rules_apply_weekends_values
        if rules_identifiers is not None or inline_rules_fields or inline_rules_field_targets:
            if rules_targets is not None:
                raise ValueError("Provide either rules_targets or inline rules_* parameters, not both.")
            inline_source_property_children['Rules'] = {
                'source_class': 'IB_ScheduleRule',
                'is_list': True,
                'identifiers': rules_identifiers,
                'source_fields': inline_rules_fields,
                'source_field_targets': inline_rules_field_targets,
            }
        inline_schedule_type_limits_fields: dict[str, Any] = {}
        inline_schedule_type_limits_field_targets: dict[str, Any] = {}
        if schedule_type_limits_name is not None:
            inline_schedule_type_limits_fields['Name'] = schedule_type_limits_name
        if schedule_type_limits_lower_limit_value is not None:
            inline_schedule_type_limits_fields['LowerLimitValue'] = schedule_type_limits_lower_limit_value
        if schedule_type_limits_upper_limit_value is not None:
            inline_schedule_type_limits_fields['UpperLimitValue'] = schedule_type_limits_upper_limit_value
        if schedule_type_limits_numeric_type is not None:
            inline_schedule_type_limits_fields['NumericType'] = schedule_type_limits_numeric_type
        if schedule_type_limits_unit_type is not None:
            inline_schedule_type_limits_fields['UnitType'] = schedule_type_limits_unit_type
        if schedule_type_limits_identifier is not None or inline_schedule_type_limits_fields or inline_schedule_type_limits_field_targets:
            if schedule_type_limits_target is not None:
                raise ValueError("Provide either schedule_type_limits_target or inline schedule_type_limits_* parameters, not both.")
            inline_source_property_children['ScheduleTypeLimits'] = {
                'source_class': 'IB_ScheduleTypeLimits',
                'is_list': False,
                'identifiers': schedule_type_limits_identifier,
                'source_fields': inline_schedule_type_limits_fields,
                'source_field_targets': inline_schedule_type_limits_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ScheduleRuleset',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
