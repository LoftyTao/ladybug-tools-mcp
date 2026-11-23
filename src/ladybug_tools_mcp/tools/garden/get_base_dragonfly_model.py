"""Get Base Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_get_base_dragonfly_model tool.'

    @mcp.tool(
        name='GD_get_base_dragonfly_model',
        description=(
            'Read the current Garden base Dragonfly model slot and return its target handoff with '
            'minimal summary_view context. Use this when a later Dragonfly, UWG, visualization, '
            'Honeybee conversion, or export tool needs the active Dragonfly model target. Use '
            'GD_list_models to list all models and DF_validate_model to validate.'
        ),
        tags={
            "base-model",
            "dragonfly",
            "garden",
            "model",
            "summary",
            "target",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_create['garden_root']; read the Dragonfly base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Dragonfly model target."""
        from garden.store import get_base_dragonfly_model as service

        return service(garden_root=garden_root)
