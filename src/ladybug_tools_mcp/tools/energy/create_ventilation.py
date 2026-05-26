"""Create Ventilation MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_ventilation as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_ventilation tool.'

    @mcp.tool(
        name='create_ventilation',
        description='Create a Honeybee Energy Ventilation load for purposeful design outdoor air using flow_per_person, flow_per_area, flow_per_zone, ACH, fractional schedule, and Sum/Max reconciliation. The schedule accepts an object_dict, Garden schedule target, or standards identifier. Use garden_root to save a Garden Properties Library load target and pass target to energy_create_program_type.ventilation or honeybee_edit_room.ventilation; set return_object_dict=false only when you want a low-token target/summary/receipt response. This is not infiltration, a VentilationFan, operable-window natural ventilation, or AirflowNetwork setup.',
        tags={
            "author",
            "energy",
            "outdoor-air",
            "program-type",
            "load",
            "ventilation",
        },
        timeout=20,
    )
    def create_ventilation(
        identifier: Annotated[str, Field(description="Ventilation object identifier.")],
        flow_per_person: Annotated[
            float, Field(description="Ventilation rate in m3/s per person.")
        ] = 0,
        flow_per_area: Annotated[
            float, Field(description="Ventilation rate in m3/s per floor area.")
        ] = 0,
        flow_per_zone: Annotated[
            float, Field(description="Whole-zone ventilation rate in m3/s.")
        ] = 0,
        air_changes_per_hour: Annotated[
            float, Field(description="Whole-zone ventilation rate in ACH.")
        ] = 0,
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional ventilation schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier; use an occupancy schedule to mimic demand-controlled ventilation."
            ),
        ] = None,
        method: Annotated[
            str, Field(description="Ventilation reconciliation method for the four design criteria: Sum adds them; Max uses the largest.")
        ] = "Sum",
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Ventilation object."""
        return service(
            identifier=identifier,
            flow_per_person=flow_per_person,
            flow_per_area=flow_per_area,
            flow_per_zone=flow_per_zone,
            air_changes_per_hour=air_changes_per_hour,
            schedule=schedule,
            method=method,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
