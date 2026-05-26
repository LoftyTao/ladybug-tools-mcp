"""Validate Ironbug model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import validate_ironbug_model as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_validate_model tool.'

    @mcp.tool(
        name="validate_model",
        description=(
            "Validate a Garden-managed Ironbug .ibjson model by ironbug_model target "
            "or Garden-relative path. Returns validation_status through "
            "is_valid/valid, summary_view, issues, and report. This replaces "
            "a full-body read workflow: do not "
            "invent read_ironbug_model and do not expect a full ibjson body."
        ),
        tags={"ironbug", "detailed-hvac", "model", "validate"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def validate_ironbug_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Ironbug target argument named ironbug_model_target; "
                    'pass the target returned by detailed_hvac_create_model, not ironbug_model.'
                )
            ),
        ] = None,
        path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .ibjson path when target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """Validate an Ironbug model and return compact issues."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            path=path,
        )
