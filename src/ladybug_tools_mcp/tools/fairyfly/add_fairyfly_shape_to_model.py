"""Add Fairyfly Shape MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.model import add_fairyfly_shape_to_model as service


def register(mcp: FastMCP) -> None:
    """Register the add_fairyfly_shape_to_model tool."""

    @mcp.tool(
        name="add_fairyfly_shape_to_model",
        description="Add a Fairyfly Shape to a Garden-backed Fairyfly Model from Ladybug Geometry 2D polygon input. The shape is saved into the model, not as a separate target.",
        tags={"fairyfly", "therm", "model", "geometry", "shape", "write", "safe", "garden-mode"},
        timeout=20,
    )
    def add_fairyfly_shape_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        vertices_2d: Annotated[
            list[list[float]],
            Field(description="Shape polygon vertices as [[x, y], ...] in model units."),
        ],
        material: Annotated[
            dict[str, Any],
            Field(description="Fairyfly THERM material object_dict, such as create_fairyfly_solid_material.object_dict."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Fairyfly model target. Defaults to base Fairyfly model."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional display name for the Shape."),
        ] = None,
        holes_2d: Annotated[
            list[list[list[float]]] | None,
            Field(description="Optional hole polygons as [[[x, y], ...], ...]."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional cleanup tolerance for duplicate and colinear vertices."),
        ] = None,
    ) -> dict[str, Any]:
        """Add a Fairyfly Shape to a model."""
        return service(
            garden_root=garden_root,
            vertices_2d=vertices_2d,
            material=material,
            model_target=model_target,
            name=name,
            holes_2d=holes_2d,
            rgb_color=rgb_color,
            tolerance=tolerance,
        )
