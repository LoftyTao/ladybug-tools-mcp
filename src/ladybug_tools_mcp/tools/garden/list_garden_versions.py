"""List Garden Versions MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import list_garden_versions as service


def register(mcp: FastMCP) -> None:
    """Register the list_garden_versions tool."""

    @mcp.tool(
        name="list_garden_versions",
        description=(
            "List compact Git-backed Garden version history for choosing undo, "
            "restore, go back, previous step, checkpoint, or rollback targets. "
            "Returns newest-first records under matches and versions; use a "
            "record's version_id string for restore_garden_version. Returns "
            "commit subjects and structured summaries only; never returns Git "
            "diff, patch text, HBJSON bodies, or full file contents."
        ),
        tags={
            "garden",
            "garden-mode",
            "version",
            "history",
            "checkpoint",
            "undo",
            "restore",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_versions(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        limit: Annotated[
            int,
            Field(
                description="Maximum number of recent versions to return.",
                ge=1,
                le=50,
            ),
        ] = 10,
    ) -> dict[str, Any]:
        """List Garden versions."""
        return service(garden_root=garden_root, limit=limit)
