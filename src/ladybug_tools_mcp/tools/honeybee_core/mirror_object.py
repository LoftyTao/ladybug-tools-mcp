"""Mirror Object MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.transform import mirror_object as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_mirror_object tool.'

    @mcp.tool(
        name='mirror_object',
        description="Mirror, or reflect, a Honeybee Model, Room, Face, Aperture, Door, or Shade target across a Ladybug Geometry Plane. This transform does not automatically repair adjacency, host containment, or dynamic state geometry. Requires a typed target and plane dict; do not pass an identifier string. Returns the original target, summary_view, persistence_receipt with updated model_target, and report; for whole-model transforms summary_view.target is the updated model target. Run search, relate_model, or validate_model after partial-object transforms when relationships matter.",
        tags={
            "edit",
            "geometry",
            "honeybee",
            "mirror",
            "model",
            "target",
            "transform",
        },
        timeout=20,
    )
    def mirror_object(
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
        plane: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Plane dict with origin o and normal n, for example {'o':[0,0,0],'n':[1,0,0]}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
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
