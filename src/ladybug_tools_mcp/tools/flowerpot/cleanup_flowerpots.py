"""Cleanup Flowerpots MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import cleanup_flowerpots as service


def register(mcp: FastMCP) -> None:
    'Register the flowerpot_cleanup_all tool.'

    @mcp.tool(
        name="cleanup_all",
        description=(
            "Clean only Garden-local Flowerpot handoff maintenance state: registry "
            "entries and Flowerpot item files. Use orphaned for missing item files, "
            "expired with older_than_days for stale handoff records, or all for a "
            "full handoff reset. Returns removed, skipped, summary_view, "
            "persistence_receipt, and report. It does not modify Garden authoring "
            "truth in garden.json, models/, libraries/, or reusable object storage; "
            "do not pass arguments null or {}."
        ),
        tags={
            "cleanup",
            "flowerpot",
            "handoff",
        },
        timeout=20,
    )
    def cleanup_flowerpots(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        cleanup_scope: Annotated[
            str,
            Field(
                description=(
                    "Cleanup scope: orphaned for registry entries missing item "
                    "files, expired with older_than_days for stale records, or all "
                    "for every Flowerpot handoff item in this Garden."
                )
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
