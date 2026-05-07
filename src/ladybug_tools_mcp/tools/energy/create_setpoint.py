"""Create Setpoint MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_setpoint as service


def register(mcp: FastMCP) -> None:
    """Register the create_setpoint tool."""

    @mcp.tool(
        name="create_setpoint",
        description="Create a Honeybee Energy Setpoint load object from heating and cooling schedules, or from simple numeric heating_setpoint and cooling_setpoint values that create constant schedules. Returns the full SDK Setpoint object_dict using Setpoint.to_dict(abridged=False). For Agent handoff into edit_honeybee_room setpoint, pass garden_root and return_object_dict=false to save the Setpoint into the Garden Properties Library and reuse the returned target instead of copying expanded schedule JSON.",
        tags={
            "honeybee-energy",
            "energy",
            "program",
            "load",
            "setpoint",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_setpoint(
        identifier: Annotated[
            str,
            Field(
                description="Setpoint object identifier. Defaults to agent_setpoint when omitted by Code Mode Agents."
            ),
        ] = "agent_setpoint",
        heating_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Heating setpoint schedule dict, Garden schedule target, or exact schedule library identifier. Optional when heating_setpoint is provided."
            ),
        ] = None,
        cooling_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Cooling setpoint schedule dict, Garden schedule target, or exact schedule library identifier. Optional when cooling_setpoint is provided."
            ),
        ] = None,
        humidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional humidifying schedule dict or schedule library identifier."
            ),
        ] = None,
        dehumidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional dehumidifying schedule dict or schedule library identifier."
            ),
        ] = None,
        heating_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant heating setpoint temperature. When provided without heating_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        cooling_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant cooling setpoint temperature. When provided without cooling_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        setpoint_cutout_difference: Annotated[
            float,
            Field(
                description="Optional temperature difference between setpoint and cutout."
            ),
        ] = 0,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root. When provided, save the Setpoint as a reusable Garden Properties Library load."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Whether to include the full SDK object_dict in the response. Use false for low-token Agent Garden workflows."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Setpoint object."""
        return service(
            identifier=identifier,
            heating_schedule=heating_schedule,
            cooling_schedule=cooling_schedule,
            humidifying_schedule=humidifying_schedule,
            dehumidifying_schedule=dehumidifying_schedule,
            heating_setpoint=heating_setpoint,
            cooling_setpoint=cooling_setpoint,
            setpoint_cutout_difference=setpoint_cutout_difference,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
