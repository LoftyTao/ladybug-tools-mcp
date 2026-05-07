"""Short natural-language alias for Radiance GIF postprocess."""

from __future__ import annotations

from ladybug_tools_mcp.tools.radiance.create_radiance_gif import register as _register


def register(mcp):
    """Register create_gif as an alias."""
    original_tool = mcp.tool

    def tool_with_alias(*args, **kwargs):
        kwargs["name"] = "create_gif"
        return original_tool(*args, **kwargs)

    mcp.tool = tool_with_alias
    try:
        _register(mcp)
    finally:
        mcp.tool = original_tool
