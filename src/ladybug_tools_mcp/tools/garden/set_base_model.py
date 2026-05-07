"""Set Base Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import set_base_model as service


def register(mcp: FastMCP) -> None:
    """Register the set_base_model tool."""

    @mcp.tool(
        name="set_base_model",
        description="Register or select an existing Honeybee/Dragonfly model target as the Garden base model for later HBJSON authoring, search, edit, visualize, validate, and simulation workflows.",
        tags={
            "garden",
            "garden-mode",
            "model",
            "base-model",
            "register",
            "hbjson",
            "authoring",
            "write",
            "safe",
        },
        timeout=10,
    )
    def set_base_model(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(description="Model target to set as the Garden base model."),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base model."""
        return service(garden_root=garden_root, model_target=model_target)
