"""Scale Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import scale_object as service


def register(mcp: FastMCP) -> None:
    """Register the scale_object tool."""

    @mcp.tool(
        name="scale_object",
        description="Scale a Honeybee Model, Room, Face, Aperture, Door, or Shade target by a positive factor from an optional Point3D origin. Requires a typed target and positive factor; do not pass arguments null or {}.",
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
            "scale",
            "write",
        },
        timeout=20,
    )
    def scale_object(
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
                description="Optional Honeybee model target dict. Defaults to base model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Scale a Honeybee target from an optional origin."""
        return service(
            garden_root=garden_root,
            target=target,
            factor=factor,
            origin=origin,
            model_target=model_target,
        )
