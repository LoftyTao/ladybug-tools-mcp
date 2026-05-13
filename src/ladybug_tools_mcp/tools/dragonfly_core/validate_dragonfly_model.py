"""Validate Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.validation import validate_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the validate_dragonfly_model tool."""

    @mcp.tool(
        name="validate_dragonfly_model",
        description="Validate an existing Dragonfly model already stored in a Garden base Dragonfly model or explicit model target. Returns is_valid, valid, structured issues, and compact object counts.",
        tags={
            "dragonfly-core",
            "garden-mode",
            "model",
            "validate",
            "validation",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Accepts the typed target or a "
                    "Garden-relative DFJSON path. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional natural alias for model_target."),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Dragonfly model."""
        if model_target is None:
            model_target = target
        return service(garden_root=garden_root, model_target=model_target)
