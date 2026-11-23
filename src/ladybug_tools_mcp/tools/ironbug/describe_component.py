"""Describe official Ironbug HVAC component schemas via C# reflection and EPDoc."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import DescribeComponentsResult


def register(mcp: FastMCP) -> None:
    """Register IB_describe_component."""

    @mcp.tool(
        name="IB_describe_component",
        description=(
            "Inspect official C# Ironbug IB_* component classes, returning constructor "
            "signatures, child wiring slots, and EnergyPlus FieldSet metadata with units, "
            "defaults, and choices. Set include_advanced=true for curve and advanced fields."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "inspect"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_describe_component(
        type_names: Annotated[
            list[str] | str,
            Field(
                description=(
                    "One IB_* type name, comma-separated string, or list, "
                    "e.g. ['IB_ChillerElectricEIR']."
                )
            ),
        ],
        include_advanced: Annotated[
            bool,
            Field(description="Include all advanced *_FieldSet fields beyond the core fields."),
        ] = False,
    ) -> DescribeComponentsResult:
        """Describe official Ironbug component schemas."""
        from garden.ironbug.service import describe_ironbug_components

        return DescribeComponentsResult.model_validate(
            describe_ironbug_components(
                type_names=type_names,
                include_advanced=include_advanced,
            )
        )
