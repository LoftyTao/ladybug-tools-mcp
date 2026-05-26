"""Honeybee Room To Visualization Set MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.honeybee import (
    honeybee_room_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    'Register the visualization_honeybee_room_to_visualization_set tool.'

    @mcp.tool(
        name='honeybee_room_to_visualization_set',
        description=(
            "Visualize one Honeybee Room target as a Ladybug Display "
            "VisualizationSet. color_by accepts type, boundary_condition, or "
            "none; use type for simple room previews. Use this read-only "
            "preview after object search finds the room target. For "
            "HTML/SVG/vtk.js export paths, set return_visualization_set=false "
            "so the tool saves a compact visualization_set_target for "
            "exporters. This previews existing room geometry; it does not edit "
            "the model or run analysis."
        ),
        tags={
            "honeybee",
            "preview",
            "room",
            "visualize",
            "visualization-set",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def honeybee_room_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        target: Annotated[
            dict[str, Any], Field(description="Honeybee Room typed target from object search or edit output; do not pass a full model dictionary.")
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the target model or Garden base model."
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Room color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include a room wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only room wireframe visualization geometry."
            ),
        ] = False,
        include_sub_faces: Annotated[
            bool,
            Field(
                description="Whether room wireframe should include apertures and doors."
            ),
        ] = True,
        include_shades: Annotated[
            bool, Field(description="Whether room wireframe should include shades.")
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false to save a compact Garden visualization_set_target for export tools."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Build a VisualizationSet from a Garden Honeybee Room typed target."""
        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            wireframe_only=wireframe_only,
            include_sub_faces=include_sub_faces,
            include_shades=include_shades,
            name=name,
            return_visualization_set=return_visualization_set,
        )
