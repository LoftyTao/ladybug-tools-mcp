"""Create Garden MCP tool."""

from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import create_garden as create_garden_service


def register(mcp: FastMCP) -> None:
    'Register the garden_create tool.'

    @mcp.tool(
        name='create',
        description='Create a Ladybug Tools Garden project workspace: a folder with garden.json, first-stage workspace directories, and a Garden-local .gitignore policy. Use this before authoring models, running simulations, or saving artifacts when no Garden exists yet. Omit root_dir to use the default Gardens root, or pass root_dir as the exact Garden root path. Existing Gardens are reused idempotently and are not deleted. Returns garden_root, target/garden_target, summary_view, persistence_receipt, and report; pass the top-level garden_root string to later Garden, Energy, Radiance, and Ironbug tools.',
        tags={
            "garden",
            "project",
            "workspace",
        },
        timeout=20,
    )
    def create_garden(
        name: Annotated[
            str | None,
            Field(
                description="Optional user-facing Garden project name, for example 'Office Study Garden'. If omitted, the name is derived from root_dir or defaults to 'Ladybug Tools Garden'."
            ),
        ] = None,
        root_dir: Annotated[
            str | None,
            Field(
                description="Optional exact Garden root path string. If omitted, the Garden is created under the default Gardens root; use root_dir rather than path or directory."
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Optional Garden description text stored in garden.json."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Optional create-tool hygiene flag. Existing Gardens are reused idempotently; "
                    "overwrite does not delete garden.json, models, libraries, or artifacts."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Garden and return its Garden target, summary, report, and receipt."""
        name = name or (Path(root_dir).name if root_dir else "Ladybug Tools Garden")
        return create_garden_service(
            name=name, root_dir=root_dir, description=description
        )
