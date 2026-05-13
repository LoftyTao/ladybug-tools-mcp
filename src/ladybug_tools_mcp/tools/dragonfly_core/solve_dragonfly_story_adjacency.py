"""Solve Dragonfly Story adjacency MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.geometry import solve_dragonfly_story_adjacency as service


def register(mcp: FastMCP) -> None:
    """Register the solve_dragonfly_story_adjacency tool."""

    @mcp.tool(
        name="solve_dragonfly_story_adjacency",
        description="Solve Room2D adjacencies on a Dragonfly Story using Story.solve_room_2d_adjacency, save the updated DFJSON, and return compact adjacency counts plus validation summary. Pass story_target from create_dragonfly_story/building workflow or story_identifier.",
        tags={"dragonfly-core", "garden-mode", "story", "adjacency", "geometry", "write", "safe"},
        timeout=30,
    )
    def solve_dragonfly_story_adjacency(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Story target. Preferred over story_identifier."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Story identifier when no story_target is available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Tolerance passed to Story.solve_room_2d_adjacency."),
        ] = 0.01,
        intersect: Annotated[
            bool,
            Field(description="Whether to intersect Room2D adjacency segments before solving."),
        ] = False,
        resolve_window_conflicts: Annotated[
            bool,
            Field(description="Whether SDK should resolve window conflicts on adjacent segments."),
        ] = True,
    ) -> dict[str, Any]:
        """Solve Dragonfly Story adjacency."""
        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
            tolerance=tolerance,
            intersect=intersect,
            resolve_window_conflicts=resolve_window_conflicts,
        )
