"""Create WindowConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the EP_create_window_construction tool.'

    @mcp.tool(
        name='EP_create_window_construction',
        description=(
            'Create a Honeybee Energy WindowConstruction from glazing/gas layers ordered from '
            'outside to inside, with an optional frame. For natural requests like a low-U window, '
            'low U-value glazing, U-factor, SHGC, visible transmittance, simple window '
            'construction, or simple glazing system, omit materials and pass u_factor, shgc, and '
            'vt to create a SDK SimpleGlazSys construction directly. With garden_root and '
            'return_object_dict=false, saves a reusable Garden target for '
            'EP_create_construction_set.aperture_set. Returns object_dict plus summary_view, or '
            'target plus persistence_receipt when saved.'
        ),
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
                description="Garden root path containing garden.json, usually GD_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description=(
                    'Return the full construction object_dict (set false with garden_root for a '
                    'compact target/summary/receipt).'
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy WindowConstruction object."""
        from garden.energy.constructionsets import (
            create_window_construction as service,
        )

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
