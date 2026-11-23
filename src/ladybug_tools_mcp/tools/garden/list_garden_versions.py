"""List Garden Versions MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_list_versions tool.'

    @mcp.tool(
        name='GD_list_versions',
        description=(
            'List compact Garden version history for choosing undo, restore, go back, previous '
            'step, checkpoint, or rollback targets. Returns newest-first records under matches '
            "and versions; pass a record's version_id or target to GD_restore_version. Records "
            'include subjects, metadata, and version targets without diffs or file bodies.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "rollback",
            "restore",
            "search",
            "version",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_versions(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']; list history for this one Garden."
                )
            ),
        ],
        limit: Annotated[
            int,
            Field(
                description=(
                    "Maximum number of newest Garden version records to return "
                    "under matches and versions; use 1-50."
                ),
                ge=1,
                le=50,
            ),
        ] = 10,
    ) -> dict[str, Any]:
        """List Garden versions."""
        from garden.versions import list_garden_versions as service

        return service(garden_root=garden_root, limit=limit)
