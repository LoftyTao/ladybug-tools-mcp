"""Create an ASHRAE clear sky WEA file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_ashrae_clear_sky_wea as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_ashrae_clear_sky_wea tool.'

    @mcp.tool(
        name='create_ashrae_clear_sky_wea',
        description=(
            "Create a Radiance WEA file from ASHRAE Clear Sky conditions for "
            "a Garden location. Use this for clear-sky daylight or irradiance "
            "setup when the workflow needs synthetic WEA weather for "
            "radiance_create_sky_matrix. This writes WEA data for Radiance "
            "sky workflows; it does not download EPW files or run EnergyPlus. "
            "Returns target, wea_target, summary_view, persistence_receipt, "
            "and report."
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "wea",
            "ashrae-clear-sky",
        },
        timeout=60,
    )
    def create_ashrae_clear_sky_wea(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the ASHRAE clear-sky WEA artifact and target."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dictionary with city, latitude, longitude, time_zone, and optional elevation."),
        ] = None,
        city: Annotated[
            str | None,
            Field(description="Optional city name accepted when location is omitted."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Optional state or region value used when location is omitted."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional latitude accepted when location is omitted."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional longitude accepted when location is omitted."),
        ] = None,
        time_zone: Annotated[
            float | None,
            Field(description="Optional time zone accepted when location is omitted."),
        ] = None,
        elevation: Annotated[
            float | None,
            Field(description="Optional elevation accepted when location is omitted."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness value. Default 1."),
        ] = 1,
        timestep: Annotated[
            int,
            Field(description="WEA timestep. Default 1 for hourly data."),
        ] = 1,
        is_leap_year: Annotated[
            bool,
            Field(description="Whether to create a leap-year WEA."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for WEA artifacts."),
        ] = "artifacts/radiance/wea",
        write_hours: Annotated[
            bool,
            Field(description="Whether to write hour values into the WEA file."),
        ] = False,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full Wea object_dict. Keep false for compact Agent handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a clear-sky WEA target."""
        if identifier is None:
            identifier = city or "ashrae_clear_sky_wea"
        if location is None:
            if latitude is None or longitude is None or time_zone is None:
                raise ValueError(
                    "Provide location, or provide latitude, longitude, and time_zone."
                )
            location = {
                "type": "Location",
                "city": city or identifier,
                "state": region,
                "latitude": latitude,
                "longitude": longitude,
                "time_zone": time_zone,
                "elevation": 0 if elevation is None else elevation,
            }
        return service(
            garden_root=garden_root,
            identifier=identifier,
            location=location,
            sky_clearness=sky_clearness,
            timestep=timestep,
            is_leap_year=is_leap_year,
            output_subdir=output_subdir,
            write_hours=write_hours,
            return_object_dict=return_object_dict,
        )
