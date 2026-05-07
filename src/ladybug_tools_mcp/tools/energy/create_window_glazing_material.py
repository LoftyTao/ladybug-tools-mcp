"""Create detailed window glazing material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_glazing_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_window_glazing_material tool."""

    @mcp.tool(
        name="create_window_glazing_material",
        description="Create a Honeybee Energy EnergyWindowMaterialGlazing layer for detailed WindowConstruction assemblies. Returns object_dict plus summary_view. Use return_detail='summary' for key optical and thermal values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "window",
            "glazing",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_window_glazing_material(
        identifier: Annotated[str, Field(description="Glazing material identifier.")],
        thickness: Annotated[
            float, Field(description="Glass thickness in meters.")
        ] = 0.003,
        solar_transmittance: Annotated[
            float, Field(description="Solar transmittance.")
        ] = 0.85,
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.075,
        visible_transmittance: Annotated[
            float, Field(description="Visible transmittance.")
        ] = 0.9,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.075,
        infrared_transmittance: Annotated[
            float, Field(description="Infrared transmittance.")
        ] = 0,
        emissivity: Annotated[
            float, Field(description="Front-side emissivity.")
        ] = 0.84,
        emissivity_back: Annotated[
            float, Field(description="Back-side emissivity.")
        ] = 0.84,
        conductivity: Annotated[
            float, Field(description="Glass conductivity in W/m-K.")
        ] = 0.9,
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
        """Create a Honeybee Energy EnergyWindowMaterialGlazing object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            solar_transmittance=solar_transmittance,
            solar_reflectance=solar_reflectance,
            visible_transmittance=visible_transmittance,
            visible_reflectance=visible_reflectance,
            infrared_transmittance=infrared_transmittance,
            emissivity=emissivity,
            emissivity_back=emissivity_back,
            conductivity=conductivity,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
