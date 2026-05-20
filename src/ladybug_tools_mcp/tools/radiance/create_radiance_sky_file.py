"""Create Radiance sky file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sky_file tool."""

    @mcp.tool(
        name="create_radiance_sky_file",
        description="Create a Garden radiance_sky_file target for point-in-time Radiance runs.",
        tags={"honeybee-radiance", "radiance", "sky", "sky-file", "write", "safe"},
        timeout=60,
    )
    def create_radiance_sky_file(
        garden_root: Annotated[str, Field(description="Required exact Garden root path containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the Radiance .sky artifact and target.")] = "radiance_sky_file",
        month: Annotated[int, Field(description="Month number for date/time mode.")] = 6,
        day: Annotated[int, Field(description="Day of month for date/time mode.")] = 21,
        time: Annotated[str | float, Field(description="Time for date/time mode.")] = "12:00",
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny or cloudy.")] = "sunny",
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a Radiance sky file."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            sky_type=sky_type,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )
