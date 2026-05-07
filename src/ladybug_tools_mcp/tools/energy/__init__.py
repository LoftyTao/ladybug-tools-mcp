"""Honeybee Energy tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.energy.create_air_boundary_construction import (
    register as register_create_air_boundary_construction,
)
from ladybug_tools_mcp.tools.energy.create_aperture_construction_set import (
    register as register_create_aperture_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_construction_set import (
    register as register_create_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_custom_window_gas_material import (
    register as register_create_custom_window_gas_material,
)
from ladybug_tools_mcp.tools.energy.create_door_construction_set import (
    register as register_create_door_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_electric_equipment import (
    register as register_create_electric_equipment,
)
from ladybug_tools_mcp.tools.energy.create_electric_load_center import (
    register as register_create_electric_load_center,
)
from ladybug_tools_mcp.tools.energy.create_floor_construction_set import (
    register as register_create_floor_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_gas_equipment import (
    register as register_create_gas_equipment,
)
from ladybug_tools_mcp.tools.energy.create_ideal_air_system import (
    register as register_create_ideal_air_system,
)
from ladybug_tools_mcp.tools.energy.create_infiltration import (
    register as register_create_infiltration,
)
from ladybug_tools_mcp.tools.energy.create_lighting import (
    register as register_create_lighting,
)
from ladybug_tools_mcp.tools.energy.create_opaque_construction import (
    register as register_create_opaque_construction,
)
from ladybug_tools_mcp.tools.energy.create_opaque_material import (
    register as register_create_opaque_material,
)
from ladybug_tools_mcp.tools.energy.create_opaque_no_mass_material import (
    register as register_create_opaque_no_mass_material,
)
from ladybug_tools_mcp.tools.energy.create_people import (
    register as register_create_people,
)
from ladybug_tools_mcp.tools.energy.create_program_type import (
    register as register_create_program_type,
)
from ladybug_tools_mcp.tools.energy.create_pv_properties import (
    register as register_create_pv_properties,
)
from ladybug_tools_mcp.tools.energy.create_roof_ceiling_construction_set import (
    register as register_create_roof_ceiling_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_schedule_day import (
    register as register_create_schedule_day,
)
from ladybug_tools_mcp.tools.energy.create_schedule_rule import (
    register as register_create_schedule_rule,
)
from ladybug_tools_mcp.tools.energy.create_schedule_ruleset import (
    register as register_create_schedule_ruleset,
)
from ladybug_tools_mcp.tools.energy.create_service_hot_water import (
    register as register_create_service_hot_water,
)
from ladybug_tools_mcp.tools.energy.create_setpoint import (
    register as register_create_setpoint,
)
from ladybug_tools_mcp.tools.energy.create_shade_construction import (
    register as register_create_shade_construction,
)
from ladybug_tools_mcp.tools.energy.create_simple_glazing_material import (
    register as register_create_simple_glazing_material,
)
from ladybug_tools_mcp.tools.energy.create_vegetation_material import (
    register as register_create_vegetation_material,
)
from ladybug_tools_mcp.tools.energy.create_ventilation import (
    register as register_create_ventilation,
)
from ladybug_tools_mcp.tools.energy.create_zone_ventilation_fan import (
    register as register_create_zone_ventilation_fan,
)
from ladybug_tools_mcp.tools.energy.create_wall_construction_set import (
    register as register_create_wall_construction_set,
)
from ladybug_tools_mcp.tools.energy.create_window_blind_material import (
    register as register_create_window_blind_material,
)
from ladybug_tools_mcp.tools.energy.create_window_construction import (
    register as register_create_window_construction,
)
from ladybug_tools_mcp.tools.energy.create_window_frame_material import (
    register as register_create_window_frame_material,
)
from ladybug_tools_mcp.tools.energy.create_window_gas_material import (
    register as register_create_window_gas_material,
)
from ladybug_tools_mcp.tools.energy.create_window_gas_mixture_material import (
    register as register_create_window_gas_mixture_material,
)
from ladybug_tools_mcp.tools.energy.create_window_glazing_material import (
    register as register_create_window_glazing_material,
)
from ladybug_tools_mcp.tools.energy.create_window_shade_material import (
    register as register_create_window_shade_material,
)
from ladybug_tools_mcp.tools.energy.search_energy_library_objects import (
    register as register_search_energy_library_objects,
)
from ladybug_tools_mcp.tools.energy.search_hvac_templates import (
    register as register_search_hvac_templates,
)
from ladybug_tools_mcp.tools.energy.setup_airflow_network import (
    register as register_setup_airflow_network,
)
from ladybug_tools_mcp.tools.energy.setup_daylighting_control_to_center import (
    register as register_setup_daylighting_control_to_center,
)
from ladybug_tools_mcp.tools.energy.setup_simple_ventilation_properties import (
    register as register_setup_simple_ventilation_properties,
)


def register(mcp: FastMCP) -> None:
    """Register Honeybee Energy tools."""
    register_create_schedule_day(mcp)
    register_create_schedule_rule(mcp)
    register_create_schedule_ruleset(mcp)
    register_create_opaque_material(mcp)
    register_create_opaque_no_mass_material(mcp)
    register_create_vegetation_material(mcp)
    register_create_window_glazing_material(mcp)
    register_create_simple_glazing_material(mcp)
    register_create_window_gas_material(mcp)
    register_create_custom_window_gas_material(mcp)
    register_create_window_gas_mixture_material(mcp)
    register_create_window_frame_material(mcp)
    register_create_window_shade_material(mcp)
    register_create_window_blind_material(mcp)
    register_create_opaque_construction(mcp)
    register_create_window_construction(mcp)
    register_create_shade_construction(mcp)
    register_create_air_boundary_construction(mcp)
    register_create_wall_construction_set(mcp)
    register_create_floor_construction_set(mcp)
    register_create_roof_ceiling_construction_set(mcp)
    register_create_aperture_construction_set(mcp)
    register_create_door_construction_set(mcp)
    register_create_construction_set(mcp)
    register_create_people(mcp)
    register_create_lighting(mcp)
    register_create_electric_equipment(mcp)
    register_create_electric_load_center(mcp)
    register_create_gas_equipment(mcp)
    register_create_ventilation(mcp)
    register_create_infiltration(mcp)
    register_create_service_hot_water(mcp)
    register_create_setpoint(mcp)
    register_create_program_type(mcp)
    register_create_zone_ventilation_fan(mcp)
    register_create_pv_properties(mcp)
    register_setup_simple_ventilation_properties(mcp)
    register_setup_airflow_network(mcp)
    register_setup_daylighting_control_to_center(mcp)
    register_create_ideal_air_system(mcp)
    register_search_hvac_templates(mcp)
    register_search_energy_library_objects(mcp)
