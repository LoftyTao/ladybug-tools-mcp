"""Create Infiltration MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_infiltration as service


def register(mcp: FastMCP) -> None:
    """Register the create_infiltration tool."""

    @mcp.tool(
        name="create_infiltration",
        description="Create a Honeybee Energy Infiltration load object from flow_per_exterior_area and optional schedule/coefficients. Use garden_root and return_object_dict=false to save the load and pass its target to create_program_type.",
        tags={
            "honeybee-energy",
            "energy",
            "program",
            "load",
            "infiltration",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_infiltration(
        identifier: Annotated[
            str, Field(description="Infiltration object identifier.")
        ],
        flow_per_exterior_area: Annotated[
            float,
            Field(
                description="Infiltration intensity in m3/s per exterior surface area."
            ),
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional infiltration schedule dict or schedule library identifier."
            ),
        ] = None,
        constant_coefficient: Annotated[
            float | None,
            Field(description="Optional infiltration constant coefficient."),
        ] = None,
        temperature_coefficient: Annotated[
            float | None,
            Field(description="Optional infiltration temperature coefficient."),
        ] = None,
        velocity_coefficient: Annotated[
            float | None,
            Field(description="Optional infiltration wind velocity coefficient."),
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
        """Create a Honeybee Energy Infiltration object."""
        return service(
            identifier=identifier,
            flow_per_exterior_area=flow_per_exterior_area,
            schedule=schedule,
            constant_coefficient=constant_coefficient,
            temperature_coefficient=temperature_coefficient,
            velocity_coefficient=velocity_coefficient,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
