"""Stop Web View Mode MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.url_fallback import stop_preview_url_fallback
from web_view.session import stop_web_view_session


def register(mcp: FastMCP) -> None:
    'Register the web_view_stop_mode tool.'

    @mcp.tool(
        name="stop_mode",
        description=(
            "Stop Garden Web View Mode by marking the FastMCP App preview session "
            "inactive. Code Mode stops exporting automatic session-managed vtk.js "
            "previews for the Garden after this call. Returns session, "
            "session_path, summary_view, and viewer status. It does not delete "
            "preview history, remove Garden visualization artifacts, or close a "
            "host App panel. If a local fallback URL was started for a host "
            "without MCP Apps UI support, this call also stops that local URL."
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
    )
    def stop_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")],
    ) -> dict[str, Any]:
        """Disable Web View Mode for a Garden."""
        result = stop_web_view_session(garden_root=garden_root)
        result["url_fallback"] = stop_preview_url_fallback(garden_root=garden_root)
        result["viewer"] = {
            "status": "stopped",
            "ui": "FastMCP App",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
        }
        return result
