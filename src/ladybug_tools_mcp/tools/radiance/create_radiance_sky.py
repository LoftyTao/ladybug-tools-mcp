"""Create a Radiance sky MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_cie_standard_sky as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_sky tool.'

    @mcp.tool(
        name="create_sky",
        description=(
            "Create a Radiance sky definition artifact from standard sky "
            "inputs for point-in-time daylight workflows. Use "
            "radiance_create_sky_file when a recipe needs a persisted sky file "
            "target. This creates sky input data only; it does not create WEA "
            "weather, sky matrices, or simulation runs. Returns target, "
            "sky_target, summary_view, persistence_receipt, and report."
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "point-in-time",
            "sky-file",
        },
        timeout=60,
    )
    def create_radiance_sky(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        identifier: Annotated[str, Field(description="Stable identifier for the point-in-time Radiance .sky artifact and target.")] = "radiance_sky",
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
