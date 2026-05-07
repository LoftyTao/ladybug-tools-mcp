"""Create a Radiance CIE standard sky file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service


_SKY_CONDITION_ALIASES = {
    "0": "sunny",
    "1": "sunny_no_sun",
    "2": "intermediate",
    "3": "intermediate_no_sun",
    "4": "cloudy",
    "5": "uniform_cloudy",
    "clear": "sunny",
    "clear_sky": "sunny",
    "clear_sun": "sunny",
    "sunny_sky": "sunny",
    "sun_up": "sunny",
    "sunup": "sunny",
    "sun_only": "sunny",
    "sunny": "sunny",
    "sunny_no_sun": "sunny_no_sun",
    "intermediate": "intermediate",
    "intermediate_no_sun": "intermediate_no_sun",
    "cloudy": "cloudy",
    "uniform": "uniform_cloudy",
    "uniform_cloudy": "uniform_cloudy",
}
_TIME_ZONE_OFFSET_ALIASES = {
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


def _normalize_sky_aliases(
    *,
    time: str | float | None,
    hour: str | float | None,
    sky_type: str,
    sky_condition: str | int | None,
) -> tuple[str | float | None, str]:
    if time is None and hour is not None:
        time = hour
    if sky_condition is None:
        normalized_type = str(sky_type).strip().lower().replace("-", "_").replace(" ", "_")
        return time, _SKY_CONDITION_ALIASES.get(normalized_type, sky_type)
    normalized_condition = str(sky_condition).strip().lower().replace("-", "_").replace(" ", "_")
    return time, _SKY_CONDITION_ALIASES.get(normalized_condition, str(sky_condition))


def _normalize_time_zone_alias(time_zone: str | int | float | None) -> str | None:
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
    return _TIME_ZONE_OFFSET_ALIASES.get(key, str(time_zone))


def _date_from_season(season: str | None) -> tuple[int, int] | None:
    if season is None:
        return None
    normalized = season.strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "summer": (6, 21),
        "summer_solstice": (6, 21),
        "winter": (12, 21),
        "winter_solstice": (12, 21),
        "spring": (3, 21),
        "spring_equinox": (3, 21),
        "fall": (9, 21),
        "autumn": (9, 21),
        "fall_equinox": (9, 21),
        "autumn_equinox": (9, 21),
    }.get(normalized)


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
        season: Annotated[
            str | None,
            Field(description="Optional Agent shorthand for date when month/day are omitted: summer, winter, spring, fall/autumn."),
        ] = None,
        time: Annotated[
            str | float | None,
            Field(description="Time for date/time mode, for example 12:00 or 12.0."),
        ] = None,
        hour: Annotated[
            str | float | None,
            Field(description="Optional Agent alias for time. For example hour=12 creates a noon sky."),
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
        sky_condition: Annotated[
            str | int | None,
            Field(description="Optional Agent alias for sky_type. Numeric CIE values 0-5 are accepted."),
        ] = None,
        north: Annotated[
            float | None,
            Field(description="Optional north angle hint accepted for Agent compatibility. Ignored for this point-in-time sky file."),
        ] = None,
        ground_hemisphere: Annotated[
            bool | None,
            Field(description="Optional Agent hint accepted for compatibility. Ignored; use ground_reflectance for ground brightness."),
        ] = None,
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
            Field(description="Garden-relative output folder for Radiance .sky artifacts. Natural hints like sky_files normalize to artifacts/radiance/sky."),
        ] = "artifacts/radiance/sky",
        return_object_dict: Annotated[
            bool | None,
            Field(description="Ignored compatibility hint; sky tools return compact targets and summaries."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file."""
        _ = return_object_dict
        if identifier is None:
            identifier = "cie_standard_sky"
        time, sky_type = _normalize_sky_aliases(
            time=time,
            hour=hour,
            sky_type=sky_type,
            sky_condition=sky_condition,
        )
        if (month is None or day is None) and solar_altitude is None and solar_azimuth is None:
            season_date = _date_from_season(season)
            if season_date is None and time is not None:
                season_date = (6, 21)
            if season_date is not None:
                if month is None:
                    month = season_date[0]
                if day is None:
                    day = season_date[1]
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
