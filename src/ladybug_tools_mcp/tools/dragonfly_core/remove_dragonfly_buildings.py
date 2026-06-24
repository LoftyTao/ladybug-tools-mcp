"""Remove Dragonfly Buildings MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.editing import remove_dragonfly_buildings as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_remove_buildings tool."""

    @mcp.tool(
        name="remove_buildings",
        description=(
            "Remove Buildings from a Garden Dragonfly Model using Building object "
            "targets or identifiers. Embedded Stories and Room2Ds inside removed "
            "Buildings leave the model with their parent Building and the scope is "
            "reported in relationship_cleanup. Returns target, model_target, "
            "summary_view, persistence_receipt, and report for the updated model."
        ),
        tags={"dragonfly", "building", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_buildings(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Building object targets from df_search_objects."),
        ] = None,
        building_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Building identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Buildings."""
        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            building_identifiers=building_identifiers,
            model_target=model_target,
        )
