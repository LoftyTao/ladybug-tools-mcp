"""Honeybee Radiance tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.radiance.add_radiance_luminaire_to_model import (
    register as register_add_radiance_luminaire_to_model,
)
from ladybug_tools_mcp.tools.radiance.create_ashrae_clear_sky_wea import (
    register as register_create_ashrae_clear_sky_wea,
)
from ladybug_tools_mcp.tools.radiance.create_cie_standard_sky import (
    register as register_create_cie_standard_sky,
)
from ladybug_tools_mcp.tools.radiance.create_climate_based_sky import (
    register as register_create_climate_based_sky,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_parameters import (
    register as register_create_radiance_parameters,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_sky import (
    register as register_create_radiance_sky,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_sky_file import (
    register as register_create_radiance_sky_file,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_glass_modifier import (
    register as register_create_radiance_glass_modifier,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_metal_modifier import (
    register as register_create_radiance_metal_modifier,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_mirror_modifier import (
    register as register_create_radiance_mirror_modifier,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_opaque_modifier import (
    register as register_create_radiance_opaque_modifier,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_luminaire import (
    register as register_create_radiance_luminaire,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_sensor_grid import (
    register as register_create_radiance_sensor_grid,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_sensor_grid_from_object import (
    register as register_create_radiance_sensor_grid_from_object,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_shade_state import (
    register as register_create_radiance_shade_state,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_state_geometry import (
    register as register_create_radiance_state_geometry,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_subface_state import (
    register as register_create_radiance_subface_state,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_trans_modifier import (
    register as register_create_radiance_trans_modifier,
)
from ladybug_tools_mcp.tools.radiance.create_radiance_view import (
    register as register_create_radiance_view,
)
from ladybug_tools_mcp.tools.radiance.create_sky_matrix import (
    register as register_create_sky_matrix,
)
from ladybug_tools_mcp.tools.radiance.create_wea_from_weather_file import (
    register as register_create_wea_from_weather_file,
)
from ladybug_tools_mcp.tools.radiance.get_radiance_run import (
    register as register_get_radiance_run,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_grid_results import (
    register as register_list_radiance_grid_results,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_artifact_files import (
    register as register_list_radiance_artifact_files,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_artifacts import (
    register as register_list_radiance_artifacts,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_hdr_images import (
    register as register_list_radiance_hdr_images,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_run_outputs import (
    register as register_list_radiance_run_outputs,
)
from ladybug_tools_mcp.tools.radiance.list_radiance_runs import (
    register as register_list_radiance_runs,
)
from ladybug_tools_mcp.tools.radiance.radiance_grid_result_to_visualization_set import (
    register as register_radiance_grid_result_to_visualization_set,
)
from ladybug_tools_mcp.tools.radiance.radiance_hdr_to_falsecolor import (
    register as register_radiance_hdr_to_falsecolor,
)
from ladybug_tools_mcp.tools.radiance.radiance_hdr_to_gif import (
    register as register_radiance_hdr_to_gif,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_library_objects import (
    register as register_search_radiance_library_objects,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_sensor_grids import (
    register as register_search_radiance_sensor_grids,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_sky_files import (
    register as register_search_radiance_sky_files,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_parameters import (
    register as register_search_radiance_parameters,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_visualizations import (
    register as register_search_radiance_visualizations,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_views import (
    register as register_search_radiance_views,
)
from ladybug_tools_mcp.tools.radiance.search_radiance_images import (
    register as register_search_radiance_images,
)
from ladybug_tools_mcp.tools.radiance.setup_radiance_dynamic_group import (
    register as register_setup_radiance_dynamic_group,
)
from ladybug_tools_mcp.tools.radiance.summarize_annual_daylight_metrics import (
    register as register_summarize_annual_daylight_metrics,
)
from ladybug_tools_mcp.tools.radiance.summarize_radiance_glare_metrics import (
    register as register_summarize_radiance_glare_metrics,
)
from ladybug_tools_mcp.tools.radiance.start_radiance_grid_run import (
    register as register_start_radiance_grid_run,
)
from ladybug_tools_mcp.tools.radiance.start_radiance_matrix_run import (
    register as register_start_radiance_matrix_run,
)
from ladybug_tools_mcp.tools.radiance.start_radiance_view_run import (
    register as register_start_radiance_view_run,
)


def register(mcp: FastMCP) -> None:
    """Register Honeybee Radiance tools."""
    register_create_radiance_opaque_modifier(mcp)
    register_create_radiance_mirror_modifier(mcp)
    register_create_radiance_metal_modifier(mcp)
    register_create_radiance_trans_modifier(mcp)
    register_create_radiance_glass_modifier(mcp)
    register_create_radiance_luminaire(mcp)
    register_add_radiance_luminaire_to_model(mcp)
    register_create_radiance_state_geometry(mcp)
    register_create_radiance_shade_state(mcp)
    register_create_radiance_subface_state(mcp)
    register_setup_radiance_dynamic_group(mcp)
    register_create_radiance_sensor_grid(mcp)
    register_create_radiance_sensor_grid_from_object(mcp)
    register_create_radiance_view(mcp)
    register_create_wea_from_weather_file(mcp)
    register_create_ashrae_clear_sky_wea(mcp)
    register_create_cie_standard_sky(mcp)
    register_create_radiance_sky(mcp)
    register_create_radiance_sky_file(mcp)
    register_create_climate_based_sky(mcp)
    register_create_sky_matrix(mcp)
    register_create_radiance_parameters(mcp)
    register_start_radiance_grid_run(mcp)
    register_start_radiance_view_run(mcp)
    register_start_radiance_matrix_run(mcp)
    register_get_radiance_run(mcp)
    register_list_radiance_runs(mcp)
    register_list_radiance_run_outputs(mcp)
    register_list_radiance_artifact_files(mcp)
    register_list_radiance_artifacts(mcp)
    register_list_radiance_hdr_images(mcp)
    register_radiance_hdr_to_falsecolor(mcp)
    register_radiance_hdr_to_gif(mcp)
    register_list_radiance_grid_results(mcp)
    register_radiance_grid_result_to_visualization_set(mcp)
    register_summarize_annual_daylight_metrics(mcp)
    register_summarize_radiance_glare_metrics(mcp)
    register_search_radiance_library_objects(mcp)
    register_search_radiance_sensor_grids(mcp)
    register_search_radiance_sky_files(mcp)
    register_search_radiance_parameters(mcp)
    register_search_radiance_visualizations(mcp)
    register_search_radiance_views(mcp)
    register_search_radiance_images(mcp)
