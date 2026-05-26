"""Create ElectricEquipment MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_electric_equipment as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_electric_equipment tool.'

    @mcp.tool(
        name='create_electric_equipment',
        description='Create a Honeybee Energy ElectricEquipment internal-gains load from equipment power density and an optional fractional schedule. The schedule accepts an object_dict, Garden schedule target, or standards identifier. Use garden_root to save a Garden Properties Library load target and pass target to energy_create_program_type.electric_equipment; set return_object_dict=false only when you want a low-token target/summary/receipt response. This is plug/process equipment energy, not a Radiance luminaire or electric load center.',
        tags={
            "author",
            "energy",
            "electric-equipment",
            "electric",
            "internal-gains",
            "program-type",
            "load",
        },
        timeout=20,
    )
    def create_electric_equipment(
        identifier: Annotated[
            str, Field(description="ElectricEquipment object identifier.")
        ],
        watts_per_area: Annotated[
            float, Field(description="Electric equipment power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional equipment schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 radiant fraction of equipment heat gain."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 latent fraction of equipment heat gain."),
        ] = None,
        lost_fraction: Annotated[
            float | None,
            Field(
                description="Optional 0-1 fraction of equipment load lost outside the zone and HVAC system, such as directly exhausted heat."
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
        """Create a Honeybee Energy ElectricEquipment object."""
        return service(
            identifier=identifier,
            watts_per_area=watts_per_area,
            schedule=schedule,
            radiant_fraction=radiant_fraction,
            latent_fraction=latent_fraction,
            lost_fraction=lost_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
