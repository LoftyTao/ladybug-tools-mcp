"""Create Dragonfly WindowParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.envelope_parameters import (
    create_dragonfly_window_parameter as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_dragonfly_window_parameter tool."""

    @mcp.tool(
        name="create_dragonfly_window_parameter",
        description=(
            "Create a compact SDK-backed Dragonfly WindowParameter artifact for "
            "Room2D, Story, Building, or Model outdoor wall application. Supports "
            "parameter_type simple_window_ratio and repeating_window_ratio only; "
            "this is not a Honeybee aperture alias. Returns the compact artifact "
            "as parameter, window_parameter, target, and object_dict."
        ),
        tags={"dragonfly-core", "garden-mode", "window", "parameter", "create", "safe"},
        timeout=20,
    )
    def create_dragonfly_window_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        parameter_type: Annotated[
            str,
            Field(
                description="Required Dragonfly window parameter type: simple_window_ratio or repeating_window_ratio."
            ),
        ],
        window_ratio: Annotated[
            float | None,
            Field(description="Window-to-wall ratio used by the Dragonfly parameter."),
        ] = None,
        wwr: Annotated[
            float | None,
            Field(description="Optional natural alias for window_ratio."),
        ] = None,
        rect_split: Annotated[
            bool,
            Field(description="SimpleWindowRatio rect_split flag."),
        ] = True,
        window_height: Annotated[
            float | None,
            Field(description="Required for repeating_window_ratio."),
        ] = None,
        sill_height: Annotated[
            float | None,
            Field(description="Required for repeating_window_ratio."),
        ] = None,
        horizontal_separation: Annotated[
            float | None,
            Field(description="Required for repeating_window_ratio."),
        ] = None,
        horiz_separator: Annotated[
            float | None,
            Field(description="Optional natural alias for horizontal_separation."),
        ] = None,
        vertical_separation: Annotated[
            float,
            Field(description="Optional vertical separation for repeating_window_ratio."),
        ] = 0,
        return_object_dict: Annotated[
            bool | None,
            Field(description="Optional low-cost output hint; this tool already returns a compact artifact."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly WindowParameter artifact."""
        if window_ratio is None:
            window_ratio = wwr
        if window_ratio is None:
            raise ValueError("create_dragonfly_window_parameter requires window_ratio or wwr.")
        if horizontal_separation is None and horiz_separator is not None:
            horizontal_separation = horiz_separator
        return service(
            garden_root=garden_root,
            parameter_type=parameter_type,
            window_ratio=window_ratio,
            rect_split=rect_split,
            window_height=window_height,
            sill_height=sill_height,
            horizontal_separation=horizontal_separation,
            vertical_separation=vertical_separation,
        )
