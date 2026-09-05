"""UWG Alternative Weather tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools._registration import register_discovered_tools


def register(mcp: FastMCP) -> None:
    """Register UWG Alternative Weather tools."""
    register_discovered_tools(mcp, __name__)
