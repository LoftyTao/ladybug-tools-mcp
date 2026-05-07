"""Create a Ladybug Radiance SkyMatrix target MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_sky_matrix as service


def register(mcp: FastMCP) -> None:
    """Register the create_sky_matrix tool."""

    @mcp.tool(
        name="create_sky_matrix",
        description="Create a Garden sky_matrix target for Ladybug Radiance studies from a wea_file target, Garden weather_file target, Garden-relative EPW path, or ASHRAE clear-sky Location. This is a Radiance sky foundation tool for gendaymtx/SkyMatrix setup; compute=false stores compact parameters, compute=true also stores direct/diffuse sky patch values.",
        tags={
            "honeybee-radiance",
            "ladybug-radiance",
            "radiance",
            "sky",
            "sky-matrix",
            "gendaymtx",
            "wea",
            "garden-mode",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=120,
    )
    def create_sky_matrix(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the sky_matrix target. Defaults to sky_matrix when omitted by an Agent."),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional wea_file target from create_wea_from_weather_file or create_ashrae_clear_sky_wea."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target. Use instead of wea_target, epw_path, or location."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path fallback. Use instead of wea_target, weather_target, or location."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dict for ASHRAE clear-sky SkyMatrix. Use instead of wea/weather/epw inputs."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness when location is used."),
        ] = 1,
        sky_type: Annotated[
            str | None,
            Field(description="Optional Agent hint accepted for compatibility. Ignored; source WEA/location determines sky data."),
        ] = None,
        north: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        north_angle: Annotated[
            float | None,
            Field(description="Optional Agent alias for north."),
        ] = None,
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
            Field(description="Garden-relative output folder for sky matrix JSON artifacts. Weather-folder hints such as imports/weather normalize to artifacts/radiance/sky."),
        ] = "artifacts/radiance/sky",
        return_object_dict: Annotated[
            bool | None,
            Field(description="Ignored compatibility hint; sky matrix tools return compact targets and summaries."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a SkyMatrix target."""
        _ = (return_object_dict, sky_type)
        if identifier is None:
            identifier = "sky_matrix"
        if north_angle is not None:
            north = north_angle
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
