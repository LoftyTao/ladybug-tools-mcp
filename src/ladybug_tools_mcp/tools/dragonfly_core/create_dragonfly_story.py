"""Create Dragonfly Story MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the DF_story tool.'

    @mcp.tool(
        name="DF_story",
        description=(
            'Create a Dragonfly Story draft object from Dragonfly Room2D targets. Pass identifier '
            'or display_name; attach the returned Story target to a Building with DF_building.'
        ),
        tags={"dragonfly", "story", "room2d", "author", "assembly"},
        timeout=20,
    )
    def create_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        room2d_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Required list of Dragonfly Room2D targets from DF_room2d or DF_search_objects.'
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
                    "Optional Dragonfly Model target dict, usually DF_model['target']; "
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
                    "Dragonfly Story type; values are case-sensitive. Use Standard for ordinary ground, "
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
        from garden.dragonfly_core.creation import create_dragonfly_story as service

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
