"""Query Dragonfly Room2Ds by one SDK attribute MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.queries import query_dragonfly_room2ds_by_attribute as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_query_room2ds_by_attribute tool."""

    @mcp.tool(
        name="room2ds_by_attribute",
        description=(
            "Return Dragonfly Room2D targets and compact values for one SDK "
            "attribute, such as floor_area, volume, or floor_height. This is a "
            "read-only summary/query tool and does not return Room2D object bodies."
        ),
        tags={"dragonfly", "geometry", "summary", "query"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def query_dragonfly_room2ds_by_attribute(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        attribute: Annotated[
            str,
            Field(description="Dragonfly Room2D SDK property name, such as floor_area."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
    ) -> dict[str, Any]:
        """Query Dragonfly Room2Ds by one attribute."""
        return service(
            garden_root=garden_root,
            attribute=attribute,
            model_target=model_target,
        )
