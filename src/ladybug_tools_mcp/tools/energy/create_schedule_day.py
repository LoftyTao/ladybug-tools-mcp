"""Create ScheduleDay MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.schedules import create_schedule_day as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_schedule_day tool.'

    @mcp.tool(
        name='create_schedule_day',
        description='Create a Honeybee Energy ScheduleDay, the single-day profile used inside ScheduleRule or ScheduleRuleset objects. If times is omitted, values must contain exactly one all-day constant value. If times is provided, values and times must have the same length and each time is the Ladybug value-begins-at time, not the EnergyPlus time-until convention. Returns object_dict plus summary_view only; this lightweight day schedule is not saved to Garden and has no target.',
        tags={
            "energy",
            "schedule",
            "schedule-day",
            "author",
        },
        timeout=20,
    )
    def create_schedule_day(
        identifier: Annotated[str, Field(description="ScheduleDay identifier.")],
        values: Annotated[
            list[float],
            Field(
                description="Numeric values for one day. Use one value when times is omitted; otherwise provide exactly one value for each value-begins-at time."
            ),
        ],
        times: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ladybug Time dictionaries or strings for value start times such as '09:00'. These are value-begins-at times, not EnergyPlus Schedule:Day time-until values."
            ),
        ] = None,
        interpolate: Annotated[
            bool,
            Field(
                description="Whether to linearly interpolate between schedule values."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ScheduleDay."""
        return service(
            identifier=identifier, values=values, times=times, interpolate=interpolate
        )
