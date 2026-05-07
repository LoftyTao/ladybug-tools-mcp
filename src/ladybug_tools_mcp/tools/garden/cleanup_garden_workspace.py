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
    """Register the cleanup_garden_workspace tool."""

    @mcp.tool(
        name="cleanup_garden_workspace",
        description="Clean selected Garden workspace scopes like tmp, artifacts, flowerpots, payloads, imports, or runs without touching garden.json, models, or libraries.",
        tags={"garden", "garden-mode", "write", "safe", "workspace-cleanup"},
        timeout=30,
    )
    def cleanup_garden_workspace(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        cleanup_scopes: Annotated[
            list[CleanupScope],
            Field(
                description="Explicit Garden workspace scopes to clean. Allowed values: tmp, artifacts, flowerpots, payloads, imports, runs.",
                min_length=1,
            ),
        ],
        dry_run: Annotated[
            bool,
            Field(
                description="If true, report which selected scopes would be cleaned without deleting any files."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Clean selected non-authoring workspace directories inside one Garden root."""
        return cleanup_garden_workspace_service(
            garden_root=garden_root,
            cleanup_scopes=list(cleanup_scopes),
            dry_run=dry_run,
        )
