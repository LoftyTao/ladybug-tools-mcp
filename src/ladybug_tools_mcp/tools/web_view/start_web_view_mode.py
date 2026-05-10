"""Start Web View Mode MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.runtime import DEFAULT_WEB_VIEW_PORT, start_web_view_runtime


def register(mcp: FastMCP) -> None:
    """Register the start_web_view_mode tool."""

    @mcp.tool(
        name="start_web_view_mode",
        description=(
            "Enable Garden-local Web View Mode and start its local React + vtk.js "
            "preview server. In Code Mode, significant Honeybee edits automatically "
            "export session-managed vtk.js previews while ordinary tool return "
            "values stay unchanged. Returns the local viewer URL for the host app "
            "to open in a side-panel browser."
        ),
        tags={"web-view", "garden-mode", "preview", "write", "safe"},
        timeout=20,
    )
    def start_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root directory.")],
        name: Annotated[
            str,
            Field(description="Human-readable local Web View session name."),
        ] = "Code Mode Web View",
        host: Annotated[
            str,
            Field(description="Local host interface for the Web View server."),
        ] = "127.0.0.1",
        port: Annotated[
            int,
            Field(
                description=(
                    "Local Web View server port. Use 0 only in tests to request an "
                    "ephemeral port; production/demo mode should use an explicit port."
                ),
                ge=0,
                le=65535,
            ),
        ] = DEFAULT_WEB_VIEW_PORT,
        output_dir: Annotated[
            str | None,
            Field(
                description=(
                    "Optional viewer workspace directory. Defaults to the Garden "
                    "tmp/web_view/viewer directory."
                )
            ),
        ] = None,
        watch_interval_seconds: Annotated[
            float,
            Field(description="Garden preview watcher interval in seconds.", gt=0),
        ] = 0.5,
    ) -> dict[str, Any]:
        """Enable Web View Mode and serve its local viewer for a Garden."""
        return start_web_view_runtime(
            garden_root=garden_root,
            name=name,
            host=host,
            port=port,
            output_dir=output_dir,
            watch_interval_seconds=watch_interval_seconds,
        )
