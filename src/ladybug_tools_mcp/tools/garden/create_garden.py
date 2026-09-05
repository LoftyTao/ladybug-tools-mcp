"""Create Garden MCP tool."""

from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the GD_create tool.'

    @mcp.tool(
        name='GD_create',
        description='Create a Ladybug Tools Garden project workspace with garden.json and a Garden-local .gitignore policy. When Git is available on PATH, the tool also initializes the Garden-local .git repository by default. When Git is unavailable, Garden creation still succeeds and report.warnings states that version management is unavailable; after Git is installed, any Garden version tool initializes the repository. Model, library, import, run, artifact, Flowerpot, payload, and temporary directories are created only when their workflows first write to them. Use this before authoring models, running simulations, or saving artifacts when no Garden exists yet. Omit root_dir to use the default Gardens root, or pass root_dir as the exact Garden root path. Existing Gardens are reused idempotently and gain a .git repository when Git is available and the repository is missing; they are not deleted. Returns garden_root, target/garden_target, summary_view, persistence_receipt, and report; pass the top-level garden_root string to later Garden, Energy, Radiance, and Ironbug tools.',
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
        from garden.store import create_garden as create_garden_service

        name = name or (Path(root_dir).name if root_dir else "Ladybug Tools Garden")
        return create_garden_service(
            name=name, root_dir=root_dir, description=description
        )
