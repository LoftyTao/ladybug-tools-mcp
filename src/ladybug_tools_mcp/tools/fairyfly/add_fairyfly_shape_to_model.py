"""Add Fairyfly Shape MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.model import add_fairyfly_shape_to_model as service


def register(mcp: FastMCP) -> None:
    'Register the therm_add_shape_to_model tool.'

    @mcp.tool(
        name="add_shape_to_model",
        description=(
            "Add a Fairyfly Shape to a Garden-backed Fairyfly Model from Ladybug "
            "Geometry 2D polygon input and a THERM material object_dict. The shape is "
            "saved into the model, not as a separate target. This edits the 2D section "
            "and does not run THERM."
        ),
        tags={"fairyfly", "therm", "model", "geometry", "shape", "2d"},
        timeout=20,
    )
    def add_fairyfly_shape_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        vertices_2d: Annotated[
            list[list[float]],
            Field(description="Fairyfly Shape polygon vertices as [[x, y], ...] in two-dimensional model units."),
        ],
        material: Annotated[
            dict[str, Any],
            Field(description='Fairyfly THERM material object_dict, such as therm_create_solid_material.object_dict.'),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually therm_create_model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
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
