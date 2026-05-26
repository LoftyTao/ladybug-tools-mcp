"""Cleanup Garden workspace MCP tool."""

from __future__ import annotations
from typing import Annotated, Any, Literal
from fastmcp import FastMCP
from pydantic import Field
from garden.store import (
    cleanup_garden_workspace as cleanup_garden_workspace_service,
)

CleanupScope = Literal["artifacts", "flowerpots", "imports", "payloads", "runs", "tmp"]


def register(mcp: FastMCP) -> None:
    'Register the garden_cleanup_workspace tool.'

    @mcp.tool(
        name='cleanup_workspace',
        description="Clean selected non-authoring Garden workspace scopes such as tmp, artifacts, flowerpots, payloads, imports, or runs. This maintenance tool does not touch garden.json, models/, or libraries/, and dry_run reports what would be cleaned before deleting files. Use it when a Garden has too many temporary or generated workspace files, not to remove project authoring truth. Returns removed/skipped lists, summary_view, persistence_receipt, and report.",
        tags={
            "cleanup",
            "garden",
            "workspace",
            "maintenance",
        },
        timeout=30,
    )
    def cleanup_garden_workspace(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'] or a path selected from garden_list.")
        ],
        cleanup_scopes: Annotated[
            list[CleanupScope],
            Field(
                description="Explicit Garden workspace scopes to clean. Allowed values are tmp, artifacts, flowerpots, payloads, imports, and runs; models and libraries are intentionally not valid cleanup scopes.",
                min_length=1,
            ),
        ],
        dry_run: Annotated[
            bool,
            Field(
                description="If true, report which selected scopes would be cleaned without deleting files; use this before destructive cleanup when the user has not explicitly confirmed."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Clean selected non-authoring workspace directories inside one Garden root."""
        return cleanup_garden_workspace_service(
            garden_root=garden_root,
            cleanup_scopes=list(cleanup_scopes),
            dry_run=dry_run,
        )
