"""Create Fairyfly SolidMaterial MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.materials import create_fairyfly_solid_material as service


def register(mcp: FastMCP) -> None:
    'Register the therm_create_solid_material tool.'

    @mcp.tool(
        name="create_solid_material",
        description=(
            "Create a Fairyfly THERM SolidMaterial payload for use with "
            "therm_add_shape_to_model. This returns an inline object_dict, not a "
            "Garden target, and it does not attach the material to a model by itself."
        ),
        tags={"fairyfly", "therm", "material", "author", "thermal"},
        timeout=20,
    )
    def create_fairyfly_solid_material(
        name: Annotated[
            str,
            Field(description="Required display name for the Fairyfly/THERM solid material object_dict."),
        ],
        conductivity: Annotated[
            float,
            Field(description="Thermal conductivity in W/m-K."),
        ],
        emissivity: Annotated[
            float,
            Field(description="Front-side infrared hemispherical emissivity."),
        ] = 0.9,
        emissivity_back: Annotated[
            float | None,
            Field(description="Optional back-side emissivity. Defaults to emissivity."),
        ] = None,
        density: Annotated[
            float | None,
            Field(description="Optional density in kg/m3."),
        ] = None,
        porosity: Annotated[
            float | None,
            Field(description="Optional porosity from 0 to 1."),
        ] = None,
        specific_heat: Annotated[
            float | None,
            Field(description="Optional specific heat in J/kg-K."),
        ] = None,
        vapor_diffusion_resistance: Annotated[
            float | None,
            Field(description="Optional vapor diffusion resistance factor."),
        ] = None,
        reflectance: Annotated[
            float | None,
            Field(description="Optional solar reflectance from 0 to 1."),
        ] = None,
        transmittance: Annotated[
            float | None,
            Field(description="Optional solar transmittance from 0 to 1."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
    ) -> dict:
        """Create a Fairyfly SolidMaterial payload."""
        return service(
            name=name,
            conductivity=conductivity,
            emissivity=emissivity,
            emissivity_back=emissivity_back,
            density=density,
            porosity=porosity,
            specific_heat=specific_heat,
            vapor_diffusion_resistance=vapor_diffusion_resistance,
            reflectance=reflectance,
            transmittance=transmittance,
            rgb_color=rgb_color,
        )
