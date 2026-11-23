"""Get Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_get_base_honeybee_model tool.'

    @mcp.tool(
        name='GD_get_base_honeybee_model',
        description=(
            'Read the current Garden base Honeybee model slot and return its target handoff with '
            'minimal summary_view context. Use this when a later Honeybee, Energy, Radiance, '
            'visualization, or export tool needs the active Honeybee model target. Use '
            'GD_list_models to list all models and HB_validate_model to validate.'
        ),
        tags={
            "base-model",
            "garden",
            "honeybee",
            "model",
            "summary",
            "target",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_create['garden_root']; read the Honeybee base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Honeybee model target."""
        from garden.store import get_base_honeybee_model as service

        return service(garden_root=garden_root)
