"""Create a generic Radiance sky MCP alias tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service
from ladybug_tools_mcp.tools.radiance.create_cie_standard_sky import (
    _normalize_sky_aliases,
)


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sky alias tool."""

    @mcp.tool(
        name="create_radiance_sky",
        description="Agent-friendly alias for create_cie_standard_sky. Create a Garden radiance_sky_file target for a point-in-time Radiance CIE sky; accepts natural aliases such as hour and sky_condition.",
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
            "alias",
        },
        timeout=60,
    )
    def create_radiance_sky(
        garden_root: Annotated[str, Field(description="Required exact Garden root path containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Radiance .sky artifact and target.")] = "radiance_sky",
        month: Annotated[int | None, Field(description="Month number for date/time mode.")] = None,
        day: Annotated[int | None, Field(description="Day of month for date/time mode.")] = None,
        time: Annotated[str | float | None, Field(description="Time for date/time mode, for example 12:00 or 12.0.")] = None,
        hour: Annotated[str | float | None, Field(description="Optional alias for time.")] = None,
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny, cloudy, or intermediate.")] = "sunny",
        sky_condition: Annotated[str | int | None, Field(description="Optional alias for sky_type. Numeric CIE values 0-5 are accepted.")] = None,
        sun_angle: Annotated[list[float] | None, Field(description="Optional [altitude, azimuth] hint accepted for compatibility. Ignored when date/time is provided.")] = None,
        radiance_parameters: Annotated[dict[str, Any] | str | None, Field(description="Optional Agent context hint accepted for compatibility. Ignored by sky creation.")] = None,
        latitude: Annotated[float | None, Field(description="Optional site latitude.")] = None,
        longitude: Annotated[float | None, Field(description="Optional site longitude.")] = None,
        time_zone: Annotated[
            float | None,
            Field(description="Alias/context hint for standard_meridian accepted for Agent compatibility."),
        ] = None,
        standard_meridian: Annotated[float | None, Field(description="Optional standard meridian.")] = None,
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        north: Annotated[float | None, Field(description="Optional north angle hint accepted for compatibility. Ignored.")] = None,
        ground_hemisphere: Annotated[bool | None, Field(description="Optional Agent hint accepted for compatibility. Ignored.")] = None,
        return_object_dict: Annotated[bool | None, Field(description="Ignored compatibility hint; sky tools return compact targets and summaries.")] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder for Radiance .sky artifacts.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file through a generic alias."""
        _ = return_object_dict
        if sky_type.strip().lower() == "cie" and sky_condition is None:
            sky_type = "sunny"
        if sky_type.strip().lower().replace("-", "_").replace(" ", "_") in {
            "climatedaysky",
            "climate_day_sky",
            "climate_based",
        } and sky_condition is None:
            sky_type = "sunny"
        time, sky_type = _normalize_sky_aliases(
            time=time,
            hour=hour,
            sky_type=sky_type,
            sky_condition=sky_condition,
        )
        if month is None:
            month = 6
        if day is None:
            day = 21
        if time is None:
            time = "12:00"
        if standard_meridian is None and time_zone is not None:
            standard_meridian = time_zone
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            sky_type=sky_type,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )
