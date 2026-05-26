"""Search EPW map MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.epw_map import search_epw_map as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_search_epw_map tool.'

    @mcp.tool(
        name='search_epw_map',
        description=(
            "Search the Ladybug Tools EPW map for remote weather candidates "
            "by station or location text, station id, source such as TMYx or "
            "TMY3, host such as onebuilding or doe, and optional coordinates. "
            "Returns small epw_map_weather targets for energyplus_download_epw "
            "and accepts text like 'Boston Logan TMY3'. It does not register "
            "weather files in a Garden; call energyplus_download_epw next."
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "search",
            "map",
        },
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def search_epw_map(
        query: Annotated[
            str | None,
            Field(
                description="Optional station, place, country, source, or station id query, such as Boston Logan TMY3."
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description="Optional source filter, for example TMYx, TMY3, CWEC, IWEC."
            ),
        ] = None,
        host: Annotated[
            str | None, Field(description="Optional host filter: onebuilding or doe.")
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional latitude for nearest-first sorting."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional longitude for nearest-first sorting."),
        ] = None,
        max_results: Annotated[
            int, Field(description="Maximum number of EPW map candidate records to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search EPW map records."""
        query_value = query if query is not None else query
        return service(
            query=query_value,
            source=source,
            host=host,
            latitude=latitude,
            longitude=longitude,
            max_results=max_results,
        )
