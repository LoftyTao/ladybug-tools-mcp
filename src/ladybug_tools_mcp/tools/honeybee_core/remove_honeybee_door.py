"""Remove Honeybee Door MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_door as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_remove_door tool.'

    @mcp.tool(
        name="remove_door",
        description='Remove one Honeybee Door from a Garden model using a door typed target from honeybee_search_model_objects and persist the updated model. Hosted Doors are supported; when the target is one side of a Surface-adjacent interior pair, the paired Door can be removed too and reported as paired_removed_identifier with removed_count=2. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "door",
            "edit",
            "hosted",
            "honeybee",
            "interior-door",
            "paired-door",
            "remove",
            "surface",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee door typed target from honeybee_search_model_objects; not a door identifier string.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Door by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
