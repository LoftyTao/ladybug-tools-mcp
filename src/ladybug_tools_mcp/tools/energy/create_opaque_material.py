"""Create opaque EnergyMaterial MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import create_opaque_material as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_opaque_material tool.'

    @mcp.tool(
        name='create_opaque_material',
        description="Create a Honeybee Energy EnergyMaterial opaque material layer with thermal mass for OpaqueConstruction assemblies. Returns object_dict plus summary_view. Use return_detail='summary' for key thickness, conductivity, density, heat capacity, R-value, and U-value fields or 'full' for a matrix of material property values. Use garden_root and return_object_dict=false to save the material target for construction tools.",
        tags={
            "energy",
            "construction",
            "material",
            "thermal-mass",
            "author",
        },
        timeout=20,
    )
    def create_opaque_material(
        identifier: Annotated[str, Field(description="EnergyMaterial identifier.")],
        thickness: Annotated[float, Field(description="Layer thickness in meters.")],
        conductivity: Annotated[
            float, Field(description="Thermal conductivity in W/m-K.")
        ],
        density: Annotated[float, Field(description="Density in kg/m3.")],
        specific_heat: Annotated[float, Field(description="Specific heat in J/kg-K.")],
        roughness: Annotated[
            str, Field(description="EnergyPlus roughness label.")
        ] = "MediumRough",
        thermal_absorptance: Annotated[
            float, Field(description="Long-wave absorptance.")
        ] = 0.9,
        solar_absorptance: Annotated[
            float, Field(description="Solar absorptance.")
        ] = 0.7,
        visible_absorptance: Annotated[
            float | None, Field(description="Visible absorptance.")
        ] = None,
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
        """Create a Honeybee Energy EnergyMaterial object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity=conductivity,
            density=density,
            specific_heat=specific_heat,
            roughness=roughness,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
