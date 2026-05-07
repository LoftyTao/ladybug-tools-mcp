"""Create Trans Honeybee Radiance modifier MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.modifiers import create_radiance_trans_modifier as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_trans_modifier tool."""

    @mcp.tool(
        name="create_radiance_trans_modifier",
        description="Create a Honeybee Radiance Trans translucent modifier. Supports simple rgb_reflectance or full r/g/b reflectance inputs, plus transmitted diffuse/specular fractions. Use garden_root and return_object_dict=false to save a reusable Garden Properties Library modifier target.",
        tags={
            "honeybee-radiance",
            "radiance",
            "modifier",
            "material",
            "trans",
            "translucent",
            "rgb-reflectance",
            "radiance-modifiers",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_trans_modifier(
        identifier: Annotated[str, Field(description="Radiance modifier identifier.")],
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
        specularity: Annotated[float, Field(description="Trans specularity fraction.")] = 0.0,
        roughness: Annotated[float, Field(description="Trans roughness fraction.")] = 0.0,
        transmitted_diff: Annotated[
            float,
            Field(description="Diffuse transmitted fraction."),
        ] = 0.0,
        transmitted_spec: Annotated[
            float,
            Field(description="Specular transmitted fraction."),
        ] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root for saving this modifier."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Trans modifier."""
        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            transmitted_diff=transmitted_diff,
            transmitted_spec=transmitted_spec,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
