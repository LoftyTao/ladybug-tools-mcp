"""List supported Dragonfly Room2D attribute query fields MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.queries import list_dragonfly_room2d_attributes as service


def register(mcp: FastMCP) -> None:
    """Register the df_room2d_attributes tool."""

    @mcp.tool(
        name="room2d_attributes",
        description=(
            "List compact Dragonfly Room2D attributes supported by "
            "df_room2ds_by_attribute, including value type hints and supported "
            "operators. Use this before attribute grouping when the attribute "
            "name is uncertain. Returns attributes, summary_view, and report."
        ),
        tags={"dragonfly", "room2d", "attribute", "query", "list"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_df_room2d_attributes(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target; defaults to the Garden "
                    "base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List compact Room2D attributes supported by attribute grouping."""
        return service(garden_root=garden_root, model_target=model_target)
