"""Create Dragonfly Story MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_story as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_create_story tool.'

    @mcp.tool(
        name="create_story",
        description=(
            "Create a Dragonfly Story draft object from Dragonfly Room2D targets. "
            "The parameter name is exactly room2d_targets, not room2ds and not room_2ds. "
            "Pass identifier or a natural display_name; the returned Story target "
            "can be passed to dragonfly_create_building. This does not attach the "
            "Story to a Building until that Building tool is called."
        ),
        tags={"dragonfly", "story", "room2d", "author", "assembly"},
        timeout=20,
    )
    def create_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        room2d_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Required list of Dragonfly Room2D targets. The parameter name "
                    "is exactly room2d_targets, not room2ds and not room_2ds. Use "
                    'room2d_target values returned by dragonfly_create_room2d or '
                    "target values from a Room2D search."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly Story identifier. If omitted, display_name "
                    "is converted to a stable identifier."
                )
            ),
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
        floor_to_floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor-to-floor height."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor height."),
        ] = None,
        multiplier: Annotated[
            int,
            Field(description="Dragonfly Story multiplier for repeated floors."),
        ] = 1,
        story_type: Annotated[
            str,
            Field(
                description=(
                    "Dragonfly Story type. Use Standard for ordinary ground, "
                    "middle, top, or typical floors. Only use CeilingPlenum or "
                    "FloorPlenum for plenum stories."
                )
            ),
        ] = "Standard",
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional user-facing Story name. If identifier is omitted, "
                    "spaces are converted to underscores for the identifier."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Story."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            room2d_targets=room2d_targets,
            model_target=model_target,
            floor_to_floor_height=floor_to_floor_height,
            floor_height=floor_height,
            multiplier=multiplier,
            story_type=story_type,
            display_name=display_name,
        )
