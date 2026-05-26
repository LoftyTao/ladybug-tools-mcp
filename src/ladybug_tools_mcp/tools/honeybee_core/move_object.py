"""Move Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import move_object as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_move_object tool.'

    @mcp.tool(
        name='move_object',
        description="Move a Honeybee Model, Room, Face, Aperture, Door, or Shade target along a Ladybug Geometry Vector3D. This transform does not automatically repair adjacency, host containment, or dynamic state geometry. Requires garden_root, a typed target from search or a prior result, and vector; do not pass an identifier string. Returns the original target, summary_view, persistence_receipt with updated model_target, and report; for whole-model transforms summary_view.target is the updated model target. Run search, relate_model, or validate_model after partial-object transforms when relationships matter.",
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "move",
            "target",
            "transform",
        },
        timeout=20,
    )
    def move_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from honeybee_search_model_objects or a prior tool result; not an identifier string.'
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
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
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
