"""Create simple glazing system material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_simple_glazing_material as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_simple_glazing_material tool.'

    @mcp.tool(
        name='create_simple_glazing_material',
        description="Create a Honeybee Energy EnergyWindowMaterialSimpleGlazSys material for a full simplified glazing system using U-factor, SHGC, and visible transmittance. It must be the only layer in a WindowConstruction; use energy_create_window_construction with u_factor, shgc, and vt when the user wants a complete reusable window construction target. Returns object_dict plus summary_view, or a saved material target when garden_root is provided and return_object_dict=false.",
        tags={
            "energy",
            "construction",
            "material",
            "window",
            "glazing",
            "u-factor",
            "shgc",
            "author",
        },
        timeout=20,
    )
    def create_simple_glazing_material(
        identifier: Annotated[
            str, Field(description="Simple glazing material identifier.")
        ],
        u_factor: Annotated[
            float | None, Field(description="Glazing system U-factor in W/m2-K.")
        ] = None,
        shgc: Annotated[
            float | None, Field(description="Solar heat gain coefficient.")
        ] = None,
        vt: Annotated[float, Field(description="Visible transmittance.")] = 0.6,
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
        """Create a Honeybee Energy EnergyWindowMaterialSimpleGlazSys object."""
        if u_factor is None:
            raise ValueError("u_factor is required.")
        if shgc is None:
            raise ValueError("shgc is required.")
        return service(
            identifier=identifier,
            u_factor=u_factor,
            shgc=shgc,
            vt=vt,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
