"""Start Web View Mode MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from web_view.runtime import DEFAULT_WEB_VIEW_PORT, start_web_view_runtime


def register(mcp: FastMCP) -> None:
    'Register the web_view_start_mode tool.'

    @mcp.tool(
        name="start_mode",
        description=(
            "Start Garden-local Web View Mode: a local React + vtk.js preview "
            "session, viewer server, and Garden watcher for side-panel viewing. In "
            "Code Mode, significant Honeybee edits can export session-managed "
            "vtk.js previews while ordinary tool return values stay unchanged. "
            "Returns session, session_path, summary_view, viewer, and workspace "
            "with viewer.url for the host app to open. This is not browser "
            "automation and does not create formal saved Garden viewer artifacts; "
            "use the persistent .vtkjs artifact exporter when a reusable Web 3D "
            "asset is the requested output."
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
    )
    def start_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")],
        name: Annotated[
            str,
            Field(description="Human-readable local Web View session name for summary_view and viewer title."),
        ] = "Code Mode Web View",
        host: Annotated[
            str,
            Field(description="Local host interface for the Web View server, usually 127.0.0.1."),
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
                    "Optional viewer workspace directory for generated React/vtk.js "
                    "preview files. Defaults to the Garden tmp/web_view/viewer "
                    "directory."
                )
            ),
        ] = None,
        watch_interval_seconds: Annotated[
            float,
            Field(description="Garden preview watcher interval in seconds for Web View Mode.", gt=0),
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
