"""Create Mirror Honeybee Radiance modifier MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.modifiers import create_radiance_mirror_modifier as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_mirror_modifier tool.'

    @mcp.tool(
        name="create_mirror_modifier",
        description=(
            "Create a Honeybee Radiance Mirror modifier with RGB reflectance "
            "for planar virtual-source reflections. Use garden_root and "
            "return_object_dict=false to save a reusable Garden Properties "
            "Library modifier target. This is a Radiance optical modifier, not "
            "geometry, a view, or an Energy construction."
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "mirror",
        },
        timeout=20,
    )
    def create_radiance_mirror_modifier(
        identifier: Annotated[str, Field(description="Radiance Mirror modifier identifier.")],
        rgb_reflectance: Annotated[
            float | None,
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
        alternate_material: Annotated[
            str | None,
            Field(description="Optional alternate material for non-source rays, such as void."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Mirror modifier."""
        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            alternate_material=alternate_material,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
