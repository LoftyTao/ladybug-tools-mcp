"""Rotate Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import rotate_object as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_rotate_object tool.'

    @mcp.tool(
        name='rotate_object',
        description="Rotate a Honeybee Model, Room, Face, Aperture, Door, or Shade target around a Ladybug Geometry Vector3D axis and Point3D origin, with angle_degrees in degrees. This transform does not automatically repair adjacency, host containment, or dynamic state geometry. Requires a typed target plus axis and origin dicts; do not pass an identifier string. Returns the original target, summary_view, persistence_receipt with updated model_target, and report; for whole-model transforms summary_view.target is the updated model target. Run search, relate_model, or validate_model after partial-object transforms when relationships matter.",
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "rotate",
            "target",
            "transform",
        },
        timeout=20,
    )
    def rotate_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from honeybee_search_model_objects or a prior tool result.'
            ),
        ],
        axis: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Vector3D axis dict, for example {'x':0,'y':0,'z':1}."
            ),
        ],
        angle_degrees: Annotated[
            float, Field(description="Required rotation angle in degrees.")
        ],
        origin: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Point3D origin dict, for example {'x':0,'y':0,'z':0}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Rotate a Honeybee target around an axis and origin."""
        return service(
            garden_root=garden_root,
            target=target,
            axis=axis,
            angle_degrees=angle_degrees,
            origin=origin,
            model_target=model_target,
        )
