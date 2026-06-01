"""Start Web View Mode as a FastMCP Custom HTML App."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP, UI_EXTENSION_ID
from fastmcp.server.context import Context
from fastmcp.tools import ToolResult
from mcp import types
from pydantic import Field

from web_view.app import (
    APP_RESOURCE_DOMAINS,
    UNMOUNTED_VIEW_RESOURCE_URI,
    VIEW_RESOURCE_URI,
    app_meta,
    start_preview_app_session,
    viewer_html,
)
from web_view.url_fallback import start_preview_url_fallback


def _app_config() -> AppConfig:
    return AppConfig(
        resource_uri=VIEW_RESOURCE_URI,
        csp=ResourceCSP(resource_domains=list(APP_RESOURCE_DOMAINS)),
        prefers_border=True,
    )


def register(mcp: FastMCP) -> None:
    """Register the web_view_start_mode tool and its App resource."""

    @mcp.resource(
        UNMOUNTED_VIEW_RESOURCE_URI,
        name="ladybug-tools-vtkjs-preview",
        description="FastMCP Custom HTML App resource for Garden vtk.js previews.",
        app=AppConfig(csp=ResourceCSP(resource_domains=list(APP_RESOURCE_DOMAINS))),
    )
    def vtkjs_preview_view() -> str:
        """Return the Web View Mode HTML resource."""
        return viewer_html()

    @mcp.tool(
        name="start_mode",
        description=(
            "Start Garden Web View Mode as a FastMCP Custom HTML App for vtk.js "
            "previewing. In Code Mode, significant Honeybee, Dragonfly, Fairyfly, "
            "and VisualizationSet edits can keep exporting session-managed vtk.js "
            "previews while ordinary tool return values stay unchanged. Returns "
            "session, session_path, summary_view, app, viewer, and Garden handoff "
            "metadata for the host App, including whether the MCP client "
            "advertises the Apps UI extension. This opens an interactive MCP App "
            "in hosts that support that extension. When the host does not "
            "advertise the extension, the result also includes a local-only "
            "fallback viewer URL so Codex and other Agents can open the same "
            "Garden-backed vtk.js preview without maintaining an extra "
            "frontend project runtime. Use the persistent .vtkjs artifact "
            "exporter when a reusable Web 3D asset is the requested output."
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
        app=_app_config(),
        meta=app_meta(),
    )
    def start_web_view_mode(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")],
        name: Annotated[
            str,
            Field(description="Human-readable Web View session name for summary_view and the FastMCP App title."),
        ] = "Code Mode vtk.js Preview",
        preview_kinds: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional preview kinds to record for this Garden session, such "
                    "as object_edit, base_honeybee_model, base_dragonfly_model, "
                    "search_highlight, or analysis_overlay."
                )
            ),
        ] = None,
        ctx: Context = None,  # type: ignore[assignment]
    ) -> ToolResult:
        """Enable Web View Mode for a Garden and return the FastMCP App payload."""
        result = start_preview_app_session(
            garden_root=garden_root,
            name=name,
            preview_kinds=preview_kinds,
        )
        client_supports_ui = (
            bool(ctx.client_supports_extension(UI_EXTENSION_ID)) if ctx is not None else None
        )
        result["app"]["client_supports_ui_extension"] = client_supports_ui
        result["summary_view"]["client_supports_ui_extension"] = client_supports_ui
        if client_supports_ui is False:
            fallback = start_preview_url_fallback(garden_root=garden_root, name=name)
            result["viewer"]["url"] = fallback["url"]
            result["viewer"]["url_fallback"] = fallback
            result["summary_view"]["fallback_viewer_url"] = fallback["url"]
            result["summary_view"]["viewer_url"] = fallback["url"]
            message = (
                "FastMCP vtk.js preview session is ready, but this MCP client "
                "does not advertise the Apps UI extension, so it will not render "
                "the App iframe. Open the returned local fallback URL to view "
                "the same Garden preview."
            )
        else:
            message = "FastMCP vtk.js preview App is ready for this Garden."
        return ToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=message,
                )
            ],
            structured_content=result,
            meta=app_meta(),
        )
