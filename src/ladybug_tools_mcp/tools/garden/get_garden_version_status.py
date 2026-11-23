"""Get Garden Version Status MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_get_version_status tool.'

    @mcp.tool(
        name='GD_get_version_status',
        description=(
            'Check whether Garden authoring truth has uncommitted changes that should become a '
            'Garden version checkpoint. Use before restore or after authoring changes to decide '
            'whether GD_create_version is needed. Returns compact dirty-state counts in '
            'summary_view and a report.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "summary",
            "version",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_garden_version_status(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']; the status covers Garden "
                    "authoring truth paths, not arbitrary files."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return Garden version status."""
        from garden.versions import get_garden_version_status as service

        return service(garden_root=garden_root)
