"""Create window blind material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_blind_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_window_blind_material tool.'

    @mcp.tool(
        name='create_window_blind_material',
        description=(
            "Create a Honeybee Energy EnergyWindowMaterialBlind layer for "
            "window constructions with blinds. This returns a window material "
            "layer for later construction assembly; it does not assign blinds "
            "to apertures. Returns object_dict plus summary_view; "
            "return_detail='full' also includes a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "blind",
        },
        timeout=20,
    )
    def create_window_blind_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyWindowMaterialBlind identifier for a window blind layer.")
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
