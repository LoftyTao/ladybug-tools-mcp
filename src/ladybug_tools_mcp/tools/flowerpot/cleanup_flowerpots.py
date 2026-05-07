"""Cleanup Flowerpots MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import cleanup_flowerpots as service


def register(mcp: FastMCP) -> None:
    """Register the cleanup_flowerpots tool."""

    @mcp.tool(
        name="cleanup_flowerpots",
        description="Clean Garden-local Flowerpot handoff registry entries and item files without touching Garden authoring truth in garden.json, models, or libraries. Supports dry_run for safe previews and cleanup_scope values orphaned, expired, or all. Do not pass arguments null or {}.",
        tags={
            "flowerpot",
            "garden-mode",
            "platform-handoff",
            "registered-container",
            "cleanup",
            "write",
            "safe",
        },
        timeout=20,
    )
    def cleanup_flowerpots(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        cleanup_scope: Annotated[
            str,
            Field(
                description="Cleanup scope. Use orphaned for registry entries missing item files, expired with older_than_days, or all for all Flowerpot handoff items."
            ),
        ] = "orphaned",
        dry_run: Annotated[
            bool,
            Field(description="Preview cleanup without deleting Flowerpot files."),
        ] = False,
        older_than_days: Annotated[
            int | None,
            Field(
                description="Optional age threshold in days for cleanup_scope=expired."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Clean registered Flowerpot handoff state."""
        return service(
            garden_root=garden_root,
            cleanup_scope=cleanup_scope,
            dry_run=dry_run,
            older_than_days=older_than_days,
        )
