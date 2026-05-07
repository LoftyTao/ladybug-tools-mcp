"""Create an ASHRAE clear sky WEA file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_ashrae_clear_sky_wea as service


def register(mcp: FastMCP) -> None:
    """Register the create_ashrae_clear_sky_wea tool."""

    @mcp.tool(
        name="create_ashrae_clear_sky_wea",
        description="Create a Radiance/DAYSIM WEA file artifact from a Ladybug Location using the ASHRAE clear sky model. Use this when no EPW is needed and the user asks for a theoretical clear-sky WEA or sky matrix source.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sky",
            "wea",
            "clear-sky",
            "ashrae",
            "location",
            "garden-mode",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_ashrae_clear_sky_wea(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the WEA artifact and target."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dictionary with city, latitude, longitude, time_zone, and optional elevation."),
        ] = None,
        city: Annotated[
            str | None,
            Field(description="Optional city name accepted when location is omitted."),
        ] = None,
        location_name: Annotated[
            str | None,
            Field(description="Optional location/city name alias accepted when location is omitted."),
        ] = None,
        location_identifier: Annotated[
            str | None,
            Field(description="Optional Agent alias for identifier/location_name."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Optional state/region hint accepted when location is omitted."),
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
        if identifier is None and location_identifier is not None:
            identifier = location_identifier
        if location_name is None and location_identifier is not None:
            location_name = location_identifier
        if identifier is None:
            identifier = city or location_name or "ashrae_clear_sky_wea"
        if location is None:
            if latitude is None or longitude is None or time_zone is None:
                raise ValueError(
                    "Provide location, or provide latitude, longitude, and time_zone."
                )
            location = {
                "type": "Location",
                "city": city or location_name or identifier,
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
