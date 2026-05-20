"""Create a Radiance CIE standard sky file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service


_TIME_ZONE_OFFSET_NAMES = {
    -9: "YST",
    -8: "PST",
    -7: "MST",
    -6: "CST",
    -5: "EST",
    -4: "AST",
    0: "GMT",
    1: "CET",
    2: "EET",
    3: "AST",
    4: "GST",
    5.5: "IST",
    9: "JST",
    12: "NZST",
}


def _normalize_time_zone(time_zone: str | int | float | None) -> str | None:
    if time_zone is None:
        return None
    if isinstance(time_zone, str):
        stripped = time_zone.strip()
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
    else:
        numeric = float(time_zone)
    key: int | float = int(numeric) if numeric.is_integer() else numeric
    return _TIME_ZONE_OFFSET_NAMES.get(key, str(time_zone))


def register(mcp: FastMCP) -> None:
    """Register the create_cie_standard_sky tool."""

    @mcp.tool(
        name="create_cie_standard_sky",
        description="Create a Garden radiance_sky_file target backed by a Radiance gensky command. Use this for a single-timestep CIE standard sky such as sunny, cloudy, uniform cloudy, or intermediate. The persisted .sky file starts with !gensky and is meant as a compact Radiance scene include, not a full daylight recipe or annual sky matrix.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sky",
            "cie",
            "standard-sky",
            "gensky",
            "garden-mode",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_cie_standard_sky(
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
        time_zone: Annotated[
            str | int | float | None,
            Field(description="Optional Radiance time zone token such as MST or EST. Numeric offsets like -5 are accepted and normalized to common Radiance tokens."),
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
        sky_type: Annotated[
            str,
            Field(description="CIE sky type: sunny, sunny_no_sun, cloudy, uniform_cloudy, intermediate, or intermediate_no_sun."),
        ] = "sunny",
        latitude: Annotated[
            float | None,
            Field(description="Optional site latitude in degrees for the gensky -a option."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional site longitude in degrees for the gensky -o option."),
        ] = None,
        standard_meridian: Annotated[
            float | None,
            Field(description="Optional standard meridian for the gensky -m option."),
        ] = None,
        ground_reflectance: Annotated[
            float | None,
            Field(description="Optional average ground reflectance for the gensky -g option."),
        ] = None,
        sky_turbidity: Annotated[
            float | None,
            Field(description="Optional sky turbidity for the gensky -t option."),
        ] = None,
        solar_radiance: Annotated[
            float | None,
            Field(description="Optional solar radiance for the gensky -r option."),
        ] = None,
        direct_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Optional direct horizontal irradiance for the gensky -R option."),
        ] = None,
        zenith_brightness: Annotated[
            float | None,
            Field(description="Optional zenith brightness for the gensky -b option."),
        ] = None,
        diffuse_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Optional diffuse horizontal irradiance for the gensky -B option."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance .sky artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file."""
        if identifier is None:
            identifier = "cie_standard_sky"
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            time_zone=_normalize_time_zone(time_zone),
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            sky_type=sky_type,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            sky_turbidity=sky_turbidity,
            solar_radiance=solar_radiance,
            direct_horizontal_irradiance=direct_horizontal_irradiance,
            zenith_brightness=zenith_brightness,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            output_subdir=output_subdir,
        )
