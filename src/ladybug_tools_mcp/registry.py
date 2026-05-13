"""Tool registry for the single Ladybug Tools MCP service."""

from fastmcp import FastMCP

from garden.fairyfly.availability import fairyfly_tools_enabled
from ladybug_tools_mcp.tools.config import register as register_config_tools
from ladybug_tools_mcp.tools.dragonfly_core import register as register_dragonfly_tools
from ladybug_tools_mcp.tools.energy import register as register_energy_tools
from ladybug_tools_mcp.tools.flowerpot import register as register_flowerpot_tools
from ladybug_tools_mcp.tools.garden import register as register_garden_tools
from ladybug_tools_mcp.tools.honeybee_core import register as register_honeybee_tools
from ladybug_tools_mcp.tools.libraries import register as register_library_tools
from ladybug_tools_mcp.tools.radiance import register as register_radiance_tools
from ladybug_tools_mcp.tools.run_energy import register as register_run_energy_tools
from ladybug_tools_mcp.tools.run_uwg import register as register_run_uwg_tools
from ladybug_tools_mcp.tools.visualize import register as register_visualize_tools
from ladybug_tools_mcp.tools.web_view import register as register_web_view_tools


def register_tools(mcp: FastMCP) -> FastMCP:
    """Register all public MCP tools on one FastMCP service."""
    register_config_tools(mcp)
    register_garden_tools(mcp)
    register_flowerpot_tools(mcp)
    register_honeybee_tools(mcp)
    register_dragonfly_tools(mcp)
    register_energy_tools(mcp)
    register_radiance_tools(mcp)
    register_run_energy_tools(mcp)
    register_run_uwg_tools(mcp)
    register_library_tools(mcp)
    register_visualize_tools(mcp)
    register_web_view_tools(mcp)
    if fairyfly_tools_enabled():
        from ladybug_tools_mcp.tools.fairyfly import register as register_fairyfly_tools

        register_fairyfly_tools(mcp)
    return mcp
