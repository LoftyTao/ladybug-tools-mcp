"""Create Ironbug model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import create_ironbug_model as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_create_model tool.'

    @mcp.tool(
        name="create_model",
        description=(
            "Create a Garden-managed Ironbug-Core IB_Model and save it as .ibjson. "
            "Returns an ironbug_model target, compact summary_view, and persistence "
            "receipt; it does not return the full ibjson body. Use this before "
            'detailed_hvac_validate_model or detailed_hvac_search_model_objects. This does not '
            "generate OSM/IDF or run EnergyPlus. Required arguments are garden_root "
            "and identifier; there is no model_name, hvac_system_type, "
            "set_base, return_object_dict, or include_body argument."
        ),
        tags={"ironbug", "detailed-hvac", "model", "author"},
        timeout=20,
    )
    def create_ironbug_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        identifier: Annotated[
            str,
            Field(
                description=(
                    "Stable Ironbug model identifier used for the .ibjson file name; "
                    "use identifier, not model_name, name, or set_base."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug model display name."),
        ] = None,
        include_hvac_system: Annotated[
            bool,
            Field(
                description=(
                    "When true, initialize an empty IB_HVACSystem under IB_Model; "
                    "use this boolean, not hvac_system_type."
                )
            ),
        ] = True,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Replace an existing models/ironbug/<identifier>.ibjson file; "
                    "set overwrite=True intentionally when retrying the same identifier."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Garden-managed Ironbug model."""

        return service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            include_hvac_system=include_hvac_system,
            overwrite=overwrite,
        )
