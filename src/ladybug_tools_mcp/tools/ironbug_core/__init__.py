"""Ironbug-Core tool registration."""

from importlib import import_module
from pathlib import Path

from fastmcp import FastMCP

from ladybug_tools_mcp.tools.ironbug_core.apply_ironbug_detailed_hvac_to_dragonfly_model import (
    register as register_apply_ironbug_detailed_hvac_to_dragonfly_model,
)
from ladybug_tools_mcp.tools.ironbug_core.apply_ironbug_detailed_hvac_to_dragonfly_energy_properties import (
    register as register_apply_ironbug_detailed_hvac_to_dragonfly_energy_properties,
)
from ladybug_tools_mcp.tools.ironbug_core.apply_ironbug_detailed_hvac_to_honeybee_model import (
    register as register_apply_ironbug_detailed_hvac_to_honeybee_model,
)
from ladybug_tools_mcp.tools.ironbug_core.create_ironbug_model import (
    register as register_create_ironbug_model,
)
from ladybug_tools_mcp.tools.ironbug_core.create_ironbug_chilled_water_loop import (
    register as register_create_ironbug_chilled_water_loop,
)
from ladybug_tools_mcp.tools.ironbug_core.create_ironbug_condenser_water_loop import (
    register as register_create_ironbug_condenser_water_loop,
)
from ladybug_tools_mcp.tools.ironbug_core.create_ironbug_hot_water_loop import (
    register as register_create_ironbug_hot_water_loop,
)
from ladybug_tools_mcp.tools.ironbug_core.add_ironbug_hvac_component import (
    register as register_add_ironbug_hvac_component,
)
from ladybug_tools_mcp.tools.ironbug_core.list_ironbug_hvac_component_types import (
    register as register_list_ironbug_hvac_component_types,
)
from ladybug_tools_mcp.tools.ironbug_core.create_ironbug_detailed_hvac import (
    register as register_create_ironbug_detailed_hvac,
)
from ladybug_tools_mcp.tools.ironbug_core.search_ironbug_model_objects import (
    register as register_search_ironbug_model_objects,
)
from ladybug_tools_mcp.tools.ironbug_core.validate_ironbug_model import (
    register as register_validate_ironbug_model,
)


_SOURCE_CREATE_TOOL_EXCLUDES = {
    "create_ironbug_model",
    "create_ironbug_detailed_hvac",
    "create_ironbug_chilled_water_loop",
    "create_ironbug_condenser_water_loop",
    "create_ironbug_hot_water_loop",
}


def _iter_source_create_tool_module_names() -> tuple[str, ...]:
    """Return public per-file Ironbug create tool module names."""

    tools_dir = Path(__file__).parent
    return tuple(
        sorted(
            path.stem
            for path in tools_dir.glob("create_ironbug_*.py")
            if path.stem not in _SOURCE_CREATE_TOOL_EXCLUDES
        )
    )


def _register_source_create_tools(mcp: FastMCP) -> None:
    """Register per-file source-backed Ironbug create tools."""

    for module_name in _iter_source_create_tool_module_names():
        module = import_module(f"ladybug_tools_mcp.tools.ironbug_core.{module_name}")
        module.register(mcp)


def register(mcp: FastMCP) -> None:
    """Register Ironbug-Core tools."""

    register_create_ironbug_model(mcp)
    _register_source_create_tools(mcp)
    register_create_ironbug_chilled_water_loop(mcp)
    register_create_ironbug_condenser_water_loop(mcp)
    register_create_ironbug_hot_water_loop(mcp)
    register_list_ironbug_hvac_component_types(mcp)
    register_add_ironbug_hvac_component(mcp)
    register_validate_ironbug_model(mcp)
    register_search_ironbug_model_objects(mcp)
    register_create_ironbug_detailed_hvac(mcp)
    register_apply_ironbug_detailed_hvac_to_honeybee_model(mcp)
    register_apply_ironbug_detailed_hvac_to_dragonfly_model(mcp)
    register_apply_ironbug_detailed_hvac_to_dragonfly_energy_properties(mcp)
