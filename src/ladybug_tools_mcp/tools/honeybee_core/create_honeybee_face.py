"""Create Honeybee Face MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_face as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_face tool.'

    @mcp.tool(
        name="create_face",
        description="Create an orphaned Honeybee Face from a Ladybug Geometry Face3D dictionary and persist it in the Garden Honeybee Model. The Honeybee SDK infers default face type and boundary condition here; this tool does not accept face_type or boundary_condition parameters and is not a direct EnergyPlus surface or Radiance polygon authoring tool. Requires garden_root, identifier, and geometry; do not pass arguments null or {}. Downstream tools use the returned nested target dict. Returns target, object_target, model_target, face_target, summary_view, persistence_receipt, and report.",
        tags={
            "author",
            "face",
            "geometry",
            "honeybee",
        },
        timeout=20,
    )
    def create_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee face identifier.")
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Face3D dict, for example {'type':'Face3D','boundary':[[x,y,z],...]}; not Rhino geometry, face_type, or boundary_condition."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
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
