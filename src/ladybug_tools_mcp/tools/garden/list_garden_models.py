"""List Garden Models MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the GD_list_models tool.'

    @mcp.tool(
        name='GD_list_models',
        description="List registered Honeybee, Dragonfly, Fairyfly, and Ironbug model targets in a Garden, including HBJSON, DFJSON, FFJSON, and IBJSON authoring records. Use this to choose an existing model target before edit, export, visualization, energy, Radiance, THERM, or DetailedHVAC workflows. Returns matches plus summary_view with base_honeybee_model, base_dragonfly_model, and base_fairyfly_model when present; Ironbug models have no base slot. Pass a selected model target to downstream model tools.",
        tags={
            "garden",
            "model",
            "search",
            "honeybee",
            "dragonfly",
            "fairyfly",
            "ironbug",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_models(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'] or GD_get['garden_root'].")
        ],
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden-relative HBJSON, DFJSON, FFJSON, or IBJSON model file paths in each match."),
        ] = True,
    ) -> dict[str, Any]:
        """List registered Garden model targets."""
        from garden.store import list_garden_models as service

        return service(garden_root=garden_root, include_paths=include_paths)
