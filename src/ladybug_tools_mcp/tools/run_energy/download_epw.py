"""Download EPW map weather MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.epw_map import download_epw as service


def register(mcp: FastMCP) -> None:
    """Register the download_epw tool."""

    @mcp.tool(
        name="download_epw",
        description='Download a selected Ladybug Tools EPW map weather archive into the Garden imports/weather area, register it in garden.json, and return a reusable weather_file target for start_energy_run. Required natural path: search_epw_map(query="Boston Logan TMY3", max_results=1), then download_epw(garden_root="<Garden>", epw_map_target=matches[0].target). This tool has no global/default weather folder mode.',
        tags={
            "run-energy",
            "energy",
            "weather",
            "epw",
            "epw-map",
            "download",
            "weather-file",
            "target",
            "write",
            "safe",
        },
        timeout=300,
    )
    def download_epw(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path. Downloaded EPW/DDY files are always stored under this Garden's imports/weather folder."
            ),
        ],
        epw_map_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional epw_map_weather target returned by search_epw_map matches[i].target."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description="Optional exact station/place query when no target is passed."
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(description="Optional source filter, for example TMYx or TMY3."),
        ] = None,
        host: Annotated[
            str | None, Field(description="Optional host filter: onebuilding or doe.")
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Whether to re-download when the zip already exists."),
        ] = False,
    ) -> dict[str, Any]:
        """Download EPW weather data and return a weather_file target."""
        return service(
            garden_root=garden_root,
            epw_map_target=epw_map_target,
            query=query,
            source=source,
            host=host,
            overwrite=overwrite,
        )
