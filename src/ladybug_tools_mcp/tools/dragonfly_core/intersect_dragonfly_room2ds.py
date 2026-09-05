"""Intersect Dragonfly Room2D adjacency segments MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, StrictFloat, StrictStr


def register(mcp: FastMCP) -> None:
    """Register the DF_intersect_room2ds tool."""

    @mcp.tool(
        name="DF_intersect_room2ds",
        description=(
            "Intersect adjacent Dragonfly Room2D segments with "
            "Room2D.intersect_adjacency. This operation clears original boundary "
            "conditions, window/glazing parameters, and shading parameters as wall "
            "segments are subdivided; run it before assigning those properties. It "
            "does not restore or automatically preserve them. The tool applies to "
            "all Room2Ds in the selected Story, Building, or Model scope, and saves "
            "at most once only when the model changes. It returns affected "
            "Building, Story, and Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "intersect", "adjacency", "edit"},
        timeout=30,
    )
    def intersect_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        tolerance: Annotated[
            StrictFloat,
            Field(description="Positive tolerance passed to Room2D.intersect_adjacency; defaults to 0.01."),
        ] = 0.01,
        host_type: Annotated[
            StrictStr | None,
            Field(description="Optional scope type: story, building, or model. Defaults to model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Story or Building target restricting the Room2D scope."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Intersect Dragonfly Room2D adjacency segments."""
        from garden.dragonfly_core.geometry import intersect_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
