"""Visualize tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.visualize.compose_visualization_sets import (
    register as register_compose_visualization_sets,
)
from ladybug_tools_mcp.tools.visualize.compose_model_analysis_visualization_set import (
    register as register_compose_model_analysis_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.create_2d_legend_parameter import (
    register as register_create_2d_legend_parameter,
)
from ladybug_tools_mcp.tools.visualize.data_collection_hourly_plot_to_visualization_set import (
    register as register_data_collection_hourly_plot_to_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.data_collection_monthly_chart_to_html import (
    register as register_data_collection_monthly_chart_to_html,
)
from ladybug_tools_mcp.tools.visualize.data_collection_monthly_chart_to_visualization_set import (
    register as register_data_collection_monthly_chart_to_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.data_collection_to_file import (
    register as register_data_collection_to_file,
)
from ladybug_tools_mcp.tools.visualize.edit_2d_legend_parameter import (
    register as register_edit_2d_legend_parameter,
)
from ladybug_tools_mcp.tools.visualize.honeybee_face_to_visualization_set import (
    register as register_honeybee_face_to_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.honeybee_model_to_visualization_set import (
    register as register_honeybee_model_to_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.honeybee_room_to_visualization_set import (
    register as register_honeybee_room_to_visualization_set,
)
from ladybug_tools_mcp.tools.visualize.visualization_set_to_html import (
    register as register_visualization_set_to_html,
)
from ladybug_tools_mcp.tools.visualize.visualization_set_to_svg import (
    register as register_visualization_set_to_svg,
)
from ladybug_tools_mcp.tools.visualize.visualization_set_to_vtkjs import (
    register as register_visualization_set_to_vtkjs,
)


def register(mcp: FastMCP) -> None:
    """Register Visualize tools."""
    register_create_2d_legend_parameter(mcp)
    register_edit_2d_legend_parameter(mcp)
    register_data_collection_hourly_plot_to_visualization_set(mcp)
    register_data_collection_monthly_chart_to_visualization_set(mcp)
    register_data_collection_monthly_chart_to_html(mcp)
    register_data_collection_to_file(mcp)
    register_honeybee_model_to_visualization_set(mcp)
    register_honeybee_room_to_visualization_set(mcp)
    register_honeybee_face_to_visualization_set(mcp)
    register_compose_visualization_sets(mcp)
    register_compose_model_analysis_visualization_set(mcp)
    register_visualization_set_to_html(mcp)
    register_visualization_set_to_svg(mcp)
    register_visualization_set_to_vtkjs(mcp)
