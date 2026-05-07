"""Create window gas material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_gas_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_window_gas_material tool."""

    @mcp.tool(
        name="create_window_gas_material",
        description="Create a Honeybee Energy EnergyWindowMaterialGas gap layer for WindowConstruction assemblies. Returns object_dict plus summary_view. Use return_detail='summary' for key gas values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "window",
            "gas",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_window_gas_material(
        identifier: Annotated[str, Field(description="Gas material identifier.")],
        thickness: Annotated[
            float, Field(description="Gas gap thickness in meters.")
        ] = 0.0125,
        gas_type: Annotated[
            str, Field(description="Gas type: Air, Argon, Krypton, or Xenon.")
        ] = "Air",
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
        """Create a Honeybee Energy EnergyWindowMaterialGas object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            gas_type=gas_type,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
