"""Dragonfly DES tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.des.assign_building_loads import (
    register as register_assign_building_loads,
)
from ladybug_tools_mcp.tools.des.create_fifth_gen_thermal_loop import (
    register as register_create_fifth_gen_thermal_loop,
)
from ladybug_tools_mcp.tools.des.create_fourth_gen_thermal_loop import (
    register as register_create_fourth_gen_thermal_loop,
)
from ladybug_tools_mcp.tools.des.create_ghe_borehole_parameter import (
    register as register_create_ghe_borehole_parameter,
)
from ladybug_tools_mcp.tools.des.create_ghe_design_parameter import (
    register as register_create_ghe_design_parameter,
)
from ladybug_tools_mcp.tools.des.create_ghe_fluid_parameter import (
    register as register_create_ghe_fluid_parameter,
)
from ladybug_tools_mcp.tools.des.create_ghe_pipe_parameter import (
    register as register_create_ghe_pipe_parameter,
)
from ladybug_tools_mcp.tools.des.create_ghe_soil_parameter import (
    register as register_create_ghe_soil_parameter,
)
from ladybug_tools_mcp.tools.des.create_ghe_thermal_loop import (
    register as register_create_ghe_thermal_loop,
)
from ladybug_tools_mcp.tools.des.create_ground_heat_exchanger import (
    register as register_create_ground_heat_exchanger,
)
from ladybug_tools_mcp.tools.des.create_horizontal_pipe_parameter import (
    register as register_create_horizontal_pipe_parameter,
)
from ladybug_tools_mcp.tools.des.create_thermal_connector import (
    register as register_create_thermal_connector,
)
from ladybug_tools_mcp.tools.des.export_model_to_des import (
    register as register_export_model_to_des,
)
from ladybug_tools_mcp.tools.des.export_urbanopt_model import (
    register as register_export_urbanopt_model,
)
from ladybug_tools_mcp.tools.des.list_urbanopt_run_outputs import (
    register as register_list_urbanopt_run_outputs,
)
from ladybug_tools_mcp.tools.des.poll_modelica_simulation import (
    register as register_poll_modelica_simulation,
)
from ladybug_tools_mcp.tools.des.poll_sys_param import (
    register as register_poll_sys_param,
)
from ladybug_tools_mcp.tools.des.poll_urbanopt_simulation import (
    register as register_poll_urbanopt_simulation,
)
from ladybug_tools_mcp.tools.des.prepare_urbanopt_project import (
    register as register_prepare_urbanopt_project,
)
from ladybug_tools_mcp.tools.des.start_modelica_simulation import (
    register as register_start_modelica_simulation,
)
from ladybug_tools_mcp.tools.des.start_sys_param import (
    register as register_start_sys_param,
)
from ladybug_tools_mcp.tools.des.start_urbanopt_simulation import (
    register as register_start_urbanopt_simulation,
)
from ladybug_tools_mcp.tools.des.write_modelica_project import (
    register as register_write_modelica_project,
)


def register(mcp: FastMCP) -> None:
    """Register Dragonfly DES authoring tools."""
    register_create_thermal_connector(mcp)
    register_create_horizontal_pipe_parameter(mcp)
    register_create_ghe_soil_parameter(mcp)
    register_create_ghe_fluid_parameter(mcp)
    register_create_ghe_pipe_parameter(mcp)
    register_create_ghe_borehole_parameter(mcp)
    register_create_ghe_design_parameter(mcp)
    register_create_ground_heat_exchanger(mcp)
    register_create_fourth_gen_thermal_loop(mcp)
    register_create_fifth_gen_thermal_loop(mcp)
    register_create_ghe_thermal_loop(mcp)
    register_export_urbanopt_model(mcp)
    register_export_model_to_des(mcp)
    register_prepare_urbanopt_project(mcp)
    register_start_urbanopt_simulation(mcp)
    register_poll_urbanopt_simulation(mcp)
    register_list_urbanopt_run_outputs(mcp)
    register_assign_building_loads(mcp)
    register_start_sys_param(mcp)
    register_poll_sys_param(mcp)
    register_write_modelica_project(mcp)
    register_start_modelica_simulation(mcp)
    register_poll_modelica_simulation(mcp)
