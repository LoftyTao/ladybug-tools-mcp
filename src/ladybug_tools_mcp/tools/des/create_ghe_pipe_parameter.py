"""Create Dragonfly DES PipeParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_ghe_pipe_parameter as service


def register(mcp: FastMCP) -> None:
    """Register the DES GHE pipe parameter tool."""

    @mcp.tool(
        name="create_ghe_pipe_parameter",
        description=(
            "Create a Dragonfly DES PipeParameter for ground heat exchanger borehole "
            "pipes, including inner and outer diameters, shank spacing, roughness, "
            "conductivity, heat capacity, and U-tube arrangement. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "parameter", "pipe", "target"},
        timeout=20,
    )
    def create_ghe_pipe_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved PipeParameter target.")],
        inner_diameter: Annotated[float | None, Field(description="Optional pipe inner diameter in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        outer_diameter: Annotated[float | None, Field(description="Optional pipe outer diameter in meters; must be greater than inner_diameter when both are set.")] = None,
        shank_spacing: Annotated[float | None, Field(description="Optional U-tube shank spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        roughness: Annotated[float | None, Field(description="Optional pipe roughness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        conductivity: Annotated[float | None, Field(description="Optional pipe conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional pipe heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        arrangement: Annotated[str | None, Field(description="Optional SDK pipe arrangement such as SingleUTube, DoubleUTubeSeries, or DoubleUTubeParallel.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES PipeParameter."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            inner_diameter=inner_diameter,
            outer_diameter=outer_diameter,
            shank_spacing=shank_spacing,
            roughness=roughness,
            conductivity=conductivity,
            heat_capacity=heat_capacity,
            arrangement=arrangement,
        )
