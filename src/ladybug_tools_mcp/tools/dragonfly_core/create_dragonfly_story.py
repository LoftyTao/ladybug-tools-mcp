"""Create Dragonfly Story MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_story as service


def register(mcp: FastMCP) -> None:
    """Register the create_dragonfly_story tool."""

    @mcp.tool(
        name="create_dragonfly_story",
        description=(
            "Create a Dragonfly Story draft object from Dragonfly Room2D targets. "
            "Pass identifier or a natural display_name; the returned Story target "
            "can be passed to create_dragonfly_building."
        ),
        tags={"dragonfly-core", "garden-mode", "story", "create", "write", "safe"},
        timeout=20,
    )
    def create_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        room2d_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Required list of Dragonfly Room2D targets. Use room2d_target "
                    "values returned by create_dragonfly_room2d or target values "
                    "from a Room2D search."
                )
            ),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional natural alias for room2d_targets."),
        ] = None,
        rooms: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional natural alias for room2d_targets."),
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
        story_identifier: Annotated[
            str | None,
            Field(description="Optional natural alias for identifier."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Accepts the typed target or a "
                    "Garden-relative DFJSON path. Defaults to base Dragonfly model."
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
        floor_z: Annotated[
            float | None,
            Field(description="Optional natural alias for Story floor_height."),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural floor height hint. Used as floor_to_floor_height "
                    "when floor_to_floor_height is omitted."
                )
            ),
        ] = None,
        height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural height alias for floor_to_floor_height."
                )
            ),
        ] = None,
        multiplier: Annotated[
            int,
            Field(description="Story multiplier."),
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
        story_number: Annotated[
            int | None,
            Field(
                description=(
                    "Optional natural story number hint. Used to infer floor_height "
                    "when floor_height is omitted."
                )
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Building target for natural temporary-floor workflows. "
                    "When room2d_targets are omitted, the service copies the host "
                    "Building top-floor layout into a draft Story."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Story."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            story_identifier=story_identifier,
            room2d_targets=room2d_targets,
            room_targets=room_targets,
            rooms=rooms,
            model_target=model_target,
            floor_to_floor_height=floor_to_floor_height,
            floor_height=floor_height,
            floor_z=floor_z,
            floor_to_ceiling_height=floor_to_ceiling_height,
            height=height,
            multiplier=multiplier,
            story_type=story_type,
            display_name=display_name,
            story_number=story_number,
            host_target=host_target,
        )
