"""Namespace and public tool-name policy for Ladybug Tools MCP."""

from __future__ import annotations

import re
from collections.abc import Callable

from fastmcp import FastMCP


TOOL_NAMESPACE_BY_FAMILY: dict[str, str] = {
    "config": "config",
    "garden": "garden",
    "flowerpot": "flowerpot",
    "libraries": "library",
    "web_view": "web_view",
    "honeybee_core": "honeybee",
    "dragonfly_core": "dragonfly",
    "energy": "energy",
    "run_energy": "energyplus",
    "radiance": "radiance",
    "visualize": "visualization",
    "run_uwg": "uwg",
    "fairyfly": "therm",
    "ironbug_core": "detailed_hvac",
}


# Namespace-local names remove only repeated family prefixes. They should keep
# the domain object and output type readable once the runtime namespace is
# prepended, for example ``visualization_set_to_vtkjs`` or
# ``detailed_hvac_zone_equipment_ptac``.
EXPLICIT_LOCAL_TOOL_NAMES: dict[str, str] = {
    "get_ladybug_tools_config": "get_runtime_config",
    "cleanup_garden_workspace": "cleanup_workspace",
    "create_garden": "create",
    "create_garden_version": "create_version",
    "export_model_file": "export_model_file",
    "get_base_dragonfly_model": "get_base_dragonfly_model",
    "get_base_honeybee_model": "get_base_honeybee_model",
    "get_garden": "get",
    "get_garden_version_status": "get_version_status",
    "list_garden_artifacts": "list_artifacts",
    "list_garden_models": "list_models",
    "list_garden_versions": "list_versions",
    "list_gardens": "list",
    "restore_garden_version": "restore_version",
    "save_base_dragonfly_model": "save_base_dragonfly_model",
    "save_base_honeybee_model": "save_base_honeybee_model",
    "set_base_dragonfly_model": "set_base_dragonfly_model",
    "set_base_honeybee_model": "set_base_honeybee_model",
    "cleanup_flowerpots": "cleanup_all",
    "create_flowerpot": "create",
    "get_flowerpot": "get",
    "get_active_flowerpot_context": "get_active_context",
    "get_garden_properties_library_object": "get_garden_properties_object",
    "normalize_garden_properties_library_storage": "normalize_garden_properties_storage",
    "save_garden_properties_library_object": "save_garden_properties_object",
    "search_garden_properties_library_objects": "search_garden_properties_objects",
    "start_web_view_mode": "start_mode",
    "stop_web_view_mode": "stop_mode",
    "honeybee_model_to_dragonfly": "convert_honeybee_model_to_dragonfly",
    "dragonfly_model_to_honeybee": "model_to_honeybee",
    "dragonfly_model_envelope_edges_to_visualization_set": "model_envelope_edges_to_visualization_set",
    "dragonfly_model_to_visualization_set": "model_to_visualization_set",
    "dragonfly_models_to_comparison_visualization_set": "models_to_comparison_visualization_set",
    "create_energy_output_request": "create_output_request",
    "download_epw": "download_epw",
    "energy_result_hourly_plot_to_html": "result_hourly_plot_to_html",
    "energy_result_monthly_chart_to_html": "result_monthly_chart_to_html",
    "get_energy_run": "poll_simulation",
    "list_energy_run_outputs": "list_run_outputs",
    "list_energy_runs": "list_runs",
    "read_energy_errors": "read_errors",
    "read_energy_eui": "read_eui",
    "read_energy_result_data": "read_result_data",
    "read_weather_file_data": "read_weather_file_data",
    "run_energy": "run_simulation_wait",
    "run_idf_file": "run_idf_file",
    "run_osm_file": "run_osm_file",
    "search_epw_map": "search_epw_map",
    "search_weather_files": "search_weather_files",
    "start_energy_run": "start_simulation",
    "apply_dragonfly_uwg_properties": "apply_dragonfly_properties",
    "create_uwg_simulation_parameter": "create_simulation_parameter",
    "get_uwg_run": "poll_simulation",
    "list_uwg_run_outputs": "list_run_outputs",
    "list_uwg_runs": "list_runs",
    "run_uwg": "run_simulation_wait",
    "start_uwg_run": "start_simulation",
    "dragonfly_model_to_uwg": "dragonfly_model_to_uwg",
    "get_dragonfly_uwg_properties_summary": "get_dragonfly_properties_summary",
    "add_radiance_luminaire_to_model": "add_luminaire_to_model",
    "create_radiance_glass_modifier": "create_glass_modifier",
    "create_radiance_luminaire": "create_luminaire",
    "create_radiance_metal_modifier": "create_metal_modifier",
    "create_radiance_mirror_modifier": "create_mirror_modifier",
    "create_radiance_opaque_modifier": "create_opaque_modifier",
    "create_radiance_parameters": "create_parameters",
    "create_radiance_sensor_grid": "create_sensor_grid",
    "create_radiance_sensor_grid_from_object": "create_sensor_grid_from_object",
    "create_radiance_shade_state": "create_shade_state",
    "create_radiance_sky": "create_sky",
    "create_radiance_sky_file": "create_sky_file",
    "create_radiance_state_geometry": "create_state_geometry",
    "create_radiance_subface_state": "create_subface_state",
    "create_radiance_trans_modifier": "create_trans_modifier",
    "create_radiance_view": "create_view",
    "get_radiance_run": "poll_simulation",
    "list_radiance_artifact_files": "list_artifact_files",
    "list_radiance_artifacts": "list_artifacts",
    "list_radiance_grid_results": "list_grid_results",
    "list_radiance_hdr_images": "list_hdr_images",
    "list_radiance_run_outputs": "list_run_outputs",
    "list_radiance_runs": "list_runs",
    "radiance_grid_result_to_visualization_set": "grid_result_to_visualization_set",
    "radiance_hdr_to_falsecolor": "hdr_to_falsecolor",
    "radiance_hdr_to_gif": "hdr_to_gif",
    "search_radiance_images": "search_images",
    "search_radiance_library_objects": "search_library_objects",
    "search_radiance_parameters": "search_parameters",
    "search_radiance_sensor_grids": "search_sensor_grids",
    "search_radiance_sky_files": "search_sky_files",
    "search_radiance_views": "search_views",
    "search_radiance_visualizations": "search_visualizations",
    "setup_radiance_dynamic_group": "setup_dynamic_group",
    "start_radiance_grid_run": "start_grid_simulation",
    "start_radiance_matrix_run": "start_matrix_simulation",
    "start_radiance_view_run": "start_view_simulation",
    "summarize_radiance_glare_metrics": "summarize_glare_metrics",
    "honeybee_face_to_visualization_set": "honeybee_face_to_visualization_set",
    "honeybee_model_to_visualization_set": "honeybee_model_to_visualization_set",
    "honeybee_room_to_visualization_set": "honeybee_room_to_visualization_set",
    "compose_model_analysis_visualization_set": "compose_model_analysis_visualization_set",
    "compose_visualization_sets": "compose_visualization_sets",
    "create_2d_legend_parameter": "create_2d_legend_parameter",
    "data_collection_hourly_plot_to_visualization_set": "data_collection_hourly_plot_to_visualization_set",
    "data_collection_monthly_chart_to_html": "data_collection_monthly_chart_to_html",
    "data_collection_monthly_chart_to_visualization_set": "data_collection_monthly_chart_to_visualization_set",
    "data_collection_to_file": "data_collection_to_file",
    "edit_2d_legend_parameter": "edit_2d_legend_parameter",
    "sky_matrix_to_radiation_dome_visualization_set": "sky_matrix_to_radiation_dome_visualization_set",
    "sky_matrix_to_skydome_visualization_set": "sky_matrix_to_skydome_visualization_set",
    "sunpath_to_visualization_set": "sunpath_to_visualization_set",
    "visualization_set_to_html": "set_to_html",
    "visualization_set_to_svg": "set_to_svg",
    "visualization_set_to_vtkjs": "set_to_vtkjs",
    "fairyfly_model_to_visualization_set": "model_to_visualization_set",
    "fairyfly_therm_result_to_visualization_set": "result_to_visualization_set",
    "get_base_fairyfly_model": "get_base_model",
    "get_fairyfly_therm_run": "poll_simulation",
    "list_fairyfly_therm_runs": "list_runs",
    "read_fairyfly_therm_result": "read_result",
    "read_fairyfly_u_factor_result": "read_u_factor",
    "set_base_fairyfly_model": "set_base_model",
    "start_fairyfly_therm_run": "start_simulation",
    "validate_fairyfly_model": "validate_model",
    "write_fairyfly_model_to_thmz": "write_model_to_thmz",
    "add_fairyfly_boundary_to_model": "add_boundary_to_model",
    "add_fairyfly_shape_to_model": "add_shape_to_model",
    "create_fairyfly_model": "create_model",
    "create_fairyfly_solid_material": "create_solid_material",
    "add_ironbug_hvac_component": "add_hvac_component_fallback",
    "apply_ironbug_detailed_hvac_to_dragonfly_energy_properties": "apply_to_dragonfly_energy_properties",
    "apply_ironbug_detailed_hvac_to_dragonfly_model": "apply_to_dragonfly_model",
    "apply_ironbug_detailed_hvac_to_honeybee_model": "apply_to_honeybee_model",
    "create_ironbug_chilled_water_loop": "plant_loop_chilled_water",
    "create_ironbug_condenser_water_loop": "plant_loop_condenser_water",
    "create_ironbug_detailed_hvac": "create_detailed_hvac_system",
    "create_ironbug_hot_water_loop": "plant_loop_hot_water",
    "create_ironbug_model": "create_model",
    "list_ironbug_hvac_component_types": "list_hvac_component_types",
    "search_ironbug_model_objects": "search_model_objects",
    "validate_ironbug_model": "validate_model",
}


