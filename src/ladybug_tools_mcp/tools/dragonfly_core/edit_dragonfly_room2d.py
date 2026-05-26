"""Edit Dragonfly Room2D MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import edit_dragonfly_room2d as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_edit_room2d tool.'

    @mcp.tool(
        name="edit_room2d",
        description=(
            "Edit a model-embedded Dragonfly Room2D using public Dragonfly SDK methods. "
            "Prefer room2d_target with a Dragonfly Room2D target and garden_root; "
            "room_identifier is accepted when a target is not available. For floor "
            "boundary edits pass vertices. Use the adjacency and cleanup tools for "
            "those separate geometry operations."
        ),
        tags={"dragonfly", "room2d", "geometry", "edit", "metadata", "floor-plate"},
        timeout=20,
    )
    def edit_dragonfly_room2d(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        room2d_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Room2D target or identifier in the selected Story. "
                    "Prefer room2d_target when available."
                )
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural Room2D identifier. Use when a target is not "
                    "available; model_target or the base Dragonfly model is used."
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
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="Optional replacement Dragonfly Room2D floor boundary vertices as [[x, y], ...]."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional floor height used with replacement vertices."),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(description="Optional Room2D floor-to-ceiling height."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Room2D display name."),
        ] = None,
        zone: Annotated[
            str | None,
            Field(description="Optional Room2D zone name."),
        ] = None,
        is_ground_contact: Annotated[
            bool | None,
            Field(description="Optional ground-contact flag."),
        ] = None,
        is_top_exposed: Annotated[
            bool | None,
            Field(description="Optional top-exposed flag."),
        ] = None,
        projection_distance: Annotated[
            float,
            Field(description="Projection distance passed to Room2D.replace_floor_geometry."),
        ] = 0,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Room2D."""
        if room2d_target is None and room_identifier is None:
            raise ValueError('dragonfly_edit_room2d requires room2d_target or room_identifier.')
        return service(
            garden_root=garden_root,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
            vertices=vertices,
            floor_height=floor_height,
            floor_to_ceiling_height=floor_to_ceiling_height,
            display_name=display_name,
            zone=zone,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            projection_distance=projection_distance,
        )
