"""Start the local Web View sidebar viewer."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.session import start_web_view_session
from web_view.url_fallback import start_preview_url_fallback


def register(mcp: FastMCP) -> None:
    """Register the Garden-local Web View entry tool."""

    @mcp.tool(
        name="GD_web_view_start_mode",
        description=(
            "Start the Garden-local vtk.js Web View sidebar viewer and return its "
            "127.0.0.1 URL. Significant Honeybee, Dragonfly, Fairyfly, and "
            "VisualizationSet edits in Code Mode automatically record session "
            "previews; the viewer silently polls them and preserves its camera."
        ),
        tags={"preview", "vtkjs", "web-view"},
        timeout=20,
    )
    def start_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_create['garden_root'].")],
        name: Annotated[str, Field(description="Human-readable viewer session name.")] = "Code Mode vtk.js Preview",
        preview_kinds: Annotated[
            list[str] | None,
            Field(description="Optional preview kinds such as object_edit, base_honeybee_model, base_dragonfly_model, search_highlight, or analysis_overlay."),
        ] = None,
    ) -> dict[str, Any]:
        """Enable local Web View Mode and return the sidebar viewer URL."""
        result = start_web_view_session(
            garden_root=garden_root,
            name=name,
            preview_kinds=preview_kinds,
        )
        viewer = start_preview_url_fallback(garden_root=garden_root, name=name)
        result["viewer"] = viewer
        result["summary_view"]["viewer_url"] = viewer["url"]
        return result
