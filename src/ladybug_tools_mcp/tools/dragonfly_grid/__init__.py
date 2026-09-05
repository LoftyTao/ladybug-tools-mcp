"""Dragonfly Electric Grid tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools._registration import register_discovered_tools


def register(mcp: FastMCP) -> None:
    """Register Dragonfly Electric Grid tools."""
    register_discovered_tools(mcp, __name__)
