"""Stop Web View Mode MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.runtime import stop_web_view_runtime
from web_view.session import stop_web_view_session


def register(mcp: FastMCP) -> None:
    """Register the stop_web_view_mode tool."""

    @mcp.tool(
        name="stop_web_view_mode",
        description=(
            "Disable Garden-local Web View Mode and stop its local Web View "
            "server without deleting preview history. Code Mode stops exporting "
            "automatic vtk.js previews for the Garden after this call."
        ),
        tags={"web-view", "garden-mode", "preview", "write", "safe"},
        timeout=20,
    )
    def stop_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
    ) -> dict[str, Any]:
        """Disable Web View Mode for a Garden."""
        viewer = stop_web_view_runtime(garden_root=garden_root)
        result = stop_web_view_session(garden_root=garden_root)
        result["viewer"] = viewer or {"status": "not_running"}
        return result
