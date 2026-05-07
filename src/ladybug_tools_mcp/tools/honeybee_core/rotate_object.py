"""Rotate Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import rotate_object as service


def register(mcp: FastMCP) -> None:
    """Register the rotate_object tool."""

    @mcp.tool(
        name="rotate_object",
        description="Rotate a Honeybee Model, Room, Face, Aperture, Door, or Shade target around a 3D axis and origin. Requires a typed target plus Ladybug Geometry axis and origin dicts; do not pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "room",
            "face",
            "aperture",
            "door",
            "shade",
            "transform",
            "rotate",
            "write",
        },
        timeout=20,
    )
    def rotate_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee model target or object typed target from search_honeybee_model_objects or a prior tool result."
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
                description="Optional Honeybee model target dict. Defaults to base model unless target is a model target."
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
