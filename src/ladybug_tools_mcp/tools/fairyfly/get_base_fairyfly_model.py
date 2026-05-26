"""Get Base Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_fairyfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the therm_get_base_model tool.'

    @mcp.tool(
        name="get_base_model",
        description=(
            "Read the Garden base Fairyfly model target and minimal context. This is "
            "not a validation tool; use therm_validate_model for validation flags or "
            "issue checks, and use THERM tools only after a model exists."
        ),
        tags={"fairyfly", "therm", "model", "summary", "garden"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Fairyfly model target."""
        return service(garden_root=garden_root)
