"""Create window blind material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_blind_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_window_blind_material tool."""

    @mcp.tool(
        name="create_window_blind_material",
        description="Create a Honeybee Energy EnergyWindowMaterialBlind layer for window constructions with blinds. Returns object_dict plus summary_view. Use return_detail='summary' for key blind values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "window",
            "blind",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_window_blind_material(
        identifier: Annotated[
            str, Field(description="Window blind material identifier.")
        ],
        slat_orientation: Annotated[
            str, Field(description="Horizontal or Vertical.")
        ] = "Horizontal",
        slat_width: Annotated[
            float, Field(description="Slat width in meters.")
        ] = 0.025,
        slat_separation: Annotated[
            float, Field(description="Slat separation in meters.")
        ] = 0.01875,
        slat_angle: Annotated[float, Field(description="Slat angle in degrees.")] = 45,
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
        """Create a Honeybee Energy EnergyWindowMaterialBlind object."""
        return service(
            identifier=identifier,
            slat_orientation=slat_orientation,
            slat_width=slat_width,
            slat_separation=slat_separation,
            slat_angle=slat_angle,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
