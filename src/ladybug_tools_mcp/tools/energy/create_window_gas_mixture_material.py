"""Create window gas mixture material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_gas_mixture_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_window_gas_mixture_material tool.'

    @mcp.tool(
        name='create_window_gas_mixture_material',
        description=(
            "Create a Honeybee Energy EnergyWindowMaterialGasMixture gap layer "
            "from gas types and fractions for WindowConstruction assemblies. "
            "This is a reusable gas layer, not a full glazing construction. "
            "Returns object_dict plus summary_view; return_detail='full' also "
            "includes a material property matrix."
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
    def create_window_gas_mixture_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyWindowMaterialGasMixture identifier for a window gas mixture layer.")
        ],
        thickness: Annotated[
            float, Field(description="Gas gap thickness in meters.")
        ] = 0.0125,
        gas_types: Annotated[
            list[str] | None, Field(description="Gas type list.")
        ] = None,
        gas_fractions: Annotated[
            list[float] | None, Field(description="Gas fraction list summing to 1.")
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
        """Create a Honeybee Energy EnergyWindowMaterialGasMixture object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            gas_types=gas_types,
            gas_fractions=gas_fractions,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
