"""Flowerpot tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.flowerpot.cleanup_flowerpots import (
    register as register_cleanup_flowerpots,
)
from ladybug_tools_mcp.tools.flowerpot.create_flowerpot import (
    register as register_create_flowerpot,
)
from ladybug_tools_mcp.tools.flowerpot.get_flowerpot import (
    register as register_get_flowerpot,
)
from ladybug_tools_mcp.tools.flowerpot.get_active_flowerpot_context import (
    register as register_get_active_flowerpot_context,
)


def register(mcp: FastMCP) -> None:
    """Register Flowerpot tools."""
    register_create_flowerpot(mcp)
    register_get_flowerpot(mcp)
    register_get_active_flowerpot_context(mcp)
    register_cleanup_flowerpots(mcp)
