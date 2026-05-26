"""Create WindowConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_construction as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_window_construction tool.'

    @mcp.tool(
        name='create_window_construction',
        description='Create a Honeybee Energy WindowConstruction from glazing/gas layers ordered from outside to inside, with an optional frame. For natural requests like a low-U window, low U-value glazing, U-factor, SHGC, visible transmittance, simple window construction, or simple glazing system, omit materials and pass u_factor, shgc, and vt to create a SDK SimpleGlazSys construction directly. In an existing Garden workflow, pass garden_root and set return_object_dict=false to save a reusable Garden target, then pass the returned target to energy_create_construction_set.aperture_set for the exterior window slot. Do not handwrite a WindowConstruction dict. Returns object_dict plus summary_view, or target plus persistence_receipt when saved.',
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
    def create_window_construction(
        identifier: Annotated[str, Field(description="WindowConstruction identifier.")],
        materials: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Window material layers from outside to inside. Omit when using u_factor, shgc, and vt simple-parameter creation."
            ),
        ] = None,
        u_factor: Annotated[
            float | None,
            Field(
                description="U-factor in W/m2-K for SDK simple-parameter window construction. Use the exact argument name u_factor when the user asks for a low-U window and has not supplied material layers."
            ),
        ] = None,
        shgc: Annotated[
            float | None,
            Field(
                description="Solar heat gain coefficient for SDK simple-parameter window construction."
            ),
        ] = None,
        vt: Annotated[
            float,
            Field(
                description="Visible transmittance for SDK simple-parameter window construction."
            ),
        ] = 0.6,
        frame: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional EnergyWindowFrame object_dict or library identifier."
            ),
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full also returns a layer_matrix with material rows."
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
                description="Return the full construction object_dict. Set return_object_dict=false with garden_root to pass only target/summary/receipt as a reusable Garden target; not a handwritten WindowConstruction dict."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy WindowConstruction object."""
        return service(
            identifier=identifier,
            materials=materials,
            u_factor=u_factor,
            shgc=shgc,
            vt=vt,
            frame=frame,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
