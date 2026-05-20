"""Apply Dragonfly WindowParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.envelope_parameters import (
    apply_dragonfly_window_parameter as service,
)


def register(mcp: FastMCP) -> None:
    """Register the apply_dragonfly_window_parameter tool."""

    @mcp.tool(
        name="apply_dragonfly_window_parameter",
        description="Apply a Dragonfly WindowParameter artifact using public Dragonfly SDK set methods. Supports Room2D all outdoor, Room2D segment, Story outdoor, Building outdoor, and Model outdoor application. Pass host_type explicitly as room2d, story, building, or model.",
        tags={"dragonfly-core", "garden-mode", "window", "parameter", "apply", "write", "safe"},
        timeout=20,
    )
    def apply_dragonfly_window_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        window_parameter: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required parameter dict returned by create_dragonfly_window_parameter. "
                    "Use create result['parameter'] or result['window_parameter']; do not "
                    "look for value.window_parameter."
                )
            ),
        ] = None,
        host_type: Annotated[
            str | None,
            Field(description="Host type: room2d, story, building, or model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly object target unless host_type is model."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        application_scope: Annotated[
            str,
            Field(description="Application scope: all_outdoor or segment. Segment is Room2D-only."),
        ] = "all_outdoor",
        segment_index: Annotated[
            int | None,
            Field(description="Required when application_scope is segment."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply a Dragonfly WindowParameter."""
        if window_parameter is None:
            raise ValueError("apply_dragonfly_window_parameter requires window_parameter.")
        return service(
            garden_root=garden_root,
            window_parameter=window_parameter,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
            application_scope=application_scope,
            segment_index=segment_index,
        )
