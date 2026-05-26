"""List Ironbug HVAC component types MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import list_ironbug_hvac_component_types as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_list_hvac_component_types tool.'

    @mcp.tool(
        name="list_hvac_component_types",
        description=(
            "List source-backed Ironbug HVAC component types that the assembly "
            "tools can create for Garden-managed .ibjson models. Use this before "
            'detailed_hvac_add_hvac_component_fallback. It returns component_types with '
            "component_type ids, Ironbug source classes, source paths, and whether "
            "the type is useful for source-backed plant-loop examples such as "
            "Example 1, Example 3 plant-core, or boiler hot-water loops. Optional "
            "query filters by component id, source class, source path, or example. "
            "Returns summary_view and report for fallback component selection."
        ),
        tags={"ironbug", "detailed-hvac", "component", "search"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_ironbug_hvac_component_types(
        garden_root: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; this list is global and does "
                    "not require garden_root."
                )
            ),
        ] = None,
        ironbug_model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Ironbug model target context. This list is global "
                    "and does not require ironbug_model_target."
                )
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Optional case-insensitive filter over component_type, "
                    "source_class, source_path, and example tags. Pass empty or "
                    "omit it to list all supported component types."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List source-backed Ironbug HVAC component types."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            query=query,
        )
