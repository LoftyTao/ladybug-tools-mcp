"""Remove Honeybee Face MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_face as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_remove_face tool.'

    @mcp.tool(
        name="remove_face",
        description='Remove one orphaned Honeybee Face from a Garden model using a face typed target from honeybee_search_model_objects and persist the updated model. Room-hosted Faces are rejected because deleting one would break the Room closed solid; this is not a remove wall from room shortcut. Requires garden_root and target; do not pass an identifier string. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "edit",
            "face",
            "geometry",
            "honeybee",
            "orphaned-face",
            "remove",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face typed target from honeybee_search_model_objects; not a face identifier string. Room-hosted faces cannot be removed by this tool.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Face by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
