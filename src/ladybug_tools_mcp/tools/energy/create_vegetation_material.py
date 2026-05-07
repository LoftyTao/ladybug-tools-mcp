"""Create vegetation roof material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_vegetation_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_vegetation_material tool."""

    @mcp.tool(
        name="create_vegetation_material",
        description="Create a Honeybee Energy EnergyMaterialVegetation green-roof material. Returns object_dict plus summary_view. Use return_detail='summary' for key thermal/plant values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "vegetation",
            "green-roof",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_vegetation_material(
        identifier: Annotated[
            str, Field(description="Vegetation material identifier.")
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
                description="Optional Garden root for saving this material to the Garden Properties Library."
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
