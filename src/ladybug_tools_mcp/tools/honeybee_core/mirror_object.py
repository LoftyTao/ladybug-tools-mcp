"""Mirror Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import mirror_object as service


def register(mcp: FastMCP) -> None:
    """Register the mirror_object tool."""

    @mcp.tool(
        name="mirror_object",
        description="Mirror a Honeybee Model, Room, Face, Aperture, Door, or Shade target by reflecting it across a Ladybug Geometry Plane. Requires a typed target and plane dict; do not pass arguments null or {}.",
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
            "mirror",
            "reflect",
            "write",
        },
        timeout=20,
    )
    def mirror_object(
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
        plane: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Plane dict with origin o and normal n, for example {'o':[0,0,0],'n':[1,0,0]}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to base model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Reflect a Honeybee target across a Plane."""
        return service(
            garden_root=garden_root,
            target=target,
            plane=plane,
            model_target=model_target,
        )
