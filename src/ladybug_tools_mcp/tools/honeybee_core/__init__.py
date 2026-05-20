"""Honeybee Core tool registration."""

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_aperture import (
    register as register_create_honeybee_aperture,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_apertures_by_parameters import (
    register as register_create_honeybee_apertures_by_parameters,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_door import (
    register as register_create_honeybee_door,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_face import (
    register as register_create_honeybee_face,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_model import (
    register as register_create_honeybee_model,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_room import (
    register as register_create_honeybee_room,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_shade import (
    register as register_create_honeybee_shade,
)
from ladybug_tools_mcp.tools.honeybee_core.create_honeybee_shades_by_parameters import (
    register as register_create_honeybee_shades_by_parameters,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_aperture import (
    register as register_edit_honeybee_aperture,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_door import (
    register as register_edit_honeybee_door,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_face import (
    register as register_edit_honeybee_face,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_model import (
    register as register_edit_honeybee_model,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_room import (
    register as register_edit_honeybee_room,
)
from ladybug_tools_mcp.tools.honeybee_core.edit_honeybee_shade import (
    register as register_edit_honeybee_shade,
)
from ladybug_tools_mcp.tools.honeybee_core.mirror_object import (
    register as register_mirror_object,
)
from ladybug_tools_mcp.tools.honeybee_core.move_object import (
    register as register_move_object,
)
from ladybug_tools_mcp.tools.honeybee_core.relate_honeybee_model import (
    register as register_relate_honeybee_model,
)
from ladybug_tools_mcp.tools.honeybee_core.remove_honeybee_aperture import (
    register as register_remove_honeybee_aperture,
)
from ladybug_tools_mcp.tools.honeybee_core.remove_honeybee_door import (
    register as register_remove_honeybee_door,
)
from ladybug_tools_mcp.tools.honeybee_core.remove_honeybee_face import (
    register as register_remove_honeybee_face,
)
from ladybug_tools_mcp.tools.honeybee_core.remove_honeybee_room import (
    register as register_remove_honeybee_room,
)
from ladybug_tools_mcp.tools.honeybee_core.remove_honeybee_shade import (
    register as register_remove_honeybee_shade,
)
from ladybug_tools_mcp.tools.honeybee_core.rotate_object import (
    register as register_rotate_object,
)
from ladybug_tools_mcp.tools.honeybee_core.scale_object import (
    register as register_scale_object,
)
from ladybug_tools_mcp.tools.honeybee_core.search_honeybee_model_objects import (
    register as register_search_honeybee_model_objects,
)
from ladybug_tools_mcp.tools.honeybee_core.validate_honeybee_model import (
    register as register_validate_honeybee_model,
)


def register(mcp: FastMCP) -> None:
    """Register Honeybee Core tools."""
    register_create_honeybee_model(mcp)
    register_create_honeybee_room(mcp)
    register_create_honeybee_face(mcp)
    register_create_honeybee_aperture(mcp)
    register_create_honeybee_apertures_by_parameters(mcp)
    register_create_honeybee_shades_by_parameters(mcp)
    register_create_honeybee_door(mcp)
    register_create_honeybee_shade(mcp)
    register_edit_honeybee_model(mcp)
    register_edit_honeybee_face(mcp)
    register_edit_honeybee_room(mcp)
    register_edit_honeybee_aperture(mcp)
    register_edit_honeybee_door(mcp)
    register_edit_honeybee_shade(mcp)
    register_remove_honeybee_face(mcp)
    register_remove_honeybee_aperture(mcp)
    register_remove_honeybee_door(mcp)
    register_remove_honeybee_room(mcp)
    register_remove_honeybee_shade(mcp)
    register_move_object(mcp)
    register_rotate_object(mcp)
    register_scale_object(mcp)
    register_mirror_object(mcp)
    register_relate_honeybee_model(mcp)
    register_validate_honeybee_model(mcp)
    register_search_honeybee_model_objects(mcp)
