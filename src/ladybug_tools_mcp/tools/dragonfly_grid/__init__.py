"""Dragonfly Electric Grid tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.dragonfly_grid.create_electrical_connector import (
    register as register_create_electrical_connector,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_electrical_network import (
    register as register_create_electrical_network,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_financial_parameters import (
    register as register_create_financial_parameters,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_ground_photovoltaics import (
    register as register_create_ground_photovoltaics,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_road_network import (
    register as register_create_road_network,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_substation import (
    register as register_create_substation,
)
from ladybug_tools_mcp.tools.dragonfly_grid.create_transformer import (
    register as register_create_transformer,
)
from ladybug_tools_mcp.tools.dragonfly_grid.grid_network_to_visualization_set import (
    register as register_grid_network_to_visualization_set,
)
from ladybug_tools_mcp.tools.dragonfly_grid.grid_results_to_visualization_set import (
    register as register_grid_results_to_visualization_set,
)
from ladybug_tools_mcp.tools.dragonfly_grid.read_opendss_result import (
    register as register_read_opendss_result,
)
from ladybug_tools_mcp.tools.dragonfly_grid.search_opendss import (
    register as register_search_opendss,
)
from ladybug_tools_mcp.tools.dragonfly_grid.start_opendss import (
    register as register_start_opendss,
)
from ladybug_tools_mcp.tools.dragonfly_grid.start_reopt import (
    register as register_start_reopt,
)
from ladybug_tools_mcp.tools.dragonfly_grid.start_rnm import (
    register as register_start_rnm,
)


def register(mcp: FastMCP) -> None:
    """Register Dragonfly Electric Grid tools."""
    register_create_substation(mcp)
    register_create_transformer(mcp)
    register_create_electrical_connector(mcp)
    register_create_electrical_network(mcp)
    register_create_road_network(mcp)
    register_create_ground_photovoltaics(mcp)
    register_create_financial_parameters(mcp)
    register_search_opendss(mcp)
    register_start_rnm(mcp)
    register_start_opendss(mcp)
    register_read_opendss_result(mcp)
    register_start_reopt(mcp)
    register_grid_network_to_visualization_set(mcp)
    register_grid_results_to_visualization_set(mcp)
