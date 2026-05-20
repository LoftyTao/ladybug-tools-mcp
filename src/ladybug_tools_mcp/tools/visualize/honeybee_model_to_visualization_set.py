"""Honeybee Model To Visualization Set MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.honeybee import (
    honeybee_model_to_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the honeybee_model_to_visualization_set tool."""

    @mcp.tool(
        name="honeybee_model_to_visualization_set",
        description="Create a Ladybug Display VisualizationSet / visualization set from a Honeybee model in a Garden. color_by accepts only type, boundary_condition, or none; use type for simple model previews. For Agent HTML/SVG export paths, set return_visualization_set=false so the tool saves a compact visualization_set_target for visualization_set_to_html/svg instead of moving the full VisualizationSet dict.",
        tags={
            "visualize",
            "visualization-set",
            "honeybee-model",
            "honeybee-core",
            "garden-mode",
            "model",
            "preview",
            "read",
            "safe",
        },
        timeout=30,
    )
    def honeybee_model_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target. Defaults to the Garden base model."
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(
                description="Model color strategy: type, boundary_condition, or none."
            ),
        ] = "type",
        include_wireframe: Annotated[
            bool, Field(description="Whether to include the model wireframe layer.")
        ] = True,
        wireframe_only: Annotated[
            bool,
            Field(
                description="Whether to return only wireframe visualization geometry."
            ),
        ] = False,
        use_mesh: Annotated[
            bool,
            Field(
                description="Whether colored model geometry should be DisplayMesh3D instead of DisplayFace3D."
            ),
        ] = False,
        hide_color_by: Annotated[
            bool,
            Field(
                description="Whether the color-by geometry layer should be hidden by default."
            ),
        ] = False,
        room_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional RoomAttribute specs for property-colored room AnalysisGeometry. Each spec supports name, attrs, color, text, and legend_parameter."
            ),
        ] = None,
        face_attributes: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional FaceAttribute specs for property-colored face AnalysisGeometry. Each spec supports name, attrs, color, text, legend_parameter, face_types, and boundary_conditions."
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false to save a Garden visualization_set_target for visualization_set_to_html/svg."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from a Garden Honeybee model."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            wireframe_only=wireframe_only,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            room_attributes=room_attributes,
            face_attributes=face_attributes,
            name=name,
            return_visualization_set=return_visualization_set,
        )
