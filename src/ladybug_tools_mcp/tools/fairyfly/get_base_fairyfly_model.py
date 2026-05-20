"""Get Base Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_fairyfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the get_base_fairyfly_model tool."""

    @mcp.tool(
        name="get_base_fairyfly_model",
        description="Read the Garden base Fairyfly model target and minimal context. This is not a validation tool; use validate_fairyfly_model for validation flags or issue checks.",
        tags={"fairyfly", "therm", "garden-mode", "model", "base-fairyfly-model", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory containing garden.json."),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Fairyfly model target."""
        return service(garden_root=garden_root)
