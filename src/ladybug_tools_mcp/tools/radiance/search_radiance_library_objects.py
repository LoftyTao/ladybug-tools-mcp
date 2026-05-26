"""Search Honeybee Radiance standards library objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.radiance.libraries import (
    search_radiance_library_objects as service,
)


def register(mcp: FastMCP) -> None:
    'Register the radiance_search_library_objects tool.'

    @mcp.tool(
        name="search_library_objects",
        description=(
            "Search Honeybee Radiance standards library identifiers for "
            "modifiers, materials, and modifier sets. Use returned identifiers "
            "in Radiance authoring tools or Honeybee Radiance properties. This "
            "searches built-in Radiance libraries and does not search Garden "
            "files, Energy materials, or Radiance result artifacts. Returns "
            "matches, summary_view, and report."
        ),
        tags={
            "search",
            "radiance",
            "modifier",
            "material",
            "author",
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
                description="Optional library family filter: modifier, modifier_set, material, or all."
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
