"""Apply Dragonfly ShadingParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.envelope_parameters import (
    apply_dragonfly_shading_parameter as service,
)


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_apply_shading_parameter tool.'

    @mcp.tool(
        name="apply_shading_parameter",
        description=(
            "Apply a Dragonfly ShadingParameter artifact using public Dragonfly SDK "
            "set_outdoor_shading_parameters methods. Supports Room2D, Story, Building, "
            "and Model outdoor application. Returns target, report, and the updated "
            "Dragonfly host context; this does not create Honeybee Shades or Radiance "
            "modifiers."
        ),
        tags={"dragonfly", "shading", "parameter", "edit", "overhang"},
        timeout=20,
    )
    def apply_dragonfly_shading_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        shading_parameter: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required parameter dict returned by dragonfly_create_shading_parameter. '
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
            Field(description="Required Dragonfly Room2D, Story, or Building target unless host_type is model."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
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
