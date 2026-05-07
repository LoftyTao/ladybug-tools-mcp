"""Natural-language alias for listing Radiance run HDR images."""

from __future__ import annotations

from ladybug_tools_mcp.tools.radiance.list_radiance_hdr_images import register as _register


def register(mcp):
    """Register get_radiance_run_hdr_images as an alias."""
    original_tool = mcp.tool

    def tool_with_alias(*args, **kwargs):
        kwargs["name"] = "get_radiance_run_hdr_images"
        return original_tool(*args, **kwargs)

    mcp.tool = tool_with_alias
    try:
        _register(mcp)
    finally:
        mcp.tool = original_tool
