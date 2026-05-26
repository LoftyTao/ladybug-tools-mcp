"""Validate Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.validation import validate_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_validate_model tool.'

    @mcp.tool(
        name="validate_model",
        description=(
            "Validate an existing Dragonfly model already stored in a Garden base "
            "Dragonfly model or explicit model target. Returns validation_status "
            "through is_valid/valid, summary_view, report, structured issues, and "
            "compact object counts. This reports issues only; cleanup and adjacency "
            "tools perform model edits."
        ),
        tags={"dragonfly", "model", "validate", "summary", "check"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Dragonfly model."""
        return service(garden_root=garden_root, model_target=model_target)
