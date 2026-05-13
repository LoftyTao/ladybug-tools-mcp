"""Apply Dragonfly ShadingParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.envelope_parameters import (
    apply_dragonfly_shading_parameter as service,
)


def register(mcp: FastMCP) -> None:
    """Register the apply_dragonfly_shading_parameter tool."""

    @mcp.tool(
        name="apply_dragonfly_shading_parameter",
        description="Apply a Dragonfly ShadingParameter artifact using public Dragonfly SDK set_outdoor_shading_parameters methods. Supports Room2D, Story, Building, and Model outdoor application.",
        tags={"dragonfly-core", "garden-mode", "shading", "parameter", "apply", "write", "safe"},
        timeout=20,
    )
    def apply_dragonfly_shading_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        shading_parameter: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required parameter dict returned by create_dragonfly_shading_parameter. "
                    "Use create result['parameter'] or result['shading_parameter']; do not "
                    "look for value.shading_parameter."
                )
            ),
        ],
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
            Field(description="Only all_outdoor is supported by the stable Dragonfly SDK shading set methods."),
        ] = "all_outdoor",
    ) -> dict[str, Any]:
        """Apply a Dragonfly ShadingParameter."""
        return service(
            garden_root=garden_root,
            shading_parameter=shading_parameter,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
            application_scope=application_scope,
        )
