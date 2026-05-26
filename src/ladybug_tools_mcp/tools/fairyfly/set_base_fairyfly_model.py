"""Set Base Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import set_domain_base_model


def register(mcp: FastMCP) -> None:
    'Register the therm_set_base_model tool.'

    @mcp.tool(
        name="set_base_model",
        description=(
            "Register or select an existing Fairyfly model target as the Garden base "
            "Fairyfly model. Returns target, summary_view, and report for downstream "
            "Fairyfly tools; this does not validate, export, or simulate the model."
        ),
        tags={"fairyfly", "therm", "model", "garden", "base-model"},
        timeout=10,
    )
    def set_base_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(description="Fairyfly model target with target_type=fairyfly_model to set as the Garden base Fairyfly model."),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Fairyfly model."""
        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="fairyfly",
        )
