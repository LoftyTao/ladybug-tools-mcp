"""Set Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import set_domain_base_model


def register(mcp: FastMCP) -> None:
    """Register the set_base_honeybee_model tool."""

    @mcp.tool(
        name="set_base_honeybee_model",
        description="Register or select an existing Honeybee model target as the Garden base Honeybee model.",
        tags={"garden", "garden-mode", "honeybee", "model", "base-honeybee-model", "write", "safe"},
        timeout=10,
    )
    def set_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(description="Honeybee model target to set as the Garden base Honeybee model."),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Honeybee model."""
        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="honeybee",
        )
