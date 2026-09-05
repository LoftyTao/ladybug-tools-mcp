"""Search weather files MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the EP_search_weather_files tool.'

    @mcp.tool(
        name='EP_search_weather_files',
        description=(
            "Search weather_file targets already managed by a Garden under "
            "imports/weather and registered in garden.json. This tool does "
            "not search bundled FastMCP resources, global SDK weather folders, "
            "remote sites, or UWG parameter files. Import a bundled station from "
            "weather://catalog with EP_import_local_weather, or obtain "
            "another EPW archive from https://climate.onebuilding.org/."
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "search",
            "garden",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_weather_files(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_create['garden_root']; required when saving or reading Garden targets."),
        ],
        query: Annotated[
            str | None,
            Field(
                description="Optional substring query against Garden weather identifiers, station names, station ids, source, host, and EPW paths."
            ),
        ] = None,
        max_results: Annotated[
            int, Field(description="Maximum number of Garden EPW matches to return.")
        ] = 10,
        require_ddy: Annotated[
            bool,
            Field(description="Only return EPW files that have a sibling DDY file."),
        ] = False,
    ) -> dict[str, Any]:
        """Search weather files and return weather_file targets."""
        from garden.run_energy.config import search_weather_files as service

        return service(
            garden_root=garden_root,
            query=query,
            max_results=max_results,
            require_ddy=require_ddy,
        )
