"""Create window frame material MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_window_frame_material as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_window_frame_material tool."""

    @mcp.tool(
        name="create_window_frame_material",
        description="Create a Honeybee Energy EnergyWindowFrame that can be attached to a WindowConstruction. Returns object_dict plus summary_view. Use return_detail='summary' for key frame values or 'full' for a matrix of material property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "material",
            "window",
            "frame",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_window_frame_material(
        identifier: Annotated[str, Field(description="Window frame identifier.")],
        width: Annotated[float, Field(description="Frame width in meters.")],
        conductance: Annotated[
            float, Field(description="Frame conductance in W/m2-K.")
        ],
        edge_to_center_ratio: Annotated[
            float, Field(description="Edge-to-center glass conductance ratio.")
        ] = 1,
        outside_projection: Annotated[
            float, Field(description="Outside frame projection in meters.")
        ] = 0,
        inside_projection: Annotated[
            float, Field(description="Inside frame projection in meters.")
        ] = 0,
        thermal_absorptance: Annotated[
            float, Field(description="Long-wave absorptance.")
        ] = 0.9,
        solar_absorptance: Annotated[
            float, Field(description="Solar absorptance.")
        ] = 0.7,
        visible_absorptance: Annotated[
            float | None, Field(description="Visible absorptance.")
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for saving this material to the Garden Properties Library."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowFrame object."""
        return service(
            identifier=identifier,
            width=width,
            conductance=conductance,
            edge_to_center_ratio=edge_to_center_ratio,
            outside_projection=outside_projection,
            inside_projection=inside_projection,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
