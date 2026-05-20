"""Compose Visualization Sets MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.visualize.honeybee import compose_visualization_sets as service


def register(mcp: FastMCP) -> None:
    """Register the compose_visualization_sets tool."""

    @mcp.tool(
        name="compose_visualization_sets",
        description="Compose multiple Ladybug Display VisualizationSets into one scene from either visualization_set dictionaries or Garden-backed visualization_set_targets. Preferred Agent path is garden_root plus exact visualization_set_targets from upstream tools and return_visualization_set=false, returning a compact visualization_set_target for visualization_set_to_html/svg/vtkjs without expanding large geometry dicts. Do not invent a type field; target dicts use target_type=visualization_set. For model + room preview overlays, set conflict_strategy=rename on the first compose attempt because wireframe identifiers often repeat. If some input VisualizationSets omit units, the first explicit unit is used; pass units only when intentionally converting between explicit unit systems.",
        tags={"visualize", "dual-mode", "payload-mode", "target-mode", "garden-mode", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def compose_visualization_sets(
        visualization_sets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="VisualizationSet dictionaries to combine. Prefer visualization_set_targets for Agent Garden workflows."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root directory. Required when using visualization_set_targets or return_visualization_set=false."),
        ] = None,
        visualization_set_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Garden-backed visualization_set targets from upstream visualize tools. Use target_type=visualization_set; do not invent type=visualization_set."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional composed VisualizationSet identifier and display name."
            ),
        ] = None,
        units: Annotated[
            str | None,
            Field(
                description="Optional output units. If omitted, explicit input units must match; blank/missing units adopt the first explicit unit."
            ),
        ] = None,
        check_duplicate_geometry_ids: Annotated[
            bool, Field(description="Whether to check geometry identifier conflicts.")
        ] = True,
        conflict_strategy: Annotated[
            str,
            Field(
                description="Geometry identifier conflict strategy: error or rename. Use rename for model + room preview overlays because wireframe identifiers often repeat."
            ),
        ] = "error",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet dict. Set false with garden_root to save and return a compact visualization_set_target for exporters."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Compose VisualizationSet dictionaries into one VisualizationSet."""
        return service(
            visualization_sets=visualization_sets,
            garden_root=garden_root,
            visualization_set_targets=visualization_set_targets,
            name=name,
            units=units,
            check_duplicate_geometry_ids=check_duplicate_geometry_ids,
            conflict_strategy=conflict_strategy,
            return_visualization_set=return_visualization_set,
        )
