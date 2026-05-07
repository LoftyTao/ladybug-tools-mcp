"""Create ServiceHotWater MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_service_hot_water as service


def register(mcp: FastMCP) -> None:
    """Register the create_service_hot_water tool."""

    @mcp.tool(
        name="create_service_hot_water",
        description="Create a Honeybee Energy ServiceHotWater load object from flow_per_area and optional schedule/temperature/fraction fields. Use garden_root and return_object_dict=false to save the load and pass its target to create_program_type.",
        tags={
            "honeybee-energy",
            "energy",
            "program",
            "load",
            "service-hot-water",
            "create",
            "safe",
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
                description="Optional hot water schedule dict or schedule library identifier."
            ),
        ] = None,
        target_temperature: Annotated[
            float | None,
            Field(description="Optional target water temperature in Celsius."),
        ] = None,
        sensible_fraction: Annotated[
            float | None,
            Field(description="Optional sensible fraction of hot water load."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional latent fraction of hot water load."),
        ] = None,
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
