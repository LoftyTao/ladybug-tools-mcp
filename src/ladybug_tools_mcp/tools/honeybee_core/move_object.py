"""Move Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import move_object as service


def register(mcp: FastMCP) -> None:
    """Register the move_object tool."""

    @mcp.tool(
        name="move_object",
        description="Move a Honeybee Model, Room, Face, Aperture, Door, or Shade target along a Ladybug Geometry Vector3D. Requires garden_root, a typed target from search or a prior result, and vector; do not pass arguments null or {}.",
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
            "move",
            "write",
        },
        timeout=20,
    )
    def move_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee model target or object typed target from search_honeybee_model_objects or a prior tool result; not an identifier string."
            ),
        ],
        vector: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Vector3D dict, for example {'type':'Vector3D','x':0.5,'y':0,'z':0} or {'x':0.5,'y':0,'z':0}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to base model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Move a Honeybee target along a Vector3D."""
        return service(
            garden_root=garden_root,
            target=target,
            vector=vector,
            model_target=model_target,
        )
