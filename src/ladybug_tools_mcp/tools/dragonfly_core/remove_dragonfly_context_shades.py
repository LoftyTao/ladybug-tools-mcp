"""Remove Dragonfly ContextShades MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import remove_dragonfly_context_shades as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_remove_context_shades tool."""

    @mcp.tool(
        name="remove_context_shades",
        description=(
            "Remove ContextShades from a Garden Dragonfly Model using ContextShade "
            "object targets or identifiers. Returns target, model_target, summary_view, "
            "persistence_receipt, and report for the updated Dragonfly Model."
        ),
        tags={"dragonfly", "context-shade", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_context_shades(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional ContextShade object targets from df_search_objects."),
        ] = None,
        context_shade_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional ContextShade identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly ContextShades."""
        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            context_shade_identifiers=context_shade_identifiers,
            model_target=model_target,
        )
