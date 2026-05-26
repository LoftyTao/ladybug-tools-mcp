"""Create a Ladybug Radiance SkyMatrix target MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_sky_matrix as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_sky_matrix tool.'

    @mcp.tool(
        name='create_sky_matrix',
        description=(
            "Create a Garden sky_matrix target for Ladybug Radiance studies "
            "from a wea_file target, Garden weather_file target, Garden-"
            "relative EPW path, or ASHRAE clear-sky Location. This prepares "
            "gendaymtx/SkyMatrix inputs for annual or matrix recipes; "
            "compute=true also stores direct and diffuse sky patch values. It "
            "does not start a Radiance recipe or download EPW files."
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "sky-matrix",
            "wea",
        },
        timeout=120,
    )
    def create_sky_matrix(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the Radiance sky_matrix target. Defaults to sky_matrix when omitted by an Agent."),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional wea_file target from radiance_create_wea_from_weather_file or radiance_create_ashrae_clear_sky_wea.'),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target. Use instead of wea_target, epw_path, or location."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path. Use instead of wea_target, weather_target, or location."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dict for ASHRAE clear-sky SkyMatrix. Use instead of wea/weather/epw inputs."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness when location is used."),
        ] = 1,
        north: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        high_density: Annotated[
            bool,
            Field(description="Use Reinhart high-density sky patches instead of default Tregenza patches."),
        ] = False,
        ground_reflectance: Annotated[
            float,
            Field(description="Average ground reflectance for the sky matrix."),
        ] = 0.2,
        compute: Annotated[
            bool,
            Field(description="When true, compute and persist direct/diffuse sky patch values. Keep false for compact setup."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for sky matrix JSON artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a SkyMatrix target."""
        if identifier is None:
            identifier = "sky_matrix"
        return service(
            garden_root=garden_root,
            identifier=identifier,
            wea_target=wea_target,
            weather_target=weather_target,
            epw_path=epw_path,
            location=location,
            sky_clearness=sky_clearness,
            north=north,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
            compute=compute,
            output_subdir=output_subdir,
        )
