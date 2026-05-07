"""Create ScheduleDay MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.schedules import create_schedule_day as service


def register(mcp: FastMCP) -> None:
    """Register the create_schedule_day tool."""

    @mcp.tool(
        name="create_schedule_day",
        description="Create a Honeybee Energy ScheduleDay from values and optional Ladybug Time dictionaries. If times is omitted, values must contain exactly one all-day constant value. If times is provided, values and times must have the same length and each time is the start time at which the matching value begins. This lightweight object is not saved to Garden and has no target; pass its returned object_dict as create_schedule_ruleset.default_day_schedule.",
        tags={
            "honeybee-energy",
            "energy",
            "schedule",
            "schedule-day",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_schedule_day(
        identifier: Annotated[str, Field(description="ScheduleDay identifier.")],
        values: Annotated[
            list[float],
            Field(
                description="Schedule values for one day. Use one value when times is omitted; otherwise provide exactly one value for each time in times."
            ),
        ],
        times: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ladybug Time dictionaries or strings for value start times. These are value-begins-at times, not EnergyPlus time-until values."
            ),
        ] = None,
        interpolate: Annotated[
            bool,
            Field(
                description="Whether to linearly interpolate between schedule values."
            ),
        ] = False,
        garden_root: Annotated[
            str | None,
            Field(
                description="Ignored Agent compatibility hint. ScheduleDay is an intermediate object and is not saved directly to Garden."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ScheduleDay."""
        return service(
            identifier=identifier, values=values, times=times, interpolate=interpolate
        )
