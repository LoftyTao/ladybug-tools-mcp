"""Stop Web View Mode MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.runtime import stop_web_view_runtime
from web_view.session import stop_web_view_session


def register(mcp: FastMCP) -> None:
    'Register the web_view_stop_mode tool.'

    @mcp.tool(
        name="stop_mode",
        description=(
            "Stop Garden-local Web View Mode by marking the local preview session "
            "inactive and stopping its viewer server and watcher. Code Mode stops "
            "exporting automatic session-managed vtk.js previews for the Garden "
            "after this call. Returns session, session_path, summary_view, and "
            "viewer runtime status. It does not delete preview history, remove "
            "Garden visualization artifacts, or close a browser tab."
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
        viewer = stop_web_view_runtime(garden_root=garden_root)
        result = stop_web_view_session(garden_root=garden_root)
        result["viewer"] = viewer or {"status": "not_running"}
        return result
