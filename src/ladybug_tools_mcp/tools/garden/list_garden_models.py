"""List Garden Models MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import list_garden_models as service


def register(mcp: FastMCP) -> None:
    'Register the garden_list_models tool.'

    @mcp.tool(
        name='list_models',
        description="List registered Honeybee, Dragonfly, and Fairyfly model targets in a Garden, including HBJSON/DFJSON authoring records and reusable model_target entries. Use this to choose an existing model target before edit, export, visualization, energy, Radiance, or THERM workflows. Returns matches plus summary_view with base_honeybee_model, base_dragonfly_model, and base_fairyfly_model when present; pass a selected model target to downstream model tools.",
        tags={
            "garden",
            "model",
            "search",
            "honeybee",
            "dragonfly",
            "fairyfly",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_models(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'] or garden_get['garden_root'].")
        ],
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden-relative model file paths such as models/*.hbjson or models/*.dfjson in each match."),
        ] = True,
    ) -> dict[str, Any]:
        """List registered Garden model targets."""
        return service(garden_root=garden_root, include_paths=include_paths)
