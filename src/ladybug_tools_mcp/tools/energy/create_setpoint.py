"""Create Setpoint MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_setpoint as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_setpoint tool.'

    @mcp.tool(
        name='create_setpoint',
        description='Create a Honeybee Energy Setpoint thermostat/humidistat resource from heating and cooling schedules, or from numeric Celsius heating_setpoint and cooling_setpoint values that become constant schedules. Use it as the program-type thermostat companion to ventilation, infiltration, and service hot water demand loads; it does not size outdoor air or ACH. Schedules accept object_dicts, Garden schedule targets, or standards identifiers. Use garden_root to save a Garden Properties Library load target and pass target to energy_create_program_type.setpoint or honeybee_edit_room.setpoint; set return_object_dict=false only when you want a low-token target/summary/receipt response. This is zone thermostat/humidistat control data, not HVAC supply-air temperature or a DetailedHVAC setpoint manager.',
        tags={
            "author",
            "energy",
            "humidistat",
            "program-type",
            "setpoint",
            "thermostat",
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
                description="Heating setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier. Optional when heating_setpoint is provided."
            ),
        ] = None,
        cooling_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Cooling setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier. Optional when cooling_setpoint is provided."
            ),
        ] = None,
        humidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional humidifying setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        dehumidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional dehumidifying setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        heating_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant heating thermostat setpoint in Celsius. When provided without heating_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        cooling_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant cooling thermostat setpoint in Celsius. When provided without cooling_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        setpoint_cutout_difference: Annotated[
            float,
            Field(
                description="Optional positive Celsius temperature difference between thermostat setpoint and cutout for throttling range control."
            ),
        ] = 0,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
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
