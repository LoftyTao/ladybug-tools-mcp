"""List Garden Models MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import list_garden_models as service


def register(mcp: FastMCP) -> None:
    """Register the list_garden_models tool."""

    @mcp.tool(
        name="list_garden_models",
        description="List registered Honeybee and Dragonfly model targets, HBJSON/DFJSON authoring files, and reusable model_target entries in a Garden.",
        tags={
            "garden",
            "garden-mode",
            "model",
            "registered-models",
            "model-targets",
            "hbjson",
            "dfjson",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_models(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden-relative model file paths."),
        ] = True,
    ) -> dict[str, Any]:
        """List registered Garden model targets."""
        return service(garden_root=garden_root, include_paths=include_paths)
