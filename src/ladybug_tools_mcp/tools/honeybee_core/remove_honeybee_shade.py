"""Remove Honeybee Shade MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_shade as service


def register(mcp: FastMCP) -> None:
    """Register the remove_honeybee_shade tool."""

    @mcp.tool(
        name="remove_honeybee_shade",
        description="Remove one Honeybee Shade from a Garden model using a shade typed target from search_honeybee_model_objects and persist the updated model. Requires garden_root and target; do not pass arguments null or {}.",
        tags={"honeybee-core", "garden-mode", "shade", "write", "destructive"},
        timeout=20,
    )
    def remove_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee shade typed target from search_honeybee_model_objects; not a shade identifier string."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Shade by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
