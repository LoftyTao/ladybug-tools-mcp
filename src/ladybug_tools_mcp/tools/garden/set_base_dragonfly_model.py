"""Set Base Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import set_domain_base_model


def register(mcp: FastMCP) -> None:
    """Register the set_base_dragonfly_model tool."""

    @mcp.tool(
        name="set_base_dragonfly_model",
        description="Register or select an existing Dragonfly model target as the Garden base Dragonfly model.",
        tags={"garden", "garden-mode", "dragonfly", "model", "base-dragonfly-model", "write", "safe"},
        timeout=10,
    )
    def set_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(description="Dragonfly model target to set as the Garden base Dragonfly model."),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Dragonfly model."""
        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="dragonfly",
        )
