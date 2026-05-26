"""Create opaque Honeybee Radiance modifier MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.modifiers import create_radiance_opaque_modifier as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_opaque_modifier tool.'

    @mcp.tool(
        name="create_opaque_modifier",
        description=(
            "Create an opaque Honeybee Radiance modifier using the SDK Plastic "
            "material with RGB reflectance. Use garden_root and "
            "return_object_dict=false to save a reusable Garden Properties "
            "Library modifier target for Honeybee face, aperture, door, or "
            "shade Radiance modifier fields. This does not create Energy "
            "opaque materials or Radiance sensor geometry."
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "opaque",
        },
        timeout=20,
    )
    def create_radiance_opaque_modifier(
        identifier: Annotated[str, Field(description="Radiance Plastic/Opaque modifier identifier.")],
        rgb_reflectance: Annotated[
            float | list[float] | None,
            Field(description="Simple reflectance for red, green, and blue channels."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        specularity: Annotated[float, Field(description="Plastic specularity fraction.")] = 0.0,
        roughness: Annotated[float, Field(description="Plastic roughness fraction.")] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create an opaque Honeybee Radiance modifier."""
        if isinstance(rgb_reflectance, list):
            if len(rgb_reflectance) != 3:
                raise ValueError("rgb_reflectance list must have three values.")
            r_reflectance, g_reflectance, b_reflectance = [
                float(value) for value in rgb_reflectance
            ]
            rgb_reflectance = None
        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
