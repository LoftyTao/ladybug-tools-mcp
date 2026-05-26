"""List Gardens MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import list_gardens as list_gardens_service


def register(mcp: FastMCP) -> None:
    'Register the garden_list tool.'

    @mcp.tool(
        name='list',
        description="List existing Ladybug Tools Garden project workspaces by finding folders that contain garden.json. Use this when a user asks to find saved Gardens, choose a project workspace, or continue prior work. Results are sorted with the most recent Gardens first and may include root paths, descriptions, and base-model summaries. Returns matches with reusable garden_target objects plus summary_view cleanup guidance; pass a selected match path as garden_root to garden_get or downstream tools.",
        tags={
            "garden",
            "project",
            "search",
            "workspace",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_gardens(
        root_dir: Annotated[
            str | None,
            Field(description="Optional directory to search for Garden folders. If omitted, the default Gardens root is searched; a direct Garden root containing garden.json is also accepted."),
        ] = None,
        include_paths: Annotated[
            bool, Field(description="Whether to include Garden root path strings in matches so the user or Agent can pass one as garden_root.")
        ] = True,
        include_base_models: Annotated[
            bool,
            Field(description="Whether to include each Garden's base_honeybee_model, base_dragonfly_model, and related base-model summaries when present."),
        ] = True,
        include_description: Annotated[
            bool, Field(description="Whether to include each Garden description stored in garden.json.")
        ] = True,
    ) -> dict[str, Any]:
        """List Gardens under a root directory."""
        return list_gardens_service(
            root_dir=root_dir,
            include_paths=include_paths,
            include_base_models=include_base_models,
            include_description=include_description,
        )
