"""Create ShadeConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_shade_construction as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_shade_construction tool.'

    @mcp.tool(
        name='create_shade_construction',
        description=(
            "Create a Honeybee Energy ShadeConstruction for outdoor Honeybee "
            "Shade energy properties. This sets reflectance and specular "
            "behavior for an energy construction; it does not create Honeybee "
            "shade geometry or Radiance materials. Returns object_dict plus "
            "summary_view with the scalar property values."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "shade",
        },
        timeout=20,
    )
    def create_shade_construction(
        identifier: Annotated[str, Field(description="Honeybee ShadeConstruction identifier for an Energy shade surface.")],
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.2,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.2,
        is_specular: Annotated[
            bool, Field(description="Whether reflection is specular.")
        ] = False,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full keeps the same concise fields for this scalar construction."
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
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ShadeConstruction object."""
        return service(
            identifier=identifier,
            solar_reflectance=solar_reflectance,
            visible_reflectance=visible_reflectance,
            is_specular=is_specular,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
