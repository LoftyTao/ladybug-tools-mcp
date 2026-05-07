"""Get Garden Version Status MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import get_garden_version_status as service


def register(mcp: FastMCP) -> None:
    """Register the get_garden_version_status tool."""

    @mcp.tool(
        name="get_garden_version_status",
        description=(
            "Check whether Garden authoring truth has uncommitted version, history, "
            "checkpoint, undo, or restore changes. Use before restore and at the "
            "end of Agent workflows to decide whether create_garden_version is "
            "needed. Returns compact counts only; no diff or file bodies."
        ),
        tags={
            "garden",
            "garden-mode",
            "version",
            "status",
            "history",
            "checkpoint",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_garden_version_status(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
    ) -> dict[str, Any]:
        """Return Garden version status."""
        return service(garden_root=garden_root)
