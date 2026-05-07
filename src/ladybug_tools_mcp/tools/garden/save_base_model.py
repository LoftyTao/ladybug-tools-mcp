"""Save Base Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import save_base_model as service


def register(mcp: FastMCP) -> None:
    """Register the save_base_model tool."""

    @mcp.tool(
        name="save_base_model",
        description="Save the current Honeybee base model back to Garden authoring truth. This uses Honeybee Model.to_hbjson and does not rely on SDK default folders. Requires an existing Garden base model; if the Garden is empty, report the failure.",
        tags={
            "garden",
            "garden-mode",
            "model",
            "base-model",
            "hbjson",
            "authoring-truth",
            "save",
            "write",
            "safe",
        },
        timeout=20,
    )
    def save_base_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json. Do not pass null or {}."
            ),
        ],
        message: Annotated[
            str | None, Field(description="Optional short save message.")
        ] = None,
        force: Annotated[
            bool, Field(description="Force a save even when changes are light.")
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional output HBJSON name, without extension."),
        ] = None,
        indent: Annotated[
            int | None, Field(description="HBJSON indentation. Defaults to 2.")
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(description="Extension properties to include. Defaults to all."),
        ] = None,
        triangulate_sub_faces: Annotated[
            bool, Field(description="Whether to triangulate sub-faces on save.")
        ] = False,
    ) -> dict[str, Any]:
        """Save the current Garden base model."""
        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
            triangulate_sub_faces=triangulate_sub_faces,
        )
