"""Remove Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_room as service


def register(mcp: FastMCP) -> None:
    """Register the remove_honeybee_room tool."""

    @mcp.tool(
        name="remove_honeybee_room",
        description="Remove one Honeybee Room from a Garden model using a room typed target from search_honeybee_model_objects and persist the updated model. Requires garden_root and target; do not pass arguments null or {}.",
        tags={"honeybee-core", "garden-mode", "room", "write", "destructive"},
        timeout=20,
    )
    def remove_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee room typed target from search_honeybee_model_objects; not a room identifier string."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Room by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
