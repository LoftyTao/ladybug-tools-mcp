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
        description="Compose multiple Ladybug Display VisualizationSet dictionaries into one scene. Use after Honeybee model, room, or face visualization tools before HTML or SVG export.",
        tags={"visualize", "dual-mode", "payload-mode", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def compose_visualization_sets(
        visualization_sets: Annotated[
            list[dict[str, Any]],
            Field(description="VisualizationSet dictionaries to combine."),
        ],
        name: Annotated[
            str | None,
            Field(
                description="Optional composed VisualizationSet identifier and display name."
            ),
        ] = None,
        units: Annotated[
            str | None,
            Field(
                description="Optional output units. If omitted, input units must match."
            ),
        ] = None,
        check_duplicate_geometry_ids: Annotated[
            bool, Field(description="Whether to check geometry identifier conflicts.")
        ] = True,
        conflict_strategy: Annotated[
            str,
            Field(
                description="Geometry identifier conflict strategy: error or rename."
            ),
        ] = "error",
    ) -> dict[str, Any]:
        """Compose VisualizationSet dictionaries into one VisualizationSet."""
        return service(
            visualization_sets=visualization_sets,
            name=name,
            units=units,
            check_duplicate_geometry_ids=check_duplicate_geometry_ids,
            conflict_strategy=conflict_strategy,
        )
