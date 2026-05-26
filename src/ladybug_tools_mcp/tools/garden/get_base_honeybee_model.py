"""Get Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_honeybee_model as service


def register(mcp: FastMCP) -> None:
    'Register the garden_get_base_honeybee_model tool.'

    @mcp.tool(
        name='get_base_honeybee_model',
        description=(
            "Read the current Garden base Honeybee model slot and return its "
            "target handoff with minimal summary_view context. Use this when a "
            "later Honeybee, Energy, Radiance, visualization, or export tool needs "
            "the active Honeybee model target. This is not a model-list, full "
            "HBJSON read, or validation tool; use garden_list_models for all model "
            "targets and honeybee_validate_model for issue checks."
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
                    "garden_create['garden_root']; read the Honeybee base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Honeybee model target."""
        return service(garden_root=garden_root)
