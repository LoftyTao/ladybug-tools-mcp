"""Inspect a Garden Ironbug HVAC system."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    InspectSystemResult,
    IronbugModelTargetRef,
    dump_target,
)


def register(mcp: FastMCP) -> None:
    """Register IB_inspect_system."""

    @mcp.tool(
        name="IB_inspect_system",
        description=(
            "Inspect a Garden-managed Ironbug IB_HVACSystem summary, loop counts, "
            "and components. Set include_draft=true to also include the editable "
            "component and loop draft JSON."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "inspect"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_inspect_system(
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
        include_draft: Annotated[
            bool,
            Field(description="Include the editable component and loop draft JSON."),
        ] = False,
    ) -> InspectSystemResult:
        """Inspect an Ironbug HVAC system in a Garden."""
        from garden.ironbug.service import inspect_ironbug_system

        return InspectSystemResult.model_validate(
            inspect_ironbug_system(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                include_draft=include_draft,
            )
        )
