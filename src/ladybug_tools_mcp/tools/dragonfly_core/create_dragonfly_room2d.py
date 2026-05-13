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
                    "infers it from story_number or the trailing number in story/story_identifier."
                )
            ),
        ] = None,
        floor_z: Annotated[
            float | None,
            Field(description="Optional natural alias for floor_height/elevation."),
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
        room_vertices: Annotated[
            Any,
            Field(
                description=(
                    "Optional explicit Room2D floor boundary vertices. This is "
                    "accepted for natural prompts that say room vertices; vertices "
                    "remains the canonical field."
                )
            ),
        ] = None,
        floor_verts: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural alias for Room2D floor boundary vertices. "
                    "Equivalent to vertices."
                )
            ),
        ] = None,
        floor_boundary: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural field for Room2D floor boundary vertices "
                    "as [[x, y], ...]. Equivalent to vertices."
                )
            ),
        ] = None,
        segments: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural segment boundary as dictionaries with p1/p2 "
                    "or start/end points. The service uses each segment p1 as "
                    "ordered Room2D vertices and applies origin when provided."
                )
            ),
        ] = None,
        floor_geometry: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural field for the Room2D floor boundary as "
                    "[[x, y], ...] or a compact Rectangle2D dict with origin, "
                    "width, and height/depth. It is normalized to vertices."
                )
            ),
        ] = None,
        geometry: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural alias for floor_geometry. Polygon-style "
                    "coordinates/vertices are normalized to Room2D vertices."
                )
            ),
        ] = None,
        room_geometry: Annotated[
            Any,
            Field(description="Optional natural alias for geometry/floor_geometry."),
        ] = None,
        room_polygon: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural polygon dict for the Room2D boundary. "
                    "Coordinates/vertices are normalized to vertices."
                )
            ),
        ] = None,
        plane: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural plane hint accepted for polygon-style calls. "
                    "Dragonfly Room2D creation uses the 2D boundary coordinates."
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
        floor_to_floor_height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural floor-to-floor height hint. Used as the "
                    "Room2D height when floor_to_ceiling_height and height are omitted."
                )
            ),
        ] = None,
        story_height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural height alias often used when describing a story. "
                    "Used as Room2D height when floor_to_ceiling_height, height, "
                    "and floor_to_floor_height are omitted."
                )
            ),
        ] = None,
        room_height: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural alias for Room2D floor-to-ceiling height. "
                    "Used when floor_to_ceiling_height, height, floor_to_floor_height, "
                    "and story_height are omitted."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Accepts the typed target or a "
                    "Garden-relative DFJSON path such as models/dragonfly/model.dfjson. "
                    "Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional natural alias for model_target when the host is a "
                    "Dragonfly model target."
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
                    "Optional natural story number hint. The geometry service "
                    "does not need it when floor_height is provided."
                )
            ),
        ] = None,
        floor_num: Annotated[
            int | None,
            Field(description="Optional natural alias for story_number."),
        ] = None,
        story_count: Annotated[
            int | None,
            Field(
                description=(
                    "Optional natural story count hint accepted for low-cost "
                    "agent calls. Used as story_number only when story_number "
                    "and floor_num are omitted."
                )
            ),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural Story identifier hint. Use create_dragonfly_story "
                    "with the returned Room2D target to actually place this room in a Story."
                )
            ),
        ] = None,
        story: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural story name or identifier hint. Equivalent "
                    "to story_identifier for height inference only."
                )
            ),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(
                description=(
                    "Optional natural multiplier hint accepted for Room2D calls. "
                    "Story multiplier is set on create_dragonfly_story."
                )
            ),
        ] = None,
        floor_area: Annotated[
            float | None,
            Field(
                description=(
                    "Optional natural Room2D floor area. When no vertices or "
                    "dimensions are provided, the service creates a square room "
                    "with this area."
                )
            ),
        ] = None,
        segment_count: Annotated[
            int | None,
            Field(
                description=(
                    "Optional natural segment count hint. Boundary geometry is "
                    "still read from vertices, segments, or dimensions."
                )
            ),
        ] = None,
        room_type: Annotated[
            str | None,
            Field(description="Optional natural room type hint saved as user_data."),
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
        if model_target is None:
            model_target = host_target
        result = service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            floor_z=floor_z,
            vertices=vertices,
            room_vertices=room_vertices,
            floor_verts=floor_verts,
            floor_boundary=floor_boundary,
            segments=segments,
            floor_geometry=floor_geometry,
            geometry=geometry,
            room_geometry=room_geometry,
            room_polygon=room_polygon,
            plane=plane,
            floor_height=floor_height,
            floor_to_ceiling_height=floor_to_ceiling_height,
            floor_to_floor_height=floor_to_floor_height,
            story_height=story_height,
            room_height=room_height,
            model_target=model_target,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            x_dim=x_dim,
            y_dim=y_dim,
            origin=origin,
            height=height,
            story_number=story_number,
            floor_num=floor_num,
            story_count=story_count,
            story_identifier=story_identifier,
            story=story,
            multiplier=multiplier,
            floor_area=floor_area,
            segment_count=segment_count,
            room_type=room_type,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        return result
