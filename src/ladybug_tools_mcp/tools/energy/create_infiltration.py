"""Create Infiltration MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.programtypes import create_infiltration as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_infiltration tool.'

    @mcp.tool(
        name='create_infiltration',
        description='Create a Honeybee Energy Infiltration load for uncontrolled outdoor air leakage through the envelope, using flow_per_exterior_area plus optional fractional schedule and EnergyPlus/BLAST/DOE2-style coefficients. The schedule accepts an object_dict, Garden schedule target, or standards identifier. Use garden_root to save a Garden Properties Library load target and pass target to energy_create_program_type.infiltration; set return_object_dict=false only when you want a low-token target/summary/receipt response. This is not design ventilation, fan-assisted zone ventilation, operable-window natural ventilation, or AirflowNetwork authoring.',
        tags={
            "author",
            "energy",
            "envelope",
            "infiltration",
            "program-type",
            "load",
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
                description="Optional fractional infiltration schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        constant_coefficient: Annotated[
            float | None,
            Field(description="Optional constant leakage coefficient; EnergyPlus default is 1 while BLAST/DOE2 use different reference coefficients."),
        ] = None,
        temperature_coefficient: Annotated[
            float | None,
            Field(description="Optional temperature-difference coefficient multiplied by indoor-outdoor delta C."),
        ] = None,
        velocity_coefficient: Annotated[
            float | None,
            Field(description="Optional wind velocity coefficient multiplied by exterior wind speed in m/s."),
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
