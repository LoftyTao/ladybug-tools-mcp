"""Ladybug Tools configuration tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.config.get_ladybug_tools_config import (
    register as register_get_ladybug_tools_config,
)


def register(mcp: FastMCP) -> None:
    """Register Ladybug Tools configuration tools."""
    register_get_ladybug_tools_config(mcp)
