"""Web View Mode tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.web_view.preview_artifact import (
    register as register_preview_artifact,
)
from ladybug_tools_mcp.tools.web_view.preview_state import (
    register as register_preview_state,
)
from ladybug_tools_mcp.tools.web_view.start_web_view_mode import (
    register as register_start_web_view_mode,
)
from ladybug_tools_mcp.tools.web_view.stop_web_view_mode import (
    register as register_stop_web_view_mode,
)


def register(mcp: FastMCP) -> None:
    """Register Web View Mode tools."""
    register_start_web_view_mode(mcp)
    register_preview_state(mcp)
    register_preview_artifact(mcp)
    register_stop_web_view_mode(mcp)
