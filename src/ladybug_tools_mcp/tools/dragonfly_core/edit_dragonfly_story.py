"""Edit Dragonfly Story MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_story as service


def register(mcp: FastMCP) -> None:
    """Register the edit_dragonfly_story tool."""

    @mcp.tool(
        name="edit_dragonfly_story",
        description="Edit a model-embedded Dragonfly Story using public Dragonfly SDK properties. Requires story_target or story_identifier; supports display_name, floor_height, floor_to_floor_height, and multiplier.",
        tags={"dragonfly-core", "garden-mode", "story", "edit", "write", "safe"},
        timeout=20,
    )
    def edit_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Story target from creation or search."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Story identifier when story_target is not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
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
            Field(description="Optional Story multiplier."),
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
