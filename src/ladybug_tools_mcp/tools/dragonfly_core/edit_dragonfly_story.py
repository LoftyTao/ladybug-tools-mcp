"""Edit Dragonfly Story MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_story as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_edit_story tool.'

    @mcp.tool(
        name="edit_story",
        description=(
            "Edit a model-embedded Dragonfly Story using public Dragonfly SDK "
            "properties. Requires story_target or story_identifier; supports "
            "display_name, floor_height, floor_to_floor_height, and multiplier. "
            "Use solve/reset adjacency tools for Story boundary-condition changes."
        ),
        tags={"dragonfly", "story", "edit", "geometry", "metadata", "multiplier"},
        timeout=20,
    )
    def edit_dragonfly_story(
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
            Field(description="Optional Dragonfly Story identifier when story_target is not available."),
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
        display_name: Annotated[
            str | None,
            Field(description="Optional Story display name."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor height."),
        ] = None,
        floor_to_floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor-to-floor height."),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(description="Optional Dragonfly Story multiplier for repeated floors."),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Story."""
        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
            display_name=display_name,
            floor_height=floor_height,
            floor_to_floor_height=floor_to_floor_height,
            multiplier=multiplier,
        )
