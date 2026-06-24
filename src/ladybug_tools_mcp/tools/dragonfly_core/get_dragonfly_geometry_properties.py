"""Get compact Dragonfly geometry properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.queries import get_dragonfly_geometry_properties as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_get_geometry_properties tool."""

    @mcp.tool(
        name="geometry_properties",
        description=(
            "Return compact Dragonfly geometry property records for Buildings, "
            "Stories, Room2Ds, and ContextShades in the Garden base Dragonfly "
            "model or an explicit Dragonfly model/object target. This is a "
            "summary/query tool and does not return DFJSON object bodies."
        ),
        tags={"dragonfly", "geometry", "summary", "query"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_dragonfly_geometry_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly object target to summarize instead of the whole model."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        attributes: Annotated[
            list[str] | None,
            Field(
                description="Optional SDK property names to include, such as floor_area or volume."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get compact Dragonfly geometry properties."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            attributes=attributes,
        )