def normalize_component_parameter_name(value: str) -> str:
    """Return a lowercase snake_case component slug."""

    text = value.strip("_")
    parts: list[str] = []
    for token in re.split(r"[^0-9A-Za-z]+", text):
        if not token:
            continue
        token = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", token)
        token = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", token)
        parts.append(token.lower())
    return "_".join(parts)


def ironbug_component_short_name(source_class: str) -> str:
    """Return the namespace-local short name for an Ironbug source class."""

    explicit = {
        "IB_ZoneHVACPackagedTerminalAirConditioner": "zone_equipment_ptac",
        "IB_ZoneHVACPackagedTerminalHeatPump": "zone_equipment_pthp",
        "IB_ZoneHVACFourPipeFanCoil": "zone_equipment_four_pipe_fan_coil",
        "IB_AirTerminalSingleDuctVAVReheat": "air_terminal_vav_reheat",
        "IB_AirTerminalSingleDuctVAVNoReheat": "air_terminal_vav_no_reheat",
        "IB_AirLoopHVAC": "air_loop_hvac",
        "IB_FanOnOff": "fan_on_off",
        "IB_FanConstantVolume": "fan_constant_volume",
        "IB_PumpConstantSpeed": "pump_constant_speed",
        "IB_PumpVariableSpeed": "pump_variable_speed",
        "IB_ChillerElectricEIR": "chiller_electric_eir",
        "IB_BoilerHotWater": "boiler_hot_water",
    }
    if source_class in explicit:
        return explicit[source_class]
    text = re.sub(r"^IB_", "", source_class.strip())
    slug = normalize_component_parameter_name(text)
    if slug.startswith("zone_hvac_"):
        return "zone_equipment_" + slug.removeprefix("zone_hvac_")
    if slug.startswith("air_loop_hvac_"):
        return "air_loop_" + slug.removeprefix("air_loop_hvac_")
    return slug


