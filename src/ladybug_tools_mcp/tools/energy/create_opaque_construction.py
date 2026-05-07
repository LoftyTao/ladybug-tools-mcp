"""Create OpaqueConstruction MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import (
    create_opaque_construction as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_opaque_construction tool."""

    @mcp.tool(
        name="create_opaque_construction",
        description="Create a Honeybee Energy OpaqueConstruction from opaque material layers ordered from outside to inside. Material inputs can be object_dict values, Garden Properties Library targets, or Energy standards library identifiers. Use garden_root and return_object_dict=false to save the construction and pass its target downstream. Returns object_dict plus summary_view with layer identifiers and derived thermal properties.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "construction",
            "opaque",
            "create",
            "safe",
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
                description="Optional Garden root for consuming material targets and saving this construction."
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
