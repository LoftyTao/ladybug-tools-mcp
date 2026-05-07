"""Create a WEA file from Garden weather data MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.sky import create_wea_from_weather_file as service


def register(mcp: FastMCP) -> None:
    """Register the create_wea_from_weather_file tool."""

    @mcp.tool(
        name="create_wea_from_weather_file",
        description="Create a Radiance/DAYSIM WEA file artifact from a Garden-managed weather_file target or Garden-relative EPW path. Preferred Agent path: pass weather_target returned by download_epw/search_weather_files. Returns a compact wea_file target for create_sky_matrix and later run_radiance workflows.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sky",
            "wea",
            "weather",
            "epw",
            "garden-mode",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_wea_from_weather_file(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the WEA artifact and target."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target from download_epw/search_weather_files."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path fallback. Use instead of weather_target."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="WEA timestep. Default 1 for hourly data."),
        ] = 1,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year to keep in the WEA."),
        ] = None,
        write_hours: Annotated[
            bool,
            Field(description="Whether to write hour values into the WEA file."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for WEA artifacts."),
        ] = "artifacts/radiance/wea",
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full Wea object_dict. Keep false for compact Agent handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a WEA file target from EPW weather data."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            weather_target=weather_target,
            epw_path=epw_path,
            timestep=timestep,
            hoys=hoys,
            write_hours=write_hours,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
