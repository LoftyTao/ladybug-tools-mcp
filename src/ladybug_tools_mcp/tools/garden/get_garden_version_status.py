"""Get Garden Version Status MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import get_garden_version_status as service


def register(mcp: FastMCP) -> None:
    'Register the garden_get_version_status tool.'

    @mcp.tool(
        name='get_version_status',
        description=(
            "Check whether Garden authoring truth has uncommitted changes that "
            "should become a Garden version checkpoint. Use before restore and "
            "at the end of Agent workflows to decide whether garden_create_version "
            "is needed. Returns summary_view compact dirty-state counts and a "
            "report only; it is not a file diff, model diff, or Git log reader."
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
                    "garden_create['garden_root']; the status covers Garden "
                    "authoring truth paths, not arbitrary files."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return Garden version status."""
        return service(garden_root=garden_root)
