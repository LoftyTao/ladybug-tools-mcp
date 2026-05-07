"""Garden Properties Library tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.libraries.get_garden_properties_library_object import (
    register as register_get_garden_properties_library_object,
)
from ladybug_tools_mcp.tools.libraries.normalize_garden_properties_library_storage import (
    register as register_normalize_garden_properties_library_storage,
)
from ladybug_tools_mcp.tools.libraries.save_garden_properties_library_object import (
    register as register_save_garden_properties_library_object,
)
from ladybug_tools_mcp.tools.libraries.search_garden_properties_library import (
    register as register_search_garden_properties_library,
)
from ladybug_tools_mcp.tools.libraries.search_garden_properties_library_objects import (
    register as register_search_garden_properties_library_objects,
)


def register(mcp: FastMCP) -> None:
    """Register Garden Properties Library tools."""
    register_save_garden_properties_library_object(mcp)
    register_get_garden_properties_library_object(mcp)
    register_normalize_garden_properties_library_storage(mcp)
    register_search_garden_properties_library(mcp)
    register_search_garden_properties_library_objects(mcp)
