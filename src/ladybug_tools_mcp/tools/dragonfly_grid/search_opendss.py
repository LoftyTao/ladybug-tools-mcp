"""Search Dragonfly OpenDSS catalog MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the Grid OpenDSS catalog search tool."""

    @mcp.tool(
        name="DF_grid_search_opendss",
        description=(
            "Search Dragonfly Energy OpenDSS catalog identifiers for transformer "
            "properties, power lines, and wires. Returns compact catalog records "
            "for DF_grid_transformer and DF_grid_electrical_connector inputs, "
            "plus matches, summary_view, and report."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "search", "catalog", "list"},
        timeout=20,
    )
    def search_opendss(
        keywords: Annotated[list[str] | None, Field(description="Optional keywords that must all appear in the catalog identifier.")] = None,
        catalogs: Annotated[list[str] | None, Field(description="Optional catalogs: transformer_properties, power_lines, wires.")] = None,
        limit: Annotated[int, Field(description="Maximum compact records to return.")] = 25,
    ) -> dict[str, Any]:
        """Search OpenDSS catalog identifiers."""
        from garden.dragonfly_grid.catalog import search_opendss as service

        return service(keywords=keywords, catalogs=catalogs, limit=limit)
