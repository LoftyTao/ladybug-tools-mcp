"""FastMCP App backend tool for vtk.js preview state."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.apps import AppConfig
from pydantic import Field

from web_view.app import PREVIEW_STATE_TOOL, app_meta, read_preview_state


def register(mcp: FastMCP) -> None:
    """Register the App-only preview_state tool."""

    @mcp.tool(
        name="preview_state",
        description=(
            "App-only backend for the FastMCP vtk.js preview. Returns compact "
            "Garden Web View state, active session step, current artifact "
            "metadata, summary_view-style report, and polling interval for the "
            "iframe; use web_view_start_mode to open the user-facing App."
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
        app=AppConfig(visibility=["app"]),
        meta=app_meta(PREVIEW_STATE_TOOL),
    )
    def preview_state(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")],
    ) -> dict[str, Any]:
        """Return current FastMCP App preview state for one Garden."""
        return read_preview_state(garden_root=garden_root)
