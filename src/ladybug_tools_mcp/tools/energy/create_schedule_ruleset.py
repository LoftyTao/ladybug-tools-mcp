"""Create ScheduleRuleset MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.schedules import create_schedule_ruleset as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_schedule_ruleset tool.'

    @mcp.tool(
        name='create_schedule_ruleset',
        description="Create a Honeybee Energy ScheduleRuleset, the saved annual schedule resource assembled from a default ScheduleDay plus optional ScheduleRules, holiday, and design-day schedules. Use this for occupancy, lighting, equipment, setpoint, transmittance, or other annual schedules before ProgramType/load/Room property assignment. Returns object_dict, summary_view, and optional data; with garden_root it also returns target, persistence_receipt, and when include_data=true a data_target plus data_persistence_receipt.",
        tags={
            "energy",
            "schedule",
            "ruleset",
            "schedule-type-limit",
            "holiday",
            "design-day",
            "author",
        },
        timeout=20,
    )
    def create_schedule_ruleset(
        identifier: Annotated[str, Field(description="ScheduleRuleset identifier.")],
        default_day_schedule: Annotated[
            dict[str, Any] | None,
            Field(
                description='Default ScheduleDay object_dict, usually returned by energy_create_schedule_day. If omitted, provide default_value for the Agent-friendly all-day shorthand.'
            ),
        ] = None,
        schedule_rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description='Optional ScheduleRule object_dict rows ordered from highest to lowest priority, usually returned by energy_create_schedule_rule. Do not pass interval rows here; use rules for shorthand rows.'
            ),
        ] = None,
        rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional Agent-friendly interval shorthand. Each row must include start_time, end_time, value, and a day filter such as days='weekdays', weekdays='weekday', or apply_days as seven booleans Sunday through Saturday. Converted into a real Honeybee ScheduleRule."
            ),
        ] = None,
        schedule_type_limit: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional ScheduleTypeLimit dict or standards-library identifier that constrains values and units."),
        ] = None,
        default_value: Annotated[
            float | None,
            Field(
                description="Agent-friendly all-day default value used when default_day_schedule is omitted, for example 0.0 for unoccupied hours."
            ),
        ] = None,
        summer_designday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional summer design-day ScheduleDay object_dict."),
        ] = None,
        winter_designday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional winter design-day ScheduleDay object_dict."),
        ] = None,
        holiday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional holiday ScheduleDay object_dict."),
        ] = None,
        include_data: Annotated[
            bool,
            Field(
                description="Whether to generate Ladybug DataCollection schedule data for summary, target persistence, or optional return as data."
            ),
        ] = True,
        return_data: Annotated[
            bool,
            Field(
                description="Return the full Ladybug DataCollection dict in data. Set false with garden_root to persist data_target/data_persistence_receipt instead of sending all schedule values through the Agent context."
            ),
        ] = True,
        data_analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dict or string for generated data. When provided, schedule data is generated at its timestep and filtered with Ladybug DataCollection.filter_by_analysis_period. It supplies timestep, date/time range, and leap-year settings."
            ),
        ] = None,
        data_timestep: Annotated[
            int,
            Field(
                description="DataCollection timestep, in steps per hour. Ignored when data_analysis_period is provided."
            ),
        ] = 1,
        data_start_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DataCollection start date as Ladybug Date dict or string."
            ),
        ] = None,
        data_end_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DataCollection end date as Ladybug Date dict or string."
            ),
        ] = None,
        data_start_dow: Annotated[
            str, Field(description="Day of week for the start date. Default: Sunday.")
        ] = "Sunday",
        data_holidays: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional holiday dates as Ladybug Date dicts or strings."
            ),
        ] = None,
        data_leap_year: Annotated[
            bool, Field(description="Whether generated data should use a leap year.")
        ] = False,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full ScheduleRuleset object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a complete Honeybee Energy ScheduleRuleset."""
        return service(
            identifier=identifier,
            default_day_schedule=default_day_schedule,
            schedule_rules=schedule_rules,
            rules=rules,
            schedule_type_limit=schedule_type_limit,
            default_value=default_value,
            summer_designday_schedule=summer_designday_schedule,
            winter_designday_schedule=winter_designday_schedule,
            holiday_schedule=holiday_schedule,
            include_data=include_data,
            data_analysis_period=data_analysis_period,
            data_timestep=data_timestep,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            data_start_dow=data_start_dow,
            data_holidays=data_holidays,
            data_leap_year=data_leap_year,
            garden_root=garden_root,
            return_data=return_data,
            return_object_dict=return_object_dict,
        )
