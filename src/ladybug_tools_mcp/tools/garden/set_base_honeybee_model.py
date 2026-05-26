"""Set Base Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import set_domain_base_model


def register(mcp: FastMCP) -> None:
    'Register the garden_set_base_honeybee_model tool.'

    @mcp.tool(
        name='set_base_honeybee_model',
        description=(
            "Register or select an existing Honeybee model target as the Garden "
            "base Honeybee model slot. Pass the nested model_target from a "
            "Honeybee create tool, garden_list_models, or another base-model "
            "handoff; this writes garden.json and may add the target to the "
            "manifest model list. Returns model_target, summary_view, and "
            "persistence_receipt for subsequent Honeybee, Energy, Radiance, "
            "visualization, versioning, or export calls. It does not edit model "
            "geometry or validate HBJSON."
        ),
        tags={
            "author",
            "base-model",
            "garden",
            "honeybee",
            "model",
            "target",
        },
        timeout=10,
    )
    def set_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; set the Honeybee base-model "
                    "slot in this Garden manifest."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Nested Honeybee model target to set as the Garden base "
                    "Honeybee model. Pass the model_target dict itself, not a full "
                    "tool response and not only an identifier string."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Honeybee model."""
        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="honeybee",
        )
