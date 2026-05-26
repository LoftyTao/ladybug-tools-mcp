"""Create Dragonfly ShadingParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.envelope_parameters import (
    create_dragonfly_shading_parameter as service,
)


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_create_shading_parameter tool.'

    @mcp.tool(
        name="create_shading_parameter",
        description=(
            "Create a compact SDK-backed Dragonfly ShadingParameter artifact for "
            "outdoor wall application. Supports parameter_type overhang and "
            "extruded_border only; this is a Dragonfly envelope parameter, not a Honeybee "
            "Shade or Radiance modifier. Returns "
            "the compact artifact as parameter, shading_parameter, target, and "
            "object_dict."
        ),
        tags={"dragonfly", "shading", "parameter", "author", "overhang", "extruded-border"},
        timeout=20,
    )
    def create_dragonfly_shading_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        parameter_type: Annotated[
            str,
            Field(description="Required Dragonfly shading parameter type: overhang or extruded_border."),
        ],
        depth: Annotated[
            float,
            Field(description="Depth for the Dragonfly overhang or extruded-border shading parameter."),
        ],
        angle: Annotated[
            float,
            Field(description="Overhang angle in degrees. Ignored by extruded_border."),
        ] = 0,
    ) -> dict[str, Any]:
        """Create a Dragonfly ShadingParameter artifact."""
        return service(
            garden_root=garden_root,
            parameter_type=parameter_type,
            depth=depth,
            angle=angle,
        )
