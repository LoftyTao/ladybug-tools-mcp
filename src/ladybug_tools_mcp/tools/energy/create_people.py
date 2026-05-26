"""Create People MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_people as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_people tool.'

    @mcp.tool(
        name='create_people',
        description='Create a Honeybee Energy People occupancy load object from people_per_area and optional occupancy/activity schedules. Occupancy schedules should be Fractional. Only pass activity_schedule when it is an Activity Level schedule in W/person; omit activity_schedule to use the SDK default seated-activity schedule. Do not reuse a Fractional occupancy schedule as activity_schedule. Use garden_root and return_object_dict=false to save a load target for energy_create_program_type.',
        tags={
            "energy",
            "program-type",
            "load",
            "occupancy",
            "author",
        },
        timeout=20,
    )
    def create_people(
        identifier: Annotated[str, Field(description="People object identifier.")],
        people_per_area: Annotated[
            float, Field(description="People density in people per square meter.")
        ],
        occupancy_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional occupancy schedule dict or schedule library identifier."
            ),
        ] = None,
        activity_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Activity Level schedule dict or library identifier in W/person. Do not pass a Fractional occupancy schedule here; omit for default seated activity."
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional radiant fraction of sensible heat."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(
                description="Optional latent heat fraction. Omit to use SDK autocalculate."
            ),
        ] = None,
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
        """Create a Honeybee Energy People object."""
        return service(
            identifier=identifier,
            people_per_area=people_per_area,
            occupancy_schedule=occupancy_schedule,
            activity_schedule=activity_schedule,
            radiant_fraction=radiant_fraction,
            latent_fraction=latent_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
