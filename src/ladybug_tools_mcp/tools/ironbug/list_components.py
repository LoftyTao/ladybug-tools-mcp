"""List or search official Ironbug HVAC component types."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    IronbugCategory,
    ListComponentsResult,
)


def register(mcp: FastMCP) -> None:
    """Register IB_list_components."""

    @mcp.tool(
        name="IB_list_components",
        description=(
            "Search or browse official C# Ironbug.HVAC component classes by category or "
            "keyword, including English and common Chinese HVAC terms. Use discovered "
            "IB_* type names with IB_describe_component."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "search"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_list_components(
        category: Annotated[
            IronbugCategory | None,
            Field(description="Optional Ironbug component category filter."),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Optional keyword or IB_* type name query, e.g. 'chiller', "
                    "'vav', or '冷机'."
                )
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(ge=1, le=100, description="Maximum number of matching component types per page (1-100)."),
        ] = 25,
        offset: Annotated[
            int,
            Field(ge=0, description="Zero-based pagination offset into matched component types (default: 0)."),
        ] = 0,
    ) -> ListComponentsResult:
        """List official Ironbug component classes."""
        from garden.ironbug.service import list_ironbug_components

        return ListComponentsResult.model_validate(
            list_ironbug_components(
                category=category,
                query=query,
                limit=limit,
                offset=offset,
            )
        )
