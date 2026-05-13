"""Get Garden summary MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_garden as service


def register(mcp: FastMCP) -> None:
    """Register the get_garden tool."""

    @mcp.tool(
        name="get_garden",
        description="Read a compact Garden manifest summary from an existing garden_root. Use this to confirm a Garden exists, get its target, split Honeybee/Dragonfly base model targets, and counts; it does not create or mutate the Garden.",
        tags={"garden", "project", "manifest", "summary", "read", "safe"},
        timeout=20,
    )
    def get_garden(
        garden_root: Annotated[
            str,
            Field(description="Exact Garden root path string containing garden.json."),
        ],
    ) -> dict:
        """Return a compact Garden manifest summary."""
        return service(garden_root=garden_root)
