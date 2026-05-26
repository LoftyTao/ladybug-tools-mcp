"""Reset Dragonfly Story adjacency MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.geometry import reset_dragonfly_story_adjacency as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_reset_story_adjacency tool.'

    @mcp.tool(
        name="reset_story_adjacency",
        description=(
            "Reset Surface boundary conditions on a Dragonfly Story using "
            "Story.reset_adjacency, save the updated DFJSON, and return compact "
            "adjacency counts plus validation summary. Pass story_target or "
            "story_identifier; this does not change Room2D floor boundaries."
        ),
        tags={"dragonfly", "story", "geometry", "edit", "adjacency"},
        timeout=30,
    )
    def reset_dragonfly_story_adjacency(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Story target or story identifier in the selected Garden model. "
                    "Prefer story_target when available."
                )
            ),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Dragonfly Story identifier when no story_target is available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Reset Dragonfly Story adjacency."""
        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
        )
