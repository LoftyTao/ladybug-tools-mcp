"""Align Dragonfly Room2Ds MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, StrictFloat, StrictStr


def register(mcp: FastMCP) -> None:
    """Register the DF_align_room2ds tool."""

    @mcp.tool(
        name="DF_align_room2ds",
        description=(
            "Align Room2D vertices in a Dragonfly Story, Building, or Model to a "
            "list of straight 2D line segments using Story.align. The operation "
            "also removes duplicate/degenerate Room2Ds using Dragonfly SDK methods, "
            "saves at most once only when the model changes, and returns affected "
            "Building, Story, and Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "align", "edit"},
        timeout=30,
    )
    def align_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        lines: Annotated[
            list[list[list[StrictFloat]]],
            Field(
                description=(
                    "Required straight 2D line segments as "
                    "[[[x1, y1], [x2, y2]], ...]."
                )
            ),
        ],
        distance: Annotated[
            StrictFloat,
            Field(description="Maximum distance from a line for a vertex to be aligned; defaults to 0.5."),
        ] = 0.5,
        tolerance: Annotated[
            StrictFloat,
            Field(description="Positive Dragonfly geometry tolerance; defaults to 0.01."),
        ] = 0.01,
        host_type: Annotated[
            StrictStr | None,
            Field(description="Optional scope type: story, building, or model. Defaults to model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Story or Building target when host_type is story or building."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Align Dragonfly Room2Ds."""
        from garden.dragonfly_core.geometry import align_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            lines=lines,
            distance=distance,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
