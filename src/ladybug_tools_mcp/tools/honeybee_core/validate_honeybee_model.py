"""Validate Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.validation import (
    validate_honeybee_model as service,
)


def register(mcp: FastMCP) -> None:
    'Register the honeybee_validate_model tool.'

    @mcp.tool(
        name="validate_model",
        description='Validate an existing Honeybee model already stored in a Garden base Honeybee model or explicit model target using Honeybee Model.check_all with detailed issues. Use this tool, not garden_get_base_honeybee_model or an EnergyPlus simulation run, when a user asks to validate, check model validity, or list issues. Returns validation_status through is_valid/valid, issues, summary_view, and report. Requires garden_root; this is read-only and does not repair, relate, save the model, or accept a raise_exception parameter.',
        tags={
            "check",
            "honeybee",
            "issues",
            "model",
            "summary",
            "validate",
            "validation-report",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model; do not pass full model body."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Honeybee model and return structured issues."""
        return service(garden_root=garden_root, model_target=model_target)
