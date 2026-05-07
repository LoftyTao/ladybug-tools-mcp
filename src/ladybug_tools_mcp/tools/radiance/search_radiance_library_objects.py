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
        description='Search Honeybee Radiance standards library identifiers for radiance modifiers, radiance materials, modifier sets, plastic, glass, metal, and trans materials. Required call shape: {"name":"search_radiance_library_objects","arguments":{"query":"generic wall","object_family":"modifier","limit":3}}. object_type is accepted as an Agent-friendly synonym for object_family. garden_root is accepted only as an ignored Agent context hint. Use returned identifiers directly in edit_honeybee_aperture/door/shade modifier fields. Do not pass arguments null or {}.',
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
        object_type: Annotated[
            str | None,
            Field(
                description="Optional Agent-friendly object type filter with the same values as object_family. If both are provided, object_family wins."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional ignored Agent context hint. This standards-library search does not read the Garden."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search Honeybee Radiance standards library identifiers."""
        return service(
            query=query,
            object_family=object_family,
            object_type=object_type,
            limit=limit,
            garden_root=garden_root,
        )
