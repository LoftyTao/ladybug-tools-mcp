"""URBANopt Energy tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.run_urbanopt.list_run_outputs import (
    register as register_list_run_outputs,
)
from ladybug_tools_mcp.tools.run_urbanopt.poll_simulation import (
    register as register_poll_simulation,
)
from ladybug_tools_mcp.tools.run_urbanopt.prepare_project import (
    register as register_prepare_project,
)
from ladybug_tools_mcp.tools.run_urbanopt.start_simulation import (
    register as register_start_simulation,
)


def register(mcp: FastMCP) -> None:
    """Register URBANopt Energy tools."""
    register_prepare_project(mcp)
    register_start_simulation(mcp)
    register_poll_simulation(mcp)
    register_list_run_outputs(mcp)
