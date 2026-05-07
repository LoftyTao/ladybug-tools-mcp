"""Search EPW map MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.epw_map import search_epw_map as service


def register(mcp: FastMCP) -> None:
    """Register the search_epw_map tool."""

    @mcp.tool(
        name="search_epw_map",
        description="Search the Ladybug Tools EPW map for remote weather candidates by station/location text, station id, source such as TMYx/TMY3, host such as onebuilding/doe, and optional coordinates. Returns a small epw_map_weather target for download_epw; accepts human text like 'Boston Logan TMY3'; never returns the full EPW map.",
        tags={
            "run-energy",
            "energy",
            "weather",
            "epw",
            "epw-map",
            "download",
            "search",
            "target",
            "read-only",
            "safe",
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
            int, Field(description="Maximum number of candidate records to return.")
        ] = 10,
        detail: Annotated[
            str | None,
            Field(
                description="Optional Agent search-detail hint accepted for compatibility with Code Mode search habits. Ignored; EPW map results are always compact targets."
            ),
        ] = None,
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
