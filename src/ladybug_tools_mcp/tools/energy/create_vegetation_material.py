"""Create vegetation roof material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_vegetation_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_vegetation_material tool.'

    @mcp.tool(
        name='create_vegetation_material',
        description=(
            "Create a Honeybee Energy EnergyMaterialVegetation green-roof "
            "material layer for roof constructions. This describes roof soil "
            "and plant thermal properties; it does not create landscape "
            "geometry, UWG vegetation, or a full roof construction. Returns "
            "object_dict plus summary_view; return_detail='full' also includes "
            "a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "vegetation",
        },
        timeout=20,
    )
    def create_vegetation_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyMaterialVegetation identifier for a vegetated roof layer.")
        ],
        thickness: Annotated[
            float,
            Field(
                ge=0.1,
                description=(
                    "Soil thickness in meters. OpenStudio RoofVegetation "
                    "requires at least 0.1 m."
                ),
            ),
        ] = 0.1,
        conductivity: Annotated[
            float, Field(description="Dry soil conductivity in W/m-K.")
        ] = 0.35,
        density: Annotated[
            float, Field(description="Dry soil density in kg/m3.")
        ] = 1100,
        specific_heat: Annotated[
            float, Field(description="Dry soil specific heat in J/kg-K.")
        ] = 1200,
        plant_height: Annotated[
            float, Field(description="Plant height in meters.")
        ] = 0.2,
        leaf_area_index: Annotated[float, Field(description="Leaf area index.")] = 1.0,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyMaterialVegetation object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity=conductivity,
            density=density,
            specific_heat=specific_heat,
            plant_height=plant_height,
            leaf_area_index=leaf_area_index,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
