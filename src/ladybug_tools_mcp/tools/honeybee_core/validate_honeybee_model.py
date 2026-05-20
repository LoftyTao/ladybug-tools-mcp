"""Validate Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.validation import (
    validate_honeybee_model as service,
)


def register(mcp: FastMCP) -> None:
    """Register the validate_honeybee_model tool."""

    @mcp.tool(
        name="validate_honeybee_model",
        description="Validate an existing Honeybee model already stored in a Garden base Honeybee model or explicit model target. Use this tool, not get_base_honeybee_model, when a user asks to validate, check model validity, return a validation flag, or inspect validation issues. Returns validation report data with top-level is_valid/valid helpers, report, summary_view.is_valid, and structured validation issues. Requires garden_root; this is read-only and does not repair, relate, or save the model. There is no raise_exception parameter; validation problems are returned in the report.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "validate",
            "validation",
            "is-valid",
            "validation-flag",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model; do not pass full model body."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Honeybee model and return structured issues."""
        return service(garden_root=garden_root, model_target=model_target)
