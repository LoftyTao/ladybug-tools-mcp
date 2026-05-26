"""Get Base Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the garden_get_base_dragonfly_model tool.'

    @mcp.tool(
        name='get_base_dragonfly_model',
        description=(
            "Read the current Garden base Dragonfly model slot and return its "
            "target handoff with minimal summary_view context. Use this when a "
            "later Dragonfly, UWG, visualization, Honeybee conversion, or export "
            "tool needs the active Dragonfly model target. This is not a model-list, "
            "full DFJSON read, or validation tool; use garden_list_models for all "
            "model targets and dragonfly_validate_model for issue checks."
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
                    "garden_create['garden_root']; read the Dragonfly base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Dragonfly model target."""
        return service(garden_root=garden_root)
