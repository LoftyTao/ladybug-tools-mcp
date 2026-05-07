"""Garden tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.garden.cleanup_garden_workspace import (
    register as register_cleanup_garden_workspace,
)
from ladybug_tools_mcp.tools.garden.create_garden import (
    register as register_create_garden,
)
from ladybug_tools_mcp.tools.garden.create_garden_version import (
    register as register_create_garden_version,
)
from ladybug_tools_mcp.tools.garden.get_garden_version_status import (
    register as register_get_garden_version_status,
)
from ladybug_tools_mcp.tools.garden.get_garden import (
    register as register_get_garden,
)
from ladybug_tools_mcp.tools.garden.get_base_model import (
    register as register_get_base_model,
)
from ladybug_tools_mcp.tools.garden.get_honeybee_model import (
    register as register_get_honeybee_model,
)
from ladybug_tools_mcp.tools.garden.list_garden_artifacts import (
    register as register_list_garden_artifacts,
)
from ladybug_tools_mcp.tools.garden.list_garden_files import (
    register as register_list_garden_files,
)
from ladybug_tools_mcp.tools.garden.list_garden_models import (
    register as register_list_garden_models,
)
from ladybug_tools_mcp.tools.garden.list_gardens import (
    register as register_list_gardens,
)
from ladybug_tools_mcp.tools.garden.list_garden_versions import (
    register as register_list_garden_versions,
)
from ladybug_tools_mcp.tools.garden.restore_garden_version import (
    register as register_restore_garden_version,
)
from ladybug_tools_mcp.tools.garden.save_base_model import (
    register as register_save_base_model,
)
from ladybug_tools_mcp.tools.garden.search_honeybee_models import (
    register as register_search_honeybee_models,
)
from ladybug_tools_mcp.tools.garden.search_garden_artifacts import (
    register as register_search_garden_artifacts,
)
from ladybug_tools_mcp.tools.garden.search_garden_objects import (
    register as register_search_garden_objects,
)
from ladybug_tools_mcp.tools.garden.set_base_model import (
    register as register_set_base_model,
)


def register(mcp: FastMCP) -> None:
    """Register Garden tools."""
    register_create_garden(mcp)
    register_get_garden(mcp)
    register_get_garden_version_status(mcp)
    register_create_garden_version(mcp)
    register_list_garden_versions(mcp)
    register_restore_garden_version(mcp)
    register_cleanup_garden_workspace(mcp)
    register_list_gardens(mcp)
    register_list_garden_models(mcp)
    register_search_honeybee_models(mcp)
    register_set_base_model(mcp)
    register_get_base_model(mcp)
    register_get_honeybee_model(mcp)
    register_save_base_model(mcp)
    register_list_garden_artifacts(mcp)
    register_search_garden_artifacts(mcp)
    register_search_garden_objects(mcp)
    register_list_garden_files(mcp)
