"""Get Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_honeybee_model as service


def register(mcp: FastMCP) -> None:
    """Register the get_base_honeybee_model tool."""

    @mcp.tool(
        name="get_base_honeybee_model",
        description="Read the Garden base Honeybee model target and minimal context. This is not a validation tool; use validate_honeybee_model for validation flags or issue checks.",
        tags={"garden", "garden-mode", "honeybee", "model", "base-honeybee-model", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory containing garden.json."),
        ],
        include_body: Annotated[
            bool,
            Field(description="Explicitly request full model body. Defaults to false."),
        ] = False,
    ) -> dict[str, Any]:
        """Return the Garden base Honeybee model target."""
        return service(garden_root=garden_root, include_body=include_body)
