"""Create Honeybee Face MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_face as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_face tool."""

    @mcp.tool(
        name="create_honeybee_face",
        description="Create an orphaned Honeybee Face from a Ladybug Geometry Face3D dictionary. Requires garden_root, identifier, and geometry; do not pass arguments null or {}. Downstream tools use only the returned nested target dict, not the full tool response.",
        tags={"honeybee-core", "garden-mode", "face", "geometry", "write", "safe"},
        timeout=20,
    )
    def create_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee face identifier.")
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Face3D dict, for example {'type':'Face3D','boundary':[[x,y,z],...]}; not Rhino geometry."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create an orphaned Honeybee Face."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            model_target=model_target,
        )
