"""Create Garden MCP tool."""

from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import create_garden as create_garden_service


def register(mcp: FastMCP) -> None:
    """Register the create_garden tool."""

    @mcp.tool(
        name="create_garden",
        description='Create a Ladybug Tools Garden project workspace and persistence container with garden.json, first-stage folders, and a Garden-local .gitignore policy. Preferred default-root call shape: {"name":"create_garden","arguments":{"name":"Office Garden"}}. Omit root_dir to create under the default Gardens root, or pass "root_dir" for an exact Garden root path such as tests/.artifacts/.../garden. The folder argument is root_dir; do not use path or directory. Later tools need the returned top-level garden_root string, not the garden_target/target dict. Use a complete arguments object; do not pass arguments null or {}.',
        tags={
            "garden",
            "garden-mode",
            "project-workspace",
            "persistence-container",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_garden(
        name: Annotated[
            str | None,
            Field(
                description="Optional Garden name string, for example 'Office Study Garden'. If omitted, a name is derived from the root directory."
            ),
        ] = None,
        root_dir: Annotated[
            str | None,
            Field(
                description="Optional exact Garden root path string. If omitted, the Garden is created under the default Gardens root."
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Optional Garden description for the manifest."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Garden and return its Garden target, summary, report, and receipt."""
        name = name or (Path(root_dir).name if root_dir else "Ladybug Tools Garden")
        return create_garden_service(
            name=name, root_dir=root_dir, description=description
        )
