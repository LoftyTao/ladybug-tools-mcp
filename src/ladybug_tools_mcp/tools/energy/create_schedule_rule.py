"""Create ScheduleRule MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.schedules import create_schedule_rule as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_schedule_rule tool.'

    @mcp.tool(
        name='create_schedule_rule',
        description='Create a Honeybee Energy ScheduleRule that applies one ScheduleDay to selected weekdays and optional Ladybug Date bounds. Use this for weekday/weekend, seasonal, or exception rules before assembling a ScheduleRuleset. Returns object_dict and summary_view for energy_create_schedule_ruleset.schedule_rules; this rule is not saved as its own Garden target.',
        tags={
            "energy",
            "schedule",
            "schedule-rule",
            "weekday",
            "weekend",
            "author",
        },
        timeout=20,
    )
    def create_schedule_rule(
        schedule_day: Annotated[
            dict[str, Any],
            Field(
                description='ScheduleDay object_dict, usually returned by energy_create_schedule_day; ScheduleRule cannot consume a saved target because ScheduleDay is not persisted separately.'
            ),
        ],
        apply_sunday: Annotated[
            bool, Field(description="Apply rule on Sunday.")
        ] = False,
        apply_monday: Annotated[
            bool, Field(description="Apply rule on Monday.")
        ] = False,
        apply_tuesday: Annotated[
            bool, Field(description="Apply rule on Tuesday.")
        ] = False,
        apply_wednesday: Annotated[
            bool, Field(description="Apply rule on Wednesday.")
        ] = False,
        apply_thursday: Annotated[
            bool, Field(description="Apply rule on Thursday.")
        ] = False,
        apply_friday: Annotated[
            bool, Field(description="Apply rule on Friday.")
        ] = False,
        apply_saturday: Annotated[
            bool, Field(description="Apply rule on Saturday.")
        ] = False,
        start_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug Date dict or string for the first date when this rule can apply."
            ),
        ] = None,
        end_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug Date dict or string for the last date when this rule can apply."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ScheduleRule."""
        return service(
            schedule_day=schedule_day,
            apply_sunday=apply_sunday,
            apply_monday=apply_monday,
            apply_tuesday=apply_tuesday,
            apply_wednesday=apply_wednesday,
            apply_thursday=apply_thursday,
            apply_friday=apply_friday,
            apply_saturday=apply_saturday,
            start_date=start_date,
            end_date=end_date,
        )
