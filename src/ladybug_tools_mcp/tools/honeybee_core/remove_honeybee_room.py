"""Remove Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_room as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_remove_room tool.'

    @mcp.tool(
        name="remove_room",
        description='Remove one Honeybee Room from a Garden model using a room typed target from honeybee_search_model_objects and persist the updated model. This also clears Surface boundary relationships in remaining rooms that pointed to the removed room and reports adjacency_cleanup. Requires garden_root and target; do not pass an identifier string. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "adjacency",
            "boundary",
            "cleanup",
            "edit",
            "honeybee",
            "remove",
            "room",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee room typed target from honeybee_search_model_objects; not a room identifier string.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Room by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
