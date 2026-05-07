"""Get Garden Properties Library object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.libraries.properties import (
    get_garden_properties_library_object as service,
)


def register(mcp: FastMCP) -> None:
    """Register the get_garden_properties_library_object tool."""

    @mcp.tool(
        name="get_garden_properties_library_object",
        description="Read one reusable object from the Garden Properties Library by target or by domain, family, and identifier. Returns the saved SDK object dict.",
        tags={
            "garden",
            "properties",
            "library",
            "get",
            "read-only",
            "energy",
            "radiance",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_garden_properties_library_object(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden Properties Library object target."),
        ] = None,
        domain: Annotated[
            str | None, Field(description="Optional domain when target is omitted.")
        ] = None,
        object_family: Annotated[
            str | None,
            Field(description="Optional object family when target is omitted."),
        ] = None,
        identifier: Annotated[
            str | None, Field(description="Optional identifier when target is omitted.")
        ] = None,
    ) -> dict[str, Any]:
        """Read one Garden Properties Library object."""
        return service(
            garden_root=garden_root,
            target=target,
            domain=domain,
            object_family=object_family,
            identifier=identifier,
        )
