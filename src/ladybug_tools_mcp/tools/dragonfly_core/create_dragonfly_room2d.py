"""Create Dragonfly Room2D MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_room2d as service


def register(mcp: FastMCP) -> None:
    """Register the create_dragonfly_room2d tool."""

    @mcp.tool(
        name="create_dragonfly_room2d",
        description="Create a Dragonfly Room2D draft object in a Garden from 2D vertices. The Room2D is saved as a Dragonfly object target and can be used by create_dragonfly_story. Call create_dragonfly_model first or pass a Dragonfly model_target.",
        tags={"dragonfly-core", "garden-mode", "room2d", "create", "write", "safe"},
        timeout=20,
    )
    def create_dragonfly_room2d(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(description="Required Dragonfly Room2D identifier."),
        ],
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional human-readable Room2D display name. Use identifier "
                    "for the stable object id."
                )
            ),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(
                description=(
                    "Floor elevation for the Room2D. If omitted, the service "
                    "infers it from story_number."
                )
            ),
        ] = None,
        vertices: Annotated[
            Any,
            Field(
                description=(
                    "2D floor boundary vertices as [[x, y], ...] in order. "
                    "3D points are accepted and normalized to their [x, y] "
                    "coordinates. For a simple rectangle, omit vertices and "
                    "pass x_dim and y_dim."
                )
            ),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(
                description=(
                    "Room2D floor-to-ceiling height. For rectangular input, "
                    "height is also accepted as a short natural-language field. "
                    "Defaults to 3.0 when omitted."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        is_ground_contact: Annotated[
            bool,
            Field(description="Whether the Room2D floor is ground-contact."),
        ] = False,
        is_top_exposed: Annotated[
            bool,
            Field(description="Whether the Room2D ceiling is top-exposed."),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangle width in the x direction."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangle depth in the y direction."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Optional rectangle origin [x, y]. Defaults to [0, 0]."),
        ] = None,
        height: Annotated[
            float | None,
            Field(
                description="Optional short field for floor-to-ceiling height in rectangular mode."
            ),
        ] = None,
        story_number: Annotated[
            int | None,
            Field(
                description=(
                    "Optional story number. The geometry service "
                    "does not need it when floor_height is provided."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional low-cost output control. Set false to omit the full "
                    "Room2D object_dict while keeping targets, summary, receipt, "
                    "and report."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Room2D."""
        result = service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            vertices=vertices,
            floor_height=floor_height,
            floor_to_ceiling_height=floor_to_ceiling_height,
            model_target=model_target,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            x_dim=x_dim,
            y_dim=y_dim,
            origin=origin,
            height=height,
            story_number=story_number,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        return result
