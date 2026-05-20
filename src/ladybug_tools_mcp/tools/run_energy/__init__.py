"""Energy simulation tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.run_energy.download_epw import (
    register as register_download_epw,
)
from ladybug_tools_mcp.tools.run_energy.create_energy_output_request import (
    register as register_create_energy_output_request,
)
from ladybug_tools_mcp.tools.run_energy.energy_result_hourly_plot_to_html import (
    register as register_energy_result_hourly_plot_to_html,
)
from ladybug_tools_mcp.tools.run_energy.energy_result_monthly_chart_to_html import (
    register as register_energy_result_monthly_chart_to_html,
)
from ladybug_tools_mcp.tools.run_energy.get_energy_run import (
    register as register_get_energy_run,
)
from ladybug_tools_mcp.tools.run_energy.list_energy_run_outputs import (
    register as register_list_energy_run_outputs,
)
from ladybug_tools_mcp.tools.run_energy.list_energy_runs import (
    register as register_list_energy_runs,
)
from ladybug_tools_mcp.tools.run_energy.read_energy_errors import (
    register as register_read_energy_errors,
)
from ladybug_tools_mcp.tools.run_energy.read_energy_eui import (
    register as register_read_energy_eui,
)
from ladybug_tools_mcp.tools.run_energy.read_energy_result_data import (
    register as register_read_energy_result_data,
)
from ladybug_tools_mcp.tools.run_energy.read_weather_file_data import (
    register as register_read_weather_file_data,
)
from ladybug_tools_mcp.tools.run_energy.run_energy import (
    register as register_run_energy,
)
from ladybug_tools_mcp.tools.run_energy.run_idf_file import (
    register as register_run_idf_file,
)
from ladybug_tools_mcp.tools.run_energy.run_osm_file import (
    register as register_run_osm_file,
)
from ladybug_tools_mcp.tools.run_energy.search_epw_map import (
    register as register_search_epw_map,
)
from ladybug_tools_mcp.tools.run_energy.search_weather_files import (
    register as register_search_weather_files,
)
from ladybug_tools_mcp.tools.run_energy.start_energy_run import (
    register as register_start_energy_run,
)


def register(mcp: FastMCP) -> None:
    """Register Energy simulation tools."""
    register_search_epw_map(mcp)
    register_download_epw(mcp)
    register_search_weather_files(mcp)
    register_create_energy_output_request(mcp)
    register_start_energy_run(mcp)
    register_run_energy(mcp)
    register_run_osm_file(mcp)
    register_run_idf_file(mcp)
    register_list_energy_runs(mcp)
    register_get_energy_run(mcp)
    register_list_energy_run_outputs(mcp)
    register_read_energy_eui(mcp)
    register_read_energy_errors(mcp)
    register_read_energy_result_data(mcp)
    register_read_weather_file_data(mcp)
    register_energy_result_hourly_plot_to_html(mcp)
    register_energy_result_monthly_chart_to_html(mcp)
