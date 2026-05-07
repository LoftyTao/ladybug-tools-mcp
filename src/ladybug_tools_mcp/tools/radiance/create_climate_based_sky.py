"""Create a Radiance climate-based sky file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_climate_based_sky as service
from ladybug_tools_mcp.tools.radiance.create_cie_standard_sky import (
    _normalize_time_zone_alias,
)


def register(mcp: FastMCP) -> None:
    """Register the create_climate_based_sky tool."""

    @mcp.tool(
        name="create_climate_based_sky",
        description="Create a Garden radiance_sky_file target backed by a Radiance gendaylit command. Use this for a single-timestep climate-based sky from direct normal plus diffuse horizontal irradiance or illuminance. The persisted .sky file starts with !gendaylit and is meant as a compact Radiance scene include, not a full daylight recipe or annual sky matrix.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sky",
            "climate-based",
            "gendaylit",
            "irradiance",
            "illuminance",
            "garden-mode",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_climate_based_sky(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the Radiance .sky artifact and target."),
        ] = None,
        month: Annotated[
            int | None,
            Field(description="Month number for date/time mode. Required unless solar angles are used."),
        ] = None,
        day: Annotated[
            int | None,
            Field(description="Day of month for date/time mode. Required unless solar angles are used."),
        ] = None,
        time: Annotated[
            str | float | None,
            Field(description="Time for date/time mode, for example 12:00 or 12.0."),
        ] = None,
        hour: Annotated[
            str | float | None,
            Field(description="Optional Agent alias for time."),
        ] = None,
        time_zone: Annotated[
            str | int | float | None,
            Field(description="Optional Radiance time zone token such as MST or EST. Numeric offsets like -7 are accepted and normalized to common Radiance tokens."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Use local solar time instead of local standard time."),
        ] = False,
        solar_altitude: Annotated[
            float | None,
            Field(description="Optional sun altitude angle in degrees. Provide with solar_azimuth instead of month/day/time."),
        ] = None,
        solar_azimuth: Annotated[
            float | None,
            Field(description="Optional sun azimuth angle in degrees. Provide with solar_altitude instead of month/day/time."),
        ] = None,
        direct_normal_irradiance: Annotated[
            float | None,
            Field(description="Direct normal irradiance for the gendaylit -W option. Provide with diffuse_horizontal_irradiance."),
        ] = None,
        diffuse_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Diffuse horizontal irradiance for the gendaylit -W option. Provide with direct_normal_irradiance."),
        ] = None,
        direct_normal_illuminance: Annotated[
            float | None,
            Field(description="Direct normal illuminance for the gendaylit -L option. Provide with diffuse_horizontal_illuminance."),
        ] = None,
        diffuse_horizontal_illuminance: Annotated[
            float | None,
            Field(description="Diffuse horizontal illuminance for the gendaylit -L option. Provide with direct_normal_illuminance."),
        ] = None,
        output_mode: Annotated[
            int | None,
            Field(description="Optional gendaylit -O output mode, for example 0 for visible radiation."),
        ] = None,
        sky_part: Annotated[
            str | None,
            Field(description="Optional sky part hint: visible/luminance or solar/radiance."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional site latitude in degrees for the gendaylit -a option."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional site longitude in degrees for the gendaylit -o option."),
        ] = None,
        standard_meridian: Annotated[
            float | None,
            Field(description="Optional standard meridian for the gendaylit -m option."),
        ] = None,
        ground_reflectance: Annotated[
            float | None,
            Field(description="Optional average ground reflectance for the gendaylit -g option."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance .sky artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a climate-based Radiance sky file."""
        if identifier is None:
            identifier = "climate_based_sky"
        if time is None and hour is not None:
            time = hour
        if month is None:
            month = 6
        if day is None:
            day = 21
        if time is None:
            time = "12:00"
        if (
            direct_normal_irradiance is None
            and diffuse_horizontal_irradiance is None
            and direct_normal_illuminance is None
            and diffuse_horizontal_illuminance is None
        ):
            direct_normal_irradiance = 800
            diffuse_horizontal_irradiance = 120
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            time_zone=_normalize_time_zone_alias(time_zone),
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            direct_normal_irradiance=direct_normal_irradiance,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            direct_normal_illuminance=direct_normal_illuminance,
            diffuse_horizontal_illuminance=diffuse_horizontal_illuminance,
            output_mode=output_mode,
            sky_part=sky_part,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )
