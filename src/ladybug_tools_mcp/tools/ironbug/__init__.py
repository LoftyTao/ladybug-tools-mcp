"""Ironbug DetailedHVAC MCP tools backed by official C# Ironbug.HVAC."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools._registration import register_discovered_tools


def register(mcp: FastMCP) -> None:
    """Register the 8 Ironbug MCP tools."""
    register_discovered_tools(mcp, __name__)
