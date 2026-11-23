"""Validate Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the HB_validate_model tool.'

    @mcp.tool(
        name="HB_validate_model",
        description=(
            'Validate an existing Honeybee model in a Garden using Honeybee Model.check_all '
            '(read-only). Returns is_valid/valid, issues, summary_view, and report.'
        ),
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
                description="Required Garden root path containing garden.json, usually GD_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target dict, usually HB_create_model['target']; "
                    'defaults to the Garden base Honeybee Model.'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Honeybee model and return structured issues."""
        from garden.honeybee_core.validation import (
            validate_honeybee_model as service,
        )

        return service(garden_root=garden_root, model_target=model_target)
