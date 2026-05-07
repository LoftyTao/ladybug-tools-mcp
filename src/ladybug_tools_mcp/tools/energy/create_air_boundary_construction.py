"""Create AirBoundaryConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_air_boundary_construction as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_air_boundary_construction tool."""

    @mcp.tool(
        name="create_air_boundary_construction",
        description="Create a Honeybee Energy AirBoundaryConstruction for air-boundary Faces. Returns object_dict plus summary_view with air mixing property values.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "construction",
            "air-boundary",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_air_boundary_construction(
        identifier: Annotated[
            str, Field(description="AirBoundaryConstruction identifier.")
        ],
        air_mixing_per_area: Annotated[
            float, Field(description="Air mixing per area in m3/s-m2.")
        ] = 0.1,
        air_mixing_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional schedule dict or library identifier."),
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full keeps the same concise fields for this scalar construction."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming schedule targets and saving this construction."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy AirBoundaryConstruction object."""
        return service(
            identifier=identifier,
            air_mixing_per_area=air_mixing_per_area,
            air_mixing_schedule=air_mixing_schedule,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
