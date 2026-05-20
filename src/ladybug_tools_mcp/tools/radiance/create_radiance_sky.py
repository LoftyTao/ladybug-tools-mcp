"""Create a Radiance sky MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sky tool."""

    @mcp.tool(
        name="create_radiance_sky",
        description="Create a Garden radiance_sky_file target for a point-in-time Radiance CIE sky.",
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
    def create_radiance_sky(
        garden_root: Annotated[str, Field(description="Required exact Garden root path containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Radiance .sky artifact and target.")] = "radiance_sky",
        month: Annotated[int, Field(description="Month number for date/time mode.")] = 6,
        day: Annotated[int, Field(description="Day of month for date/time mode.")] = 21,
        time: Annotated[str | float, Field(description="Time for date/time mode, for example 12:00 or 12.0.")] = "12:00",
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny, cloudy, or intermediate.")] = "sunny",
        latitude: Annotated[float | None, Field(description="Optional site latitude.")] = None,
        longitude: Annotated[float | None, Field(description="Optional site longitude.")] = None,
        standard_meridian: Annotated[float | None, Field(description="Optional standard meridian.")] = None,
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder for Radiance .sky artifacts.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file."""
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
