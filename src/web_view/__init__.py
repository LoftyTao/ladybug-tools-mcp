"""FastMCP App Web View support for Garden-backed previews."""

from web_view.app import (
    APP_NAME,
    POLL_INTERVAL_MS,
    PREVIEW_ARTIFACT_TOOL,
    PREVIEW_STATE_TOOL,
    UNMOUNTED_VIEW_RESOURCE_URI,
    VIEW_RESOURCE_URI,
    app_backend_tool_name,
    app_meta,
    app_tool_hash,
    read_preview_artifact,
    read_preview_state,
    start_preview_app_session,
    viewer_html,
)
from web_view.url_fallback import (
    fallback_viewer_html,
    start_preview_url_fallback,
    stop_preview_url_fallback,
)
from web_view.session import (
    SUPPORTED_PREVIEW_KINDS,
    get_web_view_config,
    read_web_view_session,
    record_preview_failure,
    record_preview_file_step,
    record_preview_step,
    start_web_view_session,
    stop_web_view_session,
)

__all__ = [
    "APP_NAME",
    "POLL_INTERVAL_MS",
    "PREVIEW_ARTIFACT_TOOL",
    "PREVIEW_STATE_TOOL",
    "SUPPORTED_PREVIEW_KINDS",
    "UNMOUNTED_VIEW_RESOURCE_URI",
    "VIEW_RESOURCE_URI",
    "app_backend_tool_name",
    "app_meta",
    "app_tool_hash",
    "get_web_view_config",
    "read_preview_artifact",
    "read_preview_state",
    "read_web_view_session",
    "record_preview_failure",
    "record_preview_file_step",
    "record_preview_step",
    "fallback_viewer_html",
    "start_preview_url_fallback",
    "start_preview_app_session",
    "start_web_view_session",
    "stop_preview_url_fallback",
    "stop_web_view_session",
    "viewer_html",
]
