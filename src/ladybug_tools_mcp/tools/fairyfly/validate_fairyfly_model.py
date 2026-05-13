"""Validate Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.validation import validate_fairyfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the validate_fairyfly_model tool."""

    @mcp.tool(
        name="validate_fairyfly_model",
        description="Validate a Garden-backed Fairyfly Model with Fairyfly SDK checks and return compact issues and object counts.",
        tags={"fairyfly", "therm", "validate", "model", "safe", "garden-mode"},
        timeout=20,
    )
    def validate_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Fairyfly model target. Defaults to base Fairyfly model."),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Fairyfly model."""
        return service(garden_root=garden_root, model_target=model_target)
