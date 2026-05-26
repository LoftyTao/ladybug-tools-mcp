"""Create opaque no-mass EnergyMaterialNoMass MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_opaque_no_mass_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_opaque_no_mass_material tool.'

    @mcp.tool(
        name='create_opaque_no_mass_material',
        description=(
            "Create a Honeybee Energy EnergyMaterialNoMass opaque material "
            "from an R-value for walls, roofs, floors, or other opaque "
            "construction layers. This returns a material layer for later use "
            "in an opaque construction; it does not assign the layer to model "
            "geometry. Returns object_dict plus summary_view; "
            "return_detail='full' also includes a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "opaque",
        },
        timeout=20,
    )
    def create_opaque_no_mass_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyMaterialNoMass identifier for an opaque no-mass layer.")
        ],
        r_value: Annotated[float, Field(description="Thermal resistance in m2-K/W.")],
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
        """Create a Honeybee Energy EnergyMaterialNoMass object."""
        return service(
            identifier=identifier,
            r_value=r_value,
            roughness=roughness,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
