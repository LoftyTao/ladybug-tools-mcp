"""Create Ventilation MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_ventilation as service


def register(mcp: FastMCP) -> None:
    """Register the create_ventilation tool."""

    @mcp.tool(
        name="create_ventilation",
        description="Create a Honeybee Energy Ventilation load object using SDK-native flow_per_person, flow_per_area, flow_per_zone, ACH, schedule, and Sum/Max method fields. Use garden_root and return_object_dict=false to save the load and pass its target to create_program_type.",
        tags={
            "honeybee-energy",
            "energy",
            "program",
            "load",
            "ventilation",
            "create",
            "safe",
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
                description="Optional ventilation schedule dict or schedule library identifier."
            ),
        ] = None,
        method: Annotated[
            str, Field(description="Ventilation reconciliation method: Sum or Max.")
        ] = "Sum",
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for saving this load to the Garden Properties Library."
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
