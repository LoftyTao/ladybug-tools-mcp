"""Tool registry for the single Ladybug Tools MCP service."""

from fastmcp import FastMCP

from garden.fairyfly.availability import fairyfly_tools_enabled
from ladybug_tools_mcp.tools.config import register as register_config_tools
from ladybug_tools_mcp.tools.dragonfly_core import register as register_dragonfly_tools
from ladybug_tools_mcp.tools.energy import register as register_energy_tools
from ladybug_tools_mcp.tools.flowerpot import register as register_flowerpot_tools
from ladybug_tools_mcp.tools.garden import register as register_garden_tools
from ladybug_tools_mcp.tools.honeybee_core import register as register_honeybee_tools
from ladybug_tools_mcp.tools.ironbug_core import register as register_ironbug_tools
from ladybug_tools_mcp.tools.libraries import register as register_library_tools
from ladybug_tools_mcp.tools.radiance import register as register_radiance_tools
from ladybug_tools_mcp.tools.run_energy import register as register_run_energy_tools
from ladybug_tools_mcp.tools.run_uwg import register as register_run_uwg_tools
from ladybug_tools_mcp.tools.visualize import register as register_visualize_tools
from ladybug_tools_mcp.tools.web_view import register as register_web_view_tools
from ladybug_tools_mcp.tool_namespaces import mount_registered_family


def register_tools(mcp: FastMCP) -> FastMCP:
    """Register all public MCP tools on one FastMCP service."""
    mount_registered_family(mcp, family="config", register=register_config_tools)
    mount_registered_family(mcp, family="garden", register=register_garden_tools)
    mount_registered_family(mcp, family="flowerpot", register=register_flowerpot_tools)
    mount_registered_family(mcp, family="honeybee_core", register=register_honeybee_tools)
    mount_registered_family(mcp, family="ironbug_core", register=register_ironbug_tools)
    mount_registered_family(mcp, family="dragonfly_core", register=register_dragonfly_tools)
    mount_registered_family(mcp, family="energy", register=register_energy_tools)
    mount_registered_family(mcp, family="radiance", register=register_radiance_tools)
    mount_registered_family(mcp, family="run_energy", register=register_run_energy_tools)
    mount_registered_family(mcp, family="run_uwg", register=register_run_uwg_tools)
    mount_registered_family(mcp, family="libraries", register=register_library_tools)
    mount_registered_family(mcp, family="visualize", register=register_visualize_tools)
    mount_registered_family(mcp, family="web_view", register=register_web_view_tools)
    if fairyfly_tools_enabled():
        from ladybug_tools_mcp.tools.fairyfly import register as register_fairyfly_tools

        mount_registered_family(mcp, family="fairyfly", register=register_fairyfly_tools)
    return mcp
