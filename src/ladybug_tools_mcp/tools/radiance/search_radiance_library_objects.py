"""Search Honeybee Radiance standards library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.radiance.libraries import (
    search_radiance_library_objects as service,
)


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_library_objects tool."""

    @mcp.tool(
        name="search_radiance_library_objects",
        description='Search Honeybee Radiance standards library identifiers for radiance modifiers, radiance materials, modifier sets, plastic, glass, metal, and trans materials. Required call shape: {"query":"generic wall","object_family":"modifier","limit":3}. Use returned identifiers directly in edit_honeybee_aperture/door/shade modifier fields. Do not pass arguments null or {}.',
        tags={
            "honeybee-radiance",
            "radiance",
            "library",
            "standards",
            "search",
            "radiance-modifiers",
            "radiance-materials",
            "modifier",
            "modifier-set",
            "plastic",
            "glass",
            "metal",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_library_objects(
        query: Annotated[
            str,
            Field(
                description="Required non-empty search text, such as 'generic wall' or 'modifier set'. Do not omit."
            ),
        ],
        object_family: Annotated[
            str | None,
            Field(
                description="Optional family filter: modifier, modifier_set, or all."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Radiance standards library identifiers."""
        return service(
            query=query,
            object_family=object_family,
            limit=limit,
        )
