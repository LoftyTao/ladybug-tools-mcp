"""Create Glass Honeybee Radiance modifier MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.modifiers import create_radiance_glass_modifier as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_glass_modifier tool."""

    @mcp.tool(
        name="create_radiance_glass_modifier",
        description="Create a Honeybee Radiance Glass modifier. The SDK glass interface uses transmittance or transmissivity, not reflectance. Supports simple rgb_transmittance/rgb_transmissivity numbers, [r, g, b] lists, or full r/g/b transmission inputs. Use garden_root and return_object_dict=false to save a reusable Garden Properties Library modifier target.",
        tags={
            "honeybee-radiance",
            "radiance",
            "modifier",
            "material",
            "glass",
            "rgb-transmittance",
            "rgb-transmissivity",
            "radiance-modifiers",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_glass_modifier(
        identifier: Annotated[str, Field(description="Radiance modifier identifier.")],
        rgb_transmittance: Annotated[
            float | list[float] | None,
            Field(description="Simple visible transmittance for all channels, or [r, g, b] transmittance values."),
        ] = None,
        transmittance: Annotated[
            float | list[float] | None,
            Field(description="Optional natural synonym for rgb_transmittance. Accepts a number or [r, g, b] values."),
        ] = None,
        r_transmittance: Annotated[
            float | None,
            Field(description="Red transmittance. Provide with g_transmittance and b_transmittance."),
        ] = None,
        g_transmittance: Annotated[
            float | None,
            Field(description="Green transmittance. Provide with r_transmittance and b_transmittance."),
        ] = None,
        b_transmittance: Annotated[
            float | None,
            Field(description="Blue transmittance. Provide with r_transmittance and g_transmittance."),
        ] = None,
        rgb_transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Simple transmissivity for all channels, or [r, g, b] transmissivity values."),
        ] = None,
        transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Optional natural synonym for rgb_transmissivity. Accepts a number or [r, g, b] values."),
        ] = None,
        r_transmissivity: Annotated[
            float | None,
            Field(description="Red transmissivity. Provide with g_transmissivity and b_transmissivity."),
        ] = None,
        g_transmissivity: Annotated[
            float | None,
            Field(description="Green transmissivity. Provide with r_transmissivity and b_transmissivity."),
        ] = None,
        b_transmissivity: Annotated[
            float | None,
            Field(description="Blue transmissivity. Provide with r_transmissivity and g_transmissivity."),
        ] = None,
        refraction_index: Annotated[
            float | None,
            Field(description="Optional glass refraction index, such as 1.52 for float glass."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root for saving this modifier."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Glass modifier."""
        if rgb_transmittance is None:
            rgb_transmittance = transmittance
        if rgb_transmissivity is None:
            rgb_transmissivity = transmissivity
        if isinstance(rgb_transmittance, list):
            if len(rgb_transmittance) != 3:
                raise ValueError("rgb_transmittance list must have three values.")
            r_transmittance, g_transmittance, b_transmittance = [
                float(value) for value in rgb_transmittance
            ]
            rgb_transmittance = None
        if isinstance(rgb_transmissivity, list):
            if len(rgb_transmissivity) != 3:
                raise ValueError("rgb_transmissivity list must have three values.")
            r_transmissivity, g_transmissivity, b_transmissivity = [
                float(value) for value in rgb_transmissivity
            ]
            rgb_transmissivity = None
        return service(
            identifier=identifier,
            rgb_transmittance=rgb_transmittance,
            r_transmittance=r_transmittance,
            g_transmittance=g_transmittance,
            b_transmittance=b_transmittance,
            rgb_transmissivity=rgb_transmissivity,
            r_transmissivity=r_transmissivity,
            g_transmissivity=g_transmissivity,
            b_transmissivity=b_transmissivity,
            refraction_index=refraction_index,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
