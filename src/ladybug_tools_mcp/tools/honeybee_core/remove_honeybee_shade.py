"""Remove Honeybee Shade MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_shade as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_remove_shade tool.'

    @mcp.tool(
        name="remove_shade",
        description='Remove one Honeybee Shade from a Garden model using a shade typed target from honeybee_search_model_objects and persist the updated model. Orphaned and hosted shades are supported, including Room, Face, Aperture, and Door child shade contexts; the service removes the child from its parent list where needed. Requires garden_root and target; do not pass an identifier string. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "edit",
            "hosted",
            "hosted-shade",
            "honeybee",
            "remove",
            "shade",
            "shading",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee shade typed target from honeybee_search_model_objects; not a shade identifier string.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Shade by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
