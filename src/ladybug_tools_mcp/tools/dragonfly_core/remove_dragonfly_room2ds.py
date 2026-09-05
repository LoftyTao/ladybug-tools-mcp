"""Remove Dragonfly Room2Ds MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DF_remove_room2ds tool."""

    @mcp.tool(
        name="DF_remove_room2ds",
        description=(
            "Remove Room2Ds from a Garden Dragonfly Model using Room2D object targets "
            "or identifiers. Empty parent Stories and Buildings are cleaned from the "
            "saved model and reported in relationship_cleanup. Returns target, "
            "model_target, summary_view, persistence_receipt, and report for the "
            "updated Dragonfly Model."
        ),
        tags={"dragonfly", "room2d", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_room2ds(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Room2D object targets from DF_search_objects or DF_room2ds_by_attribute."),
        ] = None,
        room2d_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Room2D identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Room2Ds."""
        from garden.dragonfly_core.editing import remove_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            room2d_identifiers=room2d_identifiers,
            model_target=model_target,
        )
