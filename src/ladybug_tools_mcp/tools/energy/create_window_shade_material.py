"""Create window shade material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_shade_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_window_shade_material tool."""

    @mcp.tool(
        name="create_window_shade_material",
        description="Create a Honeybee Energy EnergyWindowMaterialShade layer for window constructions with shades. Returns object_dict plus summary_view. Use return_detail='summary' for key optical and thermal values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "window",
            "shade",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_window_shade_material(
        identifier: Annotated[
            str, Field(description="Window shade material identifier.")
        ],
        thickness: Annotated[
            float, Field(description="Shade thickness in meters.")
        ] = 0.005,
        solar_transmittance: Annotated[
            float, Field(description="Solar transmittance.")
        ] = 0.4,
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.5,
        visible_transmittance: Annotated[
            float, Field(description="Visible transmittance.")
        ] = 0.4,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.4,
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
        """Create a Honeybee Energy EnergyWindowMaterialShade object."""
        return service(
            identifier=identifier,
            thickness=thickness,
            solar_transmittance=solar_transmittance,
            solar_reflectance=solar_reflectance,
            visible_transmittance=visible_transmittance,
            visible_reflectance=visible_reflectance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
