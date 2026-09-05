"""Tool registry for the single Ladybug Tools MCP service."""

from importlib import import_module

from fastmcp import FastMCP

from garden.fairyfly.availability import fairyfly_tools_enabled


_TOOL_FAMILIES = (
    "config",
    "garden",
    "flowerpot",
    "honeybee_core",
    "ironbug_core",
    "dragonfly_core",
    "dragonfly_grid",
    "des",
    "energy",
    "radiance",
    "run_energy",
    "run_urbanopt",
    "run_uwg",
    "libraries",
    "comfort",
    "visualize",
    "web_view",
    "fairyfly",
)


def register_tools(mcp: FastMCP) -> FastMCP:
    """Register all public MCP tools on one FastMCP service."""
    for family in _TOOL_FAMILIES:
        if family == "fairyfly" and not fairyfly_tools_enabled():
            continue
        module = import_module(f"ladybug_tools_mcp.tools.{family}")
        module.register(mcp)
    return mcp