def local_tool_name(
    old_name: str,
    *,
    family: str,
    source_class: str | None = None,
) -> str:
    """Return the namespace-local callable name for an existing wrapper name."""

    if old_name in EXPLICIT_LOCAL_TOOL_NAMES:
        return EXPLICIT_LOCAL_TOOL_NAMES[old_name]
    if family == "honeybee_core":
        return old_name.replace("_honeybee_", "_").removeprefix("honeybee_")
    if family == "dragonfly_core":
        return old_name.replace("_dragonfly_", "_").removeprefix("dragonfly_")
    if family == "ironbug_core":
        if source_class:
            return ironbug_component_short_name(source_class)
        return old_name.replace("_ironbug_", "_").removeprefix("ironbug_")
    return old_name


def public_tool_name(
    old_name: str,
    *,
    family: str,
    source_class: str | None = None,
) -> str:
    """Return the runtime public tool name after namespace mounting."""

    namespace = TOOL_NAMESPACE_BY_FAMILY[family]
    return f"{namespace}_{local_tool_name(old_name, family=family, source_class=source_class)}"


def mount_registered_family(
    parent: FastMCP,
    *,
    family: str,
    register: Callable[[FastMCP], None],
) -> None:
    """Register a tool family on a child server and mount it under a namespace."""

    namespace = TOOL_NAMESPACE_BY_FAMILY[family]
    child = FastMCP(
        f"Ladybug Tools MCP {namespace}",
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register(child)
    parent.mount(child, namespace=namespace)
