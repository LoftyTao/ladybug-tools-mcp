"""Create OpaqueConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_opaque_construction as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energy_create_opaque_construction tool.'

    @mcp.tool(
        name='create_opaque_construction',
        description="Create a Honeybee Energy OpaqueConstruction, the complete layered assembly made from opaque thermal-mass or no-mass material layers ordered from outside to inside for walls, roofs, and floors. Material inputs can be object_dict values, Garden Properties Library targets, or Energy standards library identifiers. Use garden_root and return_object_dict=false to save a reusable construction target for ConstructionSet or Room energy assignments. Returns object_dict plus summary_view, or target plus persistence_receipt when saved.",
        tags={
            "energy",
            "construction",
            "material",
            "thermal-mass",
            "wall",
            "author",
        },
        timeout=20,
    )
    def create_opaque_construction(
        identifier: Annotated[str, Field(description="OpaqueConstruction identifier.")],
        materials: Annotated[
            list[dict[str, Any] | str],
            Field(
                description="Opaque material layers from outside to inside; each item may be a dict, Garden target, or standards library identifier."
            ),
        ],
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full also returns a layer_matrix with material rows."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy OpaqueConstruction object."""
        return service(
            identifier=identifier,
            materials=materials,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
