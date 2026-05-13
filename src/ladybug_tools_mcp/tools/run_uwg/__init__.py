"""UWG Alternative Weather tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.run_uwg.apply_dragonfly_uwg_properties import (
    register as register_apply_dragonfly_uwg_properties,
)
from ladybug_tools_mcp.tools.run_uwg.create_uwg_simulation_parameter import (
    register as register_create_uwg_simulation_parameter,
)
from ladybug_tools_mcp.tools.run_uwg.dragonfly_model_to_uwg import (
    register as register_dragonfly_model_to_uwg,
)
from ladybug_tools_mcp.tools.run_uwg.get_dragonfly_uwg_properties_summary import (
    register as register_get_dragonfly_uwg_properties_summary,
)
from ladybug_tools_mcp.tools.run_uwg.get_uwg_run import (
    register as register_get_uwg_run,
)
from ladybug_tools_mcp.tools.run_uwg.list_uwg_run_outputs import (
    register as register_list_uwg_run_outputs,
)
from ladybug_tools_mcp.tools.run_uwg.list_uwg_runs import (
    register as register_list_uwg_runs,
)
from ladybug_tools_mcp.tools.run_uwg.run_uwg import register as register_run_uwg
from ladybug_tools_mcp.tools.run_uwg.start_uwg_run import (
    register as register_start_uwg_run,
)


def register(mcp: FastMCP) -> None:
    """Register UWG Alternative Weather tools."""
    register_get_dragonfly_uwg_properties_summary(mcp)
    register_apply_dragonfly_uwg_properties(mcp)
    register_create_uwg_simulation_parameter(mcp)
    register_dragonfly_model_to_uwg(mcp)
    register_start_uwg_run(mcp)
    register_run_uwg(mcp)
    register_list_uwg_runs(mcp)
    register_get_uwg_run(mcp)
    register_list_uwg_run_outputs(mcp)
