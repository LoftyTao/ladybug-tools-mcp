"""Validate Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.validation import validate_fairyfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the therm_validate_model tool.'

    @mcp.tool(
        name="validate_model",
        description=(
            "Validate a Garden-backed Fairyfly Model with Fairyfly SDK checks. Returns "
            "validation_status through summary_view/report, compact issues, object "
            "counts, and report. This reports model issues and does not repair geometry "
            "or run THERM."
        ),
        tags={"fairyfly", "therm", "model", "validate", "check"},
        timeout=20,
    )
    def validate_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually therm_create_model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Fairyfly model."""
        return service(garden_root=garden_root, model_target=model_target)
