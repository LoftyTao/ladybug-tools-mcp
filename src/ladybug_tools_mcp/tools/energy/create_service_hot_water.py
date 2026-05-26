"""Create ServiceHotWater MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_service_hot_water as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_service_hot_water tool.'

    @mcp.tool(
        name='create_service_hot_water',
        description='Create a Honeybee Energy ServiceHotWater demand load from floor-area hot water use, optional fractional schedule, tap target temperature, and sensible/latent fractions. Use it as the program-type domestic hot water demand companion to ventilation, infiltration, thermostat, and humidistat loads; it does not size outdoor air or ACH. The schedule accepts an object_dict, Garden schedule target, or standards identifier. Use garden_root to save a Garden Properties Library load target and pass target to energy_create_program_type.service_hot_water; set return_object_dict=false only when you want a low-token target/summary/receipt response. This describes hot-water use demand and zone gains, not a service hot-water plant, water heater, or loop component.',
        tags={
            "author",
            "energy",
            "hot-water",
            "program-type",
            "load",
            "service-hot-water",
        },
        timeout=20,
    )
    def create_service_hot_water(
        identifier: Annotated[
            str, Field(description="ServiceHotWater object identifier.")
        ],
        flow_per_area: Annotated[
            float, Field(description="Hot water flow per floor area in L/h-m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional hot water use schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        target_temperature: Annotated[
            float | None,
            Field(description="Optional target tap water temperature in Celsius after mixing with mains water."),
        ] = None,
        sensible_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 fraction of hot water load released as sensible heat in the zone."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 fraction of hot water load released as latent heat in the zone."),
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
        """Create a Honeybee Energy ServiceHotWater object."""
        return service(
            identifier=identifier,
            flow_per_area=flow_per_area,
            schedule=schedule,
            target_temperature=target_temperature,
            sensible_fraction=sensible_fraction,
            latent_fraction=latent_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
