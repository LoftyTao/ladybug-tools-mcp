"""Honeybee Face To Visualization Set MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.honeybee import (
    honeybee_face_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the honeybee_face_to_visualization_set tool."""

    @mcp.tool(
        name="honeybee_face_to_visualization_set",
        description="Visualize one Honeybee Face typed target as a Ladybug Display VisualizationSet. Use this read-only preview after object search finds the face target. For Agent HTML/SVG/vtk.js export paths, set return_visualization_set=false so the tool saves a compact visualization_set_target for exporters instead of moving the full VisualizationSet dict.",
        tags={"visualize", "honeybee-core", "garden-mode", "face", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def honeybee_face_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
        target: Annotated[
            dict[str, Any], Field(description="Honeybee face typed target.")
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target. Defaults to target model or Garden base model."
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Face color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include a face wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only face wireframe visualization geometry."
            ),
        ] = False,
        include_sub_faces: Annotated[
            bool,
            Field(
                description="Whether face wireframe should include apertures and doors."
            ),
        ] = True,
        include_shades: Annotated[
            bool, Field(description="Whether face wireframe should include shades.")
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false to save and return a compact visualization_set_target."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Build a VisualizationSet from a Garden Honeybee Face typed target."""
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
