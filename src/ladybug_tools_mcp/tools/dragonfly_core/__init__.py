"""Dragonfly Core tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_model import (
    register as register_create_dragonfly_model,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_room2d import (
    register as register_create_dragonfly_room2d,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_story import (
    register as register_create_dragonfly_story,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_building import (
    register as register_create_dragonfly_building,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_context_shade import (
    register as register_create_dragonfly_context_shade,
)
from ladybug_tools_mcp.tools.dragonfly_core.edit_dragonfly_room2d import (
    register as register_edit_dragonfly_room2d,
)
from ladybug_tools_mcp.tools.dragonfly_core.edit_dragonfly_model import (
    register as register_edit_dragonfly_model,
)
from ladybug_tools_mcp.tools.dragonfly_core.edit_dragonfly_story import (
    register as register_edit_dragonfly_story,
)
from ladybug_tools_mcp.tools.dragonfly_core.edit_dragonfly_building import (
    register as register_edit_dragonfly_building,
)
from ladybug_tools_mcp.tools.dragonfly_core.add_dragonfly_stories_to_building import (
    register as register_add_dragonfly_stories_to_building,
)
from ladybug_tools_mcp.tools.dragonfly_core.remove_dragonfly_stories_from_building import (
    register as register_remove_dragonfly_stories_from_building,
)
from ladybug_tools_mcp.tools.dragonfly_core.solve_dragonfly_story_adjacency import (
    register as register_solve_dragonfly_story_adjacency,
)
from ladybug_tools_mcp.tools.dragonfly_core.reset_dragonfly_story_adjacency import (
    register as register_reset_dragonfly_story_adjacency,
)
from ladybug_tools_mcp.tools.dragonfly_core.clean_dragonfly_room2d_geometry import (
    register as register_clean_dragonfly_room2d_geometry,
)
from ladybug_tools_mcp.tools.dragonfly_core.search_dragonfly_model_objects import (
    register as register_search_dragonfly_model_objects,
)
from ladybug_tools_mcp.tools.dragonfly_core.get_dragonfly_model_summary import (
    register as register_get_dragonfly_model_summary,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_window_parameter import (
    register as register_create_dragonfly_window_parameter,
)
from ladybug_tools_mcp.tools.dragonfly_core.apply_dragonfly_window_parameter import (
    register as register_apply_dragonfly_window_parameter,
)
from ladybug_tools_mcp.tools.dragonfly_core.create_dragonfly_shading_parameter import (
    register as register_create_dragonfly_shading_parameter,
)
from ladybug_tools_mcp.tools.dragonfly_core.apply_dragonfly_shading_parameter import (
    register as register_apply_dragonfly_shading_parameter,
)
from ladybug_tools_mcp.tools.dragonfly_core.get_dragonfly_properties_summary import (
    register as register_get_dragonfly_properties_summary,
)
from ladybug_tools_mcp.tools.dragonfly_core.apply_dragonfly_energy_properties import (
    register as register_apply_dragonfly_energy_properties,
)
from ladybug_tools_mcp.tools.dragonfly_core.apply_dragonfly_radiance_properties import (
    register as register_apply_dragonfly_radiance_properties,
)
from ladybug_tools_mcp.tools.dragonfly_core.validate_dragonfly_model import (
    register as register_validate_dragonfly_model,
)
from ladybug_tools_mcp.tools.dragonfly_core.dragonfly_model_to_honeybee import (
    register as register_dragonfly_model_to_honeybee,
)
from ladybug_tools_mcp.tools.dragonfly_core.honeybee_model_to_dragonfly import (
    register as register_honeybee_model_to_dragonfly,
)
from ladybug_tools_mcp.tools.dragonfly_core.dragonfly_model_to_visualization_set import (
    register as register_dragonfly_model_to_visualization_set,
)
from ladybug_tools_mcp.tools.dragonfly_core.dragonfly_model_envelope_edges_to_visualization_set import (
    register as register_dragonfly_model_envelope_edges_to_visualization_set,
)
from ladybug_tools_mcp.tools.dragonfly_core.dragonfly_models_to_comparison_visualization_set import (
    register as register_dragonfly_models_to_comparison_visualization_set,
)


def register(mcp: FastMCP) -> None:
    """Register Dragonfly Core tools."""
    register_create_dragonfly_model(mcp)
    register_create_dragonfly_room2d(mcp)
    register_create_dragonfly_story(mcp)
    register_create_dragonfly_building(mcp)
    register_create_dragonfly_context_shade(mcp)
    register_edit_dragonfly_model(mcp)
    register_edit_dragonfly_story(mcp)
    register_edit_dragonfly_building(mcp)
    register_edit_dragonfly_room2d(mcp)
    register_add_dragonfly_stories_to_building(mcp)
    register_remove_dragonfly_stories_from_building(mcp)
    register_solve_dragonfly_story_adjacency(mcp)
    register_reset_dragonfly_story_adjacency(mcp)
    register_clean_dragonfly_room2d_geometry(mcp)
    register_search_dragonfly_model_objects(mcp)
    register_get_dragonfly_model_summary(mcp)
    register_create_dragonfly_window_parameter(mcp)
    register_apply_dragonfly_window_parameter(mcp)
    register_create_dragonfly_shading_parameter(mcp)
    register_apply_dragonfly_shading_parameter(mcp)
    register_get_dragonfly_properties_summary(mcp)
    register_apply_dragonfly_energy_properties(mcp)
    register_apply_dragonfly_radiance_properties(mcp)
    register_validate_dragonfly_model(mcp)
    register_dragonfly_model_to_honeybee(mcp)
    register_honeybee_model_to_dragonfly(mcp)
    register_dragonfly_model_to_visualization_set(mcp)
    register_dragonfly_model_envelope_edges_to_visualization_set(mcp)
    register_dragonfly_models_to_comparison_visualization_set(mcp)
