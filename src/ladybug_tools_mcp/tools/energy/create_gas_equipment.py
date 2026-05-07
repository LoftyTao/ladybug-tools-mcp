"""Create GasEquipment MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_gas_equipment as service


def register(mcp: FastMCP) -> None:
    """Register the create_gas_equipment tool."""

    @mcp.tool(
        name="create_gas_equipment",
        description="Create a Honeybee Energy GasEquipment load object from watts_per_area and an optional schedule. Use garden_root and return_object_dict=false to save the load and pass its target to create_program_type.",
        tags={
            "honeybee-energy",
            "energy",
            "program",
            "load",
            "gas-equipment",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_gas_equipment(
        identifier: Annotated[
            str, Field(description="GasEquipment object identifier.")
        ],
        watts_per_area: Annotated[
            float, Field(description="Gas equipment power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional equipment schedule dict or schedule library identifier."
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional radiant fraction of equipment load."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional latent fraction of equipment load."),
        ] = None,
        lost_fraction: Annotated[
            float | None,
            Field(
                description="Optional fraction of equipment load lost outside the zone/HVAC system."
            ),
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
        """Create a Honeybee Energy GasEquipment object."""
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
