"""Save Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import save_base_honeybee_model as service


def register(mcp: FastMCP) -> None:
    'Register the garden_save_base_honeybee_model tool.'

    @mcp.tool(
        name='save_base_honeybee_model',
        description=(
            "Persist the current Garden base Honeybee model back to Garden "
            "authoring truth as HBJSON. Use after Honeybee edits have changed the "
            "in-memory base model and you need a fresh model_target before "
            "versioning, Energy, Radiance, visualization, or export. Returns "
            "model_target, summary_view, and persistence_receipt; it does not "
            "create a Garden version checkpoint and does not return the full "
            "HBJSON body."
        ),
        tags={
            "author",
            "base-model",
            "garden",
            "honeybee",
            "model",
        },
        timeout=20,
    )
    def save_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; save the current Honeybee "
                    "base-model slot for this Garden."
                )
            ),
        ],
        message: Annotated[
            str | None,
            Field(
                description=(
                    "Optional short save note stored in the persistence receipt "
                    "and summary_view; this is not a Garden version subject."
                )
            ),
        ] = None,
        force: Annotated[
            bool,
            Field(
                description=(
                    "Force the persistence receipt to report a save even when the "
                    "serialized Honeybee model target appears unchanged."
                )
            ),
        ] = False,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional HBJSON file stem without extension; defaults to the "
                    "current base Honeybee model identifier."
                )
            ),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="JSON indentation for the saved HBJSON file; defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Honeybee extension property names to include in HBJSON; "
                    "None keeps the SDK default, usually all relevant properties."
                )
            ),
        ] = None,
        triangulate_sub_faces: Annotated[
            bool,
            Field(
                description=(
                    "Whether Honeybee sub-faces should be triangulated during "
                    "HBJSON serialization."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Save the current Garden base Honeybee model."""
        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
            triangulate_sub_faces=triangulate_sub_faces,
        )
