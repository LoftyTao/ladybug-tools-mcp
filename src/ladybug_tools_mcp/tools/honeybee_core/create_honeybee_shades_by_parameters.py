"""Create Honeybee Shades By Parameters MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import (
    create_honeybee_shades_by_parameters as service,
)


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_shades_by_parameters tool.'

    @mcp.tool(
        name="create_shades_by_parameters",
        description='Create Honeybee Shade louvers, horizontal louver arrays, or aperture extruded borders on a Face or Aperture typed target. This is the parametric shade path for louver_by_count, louver_by_distance_between, and aperture-only extruded_border; it does not expose a parametric overhang mode. Use honeybee_create_shade only when the user provides explicit Face3D geometry. Prefer honeybee_search_model_objects matches[i].target or a prior result target as host_target. Requires garden_root, host_target, generation_mode, and parameters; do not pass arguments null or {}. Returns target, shade_target, targets, summary_view, persistence_receipt, and report.',
        tags={
            "aperture",
            "author",
            "extruded-border",
            "face",
            "geometry",
            "honeybee",
            "hosted",
            "louver",
            "shade",
        },
        timeout=20,
    )
    def create_honeybee_shades_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face or aperture typed target dict from nested target honeybee_search_model_objects matches[i].target or a prior create result target; full responses and identifier strings are rejected.'
            ),
        ],
        generation_mode: Annotated[
            str | None,
            Field(
                description="Required generation mode: louver_by_count, louver_by_distance_between, or extruded_border. extruded_border only accepts an aperture target."
            ),
        ] = None,
        parameters: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required small mode parameter object: louver_by_count uses {'depth':0.35,'louver_count':2}; louver_by_distance_between uses {'depth':0.35,'distance':0.5}; extruded_border uses {'depth':0.2}. Optional base_name may guide generated Shade identifiers."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Shades on a Face or Aperture with SDK parameter methods."""
        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            parameters=parameters,
            model_target=model_target,
        )
