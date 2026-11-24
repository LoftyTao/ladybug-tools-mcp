"""web_view MCP tools."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import ToolResultModel, validate_output
from web_view import (
    start_preview_url_fallback,
    start_web_view_session,
    stop_preview_url_fallback,
    stop_web_view_session,
)


def register(mcp: FastMCP) -> None:
    """Register web_view tools."""

    @mcp.tool(
        name="GD_Web_View_Start_Mode",
        description=(
            "Start the Garden-local offline vtk.js Web View workbench and return its "
            "127.0.0.1 URL. Pass optional port (1-65535) to bind an explicit port (failing "
            "clearly if occupied) or omit port to bind an ephemeral port. Significant Honeybee, "
            "Dragonfly, Fairyfly, and VisualizationSet edits in Code Mode automatically record "
            "session previews; the viewer silently polls them and preserves its camera."
        ),
        tags={"preview", "vtkjs", "web-view"},
        timeout=20,
    )
    def start_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        name: Annotated[
            str,
            Field(description="Human-readable viewer session name."),
        ] = "Code Mode vtk.js Preview",
        preview_kinds: Annotated[
            list[
                Literal[
                    "base_honeybee_model",
                    "base_dragonfly_model",
                    "object_edit",
                    "search_highlight",
                    "analysis_overlay",
                ]
            ]
            | None,
            Field(
                description="Optional preview kinds such as object_edit, base_honeybee_model, base_dragonfly_model, search_highlight, or analysis_overlay."
            ),
        ] = None,
        port: Annotated[
            int | None,
            Field(
                description="Optional local loopback port (1-65535). When omitted, binds an ephemeral port; when specified and already occupied, raises a port conflict error.",
                ge=1,
                le=65535,
            ),
        ] = None,
    ) -> ToolResultModel:
        """Enable local Web View Mode and return the sidebar viewer URL."""
        viewer = start_preview_url_fallback(garden_root=garden_root, name=name, port=port)
        result = start_web_view_session(
            garden_root=garden_root,
            name=name,
            preview_kinds=preview_kinds,
        )
        result["viewer"] = viewer
        result["summary_view"]["viewer_url"] = viewer["url"]
        result["summary_view"]["viewer_port"] = viewer["port"]
        return validate_output(ToolResultModel, result)

    @mcp.tool(
        name="GD_Web_View_Stop_Mode",
        description=(
            'Stop Garden Web View Mode by marking the local preview session inactive. Code Mode '
            'stops exporting automatic session-managed vtk.js previews for the Garden after this '
            'call. Returns session, session_path, summary_view, and viewer status. If a local '
            'fallback URL was started for a host without MCP Apps UI support, this call also '
            'stops that local URL.'
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
    )
    def stop_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
    ) -> ToolResultModel:
        """Disable Web View Mode for a Garden."""
        result = stop_web_view_session(garden_root=garden_root)
        result["url_fallback"] = stop_preview_url_fallback(garden_root=garden_root)
        result["viewer"] = {
            "status": "stopped",
            "ui": "Local sidebar viewer",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
        }
        return validate_output(ToolResultModel, result)
