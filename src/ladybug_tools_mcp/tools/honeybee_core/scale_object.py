"""Scale Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the HB_scale_object tool.'

    @mcp.tool(
        name='HB_scale_object',
        description="Scale a Honeybee Model, Room, Face, Aperture, Door, or Shade target by a positive factor from an optional Ladybug Geometry Point3D origin. This is a geometry transform, not a units conversion, and it does not automatically repair adjacency, host containment, or dynamic state geometry. Requires a typed target and positive factor; do not pass an identifier string. Returns the original target, summary_view, persistence_receipt with updated model_target, and report; for whole-model transforms summary_view.target is the updated model target. Run search, relate_model, or validate_model after partial-object transforms when relationships matter.",
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "scale",
            "target",
            "transform",
        },
        timeout=20,
    )
    def scale_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from HB_search_model_objects or a prior tool result.'
            ),
        ],
        factor: Annotated[
            float, Field(description="Required positive scale factor, for example 1.2.")
        ],
        origin: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Point3D origin dict, for example {'x':0,'y':0,'z':0}. Defaults to world origin."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_create_model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Scale a Honeybee target from an optional origin."""
        from garden.honeybee_core.transform import scale_object as service

        return service(
            garden_root=garden_root,
            target=target,
            factor=factor,
            origin=origin,
            model_target=model_target,
        )
