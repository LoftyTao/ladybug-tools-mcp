"""Remove Honeybee Aperture MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.removal import remove_honeybee_aperture as service


def register(mcp: FastMCP) -> None:
    """Register the remove_honeybee_aperture tool."""

    @mcp.tool(
        name="remove_honeybee_aperture",
        description="Remove one Honeybee Aperture from a Garden model using an aperture typed target from search_honeybee_model_objects and persist the updated model. Requires garden_root and target; do not pass arguments null or {}.",
        tags={"honeybee-core", "garden-mode", "aperture", "write", "destructive"},
        timeout=20,
    )
    def remove_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee aperture typed target from search_honeybee_model_objects; not an aperture identifier string."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Aperture by typed target."""
        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )
