"""Fairyfly MCP tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.fairyfly.add_fairyfly_boundary_to_model import (
    register as register_add_fairyfly_boundary_to_model,
)
from ladybug_tools_mcp.tools.fairyfly.add_fairyfly_shape_to_model import (
    register as register_add_fairyfly_shape_to_model,
)
from ladybug_tools_mcp.tools.fairyfly.create_fairyfly_model import (
    register as register_create_fairyfly_model,
)
from ladybug_tools_mcp.tools.fairyfly.create_fairyfly_solid_material import (
    register as register_create_fairyfly_solid_material,
)
from ladybug_tools_mcp.tools.fairyfly.fairyfly_model_to_visualization_set import (
    register as register_fairyfly_model_to_visualization_set,
)
from ladybug_tools_mcp.tools.fairyfly.fairyfly_therm_result_to_visualization_set import (
    register as register_fairyfly_therm_result_to_visualization_set,
)
from ladybug_tools_mcp.tools.fairyfly.get_base_fairyfly_model import (
    register as register_get_base_fairyfly_model,
)
from ladybug_tools_mcp.tools.fairyfly.get_fairyfly_therm_run import (
    register as register_get_fairyfly_therm_run,
)
from ladybug_tools_mcp.tools.fairyfly.list_fairyfly_therm_runs import (
    register as register_list_fairyfly_therm_runs,
)
from ladybug_tools_mcp.tools.fairyfly.read_fairyfly_therm_result import (
    register as register_read_fairyfly_therm_result,
)
from ladybug_tools_mcp.tools.fairyfly.read_fairyfly_u_factor_result import (
    register as register_read_fairyfly_u_factor_result,
)
from ladybug_tools_mcp.tools.fairyfly.set_base_fairyfly_model import (
    register as register_set_base_fairyfly_model,
)
from ladybug_tools_mcp.tools.fairyfly.start_fairyfly_therm_run import (
    register as register_start_fairyfly_therm_run,
)
from ladybug_tools_mcp.tools.fairyfly.validate_fairyfly_model import (
    register as register_validate_fairyfly_model,
)
from ladybug_tools_mcp.tools.fairyfly.write_fairyfly_model_to_thmz import (
    register as register_write_fairyfly_model_to_thmz,
)


def register(mcp: FastMCP) -> None:
    """Register Fairyfly tools."""
    register_set_base_fairyfly_model(mcp)
    register_get_base_fairyfly_model(mcp)
    register_create_fairyfly_model(mcp)
    register_create_fairyfly_solid_material(mcp)
    register_add_fairyfly_shape_to_model(mcp)
    register_add_fairyfly_boundary_to_model(mcp)
    register_validate_fairyfly_model(mcp)
    register_fairyfly_model_to_visualization_set(mcp)
    register_fairyfly_therm_result_to_visualization_set(mcp)
    register_write_fairyfly_model_to_thmz(mcp)
    register_start_fairyfly_therm_run(mcp)
    register_get_fairyfly_therm_run(mcp)
    register_list_fairyfly_therm_runs(mcp)
    register_read_fairyfly_therm_result(mcp)
    register_read_fairyfly_u_factor_result(mcp)
