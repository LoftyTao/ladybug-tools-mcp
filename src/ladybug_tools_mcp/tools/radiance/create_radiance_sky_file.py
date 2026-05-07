"""Create Radiance sky file MCP alias tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service
from ladybug_tools_mcp.tools.radiance.create_cie_standard_sky import (
    _normalize_sky_aliases,
)


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sky_file alias tool."""

    @mcp.tool(
        name="create_radiance_sky_file",
        description="Alias for create_radiance_sky/create_cie_standard_sky. Creates a Garden radiance_sky_file target for point-in-time Radiance runs.",
        tags={"honeybee-radiance", "radiance", "sky", "sky-file", "alias", "write", "safe"},
        timeout=60,
    )
    def create_radiance_sky_file(
        garden_root: Annotated[str, Field(description="Required exact Garden root path containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Radiance .sky artifact and target.")] = "radiance_sky_file",
        month: Annotated[int | None, Field(description="Month number for date/time mode.")] = None,
        day: Annotated[int | None, Field(description="Day of month for date/time mode.")] = None,
        time: Annotated[str | float | None, Field(description="Time for date/time mode.")] = None,
        hour: Annotated[str | float | None, Field(description="Optional alias for time.")] = None,
        minute: Annotated[int | float | None, Field(description="Optional minute hint accepted for Agent compatibility. Ignored; use fractional hour/time instead.")] = None,
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny or cloudy.")] = "sunny",
        radiance_sky_type: Annotated[
            str | None,
            Field(description="Optional Agent context hint accepted for compatibility. Ignored by this CIE sky alias."),
        ] = None,
        sky_condition: Annotated[str | int | None, Field(description="Optional alias for sky_type.")] = None,
        location: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional location/output context accepted for Agent compatibility. Ignored by this CIE sky alias."),
        ] = None,
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        weather_file_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional EPW/weather target accepted as Agent context. This CIE sky alias does not need the weather file."),
        ] = None,
        epw_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for weather_file_target accepted for Agent compatibility."),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for weather_file_target accepted for Agent compatibility."),
        ] = None,
        north: Annotated[
            float | None,
            Field(description="Optional north angle hint accepted for Agent compatibility. Ignored for this point-in-time sky file."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional model context hint accepted for Agent compatibility. Ignored."),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(description="Ignored compatibility hint; sky tools return compact targets and summaries."),
        ] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a Radiance sky file through a generic sky-file alias."""
        _ = (
            north,
            model_target,
            return_object_dict,
            weather_file_target,
            epw_target,
            weather_target,
            minute,
            radiance_sky_type,
            location,
        )
        time, sky_type = _normalize_sky_aliases(
            time=time,
            hour=hour,
            sky_type=sky_type,
            sky_condition=sky_condition,
        )
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=6 if month is None else month,
            day=21 if day is None else day,
            time="12:00" if time is None else time,
            sky_type=sky_type,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )
