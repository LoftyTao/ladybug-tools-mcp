"""Clean Dragonfly Room2D geometry MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.geometry import clean_dragonfly_room2d_geometry as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_clean_room2d_geometry tool.'

    @mcp.tool(
        name="clean_room2d_geometry",
        description=(
            "Clean a model-embedded Dragonfly Room2D boundary using explicit SDK "
            "methods: remove_duplicate_vertices, remove_colinear_vertices, and "
            "optionally remove_short_segments. Saves the updated DFJSON and returns "
            "summary_view, report, and segment-count diagnostics; adjacency solving "
            "and validation use separate Dragonfly tools."
        ),
        tags={"dragonfly", "room2d", "geometry", "cleanup", "repair"},
        timeout=30,
    )
    def clean_dragonfly_room2d_geometry(
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
                    "Optional model-embedded Room2D identifier. Use this when the "
                    "room target is not available but the room name is known."
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
        remove_duplicate_vertices: Annotated[
            bool,
            Field(description="Whether to call Dragonfly Room2D.remove_duplicate_vertices on the selected Room2D."),
        ] = True,
        remove_colinear_vertices: Annotated[
            bool,
            Field(description="Whether to call Room2D.remove_colinear_vertices."),
        ] = True,
        remove_short_segments_distance: Annotated[
            float | None,
            Field(description="Optional distance for Room2D.remove_short_segments. Leave null to skip."),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Tolerance passed to duplicate/colinear cleanup methods."),
        ] = 0.01,
        preserve_wall_props: Annotated[
            bool,
            Field(description="Whether Room2D.remove_colinear_vertices preserves wall properties."),
        ] = True,
        angle_tolerance: Annotated[
            float,
            Field(description="Angle tolerance passed to Room2D.remove_short_segments."),
        ] = 1.0,
    ) -> dict[str, Any]:
        """Clean Dragonfly Room2D geometry."""
        return service(
            garden_root=garden_root,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
            remove_duplicate_vertices=remove_duplicate_vertices,
            remove_colinear_vertices=remove_colinear_vertices,
            remove_short_segments_distance=remove_short_segments_distance,
            tolerance=tolerance,
            preserve_wall_props=preserve_wall_props,
            angle_tolerance=angle_tolerance,
        )
