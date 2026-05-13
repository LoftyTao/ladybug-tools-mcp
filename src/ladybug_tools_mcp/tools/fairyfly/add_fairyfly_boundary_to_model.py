"""Add Fairyfly Boundary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.model import add_fairyfly_boundary_to_model as service


def register(mcp: FastMCP) -> None:
    """Register the add_fairyfly_boundary_to_model tool."""

    @mcp.tool(
        name="add_fairyfly_boundary_to_model",
        description="Add a Fairyfly Boundary to a Garden-backed Fairyfly Model from Ladybug Geometry 2D line segment input. The boundary is saved into the model, not as a separate target.",
        tags={"fairyfly", "therm", "model", "geometry", "boundary", "write", "safe", "garden-mode"},
        timeout=20,
    )
    def add_fairyfly_boundary_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        line_segments_2d: Annotated[
            list[list[list[float]]],
            Field(description="Boundary line segments as [[[x1, y1], [x2, y2]], ...]."),
        ],
        temperature: Annotated[
            float,
            Field(description="Steady-state boundary temperature in degrees Celsius."),
        ],
        film_coefficient: Annotated[
            float,
            Field(description="Boundary film coefficient in W/m2-K."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Fairyfly model target. Defaults to base Fairyfly model."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional display name for the Boundary and its condition."),
        ] = None,
        emissivity: Annotated[
            float,
            Field(description="Radiant environment emissivity."),
        ] = 1.0,
        radiant_temperature: Annotated[
            float | None,
            Field(description="Optional radiant temperature in degrees Celsius."),
        ] = None,
        heat_flux: Annotated[
            float,
            Field(description="Optional heat flux in W/m2."),
        ] = 0,
        relative_humidity: Annotated[
            float,
            Field(description="Boundary relative humidity from 0 to 1."),
        ] = 0.5,
        u_factor_tag: Annotated[
            str | None,
            Field(description="Optional THERM U-Factor tag such as Frame or Edge."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
    ) -> dict[str, Any]:
        """Add a Fairyfly Boundary to a model."""
        return service(
            garden_root=garden_root,
            line_segments_2d=line_segments_2d,
            temperature=temperature,
            film_coefficient=film_coefficient,
            model_target=model_target,
            name=name,
            emissivity=emissivity,
            radiant_temperature=radiant_temperature,
            heat_flux=heat_flux,
            relative_humidity=relative_humidity,
            u_factor_tag=u_factor_tag,
            rgb_color=rgb_color,
        )
