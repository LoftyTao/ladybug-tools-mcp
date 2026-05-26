"""Save Base Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.store import save_base_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the garden_save_base_dragonfly_model tool.'

    @mcp.tool(
        name='save_base_dragonfly_model',
        description=(
            "Persist the current Garden base Dragonfly model back to Garden "
            "authoring truth as DFJSON. Use after Dragonfly edits have changed the "
            "in-memory base model and you need a fresh model_target before "
            "versioning, UWG, visualization, Honeybee conversion, or export. "
            "Returns model_target, summary_view, and persistence_receipt; it does "
            "not create a Garden version checkpoint and does not return the full "
            "DFJSON body."
        ),
        tags={
            "author",
            "base-model",
            "dragonfly",
            "garden",
            "model",
        },
        timeout=20,
    )
    def save_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; save the current Dragonfly "
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
                    "serialized Dragonfly model target appears unchanged."
                )
            ),
        ] = False,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional DFJSON file stem without extension; defaults to the "
                    "current base Dragonfly model identifier."
                )
            ),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="JSON indentation for the saved DFJSON file; defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Dragonfly extension property names to include in DFJSON; "
                    "None keeps the SDK default, usually all relevant properties."
                )
            ),
        ] = None,
    ) -> dict[str, object]:
        """Save the current Garden base Dragonfly model."""
        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
        )
