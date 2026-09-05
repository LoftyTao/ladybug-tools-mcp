"""Join small Dragonfly Room2Ds MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, StrictBool, StrictFloat, StrictStr


def register(mcp: FastMCP) -> None:
    """Register the DF_join_small_room2ds tool."""

    @mcp.tool(
        name="DF_join_small_room2ds",
        description=(
            "Join small Room2Ds in a Dragonfly Story, Building, or Model using "
            "Story.join_small_room_2ds, then reset and solve Story adjacencies. "
            "The operation saves at most once only when the model changes and returns affected Building, Story, and "
            "Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "join", "merge", "edit"},
        timeout=30,
    )
    def join_small_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        area_threshold: Annotated[
            StrictFloat,
            Field(description="Positive Room2D floor-area threshold below which rooms are joined; defaults to 10.0."),
        ] = 10.0,
        join_into_large: Annotated[
            StrictBool,
            Field(description="Whether small rooms should be merged into neighboring large rooms; defaults to false."),
        ] = False,
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
        """Join small Dragonfly Room2Ds."""
        from garden.dragonfly_core.geometry import join_small_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            area_threshold=area_threshold,
            join_into_large=join_into_large,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
