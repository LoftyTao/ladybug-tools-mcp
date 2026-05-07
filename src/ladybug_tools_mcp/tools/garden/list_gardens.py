"""List Gardens MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import list_gardens as list_gardens_service


def register(mcp: FastMCP) -> None:
    """Register the list_gardens tool."""

    @mcp.tool(
        name="list_gardens",
        description="List projects and project workspaces by finding existing Ladybug Tools Gardens, returned with the most recently created Gardens first. Use this when a user asks to list Gardens, find existing Gardens, discover project workspaces, or choose a saved Garden. At onboarding, show the first five matches and suggest cleanup when more than ten Gardens exist. Returns reusable garden_target objects for later Garden tools.",
        tags={
            "garden",
            "garden-mode",
            "project",
            "project-workspace",
            "find-existing-gardens",
            "list-projects",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_gardens(
        root_dir: Annotated[
            str | None,
            Field(description="Optional root directory containing Garden folders."),
        ] = None,
        include_paths: Annotated[
            bool, Field(description="Whether to include Garden root paths in matches.")
        ] = True,
        include_base_model: Annotated[
            bool,
            Field(description="Whether to include each Garden's base model summary."),
        ] = True,
        include_description: Annotated[
            bool, Field(description="Whether to include each Garden description.")
        ] = True,
    ) -> dict[str, Any]:
        """List Gardens under a root directory."""
        return list_gardens_service(
            root_dir=root_dir,
            include_paths=include_paths,
            include_base_model=include_base_model,
            include_description=include_description,
        )
