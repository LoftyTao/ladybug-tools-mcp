"""Get Garden summary MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_get tool.'

    @mcp.tool(
        name='GD_get',
        description='Read a compact Garden manifest summary from an existing garden_root. Use this after GD_list or GD_create to confirm the selected Garden exists, retrieve its target/garden_target, see separate Honeybee, Dragonfly, and Fairyfly base-model targets, and check model/artifact counts. This is a read-only manifest check; it does not create, clean, version, or mutate the Garden. Returns garden_root, target/garden_target, summary_view, and report.',
        tags={
            "garden",
            "project",
            "summary",
            "check",
        },
        timeout=20,
    )
    def get_garden(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'] or a path selected from GD_list matches."),
        ],
    ) -> dict:
        """Return a compact Garden manifest summary."""
        from garden.store import get_garden as service

        return service(garden_root=garden_root)
