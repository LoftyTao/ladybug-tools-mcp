"""Validate an Ironbug HVAC system by compiling it in-memory against OpenStudio."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    BuildingModelTargetRef,
    IronbugModelTargetRef,
    ValidateSystemResult,
    dump_target,
)


def register(mcp: FastMCP) -> None:
    """Register IB_validate_system."""

    @mcp.tool(
        name="IB_validate_system",
        description=(
            "Compile and validate an Ironbug IB_HVACSystem in-memory via official C# "
            "SaveHVAC against OpenStudio, checking Honeybee Room or Dragonfly Room2D "
            "preconditions when a model target is provided. Run this before IB_apply_to_model."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "validate"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=60,
    )
    def ib_validate_system(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_create_system. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee or Dragonfly model target to check room preconditions against."),
        ] = None,
        model_family: Annotated[
            Literal["honeybee", "dragonfly"],
            Field(description="Model family for room precondition checks (default: 'honeybee')."),
        ] = "honeybee",
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional explicit room identifiers to verify against the system's thermal zones."),
        ] = None,
    ) -> ValidateSystemResult:
        """Validate an Ironbug system against OpenStudio and model rooms."""
        from garden.ironbug.service import validate_ironbug_system

        return ValidateSystemResult.model_validate(
            validate_ironbug_system(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                model_target=dump_target(model_target),
                model_family=model_family,
                room_identifiers=room_identifiers,
            )
        )
