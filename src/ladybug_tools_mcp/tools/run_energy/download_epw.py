"""Download EPW map weather MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.epw_map import download_epw as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_download_epw tool.'

    @mcp.tool(
        name='download_epw',
        description=(
            "Download a selected Ladybug Tools EPW map weather archive into "
            "the Garden imports/weather area, register it in garden.json, and "
            "return a reusable weather_file target for "
            "energyplus_start_simulation. Normal path: "
            "energyplus_search_epw_map(query='Boston Logan TMY3', "
            "max_results=1), then energyplus_download_epw with the returned "
            "epw_map_target and the same garden_root. This tool has no "
            "global weather folder mode and does not start EnergyPlus, UWG, "
            "or Radiance workflows. If the remote weather website fails, the "
            "tool returns report.status='blocked' with recovery download "
            "fields."
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "author",
            "ddy",
        },
        timeout=300,
    )
    def download_epw(
        garden_root: Annotated[
            str,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ],
        epw_map_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional EPW map target returned by energyplus_search_epw_map; pass the target dict, not a weather URL. If omitted, provide query.'
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
            Field(description="Optional EPW source filter, for example TMYx or TMY3."),
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
