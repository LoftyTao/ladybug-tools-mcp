"""Create custom window gas material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_custom_window_gas_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_custom_window_gas_material tool.'

    @mcp.tool(
        name='create_custom_window_gas_material',
        description=(
            "Create a Honeybee Energy EnergyWindowMaterialGasCustom gap layer "
            "for window construction assemblies when built-in gas types are not "
            "enough. This is a reusable material layer, not a full construction "
            "or an EnergyPlus run input by itself. Returns object_dict plus "
            "summary_view; return_detail='full' also includes a material "
            "property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "window-layer",
        },
        timeout=20,
    )
    def create_custom_window_gas_material(
        identifier: Annotated[
            str, Field(description="Custom EnergyWindowMaterialGasCustom identifier for a window gas gap layer.")
        ],
        thickness: Annotated[float, Field(description="Gas gap thickness in meters.")],
        conductivity_coeff_a: Annotated[
            float, Field(description="Conductivity A coefficient.")
        ],
        viscosity_coeff_a: Annotated[
            float, Field(description="Viscosity A coefficient.")
        ],
        specific_heat_coeff_a: Annotated[
            float, Field(description="Specific heat A coefficient.")
        ],
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
        """Create a Honeybee Energy EnergyWindowMaterialGasCustom object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity_coeff_a=conductivity_coeff_a,
            viscosity_coeff_a=viscosity_coeff_a,
            specific_heat_coeff_a=specific_heat_coeff_a,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
