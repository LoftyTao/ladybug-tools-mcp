"""Create Lighting MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_lighting as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_lighting tool.'

    @mcp.tool(
        name='create_lighting',
        description='Create a Honeybee Energy Lighting load object from lighting power density in watts_per_area and an optional schedule. This is an internal gains load for a ProgramType, not a Radiance luminaire or daylight electric-lighting control. Use garden_root and return_object_dict=false to save a load target for energy_create_program_type.',
        tags={
            "energy",
            "program-type",
            "load",
            "lighting",
            "author",
        },
        timeout=20,
    )
    def create_lighting(
        identifier: Annotated[str, Field(description="Lighting object identifier.")],
        watts_per_area: Annotated[
            float, Field(description="Lighting power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional lighting schedule dict or schedule library identifier."
            ),
        ] = None,
        return_air_fraction: Annotated[
            float | None,
            Field(description="Optional fraction of lighting load to zone return air."),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional radiant fraction of lighting load."),
        ] = None,
        visible_fraction: Annotated[
            float | None,
            Field(description="Optional visible fraction of lighting load."),
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
        """Create a Honeybee Energy Lighting object."""
        return service(
            identifier=identifier,
            watts_per_area=watts_per_area,
            schedule=schedule,
            return_air_fraction=return_air_fraction,
            radiant_fraction=radiant_fraction,
            visible_fraction=visible_fraction,
            garden_root=garden_root if garden_root is not None else garden_root,
            return_object_dict=return_object_dict,
        )
